#!/bin/bash

# Script de gestion de l'application avec Supervisor pour une surveillance robuste
# Usage: ./manage_app_supervisor.sh [start|stop|restart|status|logs|monitor]

APP_NAME="emploi_du_temps_isa"
SUPERVISOR_CONFIG="/etc/supervisor/conf.d/emploi_du_temps_isa.conf"
SUPERVISOR_PROGRAM="emploi_du_temps_isa"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages colorés
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Fonction pour créer les dossiers nécessaires
create_dirs() {
    mkdir -p logs
    mkdir -p data
    print_status "Dossiers créés"
}

# Fonction pour installer la configuration Supervisor
install_supervisor_config() {
    print_header "Installation de la configuration Supervisor"
    
    if [ ! -f "supervisor_emploi_temps.conf" ]; then
        print_error "Fichier supervisor_emploi_temps.conf non trouvé"
        exit 1
    fi
    
    # Copier la configuration
    sudo cp supervisor_emploi_temps.conf "$SUPERVISOR_CONFIG"
    
    # Recharger la configuration Supervisor
    sudo supervisorctl reread
    sudo supervisorctl update
    
    print_status "Configuration Supervisor installée"
}

# Fonction pour démarrer l'application avec Supervisor
start_app() {
    print_header "Démarrage de l'application avec Supervisor"
    
    create_dirs
    
    # Vérifier si la configuration Supervisor est installée
    if [ ! -f "$SUPERVISOR_CONFIG" ]; then
        print_warning "Configuration Supervisor non trouvée, installation..."
        install_supervisor_config
    fi
    
    # Démarrer l'application
    sudo supervisorctl start "$SUPERVISOR_PROGRAM"
    
    if [ $? -eq 0 ]; then
        print_status "Application démarrée avec succès"
        print_status "URL: http://172.19.202.13:5005"
        print_status "Logs: logs/supervisor_stdout.log"
    else
        print_error "Erreur lors du démarrage"
        sudo supervisorctl status "$SUPERVISOR_PROGRAM"
    fi
}

# Fonction pour arrêter l'application
stop_app() {
    print_header "Arrêt de l'application"
    
    sudo supervisorctl stop "$SUPERVISOR_PROGRAM"
    
    if [ $? -eq 0 ]; then
        print_status "Application arrêtée avec succès"
    else
        print_error "Erreur lors de l'arrêt"
    fi
}

# Fonction pour redémarrer l'application
restart_app() {
    print_header "Redémarrage de l'application"
    
    sudo supervisorctl restart "$SUPERVISOR_PROGRAM"
    
    if [ $? -eq 0 ]; then
        print_status "Application redémarrée avec succès"
    else
        print_error "Erreur lors du redémarrage"
    fi
}

# Fonction pour afficher le statut
status_app() {
    print_header "Statut de l'application"
    
    echo "=== Statut Supervisor ==="
    sudo supervisorctl status "$SUPERVISOR_PROGRAM"
    
    echo ""
    echo "=== Processus en cours ==="
    ps aux | grep gunicorn | grep -v grep
    
    echo ""
    echo "=== Utilisation mémoire ==="
    free -h
    
    echo ""
    echo "=== Utilisation CPU ==="
    top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1
}

# Fonction pour afficher les logs
show_logs() {
    print_header "Logs de l'application"
    
    echo "=== Logs Supervisor (stdout) ==="
    if [ -f "logs/supervisor_stdout.log" ]; then
        tail -n 50 logs/supervisor_stdout.log
    else
        print_warning "Fichier de log stdout non trouvé"
    fi
    
    echo ""
    echo "=== Logs Supervisor (stderr) ==="
    if [ -f "logs/supervisor_stderr.log" ]; then
        tail -n 50 logs/supervisor_stderr.log
    else
        print_warning "Fichier de log stderr non trouvé"
    fi
    
    echo ""
    echo "=== Logs Gunicorn ==="
    if [ -f "logs/gunicorn_error.log" ]; then
        tail -n 30 logs/gunicorn_error.log
    else
        print_warning "Fichier de log Gunicorn non trouvé"
    fi
}

# Fonction pour surveiller l'application en temps réel
monitor_app() {
    print_header "Surveillance en temps réel"
    print_status "Appuyez sur Ctrl+C pour arrêter la surveillance"
    
    watch -n 2 '
        echo "=== $(date) ==="
        echo "Statut Supervisor:"
        sudo supervisorctl status emploi_du_temps_isa
        echo ""
        echo "Processus Gunicorn:"
        ps aux | grep gunicorn | grep -v grep
        echo ""
        echo "Mémoire utilisée:"
        free -h | grep Mem
    '
}

# Fonction pour nettoyer les logs
clean_logs() {
    print_header "Nettoyage des logs"
    
    # Sauvegarder les anciens logs
    if [ -f "logs/supervisor_stdout.log" ]; then
        mv logs/supervisor_stdout.log logs/supervisor_stdout.log.old
    fi
    if [ -f "logs/supervisor_stderr.log" ]; then
        mv logs/supervisor_stderr.log logs/supervisor_stderr.log.old
    fi
    if [ -f "logs/gunicorn_error.log" ]; then
        mv logs/gunicorn_error.log logs/gunicorn_error.log.old
    fi
    
    print_status "Logs sauvegardés et nettoyés"
}

# Gestion des arguments
case "$1" in
    start)
        start_app
        ;;
    stop)
        stop_app
        ;;
    restart)
        restart_app
        ;;
    status)
        status_app
        ;;
    logs)
        show_logs
        ;;
    monitor)
        monitor_app
        ;;
    install)
        install_supervisor_config
        ;;
    clean-logs)
        clean_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|monitor|install|clean-logs}"
        echo ""
        echo "Commandes disponibles:"
        echo "  start      - Démarrer l'application avec Supervisor"
        echo "  stop       - Arrêter l'application"
        echo "  restart    - Redémarrer l'application"
        echo "  status     - Afficher le statut détaillé"
        echo "  logs       - Afficher les logs récents"
        echo "  monitor    - Surveillance en temps réel"
        echo "  install    - Installer la configuration Supervisor"
        echo "  clean-logs - Nettoyer les anciens logs"
        echo ""
        echo "Avantages de cette configuration:"
        echo "  ✅ Redémarrage automatique en cas de crash"
        echo "  ✅ Surveillance continue des processus"
        echo "  ✅ Logs détaillés pour le debugging"
        echo "  ✅ Gestion de la mémoire et des ressources"
        exit 1
        ;;
esac
