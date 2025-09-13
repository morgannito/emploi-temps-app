import pytz
from datetime import date, timedelta, datetime
from typing import List, Dict, Optional


class WeekService:
    """Service pour la gestion des semaines académiques"""

    @staticmethod
    def generate_academic_calendar() -> List[Dict]:
        """Génère une liste de semaines alternant A et B pour toute l'année scolaire avec dates."""

        weeks = []
        is_type_A = True  # On commence par une semaine de type A

        # Date de début de l'année scolaire (dernière semaine d'août 2025)
        # Semaine 36 commence le 1er septembre 2025
        start_date = date(2025, 9, 1)  # Lundi 1er septembre 2025

        # Première partie de l'année (septembre à décembre) - Semaines 36-52
        for week_num in range(36, 53):
            week_type = "A" if is_type_A else "B"

            # Calculer la date du lundi de cette semaine
            week_offset = (week_num - 36) * 7  # 7 jours par semaine
            monday_date = start_date + timedelta(days=week_offset)

            # Formater la date
            date_str = monday_date.strftime("%d/%m/%Y")

            weeks.append({
                'name': f"Semaine {week_num} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A

        # Deuxième partie de l'année (janvier à juin) - Semaines 1-35
        # Continuer à partir de la semaine 1 (janvier 2026)
        for week_num in range(1, 36):
            week_type = "A" if is_type_A else "B"

            # Calculer la date du lundi de cette semaine
            # Semaine 1 commence le 5 janvier 2026
            january_start = date(2026, 1, 5)  # Lundi 5 janvier 2026
            week_offset = (week_num - 1) * 7
            monday_date = january_start + timedelta(days=week_offset)

            # Formater la date
            date_str = monday_date.strftime("%d/%m/%Y")

            weeks.append({
                'name': f"Semaine {week_num:02d} {week_type}",
                'date': date_str,
                'full_name': f"Semaine {week_num:02d} {week_type} ({date_str})"
            })
            is_type_A = not is_type_A

        return weeks

    @staticmethod
    def get_current_week_name(weeks_to_display: List[Dict]) -> str:
        """Détermine la semaine actuelle basée sur la date"""
        today = datetime.now(pytz.timezone("Europe/Paris")).date()
        week_num = today.isocalendar()[1]

        # Déterminer le type de semaine (A ou B) - corrigé pour 2025
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

        return week_name

    @staticmethod
    def find_week_info(week_name: str, weeks_to_display: List[Dict]) -> Optional[Dict]:
        """Trouve les informations d'une semaine dans la liste"""
        for week_info in weeks_to_display:
            if week_info['name'] == week_name:
                return week_info
        return None