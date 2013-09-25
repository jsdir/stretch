class ServicesContext(object):
    def __init__(self, environment):
        self.services = environment.system.services

    def __getattribute__(self, attr):
        data = None
        service = self.services.objects.get(name=attr)
        if service:
            data = service.data
        return data


def create_deploy_context(environment, new_release=None,
                          existing_release=None):
    return {
        'services': ServicesContext(environment),
        'environment': environment,
        'release': new_release,
        'existing_release': existing_release
    }


def create_application_context(): pass
