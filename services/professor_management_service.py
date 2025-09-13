import hashlib
import json
import os
from typing import Dict, List, Any


class ProfessorManagementService:
    """Service pour la gestion des professeurs et leurs données"""

    # Couleurs disponibles pour les professeurs
    PROF_COLORS = ["#e57373", "#81c784", "#64b5f6", "#fff176", "#ffb74d", "#ba68c8", "#4db6ac", "#f06292", "#a1887f"]

    def __init__(self, file_service):
        """
        Initialise le service avec une référence au FileManagementService

        Args:
            file_service: Instance de FileManagementService
        """
        self.file_service = file_service

    def get_prof_color(self, prof_name: str, prof_data: Dict) -> str:
        """Récupère la couleur d'un prof, ou en assigne une nouvelle."""
        if prof_name in prof_data and 'color' in prof_data[prof_name]:
            return prof_data[prof_name]['color']

        # Assigner une couleur par défaut si aucune n'est trouvée
        color_index = hash(prof_name) % len(self.PROF_COLORS)
        new_color = self.PROF_COLORS[color_index]

        # Mettre à jour la structure de données et la sauvegarder
        if prof_name not in prof_data:
            prof_data[prof_name] = {}
        prof_data[prof_name]['color'] = new_color

        self.file_service.save_prof_data(prof_data)
        return new_color

    def update_prof_color(self, prof_name: str, color: str, prof_data: Dict) -> bool:
        """Met à jour la couleur d'un professeur."""
        if color not in self.PROF_COLORS:
            return False  # Couleur invalide

        if prof_name not in prof_data:
            prof_data[prof_name] = {}

        prof_data[prof_name]['color'] = color
        self.file_service.save_prof_data(prof_data)
        return True

    def add_professor(self, prof_name: str, canonical_schedules: Dict) -> bool:
        """Ajoute un nouveau professeur avec un emploi du temps vide."""
        if prof_name in canonical_schedules:
            return False  # Le professeur existe déjà

        canonical_schedules[prof_name] = {'courses': [], 'color': None, 'preferences': {}}

        # Auto-générer ID
        prof_id = hashlib.md5(prof_name.encode()).hexdigest()[:8]
        prof_id_mapping_file = "data/prof_id_mapping.json"

        # Charger et mettre à jour le mapping des IDs
        if os.path.exists(prof_id_mapping_file):
            with open(prof_id_mapping_file, "r", encoding="utf-8") as f:
                prof_id_mapping = json.load(f)
        else:
            prof_id_mapping = {}

        prof_id_mapping[prof_name] = prof_id

        # Sauvegarder le mapping des IDs
        os.makedirs("data", exist_ok=True)
        with open(prof_id_mapping_file, "w", encoding="utf-8") as f:
            json.dump(prof_id_mapping, f, indent=2, ensure_ascii=False)

        # Sauvegarder les emplois du temps canoniques
        self.file_service.save_canonical_schedules(canonical_schedules)
        return True

    def delete_professor(self, prof_name: str, canonical_schedules: Dict) -> bool:
        """Supprime un professeur et son emploi du temps."""
        if prof_name in canonical_schedules:
            del canonical_schedules[prof_name]
            # Sauvegarder les modifications
            self.file_service.save_canonical_schedules(canonical_schedules)
            return True
        return False  # Le professeur n'a pas été trouvé

    def get_prof_schedule(self, prof_name: str, canonical_schedules: Dict) -> List[Dict]:
        """Récupère l'emploi du temps canonique d'un professeur."""
        prof_data = canonical_schedules.get(prof_name, {})
        return prof_data.get('courses', []) if isinstance(prof_data, dict) else prof_data

    def update_prof_schedule(self, prof_name: str, courses: List[Dict], canonical_schedules: Dict) -> bool:
        """Met à jour l'emploi du temps canonique d'un professeur."""
        if prof_name not in canonical_schedules:
            canonical_schedules[prof_name] = {'courses': [], 'color': None, 'preferences': {}}
        canonical_schedules[prof_name]['courses'] = courses
        self.file_service.save_canonical_schedules(canonical_schedules)
        return True

    def get_canonical_schedules_summary(self, canonical_schedules: Dict, prof_data: Dict) -> Dict:
        """Calcule un résumé des heures de cours pour chaque prof."""
        summary = {}
        for prof, prof_courses in canonical_schedules.items():
            total_hours = 0
            days_summary = {}

            courses = prof_courses.get('courses', []) if isinstance(prof_courses, dict) else prof_courses

            for course in courses:
                day = course.get('day', 'N/A')
                duration = course.get('duration_hours', 0)
                total_hours += duration

                if day not in days_summary:
                    days_summary[day] = {'count': 0, 'hours': 0}
                days_summary[day]['count'] += 1
                days_summary[day]['hours'] += duration

            summary[prof] = {
                'total_hours': f"{total_hours:.1f}h",
                'days': days_summary,
                'color': self.get_prof_color(prof, prof_data)
            }

        # Tri alphabétique des professeurs
        sorted_summary = dict(sorted(summary.items()))
        return sorted_summary

    def get_prof_id_mapping(self) -> Dict[str, str]:
        """Récupère le mapping des IDs de professeurs."""
        prof_id_mapping_file = "data/prof_id_mapping.json"
        if os.path.exists(prof_id_mapping_file):
            with open(prof_id_mapping_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_prof_name_mapping(self) -> Dict[str, str]:
        """Récupère le mapping inverse des noms de professeurs."""
        prof_id_mapping = self.get_prof_id_mapping()
        return {prof_id: prof_name for prof_name, prof_id in prof_id_mapping.items()}

    def normalize_professor_name(self, name: str) -> str:
        """Normalise le nom d'un professeur pour la recherche."""
        if not name:
            return ""

        # Supprimer les espaces en début/fin
        name = name.strip()

        # Remplacer les espaces multiples par un seul
        import re
        name = re.sub(r'\s+', ' ', name)

        return name

    def find_professor_by_partial_name(self, partial_name: str, canonical_schedules: Dict) -> List[str]:
        """Trouve les professeurs dont le nom contient la chaîne de recherche."""
        if not partial_name:
            return []

        partial_name_lower = partial_name.lower()
        matching_profs = []

        for prof_name in canonical_schedules.keys():
            if partial_name_lower in prof_name.lower():
                matching_profs.append(prof_name)

        return sorted(matching_profs)

    @staticmethod
    def get_available_colors() -> List[str]:
        """Retourne la liste des couleurs disponibles pour les professeurs."""
        return ProfessorManagementService.PROF_COLORS.copy()