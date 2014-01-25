from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stretch.settings')

app = Celery('stretch',
             broker='amqp://',
             backend='amqp://',
             include=['stretch.models'])

app.config_from_object('django.conf:settings')
app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600
)

if __name__ == '__main__':
    app.start()
