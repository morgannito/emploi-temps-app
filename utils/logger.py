"""
Système de logging professionnel pour remplacer les prints
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Dict, Any


class StructuredFormatter(logging.Formatter):
    """Formatter structuré pour les logs en production"""

    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'module': record.name,
            'message': record.getMessage(),
            'function': record.funcName,
            'line': record.lineno
        }

        # Ajouter des champs contextuels si présents
        if hasattr(record, 'course_id'):
            log_obj['course_id'] = record.course_id
        if hasattr(record, 'professor'):
            log_obj['professor'] = record.professor
        if hasattr(record, 'room_id'):
            log_obj['room_id'] = record.room_id
        if hasattr(record, 'execution_time'):
            log_obj['execution_time_ms'] = record.execution_time

        return str(log_obj)


def setup_logger(name: str = "emploi_temps") -> logging.Logger:
    """Configure un logger professionnel"""

    logger = logging.getLogger(name)

    # Éviter la double configuration
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Créer le répertoire logs s'il n'existe pas
    os.makedirs('logs', exist_ok=True)

    # Handler pour fichier avec rotation
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/application.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(StructuredFormatter())

    # Handler pour console (développement)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)

    # Formatter simple pour la console
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# Logger global pour l'application
app_logger = setup_logger()


def log_performance(operation: str, execution_time: float, **kwargs):
    """Log spécialisé pour les performances"""
    app_logger.info(
        f"Performance: {operation}",
        extra={'execution_time': execution_time, **kwargs}
    )


def log_course_operation(operation: str, course_id: str, **kwargs):
    """Log spécialisé pour les opérations sur les cours"""
    app_logger.info(
        f"Course {operation}: {course_id}",
        extra={'course_id': course_id, **kwargs}
    )


def log_room_conflict(course_id: str, room_id: str, conflict_type: str):
    """Log spécialisé pour les conflits de salles"""
    app_logger.warning(
        f"Room conflict detected: {conflict_type}",
        extra={
            'course_id': course_id,
            'room_id': room_id,
            'conflict_type': conflict_type
        }
    )


def log_database_operation(operation: str, table: str, duration: float):
    """Log spécialisé pour les opérations de base de données"""
    app_logger.info(
        f"DB {operation} on {table}",
        extra={
            'operation': operation,
            'table': table,
            'execution_time': duration
        }
    )