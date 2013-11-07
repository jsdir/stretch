import os
import json

from stretch import utils
from stretch.salt_api import caller_client
from stretch.agent import api, resources, agent_dir


class Node(resources.PersistentObject):
    name = 'node'
    attrs = {
        'env_id': None,
        'env_name': None,
        'app_path': None,
        'sha': None,
        'ports': {},
        'image': None
    }

    def pull(self, args):
        # Pull image
        if not args['app_path']:
            utils.run_cmd(['docker', 'pull', args['image']])
        # Pull templates
        templates_path = self.get_templates_path()
        src = 'salt://templates/%s/%s' % (args['env_id'], self.data['_id'])
        caller_client().function('cp.get_dir', src, templates_path)
        # Remove all contents before adding new templates
        utils.clear_path(templates_path)
        node.update(args)

    def get_templates_path(self):
        return os.path.join(agent_dir, 'templates', 'nodes', self.data['_id'])

    @property
    def pulled(self):
        return self.data['sha'] or self.data['app_path']


def configure_parser(parser):
    parser.add_argument('sha', type=str)
    parser.add_argument('app_path', type=str)
    parser.add_argument('ports', type=str, required=True)
    parser.add_argument('env_id', type=str, required=True)
    parser.add_argument('env_name', type=str, required=True)
    parser.add_argument('image', type=str, required=True)


def verify_args(args):
    args['ports'] = json.loads(args['ports'])
    if not args['sha'] and not args['sha']:
        raise Exception('neither `sha` nor `app_path` was specified')


def pull(node, args):
    args['ports'] = json.loads(args['ports'])
    node.pull(args)


resources.add_api_resource('nodes', NodeResource, NodeListResource)
resources.add_task_resource('nodes', Node, {
    'pull': {
        'parser_config': configure_parser,
        'verify_args': verify_args,
        'task': pull
    }
})
