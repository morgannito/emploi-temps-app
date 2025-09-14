# Configuration Gunicorn optimisée pour la production et la stabilité
import multiprocessing
import os

# Nombre de workers (réduit pour éviter la surcharge mémoire)
workers = min(multiprocessing.cpu_count(), 4)  # Maximum 4 workers

# Type de worker (sync est plus stable pour cette application)
worker_class = 'sync'

# Port d'écoute
bind = '0.0.0.0:5005'

# Timeouts optimisés
timeout = 300  # 5 minutes pour les requêtes longues
keepalive = 2
graceful_timeout = 60

# Nombre maximum de requêtes par worker avant redémarrage (réduit pour éviter les fuites mémoire)
max_requests = 500
max_requests_jitter = 100

# Logs détaillés pour le debugging
accesslog = './logs/gunicorn_access.log'
errorlog = './logs/gunicorn_error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Préchargement de l'application (désactivé pour éviter les problèmes de mémoire)
preload_app = False

# Nombre de connexions simultanées par worker
worker_connections = 1000

# Configuration pour éviter les fuites mémoire
worker_tmp_dir = '/dev/shm'
max_requests_jitter = 100

# Limites de mémoire (en bytes)
worker_memory_limit = 500 * 1024 * 1024  # 500MB par worker

# Headers de sécurité
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Configuration pour la stabilité
daemon = False
pidfile = './logs/gunicorn.pid'

# Callbacks pour le monitoring
def on_starting(server):
    """Appelé au démarrage du serveur"""
    server.log.info("🚀 Démarrage du serveur Gunicorn")

def on_reload(server):
    """Appelé lors du rechargement"""
    server.log.info("🔄 Rechargement du serveur Gunicorn")

def worker_int(worker):
    """Appelé quand un worker reçoit un signal INT"""
    worker.log.info("⚠️ Worker %s reçoit un signal INT", worker.pid)

def pre_fork(server, worker):
    """Appelé avant la création d'un worker"""
    server.log.info("👶 Création du worker %s", worker.pid)

def post_fork(server, worker):
    """Appelé après la création d'un worker"""
    server.log.info("✅ Worker %s créé avec succès", worker.pid)

def post_worker_init(worker):
    """Appelé après l'initialisation d'un worker"""
    worker.log.info("🎯 Worker %s initialisé", worker.pid)

def worker_abort(worker):
    """Appelé quand un worker crash"""
    worker.log.error("💥 Worker %s a crashé", worker.pid)

def on_exit(server):
    """Appelé à la fermeture du serveur"""
    server.log.info("🛑 Arrêt du serveur Gunicorn")
