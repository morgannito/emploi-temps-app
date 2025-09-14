from flask_sqlalchemy import SQLAlchemy
from infrastructure.container import container
from infrastructure.repositories.sqlalchemy_course_repository import SqlAlchemyCourseRepository, SqlAlchemyCustomCourseRepository
from domain.repositories.course_repository import CourseRepository, CustomCourseRepository
from domain.services.room_assignment_service import RoomAssignmentService


def configure_container(db: SQLAlchemy) -> None:
    """Configure le container d'injection de dépendances"""

    # Repositories - factories qui créent des instances avec la session DB
    container.register_factory(
        CourseRepository,
        lambda: SqlAlchemyCourseRepository(db.session)
    )

    container.register_factory(
        CustomCourseRepository,
        lambda: SqlAlchemyCustomCourseRepository(db.session)
    )

    # Domain services - singletons avec résolution automatique des dépendances
    container.register_singleton(
        RoomAssignmentService,
        RoomAssignmentService
    )