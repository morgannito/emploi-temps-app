"""
Gestionnaire d'erreurs global avancé
Architecture clean avec monitoring et alertes
"""

import traceback
from datetime import datetime
from functools import wraps
from flask import jsonify, render_template, request, g
from utils.logger import app_logger

class ErrorSeverity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ApplicationError(Exception):
    """Exception de base pour l'application"""
    def __init__(self, message, error_code=None, severity=ErrorSeverity.MEDIUM):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.timestamp = datetime.now()
        super().__init__(self.message)

class ValidationError(ApplicationError):
    """Erreur de validation des données"""
    def __init__(self, message, field=None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR", ErrorSeverity.LOW)

class BusinessLogicError(ApplicationError):
    """Erreur de logique métier"""
    def __init__(self, message):
        super().__init__(message, "BUSINESS_ERROR", ErrorSeverity.MEDIUM)

class SecurityError(ApplicationError):
    """Erreur de sécurité"""
    def __init__(self, message):
        super().__init__(message, "SECURITY_ERROR", ErrorSeverity.HIGH)

class SystemError(ApplicationError):
    """Erreur système critique"""
    def __init__(self, message):
        super().__init__(message, "SYSTEM_ERROR", ErrorSeverity.CRITICAL)

class ErrorHandler:
    """Gestionnaire d'erreurs centralisé"""

    def __init__(self, app=None):
        self.app = app
        self.error_stats = {}
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialise le gestionnaire d'erreurs avec l'app Flask"""
        app.register_error_handler(ApplicationError, self.handle_application_error)
        app.register_error_handler(ValidationError, self.handle_validation_error)
        app.register_error_handler(BusinessLogicError, self.handle_business_error)
        app.register_error_handler(SecurityError, self.handle_security_error)
        app.register_error_handler(SystemError, self.handle_system_error)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(500, self.handle_internal_error)
        app.register_error_handler(Exception, self.handle_generic_error)

    def _log_error(self, error, severity, context=None):
        """Log centralisé des erreurs avec contexte"""
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'severity': severity,
            'error_message': str(error),
            'type': type(error).__name__,
            'traceback': traceback.format_exc() if hasattr(error, '__traceback__') else None,
            'user': getattr(g, 'current_user', {}).get('username', 'anonymous'),
            'ip': request.environ.get('HTTP_X_REAL_IP', request.remote_addr),
            'endpoint': request.endpoint,
            'method': request.method,
            'url': request.url,
            'context': context or {}
        }

        # Statistiques
        error_key = f"{type(error).__name__}:{severity}"
        self.error_stats[error_key] = self.error_stats.get(error_key, 0) + 1

        # Log selon la gravité
        if severity == ErrorSeverity.CRITICAL:
            app_logger.critical("CRITICAL ERROR", extra=error_info)
        elif severity == ErrorSeverity.HIGH:
            app_logger.error("HIGH SEVERITY ERROR", extra=error_info)
        elif severity == ErrorSeverity.MEDIUM:
            app_logger.warning("MEDIUM SEVERITY ERROR", extra=error_info)
        else:
            app_logger.info("LOW SEVERITY ERROR", extra=error_info)

    def handle_application_error(self, error):
        """Gestion des erreurs applicatives"""
        self._log_error(error, error.severity)

        if request.is_json:
            return jsonify({
                'success': False,
                'error_code': error.error_code,
                'message': error.message,
                'timestamp': error.timestamp.isoformat(),
                'severity': error.severity
            }), 400

        return render_template('error.html',
                             error_message=error.message,
                             error_code=error.error_code), 400

    def handle_validation_error(self, error):
        """Gestion spécifique des erreurs de validation"""
        self._log_error(error, ErrorSeverity.LOW, {'field': error.field})

        if request.is_json:
            return jsonify({
                'success': False,
                'error_type': 'validation',
                'message': error.message,
                'field': error.field
            }), 422

        return render_template('error.html',
                             error_message=f"Erreur de validation: {error.message}"), 422

    def handle_business_error(self, error):
        """Gestion des erreurs de logique métier"""
        self._log_error(error, ErrorSeverity.MEDIUM)

        if request.is_json:
            return jsonify({
                'success': False,
                'error_type': 'business_logic',
                'message': error.message
            }), 409

        return render_template('error.html',
                             error_message=f"Erreur métier: {error.message}"), 409

    def handle_security_error(self, error):
        """Gestion des erreurs de sécurité"""
        self._log_error(error, ErrorSeverity.HIGH, {
            'suspicious_activity': True,
            'requires_investigation': True
        })

        if request.is_json:
            return jsonify({
                'success': False,
                'error_type': 'security',
                'message': 'Accès non autorisé'
            }), 403

        return render_template('error.html',
                             error_message="Accès non autorisé"), 403

    def handle_system_error(self, error):
        """Gestion des erreurs système critiques"""
        self._log_error(error, ErrorSeverity.CRITICAL)

        if request.is_json:
            return jsonify({
                'success': False,
                'error_type': 'system',
                'message': 'Erreur système critique'
            }), 500

        return render_template('error.html',
                             error_message="Service temporairement indisponible"), 500

    def handle_not_found(self, error):
        """Gestion des erreurs 404"""
        self._log_error(error, ErrorSeverity.LOW)

        if request.is_json:
            return jsonify({
                'success': False,
                'error_type': 'not_found',
                'message': 'Ressource non trouvée'
            }), 404

        return render_template('error.html',
                             error_message="Page non trouvée"), 404

    def handle_internal_error(self, error):
        """Gestion des erreurs internes 500"""
        self._log_error(error, ErrorSeverity.HIGH)

        if request.is_json:
            return jsonify({
                'success': False,
                'error_type': 'internal',
                'message': 'Erreur interne du serveur'
            }), 500

        return render_template('error.html',
                             error_message="Erreur interne du serveur"), 500

    def handle_generic_error(self, error):
        """Gestionnaire générique pour toutes les autres erreurs"""
        self._log_error(error, ErrorSeverity.HIGH, {
            'unhandled_exception': True
        })

        if request.is_json:
            return jsonify({
                'success': False,
                'error_type': 'unexpected',
                'message': 'Erreur inattendue'
            }), 500

        return render_template('error.html',
                             error_message="Une erreur inattendue s'est produite"), 500

    def get_error_stats(self):
        """Retourne les statistiques d'erreurs"""
        return {
            'stats': self.error_stats,
            'total_errors': sum(self.error_stats.values()),
            'timestamp': datetime.now().isoformat()
        }

def handle_errors(severity=ErrorSeverity.MEDIUM):
    """Décorateur pour la gestion automatique des erreurs"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except ApplicationError:
                # Les erreurs applicatives sont déjà gérées
                raise
            except ValueError as e:
                raise ValidationError(f"Valeur invalide: {str(e)}")
            except PermissionError as e:
                raise SecurityError(f"Permission refusée: {str(e)}")
            except Exception as e:
                if severity == ErrorSeverity.CRITICAL:
                    raise SystemError(f"Erreur critique: {str(e)}")
                else:
                    raise ApplicationError(f"Erreur: {str(e)}", severity=severity)

        return wrapper
    return decorator

# Instance globale
error_handler = ErrorHandler()