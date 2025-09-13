import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from services.student_service import StudentService


class TestStudentService:

    def test_get_current_period_strict_morning(self):
        """Test période matin (strict)"""
        morning_time = datetime(2025, 9, 13, 11, 59)
        assert StudentService.get_current_period_strict(morning_time) == "morning"

        boundary_time = datetime(2025, 9, 13, 12, 4)
        assert StudentService.get_current_period_strict(boundary_time) == "morning"

    def test_get_current_period_strict_afternoon(self):
        """Test période après-midi (strict)"""
        afternoon_time = datetime(2025, 9, 13, 12, 5)
        assert StudentService.get_current_period_strict(afternoon_time) == "afternoon"

        late_time = datetime(2025, 9, 13, 18, 0)
        assert StudentService.get_current_period_strict(late_time) == "afternoon"

    def test_get_current_period_standard_morning(self):
        """Test période matin (standard)"""
        morning_time = datetime(2025, 9, 13, 12, 29)
        assert StudentService.get_current_period_standard(morning_time) == "morning"

    def test_get_current_period_standard_afternoon(self):
        """Test période après-midi (standard)"""
        afternoon_time = datetime(2025, 9, 13, 12, 30)
        assert StudentService.get_current_period_standard(afternoon_time) == "afternoon"

    def test_is_morning_slot(self):
        """Test détection créneau matin"""
        morning_slot = {'start_time': '09:00'}
        boundary_slot = {'start_time': '11:59'}
        afternoon_slot = {'start_time': '12:00'}

        assert StudentService.is_morning_slot(morning_slot) is True
        assert StudentService.is_morning_slot(boundary_slot) is True
        assert StudentService.is_morning_slot(afternoon_slot) is False

    def test_is_afternoon_slot(self):
        """Test détection créneau après-midi"""
        morning_slot = {'start_time': '11:59'}
        afternoon_slot = {'start_time': '12:00'}
        late_slot = {'start_time': '17:00'}

        assert StudentService.is_afternoon_slot(morning_slot) is False
        assert StudentService.is_afternoon_slot(afternoon_slot) is True
        assert StudentService.is_afternoon_slot(late_slot) is True

    def test_get_french_day_name_forced(self):
        """Test nom jour français forcé"""
        now = datetime(2025, 9, 13)  # Samedi

        result = StudentService.get_french_day_name(now, "Mercredi")
        assert result == "Mercredi"

    def test_get_french_day_name_auto(self):
        """Test nom jour français automatique"""
        monday = datetime(2025, 9, 15)  # Lundi
        tuesday = datetime(2025, 9, 16)  # Mardi

        assert StudentService.get_french_day_name(monday) == "Lundi"
        assert StudentService.get_french_day_name(tuesday) == "Mardi"

    def test_filter_time_slots_by_period_morning(self):
        """Test filtrage créneaux matin"""
        time_slots = [
            {'start_time': '08:00', 'label': '8h-9h'},
            {'start_time': '11:00', 'label': '11h-12h'},
            {'start_time': '13:00', 'label': '13h-14h'}
        ]

        result = StudentService.filter_time_slots_by_period(time_slots, 'morning')
        assert len(result) == 2
        assert all(slot['start_time'] < '12:00' for slot in result)

    def test_filter_time_slots_by_period_afternoon(self):
        """Test filtrage créneaux après-midi"""
        time_slots = [
            {'start_time': '08:00', 'label': '8h-9h'},
            {'start_time': '13:00', 'label': '13h-14h'},
            {'start_time': '17:00', 'label': '17h-18h'}
        ]

        result = StudentService.filter_time_slots_by_period(time_slots, 'afternoon')
        assert len(result) == 2
        assert all(slot['start_time'] >= '12:00' for slot in result)

    def test_filter_time_slots_by_period_full_day(self):
        """Test filtrage journée complète"""
        time_slots = [
            {'start_time': '08:00', 'label': '8h-9h'},
            {'start_time': '13:00', 'label': '13h-14h'}
        ]

        result = StudentService.filter_time_slots_by_period(time_slots, 'full_day')
        assert len(result) == 2

    def test_determine_period_forced(self):
        """Test détermination période forcée"""
        now = datetime(2025, 9, 13, 15, 0)

        result = StudentService.determine_period(now, "morning", False)
        assert result == "morning"

    def test_determine_period_selector(self):
        """Test détermination période avec sélecteur"""
        now = datetime(2025, 9, 13, 15, 0)

        result = StudentService.determine_period(now, None, True)
        assert result == "full_day"

    def test_determine_period_auto(self):
        """Test détermination période automatique"""
        morning_time = datetime(2025, 9, 13, 10, 0)
        afternoon_time = datetime(2025, 9, 13, 15, 0)

        result_morning = StudentService.determine_period(morning_time, None, False)
        result_afternoon = StudentService.determine_period(afternoon_time, None, False)

        assert result_morning == "morning"
        assert result_afternoon == "afternoon"

    def test_get_period_label(self):
        """Test libellés périodes"""
        assert StudentService.get_period_label("morning") == "Matinée"
        assert StudentService.get_period_label("afternoon") == "Après-midi"
        assert StudentService.get_period_label("full_day") == "Journée complète"

    def test_generate_simple_academic_calendar(self):
        """Test génération calendrier académique simple"""
        calendar = StudentService.generate_simple_academic_calendar()

        assert len(calendar) == 52
        assert calendar[0] == "Semaine 36 A"
        assert "Semaine 37 B" in calendar
        assert "Semaine 01 B" in calendar  # Correction alternance A/B

    def test_get_courses_for_day(self):
        """Test filtrage cours par jour"""
        class MockCourse:
            def __init__(self, week_name, day):
                self.week_name = week_name
                self.day = day

        courses = [
            MockCourse("Semaine 36 A", "Lundi"),
            MockCourse("Semaine 36 A", "Mardi"),
            MockCourse("Semaine 37 B", "Lundi")
        ]

        result, target_day, valid_days = StudentService.get_courses_for_day(
            courses, "Semaine 36 A", "Lundi"
        )

        assert len(result) == 1
        assert result[0].day == "Lundi"
        assert target_day == "Lundi"
        assert "Lundi" in valid_days