# Legacy Backup - Architecture Monolithique

Ce dossier contient les fichiers de l'ancienne architecture monolithique avant refactoring.

## Fichiers archivés

- `app_new_old.py` - Version monolithique originale (1563 lignes)
- `app_new_legacy_backup.py` - Backup de sécurité identique
- `fix_templates.py` - Script de migration utilisé lors du refactoring

## Architecture remplacée

L'ancienne architecture monolithique a été remplacée le 2025-09-14 par une architecture modulaire basée sur des contrôleurs spécialisés.

### Problèmes résolus

- ❌ Monolithe de 1563 lignes difficile à maintenir
- ❌ Responsabilités mélangées dans un seul fichier
- ❌ Tests unitaires complexes à cause du couplage
- ❌ Ajout de fonctionnalités difficile

### Nouvelle architecture

- ✅ 4 contrôleurs spécialisés (~200 lignes chacun)
- ✅ Séparation des responsabilités par domaine métier
- ✅ Code modulaire et testable
- ✅ Évolutivité et maintenabilité améliorées

## Restauration (si nécessaire)

En cas de problème avec la nouvelle architecture :

```bash
# Restaurer l'ancienne version
cp legacy_backup/app_new_old.py app_new.py

# Redémarrer le serveur
python app_new.py
```

⚠️ **Ne pas supprimer** ces fichiers avant validation complète en production.