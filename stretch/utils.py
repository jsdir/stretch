import os
import errno
import random
import inspect
import shutil
import logging
import tempfile
import distutils.dir_util
import subprocess
import collections
import cPickle
from twisted.internet import task, defer

log = logging.getLogger(__name__)


#-#-#-#- Functions -#-#-#-#

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


def deferred_batch_map(items, func, batch_size):
    c = task.Cooperator()

    def get_tasks():
        for item in items:
            yield func(item)

    tasks = get_tasks()

    return defer.DeferredList([
        c.coiterate(tasks) for _ in xrange(batch_size)
    ])


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
    from stretch import config
    make_dir(config.get_config()['temp_dir'])

    dest = tempfile.mkdtemp(prefix='%s/' % config.get_config()['temp_dir'])
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

def merge(original, new):
    """
    Recursively merge dict-like objects.
    """
    for key, value in new.iteritems():
        if isinstance(value, collections.Mapping):
            original[key] = merge(original.get(key, {}), value)
        else:
            original[key] = new[key]

    return original


#-#-#-#- System -#-#-#-#

def run(cmd, env={}, raise_errors=True, shell=False):
    log.debug('Running: %s' % cmd)
    log.debug('Environment: %s' % env)
    pipe = subprocess.PIPE
    p = subprocess.Popen(cmd, stdout=pipe, stderr=pipe, shell=shell, env=env)

    output = ''
    for line in p.stdout:
        log.info(line)
        output += line

    stdout, stderr = p.communicate()
    if p.returncode != 0 and raise_errors:
        raise Exception(stderr)

    return output, p.returncode


#-#-#-#- Naming -#-#-#-#

def generate_random_hex(length=16):  # pragma: no cover
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