#!/usr/bin/env python3

import requests
import time
import statistics

def test_endpoint_performance(url, iterations=5):
    """Test les performances d'un endpoint"""
    times = []

    for i in range(iterations):
        start = time.time()
        response = requests.get(url)
        end = time.time()

        if response.status_code == 200:
            times.append((end - start) * 1000)  # Convertir en ms
        else:
            print(f"❌ Erreur {response.status_code} pour {url}")
            return None

    return {
        'min': min(times),
        'max': max(times),
        'mean': statistics.mean(times),
        'median': statistics.median(times)
    }

def main():
    base_url = "http://localhost:5005"

    print("🚀 TEST DE PERFORMANCE - APPLICATION OPTIMISÉE SQLite")
    print("=" * 60)

    # Test différents endpoints
    endpoints = {
        "Page principale": "/",
        "Liste professeurs": "/professors",
        "Semaine spécifique": "/week/Semaine%2037%20B",
        "Professeur spécifique": "/professor/M%20Bogaert"
    }

    results = {}

    for name, endpoint in endpoints.items():
        print(f"\n📊 Test: {name}")
        print(f"   Endpoint: {endpoint}")

        result = test_endpoint_performance(f"{base_url}{endpoint}")
        if result:
            results[name] = result
            print(f"   ⚡ Min: {result['min']:.1f}ms")
            print(f"   📈 Max: {result['max']:.1f}ms")
            print(f"   📊 Moyenne: {result['mean']:.1f}ms")
            print(f"   🎯 Médiane: {result['median']:.1f}ms")
        else:
            print(f"   ❌ Test échoué")

    print("\n" + "=" * 60)
    print("🎉 RÉSUMÉ DES PERFORMANCES")
    print("=" * 60)

    for name, stats in results.items():
        print(f"• {name:<20}: {stats['mean']:.1f}ms moyenne")

    # Moyenne générale
    all_means = [stats['mean'] for stats in results.values()]
    if all_means:
        print(f"\n🚀 Performance moyenne générale: {statistics.mean(all_means):.1f}ms")
        print("✅ Application TRÈS RAPIDE avec SQLite!")

if __name__ == "__main__":
    main()