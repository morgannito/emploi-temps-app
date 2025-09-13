#!/bin/bash

# Script de démarrage en production pour l'application d'emploi du temps

echo "🚀 Démarrage de l'application en mode PRODUCTION..."

# Activer l'environnement virtuel
source venv/bin/activate

# Vérifier que toutes les dépendances sont installées
echo "📦 Vérification des dépendances..."
pip install -r requirements.txt

# Créer les dossiers de données s'ils n'existent pas
mkdir -p data
mkdir -p logs

# Démarrer Gunicorn en mode production
echo "🔥 Lancement du serveur Gunicorn..."
gunicorn -c gunicorn.conf.py app_new:app

echo "✅ Application démarrée en mode production sur http://172.19.202.13:5005"
