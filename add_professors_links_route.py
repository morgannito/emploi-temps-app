import re

# Lire le fichier
with open("app_new.py", "r") as f:
    content = f.read()

# Trouver la position après la route /professors
insert_position = content.find("@app.route('/edit_schedule")

# Créer la nouvelle route
new_route = """
@app.route('/professors/links')
def professors_links():
    \"\"\"Page affichant les liens directs vers les emplois du temps des professeurs.\"\"\"
    schedule_manager.reload_data()
    
    # Créer un dictionnaire des professeurs et leurs semaines
    professors = {}
    for week_name, week_data in schedule_manager.canonical_schedules.items():
        for prof_name in week_data.get('professors', {}):
            if prof_name not in professors:
                professors[prof_name] = []
            if week_name not in professors[prof_name]:
                professors[prof_name].append(week_name)
    
    # Trier les professeurs et leurs semaines
    professors = dict(sorted(professors.items()))
    for prof in professors:
        professors[prof] = sorted(professors[prof])
    
    return render_template('prof_list.html', professors=professors)

"""

# Insérer la nouvelle route
if insert_position > 0:
    content = content[:insert_position] + new_route + content[insert_position:]
    
    with open("app_new.py", "w") as f:
        f.write(content)
    print("Route /professors/links ajoutée avec succès!")
else:
    print("Position d'insertion non trouvée")
