from typing import Dict


class ProfessorAPIService:
    """Service pour les APIs de gestion des professeurs"""

    def __init__(self, schedule_manager):
        self.schedule_manager = schedule_manager

    def add_professor(self, data: Dict) -> Dict:
        """API pour ajouter un nouveau professeur"""
        prof_name = data.get('name', '').strip()
        if not prof_name:
            return {'success': False, 'error': 'Le nom du professeur est requis.', 'status_code': 400}

        success = self.schedule_manager.add_professor(prof_name)
        if success:
            return {'success': True}
        else:
            return {'success': False, 'error': 'Ce professeur existe déjà.', 'status_code': 409}

    def update_prof_color(self, data: Dict) -> Dict:
        """API pour mettre à jour la couleur d'un professeur"""
        prof_name = data.get('name')
        color = data.get('color')
        if not prof_name or not color:
            return {'success': False, 'error': 'Données manquantes.', 'status_code': 400}

        success = self.schedule_manager.update_prof_color(prof_name, color)
        if success:
            return {'success': True}
        else:
            return {'success': False, 'error': 'Couleur invalide.', 'status_code': 400}

    def delete_professor(self, data: Dict) -> Dict:
        """API pour supprimer un professeur"""
        prof_name = data.get('name')
        if not prof_name:
            return {'success': False, 'error': 'Le nom du professeur est requis.', 'status_code': 400}

        success = self.schedule_manager.delete_professor(prof_name)
        if success:
            # Forcer la synchronisation des données pour tous les workers
            self.schedule_manager.force_sync_data()
            return {'success': True}
        else:
            return {'success': False, 'error': 'Professeur non trouvé.', 'status_code': 404}