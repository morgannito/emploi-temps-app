import json
import os
from datetime import datetime
from typing import Dict
from excel_parser import ExcelScheduleParser


class TPManagementService:
    """Service pour la gestion des TPs et cours personnalisés"""

    def __init__(self, custom_courses_file="data/custom_courses.json"):
        self.custom_courses_file = custom_courses_file
        self.custom_courses = self._load_custom_courses()

    def _load_custom_courses(self):
        """Charge les cours personnalisés depuis le fichier."""
        if os.path.exists(self.custom_courses_file):
            try:
                with open(self.custom_courses_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []

    def add_custom_course(self, course_data: Dict) -> str:
        """Ajoute un cours personnalisé (TP) et retourne son ID."""
        # Générer un ID unique pour ce cours
        course_id = f"custom_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        course_data['course_id'] = course_id

        # Parser l'horaire pour extraire les détails
        parser = ExcelScheduleParser()
        time_info = parser.parse_time_range(course_data.get('raw_time_slot', ''))
        if time_info:
            course_data['start_time'], course_data['end_time'], course_data['duration_hours'] = time_info
        else:
            course_data['start_time'], course_data['end_time'], course_data['duration_hours'] = "00:00", "00:00", 0

        self.custom_courses.append(course_data)
        self.save_custom_courses()
        return course_id

    def save_custom_courses(self):
        """Sauvegarde les cours personnalisés dans leur fichier."""
        os.makedirs("data", exist_ok=True)
        with open(self.custom_courses_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_courses, f, indent=2, ensure_ascii=False)

    def move_custom_course(self, course_id: str, new_day: str, new_week: str) -> bool:
        """Déplace un cours personnalisé vers un autre jour/semaine."""
        course_found = False
        for course in self.custom_courses:
            if course.get('course_id') == course_id:
                course['day'] = new_day
                course['week_name'] = new_week
                course_found = True
                break

        if course_found:
            self.save_custom_courses()
            return True
        return False

    def get_custom_courses(self):
        """Retourne la liste des cours personnalisés."""
        return self.custom_courses

    # ==================== GESTION NOMS TP ====================

    def save_tp_name(self, course_id: str, tp_name: str) -> bool:
        """Sauvegarde le nom d'un TP pour un cours donné."""
        try:
            # Créer le répertoire data s'il n'existe pas
            os.makedirs("data", exist_ok=True)

            tp_names_file = "data/tp_names.json"

            # Charger les noms de TP existants
            tp_names = {}
            if os.path.exists(tp_names_file):
                with open(tp_names_file, 'r', encoding='utf-8') as f:
                    tp_names = json.load(f)

            # Mettre à jour ou ajouter le nom du TP
            tp_names[course_id] = tp_name

            # Sauvegarder
            with open(tp_names_file, 'w', encoding='utf-8') as f:
                json.dump(tp_names, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Erreur lors de la sauvegarde du nom de TP: {e}")
            return False

    def get_all_tp_names(self) -> Dict[str, str]:
        """Récupère tous les noms de TP sauvegardés."""
        try:
            tp_names_file = "data/tp_names.json"
            if os.path.exists(tp_names_file):
                with open(tp_names_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Erreur lors du chargement des noms de TP: {e}")
            return {}

    def get_tp_name(self, course_id: str) -> str:
        """Récupère le nom d'un TP pour un cours donné."""
        tp_names = self.get_all_tp_names()
        return tp_names.get(course_id, '')

    def delete_tp_name(self, course_id: str) -> bool:
        """Supprime le nom d'un TP pour un cours donné."""
        try:
            tp_names_file = "data/tp_names.json"

            if os.path.exists(tp_names_file):
                with open(tp_names_file, 'r', encoding='utf-8') as f:
                    tp_names = json.load(f)

                # Supprimer le nom du TP
                if course_id in tp_names:
                    del tp_names[course_id]

                    # Sauvegarder le fichier mis à jour
                    with open(tp_names_file, 'w', encoding='utf-8') as f:
                        json.dump(tp_names, f, indent=2, ensure_ascii=False)

                    return True
                else:
                    # Le nom du TP n'existait pas, considérer comme supprimé
                    return True
            else:
                # Le fichier n'existe pas, considérer comme supprimé
                return True

        except Exception as e:
            print(f"Erreur lors de la suppression du nom de TP: {e}")
            return False