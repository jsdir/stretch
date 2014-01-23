from __future__ import absolute_import

from stretch.celery import app
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


'''
@app.task
def mul(x, y):
    return x * y


@app.task
def xsum(numbers):
    return sum(numbers)
'''
