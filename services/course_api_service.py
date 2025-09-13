import time
from typing import Dict, List, Any
from flask import jsonify, request


class CourseAPIService:
    """Service pour les APIs de gestion des cours"""

    def __init__(self, schedule_manager):
        self.schedule_manager = schedule_manager

    def add_custom_course(self, data: Dict) -> Dict:
        """API pour ajouter un TP personnalisé"""
        required_fields = ['week_name', 'day', 'raw_time_slot', 'professor', 'course_type']
        if not all(field in data for field in required_fields):
            return {'success': False, 'error': 'Données manquantes.', 'status_code': 400}

        course_id = self.schedule_manager.add_custom_course(data)

        # Forcer le rechargement des données pour tous les workers
        self.schedule_manager.reload_data()

        # Retourner les détails du cours ajouté pour l'afficher dynamiquement
        new_course = next((c for c in self.schedule_manager.custom_courses if c['course_id'] == course_id), None)

        if new_course:
            return {'success': True, 'course': new_course}
        else:
            return {'success': False, 'error': "Erreur lors de la création du cours.", 'status_code': 500}

    def move_custom_course(self, data: Dict) -> Dict:
        """API pour déplacer un TP personnalisé"""
        course_id = data.get('course_id')
        new_day = data.get('day')
        new_week = data.get('week_name')

        if not all([course_id, new_day, new_week]):
            return {'success': False, 'error': 'Données manquantes pour le report.', 'status_code': 400}

        success = self.schedule_manager.move_custom_course(course_id, new_day, new_week)

        if success:
            # Forcer le rechargement des données pour tous les workers
            self.schedule_manager.reload_data()
            return {'success': True}
        else:
            return {'success': False, 'error': 'Le cours à reporter n\'a pas été trouvé.', 'status_code': 404}

    def duplicate_course(self, data: Dict) -> Dict:
        """API pour dupliquer un cours vers plusieurs jours/semaines"""
        try:
            professor = data.get('professor')
            course_type = data.get('course_type')
            raw_time_slot = data.get('raw_time_slot')
            days = data.get('days', [])
            weeks = data.get('weeks', [])

            if not all([professor, course_type, raw_time_slot, days, weeks]):
                return {'success': False, 'error': 'Données manquantes.', 'status_code': 400}

            created_count = 0

            # Dupliquer vers chaque combinaison jour/semaine
            for day in days:
                for week in weeks:
                    course_data = {
                        'week_name': week,
                        'day': day,
                        'raw_time_slot': raw_time_slot,
                        'professor': professor,
                        'course_type': course_type,
                        'nb_students': 'N/A'
                    }

                    course_id = self.schedule_manager.add_custom_course(course_data)
                    if course_id:
                        created_count += 1

            return {'success': True, 'created_count': created_count}

        except Exception as e:
            return {'success': False, 'error': str(e), 'status_code': 500}

    def delete_course(self, data: Dict) -> Dict:
        """API pour supprimer un cours personnalisé"""
        try:
            course_id = data.get('course_id')

            if not course_id:
                return {'success': False, 'error': 'ID du cours manquant.', 'status_code': 400}

            # Chercher et supprimer le cours dans la liste des cours personnalisés
            course_found = False
            for i, course in enumerate(self.schedule_manager.custom_courses):
                if course.get('course_id') == course_id:
                    self.schedule_manager.custom_courses.pop(i)
                    course_found = True
                    break

            if course_found:
                # Supprimer aussi l'attribution de salle si elle existe
                if course_id in self.schedule_manager.room_assignments:
                    del self.schedule_manager.room_assignments[course_id]
                    self.schedule_manager.save_assignments()

                # Sauvegarder les cours personnalisés
                self.schedule_manager.save_custom_courses()
                return {'success': True}
            else:
                return {'success': False, 'error': 'Cours non trouvé.', 'status_code': 404}

        except Exception as e:
            return {'success': False, 'error': str(e), 'status_code': 500}

    def update_tp_name(self, data: Dict) -> Dict:
        """API pour mettre à jour le nom d'un TP sur un cours existant"""
        try:
            course_id = data.get('course_id')
            tp_name = data.get('tp_name')

            if not course_id or not tp_name:
                return {'success': False, 'error': 'ID du cours et nom du TP requis.', 'status_code': 400}

            # Sauvegarder le nom du TP dans un fichier dédié
            success = self.schedule_manager.save_tp_name(course_id, tp_name)

            if success:
                return {'success': True, 'tp_name': tp_name}
            else:
                return {'success': False, 'error': 'Erreur lors de la sauvegarde.', 'status_code': 500}

        except Exception as e:
            return {'success': False, 'error': str(e), 'status_code': 500}

    def get_tp_names(self) -> Dict:
        """API pour récupérer tous les noms de TP sauvegardés"""
        try:
            # Forcer la synchronisation des données avant de récupérer
            self.schedule_manager.force_sync_data()
            tp_names = self.schedule_manager.get_all_tp_names()

            return {
                'success': True,
                'tp_names': tp_names,
                'headers': {
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            }
        except Exception as e:
            print(f"Erreur lors de la récupération des noms de TP: {e}")
            return {'success': False, 'error': str(e), 'status_code': 500}

    def delete_tp_name(self, data: Dict) -> Dict:
        """API pour supprimer le nom d'un TP d'un cours"""
        try:
            course_id = data.get('course_id')

            if not course_id:
                return {'success': False, 'error': 'ID du cours requis.', 'status_code': 400}

            print(f"Suppression du TP pour le cours {course_id}")

            # Supprimer le nom du TP
            success = self.schedule_manager.delete_tp_name(course_id)

            if success:
                print(f"TP supprimé avec succès pour le cours {course_id}")
                # Forcer la synchronisation des données
                self.schedule_manager.force_sync_data()

                return {
                    'success': True,
                    'message': 'TP supprimé avec succès',
                    'headers': {
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    }
                }
            else:
                print(f"Erreur lors de la suppression du TP pour le cours {course_id}")
                return {'success': False, 'error': 'Erreur lors de la suppression.', 'status_code': 500}

        except Exception as e:
            return {'success': False, 'error': str(e), 'status_code': 500}