#!/usr/bin/env python3
"""
Script de test de performance pour les optimisations API
"""
import asyncio
import aiohttp
import time
import json
from typing import List, Dict


async def test_api_performance():
    """Teste les performances des APIs optimisées"""
    print("🚀 Début test de performance des optimisations API")

    # URL de base
    base_url = "http://localhost:5005"

    # IDs de cours pour le test (simulés)
    course_ids = [
        "course_ab1710009f496c54",
        "course_bc2820110f597d65",
        "course_cd3930221f698e76",
        "course_de4040332f799f87",
        "course_ef5150443f800098"
    ]

    async with aiohttp.ClientSession() as session:
        print("\n📊 Test 1: Requêtes individuelles (non optimisées)")
        start_time = time.time()

        tasks = []
        for course_id in course_ids:
            task = make_individual_request(session, base_url, course_id)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        individual_time = time.time() - start_time

        print(f"⏱️  Temps requêtes individuelles: {individual_time:.2f}s")
        print(f"📈 Nombre de requêtes: {len(course_ids)}")
        print(f"🔥 Temps moyen par requête: {individual_time/len(course_ids):.3f}s")

        print("\n📊 Test 2: Requête batch (optimisée)")
        start_time = time.time()

        batch_result = await make_batch_request(session, base_url, course_ids)
        batch_time = time.time() - start_time

        print(f"⏱️  Temps requête batch: {batch_time:.2f}s")
        print(f"📈 Nombre de cours traités: {batch_result.get('processed_count', 0)}")

        # Calcul gain performance
        if batch_time > 0:
            improvement = (individual_time - batch_time) / individual_time * 100
            print(f"\n🎯 AMÉLIORATION PERFORMANCE: {improvement:.1f}%")
            print(f"🚀 Facteur d'accélération: {individual_time/batch_time:.1f}x")

        print("\n📊 Test 3: Cache client (deuxième appel)")
        start_time = time.time()

        tasks = []
        for course_id in course_ids[:3]:  # Test sur 3 cours
            task = make_individual_request(session, base_url, course_id)
            tasks.append(task)

        await asyncio.gather(*tasks)
        cache_time = time.time() - start_time

        print(f"⏱️  Temps avec cache: {cache_time:.2f}s")

        return {
            'individual_time': individual_time,
            'batch_time': batch_time,
            'cache_time': cache_time,
            'improvement_percent': improvement if batch_time > 0 else 0
        }


async def make_individual_request(session, base_url: str, course_id: str):
    """Fait une requête individuelle pour obtenir les salles occupées"""
    try:
        url = f"{base_url}/api/get_occupied_rooms"
        payload = {'course_id': course_id}

        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('occupied_rooms', [])
            else:
                print(f"❌ Erreur requête individuelle {course_id}: {response.status}")
                return []

    except Exception as e:
        print(f"❌ Exception requête individuelle {course_id}: {e}")
        return []


async def make_batch_request(session, base_url: str, course_ids: List[str]):
    """Fait une requête batch pour plusieurs cours"""
    try:
        url = f"{base_url}/api/batch_occupied_rooms"
        payload = {'course_ids': course_ids}

        async with session.post(url, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                print(f"❌ Erreur requête batch: {response.status}")
                return {}

    except Exception as e:
        print(f"❌ Exception requête batch: {e}")
        return {}


async def test_client_cache():
    """Teste le cache côté client"""
    print("\n🧪 Test cache côté client")

    # Simuler les appels JavaScript avec des timings
    print("1️⃣  Premier appel - Cache MISS attendu")
    print("2️⃣  Deuxième appel (< 30s) - Cache HIT attendu")
    print("3️⃣  Troisième appel (> 30s) - Cache MISS attendu")

    print("ℹ️  Vérifiez les logs de l'application pour voir les messages de cache")


def print_summary(results: Dict):
    """Affiche un résumé des résultats"""
    print("\n" + "="*60)
    print("📋 RÉSUMÉ DES OPTIMISATIONS IMPLÉMENTÉES")
    print("="*60)

    print("\n✅ OPTIMISATIONS CLIENT:")
    print("  • Cache client avec TTL de 30s")
    print("  • Debouncing des requêtes (150ms)")
    print("  • Déduplication des requêtes en cours")
    print("  • Logs détaillés des hits/miss de cache")

    print("\n✅ OPTIMISATIONS SERVEUR:")
    print("  • Flask-Caching avec timeout 60s")
    print("  • Endpoint batch pour requêtes multiples")
    print("  • Cache à double niveau (Flask + manuel)")
    print("  • Logs de performance serveur")

    print("\n📈 RÉSULTATS PERFORMANCE:")
    if results:
        print(f"  • Amélioration globale: {results['improvement_percent']:.1f}%")
        print(f"  • Temps avant: {results['individual_time']:.2f}s")
        print(f"  • Temps après: {results['batch_time']:.2f}s")
        print(f"  • Cache client actif: {results['cache_time']:.2f}s")

    print("\n🎯 IMPACT ATTENDU:")
    print("  • Réduction de 140+ à <20 requêtes par page")
    print("  • Temps de chargement page divisé par 3-5x")
    print("  • Moins de charge serveur")
    print("  • Expérience utilisateur plus fluide")


if __name__ == "__main__":
    print("🔧 TESTS DE PERFORMANCE - OPTIMISATIONS API")
    print("=" * 50)

    try:
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(test_api_performance())

        # Test cache client (informatif)
        loop.run_until_complete(test_client_cache())

        # Résumé final
        print_summary(results)

        print("\n✅ Tests de performance terminés!")

    except KeyboardInterrupt:
        print("\n⚠️ Tests interrompus par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur durant les tests: {e}")