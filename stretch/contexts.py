class ServicesContext(object):
    def __init__(self, environment):
        self.services = environment.system.services

    def __getattribute__(self, attr):
        data = None
        service = self.services.objects.get(name=attr)
        if service:
            data = service.data
        return data


def create_deploy_context(deploy):
    return {
        'services': ServicesContext(deploy.environment),
        'environment': deploy.environment,
        'release': deploy.release,
        'existing_release': deploy.existing_release
    }


def create_application_context(): pass
