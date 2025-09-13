import re

# Lire le fichier
with open('app_new.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Nouvelle méthode add_professor
new_method = '''    def add_professor(self, prof_name: str) -> bool:
        """Ajoute un nouveau professeur avec un emploi du temps vide."""
        if prof_name in self.canonical_schedules:
            return False  # Le professeur existe déjà
        
        self.canonical_schedules[prof_name] = {'courses': [], 'color': None, 'preferences': {}}
        
        # Auto-générer ID
        prof_id = hashlib.md5(prof_name.encode()).hexdigest()[:8]
        prof_id_mapping_file = "data/prof_id_mapping.json"
        
        # Charger et mettre à jour le mapping des IDs
        if os.path.exists(prof_id_mapping_file):
            with open(prof_id_mapping_file, "r", encoding="utf-8") as f:
                prof_id_mapping = json.load(f)
        else:
            prof_id_mapping = {}
        
        prof_id_mapping[prof_name] = prof_id
        
        with open(prof_id_mapping_file, "w", encoding="utf-8") as f:
            json.dump(prof_id_mapping, f, indent=2, ensure_ascii=False)
        
        # Sauvegarder les modifications du canonical_schedules
        with open(self.canonical_schedule_file, 'w', encoding='utf-8') as f:
            json.dump(self.canonical_schedules, f, indent=2, ensure_ascii=False)
        return True'''

# Remplacer l'ancienne méthode
pattern = r'    def add_professor\(self, prof_name: str\) -> bool:.*?return True'
content = re.sub(pattern, new_method, content, flags=re.DOTALL)

# Sauvegarder
with open('app_new.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Méthode add_professor mise à jour avec succès')
