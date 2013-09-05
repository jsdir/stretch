from django.conf import settings

from stretch import utils


def run():
    sources = settings.SOURCES
    backend_class = settings.BACKEND

    # Load backend
    if not backend_class:
        raise NameError('No backend defined')

    class_name, class_options = backend_class.items()[0]
    backend = utils.get_class(class_name)(class_options)

    # Load sources
    if not sources:
        raise NameError('No sources defined')

    for source_class, options in sources.iteritems():
        source = utils.get_class(source_class)(options)
        if issubclass(source, AutoloadableSource):
            source.on_autoload = backend.pull
            fork(source.monitor())
        else:
            pass
