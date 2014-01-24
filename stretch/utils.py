import os
import random
import inspect
import shutil
import tempfile
import distutils
import collections
import cPickle


#-#-#-#- Decorators -#-#-#-#

class memoized(object):
    """
    Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args, **kwargs):
        key = cPickle.dumps(args, 1) + cPickle.dumps(kwargs, 1)
        if not self.cache.has_key(key):
            self.cache[key] = self.func(*args, **kwargs)
        return self.cache[key]


#-#-#-#- Files -#-#-#-#

def make_dir(path):
    """
    Creates a directory. This is the equivalent of `mkdir -p` in unix.
    """
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def temp_dir(path=None):
    """
    Copies the contents of `path` into a temporary directory. The path to
    this directory is returned. If `path` is None, nothing is copied into the
    temporary directory.
    """
    # Create temporary directory in case it doesn't exist.
    mkdir(settings.STRETCH_TEMP_DIR)

    dest = tempfile.mkdtemp(prefix='%s/' % settings.STRETCH_TEMP_DIR)
    if path:
        copy_dir(path, dest)
    return dest


def copy_dir(path, dest):
    """
    Copies the contents of `path` into `dest`.
    """
    distutils.dir_util.copy_tree(path, dest)


def delete_dir(path):
    shutil.rmtree(path)


#-#-#-#- Dictionaries -#-#-#-#

def merge(original_dict, new):
    """
    Recursively merge dict-like objects.
    """
    for key, value in new.iteritems():
        if isinstance(value, collections.Mapping):
            original_dict[key] = merge(original_dict.get(key, {}), value)
        else:
            original_dict[key] = new[key]

    return original_dict


#-#-#-#- Objects -#-#-#-#

def find_subclasses(module, obj_class):
    return [cls for name, cls in inspect.getmembers(module)
        if inspect.isclass(cls) and issubclass(cls, obj_class)
    ]


#-#-#-#- Naming -#-#-#-#

def generate_random_hex(length=16):
    hexdigits = '0123456789abcdef'
    return ''.join(random.choice(hexdigits) for _ in xrange(length))


def generate_memorable_name():  # pragma: no cover
    """
    Return a randomly-generated memorable name.
    """
    adjectives = [
        'afternoon', 'aged', 'ancient', 'autumn', 'billowing',
        'bitter', 'black', 'blue', 'bold', 'broken',
        'calm', 'caring', 'cold', 'cool', 'crimson',
        'damp', 'dark', 'dawn', 'delicate', 'divine',
        'dry', 'empty', 'ephemeral', 'evening', 'falling',
        'fathomless', 'floral', 'fragrant', 'frosty', 'golden',
        'green', 'hidden', 'holy', 'icy', 'imperfect',
        'impermanent', 'late', 'lingering', 'little', 'lively',
        'long', 'majestic', 'mindful', 'misty', 'morning',
        'muddy', 'nameless', 'noble', 'old', 'patient',
        'polished', 'proud', 'purple', 'quiet', 'red',
        'restless', 'rough', 'shy', 'silent', 'silvery',
        'slender', 'small', 'smooth', 'snowy', 'solitary',
        'sparkling', 'spring', 'stately', 'still', 'strong',
        'summer', 'timeless', 'twilight', 'unknowable', 'unmovable',
        'upright', 'wandering', 'weathered', 'white', 'wild',
        'winter', 'wispy', 'withered', 'young',
    ]
    nouns = [
        'bird', 'breeze', 'brook', 'brook', 'bush',
        'butterfly', 'chamber', 'chasm', 'cherry', 'cliff',
        'cloud', 'darkness', 'dawn', 'dew', 'dream',
        'dust', 'eye', 'feather', 'field', 'fire',
        'firefly', 'flower', 'foam', 'fog', 'forest',
        'frog', 'frost', 'glade', 'glitter', 'grass',
        'hand', 'haze', 'hill', 'horizon', 'lake',
        'leaf', 'lily', 'meadow', 'mist', 'moon',
        'morning', 'mountain', 'night', 'paper', 'pebble',
        'pine', 'planet', 'plateau', 'pond', 'rain',
        'resonance', 'ridge', 'ring', 'river', 'sea',
        'shadow', 'shape', 'silence', 'sky', 'smoke',
        'snow', 'snowflake', 'sound', 'star', 'stream',
        'sun', 'sun', 'sunset', 'surf', 'thunder',
        'tome', 'tree', 'violet', 'voice', 'water',
        'waterfall', 'wave', 'wave', 'wildflower', 'wind',
        'wood',
    ]
    return '%s-%s-%s' % (random.choice(adjectives), random.choice(nouns),
                         generate_random_hex(4))
