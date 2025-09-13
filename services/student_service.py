import pytz
from datetime import datetime
from dataclasses import asdict
from .week_service import WeekService
from .timeslot_service import TimeSlotService
from .course_grid_service import CourseGridService


class StudentService:
    """Service pour la gestion des vues étudiants et kiosque"""

    @staticmethod
    def get_current_period_strict(now: datetime) -> str:
        """Détermine la période basée sur l'heure (strict: 12h05 comme limite)"""
        if now.hour < 12 or (now.hour == 12 and now.minute < 5):
            return "morning"
        return "afternoon"

    @staticmethod
    def get_current_period_standard(now: datetime) -> str:
        """Détermine la période basée sur l'heure (standard: 12h30 comme limite)"""
        if now.hour < 12 or (now.hour == 12 and now.minute < 30):
            return "morning"
        else:
            return "afternoon"

    @staticmethod
    def is_morning_slot(slot: dict) -> bool:
        """Vérifie si un créneau est le matin"""
        return slot['start_time'] < '12:00'

    @staticmethod
    def is_afternoon_slot(slot: dict) -> bool:
        """Vérifie si un créneau est l'après-midi"""
        return slot['start_time'] >= '12:00'

    @staticmethod
    def get_french_day_name(now: datetime, forced_day: str = None) -> str:
        """Retourne le nom du jour en français"""
        if forced_day and forced_day in ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']:
            return forced_day

        day_mapping = {
            0: 'Lundi',    # Monday
            1: 'Mardi',    # Tuesday
            2: 'Mercredi', # Wednesday
            3: 'Jeudi',    # Thursday
            4: 'Vendredi', # Friday
            5: 'Samedi',   # Saturday
            6: 'Dimanche'  # Sunday
        }
        return day_mapping.get(now.weekday(), 'Lundi')

    @staticmethod
    def build_student_grid(courses_for_display, time_slots, current_day_fr, schedule_manager):
        """Construit la grille étudiante avec les cours placés"""
        # Initialiser la grille
        student_grid = {current_day_fr: {}}
        for time_slot in time_slots:
            student_grid[current_day_fr][time_slot['label']] = {
                'time_info': time_slot,
                'courses': []
            }

        # Placer chaque cours dans la grille
        for course in courses_for_display:
            course_start = course.start_time
            course_placed = False

            # Essayer de placer le cours dans un créneau exact
            for time_slot in time_slots:
                slot_start = TimeSlotService.time_to_minutes(time_slot['start_time'])
                slot_end = TimeSlotService.time_to_minutes(time_slot['end_time'])
                course_start_min = TimeSlotService.time_to_minutes(course_start)

                # Vérifier si le cours commence dans ce créneau
                if course_start_min >= slot_start and course_start_min < slot_end:
                    course_dict = asdict(course)
                    course_dict['room_name'] = schedule_manager.get_room_name(course.assigned_room)
                    course_dict['prof_color'] = schedule_manager.get_prof_color(course.professor)

                    student_grid[current_day_fr][time_slot['label']]['courses'].append(course_dict)
                    course_placed = True
                    break

            # Si le cours n'a pas été placé, essayer avec une logique plus souple
            if not course_placed:
                course_minutes = TimeSlotService.time_to_minutes(course_start)
                best_slot = None
                min_diff = float('inf')

                # Trouver le créneau le plus proche
                for time_slot in time_slots:
                    slot_minutes = TimeSlotService.time_to_minutes(time_slot['start_time'])
                    diff = abs(course_minutes - slot_minutes)

                    if diff < min_diff:
                        min_diff = diff
                        best_slot = time_slot

                # Placer dans le créneau le plus proche si raisonnable (< 60 minutes)
                if best_slot and min_diff < 60:
                    course_dict = asdict(course)
                    course_dict['room_name'] = schedule_manager.get_room_name(course.assigned_room)
                    course_dict['prof_color'] = schedule_manager.get_prof_color(course.professor)

                    student_grid[current_day_fr][best_slot['label']]['courses'].append(course_dict)

        return student_grid

    @staticmethod
    def filter_time_slots_by_period(time_slots, period: str):
        """Filtre les créneaux selon la période (morning/afternoon/full_day)"""
        if period == 'morning':
            return [s for s in time_slots if StudentService.is_morning_slot(s)]
        elif period == 'afternoon':
            return [s for s in time_slots if StudentService.is_afternoon_slot(s)]
        else:  # 'full_day'
            return time_slots

    @staticmethod
    def filter_empty_slots(period_slots, student_grid, current_day_fr):
        """Masque les créneaux sans cours"""
        filtered_time_slots = []
        for s in period_slots:
            label = s['label']
            slot_courses = student_grid[current_day_fr][label]['courses']
            if slot_courses:
                filtered_time_slots.append(s)
        return filtered_time_slots

    @staticmethod
    def determine_period(now: datetime, forced_period: str, show_selector: bool) -> str:
        """Détermine la période à afficher selon les paramètres"""
        if forced_period and forced_period in ['morning', 'afternoon']:
            return forced_period
        elif show_selector and not forced_period:
            # Si le sélecteur est activé mais pas de période forcée, afficher toute la journée
            return 'full_day'
        else:
            # Mode automatique basé sur l'heure actuelle
            return StudentService.get_current_period_strict(now)

    @staticmethod
    def get_period_label(period: str) -> str:
        """Retourne le libellé de la période en français"""
        if period == "morning":
            return "Matinée"
        elif period == "afternoon":
            return "Après-midi"
        else:
            return "Journée complète"

    @staticmethod
    def generate_simple_academic_calendar():
        """Génère une liste simple de semaines alternant A et B (version étudiante)"""
        weeks = []
        is_type_A = True
        # Inclure explicitement la semaine 36 avant la séquence habituelle
        weeks.append(f"Semaine 36 {'A' if is_type_A else 'B'}")
        is_type_A = not is_type_A
        # Semaines 37 à 52
        for week_num in range(37, 53):
            week_type = "A" if is_type_A else "B"
            weeks.append(f"Semaine {week_num} {week_type}")
            is_type_A = not is_type_A
        # Semaines 01 à 35
        for week_num in range(1, 36):
            week_type = "A" if is_type_A else "B"
            weeks.append(f"Semaine {week_num:02d} {week_type}")
            is_type_A = not is_type_A
        return weeks

    @staticmethod
    def get_current_academic_week_name(calendar, now: datetime):
        """Détermine le nom de la semaine académique actuelle à partir du calendrier"""
        current_week_number = now.isocalendar()[1]

        # Formats de recherche possibles pour le numéro de semaine
        search_pattern_1 = f"Semaine {current_week_number} "
        search_pattern_2 = f"Semaine {current_week_number:02d} "

        for week in calendar:
            if week.startswith(search_pattern_1) or week.startswith(search_pattern_2):
                return week

        # Si la semaine n'est pas dans le calendrier scolaire (ex: vacances), on prend la première.
        return calendar[0] if calendar else None

    @staticmethod
    def get_courses_for_day(all_courses, week_name: str, current_day_fr: str, forced_day: str = None):
        """Filtre les cours pour la semaine et le jour spécifiés"""
        valid_days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

        if forced_day and forced_day in valid_days:
            target_day = forced_day
        else:
            target_day = current_day_fr

        courses_for_display = [
            c for c in all_courses
            if c.week_name == week_name and c.day == target_day
        ]

        return courses_for_display, target_day, valid_days

    @staticmethod
    def get_student_view_data(schedule_manager, request, week_name=None):
        """Récupère toutes les données nécessaires pour la vue étudiante"""
        # Permettre de simuler une date pour les tests via un paramètre d'URL
        test_date_str = request.args.get('test_date')
        try:
            now = datetime.strptime(test_date_str, '%Y-%m-%d')
        except (ValueError, TypeError):
            now = datetime.now(pytz.timezone("Europe/Paris"))

        # Paramètres de la requête
        show_selector = request.args.get("show_selector", "false").lower() == "true"
        kiosque_mode = request.args.get("kiosque", "false").lower() == "true"
        forced_period = request.args.get('period')
        forced_day = request.args.get('day')

        # Générer le calendrier et déterminer la semaine
        weeks_to_display = StudentService.generate_simple_academic_calendar()

        if week_name is None:
            week_name = StudentService.get_current_academic_week_name(weeks_to_display, now)

        # Déterminer le jour à afficher
        current_day_fr = StudentService.get_french_day_name(now, forced_day)

        # Récupérer les cours
        all_courses = schedule_manager.get_all_courses()
        courses_for_display, target_day, valid_days = StudentService.get_courses_for_day(
            all_courses, week_name, current_day_fr, forced_day
        )

        # Générer la grille horaire
        time_slots = TimeSlotService.generate_time_grid()

        # Construire la grille étudiante
        student_grid = StudentService.build_student_grid(
            courses_for_display, time_slots, target_day, schedule_manager
        )

        # Déterminer la période à afficher
        period = StudentService.determine_period(now, forced_period, show_selector)

        # Filtrer les créneaux par période
        period_slots = StudentService.filter_time_slots_by_period(time_slots, period)

        # Masquer les créneaux vides
        filtered_time_slots = StudentService.filter_empty_slots(period_slots, student_grid, target_day)

        return {
            'student_grid': student_grid,
            'time_slots': filtered_time_slots,
            'days_order': [target_day],
            'current_week': week_name,
            'all_weeks': weeks_to_display,
            'current_period': period,
            'current_day': target_day,
            'period_label': StudentService.get_period_label(period),
            'total_courses': len(courses_for_display),
            'show_selector': show_selector,
            'forced_period': forced_period,
            'forced_day': forced_day,
            'valid_days': valid_days,
            'kiosque_mode': kiosque_mode
        }