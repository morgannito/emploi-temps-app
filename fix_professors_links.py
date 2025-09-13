import re

# Lire le fichier
with open("app_new.py", "r") as f:
    content = f.read()

# Trouver et remplacer la route /professors/links
pattern = r"@app\.route\('/professors/links'\).*?return render_template\('prof_list\.html', professors=professors\)"
replacement = """@app.route('/professors/links')
def professors_links():
    \"\"\"Page affichant les liens directs vers les emplois du temps des professeurs.\"\"\"
    schedule_manager.reload_data()
    
    # Récupérer tous les cours pour extraire les professeurs uniques
    all_courses = schedule_manager.get_all_courses()
    professors = {}
    
    for course in all_courses:
        prof_name = course.professor
        week_name = course.week_name
        
        if prof_name not in professors:
            professors[prof_name] = set()
        professors[prof_name].add(week_name)
    
    # Convertir les sets en listes triées
    for prof in professors:
        professors[prof] = sorted(list(professors[prof]))
    
    # Trier les professeurs
    professors = dict(sorted(professors.items()))
    
    return render_template('prof_list.html', professors=professors)"""

# Remplacer
content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("app_new.py", "w") as f:
    f.write(content)

print("Route corrigée!")
