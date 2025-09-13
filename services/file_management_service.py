import os
import json
import fcntl
import time
from typing import Dict, List, Any


class FileManagementService:
    """Service pour la gestion des fichiers JSON de l'application"""

    def __init__(self):
        # Configuration des chemins de fichiers
        self.schedules_file = "data/extracted_schedules.json"
        self.canonical_schedule_file = "data/professors_canonical_schedule.json"
        self.assignments_file = "data/room_assignments.json"
        self.rooms_file = "data/salle.json"
        self.prof_data_file = "data/prof_data.json"
        self.custom_courses_file = "data/custom_courses.json"

    def load_schedules(self) -> Dict:
        """Charge les données des emplois du temps bruts"""
        if os.path.exists(self.schedules_file):
            with open(self.schedules_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_canonical_schedules(self) -> Dict:
        """Charge les données canoniques des professeurs"""
        if os.path.exists(self.canonical_schedule_file):
            with open(self.canonical_schedule_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_room_assignments(self) -> Dict:
        """Charge les attributions de salles"""
        if os.path.exists(self.assignments_file):
            with open(self.assignments_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_rooms(self) -> List[Dict]:
        """Charge et adapte les données des salles"""
        if not os.path.exists(self.rooms_file):
            return []

        with open(self.rooms_file, 'r', encoding='utf-8') as f:
            rooms_data = json.load(f)

        # Adapter la structure des données des salles
        if 'rooms' in rooms_data:
            rooms = []
            for room in rooms_data['rooms']:
                adapted_room = {
                    'id': room['_id'],
                    'nom': room['name'],
                    'capacite': room['capacity'],
                    'equipement': room.get('equipment', '')
                }
                rooms.append(adapted_room)
            return rooms
        else:
            return rooms_data

    def load_prof_data(self) -> Dict:
        """Charge les données spécifiques aux professeurs (couleurs, etc.)"""
        if os.path.exists(self.prof_data_file):
            with open(self.prof_data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def load_custom_courses(self) -> List[Dict]:
        """Charge les cours personnalisés"""
        if os.path.exists(self.custom_courses_file):
            with open(self.custom_courses_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def save_room_assignments(self, assignments: Dict) -> None:
        """Sauvegarde les attributions de salles"""
        os.makedirs("data", exist_ok=True)
        with open(self.assignments_file, 'w', encoding='utf-8') as f:
            json.dump(assignments, f, ensure_ascii=False, indent=2)

    def save_prof_data(self, prof_data: Dict) -> None:
        """Sauvegarde les données des professeurs"""
        os.makedirs("data", exist_ok=True)
        with open(self.prof_data_file, 'w', encoding='utf-8') as f:
            json.dump(prof_data, f, ensure_ascii=False, indent=2)

    def save_canonical_schedules(self, schedules: Dict) -> None:
        """Sauvegarde les données canoniques"""
        os.makedirs("data", exist_ok=True)
        with open(self.canonical_schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedules, f, ensure_ascii=False, indent=2)

    def save_custom_courses(self, courses: List[Dict]) -> None:
        """Sauvegarde les cours personnalisés"""
        os.makedirs("data", exist_ok=True)
        with open(self.custom_courses_file, 'w', encoding='utf-8') as f:
            json.dump(courses, f, ensure_ascii=False, indent=2)

    def force_sync_data_with_lock(self, reload_callback) -> bool:
        """Force la synchronisation avec verrouillage pour éviter les conflits"""
        lock_file = "data/.sync_lock"
        max_wait = 5  # Attendre maximum 5 secondes

        try:
            # Créer le répertoire data s'il n'existe pas
            os.makedirs("data", exist_ok=True)

            # Essayer d'acquérir le verrou
            with open(lock_file, 'w') as lock:
                start_time = time.time()
                while time.time() - start_time < max_wait:
                    try:
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except (IOError, OSError):
                        time.sleep(0.1)
                        continue
                else:
                    # Timeout - on continue sans verrou
                    print("Warning: Impossible d'acquérir le verrou de synchronisation")
                    reload_callback()
                    return True

                # Verrou acquis, on peut synchroniser
                reload_callback()
                return True

        except Exception as e:
            print(f"Erreur lors de la synchronisation: {e}")
            return False

    def check_file_exists(self, file_path: str) -> bool:
        """Vérifie si un fichier existe"""
        return os.path.exists(file_path)

    def ensure_data_directory(self) -> None:
        """Assure que le répertoire data existe"""
        os.makedirs("data", exist_ok=True)