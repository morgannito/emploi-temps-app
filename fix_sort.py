import re

# Lire le fichier
with open('app_new.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Nouvelle méthode avec tri alphabétique
new_method = '''    def get_canonical_schedules_summary(self):
        """Calcule un résumé des heures de cours pour chaque prof."""
        summary = {}
        normalized_profs = {}
        
        # Normaliser les noms et regrouper les cours
        for prof, prof_data in self.canonical_schedules.items():
            normalized_name = normalize_professor_name(prof)
            
            if normalized_name not in normalized_profs:
                normalized_profs[normalized_name] = []
            
            courses = prof_data['courses'] if isinstance(prof_data, dict) else prof_data
            normalized_profs[normalized_name].extend(courses)
        
        # Calculer les résumés pour les noms normalisés
        for prof, courses in normalized_profs.items():
            total_hours = sum(c.get('duration_hours', 0) for c in courses)
            
            days_summary = {}
            for day in ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']:
                day_hours = sum(c.get('duration_hours', 0) for c in courses if c.get('day') == day)
                if day_hours > 0:
                    days_summary[day] = f{day_hours:.1f}h

            summary[prof] = {
                'total_hours': f{total_hours:.1f}h,
                'days': days_summary,
                'color': self.get_prof_color(prof)
            }
        
        # Tri alphabétique des professeurs
        return dict(sorted(summary.items()))'''

# Remplacer l'ancienne méthode
pattern = r'    def get_canonical_schedules_summary\(self\):.*?return summary'
content = re.sub(pattern, new_method, content, flags=re.DOTALL)

# Sauvegarder
with open('app_new.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Tri alphabétique ajouté avec succès')
