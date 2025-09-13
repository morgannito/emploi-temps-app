import json
import os
from typing import Dict, List, Any


class ProfessorViewService:
    """Service pour la gestion des vues individuelles des professeurs"""

    def __init__(self, schedule_manager):
        self.schedule_manager = schedule_manager

    def load_room_mapping(self) -> Dict[str, str]:
        """Charge le mapping des salles depuis le cache si disponible"""
        if hasattr(self.schedule_manager, 'perf_cache'):
            return self.schedule_manager.perf_cache.get_cached_room_mapping()

        # Fallback pour compatibilité
        room_mapping = {}
        try:
            salle_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'salle.json')
            with open(salle_path, 'r', encoding='utf-8') as f:
                salle_data = json.load(f)
                for room in salle_data.get('rooms', []):
                    room_mapping[room['_id']] = room['name']
        except FileNotFoundError:
            pass
        return room_mapping

    def find_professor_name(self, prof_name: str) -> str:
        """Recherche intelligente du nom du professeur avec cache"""
        if hasattr(self.schedule_manager, 'perf_cache'):
            all_courses = self.schedule_manager.perf_cache.get_cached_courses(self.schedule_manager)
        else:
            all_courses = self.schedule_manager.get_all_courses()

        all_profs = set([c.professor for c in all_courses])

        # Essayer d'abord le nom exact
        if prof_name in all_profs:
            return prof_name

        # Rechercher un nom qui contient le terme recherché
        matches = [p for p in all_profs if prof_name.lower() in p.lower()]
        if matches:
            return matches[0]  # Prendre le premier match

        # Rechercher dans l'autre sens (terme recherché contient un nom de prof)
        reverse_matches = [p for p in all_profs if p.lower() in prof_name.lower()]
        if reverse_matches:
            return reverse_matches[0]

        return prof_name  # Garder l'original si aucun match

    def get_available_weeks(self) -> List[Dict[str, str]]:
        """Récupère toutes les semaines disponibles avec cache"""
        if hasattr(self.schedule_manager, 'perf_cache'):
            return self.schedule_manager.perf_cache.get_cached_available_weeks(self.schedule_manager)

        # Fallback
        all_courses = self.schedule_manager.get_all_courses()
        available_weeks = sorted(set([c.week_name for c in all_courses]))

        weeks_list = []
        for week_name in available_weeks:
            weeks_list.append({
                'name': week_name,
                'date': None,  # Pas de date spécifique
                'full_name': week_name
            })
        return weeks_list

    def get_professor_courses(self, prof_name: str, weeks_list: List[Dict]) -> Dict[str, List]:
        """Récupère tous les cours d'un professeur pour toutes les semaines avec cache"""
        if hasattr(self.schedule_manager, 'perf_cache'):
            all_courses = self.schedule_manager.perf_cache.get_cached_courses(self.schedule_manager)
        else:
            all_courses = self.schedule_manager.get_all_courses()

        room_mapping = self.load_room_mapping()
        professor_courses = {}

        for week in weeks_list:
            week_name = week['name']
            week_courses = []

            for course in all_courses:
                if course.professor == prof_name and course.week_name == week_name:
                    # Convertir l'ID de salle en nom de salle
                    room_name = "Non attribuée"
                    if course.assigned_room:
                        room_name = room_mapping.get(course.assigned_room, f"Salle {course.assigned_room}")

                    week_courses.append({
                        'day': course.day,
                        'start_time': course.start_time,
                        'end_time': course.end_time,
                        'subject': course.course_type,
                        'room': room_name,
                        'tp_name': getattr(course, 'tp_name', course.course_type)
                    })

            if week_courses:
                # Trier par jour et heure
                days_order = {'Lundi': 0, 'Mardi': 1, 'Mercredi': 2, 'Jeudi': 3, 'Vendredi': 4}
                week_courses.sort(key=lambda x: (days_order.get(x['day'], 5), x['start_time']))
                professor_courses[week_name] = week_courses

        return professor_courses

    def generate_professor_schedule_data(self, prof_name: str) -> Dict[str, Any]:
        """Génère toutes les données nécessaires pour l'affichage du planning d'un professeur"""
        # Recherche intelligente du nom du professeur
        final_prof_name = self.find_professor_name(prof_name)

        # Récupérer les semaines disponibles
        weeks_list = self.get_available_weeks()

        # Récupérer les cours du professeur
        professor_courses = self.get_professor_courses(final_prof_name, weeks_list)

        return {
            'professor_name': final_prof_name,
            'professor_courses': professor_courses,
            'weeks_list': weeks_list
        }