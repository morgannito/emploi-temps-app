#!/usr/bin/env python3
import re

# Lire le fichier
with open('app_new.py', 'r') as f:
    content = f.read()

# Remplacer la ligne now = datetime.now()
pattern = r'(\s+)now = datetime\.now\(\)'
replacement = r'\1# Heure française (UTC+2 en été)\n\1french_tz = timezone(timedelta(hours=2))\n\1now = datetime.now(french_tz)'

content = re.sub(pattern, replacement, content)

# Écrire le fichier modifié
with open('app_new.py', 'w') as f:
    f.write(content)

print('Timezone fix applied')
