import re

# Lire le fichier
with open('app_new.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Nouvelle fonction get_courses_for_week_canonical
new_function = '''def get_courses_for_week_canonical(week_name):
    """Récupère les cours pour une semaine - utilise get_all_courses() avec filtrage"""
    # Vérifier le cache
    if not planning_cache.is_cache_valid():
        planning_cache.clear()
        planning_cache.update_sync_time()
    
    if week_name not in planning_cache._courses_cache:
        # Utiliser get_all_courses() et filtrer par semaine
        all_courses = schedule_manager.get_all_courses()
        courses = [course for course in all_courses if course.week_name == week_name]
        
        # Mettre en cache
        planning_cache._courses_cache[week_name] = courses
        print(f"🔍 Cache mis à jour: {len(courses)} cours pour {week_name}")
    
    return planning_cache._courses_cache[week_name]'''

# Remplacer l'ancienne fonction
pattern = r'def get_courses_for_week_canonical\(week_name\):.*?return planning_cache\._courses_cache\[week_name\]'
content = re.sub(pattern, new_function, content, flags=re.DOTALL)

# Sauvegarder
with open('app_new.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fonction get_courses_for_week_canonical corrigée')
