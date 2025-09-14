from flask import request, jsonify
from flask_caching import Cache
from controllers.base_controller import BaseController
from services.room_api_service import RoomAPIService
from utils.logger import app_logger, log_room_conflict, log_database_operation


class RoomController(BaseController):
    """Contrôleur pour la gestion des salles et attributions"""

    def __init__(self, schedule_manager, cache_service):
        self.schedule_manager = schedule_manager
        self.room_api_service = RoomAPIService(schedule_manager, cache_service)
        self.cache_service = cache_service
        super().__init__('rooms', url_prefix='/api')

    def _register_routes(self):
        """Enregistrement des routes pour les salles"""
        self.blueprint.route('/assign_room', methods=['POST'])(self.assign_room)
        self.blueprint.route('/check_conflict', methods=['POST'])(self.check_conflict)
        self.blueprint.route('/get_conflict_details', methods=['POST'])(self.get_conflict_details)
        self.blueprint.route('/get_occupied_rooms', methods=['POST'])(self.get_occupied_rooms)
        self.blueprint.route('/batch_occupied_rooms', methods=['POST'])(self.batch_occupied_rooms)
        self.blueprint.route('/get_free_rooms', methods=['POST'])(self.get_free_rooms)
        self.blueprint.route('/test_sync_db', methods=['POST'])(self.test_sync_db)

    def assign_room(self):
        """API pour attribuer une salle à un cours"""
        try:
            data = self.get_json_data()
            course_id = data.get('course_id')
            room_id = data.get('room_id')

            app_logger.info(f"Room assignment request: {course_id} -> {room_id}")

            if not course_id:
                return self.error_response('Course ID manquant')

            # Si room_id est vide, on supprime l'attribution
            if not room_id:
                app_logger.info(f"Removing room assignment for course: {course_id}")
                if course_id in self.schedule_manager.room_assignments:
                    del self.schedule_manager.room_assignments[course_id]
                    self.schedule_manager.save_assignments()
                    self.schedule_manager.force_sync_data()
                    app_logger.info(f"Room assignment removed successfully: {course_id}")
                return self.success_response()

            # Vérifier les conflits avec détails
            conflict_details = self.schedule_manager.check_room_conflict_detailed(course_id, room_id)

            if conflict_details['has_conflict']:
                log_room_conflict(course_id, room_id, f"Conflict: {conflict_details}")
                return jsonify({
                    'success': False,
                    'error': 'Conflit de salle détecté',
                    'conflict_details': conflict_details
                })

            # Attribuer la salle
            app_logger.debug(f"Attempting room assignment: {course_id} -> {room_id}")
            success = self.schedule_manager.assign_room(course_id, room_id)
            app_logger.debug(f"Assignment result: {success}")

            if success:
                app_logger.info(f"Room assignment successful: {course_id} -> {room_id}")
                self.schedule_manager.force_sync_data()
                self.cache_service.invalidate_occupied_rooms_cache()

                # Synchronisation DB forcée
                try:
                    self.schedule_manager.data_service.sync_room_assignments_to_db(
                        self.schedule_manager.room_assignments
                    )
                    app_logger.info("Forced database synchronization")
                except Exception as sync_error:
                    app_logger.error(f"Database sync error: {sync_error}")

                # Vérification
                app_logger.debug(f"Verification: course {course_id} in assignments = {course_id in self.schedule_manager.room_assignments}")
                if course_id in self.schedule_manager.room_assignments:
                    app_logger.debug(f"Room assigned: {self.schedule_manager.room_assignments[course_id]}")

                return self.success_response()
            else:
                app_logger.warning(f"Room assignment failed: {course_id} -> {room_id}")
                return self.error_response('Erreur lors de l\'attribution')

        except Exception as e:
            app_logger.error(f"Room assignment exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return self.error_response(str(e), 500)

    def check_conflict(self):
        """API pour vérifier les conflits de salle"""
        try:
            data = self.get_json_data()
            course_id = data.get('course_id')
            room_id = data.get('room_id')

            if not course_id or not room_id:
                return jsonify({'conflict': False})

            conflict = self.schedule_manager.check_room_conflict(course_id, room_id)
            return jsonify({'conflict': conflict})

        except Exception as e:
            return jsonify({'conflict': True, 'error': str(e)})

    def get_conflict_details(self):
        """API pour obtenir les détails des conflits de salle"""
        try:
            data = self.get_json_data()
            course_id = data.get('course_id')
            room_id = data.get('room_id')

            if not course_id or not room_id:
                return jsonify({'has_conflict': False, 'conflicts': []})

            conflict_info = self.schedule_manager.check_room_conflict_detailed(course_id, room_id)
            return jsonify(conflict_info)

        except Exception as e:
            return jsonify({
                'has_conflict': True,
                'conflicts': [{'type': 'error', 'message': str(e)}]
            })

    def get_occupied_rooms(self):
        """API optimisée pour récupérer les salles occupées pour un créneau donné"""
        data = self.get_json_data()

        # Cache avec clé basée sur les données
        cache_key = f"occupied_{data.get('course_id', '')}"

        # Vérifier le cache manuel si nécessaire
        from flask import current_app
        cache = current_app.extensions.get('cache')
        if cache:
            result = cache.get(cache_key)
            if result is None:
                result = self.room_api_service.get_occupied_rooms(data)
                cache.set(cache_key, result, timeout=60)
                app_logger.debug(f"Cache miss: {cache_key}")
            else:
                app_logger.debug(f"Cache hit: {cache_key}")
        else:
            result = self.room_api_service.get_occupied_rooms(data)

        return jsonify(result)

    def batch_occupied_rooms(self):
        """API batch pour récupérer les salles occupées pour plusieurs créneaux"""
        try:
            data = self.get_json_data()
            course_ids = data.get('course_ids', [])

            if not course_ids:
                return self.error_response('No course_ids provided', 400)

            results = {}
            for course_id in course_ids:
                course_data = {'course_id': course_id}
                result = self.room_api_service.get_occupied_rooms(course_data)
                results[course_id] = result.get('occupied_rooms', [])

            return self.success_response({
                'results': results,
                'processed_count': len(course_ids)
            })

        except Exception as e:
            app_logger.error(f"Batch occupied rooms error: {e}")
            return self.error_response(str(e), 500)

    def get_free_rooms(self):
        """API pour récupérer les salles libres pour un créneau donné"""
        data = self.get_json_data()
        result = self.room_api_service.get_free_rooms(data)
        return jsonify(result)

    def test_sync_db(self):
        """Route de test pour déclencher manuellement la synchronisation DB"""
        try:
            app_logger.info("Manual synchronization test triggered")
            updated_count = self.schedule_manager.data_service.sync_room_assignments_to_db(
                self.schedule_manager.room_assignments
            )

            # Vérifier l'état après synchronisation
            all_courses = self.schedule_manager.get_all_courses()
            courses_with_rooms = len([c for c in all_courses if c.assigned_room])
            assignments_count = len(self.schedule_manager.room_assignments)

            app_logger.info(f"Sync summary: {updated_count} courses updated, {assignments_count} assignments, {courses_with_rooms} courses with rooms")

            return self.success_response({
                'updated_count': updated_count,
                'assignments_count': assignments_count,
                'courses_with_rooms': courses_with_rooms,
                'message': f'Synchronisation terminée: {updated_count} cours mis à jour'
            })

        except Exception as e:
            app_logger.error(f"Test sync error: {e}")
            import traceback
            traceback.print_exc()
            return self.error_response(str(e), 500)