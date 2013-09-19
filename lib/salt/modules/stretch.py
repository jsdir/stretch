import docker


docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')


def create_node(id, node_type):
    pass


def delete_node(id):
    pass


def pull_release(sha, config):
    pass
