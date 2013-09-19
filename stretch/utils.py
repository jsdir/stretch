import os
import errno
import importlib
import lockfile
import string
import random
import jinja2
import collections
import salt.client
import salt.config
import salt.wheel

from django.conf import settings


def get_class(class_path):
    parts = class_path.split('.')
    module, class_name = '.'.join(parts[:-1]), parts[-1]
    return getattr(importlib.import_module(module), class_name)


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def lock(name):
    lock_dir = settings.LOCK_DIR
    return lockfile.FileLock(os.path.join(lock_dir, '%s.lock' % name))


def generate_random_hex(length=16):
    hexdigits = '0123456789abcdef'
    return ''.join(random.choice(hexdigits) for _ in xrange(length))


def update(d, u):
    """
    Recursively merge dict-like objects.
    """
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def render_template(path, contexts=[]):
    context = {}
    [update(context, c) for c in contexts]
    directory, file_name = os.path.split(path)
    loader = jinja2.loaders.FileSystemLoader(directory)
    env = jinja2.Environment(loader=loader)
    data = env.get_template(file_name).render(context)
    with open(path, 'w') as f:
        f.write(data)


def generate_memorable_name():
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


salt_master_config = salt.config.master_config(settings.SALT_CONF_PATH)
wheel_client = salt.wheel.Wheel(salt_master_config)
salt_client = salt.client.LocalClient()
