import pytz
from datetime import datetime
from dataclasses import asdict
from typing import Dict, List, Optional
from .week_service import WeekService
from .timeslot_service import TimeSlotService


class KiosqueService:
    """Service pour la gestion des vues kiosque"""

    @staticmethod
    def get_current_week_name() -> str:
        """Détermine le nom de la semaine actuelle pour le kiosque"""
        today = datetime.now().date()
        week_num = today.isocalendar()[1]
        if today.year == 2025 and week_num >= 36:
            weeks_since_start = week_num - 36
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            return f"Semaine {week_num} {week_type}"
        return "Semaine 37 A"  # Fallback

    @staticmethod
    def build_week_grid(week_courses, time_slots, schedule_manager) -> Dict:
        """Construit la grille de cours pour une semaine complète"""
        days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        week_grid = {}

        for day in days_order:
            week_grid[day] = {}
            for slot in time_slots:
                week_grid[day][slot['label']] = {
                    'time_info': slot,
                    'courses': []
                }

        # Placer les cours dans la grille
        for course in week_courses:
            day = course.day
            if day in week_grid:
                # Trouver le créneau correspondant
                for slot in time_slots:
                    if course.start_time >= slot['start_time'] and course.start_time < slot['end_time']:
                        course_dict = asdict(course)
                        course_dict['room_name'] = schedule_manager.get_room_name(course.assigned_room)
                        course_dict['prof_color'] = schedule_manager.get_prof_color(course.professor)
                        week_grid[day][slot['label']]['courses'].append(course_dict)
                        break

        return week_grid

    @staticmethod
    def group_courses_by_room(week_courses, schedule_manager) -> Dict:
        """Groupe les cours par salle avec taux d'occupation"""
        rooms_data = {}

        for course in week_courses:
            room_name = schedule_manager.get_room_name(course.assigned_room)
            if room_name not in rooms_data:
                rooms_data[room_name] = {
                    'room_id': course.assigned_room,
                    'courses': [],
                    'occupancy_rate': 0
                }
            rooms_data[room_name]['courses'].append(asdict(course))

        # Calculer taux d'occupation (35 créneaux par semaine max)
        for room_data in rooms_data.values():
            room_data['occupancy_rate'] = min(100, len(room_data['courses']) * 100 // 35)

        return rooms_data

    @staticmethod
    def get_period_info(now: datetime) -> Dict:
        """Détermine la période actuelle et les créneaux associés"""
        current_hour = now.hour

        if current_hour < 12:
            return {
                'period': 'morning',
                'period_label': 'Matinée',
                'time_range': '8h - 12h',
                'time_slots': [
                    {'start_time': '08:00', 'end_time': '09:00', 'label': '8h-9h'},
                    {'start_time': '09:00', 'end_time': '10:00', 'label': '9h-10h'},
                    {'start_time': '10:15', 'end_time': '11:15', 'label': '10h15-11h15'},
                    {'start_time': '11:15', 'end_time': '12:15', 'label': '11h15-12h15'},
                ]
            }
        else:
            return {
                'period': 'afternoon',
                'period_label': 'Après-midi',
                'time_range': '13h - 17h',
                'time_slots': [
                    {'start_time': '13:30', 'end_time': '14:30', 'label': '13h30-14h30'},
                    {'start_time': '14:30', 'end_time': '15:30', 'label': '14h30-15h30'},
                    {'start_time': '15:45', 'end_time': '16:45', 'label': '15h45-16h45'},
                    {'start_time': '16:45', 'end_time': '17:45', 'label': '16h45-17h45'},
                ]
            }

    @staticmethod
    def filter_courses_by_period(day_courses, period: str) -> List:
        """Filtre les cours selon la période avec logique inclusive"""
        period_courses = []

        for course in day_courses:
            course_hour = int(course.start_time.split(':')[0])
            if period == "morning" and course_hour < 13:  # Élargi pour inclure 12h
                period_courses.append(course)
            elif period == "afternoon" and course_hour >= 12:  # Commence à 12h
                period_courses.append(course)

        return period_courses

    @staticmethod
    def sort_courses_by_time_and_professor(courses) -> List:
        """Trie les cours par horaire puis par ordre alphabétique des professeurs"""
        def sort_key(course):
            prof_name = course.professor
            # Enlever "M " ou "Mme " pour le tri alphabétique
            if prof_name.startswith('M '):
                prof_name = prof_name[2:]
            elif prof_name.startswith('Mme '):
                prof_name = prof_name[4:]
            return (course.start_time, prof_name.lower())

        return sorted(courses, key=sort_key)

    @staticmethod
    def get_current_french_day() -> str:
        """Retourne le jour actuel en français"""
        import locale
        now = datetime.now(pytz.timezone("Europe/Paris"))
        locale.setlocale(locale.LC_TIME, "C")
        current_day = now.strftime("%A")
        locale.setlocale(locale.LC_TIME, "")

        day_translation = {
            'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi', 'Friday': 'Vendredi'
        }
        return day_translation.get(current_day, 'Lundi')

    @staticmethod
    def separate_current_and_upcoming_courses(today_courses, current_time: str) -> tuple:
        """Sépare les cours en cours et à venir"""
        current_courses = []
        upcoming_courses = []

        for course in today_courses:
            if course.start_time <= current_time <= course.end_time:
                current_courses.append(course)
            elif course.start_time > current_time:
                upcoming_courses.append(course)

        upcoming_courses.sort(key=lambda c: c.start_time)
        return current_courses, upcoming_courses

    @staticmethod
    def get_kiosque_week_data(schedule_manager, week_name: Optional[str] = None) -> Dict:
        """Récupère toutes les données pour la vue kiosque semaine"""
        if week_name is None:
            week_name = KiosqueService.get_current_week_name()

        # Récupérer tous les cours de la semaine
        all_courses = schedule_manager.get_all_courses()
        week_courses = [c for c in all_courses if c.week_name == week_name and c.assigned_room]

        # Organiser par jour
        days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        time_slots = TimeSlotService.generate_time_grid()

        week_grid = KiosqueService.build_week_grid(week_courses, time_slots, schedule_manager)

        return {
            'week_grid': week_grid,
            'time_slots': time_slots,
            'days_order': days_order,
            'current_week': week_name,
            'total_courses': len(week_courses)
        }

    @staticmethod
    def get_kiosque_room_data(schedule_manager, room_id: Optional[str] = None) -> Dict:
        """Récupère toutes les données pour la vue kiosque salle"""
        current_week = KiosqueService.get_current_week_name()

        all_courses = schedule_manager.get_all_courses()
        week_courses = [c for c in all_courses if c.week_name == current_week and c.assigned_room]

        # Si room_id spécifié, filtrer
        if room_id:
            week_courses = [c for c in week_courses if c.assigned_room == room_id]

        rooms_data = KiosqueService.group_courses_by_room(week_courses, schedule_manager)

        return {
            'rooms_data': rooms_data,
            'current_week': current_week,
            'focused_room': room_id
        }

    @staticmethod
    def get_tv_schedule_data(schedule_manager) -> Dict:
        """Récupère toutes les données pour l'affichage TV"""
        now = datetime.now(pytz.timezone("Europe/Paris"))
        current_time = now.strftime('%H:%M')
        current_day_fr = KiosqueService.get_current_french_day()
        current_week = KiosqueService.get_current_week_name()

        all_courses = schedule_manager.get_all_courses()
        today_courses = [c for c in all_courses
                        if c.week_name == current_week
                        and c.day == current_day_fr
                        and c.assigned_room]

        current_courses, upcoming_courses = KiosqueService.separate_current_and_upcoming_courses(
            today_courses, current_time
        )

        return {
            'current_courses': current_courses,
            'upcoming_courses': upcoming_courses[:8],
            'current_week': current_week,
            'current_day': current_day_fr,
            'current_time': current_time
        }

    @staticmethod
    def create_dynamic_time_slots(period_courses, schedule_manager):
        """Créer des créneaux dynamiques basés sur les horaires réels des cours"""
        from .timeslot_service import TimeSlotService
        actual_time_slots = {}

        # Grouper les cours par horaire de début
        for course in period_courses:
            start_time = course.start_time
            end_time = course.end_time

            # Créer un label pour ce créneau
            hour_start = int(start_time.split(':')[0])
            min_start = int(start_time.split(':')[1]) if ':' in start_time else 0
            hour_end = int(end_time.split(':')[0]) if end_time else hour_start + 1
            min_end = int(end_time.split(':')[1]) if ':' in end_time and end_time else 0

            # Format du label (ex: "8h-9h", "10h15-11h15")
            if min_start == 0 and min_end == 0:
                label = f"{hour_start}h-{hour_end}h"
            elif min_start == 0:
                label = f"{hour_start}h-{hour_end}h{min_end:02d}"
            elif min_end == 0:
                label = f"{hour_start}h{min_start:02d}-{hour_end}h"
            else:
                label = f"{hour_start}h{min_start:02d}-{hour_end}h{min_end:02d}"

            # Grouper les cours qui ont exactement le même horaire
            time_key = f"{start_time}-{end_time}"

            if time_key not in actual_time_slots:
                actual_time_slots[time_key] = {
                    'time_info': {
                        'start_time': start_time,
                        'end_time': end_time,
                        'label': label
                    },
                    'courses': [],
                    'sort_key': start_time
                }

            course_dict = asdict(course)
            course_dict['prof_color'] = schedule_manager.get_prof_color(course.professor)
            course_dict['room_name'] = schedule_manager.get_room_name(course.assigned_room)
            actual_time_slots[time_key]['courses'].append(course_dict)

        # Trier les créneaux par horaire et les cours par prof
        filtered_time_slots = []
        filtered_time_slots_data = {}

        # Trier les créneaux par horaire de début puis par horaire de fin
        def sort_time_slots(item):
            from .timeslot_service import TimeSlotService
            time_key, slot_data = item
            start_time = slot_data['sort_key']
            end_time = slot_data['time_info']['end_time']

            # Convertir en minutes pour tri précis
            start_minutes = TimeSlotService.time_to_minutes(start_time)
            end_minutes = TimeSlotService.time_to_minutes(end_time)

            # Trier d'abord par heure de début, puis par heure de fin
            return (start_minutes, end_minutes)

        sorted_slots = sorted(actual_time_slots.items(), key=sort_time_slots)

        for time_key, slot_data in sorted_slots:
            # Trier les cours du créneau par ordre alphabétique de prof
            slot_data['courses'].sort(key=lambda c: c['professor'].replace('M ', '').replace('Mme ', '').lower())

            filtered_time_slots.append(slot_data['time_info'])
            filtered_time_slots_data[slot_data['time_info']['label']] = slot_data

        return filtered_time_slots, filtered_time_slots_data

    @staticmethod
    def get_template_for_layout(layout: str) -> str:
        """Retourne le template approprié selon le layout"""
        template_map = {
            "standard": "kiosque_halfday.html",
            "compact": "kiosque_halfday_compact.html",
            "wide": "kiosque_halfday_wide.html",
            "ipad": "kiosque_halfday_compact.html",
            "grid4": "kiosque_halfday_grid4.html",
            "compactv1": "kiosque_halfday_compactv1.html",
            "compactv2": "kiosque_halfday_compactv2.html",
            "compactv3": "kiosque_halfday_compactv3.html",
            "compactv4": "kiosque_halfday_compactv4.html",
            "compactv5": "kiosque_halfday_compactv5.html",
            "compactv6": "kiosque_halfday_compactv6.html",
            "compactv7": "kiosque_halfday_compactv7.html",
            "compactv8": "kiosque_halfday_compactv8.html",
            "compactv9": "kiosque_halfday_compactv9.html",
            "compactv10": "kiosque_halfday_compactv10.html",
            "compactv11": "kiosque_halfday_compactv11.html"
        }
        return template_map.get(layout, "kiosque_halfday.html")

    @staticmethod
    def get_kiosque_halfday_data(schedule_manager, layout: str = "standard") -> Dict:
        """Récupère toutes les données pour la vue kiosque demi-journée"""
        now = datetime.now(pytz.timezone("Europe/Paris"))
        current_day_fr = KiosqueService.get_current_french_day()
        current_week = KiosqueService.get_current_week_name()

        # Détection automatique période
        period_info = KiosqueService.get_period_info(now)

        # Récupérer tous les cours du jour actuel
        all_courses = schedule_manager.get_all_courses()
        day_courses = [c for c in all_courses
                       if c.week_name == current_week
                       and c.day == current_day_fr
                       and c.assigned_room]

        # Filtrer par période
        period_courses = KiosqueService.filter_courses_by_period(day_courses, period_info['period'])
        period_courses = KiosqueService.sort_courses_by_time_and_professor(period_courses)

        # Créer des créneaux dynamiques
        filtered_time_slots, filtered_time_slots_data = KiosqueService.create_dynamic_time_slots(
            period_courses, schedule_manager
        )

        # Déterminer le template selon le layout
        template_name = KiosqueService.get_template_for_layout(layout)

        return {
            'time_slots_data': filtered_time_slots_data,
            'time_slots': filtered_time_slots,
            'current_week': current_week,
            'current_day': current_day_fr,
            'period': period_info['period'],
            'period_label': period_info['period_label'],
            'time_range': period_info['time_range'],
            'total_courses': len(period_courses),
            'current_time': now.strftime('%H:%M'),
            'layout': layout,
            'template_name': template_name
        }