import sys
import argparse
import subprocess
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'stretch.settings'

from django.core import management
from djcelery.management.commands import celery

from stretch import agent
from stretch.agent import supervisors


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
        subprocess.call(['gunicorn', 'stretch.agent.app:app', '-w', '4'])
        #agent.run()
    elif args.command == 'lb_supervisor':
        supervisors.run_lb_supervisor()
    elif args.command == 'endpoint_supervisor':
        supervisors.run_endpoint_supervisor()
    elif args.command == 'instance_supervisor':
        supervisors.run_instance_supervisor()
    elif args.command == 'autoload':
        management.call_command('autoload')
    elif args.command == 'celery':
        command = celery.Command()
        command.run_from_argv(['manage.py', 'celery', 'worker'])
    elif args.command == 'server':
        management.call_command('run_gunicorn')
