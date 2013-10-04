import django.dispatch


sync_source = django.dispatch.Signal(providing_args=['snapshot', 'nodes'])
load_sources = django.dispatch.Signal()
