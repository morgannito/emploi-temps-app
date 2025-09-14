from dataclasses import dataclass, field
from typing import Optional, Set
from domain.value_objects.time_slot import RoomCapacity


@dataclass
class RoomId:
    """Identifiant unique d'une salle"""
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass
class Room:
    """Entité représentant une salle de cours"""
    room_id: RoomId
    name: str
    capacity: RoomCapacity
    equipment: Set[str] = field(default_factory=set)
    building: Optional[str] = None
    floor: Optional[int] = None

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Room name cannot be empty")

    def can_accommodate_course(self, student_count: int) -> bool:
        """Vérifie si la salle peut accueillir un cours avec X étudiants"""
        return self.capacity.can_accommodate(student_count)

    def has_equipment(self, required_equipment: str) -> bool:
        """Vérifie si la salle possède un équipement donné"""
        return required_equipment.lower() in {eq.lower() for eq in self.equipment}

    def add_equipment(self, equipment_name: str) -> None:
        """Ajoute un équipement à la salle"""
        if equipment_name.strip():
            self.equipment.add(equipment_name.strip())

    def remove_equipment(self, equipment_name: str) -> None:
        """Retire un équipement de la salle"""
        self.equipment.discard(equipment_name.strip())

    def get_utilization_rate(self, student_count: int) -> float:
        """Calcule le taux d'occupation pour un nombre d'étudiants donné"""
        return self.capacity.utilization_rate(student_count)

    def is_suitable_for_course_type(self, course_type: str) -> bool:
        """Vérifie si la salle convient pour un type de cours donné"""
        course_type_lower = course_type.lower()

        if 'tp' in course_type_lower or 'pratique' in course_type_lower:
            return self.has_equipment('ordinateurs') or self.has_equipment('laboratoire')
        elif 'amphi' in course_type_lower or 'magistral' in course_type_lower:
            return self.capacity.max_students >= 50
        else:
            return True  # Cours standard, toute salle convient

    @property
    def full_location(self) -> str:
        """Localisation complète de la salle"""
        parts = [self.name]
        if self.building:
            parts.append(f"Bât. {self.building}")
        if self.floor is not None:
            parts.append(f"Étage {self.floor}")
        return " - ".join(parts)

    def to_dict(self) -> dict:
        """Conversion en dictionnaire pour compatibilité"""
        return {
            'id': str(self.room_id),
            'nom': self.name,
            'capacite': self.capacity.max_students,
            'equipment': list(self.equipment),
            'building': self.building,
            'floor': self.floor,
            'full_location': self.full_location
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Room':
        """Création depuis un dictionnaire"""
        room_id = RoomId(data['id'])
        capacity = RoomCapacity(data['capacite'])

        equipment = set(data.get('equipment', []))

        return cls(
            room_id=room_id,
            name=data['nom'],
            capacity=capacity,
            equipment=equipment,
            building=data.get('building'),
            floor=data.get('floor')
        )