import os
import time
from typing import Dict, List, Any, Optional
from threading import RLock
from datetime import date, timedelta
from services.timeslot_service import TimeSlotService


class CacheService:
    """Service centralisé pour la gestion du cache de l'application"""

    def __init__(self):
        # Cache pour les salles occupées
        self._occupied_rooms_cache = {}
        self._cache_lock = RLock()
        self._cache_ttl = 3  # 3 secondes de cache

        # Cache pour le planning
        self._academic_weeks = None
        self._courses_cache = {}
        self._last_sync_time = 0

    # ==================== CACHE SALLES OCCUPÉES ====================

    def get_cache_key(self, course_id: str, week_name: str, day: str, start_time: str, end_time: str) -> str:
        """Génère une clé de cache unique pour un créneau"""
        return f"{course_id}_{week_name}_{day}_{start_time}_{end_time}"

    def invalidate_occupied_rooms_cache(self):
        """Invalide complètement le cache des salles occupées"""
        with self._cache_lock:
            self._occupied_rooms_cache.clear()

    def get_occupied_rooms_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Récupère les salles occupées depuis le cache"""
        with self._cache_lock:
            if cache_key in self._occupied_rooms_cache:
                cached_data = self._occupied_rooms_cache[cache_key]
                if time.time() - cached_data['timestamp'] < self._cache_ttl:
                    return cached_data
        return None

    def set_occupied_rooms_cache(self, cache_key: str, rooms_list: List[str]):
        """Met en cache les salles occupées"""
        with self._cache_lock:
            self._occupied_rooms_cache[cache_key] = {
                'rooms': rooms_list,
                'timestamp': time.time()
            }

    # ==================== CACHE PLANNING ====================

    def clear_planning_cache(self):
        """Vide complètement le cache du planning"""
        self._academic_weeks = None
        self._courses_cache.clear()
        self._last_sync_time = 0

    def is_planning_cache_valid(self) -> bool:
        """Vérifie si le cache du planning est valide"""
        try:
            sync_file = "data/.last_sync"
            if os.path.exists(sync_file):
                with open(sync_file, 'r') as f:
                    last_sync = float(f.read().strip())
                return last_sync == self._last_sync_time
        except:
            pass
        return False

    def update_sync_time(self):
        """Met à jour le timestamp de synchronisation"""
        try:
            sync_file = "data/.last_sync"
            if os.path.exists(sync_file):
                with open(sync_file, 'r') as f:
                    self._last_sync_time = float(f.read().strip())
        except:
            self._last_sync_time = time.time()

    def get_cached_academic_weeks(self) -> List[Dict]:
        """Génère et cache la liste des semaines académiques"""
        if self._academic_weeks is None:
            weeks = []
            is_type_A = True

            # Première partie de l'année (septembre à décembre) - Semaines 36-52
            start_date = date(2025, 9, 1)
            for week_num in range(36, 53):
                week_type = "A" if is_type_A else "B"
                week_offset = (week_num - 36) * 7
                monday_date = start_date + timedelta(days=week_offset)
                date_str = monday_date.strftime("%d/%m/%Y")

                weeks.append({
                    'name': f"Semaine {week_num} {week_type}",
                    'date': date_str,
                    'full_name': f"Semaine {week_num} {week_type} ({date_str})"
                })
                is_type_A = not is_type_A

            # Deuxième partie de l'année (janvier à juin) - Semaines 1-35
            january_start = date(2026, 1, 5)
            for week_num in range(1, 36):
                week_type = "A" if is_type_A else "B"
                week_offset = (week_num - 1) * 7
                monday_date = january_start + timedelta(days=week_offset)
                date_str = monday_date.strftime("%d/%m/%Y")

                weeks.append({
                    'name': f"Semaine {week_num:02d} {week_type}",
                    'date': date_str,
                    'full_name': f"Semaine {week_num:02d} {week_type} ({date_str})"
                })
                is_type_A = not is_type_A

            self._academic_weeks = weeks

        return self._academic_weeks

    def get_cached_courses_for_week(self, week_name: str, schedule_manager) -> List:
        """Récupère les cours pour une semaine avec cache"""
        # Vérifier la validité du cache
        if not self.is_planning_cache_valid():
            self.clear_planning_cache()
            self.update_sync_time()

        if week_name not in self._courses_cache:
            # Utiliser get_all_courses() et filtrer par semaine
            all_courses = schedule_manager.get_all_courses()
            courses = [course for course in all_courses if course.week_name == week_name]

            # Mettre en cache
            self._courses_cache[week_name] = courses
            print(f"🔍 Cache mis à jour: {len(courses)} cours pour {week_name}")

        return self._courses_cache[week_name]

    def build_weekly_grid_optimized(self, courses_for_week: List, time_slots: List[Dict],
                                   days_order: List[str], schedule_manager) -> Dict:
        """Construction optimisée de la grille hebdomadaire"""
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
        prof_working_days = schedule_manager.get_prof_working_days()

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

    def _place_course_in_grid(self, course: Dict, time_slots_minutes: List[Dict],
                            weekly_grid: Dict, day: str):
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

    # ==================== GESTION GLOBALE ====================

    def clear_all_caches(self):
        """Vide tous les caches de l'application"""
        self.invalidate_occupied_rooms_cache()
        self.clear_planning_cache()