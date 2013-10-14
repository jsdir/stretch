import salt
import salt.wheel
import salt.runner
from django.conf import settings


clients = {}


def master_config():
    return salt.config.master_config(settings.SALT_CONF_PATH)


def salt_client():
    client = clients.get('salt')
    if not client:
        client = clients['salt'] = salt.client.LocalClient()
    return client


def wheel_client():
    client = clients.get('wheel')
    if not client:
        client = clients['wheel'] = salt.wheel.Wheel(master_config())
    return client


def runner_client():
    client = clients.get('runner')
    if not client:
        client = clients['runner'] = salt.runner.RunnerClient(master_config())
    return client


def caller_client():
    client = clients.get('caller')
    if not client:
        client = clients['caller'] = salt.client.Caller()
    return client
