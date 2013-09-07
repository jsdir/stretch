import os
import errno
import importlib
import lockfile
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


salt_master_config = salt.config.master_config(settings.SALT_CONF_PATH)
wheel_client = salt.wheel.Wheel(salt_master_config)
salt_client = salt.client.LocalClient()
