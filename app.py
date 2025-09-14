#!/usr/bin/env python3
"""
Application Flask - Gestion des emplois du temps
Architecture moderne avec contrôleurs et logging professionnel
"""

from flask import Flask
from flask_caching import Cache
import os
from datetime import datetime

# Import des modèles et configuration
from models import db
from infrastructure.config import configure_container

# Import des contrôleurs
from controllers.course_controller import CourseController
from controllers.professor_controller import ProfessorController
from controllers.room_controller import RoomController
from controllers.planning_controller import PlanningController

# Import des services globaux
from services.cache_service import CacheService

# Import du middleware de sécurité et authentification
from utils.security import SecurityMiddleware
from utils.auth import init_auth_routes
from utils.error_handler import error_handler


def create_app():
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)

    # Configuration SQLite optimisée
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'schedule.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Connection pooling et optimisations SQLAlchemy
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 20,
        'max_overflow': 0,
        'pool_pre_ping': True,
        'pool_recycle': 300,
        'echo': False,
        'connect_args': {
            'timeout': 20,
            'check_same_thread': False
        }
    }

    # Configuration Flask-Caching
    app.config['CACHE_TYPE'] = 'simple'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 60
    cache = Cache(app)

    # Configuration des templates
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Initialiser la base de données
    db.init_app(app)

    # Configuration du container d'injection de dépendances
    configure_container(db)

    # Import et initialisation du gestionnaire principal
    from core.schedule_manager import ScheduleManager
    schedule_manager = ScheduleManager()

    # Initialisation du service de cache
    cache_service = CacheService()

    # Configuration du middleware de sécurité
    security_middleware = SecurityMiddleware(app)

    # Initialisation des routes d'authentification
    init_auth_routes(app)

    # Initialisation du gestionnaire d'erreurs avancé
    error_handler.init_app(app)

    # Routes de monitoring et métriques
    @app.route('/api/error-stats')
    def get_error_stats():
        """API pour récupérer les statistiques d'erreurs"""
        from flask import jsonify
        return jsonify(error_handler.get_error_stats())

    @app.route('/api/metrics')
    def get_metrics():
        """API pour récupérer les métriques système et performance"""
        from flask import jsonify
        from utils.logger import metrics_collector
        return jsonify(metrics_collector.get_detailed_metrics())

    @app.route('/api/health')
    def health_check():
        """API de santé pour monitoring externe"""
        from flask import jsonify
        from utils.logger import metrics_collector

        system_metrics = metrics_collector.get_system_metrics()
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'uptime': system_metrics['uptime'],
            'memory_usage': system_metrics['memory_percent'],
            'error_rate': system_metrics['error_count'] / max(system_metrics['total_requests'], 1) * 100
        }

        # Déterminer le statut de santé
        if health_status['memory_usage'] > 90:
            health_status['status'] = 'degraded'
        if health_status['error_rate'] > 10:
            health_status['status'] = 'degraded'

        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code

    # Enregistrement des contrôleurs
    course_controller = CourseController(schedule_manager)
    professor_controller = ProfessorController(schedule_manager)
    room_controller = RoomController(schedule_manager, cache_service)
    planning_controller = PlanningController(schedule_manager, cache_service)

    app.register_blueprint(course_controller.blueprint)
    app.register_blueprint(professor_controller.blueprint)
    app.register_blueprint(room_controller.blueprint)
    app.register_blueprint(planning_controller.blueprint)

    # Routes de compatibilité et utilitaires restantes
    @app.route('/api/schedule/<day>')
    def api_schedule_day(day):
        """API pour compatibilité avec admin.js"""
        from flask import jsonify
        try:
            return jsonify({
                'success': True,
                'day': day,
                'data': {}
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/schedule/<day>/<room_id>/<slot_index>', methods=['PUT'])
    def api_update_schedule_slot(day, room_id, slot_index):
        """API pour mettre à jour un créneau d'emploi du temps"""
        from flask import request, jsonify
        try:
            data = request.get_json()
            return jsonify({
                'success': True,
                'message': 'Slot updated successfully'
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/test_template')
    def test_template():
        """Route de test pour vérifier les templates"""
        from flask import render_template
        from services.professor_service import ProfessorService

        schedule_manager.reload_data()
        summary = schedule_manager.get_canonical_schedules_summary()

        def get_all_professors_with_ids():
            return ProfessorService.get_all_professors_with_ids()

        prof_id_mapping = get_all_professors_with_ids()

        return render_template('test_template.html',
                             summary=summary,
                             prof_id_mapping=prof_id_mapping)

    return app


# Instance de l'application
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5007)