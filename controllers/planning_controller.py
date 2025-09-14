from flask import render_template, request, send_file, jsonify, redirect, url_for
from datetime import datetime
from controllers.base_controller import BaseController
from services.week_service import WeekService
from services.timeslot_service import TimeSlotService
from services.course_grid_service import CourseGridService
from services.planning_service import PlanningService
from services.planning_v2_service import PlanningV2Service
from services.pdf_export_service import PDFExportService
from services.kiosque_service import KiosqueService
from services.database_service import DatabaseService
import time


class PlanningController(BaseController):
    """Contrôleur pour la gestion du planning et des vues"""

    def __init__(self, schedule_manager, cache_service):
        self.schedule_manager = schedule_manager
        self.cache_service = cache_service
        self.planning_v2_service = PlanningV2Service(schedule_manager)
        super().__init__('planning', url_prefix='')

    def _register_routes(self):
        """Enregistrement des routes pour le planning"""
        # Routes principales
        self.blueprint.route('/')(self.admin)
        self.blueprint.route('/week/<week_name>')(self.admin)

        # Vues planning
        self.blueprint.route('/planning')(self.planning_readonly)
        self.blueprint.route('/planning/<week_name>')(self.planning_readonly)
        self.blueprint.route('/planning_v2')(self.planning_v2)
        self.blueprint.route('/planning_v2/<week_name>')(self.planning_v2)
        self.blueprint.route('/planning_v2_fast')(self.planning_v2_fast)
        self.blueprint.route('/planning_v2_fast/<week_name>')(self.planning_v2_fast)
        self.blueprint.route('/planning_spa')(self.planning_v2_spa)
        self.blueprint.route('/planning_spa/<week_name>')(self.planning_v2_spa)

        # Vues jour/semaine
        self.blueprint.route('/day/<week_name>/<day_name>')(self.day_view)

        # Export PDF
        self.blueprint.route('/export_week_pdf/<week_name>')(self.export_week_pdf)
        self.blueprint.route('/export_day_pdf/<week_name>/<day_name>')(self.export_day_pdf)

        # Vues kiosque et étudiants
        self.blueprint.route('/student')(self.student_view)
        self.blueprint.route('/student/<week_name>')(self.student_view)
        self.blueprint.route('/kiosque/week')(self.kiosque_week)
        self.blueprint.route('/kiosque/week/<week_name>')(self.kiosque_week)
        self.blueprint.route('/kiosque/room')(self.kiosque_room)
        self.blueprint.route('/kiosque/room/<room_id>')(self.kiosque_room)
        self.blueprint.route('/tv/schedule')(self.tv_schedule)
        self.blueprint.route('/kiosque/halfday')(self.kiosque_halfday)
        self.blueprint.route('/kiosque/halfday/<layout>')(self.kiosque_halfday)

        # Redirections SPA
        self.blueprint.route('/spa')(self.spa_redirect)
        self.blueprint.route('/spa/week/<week_name>')(self.spa_redirect)

        # API routes
        self.blueprint.route('/api/week_data/<week_name>')(self.api_week_data)
        self.blueprint.route('/api/display/current')(self.api_display_current)
        self.blueprint.route('/api/course_details/<course_id>')(self.api_course_details)
        self.blueprint.route('/api/weeks')(self.api_weeks)

        # API v2 Clean Architecture
        self.blueprint.route('/api/v2/courses/<week_name>')(self.api_v2_courses_by_week)
        self.blueprint.route('/api/v2/courses/<course_id>/validate-schedule')(self.api_v2_validate_schedule)

        # Monitoring et migration
        self.blueprint.route('/migrate')(self.migrate_database)
        self.blueprint.route('/switch_to_db')(self.switch_to_database)
        self.blueprint.route('/switch_to_json')(self.switch_to_json)
        self.blueprint.route('/api/db_monitor')(self.db_monitor_stats)
        self.blueprint.route('/api/db_monitor/clear')(self.clear_db_monitor)

    def admin(self, week_name=None):
        """Page d'administration principale avec vue hebdomadaire"""
        # Forcer la synchronisation
        self.schedule_manager.force_sync_data()

        # Vérifier la cohérence des données
        try:
            all_courses = self.schedule_manager.get_all_courses()
            room_assignments_count = len(self.schedule_manager.room_assignments)
            courses_with_rooms = sum(1 for c in all_courses if c.assigned_room)

            if abs(room_assignments_count - courses_with_rooms) > 5:
                print(f"Warning: Incohérence détectée - Attributions: {room_assignments_count}, Cours avec salles: {courses_with_rooms}")
                self.schedule_manager.force_sync_data()
        except Exception as e:
            print(f"Erreur lors de la vérification de cohérence: {e}")

        # Générer les données de planning
        weeks_to_display = WeekService.generate_academic_calendar()

        if not weeks_to_display:
            return "Erreur lors de la génération du calendrier.", 500

        # Déterminer la semaine à afficher
        if week_name is None:
            week_name = WeekService.get_current_week_name(weeks_to_display)

        # Trouver les informations de la semaine
        current_week_info = WeekService.find_week_info(week_name, weeks_to_display)
        if not current_week_info:
            current_week_info = weeks_to_display[0]
            week_name = current_week_info['name']

        # Générer la grille horaire
        time_slots = TimeSlotService.generate_time_grid()
        days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

        # Préparer les cours pour la semaine
        all_courses_for_week = CourseGridService.prepare_courses_for_week(self.schedule_manager, week_name)
        courses_to_place_in_grid = CourseGridService.prepare_courses_with_tps(all_courses_for_week)

        # Construire la grille hebdomadaire
        weekly_grid = CourseGridService.build_weekly_grid(courses_to_place_in_grid, time_slots, days_order)

        return render_template('admin_spa.html',
                             weekly_grid=weekly_grid,
                             time_slots=time_slots,
                             days_order=days_order,
                             rooms=self.schedule_manager.rooms,
                             get_room_name=self.schedule_manager.get_room_name,
                             all_weeks=weeks_to_display,
                             current_week=week_name,
                             current_week_info=current_week_info,
                             all_professors=self.schedule_manager.get_normalized_professors_list())

    def planning_readonly(self, week_name=None):
        """Vue planning en lecture seule"""
        planning_data = PlanningService.get_planning_data(self.schedule_manager, week_name)

        return render_template('planning_readonly.html',
                             week_name=planning_data['week_name'],
                             weeks_to_display=planning_data['weeks_to_display'],
                             current_week_info=planning_data['current_week_info'],
                             courses=planning_data['courses'],
                             courses_by_day_time=planning_data['courses_by_day_time'],
                             days=planning_data['days'],
                             time_slots=planning_data['time_slots'],
                             all_weeks=planning_data['all_weeks'],
                             current_week=week_name,
                             all_professors=self.schedule_manager.get_normalized_professors_list())

    def planning_v2(self, week_name=None):
        """Planning V2 - Affichage en lecture seule"""
        self.schedule_manager.force_sync_data()

        # Vérifier la cohérence des données
        self.planning_v2_service.verify_data_consistency()

        weeks_to_display = self.planning_v2_service.generate_academic_calendar()
        if not weeks_to_display:
            return "Erreur lors de la génération du calendrier.", 500

        if week_name is None:
            week_name = self.planning_v2_service.determine_current_week(weeks_to_display)

        current_week_info = self.planning_v2_service.find_week_info(week_name, weeks_to_display)

        time_slots = self.planning_v2_service.generate_time_grid()
        days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

        courses_for_week = self.planning_v2_service.get_courses_for_week(week_name)
        weekly_grid = self.planning_v2_service.build_weekly_grid(courses_for_week, time_slots, days_order)

        context = self.planning_v2_service.prepare_template_context(
            weekly_grid, time_slots, days_order, weeks_to_display, week_name, current_week_info
        )

        return render_template('planning_v2.html', **context)

    def planning_v2_fast(self, week_name=None):
        """Planning V2 Optimisé avec cache"""
        try:
            context = self.planning_v2_service.handle_fast_planning(
                week_name=week_name,
                cache_service=self.cache_service
            )
            return render_template('planning_v2.html', **context)
        except Exception as e:
            print(f"Erreur planning_v2_fast: {e}")
            return "Erreur lors de la génération du calendrier.", 500

    def planning_v2_spa(self, week_name=None):
        """Planning V2 SPA avec navigation AJAX"""
        print(f"🎯 Route /planning_spa appelée avec week_name={week_name}")

        try:
            context = self.planning_v2_service.handle_fast_planning(
                week_name=week_name,
                cache_service=self.cache_service
            )
            print(f"🎯 Contexte généré: {len(context)} éléments")
            return render_template('planning_v2_spa.html', **context)
        except Exception as e:
            print(f"❌ Erreur planning_v2_spa: {e}")
            import traceback
            traceback.print_exc()
            return f"Erreur lors de la génération du calendrier: {str(e)}", 500

    def day_view(self, week_name, day_name):
        """Page d'attribution des salles pour un jour spécifique"""
        self.schedule_manager.force_sync_data()
        data = self.schedule_manager.day_view_service.generate_day_view_data(week_name, day_name)
        return render_template('day_view.html', **data)

    def export_week_pdf(self, week_name):
        """Export PDF de la semaine"""
        try:
            buffer = PDFExportService.export_week_pdf(self.schedule_manager, week_name)
            return send_file(
                buffer,
                as_attachment=True,
                download_name=f"emploi_du_temps_{week_name.replace(' ', '_')}.pdf",
                mimetype='application/pdf'
            )
        except Exception as e:
            return f"Erreur lors de la génération du PDF: {str(e)}", 500

    def export_day_pdf(self, week_name, day_name):
        """Export PDF d'une journée"""
        try:
            buffer = PDFExportService.export_day_pdf(self.schedule_manager, week_name, day_name)
            filename = f"cours_{day_name}_{week_name.replace(' ', '_')}.pdf"
            return send_file(
                buffer,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        except Exception as e:
            return f"Erreur lors de la génération du PDF: {str(e)}", 500

    def student_view(self, week_name=None):
        """Redirection vers la vue kiosque compact"""
        return redirect(url_for('planning.kiosque_halfday', layout='compact'))

    def kiosque_week(self, week_name=None):
        """Vue kiosque - semaine complète"""
        kiosque_data = KiosqueService.get_kiosque_week_data(self.schedule_manager, week_name)
        return render_template('kiosque_week.html',
                             week_grid=kiosque_data['week_grid'],
                             time_slots=kiosque_data['time_slots'],
                             days_order=kiosque_data['days_order'],
                             current_week=kiosque_data['current_week'],
                             total_courses=kiosque_data['total_courses'])

    def kiosque_room(self, room_id=None):
        """Vue kiosque - occupation des salles"""
        kiosque_data = KiosqueService.get_kiosque_room_data(self.schedule_manager, room_id)
        return render_template('kiosque_room.html',
                             rooms_data=kiosque_data['rooms_data'],
                             current_week=kiosque_data['current_week'],
                             focused_room=kiosque_data['focused_room'])

    def tv_schedule(self):
        """Affichage TV défilant automatique"""
        tv_data = KiosqueService.get_tv_schedule_data(self.schedule_manager)
        return render_template('tv_schedule.html',
                             current_courses=tv_data['current_courses'],
                             upcoming_courses=tv_data['upcoming_courses'],
                             current_week=tv_data['current_week'],
                             current_day=tv_data['current_day'],
                             current_time=tv_data['current_time'])

    def kiosque_halfday(self, layout="standard"):
        """Vue kiosque - demi-journée avec détection automatique"""
        kiosque_data = KiosqueService.get_kiosque_halfday_data(self.schedule_manager, layout)
        return render_template(kiosque_data['template_name'],
                             time_slots_data=kiosque_data['time_slots_data'],
                             time_slots=kiosque_data['time_slots'],
                             current_week=kiosque_data['current_week'],
                             current_day=kiosque_data['current_day'],
                             period=kiosque_data['period'],
                             period_label=kiosque_data['period_label'],
                             time_range=kiosque_data['time_range'],
                             total_courses=kiosque_data['total_courses'],
                             current_time=kiosque_data['current_time'],
                             layout=kiosque_data['layout'])

    def spa_redirect(self, week_name=None):
        """Redirection de l'ancienne route SPA"""
        if week_name:
            return redirect(url_for('planning.admin', week_name=week_name), code=301)
        else:
            return redirect(url_for('planning.admin'), code=301)

    def api_week_data(self, week_name):
        """API JSON optimisée pour le SPA"""
        try:
            start_time = time.time()
            courses = DatabaseService.get_courses_by_week(week_name)

            # Format SPA optimisé
            formatted_courses = []
            time_slot_mapping = {
                '08:00': '8h00-9h00', '09:00': '9h00-10h00', '10:00': '10h00-11h00',
                '11:00': '11h00-12h00', '12:00': '12h00-13h00', '13:00': '13h00-14h00',
                '14:00': '14h00-15h00', '15:00': '15h00-16h00', '16:00': '16h00-17h00',
                '17:00': '17h00-18h00'
            }

            for course in courses:
                time_slot = time_slot_mapping.get(
                    course.start_time,
                    course.raw_time_slot or f"{course.start_time}-{course.end_time}"
                )

                formatted_course = {
                    'course_id': course.course_id,
                    'professor': course.professor,
                    'course_type': course.course_type,
                    'day': course.day,
                    'time_slot': time_slot,
                    'start_time': course.start_time,
                    'end_time': course.end_time,
                    'duration_hours': course.duration_hours,
                    'nb_students': course.nb_students or '',
                    'assigned_room': course.assigned_room
                }
                formatted_courses.append(formatted_course)

            elapsed = (time.time() - start_time) * 1000

            response_data = {
                'success': True,
                'week_name': week_name,
                'courses': formatted_courses,
                'total_courses': len(formatted_courses),
                'performance': {
                    'query_time_ms': round(elapsed, 2),
                    'courses_count': len(formatted_courses)
                }
            }

            print(f"🚀 SPA API /api/week_data/{week_name}: {len(formatted_courses)} cours en {elapsed:.2f}ms")
            return jsonify(response_data)

        except Exception as e:
            print(f"❌ Erreur SPA API week_data: {e}")
            return jsonify({
                'success': False,
                'error': str(e),
                'week_name': week_name
            }), 500

    def api_display_current(self):
        """API JSON - cours actuels"""
        import pytz
        from dataclasses import asdict

        now = datetime.now(pytz.timezone("Europe/Paris"))
        current_time = now.strftime('%H:%M')
        current_day = now.strftime('%A')
        day_translation = {
            'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi', 'Friday': 'Vendredi'
        }
        current_day_fr = day_translation.get(current_day, 'Lundi')

        week_num = now.isocalendar()[1]
        if now.year == 2025 and week_num >= 36:
            weeks_since_start = week_num - 36
            is_type_A = (weeks_since_start % 2) == 0
            week_type = "A" if is_type_A else "B"
            current_week = f"Semaine {week_num} {week_type}"

        all_courses = self.schedule_manager.get_all_courses()
        current_courses = []

        for course in all_courses:
            if (course.week_name == current_week and
                course.day == current_day_fr and
                course.assigned_room and
                course.start_time <= current_time <= course.end_time):

                course_dict = asdict(course)
                course_dict['room_name'] = self.schedule_manager.get_room_name(course.assigned_room)
                current_courses.append(course_dict)

        return jsonify({
            'current_time': current_time,
            'current_day': current_day_fr,
            'current_week': current_week,
            'courses': current_courses,
            'total_courses': len(current_courses)
        })

    def api_course_details(self, course_id):
        """API pour les détails d'un cours spécifique"""
        try:
            return jsonify({
                'success': True,
                'course_id': course_id,
                'details': {
                    'status': 'normal',
                    'capacity': '25 étudiants',
                    'equipment': 'Standard',
                    'notes': 'Cours régulier'
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def api_weeks(self):
        """API pour la liste des semaines disponibles"""
        try:
            from services.database_service import DatabaseService
            weeks = DatabaseService.get_all_weeks()
            return jsonify({'success': True, 'weeks': weeks})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def api_v2_courses_by_week(self, week_name):
        """API Clean Architecture - Récupère les cours par semaine"""
        try:
            from application.services.course_application_service import CourseApplicationService
            course_service = CourseApplicationService()
            courses = course_service.get_courses_by_week(week_name)

            return jsonify({
                'success': True,
                'data': courses,
                'architecture': 'clean-ddd'
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def api_v2_validate_schedule(self, course_id):
        """API Clean Architecture - Validation d'intégrité du planning"""
        try:
            from application.services.course_application_service import CourseApplicationService
            course_service = CourseApplicationService()
            conflicts = course_service.find_conflicting_courses(course_id)

            return jsonify({
                'success': True,
                'conflicts': conflicts,
                'has_conflicts': len(conflicts) > 0
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def migrate_database(self):
        """Route pour migrer les données JSON vers SQLite"""
        try:
            from services.migration_service import MigrationService
            migration_service = MigrationService()
            counters = migration_service.migrate_all_data()

            migration_service.benchmark_queries()

            return jsonify({
                'success': True,
                'message': 'Migration terminée',
                'counters': counters
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def switch_to_database(self):
        """Bascule vers le mode base de données"""
        self.schedule_manager.use_database = True
        return jsonify({
            'success': True,
            'message': 'Application basculée vers SQLite'
        })

    def switch_to_json(self):
        """Bascule vers le mode JSON"""
        self.schedule_manager.use_database = False
        return jsonify({
            'success': True,
            'message': 'Application basculée vers JSON'
        })

    def db_monitor_stats(self):
        """Route de monitoring des performances de base de données"""
        try:
            from services.db_monitoring_service import db_monitor

            performance_summary = db_monitor.get_performance_summary()
            database_info = db_monitor.get_database_info()
            query_patterns = db_monitor.analyze_query_patterns()

            return jsonify({
                'success': True,
                'performance': performance_summary,
                'database': database_info,
                'patterns': query_patterns,
                'timestamp': datetime.now().isoformat()
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    def clear_db_monitor(self):
        """Route pour vider les statistiques de monitoring"""
        try:
            from services.db_monitoring_service import db_monitor
            db_monitor.clear_stats()

            return jsonify({
                'success': True,
                'message': 'Statistiques de monitoring vidées'
            })

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500