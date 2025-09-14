from flask import render_template, request, redirect, url_for
from controllers.base_controller import BaseController
from services.professor_api_service import ProfessorAPIService
from services.professor_service import ProfessorService
from excel_parser import ExcelScheduleParser


class ProfessorController(BaseController):
    """Contrôleur pour la gestion des professeurs"""

    def __init__(self, schedule_manager):
        self.schedule_manager = schedule_manager
        self.professor_api_service = ProfessorAPIService(schedule_manager)
        super().__init__('professors', url_prefix='/professors')

    def _register_routes(self):
        """Enregistrement des routes pour les professeurs"""
        self.blueprint.route('')(self.list_professors_overview)
        self.blueprint.route('/<path:prof_name>')(self.professor_schedule)
        self.blueprint.route('/edit/<path:prof_name>')(self.edit_schedule)
        self.blueprint.route('/id/<prof_id>')(self.professor_by_id)

        # API routes
        self.blueprint.route('/api/add', methods=['POST'])(self.add_professor)
        self.blueprint.route('/api/update_color', methods=['POST'])(self.update_prof_color)
        self.blueprint.route('/api/delete', methods=['POST'])(self.delete_professor)
        self.blueprint.route('/api/save_schedule/<path:prof_name>', methods=['POST'])(self.save_prof_schedule)

    def list_professors_overview(self):
        """Page de vue d'ensemble des emplois du temps des professeurs"""
        self.schedule_manager.reload_data()
        summary = self.schedule_manager.get_canonical_schedules_summary()

        prof_name_mapping = ProfessorService.get_professor_name_mapping(
            self.schedule_manager.canonical_schedules
        )
        prof_id_mapping = ProfessorService.load_professor_id_mapping()

        PROF_COLORS = ["#e57373", "#81c784", "#64b5f6", "#fff176", "#ffb74d",
                       "#ba68c8", "#4db6ac", "#f06292", "#a1887f"]

        return render_template(
            'prof_schedules_overview.html',
            summary=summary,
            prof_colors=PROF_COLORS,
            prof_name_mapping=prof_name_mapping,
            prof_id_mapping=prof_id_mapping
        )

    def professor_schedule(self, prof_name):
        """Vue individuelle de l'emploi du temps d'un professeur"""
        self.schedule_manager.force_sync_data()

        data = self.schedule_manager.professor_view_service.generate_professor_schedule_data(prof_name)

        return render_template('professor_schedule.html', **data)

    def edit_schedule(self, prof_name):
        """Page d'édition de l'emploi du temps pour un professeur"""
        self.schedule_manager.reload_data()

        # Trouver le nom exact du professeur
        available_profs = list(self.schedule_manager.canonical_schedules.keys())
        exact_prof_name = ProfessorService.find_exact_professor_name(prof_name, available_profs)

        if not exact_prof_name:
            return (f"Professeur '{prof_name}' non trouvé. "
                   f"Professeurs disponibles: {', '.join(available_profs[:5])}...", 404)

        courses = self.schedule_manager.get_prof_schedule(exact_prof_name)
        sorted_courses = ProfessorService.sort_courses_by_day_and_time(courses)

        return render_template(
            'edit_schedule.html',
            prof_name=exact_prof_name,
            courses=sorted_courses
        )

    def professor_by_id(self, prof_id):
        """Redirects to professor schedule using ID"""
        prof_id_mapping = ProfessorService.load_professor_id_mapping()

        if not prof_id_mapping:
            return render_template('error.html', error="ID mapping not found"), 404

        prof_name = ProfessorService.find_professor_by_id(prof_id, prof_id_mapping)

        if not prof_name:
            return render_template('error.html',
                                 error=f"Professor ID {prof_id} not found"), 404

        return self.professor_schedule(prof_name)

    def add_professor(self):
        """API pour ajouter un nouveau professeur"""
        data = self.get_json_data()
        result = self.professor_api_service.add_professor(data)

        if 'status_code' in result:
            status_code = result.pop('status_code')
            return result, status_code
        return result

    def update_prof_color(self):
        """API pour mettre à jour la couleur d'un professeur"""
        data = self.get_json_data()
        result = self.professor_api_service.update_prof_color(data)

        if 'status_code' in result:
            status_code = result.pop('status_code')
            return result, status_code
        return result

    def delete_professor(self):
        """API pour supprimer un professeur"""
        data = self.get_json_data()
        result = self.professor_api_service.delete_professor(data)

        if 'status_code' in result:
            status_code = result.pop('status_code')
            return result, status_code
        return result

    def save_prof_schedule(self, prof_name):
        """API pour sauvegarder le nouvel emploi du temps d'un professeur"""
        try:
            new_courses = self.get_json_data()
            if not isinstance(new_courses, list):
                return self.error_response('Format de données invalide')

            # Recalculer les durées avant de sauvegarder
            parser = ExcelScheduleParser()
            for course in new_courses:
                time_info = parser.parse_time_range(course.get('raw_time_slot', ''))
                if time_info:
                    course['start_time'], course['end_time'], course['duration_hours'] = time_info
                else:
                    course['start_time'], course['end_time'], course['duration_hours'] = "00:00", "00:00", 0

            success = self.schedule_manager.update_prof_schedule(prof_name, new_courses)

            if success:
                self.schedule_manager.force_sync_data()
                return self.success_response(message='Emploi du temps mis à jour')
            else:
                return self.error_response('Impossible de sauvegarder', 404)

        except Exception as e:
            return self.error_response(str(e), 500)