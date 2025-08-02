from celery import Celery
import os

app = Celery(
    'filemanager',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    include=['filemanager.backend.tasks']
)

# Optional configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'filemanager.backend.tasks.extract_text': {'queue': 'text'},
        'filemanager.backend.tasks.embed_document': {'queue': 'embeddings'}
    }
)

if __name__ == '__main__':
    app.start()