import time
from functools import lru_cache
from typing import Dict, List, Any, Optional
from threading import RLock
import hashlib


class PerformanceCacheService:
    """Service de cache haute performance pour optimiser les requêtes fréquentes"""

    def __init__(self):
        self._cache = {}
        self._cache_lock = RLock()
        self._last_sync_time = 0
        self._sync_interval = 30  # 30 secondes

    def _should_sync(self) -> bool:
        """Vérifie si une synchronisation est nécessaire"""
        return time.time() - self._last_sync_time > self._sync_interval

    def _get_cache_key(self, *args) -> str:
        """Génère une clé de cache basée sur les arguments"""
        key_str = "_".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()[:16]

    def get_cached_courses(self, schedule_manager, force_refresh=False) -> List:
        """Cache des cours avec TTL intelligent"""
        cache_key = "all_courses"

        with self._cache_lock:
            if not force_refresh and cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if time.time() - cached_data['timestamp'] < 30:  # 30s TTL
                    return cached_data['data']

            # Recharger seulement si nécessaire
            if self._should_sync() or force_refresh:
                courses = schedule_manager.get_all_courses()
                self._cache[cache_key] = {
                    'data': courses,
                    'timestamp': time.time()
                }
                self._last_sync_time = time.time()
                return courses

            # Utiliser cache existant même expiré si pas de sync nécessaire
            if cache_key in self._cache:
                return self._cache[cache_key]['data']

            # Fallback
            courses = schedule_manager.get_all_courses()
            self._cache[cache_key] = {
                'data': courses,
                'timestamp': time.time()
            }
            return courses

    def get_cached_courses_by_week(self, schedule_manager, week_name: str) -> List:
        """Cache des cours par semaine"""
        cache_key = f"courses_week_{week_name}"

        with self._cache_lock:
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if time.time() - cached_data['timestamp'] < 60:  # 1min TTL
                    return cached_data['data']

            all_courses = self.get_cached_courses(schedule_manager)
            week_courses = [c for c in all_courses if c.week_name == week_name]

            self._cache[cache_key] = {
                'data': week_courses,
                'timestamp': time.time()
            }
            return week_courses

    def get_cached_professor_courses(self, schedule_manager, prof_name: str) -> Dict:
        """Cache des cours par professeur"""
        cache_key = f"prof_courses_{prof_name}"

        with self._cache_lock:
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if time.time() - cached_data['timestamp'] < 120:  # 2min TTL
                    return cached_data['data']

            all_courses = self.get_cached_courses(schedule_manager)
            prof_courses = {}

            # Grouper par semaine
            for course in all_courses:
                if course.professor == prof_name:
                    week = course.week_name
                    if week not in prof_courses:
                        prof_courses[week] = []
                    prof_courses[week].append(course)

            self._cache[cache_key] = {
                'data': prof_courses,
                'timestamp': time.time()
            }
            return prof_courses

    @lru_cache(maxsize=256)
    def get_cached_room_mapping(self) -> Dict[str, str]:
        """Cache statique du mapping des salles"""
        import json
        import os

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

    def get_cached_available_weeks(self, schedule_manager) -> List[Dict]:
        """Cache des semaines disponibles"""
        cache_key = "available_weeks"

        with self._cache_lock:
            if cache_key in self._cache:
                cached_data = self._cache[cache_key]
                if time.time() - cached_data['timestamp'] < 300:  # 5min TTL
                    return cached_data['data']

            all_courses = self.get_cached_courses(schedule_manager)
            available_weeks = sorted(set([c.week_name for c in all_courses]))

            weeks_list = []
            for week_name in available_weeks:
                weeks_list.append({
                    'name': week_name,
                    'date': None,
                    'full_name': week_name
                })

            self._cache[cache_key] = {
                'data': weeks_list,
                'timestamp': time.time()
            }
            return weeks_list

    def invalidate_cache(self, pattern: str = None):
        """Invalide le cache (optionnellement par pattern)"""
        with self._cache_lock:
            if pattern:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]
            else:
                self._cache.clear()

    def clear_expired_cache(self):
        """Nettoie le cache expiré"""
        current_time = time.time()
        with self._cache_lock:
            expired_keys = []
            for key, data in self._cache.items():
                if current_time - data['timestamp'] > 600:  # 10min max
                    expired_keys.append(key)

            for key in expired_keys:
                del self._cache[key]

    def get_cache_stats(self) -> Dict:
        """Stats du cache pour monitoring"""
        with self._cache_lock:
            return {
                'cache_size': len(self._cache),
                'last_sync': self._last_sync_time,
                'sync_interval': self._sync_interval
            }