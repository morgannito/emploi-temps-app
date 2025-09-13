import re

# Lire le fichier
with open("app_new.py", "r") as f:
    content = f.read()

# Remplacer la ligne désactivée par une recherche intelligente
old_line = "    # prof_name = normalize_professor_name(prof_name)  # Désactivé - garde le nom original"
new_code = """    # Recherche intelligente du nom du professeur
    all_courses = schedule_manager.get_all_courses()
    all_profs = set([c.professor for c in all_courses])
    
    # Essayer d'abord le nom exact
    if prof_name in all_profs:
        final_prof_name = prof_name
    else:
        # Rechercher un nom qui contient le terme recherché
        matches = [p for p in all_profs if prof_name.lower() in p.lower()]
        if matches:
            final_prof_name = matches[0]  # Prendre le premier match
        else:
            # Rechercher dans l'autre sens (terme recherché contient un nom de prof)
            reverse_matches = [p for p in all_profs if p.lower() in prof_name.lower()]
            if reverse_matches:
                final_prof_name = reverse_matches[0]
            else:
                final_prof_name = prof_name  # Garder l'original si aucun match
    
    prof_name = final_prof_name"""

content = content.replace(old_line, new_code)

with open("app_new.py", "w") as f:
    f.write(content)

print("Recherche intelligente ajoutée!")