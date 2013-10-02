from stretch import utils
from stretch.sources import AutoloadableSource
from stretch.backends import AutoloadingBackend
from stretch.models import Environment


# Load source
if settings.SOURCE:
    source_class_name, source_class_options = settings.SOURCE.items()[0]
    source = utils.get_class(source_class_name)(source_class_options)
else:
    raise NameError('No source defined')

# Load backend
if settings.BACKEND:
    backend_class_name, backend_class_options = settings.BACKEND.items()[0]
    backend = utils.get_class(backend_class_name)(backend_class_options)
else:
    raise NameError('No backend defined')

# Check source /backend compatibility
if isinstance(source, AutoloadableSource) and source.autoload:
    if not isinstance(backend, AutoloadingBackend):
        raise Exception('Backend incompatible with autoloadable source.')

    # Initial deploy
    source.parse()
    for environment in Environment.objects.filter(auto_deploy=True):
        environment.deploy(source)
