from typing import List, Optional
from sqlalchemy.orm import Session
from domain.entities.course import Course as DomainCourse, CourseId, CustomCourse as DomainCustomCourse
from domain.repositories.course_repository import CourseRepository, CustomCourseRepository
from domain.value_objects.time_slot import WeekIdentifier, TimeSlot
from models import Course as CourseModel, CustomCourse as CustomCourseModel


class SqlAlchemyCourseRepository(CourseRepository):
    """Implémentation SQLAlchemy du repository de cours"""

    def __init__(self, session: Session):
        self._session = session

    def find_by_id(self, course_id: CourseId) -> Optional[DomainCourse]:
        model = self._session.query(CourseModel).filter_by(id=course_id.value).first()
        return self._to_domain(model) if model else None

    def find_all(self) -> List[DomainCourse]:
        models = self._session.query(CourseModel).all()
        return [self._to_domain(model) for model in models]

    def find_by_week(self, week_identifier: WeekIdentifier) -> List[DomainCourse]:
        models = self._session.query(CourseModel).filter_by(
            week_name=week_identifier.value
        ).all()
        return [self._to_domain(model) for model in models]

    def find_by_professor(self, professor_name: str) -> List[DomainCourse]:
        models = self._session.query(CourseModel).filter_by(
            professor=professor_name
        ).all()
        return [self._to_domain(model) for model in models]

    def find_by_week_and_day(self, week_identifier: WeekIdentifier, day: str) -> List[DomainCourse]:
        models = self._session.query(CourseModel).filter(
            CourseModel.week_name == week_identifier.value,
            CourseModel.day == day
        ).all()
        return [self._to_domain(model) for model in models]

    def find_conflicting_courses(self, course: DomainCourse) -> List[DomainCourse]:
        models = self._session.query(CourseModel).filter(
            CourseModel.week_name == course.week_identifier.value,
            CourseModel.day == course.day_of_week,
            CourseModel.id != course.course_id.value
        ).all()

        conflicts = []
        for model in models:
            other_course = self._to_domain(model)
            if course.has_conflict_with(other_course):
                conflicts.append(other_course)
        return conflicts

    def save(self, course: DomainCourse) -> DomainCourse:
        model = self._session.query(CourseModel).filter_by(id=course.course_id.value).first()

        if model:
            self._update_model(model, course)
        else:
            model = self._create_model(course)
            self._session.add(model)

        self._session.commit()
        return course

    def delete(self, course_id: CourseId) -> bool:
        model = self._session.query(CourseModel).filter_by(id=course_id.value).first()
        if model:
            self._session.delete(model)
            self._session.commit()
            return True
        return False

    def get_next_available_id(self) -> CourseId:
        max_id = self._session.query(CourseModel.id).order_by(CourseModel.id.desc()).first()
        next_id = (max_id[0] if max_id else 0) + 1
        return CourseId(str(next_id))

    def _to_domain(self, model: CourseModel) -> DomainCourse:
        """Convertit un modèle SQLAlchemy en entité domaine"""
        time_slot = TimeSlot(
            start_time=model.start_time,
            end_time=model.end_time
        )

        return DomainCourse(
            course_id=CourseId(str(model.id)),
            course_type=model.course_type,
            professor_name=model.professor,
            week_identifier=WeekIdentifier.from_string(model.week_name),
            day_of_week=model.day,
            time_slot=time_slot,
            student_count=model.student_count,
            assigned_room_id=model.assigned_room,
            tp_name=model.tp_name
        )

    def _create_model(self, course: DomainCourse) -> CourseModel:
        """Crée un nouveau modèle SQLAlchemy depuis l'entité domaine"""
        return CourseModel(
            id=int(course.course_id.value),
            course_type=course.course_type,
            professor=course.professor_name,
            week_name=course.week_identifier.value,
            day=course.day_of_week,
            start_time=course.time_slot.start_time,
            end_time=course.time_slot.end_time,
            student_count=course.student_count,
            assigned_room=course.assigned_room_id,
            tp_name=course.tp_name
        )

    def _update_model(self, model: CourseModel, course: DomainCourse) -> None:
        """Met à jour un modèle SQLAlchemy avec les données de l'entité domaine"""
        model.course_type = course.course_type
        model.professor = course.professor_name
        model.week_name = course.week_identifier.value
        model.day = course.day_of_week
        model.start_time = course.time_slot.start_time
        model.end_time = course.time_slot.end_time
        model.student_count = course.student_count
        model.assigned_room = course.assigned_room_id
        model.tp_name = course.tp_name


class SqlAlchemyCustomCourseRepository(CustomCourseRepository):
    """Implémentation SQLAlchemy du repository de cours personnalisés"""

    def __init__(self, session: Session):
        self._session = session

    def find_all_custom_courses(self) -> List[DomainCustomCourse]:
        models = self._session.query(CustomCourseModel).all()
        return [self._to_domain(model) for model in models]

    def save_custom_course(self, course: DomainCustomCourse) -> DomainCustomCourse:
        model = self._session.query(CustomCourseModel).filter_by(id=course.course_id.value).first()

        if model:
            self._update_model(model, course)
        else:
            model = self._create_model(course)
            self._session.add(model)

        self._session.commit()
        return course

    def delete_custom_course(self, course_id: CourseId) -> bool:
        model = self._session.query(CustomCourseModel).filter_by(id=course_id.value).first()
        if model:
            self._session.delete(model)
            self._session.commit()
            return True
        return False

    def find_tp_name(self, course_id: CourseId) -> Optional[str]:
        model = self._session.query(CustomCourseModel).filter_by(id=course_id.value).first()
        return model.tp_name if model else None

    def save_tp_name(self, course_id: CourseId, tp_name: str) -> bool:
        model = self._session.query(CustomCourseModel).filter_by(id=course_id.value).first()
        if model:
            model.tp_name = tp_name
            self._session.commit()
            return True
        return False

    def _to_domain(self, model: CustomCourseModel) -> DomainCustomCourse:
        """Convertit un modèle SQLAlchemy en entité domaine"""
        time_slot = TimeSlot(
            start_time=model.start_time,
            end_time=model.end_time
        )

        return DomainCustomCourse(
            course_id=CourseId(str(model.id)),
            course_type=model.course_type,
            professor_name=model.professor,
            week_identifier=WeekIdentifier.from_string(model.week_name),
            day_of_week=model.day,
            time_slot=time_slot,
            student_count=model.student_count,
            assigned_room_id=model.assigned_room,
            tp_name=model.tp_name
        )

    def _create_model(self, course: DomainCustomCourse) -> CustomCourseModel:
        """Crée un nouveau modèle SQLAlchemy depuis l'entité domaine"""
        return CustomCourseModel(
            id=int(course.course_id.value),
            course_type=course.course_type,
            professor=course.professor_name,
            week_name=course.week_identifier.value,
            day=course.day_of_week,
            start_time=course.time_slot.start_time,
            end_time=course.time_slot.end_time,
            student_count=course.student_count,
            assigned_room=course.assigned_room_id,
            tp_name=course.tp_name
        )

    def _update_model(self, model: CustomCourseModel, course: DomainCustomCourse) -> None:
        """Met à jour un modèle SQLAlchemy avec les données de l'entité domaine"""
        model.course_type = course.course_type
        model.professor = course.professor_name
        model.week_name = course.week_identifier.value
        model.day = course.day_of_week
        model.start_time = course.time_slot.start_time
        model.end_time = course.time_slot.end_time
        model.student_count = course.student_count
        model.assigned_room = course.assigned_room_id
        model.tp_name = course.tp_name