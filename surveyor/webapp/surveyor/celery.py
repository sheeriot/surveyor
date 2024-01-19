# from __future__ import absolute_import, unicode_literals
import os

from celery import Celery
# from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveyor.settings')
app = Celery('surveyor')
# app.conf.enable_utc = False
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
