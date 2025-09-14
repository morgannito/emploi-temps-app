#!/usr/bin/env python3
"""
Script de surveillance automatique pour l'application d'emploi du temps
Vérifie la santé de l'application et redémarre automatiquement si nécessaire
"""

import subprocess
import time
import logging
import requests
import psutil
import os
from datetime import datetime

# Configuration
APP_NAME = "emploi_du_temps_isa"
APP_URL = "http://localhost:5005/"
HEALTH_CHECK_ENDPOINT = "http://localhost:5005/student"
MAX_MEMORY_MB = 800  # 800MB par processus
CHECK_INTERVAL = 60  # 60 secondes
MAX_RESTARTS_PER_HOUR = 3

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor.log'),
        logging.StreamHandler()
    ]
)

class AppMonitor:
    def __init__(self):
        self.restart_count = 0
        self.last_restart_time = None
        
    def log_info(self, message):
        """Log avec timestamp"""
        logging.info(f"[MONITOR] {message}")
        
    def log_error(self, message):
        """Log d'erreur avec timestamp"""
        logging.error(f"[MONITOR] {message}")
        
    def check_supervisor_status(self):
        """Vérifie le statut de l'application dans Supervisor"""
        try:
            result = subprocess.run(
                ['sudo', 'supervisorctl', 'status', APP_NAME],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                status_line = result.stdout.strip()
                if 'RUNNING' in status_line:
                    return True, status_line
                else:
                    return False, status_line
            else:
                return False, f"Erreur supervisorctl: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Timeout lors de la vérification Supervisor"
        except Exception as e:
            return False, f"Erreur lors de la vérification Supervisor: {e}"
    
    def check_http_health(self):
        """Vérifie si l'application répond aux requêtes HTTP"""
        try:
            response = requests.get(HEALTH_CHECK_ENDPOINT, timeout=10)
            if response.status_code == 200:
                return True, f"HTTP OK - Status: {response.status_code}"
            else:
                return False, f"HTTP Error - Status: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"HTTP Error: {e}"
    
    def check_memory_usage(self):
        """Vérifie l'utilisation mémoire des processus Gunicorn"""
        try:
            gunicorn_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    if 'gunicorn' in proc.info['name'].lower():
                        memory_mb = proc.info['memory_info'].rss / 1024 / 1024
                        gunicorn_processes.append({
                            'pid': proc.info['pid'],
                            'memory_mb': memory_mb
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not gunicorn_processes:
                return False, "Aucun processus Gunicorn trouvé"
            
            # Vérifier si un processus utilise trop de mémoire
            high_memory_processes = [
                p for p in gunicorn_processes 
                if p['memory_mb'] > MAX_MEMORY_MB
            ]
            
            if high_memory_processes:
                return False, f"Processus avec mémoire élevée: {high_memory_processes}"
            
            total_memory = sum(p['memory_mb'] for p in gunicorn_processes)
            return True, f"OK - {len(gunicorn_processes)} processus, {total_memory:.1f}MB total"
            
        except Exception as e:
            return False, f"Erreur lors de la vérification mémoire: {e}"
    
    def restart_application(self):
        """Redémarre l'application via Supervisor"""
        try:
            # Vérifier le nombre de redémarrages
            if self.restart_count >= MAX_RESTARTS_PER_HOUR:
                if self.last_restart_time:
                    time_since_last = time.time() - self.last_restart_time
                    if time_since_last < 3600:  # 1 heure
                        self.log_error(f"Trop de redémarrages ({self.restart_count}) dans l'heure")
                        return False
            
            self.log_info("Redémarrage de l'application...")
            
            # Arrêter l'application
            subprocess.run(['sudo', 'supervisorctl', 'stop', APP_NAME], check=True)
            time.sleep(5)
            
            # Démarrer l'application
            subprocess.run(['sudo', 'supervisorctl', 'start', APP_NAME], check=True)
            
            # Mettre à jour les compteurs
            self.restart_count += 1
            self.last_restart_time = time.time()
            
            self.log_info("Application redémarrée avec succès")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log_error(f"Erreur lors du redémarrage: {e}")
            return False
        except Exception as e:
            self.log_error(f"Erreur inattendue lors du redémarrage: {e}")
            return False
    
    def reset_restart_counter(self):
        """Réinitialise le compteur de redémarrages si plus d'une heure s'est écoulée"""
        if self.last_restart_time:
            time_since_last = time.time() - self.last_restart_time
            if time_since_last > 3600:  # 1 heure
                self.restart_count = 0
                self.log_info("Compteur de redémarrages réinitialisé")
    
    def run_health_check(self):
        """Exécute une vérification complète de la santé de l'application"""
        self.log_info("=== Début de la vérification de santé ===")
        
        # Réinitialiser le compteur si nécessaire
        self.reset_restart_counter()
        
        # Vérifier le statut Supervisor
        supervisor_ok, supervisor_msg = self.check_supervisor_status()
        self.log_info(f"Supervisor: {supervisor_msg}")
        
        # Vérifier la santé HTTP
        http_ok, http_msg = self.check_http_health()
        self.log_info(f"HTTP: {http_msg}")
        
        # Vérifier l'utilisation mémoire
        memory_ok, memory_msg = self.check_memory_usage()
        self.log_info(f"Mémoire: {memory_msg}")
        
        # Décider si un redémarrage est nécessaire
        needs_restart = False
        restart_reason = []
        
        if not supervisor_ok:
            needs_restart = True
            restart_reason.append("Supervisor")
        
        if not http_ok:
            needs_restart = True
            restart_reason.append("HTTP")
        
        if not memory_ok:
            needs_restart = True
            restart_reason.append("Mémoire")
        
        if needs_restart:
            self.log_error(f"Redémarrage nécessaire - Raisons: {', '.join(restart_reason)}")
            if self.restart_application():
                self.log_info("Redémarrage réussi")
            else:
                self.log_error("Échec du redémarrage")
        else:
            self.log_info("Application en bonne santé")
        
        self.log_info("=== Fin de la vérification de santé ===\n")
    
    def run_monitoring_loop(self):
        """Boucle principale de surveillance"""
        self.log_info("Démarrage du moniteur d'application")
        self.log_info(f"Vérification toutes les {CHECK_INTERVAL} secondes")
        
        while True:
            try:
                self.run_health_check()
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                self.log_info("Arrêt du moniteur demandé")
                break
            except Exception as e:
                self.log_error(f"Erreur dans la boucle de surveillance: {e}")
                time.sleep(CHECK_INTERVAL)

def main():
    """Point d'entrée principal"""
    # Créer le dossier de logs s'il n'existe pas
    os.makedirs('logs', exist_ok=True)
    
    monitor = AppMonitor()
    
    # Vérification initiale
    monitor.log_info("Vérification initiale de l'application...")
    monitor.run_health_check()
    
    # Démarrer la boucle de surveillance
    monitor.run_monitoring_loop()

if __name__ == "__main__":
    main()
