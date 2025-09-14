from flask import request, jsonify
from controllers.base_controller import BaseController
from services.course_api_service import CourseAPIService
from application.services.course_application_service import CourseApplicationService


class CourseController(BaseController):
    """Contrôleur pour la gestion des cours"""

    def __init__(self, schedule_manager):
        self.schedule_manager = schedule_manager
        self.course_api_service = CourseAPIService(schedule_manager)
        self.clean_course_service = CourseApplicationService()
        super().__init__('courses', url_prefix='/api/courses')

    def _register_routes(self):
        """Enregistrement des routes pour les cours"""
        self.blueprint.route('/add_custom', methods=['POST'])(self.add_custom_course)
        self.blueprint.route('/move', methods=['POST'])(self.move_custom_course)
        self.blueprint.route('/duplicate', methods=['POST'])(self.duplicate_course)
        self.blueprint.route('/delete', methods=['POST'])(self.delete_course)
        self.blueprint.route('/update_tp_name', methods=['POST'])(self.update_tp_name)
        self.blueprint.route('/get_tp_names', methods=['GET'])(self.get_tp_names)
        self.blueprint.route('/delete_tp_name', methods=['POST'])(self.delete_tp_name)
        self.blueprint.route('', methods=['GET'])(self.get_courses_clean)
        self.blueprint.route('/room/<room_id>', methods=['GET'])(self.get_courses_by_room_clean)

    def add_custom_course(self):
        """API pour ajouter un TP personnalisé"""
        data = self.get_json_data()

        # Validation
        required_fields = ['week_name', 'day', 'raw_time_slot', 'professor', 'course_type']
        validation_error = self.validate_required_fields(data, required_fields)
        if validation_error:
            return self.error_response(validation_error, 400)

        try:
            course_id = self.schedule_manager.add_custom_course(data)

            # Forcer le rechargement des données
            self.schedule_manager.reload_data()

            # Retourner les détails du cours ajouté
            new_course = next(
                (c for c in self.schedule_manager.custom_courses if c['course_id'] == course_id),
                None
            )

            if new_course:
                return self.success_response(new_course)
            else:
                return self.error_response("Erreur lors de la création du cours", 500)

        except Exception as e:
            return self.error_response(str(e), 500)

    def move_custom_course(self):
        """API pour déplacer un TP personnalisé"""
        data = self.get_json_data()

        required_fields = ['course_id', 'day', 'week_name']
        validation_error = self.validate_required_fields(data, required_fields)
        if validation_error:
            return self.error_response(validation_error, 400)

        try:
            success = self.schedule_manager.move_custom_course(
                data['course_id'],
                data['day'],
                data['week_name']
            )

            if success:
                self.schedule_manager.reload_data()
                return self.success_response()
            else:
                return self.error_response('Le cours à reporter n\'a pas été trouvé', 404)

        except Exception as e:
            return self.error_response(str(e), 500)

    def duplicate_course(self):
        """API pour dupliquer un cours vers plusieurs jours/semaines"""
        data = self.get_json_data()

        required_fields = ['professor', 'course_type', 'raw_time_slot', 'days', 'weeks']
        validation_error = self.validate_required_fields(data, required_fields)
        if validation_error:
            return self.error_response(validation_error, 400)

        try:
            created_count = 0

            for day in data['days']:
                for week in data['weeks']:
                    course_data = {
                        'week_name': week,
                        'day': day,
                        'raw_time_slot': data['raw_time_slot'],
                        'professor': data['professor'],
                        'course_type': data['course_type'],
                        'nb_students': 'N/A'
                    }

                    course_id = self.schedule_manager.add_custom_course(course_data)
                    if course_id:
                        created_count += 1

            return self.success_response({'created_count': created_count})

        except Exception as e:
            return self.error_response(str(e), 500)

    def delete_course(self):
        """API pour supprimer un cours personnalisé"""
        data = self.get_json_data()

        validation_error = self.validate_required_fields(data, ['course_id'])
        if validation_error:
            return self.error_response(validation_error, 400)

        try:
            course_id = data['course_id']

            # Chercher et supprimer le cours
            course_found = False
            for i, course in enumerate(self.schedule_manager.custom_courses):
                if course.get('course_id') == course_id:
                    self.schedule_manager.custom_courses.pop(i)
                    course_found = True
                    break

            if course_found:
                # Supprimer l'attribution de salle si elle existe
                if course_id in self.schedule_manager.room_assignments:
                    del self.schedule_manager.room_assignments[course_id]
                    self.schedule_manager.save_assignments()

                self.schedule_manager.save_custom_courses()
                return self.success_response()
            else:
                return self.error_response('Cours non trouvé', 404)

        except Exception as e:
            return self.error_response(str(e), 500)

    def update_tp_name(self):
        """API pour mettre à jour le nom d'un TP"""
        data = self.get_json_data()

        required_fields = ['course_id', 'tp_name']
        validation_error = self.validate_required_fields(data, required_fields)
        if validation_error:
            return self.error_response(validation_error, 400)

        try:
            success = self.schedule_manager.save_tp_name(data['course_id'], data['tp_name'])

            if success:
                return self.success_response({'tp_name': data['tp_name']})
            else:
                return self.error_response('Erreur lors de la sauvegarde', 500)

        except Exception as e:
            return self.error_response(str(e), 500)

    def get_tp_names(self):
        """API pour récupérer tous les noms de TP"""
        try:
            self.schedule_manager.force_sync_data()
            tp_names = self.schedule_manager.get_all_tp_names()

            response = self.success_response({'tp_names': tp_names})
            # Headers anti-cache
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

        except Exception as e:
            return self.error_response(str(e), 500)

    def delete_tp_name(self):
        """API pour supprimer le nom d'un TP"""
        data = self.get_json_data()
        result = self.course_api_service.delete_tp_name(data)

        status_code = 200
        if 'status_code' in result:
            status_code = result.pop('status_code')

        response = jsonify(result)

        # Ajouter les headers si présents
        if 'headers' in result:
            for key, value in result['headers'].items():
                response.headers[key] = value

        return response, status_code

    def get_courses_clean(self):
        """Clean Architecture - Récupère tous les cours"""
        try:
            week_name = request.args.get('week', 'Semaine 37 B')
            courses = self.clean_course_service.get_courses_by_week(week_name)

            return self.success_response({
                'courses': courses,
                'count': len(courses),
                'architecture': 'Clean Architecture with DDD'
            })

        except Exception as e:
            return self.error_response(str(e), 500)

    def get_courses_by_room_clean(self, room_id):
        """Clean Architecture - Récupère les cours d'une salle"""
        try:
            week_name = request.args.get('week', 'Semaine 37 B')
            courses = self.clean_course_service.get_courses_by_room(room_id, week_name)

            return self.success_response({
                'courses': courses,
                'count': len(courses),
                'room_id': room_id,
                'architecture': 'Clean Architecture with DDD'
            })

        except Exception as e:
            return self.error_response(str(e), 500)