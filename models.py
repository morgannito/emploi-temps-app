from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Index
from datetime import datetime

db = SQLAlchemy()


class Course(db.Model):
    """Modèle de cours optimisé avec indexes stratégiques"""
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # Champs principaux avec indexes pour queries fréquentes
    professor = db.Column(db.String(100), nullable=False, index=True)
    week_name = db.Column(db.String(50), nullable=False, index=True)
    day = db.Column(db.String(20), nullable=False, index=True)

    # Horaires
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    raw_time_slot = db.Column(db.String(50))

    # Détails du cours
    course_type = db.Column(db.String(100), nullable=False)
    nb_students = db.Column(db.String(20))
    assigned_room = db.Column(db.String(50), index=True)

    # Métadonnées
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Index composites pour queries complexes
    __table_args__ = (
        Index('idx_week_day', 'week_name', 'day'),
        Index('idx_prof_week', 'professor', 'week_name'),
        Index('idx_week_day_time', 'week_name', 'day', 'start_time'),
        Index('idx_room_week_day', 'assigned_room', 'week_name', 'day'),
        # Index ultra-spécialisé pour get_occupied_rooms
        Index('idx_occupied_rooms', 'week_name', 'day', 'assigned_room', 'start_time', 'end_time'),
    )

    def to_dict(self):
        """Convertit en dictionnaire compatible avec l'ancien système"""
        return {
            'course_id': self.course_id,
            'professor': self.professor,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_hours': self.duration_hours,
            'course_type': self.course_type,
            'nb_students': self.nb_students,
            'assigned_room': self.assigned_room,
            'day': self.day,
            'raw_time_slot': self.raw_time_slot,
            'week_name': self.week_name
        }

    def __repr__(self):
        return f'<Course {self.course_id}: {self.professor} - {self.course_type}>'


class Room(db.Model):
    """Modèle des salles"""
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.room_id,
            'nom': self.name,
            'capacite': self.capacity
        }


class Professor(db.Model):
    """Modèle des professeurs avec données de couleur et horaires"""
    __tablename__ = 'professors'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    color = db.Column(db.String(7))  # Couleur hex #RRGGBB
    working_days = db.Column(db.Text)  # JSON des jours de travail
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            'name': self.name,
            'color': self.color,
            'working_days': json.loads(self.working_days) if self.working_days else []
        }


class CustomCourse(db.Model):
    """Modèle des cours personnalisés (TPs)"""
    __tablename__ = 'custom_courses'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(100), unique=True, nullable=False, index=True)

    professor = db.Column(db.String(100), nullable=False, index=True)
    week_name = db.Column(db.String(50), nullable=False, index=True)
    day = db.Column(db.String(20), nullable=False, index=True)

    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)
    duration_hours = db.Column(db.Float, nullable=False)
    raw_time_slot = db.Column(db.String(50))

    course_type = db.Column(db.String(100), nullable=False)
    nb_students = db.Column(db.String(20))
    assigned_room = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'course_id': self.course_id,
            'professor': self.professor,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_hours': self.duration_hours,
            'course_type': self.course_type,
            'nb_students': self.nb_students,
            'assigned_room': self.assigned_room,
            'day': self.day,
            'raw_time_slot': self.raw_time_slot,
            'week_name': self.week_name
        }


class TPName(db.Model):
    """Modèle des noms personnalisés de TP"""
    __tablename__ = 'tp_names'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    tp_name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)