import django.dispatch


sync_source = django.dispatch.Signal(providing_args=['nodes'])
load_sources = django.dispatch.Signal()
release_created = django.dispatch.Signal()
