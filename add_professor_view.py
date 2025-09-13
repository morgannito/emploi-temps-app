import re

# Lire le fichier
with open("app_new.py", "r") as f:
    content = f.read()

# Trouver la position après la route /student/<week_name>
insert_position = content.find("@app.route('/export_week_pdf")

# Créer la nouvelle route
new_route = """
@app.route('/professor/<path:prof_name>')
def professor_schedule(prof_name):
    \"\"\"Vue individuelle de l'emploi du temps d'un professeur.\"\"\"
    schedule_manager.force_sync_data()
    
    # Normaliser le nom du professeur
    from excel_parser import normalize_professor_name
    prof_name = normalize_professor_name(prof_name)
    
    # Récupérer toutes les semaines
    def generate_academic_weeks():
        import datetime
        weeks = []
        is_type_A = True
        
        # Première partie (septembre-décembre 2025)
        start_date = datetime.date(2025, 9, 1)
        for week_num in range(36, 53):
            week_type = "A" if is_type_A else "B"
            week_offset = (week_num - 36) * 7
            monday_date = start_date + datetime.timedelta(days=week_offset)
            date_str = monday_date.strftime("%d/%m/%Y")
            weeks.append({
                'name': f"Semaine {week_num} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A
            
        # Deuxième partie (janvier-juin 2026)
        for week_num in range(1, 36):
            week_type = "A" if is_type_A else "B"
            january_start = datetime.date(2026, 1, 5)
            week_offset = (week_num - 1) * 7
            monday_date = january_start + datetime.timedelta(days=week_offset)
            date_str = monday_date.strftime("%d/%m/%Y")
            weeks.append({
                'name': f"Semaine {week_num:02d} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num:02d} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A
            
        return weeks
    
    weeks_list = generate_academic_weeks()
    
    # Récupérer les cours du professeur
    all_courses = schedule_manager.get_all_courses()
    professor_courses = {}
    
    for week in weeks_list:
        week_name = week['name']
        week_courses = []
        
        for course in all_courses:
            if course.professor == prof_name and course.week_name == week_name:
                week_courses.append({
                    'day': course.day,
                    'start_time': course.start_time,
                    'end_time': course.end_time,
                    'subject': course.subject,
                    'room': course.assigned_room or "Non attribuée",
                    'tp_name': course.tp_name
                })
        
        if week_courses:
            # Trier par jour et heure
            days_order = {'Lundi': 0, 'Mardi': 1, 'Mercredi': 2, 'Jeudi': 3, 'Vendredi': 4}
            week_courses.sort(key=lambda x: (days_order.get(x['day'], 5), x['start_time']))
            professor_courses[week_name] = week_courses
    
    return render_template('professor_schedule.html', 
                         professor_name=prof_name,
                         professor_courses=professor_courses,
                         weeks_list=weeks_list)

"""

# Insérer la nouvelle route
if insert_position > 0:
    content = content[:insert_position] + new_route + "\n" + content[insert_position:]
    
    with open("app_new.py", "w") as f:
        f.write(content)
    print("Route ajoutée avec succès!")
else:
    print("Position d'insertion non trouvée")
