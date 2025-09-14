#!/bin/bash

# Script d'inspection PrestaShop à distance
# Usage: ./remote_inspection.sh

SERVER="51.255.70.134"
REMOTE_PATH="/var/www/vhosts/heleneriu.fr/httpdocs"
LOG_PATH="/var/log/plesk-php82-fpm/error.log"

echo "🚀 Starting remote PrestaShop inspection..."

# Création du répertoire de travail distant
ssh $SERVER "mkdir -p /tmp/ps_inspection"

# Copie du script d'inspection
scp prestashop_inspector.py $SERVER:/tmp/ps_inspection/

# Installation des dépendances Python si nécessaire
ssh $SERVER << 'EOF'
cd /tmp/ps_inspection
python3 -c "import pymysql" 2>/dev/null || pip3 install --user pymysql
EOF

# Exécution de l'inspection
ssh $SERVER << EOF
cd /tmp/ps_inspection
python3 prestashop_inspector.py
EOF

# Récupération du rapport
scp $SERVER:/tmp/ps_inspection/prestashop_inspection_*.md ./

# Nettoyage
ssh $SERVER "rm -rf /tmp/ps_inspection"

echo "✅ Remote inspection completed!"
echo "Report files downloaded to current directory."