import pytest
from datetime import time
from domain.entities.course import Course, CourseId, CustomCourse
from domain.value_objects.time_slot import TimeSlot, WeekIdentifier
from domain.services.room_assignment_service import RoomAssignmentService
from domain.entities.room import Room, RoomId
from domain.value_objects.time_slot import RoomCapacity


class TestCourseEntity:
    """Tests unitaires pour l'entité Course"""

    def test_course_creation(self):
        course_id = CourseId("1")
        week_id = WeekIdentifier(1, "A")
        time_slot = TimeSlot(time(8, 0), time(10, 0))

        course = Course(
            course_id=course_id,
            course_type="CM",
            professor_name="Prof. Dupont",
            week_identifier=week_id,
            day_of_week="Lundi",
            time_slot=time_slot
        )

        assert course.course_id.value == "1"
        assert course.course_type == "CM"
        assert course.professor_name == "Prof. Dupont"
        assert course.week_identifier == WeekIdentifier(1, "A")
        assert course.day_of_week == "Lundi"
        assert course.duration_hours == 2.0

    def test_course_conflict_detection_same_time(self):
        """Test détection conflit - même créneau horaire"""
        time_slot = TimeSlot(time(8, 0), time(10, 0))
        week_id = WeekIdentifier(1, "A")

        course1 = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=week_id,
            day_of_week="Lundi",
            time_slot=time_slot
        )

        course2 = Course(
            course_id=CourseId("2"),
            course_type="TD",
            professor_name="Prof. B",
            week_identifier=week_id,
            day_of_week="Lundi",
            time_slot=time_slot
        )

        assert course1.has_conflict_with(course2)
        assert course2.has_conflict_with(course1)

    def test_course_no_conflict_different_day(self):
        """Test pas de conflit - jours différents"""
        time_slot = TimeSlot(time(8, 0), time(10, 0))
        week_id = WeekIdentifier(1, "A")

        course1 = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=week_id,
            day_of_week="Lundi",
            time_slot=time_slot
        )

        course2 = Course(
            course_id=CourseId("2"),
            course_type="TD",
            professor_name="Prof. B",
            week_identifier=week_id,
            day_of_week="Mardi",
            time_slot=time_slot
        )

        assert not course1.has_conflict_with(course2)

    def test_course_no_conflict_different_time(self):
        """Test pas de conflit - créneaux différents"""
        week_id = WeekIdentifier(1, "A")

        course1 = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=week_id,
            day_of_week="Lundi",
            time_slot=TimeSlot(time(8, 0), time(10, 0))
        )

        course2 = Course(
            course_id=CourseId("2"),
            course_type="TD",
            professor_name="Prof. B",
            week_identifier=week_id,
            day_of_week="Lundi",
            time_slot=TimeSlot(time(10, 0), time(12, 0))
        )

        assert not course1.has_conflict_with(course2)

    def test_course_overlap_detection(self):
        """Test détection chevauchement partiel"""
        week_id = WeekIdentifier(1, "A")

        course1 = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=week_id,
            day_of_week="Lundi",
            time_slot=TimeSlot(time(8, 0), time(10, 0))
        )

        course2 = Course(
            course_id=CourseId("2"),
            course_type="TD",
            professor_name="Prof. B",
            week_identifier=week_id,
            day_of_week="Lundi",
            time_slot=TimeSlot(time(9, 30), time(11, 30))
        )

        assert course1.has_conflict_with(course2)
        assert course2.has_conflict_with(course1)

    def test_course_room_assignment(self):
        """Test attribution et désattribution de salle"""
        course = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=WeekIdentifier(1, "A"),
            day_of_week="Lundi",
            time_slot=TimeSlot(time(8, 0), time(10, 0))
        )

        assert course.assigned_room_id is None
        assert not course.is_room_assigned

        course.assign_room("A101")
        assert course.assigned_room_id == "A101"
        assert course.is_room_assigned

        course.unassign_room()
        assert course.assigned_room_id is None
        assert not course.is_room_assigned


class TestRoomEntity:
    """Tests unitaires pour l'entité Room"""

    def test_room_creation(self):
        room_id = RoomId("A101")
        capacity = RoomCapacity(50)

        room = Room(
            room_id=room_id,
            name="Amphi A101",
            capacity=capacity,
            equipment={"projecteur", "micro"}
        )

        assert room.room_id.value == "A101"
        assert room.name == "Amphi A101"
        assert room.capacity.max_students == 50
        assert "projecteur" in room.equipment

    def test_room_can_accommodate(self):
        room = Room(
            room_id=RoomId("A101"),
            name="Salle A101",
            capacity=RoomCapacity(30),
            equipment=set()
        )

        assert room.can_accommodate_course(25)
        assert room.can_accommodate_course(30)
        assert not room.can_accommodate_course(35)

    def test_room_equipment_management(self):
        room = Room(
            room_id=RoomId("A101"),
            name="Salle A101",
            capacity=RoomCapacity(30),
            equipment=set()
        )

        assert not room.has_equipment("projecteur")

        room.add_equipment("projecteur")
        assert room.has_equipment("projecteur")
        assert "projecteur" in room.equipment

        room.remove_equipment("projecteur")
        assert not room.has_equipment("projecteur")
        assert "projecteur" not in room.equipment

    def test_room_suitability_for_course_type(self):
        # Salle standard
        room_standard = Room(
            room_id=RoomId("B201"),
            name="Salle B201",
            capacity=RoomCapacity(30),
            equipment=set()
        )

        # Salle TP avec ordinateurs
        room_tp = Room(
            room_id=RoomId("C301"),
            name="Salle TP C301",
            capacity=RoomCapacity(20),
            equipment={"ordinateurs"}
        )

        # Amphi
        room_amphi = Room(
            room_id=RoomId("A001"),
            name="Grand Amphi",
            capacity=RoomCapacity(200),
            equipment={"micro", "projecteur"}
        )

        # Tests de convenance
        assert room_standard.is_suitable_for_course_type("CM")
        assert room_standard.is_suitable_for_course_type("TD")

        assert room_tp.is_suitable_for_course_type("TP Informatique")
        assert room_tp.is_suitable_for_course_type("TD Pratique")

        assert room_amphi.is_suitable_for_course_type("Cours magistral")
        assert room_amphi.is_suitable_for_course_type("Amphi")

        assert not room_standard.is_suitable_for_course_type("TP Informatique")


class MockCourseRepository:
    """Mock repository pour les tests"""

    def __init__(self):
        self.courses = []

    def save(self, course):
        # Remplace si existe, ajoute sinon
        existing_index = None
        for i, c in enumerate(self.courses):
            if c.course_id.value == course.course_id.value:
                existing_index = i
                break

        if existing_index is not None:
            self.courses[existing_index] = course
        else:
            self.courses.append(course)
        return course

    def find_conflicting_courses(self, course):
        conflicts = []
        for c in self.courses:
            if (c.course_id.value != course.course_id.value and
                    c.week_identifier.value == course.week_identifier.value and
                    c.day_of_week == course.day_of_week):
                if course.has_conflict_with(c):
                    conflicts.append(c)
        return conflicts

    def find_by_week(self, week_identifier):
        return [c for c in self.courses if c.week_identifier.value == week_identifier.value]


class TestRoomAssignmentService:
    """Tests unitaires pour le service d'attribution des salles"""

    def setup_method(self):
        self.mock_repo = MockCourseRepository()
        self.service = RoomAssignmentService(self.mock_repo)

    def test_can_assign_room_capacity_ok(self):
        course = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=WeekIdentifier(1, "A"),
            day_of_week="Lundi",
            time_slot=TimeSlot(time(8, 0), time(10, 0)),
            student_count=25
        )

        room = Room(
            room_id=RoomId("A101"),
            name="Salle A101",
            capacity=RoomCapacity(30),
            equipment=set()
        )

        assert self.service.can_assign_room_to_course(course, room)

    def test_cannot_assign_room_capacity_insufficient(self):
        course = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=WeekIdentifier(1, "A"),
            day_of_week="Lundi",
            time_slot=TimeSlot(time(8, 0), time(10, 0)),
            student_count=35
        )

        room = Room(
            room_id=RoomId("A101"),
            name="Salle A101",
            capacity=RoomCapacity(30),
            equipment=set()
        )

        assert not self.service.can_assign_room_to_course(course, room)

    def test_cannot_assign_room_type_incompatible(self):
        course = Course(
            course_id=CourseId("1"),
            course_type="TP Informatique",
            professor_name="Prof. A",
            week_identifier=WeekIdentifier(1, "A"),
            day_of_week="Lundi",
            time_slot=TimeSlot(time(8, 0), time(10, 0)),
            student_count=20
        )

        room = Room(
            room_id=RoomId("A101"),
            name="Salle A101",
            capacity=RoomCapacity(30),
            equipment=set()  # Pas d'ordinateurs
        )

        assert not self.service.can_assign_room_to_course(course, room)

    def test_suggest_optimal_room(self):
        course = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=WeekIdentifier(1, "A"),
            day_of_week="Lundi",
            time_slot=TimeSlot(time(8, 0), time(10, 0)),
            student_count=25
        )

        rooms = [
            Room(RoomId("A101"), "Salle A101", RoomCapacity(50), set()),  # Trop grande
            Room(RoomId("B201"), "Salle B201", RoomCapacity(30), set()),  # Parfaite
            Room(RoomId("C301"), "Salle C301", RoomCapacity(100), set()), # Beaucoup trop grande
            Room(RoomId("D401"), "Salle D401", RoomCapacity(20), set()),  # Trop petite
        ]

        optimal_room = self.service.suggest_optimal_room(course, rooms)

        # Doit suggérer la salle B201 (30 places) comme optimale pour 25 étudiants
        assert optimal_room is not None
        assert optimal_room.room_id.value == "B201"

    def test_assign_and_unassign_room(self):
        course = Course(
            course_id=CourseId("1"),
            course_type="CM",
            professor_name="Prof. A",
            week_identifier=WeekIdentifier(1, "A"),
            day_of_week="Lundi",
            time_slot=TimeSlot(time(8, 0), time(10, 0)),
            student_count=25
        )

        room = Room(
            room_id=RoomId("A101"),
            name="Salle A101",
            capacity=RoomCapacity(30),
            equipment=set()
        )

        # Attribution
        success = self.service.assign_room_to_course(course, room)
        assert success
        assert course.assigned_room_id == "A101"

        # Désattribution
        success = self.service.unassign_room_from_course(course)
        assert success
        assert course.assigned_room_id is None