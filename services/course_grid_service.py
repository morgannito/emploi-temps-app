from typing import List, Dict
from dataclasses import asdict
from .timeslot_service import TimeSlotService


class CourseGridService:
    """Service pour la construction de la grille des cours"""

    @staticmethod
    def prepare_courses_with_tps(all_courses_for_week: List[Dict]) -> List[Dict]:
        """Attache les TPs aux cours originaux et retourne les cours à placer dans la grille"""

        # Séparer les cours originaux et les TPs personnalisés
        original_courses = [c for c in all_courses_for_week if not c['course_id'].startswith('custom_')]
        custom_tps = [c for c in all_courses_for_week if c['course_id'].startswith('custom_')]

        # Créer un lookup pour les cours originaux
        original_courses_lookup = {}
        for course in original_courses:
            key = (course.get('day'), course.get('professor'), course.get('raw_time_slot'))
            if key not in original_courses_lookup:
                original_courses_lookup[key] = []
            original_courses_lookup[key].append(course)

        # Initialiser related_tps pour tous les cours
        for course in all_courses_for_week:
            course['related_tps'] = []

        # Attacher les TPs aux cours originaux correspondants
        standalone_tps = []
        for tp in custom_tps:
            key = (tp.get('day'), tp.get('professor'), tp.get('raw_time_slot'))
            matching_originals = original_courses_lookup.get(key, [])

            if matching_originals:
                # Attacher ce TP au premier cours original correspondant
                matching_originals[0]['related_tps'].append(tp)
            else:
                # TP autonome (pas de cours original correspondant)
                standalone_tps.append(tp)

        # Retourner les cours à placer dans la grille
        return original_courses + standalone_tps

    @staticmethod
    def build_weekly_grid(courses_to_place: List[Dict], time_slots: List[Dict], days_order: List[str]) -> Dict:
        """Construit la grille hebdomadaire des cours"""

        # Créer une grille complète : jour -> créneau -> liste des cours
        weekly_grid = {}
        for day in days_order:
            weekly_grid[day] = {}
            for time_slot in time_slots:
                weekly_grid[day][time_slot['label']] = {
                    'time_info': time_slot,
                    'courses': []
                }

        # Placer les cours dans la grille
        for course in courses_to_place:
            day = course.get('day')
            if day not in days_order:
                continue

            course_start = course.get('start_time', '')
            course_end = course.get('end_time', '')

            course_start_min = TimeSlotService.time_to_minutes(course_start)
            course_end_min = TimeSlotService.time_to_minutes(course_end)

            # Trouver le premier créneau qui correspond au début du cours
            primary_slot = None
            for time_slot in time_slots:
                slot_start_min = TimeSlotService.time_to_minutes(time_slot['start_time'])
                slot_end_min = TimeSlotService.time_to_minutes(time_slot['end_time'])

                # Si le cours commence dans ce créneau, c'est le créneau principal
                if course_start_min >= slot_start_min and course_start_min < slot_end_min:
                    primary_slot = time_slot['label']
                    # Marquer ce cours comme cours principal dans ce créneau
                    course['is_primary_slot'] = True
                    course['spans_slots'] = []

                    # Calculer tous les créneaux que ce cours occupe
                    for other_slot in time_slots:
                        other_start_min = TimeSlotService.time_to_minutes(other_slot['start_time'])
                        other_end_min = TimeSlotService.time_to_minutes(other_slot['end_time'])

                        # Si ce créneau chevauche avec le cours
                        if not (course_end_min <= other_start_min or course_start_min >= other_end_min):
                            course['spans_slots'].append(other_slot['label'])

                            # Ajouter le cours à ce créneau
                            if other_slot['label'] == primary_slot:
                                # Dans le créneau principal, afficher toutes les infos
                                weekly_grid[day][other_slot['label']]['courses'].append(course)
                            else:
                                # Dans les autres créneaux, afficher une version réduite
                                continuation_course = course.copy()
                                continuation_course['is_continuation'] = True
                                continuation_course['primary_slot'] = primary_slot
                                weekly_grid[day][other_slot['label']]['courses'].append(continuation_course)
                    break

        return weekly_grid

    @staticmethod
    def prepare_courses_for_week(schedule_manager, week_name: str) -> List[Dict]:
        """Prépare et filtre les cours pour une semaine donnée"""
        all_courses_obj = schedule_manager.get_all_courses()
        prof_working_days = schedule_manager.get_prof_working_days()

        # Filtrer pour la semaine et ajouter les jours de travail
        all_courses_for_week = []
        for c in all_courses_obj:
            if c.week_name == week_name:
                course_dict = asdict(c)
                course_dict['working_days'] = prof_working_days.get(c.professor, [])
                all_courses_for_week.append(course_dict)

        return all_courses_for_week