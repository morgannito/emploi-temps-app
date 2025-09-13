from typing import List, Dict, Any
from services.timeslot_service import TimeSlotService


class RoomConflictService:
    """Service pour la détection et gestion des conflits de salles"""

    @staticmethod
    def times_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
        """Vérifie si deux créneaux horaires se chevauchent"""
        start1_min = TimeSlotService.time_to_minutes(start1)
        end1_min = TimeSlotService.time_to_minutes(end1)
        start2_min = TimeSlotService.time_to_minutes(start2)
        end2_min = TimeSlotService.time_to_minutes(end2)

        return not (end1_min <= start2_min or end2_min <= start1_min)

    @staticmethod
    def check_room_conflict(course_id: str, room_id: str, all_courses: List) -> bool:
        """
        Vérifie s'il y a un conflit de salle

        Args:
            course_id: Identifiant du cours
            room_id: Identifiant de la salle
            all_courses: Liste de tous les cours

        Returns:
            True s'il y a un conflit
        """
        current_course = None

        # Trouver le cours actuel
        for course in all_courses:
            if course.course_id == course_id:
                current_course = course
                break

        if not current_course:
            return True  # Cours non trouvé = conflit

        # Vérifier les autres cours
        for course in all_courses:
            if (course.course_id != course_id and
                course.assigned_room == room_id and
                course.week_name == current_course.week_name and
                course.day == current_course.day):

                # Vérifier le chevauchement horaire
                if RoomConflictService.times_overlap(
                    current_course.start_time, current_course.end_time,
                    course.start_time, course.end_time
                ):
                    return True  # Conflit détecté

        return False  # Pas de conflit

    @staticmethod
    def check_room_conflict_detailed(course_id: str, room_id: str, all_courses: List) -> Dict:
        """Vérifie s'il y a un conflit de salle avec détails"""
        current_course = None
        conflicts = []

        # Trouver le cours actuel
        for course in all_courses:
            if course.course_id == course_id:
                current_course = course
                break

        if not current_course:
            return {
                'has_conflict': True,
                'conflicts': [{'type': 'course_not_found', 'message': 'Cours non trouvé'}]
            }

        # Vérifier les autres cours
        for course in all_courses:
            if (course.course_id != course_id and
                course.assigned_room == room_id and
                course.week_name == current_course.week_name and
                course.day == current_course.day):

                # Vérifier le chevauchement horaire
                if RoomConflictService.times_overlap(
                    current_course.start_time, current_course.end_time,
                    course.start_time, course.end_time
                ):
                    conflicts.append({
                        'type': 'time_overlap',
                        'conflicting_professor': course.professor,
                        'conflicting_time': f"{course.start_time}-{course.end_time}",
                        'conflicting_class': getattr(course, 'class_name', 'N/A'),
                        'message': f"Conflit avec {course.professor} ({course.start_time}-{course.end_time})"
                    })

        return {
            'has_conflict': len(conflicts) > 0,
            'conflicts': conflicts
        }

    @staticmethod
    def get_room_conflicts_for_time_slot(room_id: str, week_name: str, day: str,
                                       start_time: str, end_time: str, all_courses: List,
                                       exclude_course_id: str = None) -> List[Dict]:
        """
        Retourne tous les cours en conflit pour une salle à un créneau donné

        Args:
            room_id: ID de la salle
            week_name: Nom de la semaine
            day: Jour de la semaine
            start_time: Heure de début
            end_time: Heure de fin
            all_courses: Liste de tous les cours
            exclude_course_id: ID de cours à exclure (optionnel)

        Returns:
            Liste des cours en conflit
        """
        conflicts = []

        for course in all_courses:
            if (course.assigned_room == room_id and
                course.week_name == week_name and
                course.day == day and
                (exclude_course_id is None or course.course_id != exclude_course_id)):

                # Vérifier le chevauchement horaire
                if RoomConflictService.times_overlap(start_time, end_time,
                                                   course.start_time, course.end_time):
                    conflicts.append({
                        'course_id': course.course_id,
                        'professor': course.professor,
                        'start_time': course.start_time,
                        'end_time': course.end_time,
                        'course_type': course.course_type,
                        'duration_hours': course.duration_hours
                    })

        return conflicts

    @staticmethod
    def find_available_rooms_for_slot(week_name: str, day: str, start_time: str, end_time: str,
                                    all_courses: List, all_rooms: List) -> List[Dict]:
        """
        Trouve toutes les salles disponibles pour un créneau donné

        Args:
            week_name: Nom de la semaine
            day: Jour de la semaine
            start_time: Heure de début
            end_time: Heure de fin
            all_courses: Liste de tous les cours
            all_rooms: Liste de toutes les salles

        Returns:
            Liste des salles disponibles
        """
        available_rooms = []

        for room in all_rooms:
            room_id = str(room.get('id'))

            # Vérifier s'il y a des conflits pour cette salle
            conflicts = RoomConflictService.get_room_conflicts_for_time_slot(
                room_id, week_name, day, start_time, end_time, all_courses
            )

            if not conflicts:  # Pas de conflit = salle disponible
                available_rooms.append({
                    'id': room_id,
                    'nom': room.get('nom', ''),
                    'capacite': room.get('capacite', 0),
                    'equipement': room.get('equipement', '')
                })

        return available_rooms

    @staticmethod
    def get_room_occupancy_for_day(room_id: str, week_name: str, day: str, all_courses: List) -> List[Dict]:
        """
        Retourne l'occupation d'une salle pour une journée donnée

        Args:
            room_id: ID de la salle
            week_name: Nom de la semaine
            day: Jour de la semaine
            all_courses: Liste de tous les cours

        Returns:
            Liste des créneaux occupés
        """
        occupancy = []

        for course in all_courses:
            if (course.assigned_room == room_id and
                course.week_name == week_name and
                course.day == day):

                occupancy.append({
                    'course_id': course.course_id,
                    'professor': course.professor,
                    'start_time': course.start_time,
                    'end_time': course.end_time,
                    'course_type': course.course_type,
                    'duration_hours': course.duration_hours
                })

        # Trier par heure de début
        occupancy.sort(key=lambda x: TimeSlotService.time_to_minutes(x['start_time']))

        return occupancy