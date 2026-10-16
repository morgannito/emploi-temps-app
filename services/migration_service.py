import json
import os
from typing import Dict, List
from models import db, Course, Room, Professor, CustomCourse, TPName
from services.database_service import DatabaseService
from excel_parser import ExcelScheduleParser
from datetime import datetime


class MigrationService:
    """Service de migration des données JSON vers SQLite"""

    def __init__(self):
        self.excel_parser = ExcelScheduleParser()

    def migrate_all_data(self) -> Dict[str, int]:
        """Migration complète des données avec compteurs"""
        print("🚀 Début migration JSON → SQLite...")

        # Créer toutes les tables
        db.create_all()

        counters = {
            'courses': 0,
            'rooms': 0,
            'professors': 0,
            'custom_courses': 0,
            'tp_names': 0,
            'errors': 0
        }

        # Migrer les salles
        counters['rooms'] = self._migrate_rooms()

        # Migrer les cours normaux
        counters['courses'] = self._migrate_courses()

        # Migrer les cours personnalisés
        counters['custom_courses'] = self._migrate_custom_courses()

        # Migrer les noms de TP
        counters['tp_names'] = self._migrate_tp_names()

        # Migrer les professeurs
        counters['professors'] = self._migrate_professors()

        print(f"✅ Migration terminée: {counters}")
        return counters

    def _migrate_rooms(self) -> int:
        """Migre les salles depuis salle.json"""
        try:
            salle_path = "data/salle.json"
            if not os.path.exists(salle_path):
                print("⚠️  Fichier salle.json non trouvé")
                return 0

            with open(salle_path, 'r', encoding='utf-8') as f:
                salle_data = json.load(f)

            count = 0
            for room_data in salle_data.get('rooms', []):
                room = Room(
                    room_id=room_data['_id'],
                    name=room_data['name'],
                    capacity=room_data.get('capacity')
                )
                db.session.add(room)
                count += 1

            db.session.commit()
            print(f"📍 Salles migrées: {count}")
            return count

        except Exception as e:
            print(f"❌ Erreur migration salles: {e}")
            db.session.rollback()
            return 0

    def _migrate_courses(self) -> int:
        """Migre les cours normaux depuis professors_canonical_schedule.json"""
        try:
            # Essayer plusieurs fichiers possibles (ordre prioritaire)
            possible_files = [
                "data/professors_canonical_schedule.json",  # 7332 cours - priorité 1
                "data/canonical_schedules.json",
                "data/extracted_schedules.json"  # seulement 198 cours - priorité basse
            ]

            schedules_path = None
            for path in possible_files:
                if os.path.exists(path):
                    schedules_path = path
                    print(f"📁 Fichier trouvé: {path}")
                    break

            if not schedules_path:
                print("⚠️  Aucun fichier de cours trouvé")
                return 0

            with open(schedules_path, 'r', encoding='utf-8') as f:
                schedules_data = json.load(f)

            # Charger les attributions de salles
            room_assignments = self._load_room_assignments()

            count = 0

            # Détecter le format du fichier
            if isinstance(schedules_data, dict):
                sample_key = next(iter(schedules_data.keys()))
                sample_value = schedules_data[sample_key]

                # Format 1: {semaine: {jour: [courses]}} - format extracted_schedules
                if isinstance(sample_value, dict) and any(isinstance(v, list) for v in sample_value.values()) and 'courses' not in sample_value:
                    print("📖 Format détecté: extracted_schedules (semaine/jour)")
                    for week_name, days_data in schedules_data.items():
                        for day_name, courses_list in days_data.items():
                            for course_data in courses_list:
                                try:
                                    # Utiliser l'ID existant ou en générer un
                                    course_id = course_data.get('course_id') or course_data.get('id') or f"{course_data.get('professor', '')}_{week_name}_{day_name}_{count}"

                                    # Les données sont déjà parsées
                                    assigned_room = course_data.get('assigned_room')
                                    if assigned_room is None:  # Chercher dans room_assignments
                                        assigned_room = room_assignments.get(course_id)

                                    course = Course(
                                        course_id=course_id,
                                        professor=course_data.get('professor', ''),
                                        week_name=week_name,
                                        day=day_name,
                                        start_time=course_data.get('start_time', '00:00'),
                                        end_time=course_data.get('end_time', '00:00'),
                                        duration_hours=course_data.get('duration_hours', 0),
                                        raw_time_slot=course_data.get('raw_time_slot', ''),
                                        course_type=course_data.get('course_type', ''),
                                        nb_students=course_data.get('nb_students', ''),
                                        assigned_room=assigned_room
                                    )

                                    db.session.add(course)
                                    count += 1

                                    # Commit par batch
                                    if count % 1000 == 0:
                                        db.session.commit()
                                        print(f"  📚 Cours migrés: {count}")

                                except Exception as e:
                                    print(f"❌ Erreur cours individuel: {e}")
                                    continue

                # Format 2: {prof: {courses: [...]}} - format principal
                elif isinstance(sample_value, dict) and 'courses' in sample_value:
                    print("📖 Format détecté: plat avec liste de cours")
                    for professor_name, prof_data in schedules_data.items():
                        courses_list = prof_data.get('courses', [])
                        for course_data in courses_list:
                            try:
                                # Générer un ID unique
                                course_id = f"{professor_name}_{course_data.get('day', '')}_{course_data.get('raw_time_slot', '')}_{count}"

                                # Les données sont déjà parsées dans ce format
                                assigned_room = course_data.get('assigned_room')
                                if assigned_room is None:  # Chercher dans room_assignments
                                    assigned_room = room_assignments.get(course_id)

                                course = Course(
                                    course_id=course_id,
                                    professor=professor_name,
                                    week_name="Générale",  # Pas de semaine spécifique dans ce format
                                    day=course_data.get('day', ''),
                                    start_time=course_data.get('start_time', '00:00'),
                                    end_time=course_data.get('end_time', '00:00'),
                                    duration_hours=course_data.get('duration_hours', 0),
                                    raw_time_slot=course_data.get('raw_time_slot', ''),
                                    course_type=course_data.get('course_type', ''),
                                    nb_students=course_data.get('nb_students', ''),
                                    assigned_room=assigned_room
                                )

                                db.session.add(course)
                                count += 1

                                # Commit par batch
                                if count % 1000 == 0:
                                    db.session.commit()
                                    print(f"  📚 Cours migrés: {count}")

                            except Exception as e:
                                print(f"❌ Erreur cours individuel: {e}")
                                continue

                # Format 3: {prof: {week: {day: [courses]}}} - ancien format hiérarchique
                elif isinstance(sample_value, dict) and any(isinstance(v, dict) for v in sample_value.values()):
                    print("📖 Format détecté: hiérarchique (prof/semaine/jour)")
                    for professor_name, weeks_data in schedules_data.items():
                        for week_name, days_data in weeks_data.items():
                            for day_name, courses_list in days_data.items():
                                count += self._process_courses_list(courses_list, professor_name, week_name, day_name, room_assignments, count)

            db.session.commit()
            print(f"📚 Cours normaux migrés: {count}")
            return count

        except Exception as e:
            print(f"❌ Erreur migration cours: {e}")
            db.session.rollback()
            return 0

    def _process_courses_list(self, courses_list, professor_name, week_name, day_name, room_assignments, count):
        """Helper pour traiter une liste de cours dans l'ancien format"""
        processed = 0
        for course_data in courses_list:
            try:
                # Générer un ID unique basé sur les données
                course_id = f"{professor_name}_{week_name}_{day_name}_{course_data.get('time_slot', '')}_{count + processed}"

                # Parser les horaires
                time_info = self.excel_parser.parse_time_range(course_data.get('time_slot', ''))
                if time_info:
                    start_time, end_time, duration = time_info
                else:
                    start_time, end_time, duration = "00:00", "00:00", 0

                # Récupérer la salle assignée
                assigned_room = room_assignments.get(course_id)

                course = Course(
                    course_id=course_id,
                    professor=professor_name,
                    week_name=week_name,
                    day=day_name,
                    start_time=start_time,
                    end_time=end_time,
                    duration_hours=duration,
                    raw_time_slot=course_data.get('time_slot', ''),
                    course_type=course_data.get('subject', ''),
                    nb_students=course_data.get('nb_students', ''),
                    assigned_room=assigned_room
                )

                db.session.add(course)
                processed += 1

                # Commit par batch
                if (count + processed) % 1000 == 0:
                    db.session.commit()
                    print(f"  📚 Cours migrés: {count + processed}")

            except Exception as e:
                print(f"❌ Erreur cours individuel: {e}")
                continue

        return processed

    def _migrate_custom_courses(self) -> int:
        """Migre les cours personnalisés depuis custom_courses.json"""
        try:
            custom_path = "data/custom_courses.json"
            if not os.path.exists(custom_path):
                print("⚠️  Fichier custom_courses.json non trouvé")
                return 0

            with open(custom_path, 'r', encoding='utf-8') as f:
                custom_data = json.load(f)

            if not isinstance(custom_data, list):
                print("⚠️  custom_courses.json n'est pas une liste, migration ignorée")
                return 0

            count = 0
            for course_data in custom_data:
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
                count += 1

            db.session.commit()
            print(f"🎯 Cours personnalisés migrés: {count}")
            return count

        except Exception as e:
            print(f"❌ Erreur migration cours personnalisés: {e}")
            db.session.rollback()
            return 0

    def _migrate_tp_names(self) -> int:
        """Migre les noms de TP depuis tp_names.json"""
        try:
            tp_names_path = "data/tp_names.json"
            if not os.path.exists(tp_names_path):
                print("⚠️  Fichier tp_names.json non trouvé")
                return 0

            with open(tp_names_path, 'r', encoding='utf-8') as f:
                tp_names_data = json.load(f)

            count = 0
            for course_id, tp_name in tp_names_data.items():
                tp = TPName(
                    course_id=course_id,
                    tp_name=tp_name
                )
                db.session.add(tp)
                count += 1

            db.session.commit()
            print(f"🏷️  Noms TP migrés: {count}")
            return count

        except Exception as e:
            print(f"❌ Erreur migration noms TP: {e}")
            db.session.rollback()
            return 0

    def _migrate_professors(self) -> int:
        """Migre les données professeurs depuis prof_data.json"""
        try:
            prof_data_path = "data/prof_data.json"
            if not os.path.exists(prof_data_path):
                print("⚠️  Fichier prof_data.json non trouvé")
                return 0

            with open(prof_data_path, 'r', encoding='utf-8') as f:
                prof_data = json.load(f)

            count = 0
            for professor_name, prof_info in prof_data.items():
                professor = Professor(
                    name=professor_name,
                    color=prof_info.get('color'),
                    working_days=json.dumps(prof_info.get('working_days', []))
                )
                db.session.add(professor)
                count += 1

            db.session.commit()
            print(f"👨‍🏫 Professeurs migrés: {count}")
            return count

        except Exception as e:
            print(f"❌ Erreur migration professeurs: {e}")
            db.session.rollback()
            return 0

    def _load_room_assignments(self) -> Dict[str, str]:
        """Charge les attributions de salles depuis room_assignments.json"""
        try:
            assignments_path = "data/room_assignments.json"
            if not os.path.exists(assignments_path):
                return {}

            with open(assignments_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def verify_migration(self) -> Dict[str, int]:
        """Vérifie la migration en comptant les enregistrements"""
        return {
            'courses': Course.query.count(),
            'rooms': Room.query.count(),
            'professors': Professor.query.count(),
            'custom_courses': CustomCourse.query.count(),
            'tp_names': TPName.query.count()
        }

    def benchmark_queries(self):
        """Test les performances des nouvelles queries"""
        import time

        print("\n🏃‍♂️ Test performance queries SQLite:")

        # Test 1: Tous les cours
        start = time.time()
        all_courses = DatabaseService.get_all_courses()
        elapsed = (time.time() - start) * 1000
        print(f"  📊 Tous les cours: {len(all_courses)} en {elapsed:.2f}ms")

        # Test 2: Cours par semaine
        if all_courses:
            week_name = all_courses[0].week_name
            start = time.time()
            week_courses = DatabaseService.get_courses_by_week(week_name)
            elapsed = (time.time() - start) * 1000
            print(f"  📅 Cours semaine '{week_name}': {len(week_courses)} en {elapsed:.2f}ms")

        # Test 3: Cours par professeur
        if all_courses:
            prof_name = all_courses[0].professor
            start = time.time()
            prof_courses = DatabaseService.get_courses_by_professor(prof_name)
            elapsed = (time.time() - start) * 1000
            print(f"  👨‍🏫 Cours prof '{prof_name}': {len(prof_courses)} en {elapsed:.2f}ms")

        # Test 4: Professeurs uniques
        start = time.time()
        professors = DatabaseService.get_all_professors()
        elapsed = (time.time() - start) * 1000
        print(f"  👥 Professeurs uniques: {len(professors)} en {elapsed:.2f}ms")