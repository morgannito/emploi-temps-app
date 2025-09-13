#!/usr/bin/env python3
"""
Script pour nettoyer les attributions de salles orphelines.
Supprime les attributions de salles qui ne correspondent plus à des cours existants.
"""

import json
import os
import hashlib
from typing import List, Dict

class ProfessorCourse:
    """Représente un cours d'un professeur"""
    def __init__(self, professor: str, start_time: str, end_time: str, 
                 duration_hours: float, course_type: str, nb_students: str,
                 assigned_room: str, day: str, raw_time_slot: str, 
                 week_name: str, course_id: str):
        self.professor = professor
        self.start_time = start_time
        self.end_time = end_time
        self.duration_hours = duration_hours
        self.course_type = course_type
        self.nb_students = nb_students
        self.assigned_room = assigned_room
        self.day = day
        self.raw_time_slot = raw_time_slot
        self.week_name = week_name
        self.course_id = course_id

def load_data():
    """Charge toutes les données nécessaires"""
    data = {}
    
    # Charger les emplois du temps canoniques
    canonical_file = "data/professors_canonical_schedule.json"
    if os.path.exists(canonical_file):
        with open(canonical_file, 'r', encoding='utf-8') as f:
            data['canonical_schedules'] = json.load(f)
    
    # Charger les attributions de salles
    assignments_file = "data/room_assignments.json"
    if os.path.exists(assignments_file):
        with open(assignments_file, 'r', encoding='utf-8') as f:
            data['room_assignments'] = json.load(f)
    
    # Charger les cours personnalisés
    custom_file = "data/custom_courses.json"
    if os.path.exists(custom_file):
        with open(custom_file, 'r', encoding='utf-8') as f:
            data['custom_courses'] = json.load(f)
    
    return data

def generate_all_course_ids(canonical_schedules: Dict, custom_courses: List[Dict]) -> set:
    """Génère tous les IDs de cours existants"""
    course_ids = set()
    
    # Générer les semaines académiques
    def generate_academic_weeks():
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
    
    academic_weeks = generate_academic_weeks()
    
    # Pour chaque professeur et chaque semaine, créer les IDs de cours
    for prof_name, prof_data in canonical_schedules.items():
        courses = prof_data.get('courses', []) if isinstance(prof_data, dict) else prof_data
        for week_name in academic_weeks:
            for i, course_data in enumerate(courses):
                # L'ID doit être unique et déterministe
                raw_id = f"{week_name}_{prof_name}_{course_data['raw_time_slot']}_{i}"
                course_id = f"course_{hashlib.md5(raw_id.encode()).hexdigest()[:16]}"
                course_ids.add(course_id)
    
    # Ajouter les IDs des cours personnalisés
    for custom_course in custom_courses:
        course_id = custom_course.get('course_id')
        if course_id:
            course_ids.add(course_id)
    
    return course_ids

def cleanup_orphan_assignments():
    """Nettoie les attributions de salles orphelines"""
    print("🧹 Nettoyage des attributions de salles orphelines...")
    
    # Charger les données
    data = load_data()
    canonical_schedules = data.get('canonical_schedules', {})
    room_assignments = data.get('room_assignments', {})
    custom_courses = data.get('custom_courses', [])
    
    print(f"📊 État initial:")
    print(f"   - Attributions de salles: {len(room_assignments)}")
    
    # Générer tous les IDs de cours existants
    valid_course_ids = generate_all_course_ids(canonical_schedules, custom_courses)
    print(f"   - Cours valides: {len(valid_course_ids)}")
    
    # Identifier les attributions orphelines
    orphan_assignments = []
    for course_id in room_assignments.keys():
        if course_id not in valid_course_ids:
            orphan_assignments.append(course_id)
    
    print(f"   - Attributions orphelines: {len(orphan_assignments)}")
    
    if not orphan_assignments:
        print("✅ Aucune attribution orpheline trouvée. Rien à nettoyer.")
        return
    
    # Afficher les attributions orphelines
    print(f"\n🗑️  Attributions orphelines à supprimer:")
    for course_id in orphan_assignments:
        room_id = room_assignments[course_id]
        print(f"   - {course_id} → Salle {room_id}")
    
    # Demander confirmation
    response = input(f"\n❓ Supprimer {len(orphan_assignments)} attribution(s) orpheline(s) ? (y/N): ")
    if response.lower() != 'y':
        print("❌ Nettoyage annulé.")
        return
    
    # Supprimer les attributions orphelines
    for course_id in orphan_assignments:
        del room_assignments[course_id]
    
    # Sauvegarder les données nettoyées
    assignments_file = "data/room_assignments.json"
    with open(assignments_file, 'w', encoding='utf-8') as f:
        json.dump(room_assignments, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Nettoyage terminé!")
    print(f"   - Attributions supprimées: {len(orphan_assignments)}")
    print(f"   - Attributions restantes: {len(room_assignments)}")
    
    # Vérifier la cohérence après nettoyage
    valid_assignments = sum(1 for course_id in room_assignments.keys() if course_id in valid_course_ids)
    print(f"   - Attributions valides: {valid_assignments}")
    
    if valid_assignments == len(room_assignments):
        print("🎉 Cohérence parfaite atteinte!")
    else:
        print("⚠️  Il reste encore des incohérences.")

if __name__ == "__main__":
    cleanup_orphan_assignments()
