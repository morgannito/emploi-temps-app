import pytest
from services.timeslot_service import TimeSlotService


class TestTimeSlotService:

    def test_generate_time_grid(self):
        """Test génération grille horaire"""
        time_slots = TimeSlotService.generate_time_grid()

        assert len(time_slots) == 10  # 8h-18h = 10 créneaux
        assert time_slots[0]['start_time'] == "08:00"
        assert time_slots[0]['end_time'] == "09:00"
        assert time_slots[0]['label'] == "8h-9h"
        assert time_slots[-1]['start_time'] == "17:00"
        assert time_slots[-1]['end_time'] == "18:00"
        assert time_slots[-1]['label'] == "17h-18h"

    def test_time_to_minutes_valid(self):
        """Test conversion heure valide en minutes"""
        assert TimeSlotService.time_to_minutes("08:00") == 480
        assert TimeSlotService.time_to_minutes("12:30") == 750
        assert TimeSlotService.time_to_minutes("18:00") == 1080
        assert TimeSlotService.time_to_minutes("00:00") == 0

    def test_time_to_minutes_invalid(self):
        """Test conversion heure invalide"""
        assert TimeSlotService.time_to_minutes("invalid") == 0
        assert TimeSlotService.time_to_minutes("") == 0
        assert TimeSlotService.time_to_minutes("8:00") == 480  # Format sans zéro

    def test_time_slots_structure(self):
        """Test structure des créneaux"""
        time_slots = TimeSlotService.generate_time_grid()

        for slot in time_slots:
            assert 'start_time' in slot
            assert 'end_time' in slot
            assert 'label' in slot

            # Vérifier format HH:MM
            start_parts = slot['start_time'].split(':')
            end_parts = slot['end_time'].split(':')
            assert len(start_parts) == 2
            assert len(end_parts) == 2
            assert start_parts[0].isdigit()
            assert start_parts[1].isdigit()

    def test_consecutive_time_slots(self):
        """Test créneaux consécutifs"""
        time_slots = TimeSlotService.generate_time_grid()

        for i in range(len(time_slots) - 1):
            current_end = TimeSlotService.time_to_minutes(time_slots[i]['end_time'])
            next_start = TimeSlotService.time_to_minutes(time_slots[i + 1]['start_time'])
            assert current_end == next_start, f"Gap entre {time_slots[i]['label']} et {time_slots[i + 1]['label']}"