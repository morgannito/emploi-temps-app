#!/usr/bin/env python3
"""
Parseur pour extraire les horaires des professeurs depuis le fichier Excel
model_emploiedu_temps.xlsm
"""

import pandas as pd
import re
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

def normalize_professor_name(name: str) -> str:
    """Normalise le nom d'un professeur pour éviter les doublons."""
    if not isinstance(name, str) or not name:
        return ""
    
    name = name.strip()
    
    # Supprimer les préfixes courants de manière insensible à la casse
    prefixes_to_remove = ['Mme ', 'M ', 'Mlle ', 'Mr ', 'Mrs ', 'Ms ']
    for prefix in prefixes_to_remove:
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix):].strip()
            break
            
    # Gérer les noms composés avec des slashes (ex: "Prof1 / Prof2")
    if '/' in name:
        name = name.split('/')[0].strip()
        
    # Mettre en casse Titre et supprimer les espaces multiples
    # "TRipier" -> "Tripier", "tripier" -> "Tripier"
    return ' '.join(name.split()).title()

class ExcelScheduleParser:
    """Parseur pour analyser le fichier Excel d'emploi du temps"""
    
    def __init__(self, excel_file: str = "data/model_emploiedu_temps.xlsm"):
        """
        Initialise le parseur
        
        Args:
            excel_file: Chemin vers le fichier Excel
        """
        self.excel_file = excel_file
    
    def parse_time_range(self, time_str: str) -> Optional[Tuple[str, str, float]]:
        """
        Parse un créneau horaire comme '9h-12h' ou '13h-16h30'
        
        Args:
            time_str: Chaîne d'horaire à parser
            
        Returns:
            Tuple (heure_debut, heure_fin, duree_heures) ou None si erreur
        """
        if not time_str or pd.isna(time_str):
            return None
            
        time_str = str(time_str).strip().replace('H', 'h')
        
        # Patterns pour matcher '9h-12h', '13h-16h30', '8h', etc.
        pattern_range = re.match(r'(\d{1,2})h(?:(\d{0,2}))?\s*-\s*(\d{1,2})h(?:(\d{0,2}))?', time_str)
        pattern_single = re.match(r'(\d{1,2})h', time_str)
        
        if pattern_range:
            start_hour = int(pattern_range.group(1))
            start_min = int(pattern_range.group(2)) if pattern_range.group(2) else 0
            end_hour = int(pattern_range.group(3))
            end_min = int(pattern_range.group(4)) if pattern_range.group(4) else 0
        elif pattern_single and '-' not in time_str:
            # Gérer les cas comme "8h" (considéré comme 1h)
            start_hour = int(pattern_single.group(1))
            start_min = 0
            end_hour = start_hour + 1
            end_min = 0
        else:
            return None
            
        start_time = f"{start_hour:02d}:{start_min:02d}"
        end_time = f"{end_hour:02d}:{end_min:02d}"
        
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = datetime.strptime(end_time, "%H:%M")
        duration = (end_dt - start_dt).total_seconds() / 3600
        
        return start_time, end_time, duration

    def parse_sheet(self, sheet_name: str) -> Dict:
        """
        Parse une feuille Excel spécifique pour extraire les horaires par jour.
        """
        try:
            df = pd.read_excel(self.excel_file, sheet_name=sheet_name, header=None)
            week_data = {'week_name': sheet_name, 'professors': {}}
            days_of_week = ['LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI']

            # Trouver tous les blocs d'emploi du temps en cherchant "Professeur"
            prof_headers = []
            for r_idx, row in df.iterrows():
                for c_idx, cell in enumerate(row):
                    if isinstance(cell, str) and cell.strip() == 'Professeur':
                        prof_headers.append((r_idx, c_idx))

            for r_idx, c_idx in prof_headers:
                # Déterminer le jour du bloc en regardant au-dessus
                day_found = "Indéterminé"
                for i in range(r_idx, -1, -1):
                    # Le nom du jour est souvent dans une cellule fusionnée à gauche
                    row_slice = df.iloc[i, max(0, c_idx - 5):c_idx + 1]
                    for cell in row_slice:
                        if isinstance(cell, str) and cell.strip() in days_of_week:
                            day_found = cell.strip().capitalize()
                            break
                    if day_found != "Indéterminé":
                        break
                
                # Parser les cours sous cet en-tête
                for i in range(r_idx + 1, len(df)):
                    row_data = df.iloc[i]
                    prof_name = str(row_data.get(c_idx, '')).strip()
                    time_slot = str(row_data.get(c_idx + 1, '')).strip()

                    if not prof_name or prof_name.lower() in ['professeur', 'nan', 'matin', 'apres-midi'] or not self.parse_time_range(time_slot):
                        break  # Fin du bloc de cours

                    parsed_time = self.parse_time_range(time_slot)
                    if parsed_time:
                        start_time, end_time, duration = parsed_time
                        
                        if prof_name not in week_data['professors']:
                            week_data['professors'][prof_name] = []
                        
                        course_data = {
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration_hours': duration,
                            'course_type': str(row_data.get(c_idx + 2, '')).strip(),
                            'nb_students': str(row_data.get(c_idx + 3, '')).strip(),
                            'assigned_room': str(row_data.get(c_idx + 5, '')).strip() if pd.notna(row_data.get(c_idx + 5)) else None,
                            'day': day_found,
                            'raw_time_slot': time_slot
                        }
                        week_data['professors'][prof_name].append(course_data)
            
            return week_data
            
        except Exception as e:
            print(f"❌ Erreur lors du parsing de {sheet_name}: {e}")
            return {}
    
    def extract_all_schedules(self) -> Dict:
        """
        Extrait tous les emplois du temps de toutes les feuilles
        
        Returns:
            Dictionnaire avec tous les emplois du temps
        """
        try:
            xl_file = pd.ExcelFile(self.excel_file)
            all_schedules = {}
            
            print(f"📊 Extraction des emplois du temps...")
            
            # Parser quelques feuilles pour commencer
            sheets_to_parse = xl_file.sheet_names[:3]  # Prendre les 3 premières feuilles
            
            for sheet_name in sheets_to_parse:
                print(f"📋 Parsing de la feuille: {sheet_name}")
                week_data = self.parse_sheet(sheet_name)
                
                if week_data and week_data.get('professors'):
                    all_schedules[sheet_name] = week_data
                    
                    # Afficher un résumé
                    prof_count = len(week_data['professors'])
                    total_courses = sum(len(courses) for courses in week_data['professors'].values())
                    print(f"   ✅ {prof_count} professeurs, {total_courses} créneaux")
                else:
                    print(f"   ❌ Aucune donnée trouvée")
            
            return all_schedules
            
        except Exception as e:
            print(f"❌ Erreur lors de l'extraction: {e}")
            return {}
    
    def save_extracted_data(self, output_file: str = "data/extracted_schedules.json"):
        """
        Sauvegarde les données extraites dans un fichier JSON
        
        Args:
            output_file: Fichier de sortie
        """
        schedules = self.extract_all_schedules()
        
        if schedules:
            # Nettoyer les données avant de sauvegarder
            for week_data in schedules.values():
                for prof, courses in list(week_data['professors'].items()):
                    if not courses:
                        del week_data['professors'][prof]

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(schedules, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Données sauvegardées dans {output_file}")
            
            # Afficher un résumé
            total_weeks = len(schedules)
            total_profs = len(set(prof for week in schedules.values() 
                                 for prof in week['professors'].keys()))
            total_courses = sum(len(courses) for week in schedules.values() 
                               for courses in week['professors'].values())
            
            print(f"📊 Résumé de l'extraction:")
            print(f"   📅 Semaines: {total_weeks}")
            print(f"   👨‍🏫 Professeurs uniques: {total_profs}")
            print(f"   📚 Créneaux de cours: {total_courses}")
        else:
            print("❌ Aucune donnée à sauvegarder")

def main():
    """Fonction principale pour tester le parseur"""
    parser = ExcelScheduleParser()
    parser.save_extracted_data()

if __name__ == "__main__":
    main() 