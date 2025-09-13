#!/bin/bash

# Script d'installation complète pour la production
# Installe et configure Supervisor, le moniteur et les services

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Variables
APP_DIR="/home/toto/app_emploie_du_temps_isa"
SUPERVISOR_CONFIG="/etc/supervisor/conf.d/emploi_du_temps_isa.conf"
SERVICE_FILE="/etc/systemd/system/emploi-temps-monitor.service"

print_header "Installation de la solution de production"

# 1. Vérifier que nous sommes dans le bon répertoire
if [ ! -f "app_new.py" ]; then
    print_error "Ce script doit être exécuté depuis le répertoire de l'application"
    exit 1
fi

# 2. Installer Supervisor si pas déjà installé
print_header "Installation de Supervisor"
if ! command -v supervisorctl &> /dev/null; then
    print_status "Installation de Supervisor..."
    sudo apt update
    sudo apt install -y supervisor
    print_status "Supervisor installé"
else
    print_status "Supervisor déjà installé"
fi

# 3. Installer les dépendances Python
print_header "Installation des dépendances Python"
print_status "Activation de l'environnement virtuel..."
source venv/bin/activate

print_status "Installation des dépendances..."
pip install -r requirements.txt
pip install gevent psutil requests

# 4. Créer les dossiers nécessaires
print_header "Création des dossiers"
mkdir -p logs
mkdir -p data
print_status "Dossiers créés"

# 5. Installer la configuration Supervisor
print_header "Configuration de Supervisor"
if [ -f "supervisor_emploi_temps.conf" ]; then
    print_status "Installation de la configuration Supervisor..."
    sudo cp supervisor_emploi_temps.conf "$SUPERVISOR_CONFIG"
    sudo supervisorctl reread
    sudo supervisorctl update
    print_status "Configuration Supervisor installée"
else
    print_error "Fichier supervisor_emploi_temps.conf non trouvé"
    exit 1
fi

# 6. Installer le service systemd pour le moniteur
print_header "Configuration du service systemd"
if [ -f "emploi-temps-monitor.service" ]; then
    print_status "Installation du service systemd..."
    sudo cp emploi-temps-monitor.service "$SERVICE_FILE"
    sudo systemctl daemon-reload
    sudo systemctl enable emploi-temps-monitor.service
    print_status "Service systemd installé et activé"
else
    print_error "Fichier emploi-temps-monitor.service non trouvé"
    exit 1
fi

# 7. Arrêter les anciens processus s'ils existent
print_header "Nettoyage des anciens processus"
sudo pkill -f gunicorn || true
sudo pkill -f monitor_app.py || true
sleep 2

# 8. Démarrer l'application
print_header "Démarrage de l'application"
print_status "Démarrage via Supervisor..."
sudo supervisorctl start emploi_du_temps_isa

# Attendre que l'application démarre
print_status "Attente du démarrage de l'application..."
sleep 15

# Vérifier le statut
if sudo supervisorctl status emploi_du_temps_isa | grep -q "RUNNING"; then
    print_status "Application démarrée avec succès"
else
    print_error "Échec du démarrage de l'application"
    sudo supervisorctl status emploi_du_temps_isa
    exit 1
fi

# 9. Démarrer le moniteur
print_header "Démarrage du moniteur"
print_status "Démarrage du service de surveillance..."
sudo systemctl start emploi-temps-monitor.service

# Vérifier le statut du moniteur
if sudo systemctl is-active --quiet emploi-temps-monitor.service; then
    print_status "Moniteur démarré avec succès"
else
    print_error "Échec du démarrage du moniteur"
    sudo systemctl status emploi-temps-monitor.service
    exit 1
fi

# 10. Test final
print_header "Test de la solution"
print_status "Test de l'application..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5005/ | grep -q "200"; then
    print_status "✅ Application accessible"
else
    print_error "❌ Application non accessible"
    exit 1
fi

print_status "Test du moniteur..."
if sudo systemctl is-active --quiet emploi-temps-monitor.service; then
    print_status "✅ Moniteur actif"
else
    print_error "❌ Moniteur inactif"
    exit 1
fi

# 11. Affichage des informations finales
print_header "Installation terminée avec succès"

echo ""
echo "🎉 Votre application est maintenant configurée pour la production !"
echo ""
echo "📋 Informations importantes :"
echo "   • Application: http://172.19.202.13:5005"
echo "   • Logs application: $APP_DIR/logs/"
echo "   • Logs moniteur: $APP_DIR/logs/monitor.log"
echo ""
echo "🔧 Commandes utiles :"
echo "   • Statut: ./manage_app_supervisor.sh status"
echo "   • Logs: ./manage_app_supervisor.sh logs"
echo "   • Redémarrage: ./manage_app_supervisor.sh restart"
echo "   • Surveillance: ./manage_app_supervisor.sh monitor"
echo ""
echo "🛡️  Fonctionnalités de sécurité :"
echo "   ✅ Redémarrage automatique en cas de crash"
echo "   ✅ Surveillance continue de la santé"
echo "   ✅ Limitation de la mémoire par processus"
echo "   ✅ Redémarrage automatique au boot"
echo "   ✅ Logs détaillés pour le debugging"
echo ""
echo "📊 Monitoring :"
echo "   • Le moniteur vérifie la santé toutes les 60 secondes"
echo "   • Redémarrage automatique si l'application ne répond plus"
echo "   • Surveillance de l'utilisation mémoire"
echo "   • Limitation à 3 redémarrages par heure maximum"
echo ""

print_status "Installation terminée !"
