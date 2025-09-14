#!/usr/bin/env python3
"""
Tests pour PrestaShop Inspector
"""

import pytest
import tempfile
import os
from pathlib import Path
from prestashop_inspector import PrestaShopInspector


def test_inspector_initialization():
    """Test initialisation inspector"""
    with tempfile.TemporaryDirectory() as tmpdir:
        inspector = PrestaShopInspector(tmpdir)
        assert inspector.root == Path(tmpdir)
        assert len(inspector.issues['critical']) == 0


def test_php_log_analysis_missing_file():
    """Test analyse logs PHP avec fichier manquant"""
    inspector = PrestaShopInspector("/tmp/test")
    result = inspector.analyze_php_logs("/nonexistent/log.log")
    assert result['total_errors'] == 0
    assert any('Log file not found' in issue for issue in inspector.issues['medium'])


def test_prestashop_logs_missing_dir():
    """Test logs PrestaShop avec répertoire manquant"""
    with tempfile.TemporaryDirectory() as tmpdir:
        inspector = PrestaShopInspector(tmpdir)
        inspector.analyze_prestashop_logs()
        assert any('logs directory missing' in issue for issue in inspector.issues['high'])


def test_cache_analysis():
    """Test analyse cache"""
    with tempfile.TemporaryDirectory() as tmpdir:
        inspector = PrestaShopInspector(tmpdir)

        # Créer structure cache
        cache_dir = Path(tmpdir) / "var/cache"
        cache_dir.mkdir(parents=True)

        # Créer fichier test
        test_file = cache_dir / "test.cache"
        test_file.write_text("test content")

        inspector.analyze_cache_status()
        # Ne devrait pas avoir d'erreurs pour un petit cache
        assert len([issue for issue in inspector.issues['medium'] if 'cache size' in issue]) == 0


def test_modules_check():
    """Test vérification modules"""
    with tempfile.TemporaryDirectory() as tmpdir:
        inspector = PrestaShopInspector(tmpdir)

        # Créer structure modules
        modules_dir = Path(tmpdir) / "modules"
        modules_dir.mkdir(parents=True)

        # Module valide
        valid_module = modules_dir / "testmodule"
        valid_module.mkdir()
        (valid_module / "testmodule.php").write_text("<?php // Valid module")

        # Module invalide
        invalid_module = modules_dir / "invalidmodule"
        invalid_module.mkdir()
        # Pas de fichier principal

        inspector.check_modules_status()
        assert any('missing main file: invalidmodule' in issue for issue in inspector.issues['medium'])


def test_permissions_check():
    """Test vérification permissions"""
    with tempfile.TemporaryDirectory() as tmpdir:
        inspector = PrestaShopInspector(tmpdir)

        # Créer quelques répertoires
        cache_dir = Path(tmpdir) / "var/cache"
        cache_dir.mkdir(parents=True)

        inspector.check_file_permissions()
        # Devrait détecter les paths manquants
        missing_paths = [issue for issue in inspector.issues['medium'] if 'Missing critical path' in issue]
        assert len(missing_paths) > 0


def test_report_generation():
    """Test génération rapport"""
    with tempfile.TemporaryDirectory() as tmpdir:
        inspector = PrestaShopInspector(tmpdir)

        # Ajouter quelques issues
        inspector.issues['critical'].append("Test critical issue")
        inspector.issues['high'].append("Test high issue")

        report = inspector.generate_report()

        assert "PRESTASHOP BACK-OFFICE INSPECTION REPORT" in report
        assert "CRITICAL ISSUES (1)" in report
        assert "HIGH ISSUES (1)" in report
        assert "Test critical issue" in report
        assert "IMMEDIATE ACTION REQUIRED" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])