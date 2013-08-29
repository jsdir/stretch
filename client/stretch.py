import sys
import argparse
import requests


resources = [
    'environment',
    'user',
    'node',
    'group',
]


def create(args):
    print args.target


def delete(args):
    print args.target


def ps(args):
    print args.target


def use(args):
    print args.target


def create_parser():
    parser = argparse.ArgumentParser(description='CLI client for stretch')
    subparsers = parser.add_subparsers()

    create_parser = subparsers.add_parser('create', help='Create a resource')
    create_parser.add_argument('target')
    create_parser.set_defaults(func=create)

    delete_parser = subparsers.add_parser('delete', help='Delete a resource')
    delete_parser.add_argument('target')
    delete_parser.set_defaults(func=delete)

    ps_parser = subparsers.add_parser('ps', help='List resources')
    ps_parser.add_argument('target')
    ps_parser.set_defaults(func=ps)

    use_parser = subparsers.add_parser('use', help='Use an API endpoint')
    use_parser.add_argument('target')
    use_parser.set_defaults(func=use)

    return parser


def main():
    parser = create_parser()

    if len(sys.argv) < 2:
        sys.argv.append('--help')

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
