#!/usr/bin/env python3
"""
Test SPA route simple pour débugger
"""

from flask import Flask, render_template, jsonify
import time
import os
from services.database_service import DatabaseService
from models import db

app = Flask(__name__)

# Configuration SQLAlchemy
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'schedule.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialiser SQLAlchemy avec l'app
db.init_app(app)

# Initialiser les services
try:
    with app.app_context():
        database_service = DatabaseService()
        print("✅ Database service initialized successfully")
except Exception as e:
    print(f"❌ Erreur initialisation DB: {e}")
    database_service = None

@app.route('/')
def home():
    return "Home page - Server OK"

@app.route('/spa')
def spa_test():
    """Route de test pour SPA"""
    return render_template('spa_planning.html')

@app.route('/test')
def test_route():
    return "Test route - OK"

@app.route('/api/week_data/<week_name>')
def api_week_data(week_name):
    """API JSON optimisée pour le SPA - version de test"""
    if not database_service:
        return jsonify({"error": "Database not available", "courses": []})

    try:
        start_time = time.time()
        courses = database_service.get_courses_by_week(week_name)

        formatted_courses = []
        time_slot_mapping = {
            '08:00': '8h00-9h00', '09:00': '9h00-10h00', '10:00': '10h00-11h00',
            '11:00': '11h00-12h00', '12:00': '12h00-13h00', '13:00': '13h00-14h00',
            '14:00': '14h00-15h00', '15:00': '15h00-16h00', '16:00': '16h00-17h00',
            '17:00': '17h00-18h00'
        }

        for course in courses:
            time_slot = time_slot_mapping.get(course.start_time, f"{course.start_time}-{course.end_time}")
            formatted_courses.append({
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
            })

        elapsed = (time.time() - start_time) * 1000
        print(f"🚀 API week_data {week_name}: {elapsed:.2f}ms, {len(formatted_courses)} courses")

        return jsonify({
            "courses": formatted_courses,
            "week_name": week_name,
            "load_time_ms": round(elapsed, 2),
            "total_courses": len(formatted_courses)
        })

    except Exception as e:
        print(f"❌ Erreur API week_data: {e}")
        return jsonify({"error": str(e), "courses": []})

if __name__ == '__main__':
    print("🚀 Démarrage serveur de test SPA...")
    app.run(debug=True, host='0.0.0.0', port=5007)