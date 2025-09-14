from typing import List, Optional
from domain.entities.course import Course
from domain.entities.room import Room
from domain.repositories.course_repository import CourseRepository


class RoomAssignmentService:
    """Service du domaine pour l'attribution des salles"""

    def __init__(self, course_repository: CourseRepository):
        self._course_repository = course_repository

    def can_assign_room_to_course(self, course: Course, room: Room) -> bool:
        """Vérifie si une salle peut être attribuée à un cours"""

        # Vérifier la capacité
        if course.student_count and not room.can_accommodate_course(course.student_count):
            return False

        # Vérifier la compatibilité équipement/type de cours
        if not room.is_suitable_for_course_type(course.course_type):
            return False

        # Vérifier les conflits horaires
        conflicting_courses = self._course_repository.find_conflicting_courses(course)
        for conflicting_course in conflicting_courses:
            if conflicting_course.assigned_room_id == str(room.room_id):
                return False

        return True

    def assign_room_to_course(self, course: Course, room: Room) -> bool:
        """Attribue une salle à un cours si possible"""
        if not self.can_assign_room_to_course(course, room):
            return False

        course.assign_room(str(room.room_id))
        self._course_repository.save(course)
        return True

    def unassign_room_from_course(self, course: Course) -> bool:
        """Retire l'attribution de salle d'un cours"""
        course.unassign_room()
        self._course_repository.save(course)
        return True

    def find_conflicting_assignments(self, course: Course) -> List[Course]:
        """Trouve tous les cours en conflit avec un cours donné pour l'attribution de salles"""
        return self._course_repository.find_conflicting_courses(course)

    def get_room_utilization_for_week(self, room: Room, week_identifier) -> float:
        """Calcule le taux d'utilisation d'une salle pour une semaine"""
        from domain.value_objects.time_slot import WeekIdentifier

        if isinstance(week_identifier, str):
            week_identifier = WeekIdentifier.from_string(week_identifier)

        courses_in_week = self._course_repository.find_by_week(week_identifier)
        room_courses = [c for c in courses_in_week if c.assigned_room_id == str(room.room_id)]

        if not room_courses:
            return 0.0

        total_hours = sum(course.duration_hours for course in room_courses)

        # Supposons 5 jours * 10 heures = 50 heures max par semaine
        max_hours_per_week = 50.0
        return min(total_hours / max_hours_per_week, 1.0)

    def suggest_optimal_room(self, course: Course, available_rooms: List[Room]) -> Optional[Room]:
        """Suggère la salle optimale pour un cours donné"""
        suitable_rooms = [room for room in available_rooms
                         if self.can_assign_room_to_course(course, room)]

        if not suitable_rooms:
            return None

        # Si le cours a un nombre d'étudiants défini, optimiser par capacité
        if course.student_count:
            # Prioriser les salles avec une capacité proche mais suffisante
            suitable_rooms.sort(
                key=lambda r: abs(r.capacity.max_students - course.student_count)
                if r.capacity.max_students >= course.student_count
                else float('inf')
            )

        return suitable_rooms[0]

    def validate_schedule_integrity(self, courses: List[Course]) -> List[str]:
        """Valide l'intégrité d'un planning et retourne les erreurs trouvées"""
        errors = []

        # Grouper par salle et vérifier les conflits
        courses_by_room = {}
        for course in courses:
            if course.assigned_room_id:
                if course.assigned_room_id not in courses_by_room:
                    courses_by_room[course.assigned_room_id] = []
                courses_by_room[course.assigned_room_id].append(course)

        # Vérifier les conflits dans chaque salle
        for room_id, room_courses in courses_by_room.items():
            for i, course1 in enumerate(room_courses):
                for course2 in room_courses[i + 1:]:
                    if course1.has_conflict_with(course2):
                        errors.append(
                            f"Conflit détecté en salle {room_id}: "
                            f"{course1.course_type} ({course1.professor_name}) "
                            f"vs {course2.course_type} ({course2.professor_name}) "
                            f"le {course1.day_of_week} {course1.week_identifier}"
                        )

        return errors