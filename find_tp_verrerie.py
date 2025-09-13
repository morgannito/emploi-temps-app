#!/usr/bin/env python3
"""
Script pour trouver les informations complètes du TP verrerie
"""

import requests
import json
import hashlib

def find_tp_verrerie():
    """Trouve les informations du TP verrerie"""
    
    # Configuration
    BASE_URL = "http://localhost:5005"
    API_GET_TP = f"{BASE_URL}/api/courses/get_tp_names"
    
    print("🔍 Recherche du TP verrerie...")
    
    try:
        # Récupérer tous les noms de TP
        response = requests.get(API_GET_TP, headers={
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success') and result.get('tp_names'):
                tp_names = result.get('tp_names', {})
                
                # Chercher le TP verrerie
                verrerie_course_id = None
                for course_id, tp_name in tp_names.items():
                    if 'verrerie' in tp_name.lower():
                        verrerie_course_id = course_id
                        print(f"✅ TP verrerie trouvé avec l'ID: {course_id}")
                        break
                
                if verrerie_course_id:
                    print(f"📝 Nom du TP: {tp_names[verrerie_course_id]}")
                    
                    # Analyser l'ID pour comprendre sa structure
                    print(f"🔍 Analyse de l'ID: {verrerie_course_id}")
                    
                    # L'ID est généré à partir de: {semaine}_{professeur}_{créneau}_{index}
                    # course_050ccdbe0a170ce8 = hash MD5 de cette combinaison
                    
                    # Essayer de trouver des informations dans les données canoniques
                    try:
                        with open('data/professors_canonical_schedule.json', 'r') as f:
                            canonical_data = json.load(f)
                        
                        print("\n📊 Recherche dans les emplois du temps canoniques...")
                        
                        # Chercher des cours qui pourraient correspondre
                        for prof_name, prof_data in canonical_data.items():
                            courses = prof_data.get('courses', [])
                            for course in courses:
                                if 'verrerie' in str(course).lower():
                                    print(f"🎯 Professeur: {prof_name}")
                                    print(f"   Jour: {course.get('day')}")
                                    print(f"   Créneau: {course.get('raw_time_slot')}")
                                    print(f"   Type: {course.get('course_type')}")
                                    return
                        
                        print("ℹ️ TP verrerie non trouvé dans les emplois du temps canoniques")
                        
                    except FileNotFoundError:
                        print("❌ Fichier professors_canonical_schedule.json non trouvé")
                    
                    # Essayer de trouver dans les cours personnalisés
                    try:
                        with open('data/custom_courses.json', 'r') as f:
                            custom_data = json.load(f)
                        
                        print("\n📊 Recherche dans les cours personnalisés...")
                        
                        for course in custom_data:
                            if 'verrerie' in str(course).lower():
                                print(f"🎯 Cours personnalisé trouvé:")
                                print(f"   Professeur: {course.get('professor')}")
                                print(f"   Jour: {course.get('day')}")
                                print(f"   Créneau: {course.get('raw_time_slot')}")
                                print(f"   Semaine: {course.get('week_name')}")
                                return
                        
                        print("ℹ️ TP verrerie non trouvé dans les cours personnalisés")
                        
                    except FileNotFoundError:
                        print("❌ Fichier custom_courses.json non trouvé")
                    
                    # Essayer de trouver dans les emplois du temps extraits
                    try:
                        with open('data/extracted_schedules.json', 'r') as f:
                            extracted_data = json.load(f)
                        
                        print("\n📊 Recherche dans les emplois du temps extraits...")
                        
                        for prof_name, prof_data in extracted_data.items():
                            courses = prof_data.get('courses', [])
                            for course in courses:
                                if 'verrerie' in str(course).lower():
                                    print(f"🎯 Professeur: {prof_name}")
                                    print(f"   Jour: {course.get('day')}")
                                    print(f"   Créneau: {course.get('raw_time_slot')}")
                                    print(f"   Type: {course.get('course_type')}")
                                    return
                        
                        print("ℹ️ TP verrerie non trouvé dans les emplois du temps extraits")
                        
                    except FileNotFoundError:
                        print("❌ Fichier extracted_schedules.json non trouvé")
                    
                    print("\n💡 Le TP verrerie semble être un TP ajouté manuellement via l'interface web")
                    print("   Pour connaître son jour, connectez-vous à l'interface web")
                    print(f"   URL: {BASE_URL}")
                    
                else:
                    print("❌ TP verrerie non trouvé")
                    
            else:
                print(f"❌ Erreur API: {result.get('error')}")
        else:
            print(f"❌ Erreur HTTP: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur réseau: {e}")
    except Exception as e:
        print(f"💥 Erreur inattendue: {e}")

if __name__ == "__main__":
    find_tp_verrerie()
