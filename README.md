# 📅 Emploi du Temps ISA

Application Flask moderne pour la gestion des emplois du temps et l'attribution de salles.

## 🏗️ Architecture

- **Clean Architecture** avec Domain-Driven Design (DDD)
- **Contrôleurs modulaires** : 4 contrôleurs spécialisés (~200 lignes chacun)
- **Logging professionnel** : Logs structurés JSON avec rotation automatique
- **Base de données** : SQLite avec indexes optimisés
- **API REST** : Endpoints pour CRUD complet

## 🚀 Démarrage rapide

```bash
# Installation
pip install -r requirements_updated.txt

# Lancement développement
python app.py

# Production avec Gunicorn
gunicorn -c gunicorn.conf.py app:app
```

## 📁 Structure du projet

```
├── app.py                   # Point d'entrée principal
├── controllers/             # Contrôleurs modulaires
│   ├── course_controller.py
│   ├── professor_controller.py
│   ├── room_controller.py
│   └── planning_controller.py
├── core/                    # Logique métier
├── domain/                  # Entités DDD
├── application/             # Services applicatifs
├── infrastructure/          # Infrastructure (DB, cache)
├── services/               # Services métier legacy
├── utils/                  # Utilitaires (logging)
├── tests/                  # Tests unitaires (53 tests)
├── scripts/                # Scripts de migration/test
└── tools/                  # Outils de monitoring
```

## 🔧 Fonctionnalités

### 📊 Gestion des cours
- Création/modification des cours personnalisés (TP)
- Attribution automatique des salles
- Détection des conflits
- Import/export Excel

### 👨‍🏫 Gestion des professeurs
- Édition des emplois du temps
- Assignation des couleurs
- Vue par professeur

### 🏢 Gestion des salles
- Attribution intelligente
- Cache des salles occupées
- API batch pour performance

### 📱 Interface moderne
- SPA (Single Page Application)
- Planning interactif
- Export PDF
- Mode kiosque

## 📈 Monitoring et logs

- **Logs structurés** : JSON avec contexte (course_id, professor, room_id)
- **Performance tracking** : Monitoring des requêtes DB
- **Rotation automatique** : 10MB par fichier, 5 backups
- **Logs spécialisés** : Room conflicts, DB operations, performance

```bash
# Voir les logs
tail -f logs/application.log
```

## 🧪 Tests

```bash
# Lancer tous les tests
pytest tests/ -v

# Tests avec couverture
pytest --cov=. tests/
```

## 🔐 Sécurité

- **Dépendances à jour** : Flask 3.1.0, Werkzeug 3.1.3
- **Vulnérabilités corrigées** : Mise à jour sécurisée septembre 2024
- **Configuration sécurisée** : Headers de sécurité Gunicorn

## 📊 Performance

- **Architecture optimisée** : De 1563 lignes monolithe → 4×200 lignes modulaires
- **Cache intelligent** : Salles occupées, planning
- **DB optimisée** : Indexes composites pour queries complexes
- **Logs de performance** : Tracking automatique des opérations lentes

## 🤝 Contribution

1. Fork du projet
2. Branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Pull Request

## 📝 Changelog

### v2.0.0 - 2024-09-14
- ✅ Refactoring complet vers architecture par contrôleurs
- ✅ Système de logging professionnel
- ✅ Mise à jour sécurité des dépendances
- ✅ 53 tests unitaires - Clean Architecture

### v1.0.0 - 2024-08
- 🎯 Version monolithique initiale
- 📊 Gestion de base des emplois du temps

---

**Développé avec ❤️ et [Claude Code](https://claude.ai/code)**
