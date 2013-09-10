#!/usr/bin/env python
import sys
import yaml
import gnupg
import argparse


def main():
    options = {}
    options['recipients'] = []

    parser = argparse.ArgumentParser(description='Encrypt a yaml file')
    parser.add_argument('filename', help='Input file')
    parser.add_argument('--homedir', help='Specify your gpg homedir, defaults '
                                          'to $GNUPGHOME or ~/.gnupg')
    parser.add_argument('-r', '--recipient', help='Encrypt using this key')
    
    args = vars(parser.parse_args())

    homedir = args.get('homedir')
    if homedir:
        options['homedir'] = homedir

    recipient = args.get('recipient')
    if recipient:
        options['recipients'].append(recipient)

    if options.has_key('homedir'):
        gpg = gnupg.GPG(gnupghome=options['homedir'])
    else:
        gpg = gnupg.GPG()

    if not options['recipients']:
        raise Exception('at least one RECIPIENT must be specified.')

    file_input = file(args['filename'], 'r')
    data = encrypt_any(options['recipients'],
                       yaml.load(file_input.read()), gpg)
    yaml.dump(data, sys.stdout)

def encrypt_any(r, d, gpg):
    if isinstance(d, str):
        return d
    elif isinstance(d, list):
        return map(lambda p: encrypt_text(r, p, gpg), d)
    elif isinstance(d, dict):
        return zip(d, map(lambda p: encrypt_text(r, p, gpg), d.values()))
    else:
        raise TypeError('Expected String, Array, or Hash, got %s' % type(d))

def encrypt_text(r, plain, gpg):
    try:
        cipher = gpg.encrypt(plain, r)
    except gnupg.Exception, err:
        raise err

    return cipher

if __name__ == '__main__':
    main()
