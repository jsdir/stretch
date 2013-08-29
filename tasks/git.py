from celery import task


@task(name='git.add')
def add(x, y):
    return x + y
