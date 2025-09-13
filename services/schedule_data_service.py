import os
import json
from typing import Dict, List, Any
from dataclasses import asdict


class ScheduleDataService:
    """Service pour la gestion des données d'emploi du temps et des salles"""

    def __init__(self, file_service):
        """
        Initialise le service avec une référence au FileManagementService

        Args:
            file_service: Instance de FileManagementService
        """
        self.file_service = file_service

    def get_room_name(self, room_id: str) -> str:
        """Récupère le nom d'une salle par son ID"""
        rooms = self.file_service.load_rooms()
        for room in rooms:
            if str(room.get('id')) == str(room_id):
                return room.get('nom', f'Salle {room_id}')
        return f'Salle {room_id}'

    def assign_room_to_course(self, course_id: str, room_id: str):
        """Assigne une salle à un cours"""
        room_assignments = self.file_service.load_room_assignments()
        room_assignments[course_id] = room_id
        self.file_service.save_room_assignments(room_assignments)
        return room_id

    def get_all_courses(self, canonical_schedules: Dict, custom_courses: List[Dict], room_assignments: Dict):
        """Génère tous les cours à partir des emplois du temps canoniques et des cours personnalisés"""
        all_courses = []

        # Générer les semaines académiques
        academic_weeks = self._generate_academic_weeks()

        # Générer les cours à partir des emplois du temps canoniques
        for prof_name, prof_data in canonical_schedules.items():
            if isinstance(prof_data, dict) and 'courses' in prof_data:
                for week_name in academic_weeks:
                    for i, course_data in enumerate(prof_data['courses']):
                        # Générer l'ID du cours unique par semaine
                        course_id = self._generate_course_id_with_week(prof_name, course_data, week_name, i)
                        assigned_room = room_assignments.get(course_id)

                        # Importer ProfessorCourse dynamiquement pour éviter import circulaire
                        import importlib
                        app_module = importlib.import_module('app_new')
                        ProfessorCourse = app_module.ProfessorCourse

                        course = ProfessorCourse(
                            professor=prof_name,
                            start_time=course_data['start_time'],
                            end_time=course_data['end_time'],
                            duration_hours=course_data['duration_hours'],
                            course_type=course_data.get('course_type', course_data.get('module', 'N/A')),
                            nb_students=course_data.get('nb_students', 'N/A'),
                            assigned_room=assigned_room,
                            day=course_data['day'],
                            raw_time_slot=course_data['raw_time_slot'],
                            week_name=week_name,
                            course_id=course_id
                        )
                        all_courses.append(course)

        # Ajouter les cours personnalisés à la liste
        for custom_course in custom_courses:
            course_id = custom_course['course_id']
            assigned_room = room_assignments.get(course_id)

            # Importer ProfessorCourse dynamiquement
            import importlib
            app_module = importlib.import_module('app_new')
            ProfessorCourse = app_module.ProfessorCourse

            course = ProfessorCourse(
                professor=custom_course['professor'],
                start_time=custom_course['start_time'],
                end_time=custom_course['end_time'],
                duration_hours=custom_course['duration_hours'],
                course_type=custom_course['course_type'],
                nb_students=custom_course.get('nb_students', 'N/A'),
                assigned_room=assigned_room,
                day=custom_course['day'],
                raw_time_slot=custom_course['raw_time_slot'],
                week_name=custom_course['week_name'],
                course_id=course_id
            )
            all_courses.append(course)

        return all_courses

    def _generate_course_id(self, prof_name: str, course_data: Dict) -> str:
        """Génère un ID unique pour un cours"""
        import hashlib
        unique_string = f"{prof_name}_{course_data.get('week_name', '')}_{course_data.get('day', '')}_{course_data.get('start_time', '')}_{course_data.get('end_time', '')}_{course_data.get('course_type', course_data.get('module', ''))}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]

    def get_all_tp_names(self) -> Dict[str, str]:
        """Récupère tous les noms de TP sauvegardés"""
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
        """Récupère le nom d'un TP pour un cours donné"""
        tp_names = self.get_all_tp_names()
        return tp_names.get(course_id, '')

    def save_tp_name(self, course_id: str, tp_name: str) -> bool:
        """Sauvegarde le nom d'un TP pour un cours donné"""
        try:
            tp_names_file = "data/tp_names.json"
            os.makedirs("data", exist_ok=True)

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

    def delete_tp_name(self, course_id: str) -> bool:
        """Supprime le nom d'un TP pour un cours donné"""
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

    def get_prof_working_days(self, canonical_schedules: Dict) -> Dict[str, List[str]]:
        """Retourne un dictionnaire des jours travaillés pour chaque professeur"""
        working_days = {}
        for prof_name, prof_data in canonical_schedules.items():
            if isinstance(prof_data, dict) and 'courses' in prof_data:
                days = sorted(list(set(c.get('day') for c in prof_data['courses'] if c.get('day') not in [None, 'Indéterminé'])))
                working_days[prof_name] = days
        return working_days

    def get_normalized_professors_list(self, canonical_schedules: Dict) -> List[str]:
        """Retourne la liste des professeurs avec noms normalisés (sans doublons)"""
        from services.professor_management_service import ProfessorManagementService
        normalized_names = set()
        for prof_name in canonical_schedules.keys():
            normalized_name = ProfessorManagementService().normalize_professor_name(prof_name)
            normalized_names.add(normalized_name)
        return sorted(list(normalized_names))

    def force_sync_data(self, reload_callback):
        """Force la synchronisation des données avec verrouillage"""
        return self.file_service.force_sync_data_with_lock(reload_callback)

    def _generate_academic_weeks(self):
        """Génère les semaines académiques"""
        weeks = []
        is_type_A = True
        for week_num in range(36, 53):
            week_type = "A" if is_type_A else "B"
            weeks.append(f"Semaine {week_num} {week_type}")
            is_type_A = not is_type_A
        for week_num in range(1, 36):
            week_type = "A" if is_type_A else "B"
            weeks.append(f"Semaine {week_num:02d} {week_type}")
            is_type_A = not is_type_A
        return weeks

    def _generate_course_id_with_week(self, prof_name: str, course_data: Dict, week_name: str, index: int) -> str:
        """Génère un ID unique pour un cours avec semaine"""
        import hashlib
        raw_id = f"{week_name}_{prof_name}_{course_data['raw_time_slot']}_{index}"
        return f"course_{hashlib.md5(raw_id.encode()).hexdigest()[:16]}"