from dataclasses import dataclass
from typing import Optional
from datetime import time


@dataclass(frozen=True)
class TimeSlot:
    """Value Object représentant un créneau horaire"""
    start_time: time
    end_time: time

    def __post_init__(self):
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time")

    @property
    def duration_minutes(self) -> int:
        """Durée en minutes"""
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        return end_minutes - start_minutes

    @property
    def duration_hours(self) -> float:
        """Durée en heures décimales"""
        return self.duration_minutes / 60.0

    def overlaps_with(self, other: 'TimeSlot') -> bool:
        """Vérifie si ce créneau chevauche avec un autre"""
        return not (self.end_time <= other.start_time or other.end_time <= self.start_time)

    def contains(self, point_time: time) -> bool:
        """Vérifie si une heure donnée est dans ce créneau"""
        return self.start_time <= point_time <= self.end_time

    @classmethod
    def from_strings(cls, start_str: str, end_str: str) -> 'TimeSlot':
        """Crée un TimeSlot à partir de chaînes HH:MM"""
        start_time = time.fromisoformat(start_str)
        end_time = time.fromisoformat(end_str)
        return cls(start_time, end_time)

    def to_display_format(self) -> str:
        """Format d'affichage lisible"""
        return f"{self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"


@dataclass(frozen=True)
class WeekIdentifier:
    """Value Object pour identifier une semaine académique"""
    number: int
    type_letter: str  # A ou B

    def __post_init__(self):
        if not (1 <= self.number <= 53):
            raise ValueError("Week number must be between 1 and 53")
        if self.type_letter not in ('A', 'B'):
            raise ValueError("Type letter must be 'A' or 'B'")

    @classmethod
    def from_string(cls, week_str: str) -> 'WeekIdentifier':
        """Parse 'Semaine 37 A' -> WeekIdentifier(37, 'A')"""
        parts = week_str.strip().split()
        if len(parts) != 3 or parts[0] != 'Semaine':
            raise ValueError(f"Invalid week format: {week_str}")

        number = int(parts[1])
        type_letter = parts[2]
        return cls(number, type_letter)

    def __str__(self) -> str:
        return f"Semaine {self.number} {self.type_letter}"

    @property
    def value(self) -> str:
        """Compatibilité legacy - retourne la représentation string"""
        return str(self)


@dataclass(frozen=True)
class RoomCapacity:
    """Value Object pour la capacité d'une salle"""
    max_students: int

    def __post_init__(self):
        if self.max_students <= 0:
            raise ValueError("Room capacity must be positive")

    def can_accommodate(self, student_count: int) -> bool:
        """Vérifie si la salle peut accueillir le nombre d'étudiants"""
        return student_count <= self.max_students

    def utilization_rate(self, student_count: int) -> float:
        """Taux d'occupation en pourcentage"""
        if student_count > self.max_students:
            return 1.0  # Suroccupation = 100%
        return student_count / self.max_students