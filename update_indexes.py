#!/usr/bin/env python3
"""
Script pour mettre à jour les index SQLite
"""

from app_new import app
from models import db


def update_indexes():
    """Met à jour les index pour optimiser get_occupied_rooms"""
    with app.app_context():
        print("🔧 Mise à jour des index SQLite pour optimisation...")

        # Drop et recreate les tables pour appliquer les nouveaux index
        db.drop_all()
        db.create_all()

        print("✅ Nouveaux index créés")
        print("⚠️  Les données doivent être re-migrées avec full_migration.py")


if __name__ == "__main__":
    update_indexes()