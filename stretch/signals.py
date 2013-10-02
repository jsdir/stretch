import django.dispatch


source_changed = django.dispatch.Signal(providing_args=['file_events'])
