import io
from datetime import date, timedelta, datetime
from typing import List, Dict
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm, inch


class PDFExportService:
    """Service pour l'export PDF des plannings"""

    @staticmethod
    def get_day_date(day: str, week_name: str) -> str:
        """Calcule la date d'un jour pour une semaine donnée"""
        import re
        match = re.search(r'Semaine (\d+)', week_name)
        if not match or day not in ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']:
            return ''

        week_num = int(match.group(1))
        base_date = date(2025, 9, 1) if week_num >= 36 else date(2026, 1, 5)
        weeks_offset = week_num - 36 if week_num >= 36 else week_num - 1
        monday_date = base_date + timedelta(weeks=weeks_offset)

        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
        day_index = days.index(day)
        day_date = monday_date + timedelta(days=day_index)
        return day_date.strftime('%d/%m')

    @staticmethod
    def export_week_pdf(schedule_manager, week_name: str) -> io.BytesIO:
        """Exporte la semaine en PDF avec une page par professeur"""
        # Forcer la synchronisation des données
        schedule_manager.force_sync_data()

        # Récupérer tous les cours pour la semaine
        all_courses = schedule_manager.get_all_courses()
        week_courses = [c for c in all_courses if c.week_name == week_name]

        # Grouper par professeur
        prof_courses = {}
        for course in week_courses:
            prof = course.professor
            if prof not in prof_courses:
                prof_courses[prof] = []
            prof_courses[prof].append(course)

        # Créer le PDF en mémoire
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Centré
        )

        prof_title_style = ParagraphStyle(
            'ProfTitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            textColor=colors.darkblue
        )

        # Titre principal
        story.append(Paragraph(f"Emploi du temps - {week_name}", title_style))

        # Date de génération
        generation_date = datetime.now().strftime("%d/%m/%Y à %H:%M")
        date_style = ParagraphStyle(
            'DateStyle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=1,
            textColor=colors.grey
        )
        story.append(Paragraph(f"Généré le {generation_date}", date_style))
        story.append(Spacer(1, 20))

        # Résumé du nombre de cours par professeur
        summary_style = ParagraphStyle(
            'SummaryStyle',
            parent=styles['Normal'],
            fontSize=11,
            alignment=0,
            spaceAfter=20
        )
        story.append(Paragraph(f"Nombre de professeurs : {len(prof_courses)}", summary_style))
        story.append(Paragraph(f"Nombre total de cours : {len(week_courses)}", summary_style))
        story.append(Spacer(1, 20))

        # Fonction pour nettoyer le nom du professeur pour le tri
        def clean_prof_name(name):
            """Supprime les préfixes Mme et M pour le tri alphabétique"""
            name = name.strip()
            if name.startswith('Mme '):
                return name[4:]  # Supprime "Mme "
            elif name.startswith('M '):
                return name[2:]   # Supprime "M "
            return name

        # Trier les professeurs par ordre alphabétique (en ignorant Mme/M)
        sorted_professors = sorted(prof_courses.keys(), key=clean_prof_name)

        # Pour chaque professeur (trié)
        for prof_name in sorted_professors:
            courses = prof_courses[prof_name]
            # Titre du professeur
            story.append(Paragraph(f"Professeur : {prof_name}", prof_title_style))

            # Trier les cours par jour et heure
            days_order = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']
            sorted_courses = sorted(courses, key=lambda x: (days_order.index(x.day) if x.day in days_order else 999, x.start_time))

            # Créer le tableau des cours
            if sorted_courses:
                # En-têtes du tableau
                data = [['Jour', 'Horaire', 'Salle']]

                for course in sorted_courses:
                    # Obtenir le nom de la salle
                    room_name = "Non assignée"
                    if course.assigned_room:
                        room_name = schedule_manager.get_room_name(course.assigned_room)

                    # Formater l'horaire
                    time_slot = f"{course.start_time} - {course.end_time}"

                    # N'afficher que Jour, Horaire, Salle
                    data.append([
                        f"{course.day} ({PDFExportService.get_day_date(course.day, week_name)})",
                        time_slot,
                        room_name
                    ])

                # Créer le tableau (3 colonnes)
                table = Table(data, colWidths=[1.5*inch, 1.8*inch, 2.2*inch])

                # Style du tableau
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))

                story.append(table)
                story.append(Spacer(1, 30))

            # Saut de page pour le prochain professeur (sauf le dernier)
            if sorted_professors.index(prof_name) < len(sorted_professors) - 1:
                story.append(PageBreak())

        # Générer le PDF
        doc.build(story)
        buffer.seek(0)

        return buffer

    @staticmethod
    def export_day_pdf(schedule_manager, week_name: str, day_name: str) -> io.BytesIO:
        """Exporte les cours d'une journée en PDF sur une seule page"""
        # Récupérer tous les cours pour la journée
        all_courses = schedule_manager.get_all_courses()
        day_courses = [c for c in all_courses if c.week_name == week_name and c.day == day_name and c.assigned_room]

        # Trier par heure de début
        day_courses.sort(key=lambda x: x.start_time)

        # Séparer les cours du matin et de l'après-midi
        morning_courses = [c for c in day_courses if int(c.start_time.split(':')[0]) < 12]
        afternoon_courses = [c for c in day_courses if int(c.start_time.split(':')[0]) >= 12]

        # Créer le PDF en mémoire
        buffer = io.BytesIO()
        # Marges très petites
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20, bottomMargin=20, leftMargin=20, rightMargin=20)
        story = []

        # Styles
        styles = getSampleStyleSheet()

        # Style pour le titre principal (journée)
        day_title_style = ParagraphStyle(
            'DayTitle',
            parent=styles['h1'],
            fontSize=16,
            spaceAfter=20,
            alignment=1 # Centré
        )
        story.append(Paragraph(f"{day_name} - {week_name}", day_title_style))

        # Style pour les titres de période
        period_title_style = ParagraphStyle(
            'PeriodTitle',
            parent=styles['h2'],
            fontSize=14,
            spaceAfter=15,
            alignment=1 # Centré
        )

        def create_course_table(courses):
            """Crée un objet Table pour une liste de cours."""
            if not courses:
                return None

            data = [['Heure', 'Professeur', 'Salle']]
            for course in courses:
                room_name = schedule_manager.get_room_name(course.assigned_room) if course.assigned_room else "N/A"
                data.append([
                    f"{course.start_time} - {course.end_time}",
                    course.professor,
                    room_name
                ])

            table = Table(data, colWidths=[150, 220, 150])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, '#f0f0f0']),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            return table

        # Ajouter la table du matin
        if morning_courses:
            story.append(Paragraph("Matinée", period_title_style))
            morning_table = create_course_table(morning_courses)
            story.append(morning_table)

        # Ajouter un saut de page si les deux périodes ont des cours
        if morning_courses and afternoon_courses:
            story.append(PageBreak())

        # Ajouter la table de l'après-midi
        if afternoon_courses:
            story.append(Paragraph("Après-midi", period_title_style))
            afternoon_table = create_course_table(afternoon_courses)
            story.append(afternoon_table)

        if not morning_courses and not afternoon_courses:
            story.append(Paragraph("Aucun cours programmé pour cette journée.", period_title_style))

        # Construire le PDF
        doc.build(story)

        # Préparer la réponse
        buffer.seek(0)

        return buffer