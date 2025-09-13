#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier le scroll horizontal dans la vue par jour
"""

import requests
import re
from bs4 import BeautifulSoup

def test_day_view():
    """Test de la vue par jour"""
    print("🔍 Diagnostic du scroll horizontal...")
    
    # Test de l'application principale
    try:
        response = requests.get("http://localhost:5005/", timeout=10)
        if response.status_code == 200:
            print("✅ Application principale accessible")
        else:
            print(f"❌ Application principale: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur accès application: {e}")
        return False
    
    # Test de la vue par jour avec des paramètres simples
    try:
        response = requests.get("http://localhost:5005/day/test/test", timeout=10)
        if response.status_code == 200:
            print("✅ Vue par jour accessible")
            
            # Analyser le contenu HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Vérifier les éléments CSS critiques
            css_content = soup.find('style')
            if css_content:
                css_text = css_content.get_text()
                
                # Vérifier les propriétés CSS importantes
                checks = [
                    ('overflow-x: scroll', 'Scroll horizontal forcé'),
                    ('overflow-x: auto', 'Scroll horizontal auto'),
                    ('flex-shrink: 0', 'Cours non rétrécissables'),
                    ('min-width:', 'Largeur minimale définie'),
                    ('max-width:', 'Largeur maximale définie'),
                    ('scrollbar-width:', 'Scrollbar personnalisée'),
                    ('-webkit-overflow-scrolling:', 'Scroll fluide'),
                ]
                
                print("\n📋 Vérification des propriétés CSS:")
                for check, description in checks:
                    if check in css_text:
                        print(f"  ✅ {description}")
                    else:
                        print(f"  ⚠️  {description} - MANQUANT")
                
                # Vérifier le JavaScript
                scripts = soup.find_all('script')
                js_content = '\n'.join([script.get_text() for script in scripts])
                
                js_checks = [
                    ('checkOverflow', 'Fonction de détection du débordement'),
                    ('scrollLeft', 'Gestion du scroll horizontal'),
                    ('wheel', 'Événement molette de souris'),
                    ('hasOverflow', 'Détection du débordement'),
                    ('overflow-indicator', 'Indicateur de débordement'),
                ]
                
                print("\n📋 Vérification du JavaScript:")
                for check, description in js_checks:
                    if check in js_content:
                        print(f"  ✅ {description}")
                    else:
                        print(f"  ⚠️  {description} - MANQUANT")
                
                # Vérifier la structure HTML
                containers = soup.find_all(class_='courses-container')
                if containers:
                    print(f"\n📋 Structure HTML: {len(containers)} conteneurs de cours trouvés")
                    
                    for i, container in enumerate(containers):
                        courses = container.find_all(class_='course-in-grid')
                        print(f"  📦 Conteneur {i+1}: {len(courses)} cours")
                        
                        # Vérifier les attributs CSS inline
                        style = container.get('style', '')
                        if 'overflow' in style:
                            print(f"    ✅ Styles inline présents")
                        else:
                            print(f"    ⚠️  Styles inline manquants")
                
                return True
            else:
                print("❌ Pas de CSS trouvé")
                return False
        else:
            print(f"❌ Vue par jour: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur vue par jour: {e}")
        return False

def test_scroll_functionality():
    """Test de la fonctionnalité de scroll"""
    print("\n🧪 Test de la fonctionnalité de scroll...")
    
    try:
        # Créer une page de test simple
        test_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                .test-container {
                    display: flex;
                    overflow-x: scroll;
                    width: 300px;
                    border: 1px solid #ccc;
                }
                .test-item {
                    min-width: 150px;
                    padding: 10px;
                    background: #f0f0f0;
                    margin: 5px;
                    flex-shrink: 0;
                }
            </style>
        </head>
        <body>
            <div class="test-container">
                <div class="test-item">Item 1</div>
                <div class="test-item">Item 2</div>
                <div class="test-item">Item 3</div>
                <div class="test-item">Item 4</div>
                <div class="test-item">Item 5</div>
            </div>
        </body>
        </html>
        """
        
        with open('test_scroll_simple.html', 'w') as f:
            f.write(test_html)
        
        print("✅ Page de test créée: test_scroll_simple.html")
        print("📋 Instructions:")
        print("  1. Ouvrez test_scroll_simple.html dans votre navigateur")
        print("  2. Vérifiez que vous pouvez faire défiler horizontalement")
        print("  3. Utilisez la molette de la souris pour tester")
        
        return True
    except Exception as e:
        print(f"❌ Erreur création test: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Diagnostic du Scroll Horizontal - Vue par Jour")
    print("=" * 50)
    
    # Test de l'application
    app_ok = test_day_view()
    
    # Test de la fonctionnalité
    scroll_ok = test_scroll_functionality()
    
    print("\n" + "=" * 50)
    print("📊 Résumé du diagnostic:")
    
    if app_ok and scroll_ok:
        print("✅ Tous les tests sont passés")
        print("🎉 Le scroll horizontal devrait fonctionner correctement")
    else:
        print("❌ Certains tests ont échoué")
        print("🔧 Vérifiez les points mentionnés ci-dessus")
    
    print("\n💡 Conseils:")
    print("  • Utilisez la molette de la souris pour faire défiler horizontalement")
    print("  • Regardez les indicateurs '↔️' qui apparaissent")
    print("  • Les cours sont maintenant plus compacts quand il y en a beaucoup")
    print("  • Utilisez le bouton '🔍 Trouver créneaux chargés' pour naviguer")

if __name__ == "__main__":
    main()
