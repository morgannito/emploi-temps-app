import pytest
import json
import os
from unittest.mock import patch, mock_open
from services.professor_service import ProfessorService


class TestProfessorService:

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_professor_id_mapping_exists(self, mock_file, mock_exists):
        """Test chargement mapping professeurs existant"""
        mock_exists.return_value = True
        mock_data = {"M Dupont": "prof_001", "Mme Martin": "prof_002"}
        mock_file.return_value.read.return_value = json.dumps(mock_data)

        result = ProfessorService.load_professor_id_mapping()
        assert result == mock_data

    @patch('os.path.exists')
    def test_load_professor_id_mapping_not_exists(self, mock_exists):
        """Test chargement mapping professeurs inexistant"""
        mock_exists.return_value = False

        result = ProfessorService.load_professor_id_mapping()
        assert result == {}

    def test_get_professor_name_mapping(self):
        """Test création mapping noms normalisés"""
        canonical_schedules = {
            "M Jean DUPONT": {},
            "Mme Marie MARTIN": {},
            "Dr Pierre BERNARD": {}
        }

        mapping = ProfessorService.get_professor_name_mapping(canonical_schedules)
        assert len(mapping) >= 3
        assert "M Jean DUPONT" in mapping.values()

    def test_extract_professors_from_courses(self):
        """Test extraction professeurs depuis cours"""
        class MockCourse:
            def __init__(self, professor, week_name):
                self.professor = professor
                self.week_name = week_name

        courses = [
            MockCourse("M Dupont", "Semaine 36 A"),
            MockCourse("M Dupont", "Semaine 37 B"),
            MockCourse("Mme Martin", "Semaine 36 A")
        ]

        result = ProfessorService.extract_professors_from_courses(courses)

        assert "M Dupont" in result
        assert "Mme Martin" in result
        assert len(result["M Dupont"]) == 2
        assert len(result["Mme Martin"]) == 1

    def test_find_exact_professor_name_exact_match(self):
        """Test recherche nom exact"""
        profs = ["M Dupont", "Mme Martin", "Dr Bernard"]

        result = ProfessorService.find_exact_professor_name("M Dupont", profs)
        assert result == "M Dupont"

    def test_find_exact_professor_name_partial_match(self):
        """Test recherche nom partiel"""
        profs = ["M Jean DUPONT", "Mme Marie MARTIN"]

        result = ProfessorService.find_exact_professor_name("dupont", profs)
        assert result == "M Jean DUPONT"

    def test_find_exact_professor_name_no_match(self):
        """Test recherche nom inexistant"""
        profs = ["M Dupont", "Mme Martin"]

        result = ProfessorService.find_exact_professor_name("Bernard", profs)
        assert result is None

    def test_find_professor_by_id(self):
        """Test recherche professeur par ID"""
        mapping = {"M Dupont": "prof_001", "Mme Martin": "prof_002"}

        result = ProfessorService.find_professor_by_id("prof_001", mapping)
        assert result == "M Dupont"

        result = ProfessorService.find_professor_by_id("prof_999", mapping)
        assert result is None

    def test_sort_courses_by_day_and_time(self):
        """Test tri cours par jour et heure"""
        courses = [
            {'day': 'Mercredi', 'start_time': '10:00'},
            {'day': 'Lundi', 'start_time': '14:00'},
            {'day': 'Lundi', 'start_time': '08:00'},
            {'day': 'Vendredi', 'start_time': '09:00'}
        ]

        sorted_courses = ProfessorService.sort_courses_by_day_and_time(courses)

        assert sorted_courses[0]['day'] == 'Lundi'
        assert sorted_courses[0]['start_time'] == '08:00'
        assert sorted_courses[1]['day'] == 'Lundi'
        assert sorted_courses[1]['start_time'] == '14:00'
        assert sorted_courses[2]['day'] == 'Mercredi'
        assert sorted_courses[3]['day'] == 'Vendredi'

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_get_all_professors_with_ids(self, mock_file, mock_exists):
        """Test récupération tous professeurs avec IDs"""
        mock_exists.return_value = True
        mock_data = {"M Dupont": "prof_001", "Mme Martin": "prof_002"}
        mock_file.return_value.read.return_value = json.dumps(mock_data)

        result = ProfessorService.get_all_professors_with_ids()
        assert result == mock_data