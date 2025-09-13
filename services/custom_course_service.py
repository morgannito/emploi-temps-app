import hashlib
import time
from typing import Dict, List, Any


class CustomCourseService:
    """Service pour la gestion des cours personnalisés"""

    def __init__(self, file_service):
        """
        Initialise le service avec une référence au FileManagementService

        Args:
            file_service: Instance de FileManagementService
        """
        self.file_service = file_service

    def add_custom_course(self, course_data: Dict) -> str:
        """Ajoute un cours personnalisé et retourne son ID"""
        course_id = f"custom_{int(time.time() * 1000)}"
        course_data['course_id'] = course_id

        if 'nb_students' not in course_data:
            course_data['nb_students'] = 'N/A'

        if 'raw_time_slot' not in course_data or not course_data['raw_time_slot']:
            course_data['raw_time_slot'] = f"{course_data.get('start_time', '00:00')}-{course_data.get('end_time', '00:00')}"

        if not course_data.get('start_time') or not course_data.get('end_time'):
            course_data['start_time'], course_data['end_time'], course_data['duration_hours'] = "00:00", "00:00", 0

        custom_courses = self.file_service.load_custom_courses()
        custom_courses.append(course_data)
        self.file_service.save_custom_courses(custom_courses)

        return course_id

    def move_custom_course(self, course_id: str, new_day: str, new_week: str) -> bool:
        """Déplace un cours personnalisé vers un autre jour/semaine"""
        custom_courses = self.file_service.load_custom_courses()
        course_found = False

        for course in custom_courses:
            if course.get('course_id') == course_id:
                course['day'] = new_day
                course['week_name'] = new_week
                course_found = True
                break

        if course_found:
            self.file_service.save_custom_courses(custom_courses)
            return True
        return False

    def delete_custom_course(self, course_id: str) -> bool:
        """Supprime un cours personnalisé"""
        custom_courses = self.file_service.load_custom_courses()
        course_found = False

        for i, course in enumerate(custom_courses):
            if course.get('course_id') == course_id:
                custom_courses.pop(i)
                course_found = True
                break

        if course_found:
            self.file_service.save_custom_courses(custom_courses)
            return True
        return False

    def get_custom_courses(self) -> List[Dict]:
        """Récupère tous les cours personnalisés"""
        return self.file_service.load_custom_courses()

    def get_custom_course_by_id(self, course_id: str) -> Dict:
        """Récupère un cours personnalisé par son ID"""
        custom_courses = self.file_service.load_custom_courses()
        for course in custom_courses:
            if course.get('course_id') == course_id:
                return course
        return None

    def filter_custom_courses_by_week(self, week_name: str) -> List[Dict]:
        """Filtre les cours personnalisés par semaine"""
        custom_courses = self.file_service.load_custom_courses()
        return [course for course in custom_courses if course.get('week_name') == week_name]

    def filter_custom_courses_by_professor(self, professor: str) -> List[Dict]:
        """Filtre les cours personnalisés par professeur"""
        custom_courses = self.file_service.load_custom_courses()
        return [course for course in custom_courses if course.get('professor') == professor]

    def update_custom_course(self, course_id: str, updated_data: Dict) -> bool:
        """Met à jour un cours personnalisé"""
        custom_courses = self.file_service.load_custom_courses()
        course_found = False

        for course in custom_courses:
            if course.get('course_id') == course_id:
                course.update(updated_data)
                course_found = True
                break

        if course_found:
            self.file_service.save_custom_courses(custom_courses)
            return True
        return False

    def save_tp_name(self, course_id: str, tp_name: str) -> bool:
        """Met à jour le nom d'un TP personnalisé"""
        return self.update_custom_course(course_id, {'tp_name': tp_name})

    @staticmethod
    def separate_original_and_custom_courses(courses: List[Dict]) -> tuple:
        """Sépare les cours originaux et personnalisés"""
        original_courses = [c for c in courses if not c['course_id'].startswith('custom_')]
        custom_courses = [c for c in courses if c['course_id'].startswith('custom_')]
        return original_courses, custom_courses

    def create_bulk_custom_courses(self, courses_data: List[Dict]) -> List[str]:
        """Crée plusieurs cours personnalisés en une fois"""
        created_ids = []
        custom_courses = self.file_service.load_custom_courses()

        for course_data in courses_data:
            course_id = f"custom_{int(time.time() * 1000)}_{len(created_ids)}"
            course_data['course_id'] = course_id

            if 'nb_students' not in course_data:
                course_data['nb_students'] = 'N/A'

            if 'raw_time_slot' not in course_data or not course_data['raw_time_slot']:
                course_data['raw_time_slot'] = f"{course_data.get('start_time', '00:00')}-{course_data.get('end_time', '00:00')}"

            custom_courses.append(course_data)
            created_ids.append(course_id)

        self.file_service.save_custom_courses(custom_courses)
        return created_ids