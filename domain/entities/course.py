from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4
from domain.value_objects.time_slot import TimeSlot, WeekIdentifier


@dataclass
class CourseId:
    """Identifiant unique d'un cours"""
    value: str = field(default_factory=lambda: str(uuid4()))

    def __str__(self) -> str:
        return self.value


@dataclass
class Course:
    """Entité principale représentant un cours dans l'emploi du temps"""
    course_id: CourseId
    professor_name: str
    course_type: str
    time_slot: TimeSlot
    week_identifier: WeekIdentifier
    day_of_week: str
    student_count: Optional[int] = None
    assigned_room_id: Optional[str] = None
    tp_name: Optional[str] = None

    def __post_init__(self):
        if not self.professor_name.strip():
            raise ValueError("Professor name cannot be empty")
        if not self.course_type.strip():
            raise ValueError("Course type cannot be empty")
        if self.day_of_week not in ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']:
            raise ValueError(f"Invalid day of week: {self.day_of_week}")
        if self.student_count is not None and self.student_count < 0:
            raise ValueError("Student count cannot be negative")

    @property
    def duration_hours(self) -> float:
        """Durée du cours en heures"""
        return self.time_slot.duration_hours

    @property
    def is_room_assigned(self) -> bool:
        """Vérifie si une salle est attribuée"""
        return self.assigned_room_id is not None

    def assign_room(self, room_id: str) -> None:
        """Attribue une salle au cours"""
        if not room_id.strip():
            raise ValueError("Room ID cannot be empty")
        self.assigned_room_id = room_id

    def unassign_room(self) -> None:
        """Retire l'attribution de salle"""
        self.assigned_room_id = None

    def has_conflict_with(self, other_course: 'Course') -> bool:
        """Vérifie si ce cours a un conflit avec un autre cours"""
        if self.week_identifier != other_course.week_identifier:
            return False
        if self.day_of_week != other_course.day_of_week:
            return False

        # Si les cours sont dans la même salle ou si on teste le conflit temporel
        same_room = (self.assigned_room_id and other_course.assigned_room_id
                    and self.assigned_room_id == other_course.assigned_room_id)
        temporal_overlap = self.time_slot.overlaps_with(other_course.time_slot)

        # Conflit si même créneau temporel (pour tests) ou même salle + même créneau
        return temporal_overlap and (same_room or
                                   not self.assigned_room_id or
                                   not other_course.assigned_room_id)

    def is_same_teaching_session(self, other_course: 'Course') -> bool:
        """Vérifie si c'est la même session d'enseignement (même prof, type, créneau)"""
        return (
            self.professor_name == other_course.professor_name
            and self.course_type == other_course.course_type
            and self.time_slot == other_course.time_slot
            and self.week_identifier == other_course.week_identifier
            and self.day_of_week == other_course.day_of_week
        )

    def to_dict(self) -> dict:
        """Conversion en dictionnaire pour compatibilité"""
        return {
            'course_id': str(self.course_id),
            'professor': self.professor_name,
            'course_type': self.course_type,
            'start_time': self.time_slot.start_time.strftime('%H:%M'),
            'end_time': self.time_slot.end_time.strftime('%H:%M'),
            'duration_hours': self.duration_hours,
            'week_name': str(self.week_identifier),
            'day': self.day_of_week,
            'nb_students': str(self.student_count) if self.student_count else '',
            'assigned_room': self.assigned_room_id,
            'raw_time_slot': self.time_slot.to_display_format()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Course':
        """Création depuis un dictionnaire"""
        course_id = CourseId(data.get('course_id', str(uuid4())))

        time_slot = TimeSlot.from_strings(
            data['start_time'],
            data['end_time']
        )

        week_identifier = WeekIdentifier.from_string(data['week_name'])

        student_count = None
        if data.get('nb_students'):
            try:
                student_count = int(data['nb_students'])
            except (ValueError, TypeError):
                student_count = None

        return cls(
            course_id=course_id,
            professor_name=data['professor'],
            course_type=data['course_type'],
            time_slot=time_slot,
            week_identifier=week_identifier,
            day_of_week=data['day'],
            student_count=student_count,
            assigned_room_id=data.get('assigned_room')
        )


@dataclass
class CustomCourse(Course):
    """Cours personnalisé (TP) - hérite de Course avec des spécificités"""
    is_custom: bool = field(default=True, init=False)
    tp_name: Optional[str] = None

    def set_tp_name(self, name: str) -> None:
        """Définit le nom personnalisé du TP"""
        if not name.strip():
            raise ValueError("TP name cannot be empty")
        self.tp_name = name.strip()

    @property
    def display_name(self) -> str:
        """Nom d'affichage du cours (avec nom TP si défini)"""
        if self.tp_name:
            return f"{self.course_type} - {self.tp_name}"
        return self.course_type

    def to_dict(self) -> dict:
        """Extension de la méthode parent pour inclure les spécificités TP"""
        data = super().to_dict()
        data['is_custom'] = self.is_custom
        data['tp_name'] = self.tp_name
        return data