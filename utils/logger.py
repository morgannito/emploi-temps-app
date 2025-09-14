"""
Système de logging professionnel pour remplacer les prints
"""

import logging
import logging.handlers
import os
import sys
import time
import psutil
from datetime import datetime
from typing import Dict, Any
from functools import wraps
from threading import Lock
from collections import defaultdict, deque


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


class MetricsCollector:
    """Collecteur de métriques en temps réel"""

    def __init__(self):
        self._lock = Lock()
        self.request_metrics = defaultdict(list)
        self.error_metrics = defaultdict(int)
        self.performance_metrics = deque(maxlen=1000)
        self.system_metrics = {'start_time': time.time()}

    def record_request(self, endpoint, method, duration, status_code):
        """Enregistre les métriques d'une requête"""
        with self._lock:
            metric = {
                'timestamp': time.time(),
                'endpoint': endpoint,
                'method': method,
                'duration': duration,
                'status_code': status_code
            }
            self.request_metrics[endpoint].append(metric)
            self.performance_metrics.append(metric)

    def record_error(self, error_type):
        """Enregistre une erreur"""
        with self._lock:
            self.error_metrics[error_type] += 1

    def get_system_metrics(self):
        """Retourne les métriques système"""
        with self._lock:
            process = psutil.Process()
            return {
                'uptime': time.time() - self.system_metrics['start_time'],
                'cpu_percent': process.cpu_percent(),
                'memory_mb': process.memory_info().rss / 1024 / 1024,
                'memory_percent': process.memory_percent(),
                'total_requests': len(self.performance_metrics),
                'error_count': sum(self.error_metrics.values()),
                'avg_response_time': self._calculate_avg_response_time()
            }

    def _calculate_avg_response_time(self):
        """Calcule le temps de réponse moyen"""
        if not self.performance_metrics:
            return 0
        total = sum(m['duration'] for m in self.performance_metrics)
        return total / len(self.performance_metrics)

    def get_detailed_metrics(self):
        """Retourne des métriques détaillées"""
        with self._lock:
            return {
                'system': self.get_system_metrics(),
                'endpoints': dict(self.request_metrics),
                'errors': dict(self.error_metrics),
                'recent_requests': list(self.performance_metrics)[-100:]
            }


# Instance globale du collecteur de métriques
metrics_collector = MetricsCollector()


def log_request_metrics(f):
    """Décorateur pour logger automatiquement les métriques des requêtes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        status_code = 200

        try:
            result = f(*args, **kwargs)
            return result
        except Exception as e:
            status_code = 500
            metrics_collector.record_error(type(e).__name__)
            raise
        finally:
            duration = (time.time() - start_time) * 1000  # en ms
            endpoint = getattr(f, '__name__', 'unknown')
            metrics_collector.record_request(endpoint, 'GET', duration, status_code)

            # Log de performance
            log_performance(f"Request {endpoint}", duration)

    return wrapper


def log_security_event(event_type: str, severity: str, details: Dict[str, Any]):
    """Log spécialisé pour les événements de sécurité"""
    app_logger.warning(
        f"Security Event: {event_type}",
        extra={
            'event_type': event_type,
            'severity': severity,
            'security_event': True,
            **details
        }
    )


def log_business_event(operation: str, entity_type: str, entity_id: str, **kwargs):
    """Log spécialisé pour les événements métier"""
    app_logger.info(
        f"Business Event: {operation} on {entity_type}",
        extra={
            'operation': operation,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'business_event': True,
            **kwargs
        }
    )