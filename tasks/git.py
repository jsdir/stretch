from celery import task


@task(name='create_host')
def create_host(backend):
    backend.create_host()
