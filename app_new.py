import pytz
from datetime import date, timedelta
#!/usr/bin/env python3
"""
Application Flask pour l'attribution de salles aux professeurs
basée sur leurs horaires extraits du fichier Excel
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from excel_parser import ExcelScheduleParser, normalize_professor_name
from dataclasses import dataclass, asdict
import re
from functools import lru_cache
import time
from threading import RLock
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import io
from services.pdf_export_service import PDFExportService

app = Flask(__name__)

# Désactiver le cache des templates en mode debug
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Gestionnaire d'erreur pour les erreurs 500
@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur pour les erreurs 500"""
    app.logger.error(f'Erreur 500: {error}')
    return render_template('error.html', error=error), 500

# Gestionnaire d'erreur pour les erreurs 404
@app.errorhandler(404)
def not_found_error(error):
    """Gestionnaire d'erreur pour les erreurs 404"""
    app.logger.error(f'Erreur 404: {error}')
    return render_template('error.html', error=error), 404

PROF_COLORS = ["#e57373", "#81c784", "#64b5f6", "#fff176", "#ffb74d", "#ba68c8", "#4db6ac", "#f06292", "#a1887f"]

# Cache pour les salles occupées avec TTL
_occupied_rooms_cache = {}
_cache_lock = RLock()
_cache_ttl = 3  # 3 secondes de cache

def _get_cache_key(course_id, week_name, day, start_time, end_time):
    """Génère une clé de cache basée sur le créneau"""
    return f"{week_name}_{day}_{start_time}_{end_time}"

def _invalidate_occupied_rooms_cache():
    """Invalide le cache des salles occupées"""
    global _occupied_rooms_cache
    with _cache_lock:
        _occupied_rooms_cache.clear()


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

        self.file_service = FileManagementService()
        self.professor_service = ProfessorManagementService(self.file_service)
        self.custom_course_service = CustomCourseService(self.file_service)
        self.data_service = ScheduleDataService(self.file_service)

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
        self.custom_courses = self.file_service.load_custom_courses()

    def force_sync_data(self):
        """Force la synchronisation via le service"""
        return self.file_service.force_sync_data_with_lock(self.load_data)

    def reload_data(self):
        """Force le rechargement via load_data et invalide le cache"""
        try:
            self.load_data()
            _invalidate_occupied_rooms_cache()
            return True
        except Exception as e:
            print(f"Erreur lors du rechargement des données: {e}")
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
        """Récupère tous les cours via le service"""
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
            print(f"❌ Erreur lors de l'attribution: {e}")
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
        start1_min = TimeSlotService.time_to_minutes(start1)
        end1_min = TimeSlotService.time_to_minutes(end1)
        start2_min = TimeSlotService.time_to_minutes(start2)
        end2_min = TimeSlotService.time_to_minutes(end2)
        
        return not (end1_min <= start2_min or end2_min <= start1_min)
    
    def save_assignments(self):
        """Sauvegarde les attributions de salles"""
        with open(self.assignments_file, 'w', encoding='utf-8') as f:
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
        with open(self.custom_courses_file, 'w', encoding='utf-8') as f:
            json.dump(self.custom_courses, f, indent=2, ensure_ascii=False)

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

    def get_prof_working_days(self) -> Dict[str, List[str]]:
        """Retourne un dictionnaire des jours travaillés pour chaque professeur."""
        working_days = {}
        for prof_name, prof_data in self.canonical_schedules.items():
            days = sorted(list(set(c.get('day') for c in prof_data['courses'] if c.get('day') not in [None, 'Indéterminé'])))
            working_days[prof_name] = days
        return working_days

    def get_normalized_professors_list(self) -> List[str]:
        """Retourne la liste des professeurs avec noms normalisés (sans doublons)."""
        normalized_names = set()
        for prof_name in self.canonical_schedules.keys():
            normalized_name = normalize_professor_name(prof_name)
            normalized_names.add(normalized_name)
        return sorted(list(normalized_names))

# Instance globale du gestionnaire
schedule_manager = ScheduleManager()

from services.week_service import WeekService
from services.timeslot_service import TimeSlotService
from services.course_grid_service import CourseGridService
from services.professor_service import ProfessorService
from services.planning_service import PlanningService
from services.student_service import StudentService
from services.kiosque_service import KiosqueService

@app.route('/')
@app.route('/week/<week_name>')
def admin(week_name=None):
    """Page d'administration principale (attribution des salles) avec vue hebdomadaire."""
    # Forcer la synchronisation des données en production
    schedule_manager.force_sync_data()

    # Vérifier la cohérence des données
    try:
        # Vérifier que les attributions de salles sont cohérentes
        all_courses = schedule_manager.get_all_courses()
        room_assignments_count = len(schedule_manager.room_assignments)
        courses_with_rooms = sum(1 for c in all_courses if c.assigned_room)

        if abs(room_assignments_count - courses_with_rooms) > 5:  # Tolérance de 5
            print(f"Warning: Incohérence détectée - Attributions: {room_assignments_count}, Cours avec salles: {courses_with_rooms}")
            # Forcer une nouvelle synchronisation
            schedule_manager.force_sync_data()
    except Exception as e:
        print(f"Erreur lors de la vérification de cohérence: {e}")

    # Utiliser les services pour générer les données
    weeks_to_display = WeekService.generate_academic_calendar()

    if not weeks_to_display:
        return "Erreur lors de la génération du calendrier.", 500

    # Déterminer la semaine à afficher
    if week_name is None:
        week_name = WeekService.get_current_week_name(weeks_to_display)

    # Trouver les informations de la semaine
    current_week_info = WeekService.find_week_info(week_name, weeks_to_display)
    if not current_week_info:
        # Fallback si la semaine n'est pas trouvée
        current_week_info = weeks_to_display[0]
        week_name = current_week_info['name']

    # Générer la grille horaire et l'ordre des jours
    time_slots = TimeSlotService.generate_time_grid()
    days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

    # Préparer les cours pour la semaine
    all_courses_for_week = CourseGridService.prepare_courses_for_week(schedule_manager, week_name)

    # Préparer les cours avec les TPs attachés
    courses_to_place_in_grid = CourseGridService.prepare_courses_with_tps(all_courses_for_week)

    # Construire la grille hebdomadaire
    weekly_grid = CourseGridService.build_weekly_grid(courses_to_place_in_grid, time_slots, days_order)

    return render_template('admin_new.html', 
                         weekly_grid=weekly_grid,
                         time_slots=time_slots,
                         days_order=days_order,
                         rooms=schedule_manager.rooms,
                         get_room_name=schedule_manager.get_room_name,
                         all_weeks=weeks_to_display,
                         current_week=week_name,
                         current_week_info=current_week_info,
                         all_professors=schedule_manager.get_normalized_professors_list())

@app.route('/planning')
@app.route('/planning/<week_name>')
def planning_readonly(week_name=None):
    """Vue planning en lecture seule (sans possibilité de modification)."""
    # Utiliser le service pour récupérer toutes les données
    planning_data = PlanningService.get_planning_data(schedule_manager, week_name)

    return render_template('planning_readonly.html',
                         week_name=planning_data['week_name'],
                         weeks_to_display=planning_data['weeks_to_display'],
                         current_week_info=planning_data['current_week_info'],
                         courses=planning_data['courses'],
                         courses_by_day_time=planning_data['courses_by_day_time'],
                         days=planning_data['days'],
                         time_slots=planning_data['time_slots'],
                         all_weeks=planning_data['all_weeks'],
                         current_week=week_name,
                         all_professors=schedule_manager.get_normalized_professors_list())




@app.route("/planning_v2")
@app.route("/planning_v2/<week_name>")
def planning_v2(week_name=None):
    """Planning V2 - Même affichage que la route principale mais en lecture seule"""
    # Forcer la synchronisation des données en production
    schedule_manager.force_sync_data()
    
    # Vérifier la cohérence des données
    try:
        # Vérifier que les attributions de salles sont cohérentes
        all_courses = schedule_manager.get_all_courses()
        room_assignments_count = len(schedule_manager.room_assignments)
        courses_with_rooms = sum(1 for c in all_courses if c.assigned_room)
        
        if abs(room_assignments_count - courses_with_rooms) > 5:  # Tolérance de 5
            print(f"Warning: Incohérence détectée - Attributions: {room_assignments_count}, Cours avec salles: {courses_with_rooms}")
            # Forcer une nouvelle synchronisation
            schedule_manager.force_sync_data()
    except Exception as e:
        print(f"Erreur lors de la vérification de cohérence: {e}")
    
    def generate_academic_calendar():
        """Génère une liste de semaines alternant A et B pour toute l'année scolaire avec dates."""
        
        weeks = []
        is_type_A = True  # On commence par une semaine de type A
        
        # Date de début de l'année scolaire (dernière semaine d'août 2025)
        # Semaine 36 commence le 1er septembre 2025
        start_date = date(2025, 9, 1)  # Lundi 1er septembre 2025
        
        # Première partie de l'année (septembre à décembre) - Semaines 36-52
        for week_num in range(36, 53):
            week_type = "A" if is_type_A else "B"
            
            # Calculer la date du lundi de cette semaine
            week_offset = (week_num - 36) * 7  # 7 jours par semaine
            monday_date = start_date + timedelta(days=week_offset)
            
            # Formater la date
            date_str = monday_date.strftime("%d/%m/%Y")
            
            weeks.append({
                'name': f"Semaine {week_num} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A
            
        # Deuxième partie de l'année (janvier à juin) - Semaines 1-35
        # Continuer à partir de la semaine 1 (janvier 2026)
        for week_num in range(1, 36):
            week_type = "A" if is_type_A else "B"
            
            # Calculer la date du lundi de cette semaine
            # Semaine 1 commence le 5 janvier 2026
            january_start = date(2026, 1, 5)  # Lundi 5 janvier 2026
            week_offset = (week_num - 1) * 7
            monday_date = january_start + timedelta(days=week_offset)
            
            # Formater la date
            date_str = monday_date.strftime("%d/%m/%Y")
            
            weeks.append({
                'name': f"Semaine {week_num:02d} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num:02d} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A
            
        return weeks
    
    def generate_time_grid():
        """Génère une grille horaire de 8h à 18h avec créneaux d'1 heure"""
        time_slots = []
        for hour in range(8, 18):
            start_time = f"{hour:02d}:00"
            end_time = f"{hour+1:02d}:00"
            time_slots.append({
                'start_time': start_time,
                'end_time': end_time,
                'label': f"{hour}h-{hour+1}h"
            })
        return time_slots
    
    weeks_to_display = generate_academic_calendar()
    
    if not weeks_to_display:
        return "Erreur lors de la génération du calendrier.", 500
    
    # Si aucune semaine n'est spécifiée, déterminer la semaine actuelle
    if week_name is None:
        today = datetime.now(pytz.timezone("Europe/Paris")).date()
        week_num = today.isocalendar()[1]
        
        # Déterminer le type de semaine (A ou B) - corrigé pour 2025
        if today.year == 2025 and week_num >= 36:
            # Semaines de septembre à décembre 2025
            weeks_since_start = week_num - 36
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            week_name = f"Semaine {week_num} {week_type}"
        elif today.year == 2026 and week_num <= 35:
            # Semaines de janvier à juin 2026
            # 17 semaines de sept-dec 2025 (36-52)
            weeks_since_start = 17 + week_num - 1
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            # Format avec zéro pour les semaines < 10
            week_name = f"Semaine {week_num:02d} {week_type}"
        else:
            # Par défaut, prendre la première semaine
            week_name = weeks_to_display[0]['name']
    
    # Trouver la semaine correspondante dans la liste
    current_week_info = None
    for week_info in weeks_to_display:
        if week_info['name'] == week_name:
            current_week_info = week_info
            break
    
    if not current_week_info:
        # Fallback si la semaine n'est pas trouvée
        current_week_info = weeks_to_display[0]
        week_name = current_week_info['name']
    
    # Générer la grille horaire
    time_slots = generate_time_grid()
    days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    
    # Préparer les données des cours
    all_courses_obj = schedule_manager.get_all_courses()
    prof_working_days = schedule_manager.get_prof_working_days()
    
    # Filtrer pour la semaine et ajouter les jours de travail
    all_courses_for_week = []
    for c in all_courses_obj:
        if c.week_name == week_name:
            course_dict = asdict(c)
            course_dict['working_days'] = prof_working_days.get(c.professor, [])
            all_courses_for_week.append(course_dict)
    
    # Attacher les TPs aux cours originaux AVANT de les placer dans la grille
    original_courses = [c for c in all_courses_for_week if not c['course_id'].startswith('custom_')]
    custom_tps = [c for c in all_courses_for_week if c['course_id'].startswith('custom_')]
    
    # Créer un lookup pour les cours originaux
    original_courses_lookup = {}
    for course in original_courses:
        key = (course.get('day'), course.get('professor'), course.get('raw_time_slot'))
        if key not in original_courses_lookup:
            original_courses_lookup[key] = []
        original_courses_lookup[key].append(course)
    
    # Initialiser related_tps pour tous les cours
    for course in all_courses_for_week:
        course['related_tps'] = []
    
    # Attacher les TPs aux cours originaux correspondants
    standalone_tps = []
    for tp in custom_tps:
        key = (tp.get('day'), tp.get('professor'), tp.get('raw_time_slot'))
        matching_originals = original_courses_lookup.get(key, [])
        
        if matching_originals:
            # Attacher ce TP au premier cours original correspondant
            matching_originals[0]['related_tps'].append(tp)
        else:
            # TP autonome (pas de cours original correspondant)
            standalone_tps.append(tp)
    
    # Ajouter les TPs autonomes à la liste des cours à afficher
    courses_to_place_in_grid = original_courses + standalone_tps
    
    # Créer une grille complète : jour -> créneau -> liste des cours
    weekly_grid = {}
    for day in days_order:
        weekly_grid[day] = {}
        for time_slot in time_slots:
            weekly_grid[day][time_slot['label']] = {
                'time_info': time_slot,
                'courses': []
            }
    
    # Placer les cours dans la grille
    for course in courses_to_place_in_grid:
        day = course.get('day')
        if day not in days_order:
            continue
            
        course_start = course.get('start_time', '')
        course_end = course.get('end_time', '')
        
        # Convertir les heures en minutes pour faciliter les calculs
        course_start_min = TimeSlotService.time_to_minutes(course_start)
        course_end_min = TimeSlotService.time_to_minutes(course_end)
        
        # Trouver le premier créneau qui correspond au début du cours
        primary_slot = None
        for time_slot in time_slots:
            slot_start_min = TimeSlotService.time_to_minutes(time_slot['start_time'])
            slot_end_min = TimeSlotService.time_to_minutes(time_slot['end_time'])
            
            # Si le cours commence dans ce créneau, c'est le créneau principal
            if course_start_min >= slot_start_min and course_start_min < slot_end_min:
                primary_slot = time_slot['label']
                # Marquer ce cours comme cours principal dans ce créneau
                course['is_primary_slot'] = True
                course['spans_slots'] = []
                
                # Calculer tous les créneaux que ce cours occupe
                for other_slot in time_slots:
                    other_start_min = TimeSlotService.time_to_minutes(other_slot['start_time'])
                    other_end_min = TimeSlotService.time_to_minutes(other_slot['end_time'])
                    
                    # Si ce créneau chevauche avec le cours
                    if not (course_end_min <= other_start_min or course_start_min >= other_end_min):
                        course['spans_slots'].append(other_slot['label'])
                        
                        # Ajouter le cours à ce créneau
                        if other_slot['label'] == primary_slot:
                            # Dans le créneau principal, afficher toutes les infos
                            weekly_grid[day][other_slot['label']]['courses'].append(course)
                        else:
                            # Dans les autres créneaux, afficher une version réduite
                            continuation_course = course.copy()
                            continuation_course['is_continuation'] = True
                            continuation_course['primary_slot'] = primary_slot
                            weekly_grid[day][other_slot['label']]['courses'].append(continuation_course)
                break
    
    return render_template('planning_v2.html',
                         weekly_grid=weekly_grid,
                         time_slots=time_slots,
                         days_order=days_order,
                         rooms=schedule_manager.rooms,
                         get_room_name=schedule_manager.get_room_name,
                         all_weeks=weeks_to_display,
                         current_week=week_name,
                         current_week_info=current_week_info,
                         all_professors=schedule_manager.get_normalized_professors_list())
@app.route('/professors')
def list_professors_overview_minimal():
    """Page de vue d'ensemble des emplois du temps des professeurs."""
    # Forcer le rechargement des données en production
    schedule_manager.reload_data()
    summary = schedule_manager.get_canonical_schedules_summary()

    # Utiliser le service pour obtenir les mappings
    prof_name_mapping = ProfessorService.get_professor_name_mapping(schedule_manager.canonical_schedules)
    prof_id_mapping = ProfessorService.load_professor_id_mapping()

    return render_template('prof_schedules_overview.html',
                         summary=summary,
                         prof_colors=PROF_COLORS,
                         prof_name_mapping=prof_name_mapping,
                         prof_id_mapping=prof_id_mapping)


@app.route('/edit_schedule/<path:prof_name>')
def edit_schedule(prof_name: str):
    """Page d'édition de l'emploi du temps pour un professeur."""

    # Forcer le rechargement des données en production
    schedule_manager.reload_data()

    # Utiliser le service pour trouver le nom exact du professeur
    available_profs = list(schedule_manager.canonical_schedules.keys())
    exact_prof_name = ProfessorService.find_exact_professor_name(prof_name, available_profs)

    if not exact_prof_name:
        return f"Professeur '{prof_name}' non trouvé. Professeurs disponibles: {', '.join(available_profs[:5])}...", 404

    courses = schedule_manager.get_prof_schedule(exact_prof_name)
    sorted_courses = ProfessorService.sort_courses_by_day_and_time(courses)

    return render_template('edit_schedule.html',
                           prof_name=exact_prof_name,
                           courses=sorted_courses)

@app.route('/api/save_prof_schedule/<path:prof_name>', methods=['POST'])
def save_prof_schedule(prof_name: str):
    """API pour sauvegarder le nouvel emploi du temps d'un professeur."""
    try:
        new_courses = request.get_json()
        if not isinstance(new_courses, list):
            return jsonify({'success': False, 'error': 'Format de données invalide.'})

        # Recalculer les durées avant de sauvegarder
        parser = ExcelScheduleParser()
        for course in new_courses:
            time_info = parser.parse_time_range(course.get('raw_time_slot', ''))
            if time_info:
                course['start_time'], course['end_time'], course['duration_hours'] = time_info
            else: # Mettre des valeurs par défaut si le parsing échoue
                course['start_time'], course['end_time'], course['duration_hours'] = "00:00", "00:00", 0
        
        success = schedule_manager.update_prof_schedule(prof_name, new_courses)

        if success:
            # Forcer la synchronisation des données pour tous les workers
            schedule_manager.force_sync_data()
            return jsonify({'success': True, 'message': 'Emploi du temps mis à jour.'})
        else:
            return jsonify({'success': False, 'error': 'Impossible de sauvegarder.'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/assign_room', methods=['POST'])
def assign_room():
    """API pour attribuer une salle à un cours"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        room_id = data.get('room_id')
        
        if not course_id:
            return jsonify({'success': False, 'error': 'Course ID manquant'})
        
        # Si room_id est vide, on supprime l'attribution
        if not room_id:
            if course_id in schedule_manager.room_assignments:
                del schedule_manager.room_assignments[course_id]
                schedule_manager.save_assignments()
                # Forcer la synchronisation des données pour tous les workers
                schedule_manager.force_sync_data()
            return jsonify({'success': True})
        
        # Vérifier les conflits avec détails
        conflict_details = schedule_manager.check_room_conflict_detailed(course_id, room_id)
        
        if conflict_details['has_conflict']:
            return jsonify({
                'success': False, 
                'error': 'Conflit de salle détecté',
                'conflict_details': conflict_details
            })
        
        # Attribuer la salle
        success = schedule_manager.assign_room(course_id, room_id)
        
        if success:
            # Forcer la synchronisation des données pour tous les workers
            schedule_manager.force_sync_data()
            # Invalider le cache des salles occupées
            _invalidate_occupied_rooms_cache()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Erreur lors de l\'attribution'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/get_conflict_details', methods=['POST'])
def get_conflict_details():
    """API pour obtenir les détails des conflits de salle"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        room_id = data.get('room_id')
        
        if not course_id or not room_id:
            return jsonify({'has_conflict': False, 'conflicts': []})
        
        conflict_info = schedule_manager.check_room_conflict_detailed(course_id, room_id)
        return jsonify(conflict_info)
    
    except Exception as e:
        return jsonify({'has_conflict': True, 'conflicts': [{'type': 'error', 'message': str(e)}]})


@app.route('/api/check_conflict', methods=['POST'])
def check_conflict():
    """API pour vérifier les conflits de salle"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        room_id = data.get('room_id')
        
        if not course_id or not room_id:
            return jsonify({'conflict': False})
        
        conflict = schedule_manager.check_room_conflict(course_id, room_id)
        return jsonify({'conflict': conflict})
    
    except Exception as e:
        return jsonify({'conflict': True, 'error': str(e)})

@app.route('/api/courses/add_custom', methods=['POST'])
def add_custom_course():
    """API pour ajouter un TP personnalisé."""
    data = request.get_json()
    
    # Validation basique
    required_fields = ['week_name', 'day', 'raw_time_slot', 'professor', 'course_type']
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'error': 'Données manquantes.'}), 400
        
    course_id = schedule_manager.add_custom_course(data)
    
    # Forcer le rechargement des données pour tous les workers
    schedule_manager.reload_data()
    
    # Retourner les détails du cours ajouté pour l'afficher dynamiquement
    new_course = next((c for c in schedule_manager.custom_courses if c['course_id'] == course_id), None)
    
    if new_course:
        return jsonify({'success': True, 'course': new_course})
    else:
        return jsonify({'success': False, 'error': "Erreur lors de la création du cours."}), 500

@app.route('/api/courses/move', methods=['POST'])
def move_custom_course():
    """API pour déplacer un TP personnalisé."""
    data = request.get_json()
    course_id = data.get('course_id')
    new_day = data.get('day')
    new_week = data.get('week_name')

    if not all([course_id, new_day, new_week]):
        return jsonify({'success': False, 'error': 'Données manquantes pour le report.'}), 400

    success = schedule_manager.move_custom_course(course_id, new_day, new_week)

    if success:
        # Forcer le rechargement des données pour tous les workers
        schedule_manager.reload_data()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Le cours à reporter n\'a pas été trouvé.'}), 404

@app.route('/api/professors/add', methods=['POST'])
def add_professor():
    """API pour ajouter un nouveau professeur."""
    data = request.get_json()
    prof_name = data.get('name', '').strip()
    if not prof_name:
        return jsonify({'success': False, 'error': 'Le nom du professeur est requis.'}), 400
    
    success = schedule_manager.add_professor(prof_name)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Ce professeur existe déjà.'}), 409

@app.route('/api/professors/update_color', methods=['POST'])
def update_prof_color():
    """API pour mettre à jour la couleur d'un professeur."""
    data = request.get_json()
    prof_name = data.get('name')
    color = data.get('color')
    if not prof_name or not color:
        return jsonify({'success': False, 'error': 'Données manquantes.'}), 400
    
    success = schedule_manager.update_prof_color(prof_name, color)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Couleur invalide.'}), 400

@app.route('/api/professors/delete', methods=['POST'])
def delete_professor():
    """API pour supprimer un professeur."""
    data = request.get_json()
    prof_name = data.get('name')
    if not prof_name:
        return jsonify({'success': False, 'error': 'Le nom du professeur est requis.'}), 400
        
    success = schedule_manager.delete_professor(prof_name)
    if success:
        # Forcer la synchronisation des données pour tous les workers
        schedule_manager.force_sync_data()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Professeur non trouvé.'}), 404

@app.route('/api/get_occupied_rooms', methods=['POST'])
def get_occupied_rooms():
    """API optimisée pour récupérer les salles occupées pour un créneau donné"""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'occupied_rooms': []})
        
        # Forcer la synchronisation des données en production
        schedule_manager.force_sync_data()
        
        # Trouver le cours actuel pour obtenir ses informations de créneau
        all_courses = schedule_manager.get_all_courses()
        current_course = None
        
        for course in all_courses:
            if course.course_id == course_id:
                current_course = course
                break
        
        if not current_course:
            return jsonify({'occupied_rooms': []})
        
        # Générer la clé de cache basée sur le créneau
        cache_key = _get_cache_key(
            course_id, 
            current_course.week_name, 
            current_course.day,
            current_course.start_time, 
            current_course.end_time
        )
        
        # Vérifier le cache
        now = time.time()
        with _cache_lock:
            if cache_key in _occupied_rooms_cache:
                cached_data = _occupied_rooms_cache[cache_key]
                if now - cached_data['timestamp'] < _cache_ttl:
                    return jsonify({'occupied_rooms': cached_data['rooms'], 'from_cache': True})
        
        # Calculer les salles occupées (cache miss ou expiré)
        occupied_rooms = set()
        
        for course in all_courses:
            if (course.course_id != course_id and 
                course.assigned_room and
                course.week_name == current_course.week_name and
                course.day == current_course.day):
                
                # Vérifier le chevauchement horaire
                if schedule_manager.times_overlap(
                    current_course.start_time, current_course.end_time,
                    course.start_time, course.end_time
                ):
                    occupied_rooms.add(course.assigned_room)
        
        occupied_rooms_list = list(occupied_rooms)
        
        # Mettre en cache
        with _cache_lock:
            _occupied_rooms_cache[cache_key] = {
                'rooms': occupied_rooms_list,
                'timestamp': now
            }
        
        return jsonify({'occupied_rooms': occupied_rooms_list, 'from_cache': False})
    
    except Exception as e:
        return jsonify({'occupied_rooms': [], 'error': str(e)})

@app.route('/api/get_free_rooms', methods=['POST'])
def get_free_rooms():
    """API pour récupérer les salles libres pour un créneau donné"""
    try:
        data = request.get_json()
        week_name = data.get('week_name')
        day_name = data.get('day_name')
        time_slot = data.get('time_slot')
        
        if not all([week_name, day_name, time_slot]):
            return jsonify({'free_rooms': [], 'error': 'Paramètres manquants'})
        
        # Forcer la synchronisation des données
        schedule_manager.force_sync_data()
        
        # Récupérer toutes les salles
        all_rooms = schedule_manager.rooms
        
        # Récupérer tous les cours
        all_courses = schedule_manager.get_all_courses()
        
        # Trouver les cours qui se chevauchent avec ce créneau
        occupied_rooms = set()
        
        # Parser le créneau horaire (ex: "8h-9h")
        time_parts = time_slot.split('-')
        if len(time_parts) == 2:
            start_time_str = time_parts[0].strip()
            end_time_str = time_parts[1].strip()
            
            # Convertir le format "8h" en "08:00"
            def convert_time_format(time_str):
                # Enlever le "h" et convertir en format HH:MM
                hour = time_str.replace('h', '').strip()
                return f"{int(hour):02d}:00"
            
            try:
                start_time = convert_time_format(start_time_str)
                end_time = convert_time_format(end_time_str)
                
                # Vérifier tous les cours pour ce jour et cette semaine
                for course in all_courses:
                    if (course.week_name == week_name and 
                        course.day == day_name and
                        course.assigned_room):
                        
                        # Vérifier le chevauchement horaire
                        if schedule_manager.times_overlap(
                            start_time, end_time,
                            course.start_time, course.end_time
                        ):
                            occupied_rooms.add(course.assigned_room)
                            
            except Exception as e:
                print(f"Erreur parsing time: {e}")
                return jsonify({'free_rooms': [], 'error': 'Erreur parsing horaire'})
        
        # Calculer les salles libres
        free_rooms = []
        for room in all_rooms:
            if room['id'] not in occupied_rooms:
                free_rooms.append({
                    'id': room['id'],
                    'nom': room['nom'],
                    'capacite': room.get('capacite', 'N/A')
                })
        
        return jsonify({
            'free_rooms': free_rooms,
            'total_rooms': len(all_rooms),
            'occupied_count': len(occupied_rooms),
            'free_count': len(free_rooms)
        })
        
    except Exception as e:
        return jsonify({'free_rooms': [], 'error': str(e)})

@app.route('/api/courses/duplicate', methods=['POST'])
def duplicate_course():
    """API pour dupliquer un cours vers plusieurs jours/semaines."""
    try:
        data = request.get_json()
        professor = data.get('professor')
        course_type = data.get('course_type')
        raw_time_slot = data.get('raw_time_slot')
        days = data.get('days', [])
        weeks = data.get('weeks', [])
        
        if not all([professor, course_type, raw_time_slot, days, weeks]):
            return jsonify({'success': False, 'error': 'Données manquantes.'}), 400
        
        created_count = 0
        
        # Dupliquer vers chaque combinaison jour/semaine
        for day in days:
            for week in weeks:
                course_data = {
                    'week_name': week,
                    'day': day,
                    'raw_time_slot': raw_time_slot,
                    'professor': professor,
                    'course_type': course_type,
                    'nb_students': 'N/A'
                }
                
                course_id = schedule_manager.add_custom_course(course_data)
                if course_id:
                    created_count += 1
        
        return jsonify({'success': True, 'created_count': created_count})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/courses/delete', methods=['POST'])
def delete_course():
    """API pour supprimer un cours personnalisé."""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'success': False, 'error': 'ID du cours manquant.'}), 400
        
        # Chercher et supprimer le cours dans la liste des cours personnalisés
        course_found = False
        for i, course in enumerate(schedule_manager.custom_courses):
            if course.get('course_id') == course_id:
                schedule_manager.custom_courses.pop(i)
                course_found = True
                break
        
        if course_found:
            # Supprimer aussi l'attribution de salle si elle existe
            if course_id in schedule_manager.room_assignments:
                del schedule_manager.room_assignments[course_id]
                schedule_manager.save_assignments()
            
            # Sauvegarder les cours personnalisés
            schedule_manager.save_custom_courses()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Cours non trouvé.'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/courses/update_tp_name', methods=['POST'])
def update_tp_name():
    """API pour mettre à jour le nom d'un TP sur un cours existant."""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        tp_name = data.get('tp_name')
        
        if not course_id or not tp_name:
            return jsonify({'success': False, 'error': 'ID du cours et nom du TP requis.'}), 400
        
        # Sauvegarder le nom du TP dans un fichier dédié
        success = schedule_manager.save_tp_name(course_id, tp_name)
        
        if success:
            return jsonify({'success': True, 'tp_name': tp_name})
        else:
            return jsonify({'success': False, 'error': 'Erreur lors de la sauvegarde.'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/courses/get_tp_names', methods=['GET'])
def get_tp_names():
    """API pour récupérer tous les noms de TP sauvegardés."""
    try:
        # Forcer la synchronisation des données avant de récupérer
        schedule_manager.force_sync_data()
        tp_names = schedule_manager.get_all_tp_names()
        
        response = jsonify({'success': True, 'tp_names': tp_names})
        # Ajouter des en-têtes anti-cache
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    except Exception as e:
        print(f"Erreur lors de la récupération des noms de TP: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/courses/delete_tp_name', methods=['POST'])
def delete_tp_name():
    """API pour supprimer le nom d'un TP d'un cours."""
    try:
        data = request.get_json()
        course_id = data.get('course_id')
        
        if not course_id:
            return jsonify({'success': False, 'error': 'ID du cours requis.'}), 400
        
        print(f"Suppression du TP pour le cours {course_id}")
        
        # Supprimer le nom du TP
        success = schedule_manager.delete_tp_name(course_id)
        
        if success:
            print(f"TP supprimé avec succès pour le cours {course_id}")
            # Forcer la synchronisation des données
            schedule_manager.force_sync_data()
            
            response = jsonify({'success': True, 'message': 'TP supprimé avec succès'})
            # Ajouter des en-têtes anti-cache
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        else:
            print(f"Erreur lors de la suppression du TP pour le cours {course_id}")
            return jsonify({'success': False, 'error': 'Erreur lors de la suppression.'}), 500
            
    except Exception as e:
        print(f"Exception lors de la suppression du TP: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/student')
@app.route('/student/<week_name>')
def student_view(week_name=None):
    """Redirection vers la nouvelle vue kiosque compact."""
    return redirect(url_for('kiosque_halfday', layout='compact'))


# ============== NOUVELLES ROUTES KIOSQUE ==============

@app.route('/kiosque/week')
@app.route('/kiosque/week/<week_name>')
def kiosque_week(week_name=None):
    """Vue kiosque - tous les cours de la semaine sur un écran"""
    kiosque_data = KiosqueService.get_kiosque_week_data(schedule_manager, week_name)

    return render_template('kiosque_week.html',
                         week_grid=kiosque_data['week_grid'],
                         time_slots=kiosque_data['time_slots'],
                         days_order=kiosque_data['days_order'],
                         current_week=kiosque_data['current_week'],
                         total_courses=kiosque_data['total_courses'])

@app.route('/kiosque/room')
@app.route('/kiosque/room/<room_id>')
def kiosque_room(room_id=None):
    """Vue kiosque - occupation des salles"""
    kiosque_data = KiosqueService.get_kiosque_room_data(schedule_manager, room_id)

    return render_template('kiosque_room.html',
                         rooms_data=kiosque_data['rooms_data'],
                         current_week=kiosque_data['current_week'],
                         focused_room=kiosque_data['focused_room'])

@app.route('/tv/schedule')
def tv_schedule():
    """Affichage TV défilant automatique"""
    tv_data = KiosqueService.get_tv_schedule_data(schedule_manager)

    return render_template('tv_schedule.html',
                         current_courses=tv_data['current_courses'],
                         upcoming_courses=tv_data['upcoming_courses'],
                         current_week=tv_data['current_week'],
                         current_day=tv_data['current_day'],
                         current_time=tv_data['current_time'])

@app.route('/kiosque/halfday')
@app.route('/kiosque/halfday/<layout>')
def kiosque_halfday(layout="standard"):
    """Vue kiosque - demi-journée avec détection automatique matin/après-midi"""
    kiosque_data = KiosqueService.get_kiosque_halfday_data(schedule_manager, layout)

    return render_template(kiosque_data['template_name'],
                         time_slots_data=kiosque_data['time_slots_data'],
                         time_slots=kiosque_data['time_slots'],
                         current_week=kiosque_data['current_week'],
                         current_day=kiosque_data['current_day'],
                         period=kiosque_data['period'],
                         period_label=kiosque_data['period_label'],
                         time_range=kiosque_data['time_range'],
                         total_courses=kiosque_data['total_courses'],
                         current_time=kiosque_data['current_time'],
                         layout=kiosque_data['layout'])

@app.route('/api/display/current')
def api_display_current():
    """API JSON - cours actuels"""
    now = datetime.now(pytz.timezone("Europe/Paris"))
    current_time = now.strftime('%H:%M')
    current_day = now.strftime('%A')
    day_translation = {
        'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi', 'Friday': 'Vendredi'
    }
    current_day_fr = day_translation.get(current_day, 'Lundi')
    
    week_num = now.isocalendar()[1]
    if now.year == 2025 and week_num >= 36:
        weeks_since_start = week_num - 36
        is_type_A = (weeks_since_start % 2) == 0
        week_type = "A" if is_type_A else "B"
        current_week = f"Semaine {week_num} {week_type}"
    
    all_courses = schedule_manager.get_all_courses()
    current_courses = []
    
    for course in all_courses:
        if (course.week_name == current_week and 
            course.day == current_day_fr and 
            course.assigned_room and
            course.start_time <= current_time <= course.end_time):
            
            course_dict = asdict(course)
            course_dict['room_name'] = schedule_manager.get_room_name(course.assigned_room)
            current_courses.append(course_dict)
    
    return jsonify({
        'current_time': current_time,
        'current_day': current_day_fr,
        'current_week': current_week,
        'courses': current_courses,
        'total_courses': len(current_courses)
    })

# ============== ROUTES ORIGINALES ==============

@app.route('/professor/<path:prof_name>')
def professor_schedule(prof_name):
    """Vue individuelle de l'emploi du temps d'un professeur."""
    schedule_manager.force_sync_data()
    
    # Charger le mapping des salles
    import json
    import os
    room_mapping = {}
    try:
        salle_path = os.path.join(os.path.dirname(__file__), 'data', 'salle.json')
        with open(salle_path, 'r', encoding='utf-8') as f:
            salle_data = json.load(f)
            for room in salle_data.get('rooms', []):
                room_mapping[room['_id']] = room['name']
    except FileNotFoundError:
        pass
    
    # Normaliser le nom du professeur
    from excel_parser import normalize_professor_name
    # Recherche intelligente du nom du professeur
    all_courses = schedule_manager.get_all_courses()
    all_profs = set([c.professor for c in all_courses])
    
    # Essayer d'abord le nom exact
    if prof_name in all_profs:
        final_prof_name = prof_name
    else:
        # Rechercher un nom qui contient le terme recherché
        matches = [p for p in all_profs if prof_name.lower() in p.lower()]
        if matches:
            final_prof_name = matches[0]  # Prendre le premier match
        else:
            # Rechercher dans l'autre sens (terme recherché contient un nom de prof)
            reverse_matches = [p for p in all_profs if p.lower() in prof_name.lower()]
            if reverse_matches:
                final_prof_name = reverse_matches[0]
            else:
                final_prof_name = prof_name  # Garder l'original si aucun match
    
    prof_name = final_prof_name
    
    # Récupérer toutes les semaines réelles des données
    all_courses = schedule_manager.get_all_courses()
    available_weeks = sorted(set([c.week_name for c in all_courses]))
    
    # Créer weeks_list avec les vraies semaines
    weeks_list = []
    for week_name in available_weeks:
        weeks_list.append({
            'name': week_name,
            'date': None,  # Pas de date spécifique
            'full_name': week_name
        })
    
    # Récupérer les cours du professeur pour toutes les semaines
    professor_courses = {}
    
    for week in weeks_list:
        week_name = week['name']
        week_courses = []
        
        for course in all_courses:
            if course.professor == prof_name and course.week_name == week_name:
                # Convertir l'ID de salle en nom de salle
                room_name = "Non attribuée"
                if course.assigned_room:
                    room_name = room_mapping.get(course.assigned_room, f"Salle {course.assigned_room}")
                
                week_courses.append({
                    'day': course.day,
                    'start_time': course.start_time,
                    'end_time': course.end_time,
                    'subject': course.course_type,
                    'room': room_name,
                    'tp_name': getattr(course, 'tp_name', course.course_type)
                })
        
        if week_courses:
            # Trier par jour et heure
            days_order = {'Lundi': 0, 'Mardi': 1, 'Mercredi': 2, 'Jeudi': 3, 'Vendredi': 4}
            week_courses.sort(key=lambda x: (days_order.get(x['day'], 5), x['start_time']))
            professor_courses[week_name] = week_courses
    
    return render_template('professor_schedule.html', 
                         professor_name=prof_name,
                         professor_courses=professor_courses,
                         weeks_list=weeks_list)


@app.route("/export_week_pdf/<week_name>")
def export_week_pdf(week_name):
    """Exporte la semaine en PDF avec une page par professeur."""
    try:
        buffer = PDFExportService.export_week_pdf(schedule_manager, week_name)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"emploi_du_temps_{week_name.replace(' ', '_')}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        return f"Erreur lors de la génération du PDF: {str(e)}", 500

@app.route('/export_day_pdf/<week_name>/<day_name>')
def export_day_pdf(week_name, day_name):
    """Exporte les cours d'une journée en PDF sur une seule page."""
    try:
        buffer = PDFExportService.export_day_pdf(schedule_manager, week_name, day_name)

        filename = f"cours_{day_name}_{week_name.replace(' ', '_')}.pdf"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )

    except Exception as e:
        return f"Erreur lors de la génération du PDF: {str(e)}", 500

@app.route('/day/<week_name>/<day_name>')
def day_view(week_name, day_name):
    """Page d'attribution des salles pour un jour spécifique au format paysage."""
    # Forcer la synchronisation des données en production
    schedule_manager.force_sync_data()
    
    def generate_time_grid():
        """Génère une grille horaire de 8h à 18h avec créneaux d'1 heure"""
        time_slots = []
        for hour in range(8, 18):
            start_time = f"{hour:02d}:00"
            end_time = f"{hour+1:02d}:00"
            time_slots.append({
                'start_time': start_time,
                'end_time': end_time,
                'label': f"{hour}h-{hour+1}h"
            })
        return time_slots

    # Générer la grille horaire
    time_slots = generate_time_grid()
    
    # Récupérer tous les cours pour la semaine et le jour spécifiés
    all_courses_obj = schedule_manager.get_all_courses()
    day_courses = []
    
    for course in all_courses_obj:
        if course.week_name == week_name and course.day == day_name:
            course_dict = asdict(course)
            course_dict['room_name'] = schedule_manager.get_room_name(course.assigned_room) if course.assigned_room else "Non assignée"
            course_dict['prof_color'] = schedule_manager.get_prof_color(course.professor)
            day_courses.append(course_dict)
    
    # Créer une grille pour le jour spécifique
    day_grid = {}
    for time_slot in time_slots:
        day_grid[time_slot['label']] = {
            'time_info': time_slot,
            'courses': []
        }
    
    # Placer les cours dans la grille
    for course in day_courses:
        course_start = course.get('start_time', '')
        
        # Trouver le créneau correspondant
        for time_slot in time_slots:
            slot_start = time_slot['start_time']
            slot_end = time_slot['end_time']
            
            # Vérifier si le cours commence dans ce créneau
            if course_start >= slot_start and course_start < slot_end:
                day_grid[time_slot['label']]['courses'].append(course)
                break
    
    return render_template('day_view.html', 
                         day_grid=day_grid,
                         time_slots=time_slots,
                         day_name=day_name,
                         week_name=week_name,
                         rooms=schedule_manager.rooms,
                         get_room_name=schedule_manager.get_room_name)



@app.route('/test_template')  
def test_template():
    """Route de test pour vérifier les templates."""
    schedule_manager.reload_data()
    summary = schedule_manager.get_canonical_schedules_summary()
    prof_id_mapping = get_all_professors_with_ids()
    
    return render_template('test_template.html', 
                         summary=summary, 
                         prof_id_mapping=prof_id_mapping)



@app.route('/professor/id/<prof_id>')
def professor_by_id(prof_id):
    """Redirects to professor schedule using ID."""
    prof_id_mapping = ProfessorService.load_professor_id_mapping()

    if not prof_id_mapping:
        return render_template('error.html', error="ID mapping not found"), 404

    # Utiliser le service pour trouver le nom du professeur
    prof_name = ProfessorService.find_professor_by_id(prof_id, prof_id_mapping)

    if not prof_name:
        return render_template('error.html', error=f"Professor ID {prof_id} not found"), 404

    # Utiliser la route existante qui fonctionne
    return professor_schedule(prof_name)

def get_all_professors_with_ids():
    """Retourne un dictionnaire {nom: id} pour tous les professeurs."""
    return ProfessorService.get_all_professors_with_ids()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005) 
# ==================== OPTIMISATIONS PLANNING V2 - FINAL ====================

class PlanningCache:
    """Cache pour optimiser les performances du planning"""
    def __init__(self):
        self._academic_weeks = None
        self._courses_cache = {}
        self._last_sync_time = 0
        
    def clear(self):
        self._academic_weeks = None
        self._courses_cache.clear()
        self._last_sync_time = 0
        
    def is_cache_valid(self):
        import time
        try:
            sync_file = "data/.last_sync"
            if os.path.exists(sync_file):
                with open(sync_file, 'r') as f:
                    last_sync = float(f.read().strip())
                return last_sync == self._last_sync_time
        except:
            pass
        return False
        
    def update_sync_time(self):
        import time
        try:
            sync_file = "data/.last_sync"
            if os.path.exists(sync_file):
                with open(sync_file, 'r') as f:
                    self._last_sync_time = float(f.read().strip())
        except:
            self._last_sync_time = time.time()

planning_cache = PlanningCache()

def get_cached_academic_weeks():
    """Génère et cache la liste des semaines académiques"""
    if planning_cache._academic_weeks is None:
        weeks = []
        is_type_A = True
        
        start_date = date(2025, 9, 1)
        for week_num in range(36, 53):
            week_type = "A" if is_type_A else "B"
            week_offset = (week_num - 36) * 7
            monday_date = start_date + timedelta(days=week_offset)
            date_str = monday_date.strftime("%d/%m/%Y")
            
            weeks.append({
                'name': f"Semaine {week_num} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A
            
        january_start = date(2026, 1, 5)
        for week_num in range(1, 36):
            week_type = "A" if is_type_A else "B"
            week_offset = (week_num - 1) * 7
            monday_date = january_start + timedelta(days=week_offset)
            date_str = monday_date.strftime("%d/%m/%Y")
            
            weeks.append({
                'name': f"Semaine {week_num:02d} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num:02d} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A
            
        planning_cache._academic_weeks = weeks
    
    return planning_cache._academic_weeks

def get_courses_for_week_canonical(week_name):
    """Récupère les cours pour une semaine - utilise get_all_courses() avec filtrage"""
    # Vérifier le cache
    if not planning_cache.is_cache_valid():
        planning_cache.clear()
        planning_cache.update_sync_time()
    
    if week_name not in planning_cache._courses_cache:
        # Utiliser get_all_courses() et filtrer par semaine
        all_courses = schedule_manager.get_all_courses()
        courses = [course for course in all_courses if course.week_name == week_name]
        
        # Mettre en cache
        planning_cache._courses_cache[week_name] = courses
        print(f"🔍 Cache mis à jour: {len(courses)} cours pour {week_name}")
    
    return planning_cache._courses_cache[week_name]

def build_weekly_grid_optimized(courses_for_week, time_slots, days_order):
    """Construction optimisée de la grille hebdomadaire"""
    time_slots_minutes = []
    for slot in time_slots:
        time_slots_minutes.append({
            'label': slot['label'],
            'start_min': TimeSlotService.time_to_minutes(slot['start_time']),
            'end_min': TimeSlotService.time_to_minutes(slot['end_time']),
            'slot_info': slot
        })
    
    weekly_grid = {}
    for day in days_order:
        weekly_grid[day] = {}
        for slot in time_slots_minutes:
            weekly_grid[day][slot['label']] = {
                'time_info': slot['slot_info'],
                'courses': []
            }
    
    courses_by_day = {}
    for day in days_order:
        courses_by_day[day] = []
    
    prof_working_days = schedule_manager.get_prof_working_days()
    for course in courses_for_week:
        if course.day in courses_by_day:
            course_dict = asdict(course)
            course_dict['working_days'] = prof_working_days.get(course.professor, [])
            courses_by_day[course.day].append(course_dict)
    
    for day in days_order:
        day_courses = courses_by_day[day]
        original_courses = [c for c in day_courses if not c['course_id'].startswith('custom_')]
        custom_tps = [c for c in day_courses if c['course_id'].startswith('custom_')]
        
        original_lookup = {}
        for course in original_courses:
            key = (course['professor'], course['raw_time_slot'])
            if key not in original_lookup:
                original_lookup[key] = []
            original_lookup[key].append(course)
        
        for course in day_courses:
            course['related_tps'] = []
        
        standalone_tps = []
        for tp in custom_tps:
            key = (tp['professor'], tp['raw_time_slot'])
            matching_originals = original_lookup.get(key, [])
            if matching_originals:
                matching_originals[0]['related_tps'].append(tp)
            else:
                standalone_tps.append(tp)
        
        courses_to_place = original_courses + standalone_tps
        
        for course in courses_to_place:
            course_start_min = time_to_minutes(course['start_time'])
            course_end_min = time_to_minutes(course['end_time'])
            
            primary_slot = None
            spans_slots = []
            
            for slot in time_slots_minutes:
                if not (course_end_min <= slot['start_min'] or course_start_min >= slot['end_min']):
                    spans_slots.append(slot['label'])
                    
                    if course_start_min >= slot['start_min'] and course_start_min < slot['end_min'] and primary_slot is None:
                        primary_slot = slot['label']
            
            if primary_slot:
                course['is_primary_slot'] = True
                course['spans_slots'] = spans_slots
                
                for slot_label in spans_slots:
                    if slot_label == primary_slot:
                        weekly_grid[day][slot_label]['courses'].append(course)
                    else:
                        continuation_course = course.copy()
                        continuation_course['is_continuation'] = True
                        continuation_course['primary_slot'] = primary_slot
                        weekly_grid[day][slot_label]['courses'].append(continuation_course)
    
    return weekly_grid

@app.route("/planning_v2_fast")
@app.route("/planning_v2_fast/<week_name>")
def planning_v2_fast(week_name=None):
    """Planning V2 Optimisé - MÊME DONNÉES que /week/"""
    import time
    start_time = time.time()
    
    # Sync légère
    try:
        sync_file = "data/.last_sync"
        if os.path.exists(sync_file):
            with open(sync_file, 'r') as f:
                last_sync = float(f.read().strip())
            if time.time() - last_sync > 300:
                schedule_manager.force_sync_data()
                planning_cache.clear()
        else:
            schedule_manager.force_sync_data()
            planning_cache.clear()
    except Exception as e:
        print(f"Erreur sync légère: {e}")
        schedule_manager.force_sync_data()
        planning_cache.clear()
    
    # Vérification cohérence
    try:
        room_assignments_count = len(schedule_manager.room_assignments)
        if room_assignments_count == 0:
            print("Warning: Aucune attribution de salle trouvée")
    except Exception as e:
        print(f"Erreur vérification cohérence: {e}")
    
    weeks_to_display = get_cached_academic_weeks()
    
    if not weeks_to_display:
        return "Erreur lors de la génération du calendrier.", 500
    
    # Détermination de la semaine courante
    if week_name is None:
        today = datetime.now(pytz.timezone("Europe/Paris")).date()
        week_num = today.isocalendar()[1]
        
        if today.year == 2025 and week_num >= 36:
            weeks_since_start = week_num - 36
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            week_name = f"Semaine {week_num} {week_type}"
        elif today.year == 2026 and week_num <= 35:
            weeks_since_start = 17 + week_num - 1
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            week_name = f"Semaine {week_num:02d} {week_type}"
        else:
            week_name = weeks_to_display[0]['name']
    
    # Trouver les infos de la semaine
    current_week_info = None
    for week_info in weeks_to_display:
        if week_info['name'] == week_name:
            current_week_info = week_info
            break
    
    if not current_week_info:
        current_week_info = weeks_to_display[0]
        week_name = current_week_info['name']
    
    # Grille horaire
    def generate_time_grid():
        time_slots = []
        for hour in range(8, 18):
            start_time = f"{hour:02d}:00"
            end_time = f"{hour+1:02d}:00"
            time_slots.append({
                'start_time': start_time,
                'end_time': end_time,
                'label': f"{hour}h-{hour+1}h"
            })
        return time_slots
    
    time_slots = generate_time_grid()
    days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
    
    # Récupération des cours - MÊME SOURCE que /week/
    courses_for_week = get_courses_for_week_canonical(week_name)
    print(f"🔢 Cours générés: {len(courses_for_week)}")
    
    # Construction de la grille
    weekly_grid = build_weekly_grid_optimized(courses_for_week, time_slots, days_order)
    
    # Mesure des performances
    end_time = time.time()
    processing_time = end_time - start_time
    print(f"⚡ Planning V2 Fast - Traitement en {processing_time:.3f}s pour {len(courses_for_week)} cours")
    
    return render_template('planning_v2.html',
                         weekly_grid=weekly_grid,
                         time_slots=time_slots,
                         days_order=days_order,
                         rooms=schedule_manager.rooms,
                         get_room_name=schedule_manager.get_room_name,
                         all_weeks=weeks_to_display,
                         current_week=week_name,
                         current_week_info=current_week_info,
                         all_professors=schedule_manager.get_normalized_professors_list(),
                         processing_time=processing_time)

