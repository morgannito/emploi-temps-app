"""
Core business logic extracted from app_new.py
Gestionnaire des emplois du temps refactorisé avec services
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

from excel_parser import ExcelScheduleParser, normalize_professor_name
from services.database_service import DatabaseService
from utils.logger import app_logger


@dataclass
class ProfessorCourse:
    """Représente un cours d'un professeur"""
    professor: str
    start_time: str
    end_time: str
    duration_hours: float
    course_type: str
    nb_students: str
    assigned_room: Optional[str]
    day: str
    raw_time_slot: str
    week_name: str
    course_id: str


class ScheduleManager:
    """Gestionnaire des emplois du temps refactorisé avec services"""

    def __init__(self):
        # Initialiser les services
        from services.file_management_service import FileManagementService
        from services.professor_management_service import ProfessorManagementService
        from services.custom_course_service import CustomCourseService
        from services.schedule_data_service import ScheduleDataService
        from services.tp_management_service import TPManagementService
        from services.professor_view_service import ProfessorViewService
        from services.day_view_service import DayViewService
        from services.performance_cache_service import PerformanceCacheService

        self.file_service = FileManagementService()
        self.professor_service = ProfessorManagementService(self.file_service)
        self.custom_course_service = CustomCourseService(self.file_service)
        self.data_service = ScheduleDataService(self.file_service)
        self.tp_management_service = TPManagementService()
        self.professor_view_service = ProfessorViewService(self)
        self.day_view_service = DayViewService(self)
        self.perf_cache = PerformanceCacheService()
        self.use_database = True  # Mode SQLite activé avec migration complète

        # Données en cache
        self.schedules = {}
        self.canonical_schedules = {}
        self.room_assignments = {}
        self.rooms = []
        self.prof_data = {}
        self.custom_courses = []

        self.load_data()

    def load_data(self):
        """Charge toutes les données via les services"""
        self.schedules = self.file_service.load_schedules()
        self.canonical_schedules = self.file_service.load_canonical_schedules()
        self.room_assignments = self.file_service.load_room_assignments()
        self.rooms = self.file_service.load_rooms()
        self.prof_data = self.file_service.load_prof_data()
        self.custom_courses = self.tp_management_service.get_custom_courses()

    def force_sync_data(self):
        """Force la synchronisation via le service"""
        return self.file_service.force_sync_data_with_lock(self.load_data)

    def reload_data(self):
        """Force le rechargement via load_data et invalide le cache"""
        try:
            self.load_data()
            from services.cache_service import CacheService
            cache_service = CacheService()
            cache_service.invalidate_occupied_rooms_cache()
            return True
        except Exception as e:
            app_logger.error(f"Failed to reload schedule data: {e}")
            return False

    def get_prof_color(self, prof_name: str) -> str:
        """Récupère la couleur d'un prof via le service"""
        color = self.professor_service.get_prof_color(prof_name, self.prof_data)
        self.prof_data = self.file_service.load_prof_data()  # Sync cache
        return color

    def update_prof_color(self, prof_name: str, color: str) -> bool:
        """Met à jour la couleur d'un professeur via le service"""
        result = self.professor_service.update_prof_color(prof_name, color, self.prof_data)
        self.prof_data = self.file_service.load_prof_data()  # Sync cache
        return result

    def save_prof_data(self):
        """Sauvegarde via le service"""
        self.file_service.save_prof_data(self.prof_data)

    def get_canonical_schedules_summary(self):
        """Calcule un résumé via le service"""
        return self.professor_service.get_canonical_schedules_summary(self.canonical_schedules, self.prof_data)

    def add_professor(self, prof_name: str) -> bool:
        """Ajoute un nouveau professeur via le service"""
        result = self.professor_service.add_professor(prof_name, self.canonical_schedules)
        self.canonical_schedules = self.file_service.load_canonical_schedules()  # Sync cache
        return result

    def delete_professor(self, prof_name: str) -> bool:
        """Supprime un professeur via le service"""
        result = self.professor_service.delete_professor(prof_name, self.canonical_schedules)
        self.canonical_schedules = self.file_service.load_canonical_schedules()  # Sync cache
        return result

    def get_prof_schedule(self, prof_name: str) -> List[Dict]:
        """Récupère l'emploi du temps canonique via le service"""
        return self.professor_service.get_prof_schedule(prof_name, self.canonical_schedules)

    def update_prof_schedule(self, prof_name: str, courses: List[Dict]):
        """Met à jour l'emploi du temps canonique via le service"""
        result = self.professor_service.update_prof_schedule(prof_name, courses, self.canonical_schedules)
        self.canonical_schedules = self.file_service.load_canonical_schedules()  # Sync cache
        return result

    def get_all_courses(self) -> List[ProfessorCourse]:
        """Récupère tous les cours avec fallback BDD/JSON"""
        if self.use_database:
            return DatabaseService.get_all_courses()
        return self.data_service.get_all_courses(self.canonical_schedules, self.custom_courses, self.room_assignments)

    def assign_room(self, course_id: str, room_id: str) -> bool:
        """Attribue une salle via le service"""
        try:
            from services.room_conflict_service import RoomConflictService
            # Vérifier les conflits
            if RoomConflictService.check_room_conflict(course_id, room_id, self.get_all_courses()):
                return False

            # Attribuer la salle
            result = self.data_service.assign_room_to_course(course_id, room_id)
            self.room_assignments = self.file_service.load_room_assignments()  # Sync cache
            return bool(result)

        except Exception as e:
            app_logger.error(f"Room assignment failed: {e}")
            return False

    def check_room_conflict(self, course_id: str, room_id: str) -> bool:
        """Vérifie les conflits via le service"""
        from services.room_conflict_service import RoomConflictService
        return RoomConflictService.check_room_conflict(course_id, room_id, self.get_all_courses())

    def check_room_conflict_detailed(self, course_id: str, room_id: str) -> dict:
        """Vérifie les conflits détaillés via le service"""
        from services.room_conflict_service import RoomConflictService
        return RoomConflictService.check_room_conflict_detailed(course_id, room_id, self.get_all_courses())

    def times_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        """Vérifie si deux créneaux horaires se chevauchent"""
        from services.timeslot_service import TimeSlotService
        start1_min = TimeSlotService.time_to_minutes(start1)
        end1_min = TimeSlotService.time_to_minutes(end1)
        start2_min = TimeSlotService.time_to_minutes(start2)
        end2_min = TimeSlotService.time_to_minutes(end2)

        return not (end1_min <= start2_min or end2_min <= start1_min)

    def save_assignments(self):
        """Sauvegarde les attributions de salles"""
        import json
        import os
        assignments_file = os.path.join("data", "room_assignments.json")
        os.makedirs("data", exist_ok=True)
        with open(assignments_file, 'w', encoding='utf-8') as f:
            json.dump(self.room_assignments, f, indent=2, ensure_ascii=False)

    def get_room_name(self, room_id: str) -> str:
        """Récupère le nom d'une salle par son ID"""
        if not room_id:
            return ""

        for room in self.rooms:
            if str(room.get('id')) == str(room_id):
                return room.get('nom', room_id)

        return room_id

    def add_custom_course(self, course_data: Dict) -> str:
        """Ajoute un cours personnalisé (TP) et retourne son ID"""
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
        """Délègue au service de gestion TP"""
        self.tp_management_service.save_custom_courses()

    def save_tp_name(self, course_id: str, tp_name: str) -> bool:
        """Sauvegarde le nom d'un TP pour un cours donné"""
        try:
            import json
            import os

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
            app_logger.error(f"TP name save failed: {e}")
            return False

    def get_all_tp_names(self) -> Dict[str, str]:
        """Récupère tous les noms de TP sauvegardés"""
        try:
            import json
            import os
            tp_names_file = "data/tp_names.json"
            if os.path.exists(tp_names_file):
                with open(tp_names_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            app_logger.error(f"TP names load failed: {e}")
            return {}

    def get_tp_name(self, course_id: str) -> str:
        """Récupère le nom d'un TP pour un cours donné"""
        tp_names = self.get_all_tp_names()
        return tp_names.get(course_id, '')

    def delete_tp_name(self, course_id: str) -> bool:
        """Délègue au service de gestion TP"""
        return self.tp_management_service.delete_tp_name(course_id)

    def move_custom_course(self, course_id: str, new_day: str, new_week: str) -> bool:
        """Déplace un cours personnalisé vers un autre jour/semaine"""
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

    def get_prof_working_days(self) -> Dict[str, List[str]]:
        """Retourne un dictionnaire des jours travaillés pour chaque professeur"""
        working_days = {}
        for prof_name, prof_data in self.canonical_schedules.items():
            days = sorted(list(set(c.get('day') for c in prof_data['courses'] if c.get('day') not in [None, 'Indéterminé'])))
            working_days[prof_name] = days
        return working_days

    def get_normalized_professors_list(self) -> List[str]:
        """Retourne la liste des professeurs avec noms normalisés"""
        if self.use_database:
            prof_names = DatabaseService.get_all_professors()
        else:
            prof_names = list(self.canonical_schedules.keys())

        normalized_names = set()
        for prof_name in prof_names:
            normalized_name = normalize_professor_name(prof_name)
            normalized_names.add(normalized_name)
        return sorted(list(normalized_names))

    def get_courses_by_week(self, week_name: str) -> List[ProfessorCourse]:
        """Récupère les cours par semaine avec SQLite/JSON"""
        if self.use_database:
            return DatabaseService.get_courses_by_week(week_name)
        # Fallback JSON simplifié
        return [course for course in self.get_all_courses() if course.week_name == week_name]

    def get_courses_by_professor(self, professor_name: str) -> List[ProfessorCourse]:
        """Récupère les cours par professeur avec SQLite/JSON"""
        if self.use_database:
            return DatabaseService.get_courses_by_professor(professor_name)
        # Fallback JSON simplifié
        return [course for course in self.get_all_courses() if course.professor == professor_name]