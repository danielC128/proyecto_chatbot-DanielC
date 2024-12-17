from celery import Celery

def make_celery(app_name, broker_url, backend_url):
    celery = Celery(app_name, broker=broker_url, backend=backend_url)
    celery.conf.update(
        broker_connection_retry_on_startup=True,
        imports=['app']  # Importa solo las tareas, no toda la app Flask
    )
    return celery

# Configuración del broker y backend de Celery
BROKER_URL = 'redis://localhost:6379/0'
BACKEND_URL = 'redis://localhost:6379/0'

# Crea la instancia de Celery
celery = make_celery('app', BROKER_URL, BACKEND_URL)
