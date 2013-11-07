import json

from stretch import utils
from stretch.agent import api, resources


class Node(resources.PersistentObject):
    name = 'node'
    attrs = {
        'env_name': None,
        'app_path': None,
        'sha': None,
        'ports': {},
        'image': None
    }

    def pull(self, sha, app_path, ports, env_name, image):
        self.update({'sha': sha})

    @property
    def pulled(self):
        return self.data['sha'] or self.data['app_path']


def configure_parser(parser):
    parser.add_argument('sha', type=str)
    parser.add_argument('app_path', type=str)
    parser.add_argument('ports', type=str, required=True)
    parser.add_argument('env_name', type=str, required=True)
    parser.add_argument('image', type=str, required=True)


def verify_args(args):
    args['ports'] = json.loads(args['ports'])
    if not args['sha'] and not args['sha']:
        raise Exception('neither `sha` nor `app_path` was specified')


def pull(node, args):
    # Pull image
    if not args['app_path']:
        utils.run_cmd(['docker', 'pull', args['image']])
    # TODO: Pull templates
    # Update node
    args['ports'] = json.loads(args['ports'])
    node.update(args)


resources.add_api_resource('nodes', NodeResource, NodeListResource)
resources.add_task_resource('nodes', Node, {
    'pull': {
        'parser_config': configure_parser,
        'verify_args': verify_args,
        'task': pull
    }
})
