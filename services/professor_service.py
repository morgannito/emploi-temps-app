import json
import os
from typing import Dict, List, Optional, Set
from excel_parser import normalize_professor_name


class ProfessorService:
    """Service pour la gestion des professeurs et leurs plannings"""

    @staticmethod
    def load_professor_id_mapping() -> Dict[str, str]:
        """Charge le mapping des IDs de professeurs depuis le fichier JSON"""
        prof_id_mapping_file = "data/prof_id_mapping.json"
        prof_id_mapping = {}
        if os.path.exists(prof_id_mapping_file):
            with open(prof_id_mapping_file, 'r', encoding='utf-8') as f:
                prof_id_mapping = json.load(f)
        return prof_id_mapping

    @staticmethod
    def get_professor_name_mapping(canonical_schedules: Dict) -> Dict[str, str]:
        """Crée un mapping des noms normalisés vers les noms originaux"""
        prof_name_mapping = {}
        for original_name in canonical_schedules.keys():
            normalized_name = normalize_professor_name(original_name)
            prof_name_mapping[normalized_name] = original_name
        return prof_name_mapping

    @staticmethod
    def extract_professors_from_courses(all_courses) -> Dict[str, List[str]]:
        """Extrait les professeurs uniques et leurs semaines depuis la liste des cours"""
        professors = {}

        for course in all_courses:
            prof_name = course.professor
            week_name = course.week_name

            if prof_name not in professors:
                professors[prof_name] = set()
            professors[prof_name].add(week_name)

        # Convertir les sets en listes triées
        for prof in professors:
            professors[prof] = sorted(list(professors[prof]))

        # Trier les professeurs
        return dict(sorted(professors.items()))

    @staticmethod
    def find_exact_professor_name(prof_name: str, available_profs: List[str]) -> Optional[str]:
        """Trouve le nom exact d'un professeur ou une correspondance"""
        # Si le nom exact existe
        if prof_name in available_profs:
            return prof_name

        # Chercher par nom de famille (après "M " ou "Mme ")
        for prof in available_profs:
            if prof_name.lower() in prof.lower() or prof.lower().endswith(prof_name.lower()):
                return prof

        return None

    @staticmethod
    def find_professor_by_id(prof_id: str, prof_id_mapping: Dict[str, str]) -> Optional[str]:
        """Trouve le nom d'un professeur à partir de son ID"""
        for name, mapped_id in prof_id_mapping.items():
            if mapped_id == prof_id:
                return name
        return None

    @staticmethod
    def sort_courses_by_day_and_time(courses: List[Dict]) -> List[Dict]:
        """Trie les cours par jour et heure"""
        days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Indéterminé']

        def get_day_index(day_name):
            try:
                return days_order.index(day_name)
            except ValueError:
                # Si le jour est invalide (ex: "Semaine 36 A "), on le met à la fin.
                return len(days_order)

        return sorted(courses, key=lambda x: (get_day_index(x.get('day', 'Indéterminé')), x.get('start_time')))

    @staticmethod
    def get_all_professors_with_ids() -> Dict[str, str]:
        """Retourne un dictionnaire {nom: id} pour tous les professeurs"""
        prof_id_mapping_file = "data/prof_id_mapping.json"
        if os.path.exists(prof_id_mapping_file):
            with open(prof_id_mapping_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}