from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional


class BaseController:
    """Contrôleur de base avec utilitaires communs"""

    def __init__(self, name: str, url_prefix: str = None):
        self.blueprint = Blueprint(name, __name__, url_prefix=url_prefix)
        self._register_routes()

    def _register_routes(self):
        """À implémenter dans les contrôleurs spécialisés"""
        pass

    def get_json_data(self) -> Dict[str, Any]:
        """Récupère les données JSON de la requête"""
        return request.get_json() or {}

    def success_response(self, data: Any = None, message: str = None) -> Dict[str, Any]:
        """Réponse de succès standardisée"""
        response = {'success': True}
        if data is not None:
            response['data'] = data
        if message:
            response['message'] = message
        return jsonify(response)

    def error_response(self, error: str, status_code: int = 400) -> tuple:
        """Réponse d'erreur standardisée"""
        return jsonify({
            'success': False,
            'error': error
        }), status_code

    def validate_required_fields(self, data: Dict[str, Any], required_fields: list) -> Optional[str]:
        """Valide la présence des champs requis"""
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return f"Champs manquants: {', '.join(missing_fields)}"
        return None