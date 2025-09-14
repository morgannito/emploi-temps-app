#!/usr/bin/env python3
"""
PrestaShop Back-Office Inspector
Analyse complète des logs, DB, et configuration PrestaShop
"""

import os
import re
import json
import csv
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any


class PrestaShopInspector:
    def __init__(self, prestashop_root: str):
        self.root = Path(prestashop_root)
        self.logs_dir = self.root / "var/logs"
        self.cache_dir = self.root / "var/cache"
        self.config_dir = self.root / "config"
        self.modules_dir = self.root / "modules"

        self.issues = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

    def analyze_php_logs(self, log_path: str = "/var/log/plesk-php82-fpm/error.log"):
        """Analyse logs PHP pour erreurs PrestaShop récentes (24h)"""
        print("🔍 Analyse des logs PHP...")

        try:
            cutoff = datetime.now() - timedelta(hours=24)
            errors = defaultdict(int)
            fatal_errors = []

            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    # Parse log PHP format
                    match = re.search(r'\[(.*?)\] PHP (Fatal error|Warning|Notice|Parse error): (.*?) in (.*?) on line (\d+)', line)
                    if match:
                        timestamp_str, level, message, file, line_num = match.groups()

                        # Filter PrestaShop related
                        if 'prestashop' in file.lower() or 'httpdocs' in file.lower():
                            error_key = f"{level}:{file}:{line_num}"
                            errors[error_key] += 1

                            if level == "Fatal error":
                                fatal_errors.append({
                                    'timestamp': timestamp_str,
                                    'level': level,
                                    'message': message,
                                    'file': file,
                                    'line': line_num,
                                    'count': errors[error_key]
                                })

            # Classement par priorité
            for error_key, count in errors.items():
                level, file, line = error_key.split(':', 2)

                if level == "Fatal error":
                    self.issues['critical'].append(f"Fatal PHP Error (x{count}): {file}:{line}")
                elif level == "Parse error":
                    self.issues['high'].append(f"Parse Error (x{count}): {file}:{line}")
                elif count > 10:  # Erreurs répétitives
                    self.issues['medium'].append(f"Repeated {level} (x{count}): {file}:{line}")

            return {'total_errors': len(errors), 'fatal_count': len(fatal_errors)}

        except FileNotFoundError:
            self.issues['medium'].append(f"Log file not found: {log_path}")
            return {'total_errors': 0, 'fatal_count': 0}

    def analyze_prestashop_logs(self):
        """Analyse logs spécifiques PrestaShop"""
        print("🔍 Analyse des logs PrestaShop...")

        if not self.logs_dir.exists():
            self.issues['high'].append("PrestaShop logs directory missing")
            return

        log_files = list(self.logs_dir.glob("*.log"))

        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                    # Recherche patterns d'erreur
                    if 'CRITICAL' in content:
                        critical_count = content.count('CRITICAL')
                        self.issues['critical'].append(f"Critical errors in {log_file.name}: {critical_count}")

                    if 'ERROR' in content:
                        error_count = content.count('ERROR')
                        if error_count > 5:
                            self.issues['high'].append(f"Multiple errors in {log_file.name}: {error_count}")

                    # Erreurs DB courantes
                    if 'MySQL server has gone away' in content:
                        self.issues['high'].append(f"DB Connection issues in {log_file.name}")

                    if 'Memory limit exceeded' in content:
                        self.issues['medium'].append(f"Memory issues in {log_file.name}")

            except Exception as e:
                self.issues['low'].append(f"Cannot read log {log_file.name}: {str(e)}")

    def check_file_permissions(self):
        """Vérification permissions critiques"""
        print("🔍 Vérification des permissions...")

        critical_paths = [
            "var/cache",
            "var/logs",
            "img",
            "upload",
            "download",
            "config/settings.inc.php"
        ]

        for path in critical_paths:
            full_path = self.root / path
            if full_path.exists():
                stat = full_path.stat()
                # Check si writable (owner write bit)
                if not (stat.st_mode & 0o200):
                    self.issues['high'].append(f"Non-writable critical path: {path}")
            else:
                self.issues['medium'].append(f"Missing critical path: {path}")

    def analyze_cache_status(self):
        """Analyse état du cache"""
        print("🔍 Analyse du cache...")

        if not self.cache_dir.exists():
            self.issues['medium'].append("Cache directory missing")
            return

        # Taille cache
        cache_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
        cache_size_mb = cache_size / (1024 * 1024)

        if cache_size_mb > 500:  # > 500MB
            self.issues['medium'].append(f"Large cache size: {cache_size_mb:.1f}MB")

        # Templates compilés
        smarty_dir = self.cache_dir / "smarty"
        if smarty_dir.exists():
            compiled_count = len(list(smarty_dir.rglob("*.php")))
            if compiled_count > 1000:
                self.issues['low'].append(f"Many compiled templates: {compiled_count}")

    def check_modules_status(self):
        """Vérification des modules"""
        print("🔍 Analyse des modules...")

        if not self.modules_dir.exists():
            self.issues['high'].append("Modules directory missing")
            return

        modules = [d for d in self.modules_dir.iterdir() if d.is_dir()]

        for module_dir in modules:
            # Check module config
            config_file = module_dir / f"{module_dir.name}.php"
            if not config_file.exists():
                self.issues['medium'].append(f"Module missing main file: {module_dir.name}")

            # Check for common problematic modules
            problematic = ['autoupgrade', 'ps_checkout', 'ps_facebook']
            if module_dir.name in problematic:
                self.issues['low'].append(f"Potentially problematic module present: {module_dir.name}")

    def check_configuration(self):
        """Vérification configuration système"""
        print("🔍 Vérification de la configuration...")

        settings_file = self.config_dir / "settings.inc.php"
        if not settings_file.exists():
            self.issues['critical'].append("Main config file missing: settings.inc.php")
            return

        try:
            with open(settings_file, 'r') as f:
                content = f.read()

                # Debug mode activé en production
                if "_PS_MODE_DEV_', true" in content:
                    self.issues['high'].append("Debug mode enabled in production")

                # Cache désactivé
                if "_PS_CACHE_ENABLED_', false" in content:
                    self.issues['medium'].append("Cache disabled - performance impact")

                # Configuration DB
                if "localhost" not in content and "127.0.0.1" not in content:
                    # DB externe - vérifier si accessible
                    self.issues['low'].append("External database detected")

        except Exception as e:
            self.issues['medium'].append(f"Cannot read config file: {str(e)}")

    def run_database_checks(self, db_config: dict):
        """Vérifications base de données"""
        print("🔍 Vérification base de données...")

        try:
            import pymysql

            conn = pymysql.connect(
                host=db_config.get('host', 'localhost'),
                user=db_config['user'],
                password=db_config['password'],
                database=db_config['database'],
                charset='utf8mb4'
            )

            cursor = conn.cursor()

            # Tables principales
            main_tables = ['ps_product', 'ps_orders', 'ps_customer', 'ps_cart', 'ps_order_detail']
            for table in main_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                if count == 0:
                    self.issues['medium'].append(f"Empty main table: {table}")

            # Intégrité référentielle
            cursor.execute("""
                SELECT COUNT(*) FROM ps_order_detail od
                LEFT JOIN ps_orders o ON od.id_order = o.id_order
                WHERE o.id_order IS NULL
            """)
            orphaned_details = cursor.fetchone()[0]
            if orphaned_details > 0:
                self.issues['medium'].append(f"Orphaned order details: {orphaned_details}")

            # Tables corrompues
            cursor.execute("CHECK TABLE ps_product, ps_orders, ps_customer")
            results = cursor.fetchall()
            for result in results:
                if result[3] != 'OK':
                    self.issues['high'].append(f"Corrupted table: {result[0]} - {result[3]}")

            conn.close()

        except ImportError:
            self.issues['low'].append("pymysql not available - skipping DB checks")
        except Exception as e:
            self.issues['medium'].append(f"Database check failed: {str(e)}")

    def performance_analysis(self):
        """Analyse performance"""
        print("🔍 Analyse des performances...")

        # Tailles importantes
        critical_dirs = ['img', 'upload', 'var']
        for dirname in critical_dirs:
            dir_path = self.root / dirname
            if dir_path.exists():
                size = sum(f.stat().st_size for f in dir_path.rglob('*') if f.is_file())
                size_mb = size / (1024 * 1024)

                if size_mb > 1000:  # > 1GB
                    self.issues['medium'].append(f"Large directory {dirname}: {size_mb:.1f}MB")

    def generate_report(self) -> str:
        """Génère le rapport final"""
        report = []
        report.append("# PRESTASHOP BACK-OFFICE INSPECTION REPORT")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        total_issues = sum(len(issues) for issues in self.issues.values())
        report.append(f"## SUMMARY: {total_issues} issues found")
        report.append("")

        for level, issues in self.issues.items():
            if issues:
                report.append(f"### {level.upper()} ISSUES ({len(issues)})")
                for issue in issues:
                    report.append(f"- {issue}")
                report.append("")

        # Recommandations
        report.append("## RECOMMENDATIONS")

        if self.issues['critical']:
            report.append("🚨 **IMMEDIATE ACTION REQUIRED**")
            report.append("- Fix critical issues immediately")
            report.append("- Check site functionality")

        if self.issues['high']:
            report.append("⚠️ **HIGH PRIORITY**")
            report.append("- Schedule maintenance window")
            report.append("- Backup before fixes")

        report.append("")
        report.append("## NEXT STEPS")
        report.append("1. Fix critical/high issues first")
        report.append("2. Test in staging environment")
        report.append("3. Monitor logs after fixes")
        report.append("4. Schedule regular health checks")

        return "\n".join(report)

    def run_full_inspection(self, db_config: dict = None):
        """Lance inspection complète"""
        print("🚀 Starting PrestaShop inspection...")

        self.analyze_php_logs()
        self.analyze_prestashop_logs()
        self.check_file_permissions()
        self.analyze_cache_status()
        self.check_modules_status()
        self.check_configuration()
        self.performance_analysis()

        if db_config:
            self.run_database_checks(db_config)

        return self.generate_report()


def main():
    """Point d'entrée principal"""

    # Configuration pour heleneriu.fr
    prestashop_root = "/var/www/vhosts/heleneriu.fr/httpdocs"
    db_config = {
        'host': 'localhost',
        'user': 'heleneridlbouton',
        'password': 'a70Icc92!',
        'database': 'heleneridlbouton'
    }

    inspector = PrestaShopInspector(prestashop_root)
    report = inspector.run_full_inspection(db_config)

    # Sauvegarde rapport
    output_file = f"prestashop_inspection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ Inspection complete! Report saved: {output_file}")
    print("\n" + "="*50)
    print(report)


if __name__ == "__main__":
    main()