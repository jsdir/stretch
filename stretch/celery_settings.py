import djcelery

CELERY_IMPORTS = ("tasks.git")

djcelery.setup_loader()
