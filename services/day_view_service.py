from typing import Dict, List, Any
from dataclasses import asdict


class DayViewService:
    """Service pour la gestion des vues par jour"""

    def __init__(self, schedule_manager):
        self.schedule_manager = schedule_manager

    def generate_time_grid(self) -> List[Dict]:
        """Génère une grille horaire de 8h à 18h avec créneaux d'1 heure"""
        time_slots = []
        for hour in range(8, 18):
            start_time = f"{hour:02d}:00"
            end_time = f"{hour+1:02d}:00"
            time_slots.append({
                'start_time': start_time,
                'end_time': end_time,
                'label': f"{hour}h-{hour+1}h"
            })
        return time_slots

    def get_day_courses(self, week_name: str, day_name: str) -> List[Dict]:
        """Récupère tous les cours pour une semaine et un jour donnés"""
        all_courses_obj = self.schedule_manager.get_all_courses()
        day_courses = []

        for course in all_courses_obj:
            if course.week_name == week_name and course.day == day_name:
                course_dict = asdict(course)
                course_dict['room_name'] = self.schedule_manager.get_room_name(course.assigned_room) if course.assigned_room else "Non assignée"
                course_dict['prof_color'] = self.schedule_manager.get_prof_color(course.professor)
                day_courses.append(course_dict)

        return day_courses

    def build_day_grid(self, time_slots: List[Dict], day_courses: List[Dict]) -> Dict:
        """Construit la grille pour un jour spécifique"""
        day_grid = {}
        for time_slot in time_slots:
            day_grid[time_slot['label']] = {
                'time_info': time_slot,
                'courses': []
            }

        # Placer les cours dans la grille
        for course in day_courses:
            course_start = course.get('start_time', '')

            # Trouver le créneau correspondant
            for time_slot in time_slots:
                slot_start = time_slot['start_time']
                slot_end = time_slot['end_time']

                # Vérifier si le cours commence dans ce créneau
                if course_start >= slot_start and course_start < slot_end:
                    day_grid[time_slot['label']]['courses'].append(course)
                    break

        return day_grid

    def generate_day_view_data(self, week_name: str, day_name: str) -> Dict[str, Any]:
        """Génère toutes les données nécessaires pour l'affichage d'un jour"""
        # Générer la grille horaire
        time_slots = self.generate_time_grid()

        # Récupérer les cours du jour
        day_courses = self.get_day_courses(week_name, day_name)

        # Construire la grille
        day_grid = self.build_day_grid(time_slots, day_courses)

        return {
            'day_grid': day_grid,
            'time_slots': time_slots,
            'day_name': day_name,
            'week_name': week_name,
            'rooms': self.schedule_manager.rooms,
            'get_room_name': self.schedule_manager.get_room_name
        }