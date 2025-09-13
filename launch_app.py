#!/usr/bin/env python3
"""
Script de lancement simplifié pour l'application de gestion d'emploi du temps
"""

import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    required_packages = ['flask', 'pandas', 'openpyxl']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Dépendances manquantes : {', '.join(missing_packages)}")
        print("📦 Installation des dépendances...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        return False
    return True

def check_data_files():
    """Vérifie que les fichiers de données nécessaires existent"""
    required_files = [
        'data/extracted_schedules.json',
        'data/professors_canonical_schedule.json',
        'data/room_assignments.json',
        'data/salle.json'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Fichiers de données manquants : {', '.join(missing_files)}")
        return False
    
    print("✅ Tous les fichiers de données sont présents")
    return True

def start_application():
    """Démarre l'application Flask"""
    print("🚀 Démarrage de l'application...")
    
    # Arrêter l'application si elle tourne déjà
    try:
        subprocess.run(['pkill', '-f', 'app_new.py'], check=False)
        time.sleep(1)
    except:
        pass
    
    # Démarrer l'application en arrière-plan
    process = subprocess.Popen([sys.executable, 'app_new.py'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    
    # Attendre que l'application démarre
    print("⏳ Attente du démarrage de l'application...")
    time.sleep(5)
    
    # Vérifier que l'application répond
    try:
        response = requests.get('http://localhost:5005', timeout=10)
        if response.status_code == 200:
            print("✅ Application démarrée avec succès !")
            print("\n🌐 URLs d'accès :")
            print("   • Interface principale : http://localhost:5005")
            print("   • Interface étudiant : http://localhost:5005/student")
            print("   • API REST : http://localhost:5005/api/")
            print("\n💡 Appuyez sur Ctrl+C pour arrêter l'application")
            return process
        else:
            print(f"❌ L'application ne répond pas correctement (code: {response.status_code})")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Impossible de se connecter à l'application : {e}")
        return None

def main():
    """Fonction principale"""
    print("🎯 Lancement de l'application de gestion d'emploi du temps")
    print("=" * 60)
    
    # Vérifications préalables
    if not check_dependencies():
        print("❌ Échec de l'installation des dépendances")
        return 1
    
    if not check_data_files():
        print("❌ Fichiers de données manquants")
        return 1
    
    # Démarrage de l'application
    process = start_application()
    if not process:
        return 1
    
    try:
        # Garder l'application en vie
        process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Arrêt de l'application...")
        process.terminate()
        process.wait()
        print("✅ Application arrêtée")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
