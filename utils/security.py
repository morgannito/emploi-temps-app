"""
Middleware et utilitaires de sécurité enterprise
Headers de sécurité, validation, et protection contre les attaques
"""

from functools import wraps
from flask import request, abort, g
from werkzeug.exceptions import TooManyRequests
import time
import secrets
from collections import defaultdict
from utils.logger import app_logger
import re
from html import escape
import bleach


class SecurityHeaders:
    """Gestionnaire des headers de sécurité HTTP"""

    @staticmethod
    def add_security_headers(response):
        """Ajoute tous les headers de sécurité essentiels"""

        # Content Security Policy - Protection XSS
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.jsdelivr.net unpkg.com; "
            "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
            "img-src 'self' data: blob:; "
            "font-src 'self' fonts.gstatic.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )
        response.headers['Content-Security-Policy'] = csp

        # Strict Transport Security - Force HTTPS
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        # Protection contre le clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Protection MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # XSS Protection (legacy browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Referrer Policy - Contrôle des informations envoyées
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy - Contrôle des APIs
        permissions = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        response.headers['Permissions-Policy'] = permissions

        # Cache Control pour les pages sensibles
        if request.endpoint and ('admin' in request.endpoint or 'edit' in request.endpoint):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'

        # Server header masking
        response.headers['Server'] = 'ISA-ScheduleApp/2.1'

        app_logger.debug(f"Security headers applied for {request.endpoint}")
        return response


class RateLimiter:
    """Rate limiter en mémoire pour protection DoS"""

    def __init__(self):
        self.requests = defaultdict(list)
        self.blocked_ips = {}

    def is_rate_limited(self, key: str, limit: int = 100, window: int = 3600):
        """Vérifie si une clé (IP) dépasse la limite"""
        now = time.time()

        # Nettoyer les anciennes requêtes
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if timestamp > now - window
        ]

        # Vérifier si l'IP est temporairement bloquée
        if key in self.blocked_ips:
            if now < self.blocked_ips[key]:
                app_logger.warning(f"Blocked IP attempt: {key}")
                return True
            else:
                del self.blocked_ips[key]

        # Compter les requêtes dans la fenêtre
        request_count = len(self.requests[key])

        if request_count >= limit:
            # Bloquer l'IP pour 15 minutes
            self.blocked_ips[key] = now + 900
            app_logger.warning(f"Rate limit exceeded: {key} ({request_count} requests)")
            return True

        # Enregistrer cette requête
        self.requests[key].append(now)
        return False


class InputValidator:
    """Validation et sanitisation des entrées utilisateur"""

    @staticmethod
    def sanitize_html(content: str) -> str:
        """Nettoie le contenu HTML"""
        if not content:
            return ""

        # Tags autorisés pour l'affichage des emplois du temps
        allowed_tags = ['b', 'i', 'u', 'br', 'p', 'span', 'div']
        allowed_attributes = {
            'span': ['class'],
            'div': ['class']
        }

        cleaned = bleach.clean(
            content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True
        )

        return cleaned

    @staticmethod
    def validate_course_id(course_id: str) -> bool:
        """Valide un ID de cours"""
        if not course_id or len(course_id) > 100:
            return False

        # Pattern: lettres, chiffres, tirets, underscores
        pattern = r'^[a-zA-Z0-9_-]+$'
        return bool(re.match(pattern, course_id))

    @staticmethod
    def validate_professor_name(name: str) -> bool:
        """Valide un nom de professeur"""
        if not name or len(name) > 100:
            return False

        # Lettres, espaces, tirets, apostrophes
        pattern = r'^[a-zA-ZÀ-ÿ\s\'-]+$'
        return bool(re.match(pattern, name))

    @staticmethod
    def validate_room_id(room_id: str) -> bool:
        """Valide un ID de salle"""
        if not room_id or len(room_id) > 50:
            return False

        # Lettres, chiffres, tirets
        pattern = r'^[a-zA-Z0-9-]+$'
        return bool(re.match(pattern, room_id))

    @staticmethod
    def validate_time_slot(time_slot: str) -> bool:
        """Valide un créneau horaire"""
        if not time_slot:
            return False

        # Pattern: "HH:MM-HH:MM"
        pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]-([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
        return bool(re.match(pattern, time_slot))

    @staticmethod
    def validate_week_name(week_name: str) -> bool:
        """Valide un nom de semaine"""
        if not week_name or len(week_name) > 50:
            return False

        # Pattern: "Semaine X Y" où X est un nombre et Y une lettre
        pattern = r'^Semaine \d{1,2} [A-Z]$'
        return bool(re.match(pattern, week_name))


class SecurityMiddleware:
    """Middleware central de sécurité"""

    def __init__(self, app=None):
        self.rate_limiter = RateLimiter()
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialise le middleware avec l'app Flask"""

        @app.before_request
        def security_before_request():
            """Contrôles de sécurité avant chaque requête"""

            # Rate limiting basique
            client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

            # Limites différentes selon l'endpoint
            if request.endpoint and 'api' in request.endpoint:
                limit = 200  # API plus permissive
            else:
                limit = 100  # Interface web

            if self.rate_limiter.is_rate_limited(client_ip, limit=limit):
                app_logger.warning(f"Rate limit block: {client_ip} to {request.endpoint}")
                abort(429)  # Too Many Requests

            # Validation des headers dangereux
            dangerous_headers = ['X-Forwarded-Host', 'X-Original-URL', 'X-Rewrite-URL']
            for header in dangerous_headers:
                if header in request.headers:
                    app_logger.warning(f"Dangerous header detected: {header} from {client_ip}")
                    abort(400)

            # Protection contre les requêtes trop larges
            if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
                app_logger.warning(f"Request too large: {request.content_length} bytes from {client_ip}")
                abort(413)

            app_logger.debug(f"Security check passed: {client_ip} -> {request.endpoint}")

        @app.after_request
        def security_after_request(response):
            """Ajoute les headers de sécurité après chaque réponse"""
            return SecurityHeaders.add_security_headers(response)


def require_valid_input(validation_func):
    """Décorateur pour valider les entrées d'API"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = request.get_json(silent=True)
                if data and not validation_func(data):
                    app_logger.warning(f"Invalid input detected: {request.endpoint}")
                    abort(400, description="Invalid input data")
            return f(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(f):
    """Décorateur pour protéger les endpoints d'administration"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Pour l'instant, vérification basique
        # Intégration avec le système JWT existant via utils.auth

        client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

        # Whitelist d'IPs pour admin (à configurer selon l'environnement)
        admin_ips = ['127.0.0.1', '::1', '192.168.1.0/24']

        # Log de l'accès admin
        app_logger.info(f"Admin access attempt: {client_ip} -> {request.endpoint}")

        # Vérification JWT via middleware intégré
        from utils.auth import verify_jwt_token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if token and not verify_jwt_token(token):
            abort(401)

        return f(*args, **kwargs)
    return wrapper


def generate_csrf_token():
    """Génère un token CSRF"""
    if 'csrf_token' not in g:
        g.csrf_token = secrets.token_hex(16)
    return g.csrf_token


def validate_csrf_token(token):
    """Valide un token CSRF"""
    return token and hasattr(g, 'csrf_token') and token == g.csrf_token