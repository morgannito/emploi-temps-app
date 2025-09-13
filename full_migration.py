#!/usr/bin/env python3
"""
Script de migration complète JSON vers SQLite
Migre toutes les données existantes du ScheduleManager vers la base SQLite
"""

import time
from app_new import app, schedule_manager
from models import db, Course, Room, Professor, CustomCourse, TPName
from services.database_service import DatabaseService


class FullMigrationService:
    """Service de migration complète des données depuis le ScheduleManager"""

    def __init__(self):
        self.batch_size = 1000
        self.counters = {
            'courses': 0,
            'rooms': 0,
            'professors': 0,
            'custom_courses': 0,
            'tp_names': 0,
            'errors': 0
        }

    def run_full_migration(self):
        """Lance la migration complète"""
        print("🚀 MIGRATION COMPLÈTE JSON → SQLite")
        print("=" * 50)

        start_time = time.time()

        # Forcer le mode JSON pour charger toutes les données
        schedule_manager.use_database = False

        # Reset de la base
        print("🗑️  Reset de la base SQLite...")
        db.drop_all()
        db.create_all()

        # Migrer les données
        self._migrate_rooms()
        self._migrate_all_courses_from_json()
        self._migrate_custom_courses()
        self._migrate_tp_names()
        self._migrate_professors()

        elapsed = time.time() - start_time
        print(f"\n✅ Migration terminée en {elapsed:.2f}s")
        print(f"📊 Résultats: {self.counters}")

        # Vérifier la migration
        self._verify_migration()

        return self.counters

    def _migrate_rooms(self):
        """Migre les salles depuis salle.json"""
        try:
            import json
            import os

            salle_path = "data/salle.json"
            if not os.path.exists(salle_path):
                print("⚠️  Fichier salle.json non trouvé")
                return

            with open(salle_path, 'r', encoding='utf-8') as f:
                salle_data = json.load(f)

            for room_data in salle_data.get('rooms', []):
                room = Room(
                    room_id=room_data['_id'],
                    name=room_data['name'],
                    capacity=room_data.get('capacity')
                )
                db.session.add(room)
                self.counters['rooms'] += 1

            db.session.commit()
            print(f"📍 Salles migrées: {self.counters['rooms']}")

        except Exception as e:
            print(f"❌ Erreur migration salles: {e}")
            db.session.rollback()

    def _migrate_all_courses_from_json(self):
        """Migre tous les cours depuis le ScheduleManager (JSON)"""
        try:
            print("📚 Chargement des cours depuis JSON...")
            all_courses = schedule_manager.get_all_courses()

            print(f"📊 Total des cours à migrer: {len(all_courses)}")

            # Charger les attributions de salles
            room_assignments = self._load_room_assignments()

            for i, course in enumerate(all_courses):
                try:
                    # Récupérer la salle assignée
                    assigned_room = getattr(course, 'assigned_room', None)
                    if assigned_room is None:
                        assigned_room = room_assignments.get(course.course_id)

                    # Créer l'objet Course SQLAlchemy
                    db_course = Course(
                        course_id=course.course_id,
                        professor=course.professor,
                        week_name=course.week_name,
                        day=course.day,
                        start_time=course.start_time,
                        end_time=course.end_time,
                        duration_hours=course.duration_hours,
                        raw_time_slot=course.raw_time_slot,
                        course_type=course.course_type,
                        nb_students=course.nb_students,
                        assigned_room=assigned_room
                    )

                    db.session.add(db_course)
                    self.counters['courses'] += 1

                    # Commit par batch pour éviter les timeouts
                    if self.counters['courses'] % self.batch_size == 0:
                        db.session.commit()
                        print(f"  ⚡ Batch migré: {self.counters['courses']} cours")

                except Exception as e:
                    print(f"❌ Erreur cours #{i}: {e}")
                    self.counters['errors'] += 1
                    continue

            # Commit final
            db.session.commit()
            print(f"📚 Cours migrés: {self.counters['courses']}")

        except Exception as e:
            print(f"❌ Erreur migration cours: {e}")
            db.session.rollback()

    def _migrate_custom_courses(self):
        """Migre les cours personnalisés"""
        try:
            custom_courses = schedule_manager.tp_management_service.get_all_custom_courses()

            for course_data in custom_courses:
                custom_course = CustomCourse(
                    course_id=course_data['course_id'],
                    professor=course_data['professor'],
                    week_name=course_data['week_name'],
                    day=course_data['day'],
                    start_time=course_data['start_time'],
                    end_time=course_data['end_time'],
                    duration_hours=course_data['duration_hours'],
                    raw_time_slot=course_data.get('raw_time_slot', ''),
                    course_type=course_data['course_type'],
                    nb_students=course_data.get('nb_students', ''),
                    assigned_room=course_data.get('assigned_room')
                )

                db.session.add(custom_course)
                self.counters['custom_courses'] += 1

            db.session.commit()
            print(f"🎯 Cours personnalisés migrés: {self.counters['custom_courses']}")

        except Exception as e:
            print(f"❌ Erreur migration cours personnalisés: {e}")
            db.session.rollback()

    def _migrate_tp_names(self):
        """Migre les noms de TP"""
        try:
            tp_names_data = schedule_manager.tp_management_service.get_all_tp_names()

            for course_id, tp_name in tp_names_data.items():
                tp = TPName(
                    course_id=course_id,
                    tp_name=tp_name
                )
                db.session.add(tp)
                self.counters['tp_names'] += 1

            db.session.commit()
            print(f"🏷️  Noms TP migrés: {self.counters['tp_names']}")

        except Exception as e:
            print(f"❌ Erreur migration noms TP: {e}")
            db.session.rollback()

    def _migrate_professors(self):
        """Migre les données professeurs"""
        try:
            import json
            import os

            prof_data_path = "data/prof_data.json"
            if not os.path.exists(prof_data_path):
                print("⚠️  Fichier prof_data.json non trouvé")
                return

            with open(prof_data_path, 'r', encoding='utf-8') as f:
                prof_data = json.load(f)

            for professor_name, prof_info in prof_data.items():
                professor = Professor(
                    name=professor_name,
                    color=prof_info.get('color'),
                    working_days=json.dumps(prof_info.get('working_days', []))
                )
                db.session.add(professor)
                self.counters['professors'] += 1

            db.session.commit()
            print(f"👨‍🏫 Professeurs migrés: {self.counters['professors']}")

        except Exception as e:
            print(f"❌ Erreur migration professeurs: {e}")
            db.session.rollback()

    def _load_room_assignments(self):
        """Charge les attributions de salles"""
        try:
            import json
            import os

            assignments_path = "data/room_assignments.json"
            if not os.path.exists(assignments_path):
                return {}

            with open(assignments_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _verify_migration(self):
        """Vérifie la migration"""
        print("\n🔍 VÉRIFICATION DE LA MIGRATION")
        print("-" * 30)

        courses_count = Course.query.count()
        rooms_count = Room.query.count()
        professors_count = Professor.query.count()
        custom_courses_count = CustomCourse.query.count()
        tp_names_count = TPName.query.count()

        print(f"📚 Cours: {courses_count}")
        print(f"📍 Salles: {rooms_count}")
        print(f"👨‍🏫 Professeurs: {professors_count}")
        print(f"🎯 Cours personnalisés: {custom_courses_count}")
        print(f"🏷️  Noms TP: {tp_names_count}")

        # Vérifier quelques semaines
        weeks = db.session.query(Course.week_name).distinct().all()
        print(f"📅 Semaines dans la DB: {len(weeks)}")

        if courses_count > 7000:
            print("✅ Migration réussie - toutes les données sont présentes!")
        else:
            print("⚠️  Migration incomplète - vérifier les données")


def main():
    """Point d'entrée principal"""
    with app.app_context():
        migration_service = FullMigrationService()
        results = migration_service.run_full_migration()

        # Test des performances
        print("\n⚡ TEST PERFORMANCE SQLite")
        print("-" * 30)

        start = time.time()
        all_courses = DatabaseService.get_all_courses()
        elapsed = (time.time() - start) * 1000
        print(f"📊 Tous les cours: {len(all_courses)} en {elapsed:.2f}ms")

        if len(all_courses) > 0:
            # Test par semaine
            week_name = all_courses[0].week_name
            start = time.time()
            week_courses = DatabaseService.get_courses_by_week(week_name)
            elapsed = (time.time() - start) * 1000
            print(f"📅 Semaine '{week_name}': {len(week_courses)} en {elapsed:.2f}ms")

            # Test par professeur
            prof_name = all_courses[0].professor
            start = time.time()
            prof_courses = DatabaseService.get_courses_by_professor(prof_name)
            elapsed = (time.time() - start) * 1000
            print(f"👨‍🏫 Prof '{prof_name}': {len(prof_courses)} en {elapsed:.2f}ms")


if __name__ == "__main__":
    main()