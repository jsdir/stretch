import salt
import salt.wheel
import salt.runner
from django.conf import settings

from stretch.utils import memoized


def master_config():
    return salt.config.master_config(settings.STRETCH_SALT_CONF_PATH)


@memoized
def salt_client():
    return salt.client.LocalClient()


@memoized
def wheel_client():
    return salt.wheel.Wheel(master_config())


@memoized
def runner_client():
    return salt.runner.RunnerClient(master_config())


@memoized
def caller_client():
    return salt.client.Caller()
