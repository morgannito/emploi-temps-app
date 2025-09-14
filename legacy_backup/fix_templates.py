#!/usr/bin/env python3
"""
Script pour corriger automatiquement les références de routes dans les templates
"""

import os
import re
import glob

# Mappings des anciens endpoints vers les nouveaux
ROUTE_MAPPINGS = {
    # Planning Controller
    'admin': 'planning.admin',
    'planning_readonly': 'planning.planning_readonly',
    'planning_v2': 'planning.planning_v2',
    'planning_v2_fast': 'planning.planning_v2_fast',
    'planning_v2_spa': 'planning.planning_v2_spa',
    'day_view': 'planning.day_view',
    'export_week_pdf': 'planning.export_week_pdf',
    'export_day_pdf': 'planning.export_day_pdf',
    'student_view': 'planning.student_view',
    'kiosque_week': 'planning.kiosque_week',
    'kiosque_room': 'planning.kiosque_room',
    'tv_schedule': 'planning.tv_schedule',
    'kiosque_halfday': 'planning.kiosque_halfday',
    'spa_redirect': 'planning.spa_redirect',
    'api_week_data': 'planning.api_week_data',
    'api_display_current': 'planning.api_display_current',

    # Professor Controller
    'list_professors_overview_minimal': 'professors.list_professors_overview',
    'professor_schedule': 'professors.professor_schedule',
    'edit_schedule': 'professors.edit_schedule',
    'professor_by_id': 'professors.professor_by_id',

    # Course Controller
    'add_custom_course': 'courses.add_custom_course',

    # Room Controller
    'assign_room': 'rooms.assign_room',
}

def fix_template_file(filepath):
    """Corrige un fichier template"""
    print(f"Processing {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = 0

    # Remplacer les url_for avec les nouveaux endpoints
    for old_endpoint, new_endpoint in ROUTE_MAPPINGS.items():
        # Pattern pour capturer url_for('endpoint', ...)
        pattern = r"\{\{\s*url_for\s*\(\s*['\"](" + old_endpoint + r")['\"]"
        replacement = "{{ url_for('" + new_endpoint + "'"

        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            print(f"  - Replaced {count} occurrences of '{old_endpoint}' -> '{new_endpoint}'")
            content = new_content
            changes_made += count

    # Sauvegarder si des changements ont été faits
    if changes_made > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ {changes_made} changes saved to {filepath}")
    else:
        print(f"  ⭐ No changes needed for {filepath}")

def main():
    """Fonction principale"""
    print("🔧 Fixing template references...")

    # Chercher tous les fichiers HTML dans templates/
    template_files = glob.glob('templates/*.html')

    if not template_files:
        print("❌ No template files found!")
        return

    print(f"Found {len(template_files)} template files")

    total_changes = 0
    for template_file in template_files:
        try:
            fix_template_file(template_file)
        except Exception as e:
            print(f"❌ Error processing {template_file}: {e}")

    print("\n✅ Template fixing complete!")

if __name__ == '__main__':
    main()