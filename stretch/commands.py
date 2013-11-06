import sys
import argparse
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'stretch.settings'

from django.core import management
from djcelery.management.commands import celery

from stretch import agent
from stretch.agent import loadbalancer_server


def run(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(prog='stretch')
    subparsers = parser.add_subparsers(help="Commands:", dest='command')

    subparsers.add_parser('agent', help='Run the stretch agent')
    subparsers.add_parser('lb', help='Run the stretch agent load balancer')
    subparsers.add_parser('autoload', help='Run the autoload handler')
    subparsers.add_parser('celery', help='Run celery queues')
    subparsers.add_parser('server', help='Run the server')

    # Set default option
    if len(args) == 0:
        args.append('server')

    # Parse arguments
    args = parser.parse_args(args)

    if args.command == 'agent':
        agent.run()
    if args.command == 'lb':
        loadbalancer_server.run()
    elif args.command == 'autoload':
        management.call_command('autoload')
    elif args.command == 'celery':
        command = celery.Command()
        command.run_from_argv(['manage.py', 'celery', 'worker'])
    elif args.command == 'server':
        management.call_command('run_gunicorn')
