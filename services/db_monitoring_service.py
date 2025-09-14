import time
import threading
from typing import Dict, List, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
import sqlite3
from models import db


@dataclass
class QueryStats:
    """Statistiques d'une requête"""
    query_type: str
    execution_time: float
    timestamp: datetime
    rows_affected: int
    table_name: str


class DatabaseMonitoringService:
    """Service de monitoring des performances de base de données"""

    def __init__(self):
        self._query_stats = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._query_counters = defaultdict(int)
        self._slow_queries_threshold = 100.0  # 100ms

    def record_query(self, query_type: str, execution_time: float,
                    rows_affected: int = 0, table_name: str = ""):
        """Enregistre une requête avec ses performances"""
        with self._lock:
            stat = QueryStats(
                query_type=query_type,
                execution_time=execution_time,
                timestamp=datetime.now(),
                rows_affected=rows_affected,
                table_name=table_name
            )

            self._query_stats.append(stat)
            self._query_counters[query_type] += 1

            if execution_time > self._slow_queries_threshold:
                print(f"🐌 SLOW QUERY DETECTED: {query_type} ({execution_time:.2f}ms)")

    def get_performance_summary(self) -> Dict:
        """Retourne un résumé des performances"""
        with self._lock:
            if not self._query_stats:
                return {"total_queries": 0}

            recent_queries = list(self._query_stats)

            total_time = sum(q.execution_time for q in recent_queries)
            avg_time = total_time / len(recent_queries) if recent_queries else 0

            slow_queries = [q for q in recent_queries
                          if q.execution_time > self._slow_queries_threshold]

            query_types = defaultdict(list)
            for q in recent_queries:
                query_types[q.query_type].append(q.execution_time)

            type_stats = {}
            for qtype, times in query_types.items():
                type_stats[qtype] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "max_time": max(times),
                    "min_time": min(times)
                }

            return {
                "total_queries": len(recent_queries),
                "total_time_ms": total_time,
                "avg_time_ms": avg_time,
                "slow_queries_count": len(slow_queries),
                "query_types": type_stats,
                "recent_queries": [
                    {
                        "type": q.query_type,
                        "time": q.execution_time,
                        "timestamp": q.timestamp.isoformat(),
                        "table": q.table_name
                    }
                    for q in recent_queries[-10:]  # 10 dernières requêtes
                ]
            }

    def get_database_info(self) -> Dict:
        """Informations système de la base de données"""
        try:
            db_path = db.engine.url.database

            # Connexion directe pour les stats SQLite
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Taille de la DB
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();")
            db_size = cursor.fetchone()[0]

            # Cache hits (approximatif)
            cursor.execute("PRAGMA cache_size;")
            cache_size = cursor.fetchone()[0]

            # Tables et leurs tailles
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()

            table_stats = {}
            for table in tables:
                table_name = table[0]
                if not table_name.startswith('sqlite_'):
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    row_count = cursor.fetchone()[0]
                    table_stats[table_name] = {"rows": row_count}

            conn.close()

            return {
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "cache_size": cache_size,
                "tables": table_stats,
                "connection_pool": {
                    "pool_size": getattr(db.engine.pool, 'size', 'N/A'),
                    "checked_out": getattr(db.engine.pool, 'checkedout', 'N/A'),
                    "overflow": getattr(db.engine.pool, 'overflow', 'N/A')
                }
            }

        except Exception as e:
            return {"error": f"Impossible de récupérer les infos DB: {e}"}

    def analyze_query_patterns(self) -> Dict:
        """Analyse les patterns de requêtes pour optimisations"""
        with self._lock:
            if not self._query_stats:
                return {}

            recent_queries = list(self._query_stats)

            # Fréquence des requêtes par type
            frequency = defaultdict(int)
            for q in recent_queries:
                frequency[q.query_type] += 1

            # Tables les plus sollicitées
            table_usage = defaultdict(int)
            for q in recent_queries:
                if q.table_name:
                    table_usage[q.table_name] += 1

            # Requêtes par heure (approximatif)
            hourly_pattern = defaultdict(int)
            for q in recent_queries:
                hour = q.timestamp.hour
                hourly_pattern[hour] += 1

            return {
                "query_frequency": dict(frequency),
                "table_usage": dict(table_usage),
                "hourly_pattern": dict(hourly_pattern),
                "recommendations": self._generate_recommendations(frequency, table_usage)
            }

    def _generate_recommendations(self, frequency: Dict, table_usage: Dict) -> List[str]:
        """Génère des recommandations d'optimisation"""
        recommendations = []

        # Recommandations basées sur la fréquence
        most_frequent = max(frequency.items(), key=lambda x: x[1]) if frequency else None
        if most_frequent and most_frequent[1] > 100:
            recommendations.append(f"Consider caching for {most_frequent[0]} (called {most_frequent[1]} times)")

        # Recommandations basées sur les tables
        most_used_table = max(table_usage.items(), key=lambda x: x[1]) if table_usage else None
        if most_used_table and most_used_table[1] > 50:
            recommendations.append(f"Optimize indexes for table {most_used_table[0]} (accessed {most_used_table[1]} times)")

        return recommendations

    def clear_stats(self):
        """Vide les statistiques"""
        with self._lock:
            self._query_stats.clear()
            self._query_counters.clear()


# Instance globale
db_monitor = DatabaseMonitoringService()


def monitor_query(func):
    """Décorateur pour monitorer les requêtes"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = (time.time() - start_time) * 1000

            # Extraire le nom de la fonction comme type de requête
            query_type = func.__name__

            # Essayer de deviner la table depuis les arguments
            table_name = ""
            if hasattr(result, '__table__'):
                table_name = result.__table__.name
            elif hasattr(result, 'first') and result.first():
                table_name = getattr(result.first().__table__, 'name', '')

            rows_affected = len(result) if hasattr(result, '__len__') else 0

            db_monitor.record_query(
                query_type=query_type,
                execution_time=execution_time,
                rows_affected=rows_affected,
                table_name=table_name
            )

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            db_monitor.record_query(
                query_type=f"{func.__name__}_ERROR",
                execution_time=execution_time,
                rows_affected=0,
                table_name=""
            )
            raise e

    return wrapper