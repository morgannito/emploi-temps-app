from typing import List, Optional, Dict, Any
from domain.entities.course import Course, CourseId, CustomCourse
from domain.entities.room import Room
from domain.repositories.course_repository import CourseRepository, CustomCourseRepository
from domain.services.room_assignment_service import RoomAssignmentService
from domain.value_objects.time_slot import WeekIdentifier, TimeSlot
from infrastructure.container import container
from utils.logger import app_logger


class CourseApplicationService:
    """Service applicatif pour la gestion des cours"""

    def __init__(self):
        self._course_repo = container.get(CourseRepository)
        self._custom_course_repo = container.get(CustomCourseRepository)
        self._room_service = container.get(RoomAssignmentService)

    def get_courses_by_week(self, week_name: str) -> List[Dict[str, Any]]:
        """Récupère tous les cours d'une semaine avec fallback défensif"""
        try:
            week_id = WeekIdentifier.from_string(week_name)
            courses = self._course_repo.find_by_week(week_id)
            custom_courses = self._custom_course_repo.find_all_custom_courses()

            # Filtrer les cours personnalisés pour la semaine
            custom_for_week = [
                c for c in custom_courses
                if getattr(c, 'week_identifier', None) and getattr(c.week_identifier, 'value', '') == week_name
            ]

            # Convertir en dictionnaires pour l'API
            result = []
            for course in courses:
                try:
                    result.append(self._course_to_dict(course))
                except Exception as e:
                    app_logger.error(f"Course mapping error {getattr(course, 'id', 'unknown')}: {e}")
                    continue

            for custom_course in custom_for_week:
                try:
                    result.append(self._course_to_dict(custom_course))
                except Exception as e:
                    app_logger.error(f"Custom course mapping error {getattr(custom_course, 'id', 'unknown')}: {e}")
                    continue

            return result

        except Exception as e:
            # Fallback vers les services legacy existants
            app_logger.warning(f"Clean Architecture fallback for {week_name}: {e}")
            try:
                from services.scheduling_service import SchedulingService
                legacy_service = SchedulingService()
                legacy_courses = legacy_service.get_all_courses()

                # Filtrer par semaine si possible
                filtered_courses = [
                    course for course in legacy_courses
                    if hasattr(course, 'week_name') and course.week_name == week_name
                ]

                # Convertir les objets legacy
                return [
                    {
                        'id': str(getattr(course, 'course_id', getattr(course, 'id', ''))),
                        'course_type': getattr(course, 'course_type', ''),
                        'professor': getattr(course, 'professor', ''),
                        'week_name': getattr(course, 'week_name', ''),
                        'day': getattr(course, 'day', ''),
                        'start_time': getattr(course, 'start_time', ''),
                        'end_time': getattr(course, 'end_time', ''),
                        'student_count': getattr(course, 'nb_students', None),
                        'assigned_room': getattr(course, 'assigned_room', None),
                        'tp_name': getattr(course, 'tp_name', None),
                        'duration_hours': getattr(course, 'duration_hours', 0),
                        '_fallback': 'legacy_service'
                    }
                    for course in filtered_courses
                ]
            except Exception as legacy_error:
                app_logger.error(f"Legacy fallback failed: {legacy_error}")
                return []

    def get_courses_by_professor(self, professor_name: str) -> List[Dict[str, Any]]:
        """Récupère tous les cours d'un professeur"""
        courses = self._course_repo.find_by_professor(professor_name)
        return [self._course_to_dict(course) for course in courses]

    def assign_room_to_course(self, course_id: str, room_data: Dict[str, Any]) -> bool:
        """Attribue une salle à un cours"""
        course = self._course_repo.find_by_id(CourseId(course_id))
        if not course:
            return False

        room = self._dict_to_room(room_data)
        return self._room_service.assign_room_to_course(course, room)

    def unassign_room_from_course(self, course_id: str) -> bool:
        """Retire l'attribution de salle d'un cours"""
        course = self._course_repo.find_by_id(CourseId(course_id))
        if not course:
            return False

        return self._room_service.unassign_room_from_course(course)

    def find_conflicting_courses(self, course_id: str) -> List[Dict[str, Any]]:
        """Trouve les cours en conflit avec un cours donné"""
        course = self._course_repo.find_by_id(CourseId(course_id))
        if not course:
            return []

        conflicts = self._room_service.find_conflicting_assignments(course)
        return [self._course_to_dict(c) for c in conflicts]

    def validate_schedule_for_week(self, week_name: str) -> List[str]:
        """Valide l'intégrité du planning d'une semaine"""
        week_id = WeekIdentifier(week_name)
        courses = self._course_repo.find_by_week(week_id)

        # Ajouter les cours personnalisés
        custom_courses = self._custom_course_repo.find_all_custom_courses()
        custom_for_week = [
            c for c in custom_courses
            if c.week_identifier.value == week_name
        ]

        all_courses = courses + custom_for_week
        return self._room_service.validate_schedule_integrity(all_courses)

    def suggest_optimal_room(self, course_id: str, available_rooms: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Suggère la salle optimale pour un cours"""
        course = self._course_repo.find_by_id(CourseId(course_id))
        if not course:
            return None

        rooms = [self._dict_to_room(room_data) for room_data in available_rooms]
        optimal_room = self._room_service.suggest_optimal_room(course, rooms)

        return optimal_room.to_dict() if optimal_room else None

    def create_custom_course(self, course_data: Dict[str, Any]) -> bool:
        """Crée un cours personnalisé"""
        try:
            time_slot = TimeSlot(
                start_time=course_data['start_time'],
                end_time=course_data['end_time']
            )

            custom_course = CustomCourse(
                course_id=CourseId(course_data['id']),
                course_type=course_data['course_type'],
                professor_name=course_data['professor'],
                week_identifier=WeekIdentifier(course_data['week_name']),
                day_of_week=course_data['day'],
                time_slot=time_slot,
                student_count=course_data.get('student_count'),
                assigned_room_id=course_data.get('assigned_room'),
                tp_name=course_data.get('tp_name')
            )

            self._custom_course_repo.save_custom_course(custom_course)
            return True

        except Exception:
            return False

    def delete_custom_course(self, course_id: str) -> bool:
        """Supprime un cours personnalisé"""
        return self._custom_course_repo.delete_custom_course(CourseId(course_id))

    def get_courses_by_room(self, room_id: str, week_name: str = None) -> List[Dict[str, Any]]:
        """Récupère tous les cours d'une salle spécifique"""
        if week_name:
            week_id = WeekIdentifier.from_string(week_name)
            courses = self._course_repo.find_by_week(week_id)
        else:
            courses = self._course_repo.find_all()

        # Filtrer par salle
        room_courses = [
            c for c in courses
            if c.assigned_room_id == room_id
        ]

        # Convertir en dictionnaires pour l'API
        result = []
        for course in room_courses:
            result.append(self._course_to_dict(course))

        return result

    def _course_to_dict(self, course: Course) -> Dict[str, Any]:
        """Convertit une entité Course en dictionnaire avec mapping défensif"""
        try:
            # Mapping défensif pour compatibilité avec différents types d'objets
            course_id = getattr(course, 'course_id', None)
            if course_id and hasattr(course_id, 'value'):
                id_value = course_id.value
            else:
                id_value = str(getattr(course, 'id', course_id or ''))

            week_id = getattr(course, 'week_identifier', None)
            if week_id and hasattr(week_id, 'value'):
                week_value = week_id.value
            else:
                week_value = str(getattr(course, 'week_name', week_id or ''))

            time_slot = getattr(course, 'time_slot', None)
            if time_slot and hasattr(time_slot, 'start_time'):
                start_time = time_slot.start_time.strftime('%H:%M') if hasattr(time_slot.start_time, 'strftime') else str(time_slot.start_time)
                end_time = time_slot.end_time.strftime('%H:%M') if hasattr(time_slot.end_time, 'strftime') else str(time_slot.end_time)
                duration = getattr(time_slot, 'duration_hours', getattr(course, 'duration_hours', 0))
            else:
                start_time = str(getattr(course, 'start_time', ''))
                end_time = str(getattr(course, 'end_time', ''))
                duration = getattr(course, 'duration_hours', 0)

            return {
                'id': id_value,
                'course_type': getattr(course, 'course_type', ''),
                'professor': getattr(course, 'professor_name', getattr(course, 'professor', '')),
                'week_name': week_value,
                'day': getattr(course, 'day_of_week', getattr(course, 'day', '')),
                'start_time': start_time,
                'end_time': end_time,
                'student_count': getattr(course, 'student_count', getattr(course, 'nb_students', None)),
                'assigned_room': getattr(course, 'assigned_room_id', getattr(course, 'assigned_room', None)),
                'tp_name': getattr(course, 'tp_name', None),
                'duration_hours': duration
            }
        except Exception as e:
            # Fallback mapping en cas d'erreur
            return {
                'id': str(getattr(course, 'id', getattr(course, 'course_id', ''))),
                'course_type': str(getattr(course, 'course_type', '')),
                'professor': str(getattr(course, 'professor_name', getattr(course, 'professor', ''))),
                'week_name': str(getattr(course, 'week_name', '')),
                'day': str(getattr(course, 'day_of_week', getattr(course, 'day', ''))),
                'start_time': str(getattr(course, 'start_time', '')),
                'end_time': str(getattr(course, 'end_time', '')),
                'student_count': getattr(course, 'student_count', getattr(course, 'nb_students', None)),
                'assigned_room': getattr(course, 'assigned_room_id', getattr(course, 'assigned_room', None)),
                'tp_name': getattr(course, 'tp_name', None),
                'duration_hours': getattr(course, 'duration_hours', 0),
                '_mapping_error': str(e)
            }

    def _dict_to_room(self, room_data: Dict[str, Any]) -> Room:
        """Convertit un dictionnaire en entité Room"""
        from domain.entities.room import RoomId
        return Room.from_dict(room_data)