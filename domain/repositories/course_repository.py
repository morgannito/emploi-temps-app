from abc import ABC, abstractmethod
from typing import List, Optional
from domain.entities.course import Course, CourseId, CustomCourse
from domain.value_objects.time_slot import WeekIdentifier


class CourseRepository(ABC):
    """Interface du repository pour les cours"""

    @abstractmethod
    def find_by_id(self, course_id: CourseId) -> Optional[Course]:
        """Trouve un cours par son ID"""
        pass

    @abstractmethod
    def find_all(self) -> List[Course]:
        """Récupère tous les cours"""
        pass

    @abstractmethod
    def find_by_week(self, week_identifier: WeekIdentifier) -> List[Course]:
        """Trouve tous les cours d'une semaine"""
        pass

    @abstractmethod
    def find_by_professor(self, professor_name: str) -> List[Course]:
        """Trouve tous les cours d'un professeur"""
        pass

    @abstractmethod
    def find_by_week_and_day(self, week_identifier: WeekIdentifier, day: str) -> List[Course]:
        """Trouve les cours d'un jour spécifique"""
        pass

    @abstractmethod
    def find_conflicting_courses(self, course: Course) -> List[Course]:
        """Trouve les cours en conflit avec un cours donné"""
        pass

    @abstractmethod
    def save(self, course: Course) -> Course:
        """Sauvegarde un cours"""
        pass

    @abstractmethod
    def delete(self, course_id: CourseId) -> bool:
        """Supprime un cours"""
        pass

    @abstractmethod
    def get_next_available_id(self) -> CourseId:
        """Génère le prochain ID disponible"""
        pass


class CustomCourseRepository(ABC):
    """Interface du repository pour les cours personnalisés"""

    @abstractmethod
    def find_all_custom_courses(self) -> List[CustomCourse]:
        """Récupère tous les cours personnalisés"""
        pass

    @abstractmethod
    def save_custom_course(self, course: CustomCourse) -> CustomCourse:
        """Sauvegarde un cours personnalisé"""
        pass

    @abstractmethod
    def delete_custom_course(self, course_id: CourseId) -> bool:
        """Supprime un cours personnalisé"""
        pass

    @abstractmethod
    def find_tp_name(self, course_id: CourseId) -> Optional[str]:
        """Récupère le nom TP d'un cours"""
        pass

    @abstractmethod
    def save_tp_name(self, course_id: CourseId, tp_name: str) -> bool:
        """Sauvegarde le nom TP d'un cours"""
        pass