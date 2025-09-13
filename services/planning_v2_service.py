from datetime import date, timedelta, datetime
from typing import Dict, List, Any
import pytz
import time
import os
from services.timeslot_service import TimeSlotService


class PlanningV2Service:
    """Service pour la gestion du planning V2 en lecture seule"""

    def __init__(self, schedule_manager):
        self.schedule_manager = schedule_manager

    def generate_academic_calendar(self) -> List[Dict]:
        """Génère une liste de semaines alternant A et B pour toute l'année scolaire avec dates"""
        weeks = []
        is_type_A = True  # On commence par une semaine de type A

        # Date de début de l'année scolaire (dernière semaine d'août 2025)
        # Semaine 36 commence le 1er septembre 2025
        start_date = date(2025, 9, 1)  # Lundi 1er septembre 2025

        # Première partie de l'année (septembre à décembre) - Semaines 36-52
        for week_num in range(36, 53):
            week_type = "A" if is_type_A else "B"

            # Calculer la date du lundi de cette semaine
            week_offset = (week_num - 36) * 7  # 7 jours par semaine
            monday_date = start_date + timedelta(days=week_offset)

            # Formater la date
            date_str = monday_date.strftime("%d/%m/%Y")

            weeks.append({
                'name': f"Semaine {week_num} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A

        # Deuxième partie de l'année (janvier à juin) - Semaines 1-35
        january_start = date(2026, 1, 5)  # Premier lundi de janvier 2026 (semaine 1)

        for week_num in range(1, 36):
            week_type = "A" if is_type_A else "B"

            # Calculer la date du lundi de cette semaine
            week_offset = (week_num - 1) * 7  # 7 jours par semaine
            monday_date = january_start + timedelta(days=week_offset)

            # Formater la date
            date_str = monday_date.strftime("%d/%m/%Y")

            weeks.append({
                'name': f"Semaine {week_num:02d} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num:02d} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A

        return weeks

    def generate_time_grid(self) -> List[Dict]:
        """Génère la grille horaire de 8h à 18h"""
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

    def determine_current_week(self, weeks_to_display: List[Dict]) -> str:
        """Détermine la semaine courante basée sur la date actuelle"""
        today = datetime.now(pytz.timezone("Europe/Paris")).date()
        week_num = today.isocalendar()[1]

        if today.year == 2025 and week_num >= 36:
            # Deuxième partie de 2025
            weeks_since_start = week_num - 36
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            week_name = f"Semaine {week_num} {week_type}"
        elif today.year == 2026 and week_num <= 35:
            # Première partie de 2026
            weeks_since_start = 17 + week_num - 1  # 17 semaines en 2025 + semaines 2026
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            week_name = f"Semaine {week_num:02d} {week_type}"
        else:
            # Fallback à la première semaine disponible
            week_name = weeks_to_display[0]['name'] if weeks_to_display else "Semaine 36 A"

        return week_name

    def find_week_info(self, week_name: str, weeks_to_display: List[Dict]) -> Dict:
        """Trouve les informations d'une semaine spécifique"""
        for week_info in weeks_to_display:
            if week_info['name'] == week_name:
                return week_info

        # Fallback à la première semaine si non trouvée
        return weeks_to_display[0] if weeks_to_display else {
            'name': week_name,
            'date': 'N/A',
            'full_name': week_name
        }

    def build_weekly_grid(self, courses_for_week: List, time_slots: List[Dict], days_order: List[str]) -> Dict:
        """Construit la grille hebdomadaire pour l'affichage"""
        # Préparer les créneaux avec minutes pour optimisation
        time_slots_minutes = []
        for slot in time_slots:
            time_slots_minutes.append({
                'label': slot['label'],
                'start_min': TimeSlotService.time_to_minutes(slot['start_time']),
                'end_min': TimeSlotService.time_to_minutes(slot['end_time']),
                'slot_info': slot
            })

        # Initialiser la grille hebdomadaire
        weekly_grid = {}
        for day in days_order:
            weekly_grid[day] = {}
            for slot in time_slots_minutes:
                weekly_grid[day][slot['label']] = {
                    'time_info': slot['slot_info'],
                    'courses': []
                }

        # Grouper les cours par jour pour optimisation
        courses_by_day = {}
        for day in days_order:
            courses_by_day[day] = []

        # Récupérer les jours de travail des professeurs pour l'affichage
        prof_working_days = self.schedule_manager.get_prof_working_days()

        # Convertir les cours en dictionnaires avec métadonnées
        for course in courses_for_week:
            if course.day in courses_by_day:
                from dataclasses import asdict
                course_dict = asdict(course)
                course_dict['working_days'] = prof_working_days.get(course.professor, [])
                courses_by_day[course.day].append(course_dict)

        # Placer les cours dans la grille pour chaque jour
        for day in days_order:
            day_courses = courses_by_day[day]

            # Séparer les cours originaux des TPs personnalisés
            original_courses = [c for c in day_courses if not c['course_id'].startswith('custom_')]
            custom_tps = [c for c in day_courses if c['course_id'].startswith('custom_')]

            # Créer un lookup des cours originaux pour associer les TPs
            original_lookup = {}
            for course in original_courses:
                key = (course['professor'], course['raw_time_slot'])
                if key not in original_lookup:
                    original_lookup[key] = []
                original_lookup[key].append(course)

            # Initialiser la liste des TPs liés
            for course in day_courses:
                course['related_tps'] = []

            # Associer les TPs personnalisés aux cours originaux
            standalone_tps = []
            for tp in custom_tps:
                key = (tp['professor'], tp['raw_time_slot'])
                matching_originals = original_lookup.get(key, [])
                if matching_originals:
                    # Associer le TP au premier cours original correspondant
                    matching_originals[0]['related_tps'].append(tp)
                else:
                    # TP indépendant
                    standalone_tps.append(tp)

            # Placer tous les cours (originaux + TPs indépendants)
            courses_to_place = original_courses + standalone_tps

            for course in courses_to_place:
                self._place_course_in_grid(course, time_slots_minutes, weekly_grid, day)

        return weekly_grid

    def _place_course_in_grid(self, course: Dict, time_slots_minutes: List[Dict], weekly_grid: Dict, day: str):
        """Place un cours dans la grille hebdomadaire"""
        course_start_min = TimeSlotService.time_to_minutes(course['start_time'])
        course_end_min = TimeSlotService.time_to_minutes(course['end_time'])

        primary_slot = None
        spans_slots = []

        # Trouver les créneaux que le cours chevauche
        for slot in time_slots_minutes:
            # Le cours chevauche le créneau si leurs intervalles se croisent
            if not (course_end_min <= slot['start_min'] or course_start_min >= slot['end_min']):
                spans_slots.append(slot['label'])

                # Le créneau primaire est celui où le cours commence
                if course_start_min >= slot['start_min'] and course_start_min < slot['end_min'] and primary_slot is None:
                    primary_slot = slot['label']

        if primary_slot:
            # Marquer les métadonnées du cours
            course['is_primary_slot'] = True
            course['spans_slots'] = spans_slots

            # Placer le cours dans chaque créneau qu'il chevauche
            for slot_label in spans_slots:
                if slot_label == primary_slot:
                    # Dans le créneau primaire, placer le cours complet
                    weekly_grid[day][slot_label]['courses'].append(course)
                else:
                    # Dans les créneaux suivants, placer une continuation
                    continuation_course = course.copy()
                    continuation_course['is_continuation'] = True
                    continuation_course['primary_slot'] = primary_slot
                    weekly_grid[day][slot_label]['courses'].append(continuation_course)

    def verify_data_consistency(self):
        """Vérifie la cohérence des données et force une resynchronisation si nécessaire"""
        try:
            all_courses = self.schedule_manager.get_all_courses()
            room_assignments_count = len(self.schedule_manager.room_assignments)
            courses_with_rooms = sum(1 for c in all_courses if c.assigned_room)

            if abs(room_assignments_count - courses_with_rooms) > 5:  # Tolérance de 5
                print(f"Warning: Incohérence détectée - Attributions: {room_assignments_count}, Cours avec salles: {courses_with_rooms}")
                # Forcer une nouvelle synchronisation
                self.schedule_manager.force_sync_data()
                return False
            return True
        except Exception as e:
            print(f"Erreur lors de la vérification de cohérence: {e}")
            return False

    def get_courses_for_week(self, week_name: str) -> List:
        """Récupère tous les cours pour une semaine donnée"""
        all_courses = self.schedule_manager.get_all_courses()
        return [course for course in all_courses if course.week_name == week_name]

    def prepare_template_context(self, weekly_grid: Dict, time_slots: List[Dict],
                               days_order: List[str], weeks_to_display: List[Dict],
                               current_week: str, current_week_info: Dict) -> Dict:
        """Prépare le contexte pour le template Jinja2"""
        return {
            'weekly_grid': weekly_grid,
            'time_slots': time_slots,
            'days_order': days_order,
            'rooms': self.schedule_manager.rooms,
            'get_room_name': self.schedule_manager.get_room_name,
            'all_weeks': weeks_to_display,
            'current_week': current_week,
            'current_week_info': current_week_info,
            'all_professors': self.schedule_manager.get_normalized_professors_list()
        }

    def handle_fast_planning(self, week_name=None, cache_service=None):
        """Version optimisée avec cache et mesures de performance"""
        start_time = time.time()

        # Sync légère avec vérification des timestamps
        self._handle_lightweight_sync(cache_service)

        # Vérification cohérence des données
        self._check_data_consistency()

        # Récupération des semaines académiques
        weeks_to_display = cache_service.get_cached_academic_weeks()

        if not weeks_to_display:
            raise Exception("Erreur lors de la génération du calendrier")

        # Détermination de la semaine courante si non fournie
        if week_name is None:
            week_name = self.determine_current_week(weeks_to_display)

        # Trouver les informations de la semaine
        current_week_info = self.find_week_info(week_name, weeks_to_display)

        # Si la semaine n'est pas trouvée, utiliser la première
        if current_week_info == weeks_to_display[0] and week_name != weeks_to_display[0]['name']:
            week_name = current_week_info['name']

        # Génération de la grille horaire
        time_slots = self.generate_time_grid()
        days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

        # Récupération des cours - MÊME SOURCE que /week/
        courses_for_week = cache_service.get_cached_courses_for_week(week_name, self.schedule_manager)
        print(f"🔢 Cours générés: {len(courses_for_week)}")

        # Construction de la grille optimisée
        weekly_grid = cache_service.build_weekly_grid_optimized(courses_for_week, time_slots, days_order, self.schedule_manager)

        # Mesure des performances
        end_time = time.time()
        processing_time = end_time - start_time
        print(f"⚡ Planning V2 Fast - Traitement en {processing_time:.3f}s pour {len(courses_for_week)} cours")

        # Préparer le contexte template
        context = self.prepare_template_context(
            weekly_grid, time_slots, days_order, weeks_to_display,
            week_name, current_week_info
        )
        context['processing_time'] = processing_time

        return context

    def _handle_lightweight_sync(self, cache_service):
        """Gère la synchronisation légère avec vérification des timestamps"""
        try:
            sync_file = "data/.last_sync"
            if os.path.exists(sync_file):
                with open(sync_file, 'r') as f:
                    last_sync = float(f.read().strip())
                if time.time() - last_sync > 300:  # 5 minutes
                    self.schedule_manager.force_sync_data()
                    if cache_service:
                        cache_service.clear_planning_cache()
            else:
                self.schedule_manager.force_sync_data()
                if cache_service:
                    cache_service.clear_planning_cache()
        except Exception as e:
            print(f"Erreur sync légère: {e}")
            self.schedule_manager.force_sync_data()
            if cache_service:
                cache_service.clear_planning_cache()

    def _check_data_consistency(self):
        """Vérifie la cohérence des attributions de salles"""
        try:
            room_assignments_count = len(self.schedule_manager.room_assignments)
            if room_assignments_count == 0:
                print("Warning: Aucune attribution de salle trouvée")
        except Exception as e:
            print(f"Erreur vérification cohérence: {e}")