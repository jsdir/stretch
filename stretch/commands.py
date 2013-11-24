import sys
import argparse
import subprocess
import multiprocessing
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'stretch.settings'

from django.core import management
from djcelery.management.commands import celery

from stretch import agent
from stretch.agent import supervisors


def run_gunicorn(app):
    workers = multiprocessing.cpu_count() * 2 + 1
    subprocess.call(['gunicorn', app, '-w', str(workers)])


def run(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(prog='stretch')
    subparsers = parser.add_subparsers(help="Commands:", dest='command')

    subparsers.add_parser('agent', help='Run the stretch agent')
    subparsers.add_parser('lb', help='Run the stretch agent load balancer')
    subparsers.add_parser('endpoint', help='Run the endpoint supervisor')
    subparsers.add_parser('instance', help='Run the instance supervisor')
    subparsers.add_parser('autoload', help='Run the autoload handler')
    subparsers.add_parser('celery', help='Run celery queues')
    subparsers.add_parser('server', help='Run the server')

    # Set default option
    if len(args) == 0:
        args.append('server')

    # Parse arguments
    args = parser.parse_args(args)

    workers = multiprocessing.cpu_count() * 2 + 1

    if args.command == 'agent':
        run_gunicorn('stretch.agent.api:app')
    elif args.command == 'lb':
        supervisors.run_lb_supervisor()
    elif args.command == 'endpoint':
        supervisors.run_endpoint_supervisor()
    elif args.command == 'instance':
        supervisors.run_instance_supervisor()
    elif args.command == 'autoload':
        management.call_command('autoload')
    elif args.command == 'celery':
        celery.Command().run_from_argv(['manage.py', 'celery', 'worker'])
    elif args.command == 'server':
        run_gunicorn('stretch.wsgi:application')
