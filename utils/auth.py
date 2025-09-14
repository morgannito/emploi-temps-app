"""
Système d'authentification basique pour l'administration
JWT tokens et gestion des sessions sécurisées
"""

import jwt
import secrets
from datetime import datetime, timedelta
from flask import request, jsonify, session, g
from functools import wraps
from utils.logger import app_logger
import hashlib
import os

# Secret key pour JWT - à générer aléatoirement en production
JWT_SECRET = os.environ.get('JWT_SECRET', secrets.token_hex(32))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_HOURS = 8

# Credentials admin par défaut (à remplacer par une vraie base d'utilisateurs)
DEFAULT_ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
DEFAULT_ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH',
    hashlib.sha256('admin123'.encode()).hexdigest())


class AuthManager:
    """Gestionnaire d'authentification"""

    @staticmethod
    def verify_credentials(username: str, password: str) -> bool:
        """Vérifie les identifiants utilisateur"""
        if not username or not password:
            return False

        # Hash du mot de passe fourni
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Vérification simple (à remplacer par une vraie DB en production)
        is_valid = (
            username == DEFAULT_ADMIN_USERNAME and
            password_hash == DEFAULT_ADMIN_PASSWORD_HASH
        )

        if is_valid:
            app_logger.info(f"Successful authentication for user: {username}")
        else:
            app_logger.warning(f"Failed authentication attempt for user: {username}")

        return is_valid

    @staticmethod
    def generate_token(username: str) -> str:
        """Génère un token JWT"""
        payload = {
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
            'iat': datetime.utcnow(),
            'role': 'admin'  # Rôle par défaut
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        app_logger.info(f"JWT token generated for user: {username}")
        return token

    @staticmethod
    def verify_token(token: str) -> dict:
        """Vérifie et décode un token JWT"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            app_logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            app_logger.warning("Invalid token")
            return None

    @staticmethod
    def get_current_user() -> dict:
        """Récupère l'utilisateur actuel depuis le token"""
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return None

        try:
            # Format: "Bearer <token>"
            token_type, token = auth_header.split(' ', 1)
            if token_type.lower() != 'bearer':
                return None

            payload = AuthManager.verify_token(token)
            return payload
        except (ValueError, AttributeError):
            return None


def login_required(f):
    """Décorateur pour protéger les routes nécessitant une authentification"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = AuthManager.get_current_user()

        if not user:
            app_logger.warning(f"Unauthorized access attempt to: {request.endpoint}")
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401

        g.current_user = user
        return f(*args, **kwargs)

    return wrapper


def admin_required_auth(f):
    """Décorateur pour les routes d'administration avec authentification JWT"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = AuthManager.get_current_user()

        if not user or user.get('role') != 'admin':
            app_logger.warning(f"Admin access denied to: {request.endpoint}")
            return jsonify({
                'success': False,
                'error': 'Admin privileges required'
            }), 403

        g.current_user = user
        return f(*args, **kwargs)

    return wrapper


class AuthAPI:
    """API d'authentification"""

    @staticmethod
    def login():
        """Endpoint de connexion"""
        try:
            data = request.get_json()

            if not data:
                return jsonify({
                    'success': False,
                    'error': 'JSON data required'
                }), 400

            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return jsonify({
                    'success': False,
                    'error': 'Username and password required'
                }), 400

            # Limitation du nombre de tentatives
            client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
            app_logger.info(f"Login attempt from {client_ip} for user: {username}")

            if AuthManager.verify_credentials(username, password):
                token = AuthManager.generate_token(username)

                return jsonify({
                    'success': True,
                    'token': token,
                    'user': {
                        'username': username,
                        'role': 'admin'
                    },
                    'expires_in': JWT_EXPIRY_HOURS * 3600
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid credentials'
                }), 401

        except Exception as e:
            app_logger.error(f"Login error: {e}")
            return jsonify({
                'success': False,
                'error': 'Internal server error'
            }), 500

    @staticmethod
    def verify():
        """Endpoint de vérification du token"""
        user = AuthManager.get_current_user()

        if user:
            return jsonify({
                'success': True,
                'user': {
                    'username': user.get('username'),
                    'role': user.get('role')
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid or expired token'
            }), 401

    @staticmethod
    def logout():
        """Endpoint de déconnexion (côté client principalement)"""
        # En JWT, la déconnexion est principalement côté client
        # On peut implémenter une blacklist de tokens si nécessaire

        app_logger.info("User logout requested")
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })


def init_auth_routes(app):
    """Initialise les routes d'authentification"""

    @app.route('/api/auth/login', methods=['POST'])
    def auth_login():
        return AuthAPI.login()

    @app.route('/api/auth/verify', methods=['GET'])
    def auth_verify():
        return AuthAPI.verify()

    @app.route('/api/auth/logout', methods=['POST'])
    def auth_logout():
        return AuthAPI.logout()

    app_logger.info("Authentication routes initialized")