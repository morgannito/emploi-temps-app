import json
import os
from typing import Dict, List, Optional
from .week_service import WeekService
from .timeslot_service import TimeSlotService


class PlanningService:
    """Service pour la gestion des plannings et vues readonly"""

    @staticmethod
    def get_available_weeks(all_courses) -> List[str]:
        """Récupère toutes les semaines disponibles depuis les cours"""
        return sorted(set([c.week_name for c in all_courses]))

    @staticmethod
    def determine_current_week(available_weeks: List[str]) -> str:
        """Détermine la semaine courante ou prend la première disponible"""
        if not available_weeks:
            return "Semaine 37 B"

        weeks_to_display = WeekService.generate_academic_calendar()
        current_week = WeekService.get_current_week_name(weeks_to_display)

        # Vérifier si la semaine calculée existe dans les données
        if current_week in available_weeks:
            return current_week
        else:
            # Si la semaine calculée n'existe pas, prendre la première disponible
            return available_weeks[0]

    @staticmethod
    def organize_courses_by_day_time(week_courses) -> Dict[str, object]:
        """Organise les cours par jour et heure pour l'affichage"""
        courses_by_day_time = {}
        for course in week_courses:
            key = f"{course.day}_{course.start_time}"
            courses_by_day_time[key] = course
        return courses_by_day_time

    @staticmethod
    def load_room_mapping() -> Dict[str, str]:
        """Charge le mapping des IDs de salles vers leurs noms"""
        room_mapping = {}
        try:
            salle_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'salle.json')
            with open(salle_path, 'r', encoding='utf-8') as f:
                salle_data = json.load(f)
                rooms_data = salle_data.get('rooms', [])
                # Créer le mapping ID -> Nom
                for room in rooms_data:
                    room_mapping[room['_id']] = room['name']
        except FileNotFoundError:
            pass
        return room_mapping

    @staticmethod
    def convert_room_ids_to_names(week_courses, room_mapping: Dict[str, str]):
        """Convertit les IDs de salles en noms pour chaque cours"""
        for course in week_courses:
            if course.assigned_room:
                # Remplacer l'ID par le nom de la salle
                course.assigned_room = room_mapping.get(course.assigned_room, f"Salle {course.assigned_room}")

    @staticmethod
    def get_planning_data(schedule_manager, week_name: Optional[str] = None) -> Dict:
        """Récupère toutes les données nécessaires pour afficher un planning"""
        # Forcer la synchronisation des données
        schedule_manager.force_sync_data()

        # Récupérer tous les cours et semaines disponibles
        all_courses = schedule_manager.get_all_courses()
        available_weeks = PlanningService.get_available_weeks(all_courses)

        # Déterminer la semaine à afficher
        if not week_name:
            week_name = PlanningService.determine_current_week(available_weeks)

        # Récupérer les informations de la semaine
        academic_calendar = WeekService.generate_academic_calendar()
        current_week_info = WeekService.find_week_info(week_name, academic_calendar)

        # Filtrer les cours pour la semaine sélectionnée
        week_courses = [c for c in all_courses if c.week_name == week_name]

        # Organiser les cours
        courses_by_day_time = PlanningService.organize_courses_by_day_time(week_courses)

        # Créer la structure des créneaux et jours
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        time_slots = [f"{hour}h-{hour+1}h" for hour in range(8, 18)]

        # Charger les données des salles
        room_mapping = PlanningService.load_room_mapping()

        # Convertir les IDs de salles en noms
        PlanningService.convert_room_ids_to_names(week_courses, room_mapping)

        return {
            'week_name': week_name,
            'weeks_to_display': academic_calendar,
            'current_week_info': current_week_info,
            'courses': week_courses,
            'courses_by_day_time': courses_by_day_time,
            'days': days,
            'time_slots': time_slots,
            'all_weeks': academic_calendar
        }