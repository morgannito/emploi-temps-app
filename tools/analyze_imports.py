#!/usr/bin/env python3
"""
Analyseur d'imports et de dépendances circulaires
"""

import ast
import os
from collections import defaultdict, deque
from pathlib import Path

class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.imports = []
        self.from_imports = []

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.from_imports.append(f"{node.module}.{alias.name}")

def analyze_file(file_path):
    """Analyse les imports d'un fichier Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        analyzer = ImportAnalyzer()
        analyzer.visit(tree)

        return {
            'imports': analyzer.imports,
            'from_imports': analyzer.from_imports
        }
    except Exception as e:
        return {'imports': [], 'from_imports': [], 'error': str(e)}

def find_circular_dependencies(project_path):
    """Détecte les dépendances circulaires"""
    dependencies = defaultdict(set)

    # Scan tous les fichiers Python
    for py_file in Path(project_path).rglob('*.py'):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue

        file_info = analyze_file(py_file)
        module_name = str(py_file.relative_to(project_path)).replace('/', '.').replace('.py', '')

        # Analyser les imports locaux
        for imp in file_info['from_imports']:
            if imp.startswith(('.', 'controllers', 'services', 'utils', 'models')):
                clean_imp = imp.split('.')[0] if '.' in imp else imp
                dependencies[module_name].add(clean_imp)

    # Détection des cycles
    cycles = []
    for module in dependencies:
        visited = set()
        path = []

        def dfs(node, path, visited):
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return True

            if node in visited:
                return False

            visited.add(node)
            path.append(node)

            for neighbor in dependencies.get(node, []):
                if dfs(neighbor, path, visited):
                    return True

            path.pop()
            return False

        dfs(module, path, visited)

    return cycles

def analyze_unused_imports(project_path):
    """Analyse les imports non utilisés"""
    unused_imports = {}

    for py_file in Path(project_path).rglob('*.py'):
        if 'venv' in str(py_file) or '__pycache__' in str(py_file):
            continue

        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)
            analyzer = ImportAnalyzer()
            analyzer.visit(tree)

            # Vérifier l'utilisation des imports
            potentially_unused = []
            for imp in analyzer.imports:
                module_name = imp.split('.')[0]
                if module_name not in content.replace(f'import {imp}', ''):
                    potentially_unused.append(imp)

            if potentially_unused:
                unused_imports[str(py_file)] = potentially_unused

        except Exception as e:
            continue

    return unused_imports

if __name__ == "__main__":
    project_path = Path(".")

    print("🔍 Analyse des dépendances...")

    # Analyser les cycles
    cycles = find_circular_dependencies(project_path)
    if cycles:
        print(f"\n⚠️  {len(cycles)} dépendances circulaires détectées:")
        for cycle in cycles:
            print(f"   {' -> '.join(cycle)}")
    else:
        print("\n✅ Aucune dépendance circulaire détectée")

    # Analyser les imports non utilisés
    unused = analyze_unused_imports(project_path)
    if unused:
        print(f"\n📦 {len(unused)} fichiers avec imports potentiellement non utilisés:")
        for file, imports in unused.items():
            print(f"   {file}: {', '.join(imports)}")
    else:
        print("\n✅ Tous les imports semblent utilisés")

    print("\n📊 Recommandations:")
    print("   - Réorganiser les imports circulaires")
    print("   - Supprimer les imports inutiles")
    print("   - Utiliser des imports lazy si nécessaire")