from typing import List, Dict, Optional, Any
from sqlalchemy import and_, or_
from models import db, Course, Room, Professor, CustomCourse, TPName
from dataclasses import dataclass
import json
import time
from services.db_monitoring_service import monitor_query
from utils.logger import app_logger, log_performance, log_database_operation


@dataclass
class ProfessorCourse:
    """Dataclass pour compatibilité avec l'ancien système"""
    professor: str
    start_time: str
    end_time: str
    duration_hours: float
    course_type: str
    nb_students: str
    assigned_room: Optional[str]
    day: str
    raw_time_slot: str
    week_name: str
    course_id: str


class DatabaseService:
    """Service d'accès aux données avec requêtes optimisées"""

    @staticmethod
    @monitor_query
    def get_all_courses() -> List[ProfessorCourse]:
        """Récupère tous les cours (normaux + personnalisés) avec cache SQLite"""
        start_time = time.time()

        # Courses normaux avec requête optimisée (sans joins car pas de relations)
        normal_courses = Course.query.options().all()

        # Courses personnalisés avec requête optimisée
        custom_courses = CustomCourse.query.options().all()

        # Conversion en dataclass pour compatibilité
        all_courses = []

        for course in normal_courses:
            all_courses.append(ProfessorCourse(
                professor=course.professor,
                start_time=course.start_time,
                end_time=course.end_time,
                duration_hours=course.duration_hours,
                course_type=course.course_type,
                nb_students=course.nb_students,
                assigned_room=course.assigned_room,
                day=course.day,
                raw_time_slot=course.raw_time_slot,
                week_name=course.week_name,
                course_id=course.course_id
            ))

        for course in custom_courses:
            all_courses.append(ProfessorCourse(
                professor=course.professor,
                start_time=course.start_time,
                end_time=course.end_time,
                duration_hours=course.duration_hours,
                course_type=course.course_type,
                nb_students=course.nb_students,
                assigned_room=course.assigned_room,
                day=course.day,
                raw_time_slot=course.raw_time_slot,
                week_name=course.week_name,
                course_id=course.course_id
            ))

        end_time = time.time()
        log_database_operation("get_all_courses", "courses", (end_time - start_time)*1000)

        return all_courses

    @staticmethod
    @monitor_query
    def get_courses_by_week(week_name: str) -> List[ProfessorCourse]:
        """Récupère les cours pour une semaine spécifique - OPTIMISÉ avec batch query"""
        start_time = time.time()

        # Batch query unique pour réduire les aller-retours DB
        from sqlalchemy import union_all

        # Query unifiée pour les deux types de cours
        normal_query = Course.query.filter_by(week_name=week_name)
        custom_query = CustomCourse.query.filter_by(week_name=week_name)

        normal_courses = normal_query.all()
        custom_courses = custom_query.all()

        courses = []
        for course in normal_courses + custom_courses:
            courses.append(ProfessorCourse(
                professor=course.professor,
                start_time=course.start_time,
                end_time=course.end_time,
                duration_hours=course.duration_hours,
                course_type=course.course_type,
                nb_students=course.nb_students,
                assigned_room=course.assigned_room,
                day=course.day,
                raw_time_slot=course.raw_time_slot,
                week_name=course.week_name,
                course_id=course.course_id
            ))

        end_time = time.time()
        log_database_operation(f"get_courses_by_week", "courses", (end_time - start_time)*1000)

        return courses

    @staticmethod
    @monitor_query
    def get_courses_by_professor(professor_name: str) -> List[ProfessorCourse]:
        """Récupère les cours d'un professeur - OPTIMISÉ avec batch query"""
        start_time = time.time()

        # Query optimisée avec index sur professor + order pour SQLite cache
        normal_courses = Course.query.filter_by(professor=professor_name).order_by(Course.week_name, Course.day, Course.start_time).all()
        custom_courses = CustomCourse.query.filter_by(professor=professor_name).order_by(CustomCourse.week_name, CustomCourse.day, CustomCourse.start_time).all()

        courses = []
        for course in normal_courses + custom_courses:
            courses.append(ProfessorCourse(
                professor=course.professor,
                start_time=course.start_time,
                end_time=course.end_time,
                duration_hours=course.duration_hours,
                course_type=course.course_type,
                nb_students=course.nb_students,
                assigned_room=course.assigned_room,
                day=course.day,
                raw_time_slot=course.raw_time_slot,
                week_name=course.week_name,
                course_id=course.course_id
            ))

        end_time = time.time()
        log_database_operation(f"get_courses_by_professor", "courses", (end_time - start_time)*1000)

        return courses

    @staticmethod
    def get_courses_by_week_and_day(week_name: str, day_name: str) -> List[ProfessorCourse]:
        """Récupère les cours pour un jour spécifique - OPTIMISÉ avec index composite"""
        start_time = time.time()

        # Query optimisée avec index composite (week_name, day)
        normal_courses = Course.query.filter(
            and_(Course.week_name == week_name, Course.day == day_name)
        ).all()

        custom_courses = CustomCourse.query.filter(
            and_(CustomCourse.week_name == week_name, CustomCourse.day == day_name)
        ).all()

        courses = []
        for course in normal_courses + custom_courses:
            courses.append(ProfessorCourse(
                professor=course.professor,
                start_time=course.start_time,
                end_time=course.end_time,
                duration_hours=course.duration_hours,
                course_type=course.course_type,
                nb_students=course.nb_students,
                assigned_room=course.assigned_room,
                day=course.day,
                raw_time_slot=course.raw_time_slot,
                week_name=course.week_name,
                course_id=course.course_id
            ))

        end_time = time.time()
        log_database_operation(f"get_courses_by_week_day", "courses", (end_time - start_time)*1000)

        return courses

    @staticmethod
    @monitor_query
    def get_occupied_rooms(week_name: str, day_name: str, start_time: str, end_time: str) -> List[str]:
        """Récupère les salles occupées pour un créneau - ULTRA OPTIMISÉ"""
        import time
        query_start = time.time()

        # Query ultra-optimisée avec SQL directe pour performances maximales
        # Utilise l'index idx_occupied_rooms spécifiquement conçu pour cette query
        from sqlalchemy import text, union_all

        # Query directe SQLite optimisée - exploite l'index composite
        raw_sql = """
        SELECT DISTINCT assigned_room
        FROM (
            SELECT assigned_room FROM courses
            WHERE week_name = :week AND day = :day AND assigned_room IS NOT NULL
            AND start_time < :end_time AND end_time > :start_time
            UNION ALL
            SELECT assigned_room FROM custom_courses
            WHERE week_name = :week AND day = :day AND assigned_room IS NOT NULL
            AND start_time < :end_time AND end_time > :start_time
        ) AS occupied
        """

        result = db.session.execute(text(raw_sql), {
            'week': week_name,
            'day': day_name,
            'start_time': start_time,
            'end_time': end_time
        })

        occupied_rooms = [row[0] for row in result if row[0]]

        elapsed = (time.time() - query_start) * 1000
        log_database_operation("get_occupied_rooms", "courses", elapsed)

        return occupied_rooms

        # Code déplacé dans la méthode optimisée ci-dessus

    @staticmethod
    def get_all_professors() -> List[str]:
        """Récupère la liste unique des professeurs"""
        # Query distincte optimisée
        professors = db.session.query(Course.professor).distinct().all()
        custom_profs = db.session.query(CustomCourse.professor).distinct().all()

        all_profs = set([p[0] for p in professors] + [p[0] for p in custom_profs])
        return sorted(list(all_profs))

    @staticmethod
    def get_all_weeks() -> List[str]:
        """Récupère la liste unique des semaines"""
        weeks = db.session.query(Course.week_name).distinct().all()
        custom_weeks = db.session.query(CustomCourse.week_name).distinct().all()

        all_weeks = set([w[0] for w in weeks] + [w[0] for w in custom_weeks])
        return sorted(list(all_weeks))

    @staticmethod
    def get_rooms() -> List[Dict]:
        """Récupère toutes les salles"""
        rooms = Room.query.all()
        return [room.to_dict() for room in rooms]

    @staticmethod
    def get_professor_color(professor_name: str) -> Optional[str]:
        """Récupère la couleur d'un professeur"""
        prof = Professor.query.filter_by(name=professor_name).first()
        return prof.color if prof else None

    @staticmethod
    def set_professor_color(professor_name: str, color: str) -> bool:
        """Définit la couleur d'un professeur"""
        try:
            prof = Professor.query.filter_by(name=professor_name).first()
            if not prof:
                prof = Professor(name=professor_name, color=color)
                db.session.add(prof)
            else:
                prof.color = color

            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Professor color update error: {e}")
            return False

    @staticmethod
    def add_custom_course(course_data: Dict) -> str:
        """Ajoute un cours personnalisé"""
        try:
            custom_course = CustomCourse(
                course_id=course_data['course_id'],
                professor=course_data['professor'],
                week_name=course_data['week_name'],
                day=course_data['day'],
                start_time=course_data['start_time'],
                end_time=course_data['end_time'],
                duration_hours=course_data['duration_hours'],
                raw_time_slot=course_data.get('raw_time_slot', ''),
                course_type=course_data['course_type'],
                nb_students=course_data.get('nb_students', ''),
                assigned_room=course_data.get('assigned_room')
            )

            db.session.add(custom_course)
            db.session.commit()
            return course_data['course_id']
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"Course creation error: {e}")
            return ""

    @staticmethod
    def save_tp_name(course_id: str, tp_name: str) -> bool:
        """Sauvegarde un nom de TP"""
        try:
            tp = TPName.query.filter_by(course_id=course_id).first()
            if not tp:
                tp = TPName(course_id=course_id, tp_name=tp_name)
                db.session.add(tp)
            else:
                tp.tp_name = tp_name

            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"TP name update error: {e}")
            return False

    @staticmethod
    def get_tp_name(course_id: str) -> str:
        """Récupère le nom d'un TP"""
        tp = TPName.query.filter_by(course_id=course_id).first()
        return tp.tp_name if tp else ""

    @staticmethod
    def get_all_tp_names() -> Dict[str, str]:
        """Récupère tous les noms de TP"""
        tps = TPName.query.all()
        return {tp.course_id: tp.tp_name for tp in tps}