import time
from typing import Dict, List, Any
from flask import jsonify


class RoomAPIService:
    """Service pour les APIs de gestion des salles et conflits"""

    def __init__(self, schedule_manager, cache_service):
        self.schedule_manager = schedule_manager
        self.cache_service = cache_service

    def get_occupied_rooms(self, data: Dict) -> Dict:
        """API optimisée pour récupérer les salles occupées pour un créneau donné"""
        try:
            course_id = data.get('course_id')

            if not course_id:
                return {'occupied_rooms': []}

            # Forcer la synchronisation des données en production
            self.schedule_manager.force_sync_data()

            # Trouver le cours actuel pour obtenir ses informations de créneau
            all_courses = self.schedule_manager.get_all_courses()
            current_course = None

            for course in all_courses:
                if course.course_id == course_id:
                    current_course = course
                    break

            if not current_course:
                return {'occupied_rooms': []}

            # Générer la clé de cache basée sur le créneau
            cache_key = self.cache_service.get_cache_key(
                course_id,
                current_course.week_name,
                current_course.day,
                current_course.start_time,
                current_course.end_time
            )

            # Vérifier le cache
            cached_data = self.cache_service.get_occupied_rooms_from_cache(cache_key)
            if cached_data:
                return {'occupied_rooms': cached_data['rooms'], 'from_cache': True}

            # Calculer les salles occupées (cache miss ou expiré)
            occupied_rooms = set()

            for course in all_courses:
                if (course.course_id != course_id and
                    course.assigned_room and
                    course.week_name == current_course.week_name and
                    course.day == current_course.day):

                    # Vérifier le chevauchement horaire
                    if self.schedule_manager.times_overlap(
                        current_course.start_time, current_course.end_time,
                        course.start_time, course.end_time
                    ):
                        occupied_rooms.add(course.assigned_room)

            occupied_rooms_list = list(occupied_rooms)

            # Mettre en cache
            self.cache_service.set_occupied_rooms_cache(cache_key, occupied_rooms_list)

            return {'occupied_rooms': occupied_rooms_list, 'from_cache': False}

        except Exception as e:
            return {'occupied_rooms': [], 'error': str(e)}

    def get_free_rooms(self, data: Dict) -> Dict:
        """API pour récupérer les salles libres pour un créneau donné"""
        try:
            week_name = data.get('week_name')
            day_name = data.get('day_name')
            time_slot = data.get('time_slot')

            if not all([week_name, day_name, time_slot]):
                return {'free_rooms': [], 'error': 'Paramètres manquants'}

            # Forcer la synchronisation des données
            self.schedule_manager.force_sync_data()

            # Récupérer toutes les salles
            all_rooms = self.schedule_manager.rooms

            # Récupérer tous les cours
            all_courses = self.schedule_manager.get_all_courses()

            # Trouver les cours qui se chevauchent avec ce créneau
            occupied_rooms = set()

            # Parser le créneau horaire (ex: "8h-9h")
            time_parts = time_slot.split('-')
            if len(time_parts) == 2:
                start_time_str = time_parts[0].strip()
                end_time_str = time_parts[1].strip()

                # Convertir le format "8h" en "08:00"
                def convert_time_format(time_str):
                    # Enlever le "h" et convertir en format HH:MM
                    hour = time_str.replace('h', '').strip()
                    return f"{int(hour):02d}:00"

                try:
                    start_time = convert_time_format(start_time_str)
                    end_time = convert_time_format(end_time_str)

                    # Vérifier tous les cours pour ce jour et cette semaine
                    for course in all_courses:
                        if (course.week_name == week_name and
                            course.day == day_name and
                            course.assigned_room):

                            # Vérifier le chevauchement horaire
                            if self.schedule_manager.times_overlap(
                                start_time, end_time,
                                course.start_time, course.end_time
                            ):
                                occupied_rooms.add(course.assigned_room)

                except Exception as e:
                    print(f"Erreur parsing time: {e}")
                    return {'free_rooms': [], 'error': 'Erreur parsing horaire'}

            # Calculer les salles libres
            free_rooms = []
            for room in all_rooms:
                if room['id'] not in occupied_rooms:
                    free_rooms.append({
                        'id': room['id'],
                        'nom': room['nom'],
                        'capacite': room.get('capacite', 'N/A')
                    })

            return {
                'free_rooms': free_rooms,
                'total_rooms': len(all_rooms),
                'occupied_count': len(occupied_rooms),
                'free_count': len(free_rooms)
            }

        except Exception as e:
            return {'free_rooms': [], 'error': str(e)}