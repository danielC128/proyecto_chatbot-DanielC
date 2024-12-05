from celery import Celery

celery = Celery('app', broker='redis://localhost:6379/0')

celery.conf.update(
    result_backend='redis://localhost:6379/0',
    broker_connection_retry_on_startup=True,
)
