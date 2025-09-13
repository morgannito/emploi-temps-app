import sys

# Lire le fichier
with open("app_new.py", "r") as f:
    lines = f.readlines()

# Trouver et modifier les lignes 764-766
new_code = """    # Si aucune semaine n'est spécifiée, déterminer la semaine actuelle
    if week_name is None:
        import datetime
        today = datetime.date.today()
        week_num = today.isocalendar()[1]
        
        # Déterminer le type de semaine (A ou B)
        if today.year == 2025 and week_num >= 36:
            # Semaines de septembre à décembre 2025
            weeks_since_start = week_num - 36
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            week_name = f"Semaine {week_num} {week_type}"
        elif today.year == 2026 and week_num <= 35:
            # Semaines de janvier à juin 2026
            # 17 semaines de sept-dec 2025 (36-52)
            weeks_since_start = 17 + week_num - 1
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            # Format avec zéro pour les semaines < 10
            week_name = f"Semaine {week_num:02d} {week_type}"
        else:
            # Par défaut, prendre la première semaine
            week_name = weeks_to_display[0]['name']
"""

# Remplacer les lignes 764-766
new_lines = lines[:764] + [new_code] + lines[767:]

# Écrire le fichier modifié
with open("app_new.py", "w") as f:
    f.writelines(new_lines)

print("Modification effectuée avec succès!")
