import datetime

def get_current_week_name():
    """Détermine la semaine actuelle basée sur la date du jour."""
    today = datetime.date.today()
    
    # Date de début de l'année scolaire (1er septembre 2025)
    start_date = datetime.date(2025, 9, 1)
    
    # Si on est avant le début de l'année scolaire
    if today < start_date:
        return "Semaine 36 A"
    
    # Calculer le numéro de semaine ISO
    week_num = today.isocalendar()[1]
    
    # Si on est en 2025 (septembre-décembre)
    if today.year == 2025:
        if week_num >= 36:
            # Calculer si c'est une semaine A ou B
            weeks_since_start = week_num - 36
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            return f"Semaine {week_num} {week_type}"
    
    # Si on est en 2026 (janvier-juin)
    elif today.year == 2026:
        if week_num <= 35:
            # Calculer le nombre de semaines depuis septembre 2025
            # Semaines 36-52 de 2025 = 17 semaines
            weeks_since_start = 17 + week_num - 1
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            # Format avec zéro pour les semaines < 10
            if week_num < 10:
                return f"Semaine 0{week_num} {week_type}"
            else:
                return f"Semaine {week_num} {week_type}"
    
    # Par défaut, retourner la première semaine
    return "Semaine 36 A"

# Test
print(get_current_week_name())
EOF'
