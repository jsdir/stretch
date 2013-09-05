from django.conf import settings

from stretch import utils


def run():
    sources = settings.STRETCH['SOURCES']
    backend_class = settings.STRETCH['BACKEND']

    # Load backend
    if not backend:
        raise NameError('No backend defined')
    backend = utils.get_class(backend)()

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
