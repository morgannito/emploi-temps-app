#!/usr/bin/env python3

import json
import os
import sys
from flask import Flask

# Test simple du parsing JSON
def test_format_detection():
    print("🔍 Test détection format JSON...")

    # Format extracted_schedules
    extracted_path = "data/extracted_schedules.json"
    if os.path.exists(extracted_path):
        with open(extracted_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        sample_key = next(iter(data.keys()))
        sample_value = data[sample_key]

        print(f"📁 Fichier: {extracted_path}")
        print(f"🔑 Sample key: {sample_key}")
        print(f"📋 Sample value type: {type(sample_value)}")

        if isinstance(sample_value, dict):
            print(f"🔍 Keys in sample: {list(sample_value.keys())}")
            if any(isinstance(v, list) for v in sample_value.values()):
                print("✅ Format détecté: extracted_schedules (semaine/jour)")

                # Compter cours
                total_courses = 0
                for week_name, days_data in data.items():
                    for day_name, courses_list in days_data.items():
                        total_courses += len(courses_list)
                        if total_courses <= 5:  # Montrer quelques exemples
                            print(f"   📅 {week_name}/{day_name}: {len(courses_list)} cours")

                print(f"📊 Total cours trouvés: {total_courses}")
            else:
                print("❓ Format non reconnu")
    else:
        print(f"❌ Fichier non trouvé: {extracted_path}")

    # Autres fichiers
    other_files = [
        "data/professors_canonical_schedule.json",
        "data/canonical_schedules.json"
    ]

    for file_path in other_files:
        if os.path.exists(file_path):
            print(f"\n📁 Fichier trouvé: {file_path}")
        else:
            print(f"❌ Fichier absent: {file_path}")

if __name__ == "__main__":
    test_format_detection()