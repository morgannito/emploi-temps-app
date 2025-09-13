from typing import List, Dict


class TimeSlotService:
    """Service pour la gestion des créneaux horaires"""

    @staticmethod
    def generate_time_grid() -> List[Dict]:
        """Génère une grille horaire de 8h à 18h avec créneaux d'1 heure"""
        time_slots = []
        for hour in range(8, 18):
            start_time = f"{hour:02d}:00"
            end_time = f"{hour+1:02d}:00"
            time_slots.append({
                'start_time': start_time,
                'end_time': end_time,
                'label': f"{hour}h-{hour+1}h"
            })
        return time_slots

    @staticmethod
    def time_to_minutes(time_str: str) -> int:
        """Convertit une heure au format HH:MM en minutes"""
        if ':' not in time_str:
            return 0
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes