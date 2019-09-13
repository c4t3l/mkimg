#!/usr/bin/python3

import argparse
import subprocess
import sys

MKIMG_COMMANDS = ('init', 'build', 'clean', 'summary')
__version__ = '1'


def create_parser():

    parser = argparse.ArgumentParser(prog='mkimg',
                                     description='''Wrapper for mkosi.  This utility generates a compressed btrfs subvolume 
                                                    image based upon Centos 7.  This subvolume is a self contained 
                                                    filesystem with no nested subvolumes.''',
                                     add_help=False)
    group = parser.add_argument_group('Commands')
    group.add_argument('verb',
                       choices=MKIMG_COMMANDS,
                       default='build',
                       action='store',
                       help='Operations to execute.')
    group.add_argument('-h',
                       '--help',
                       action='help',
                       help="Show this help")
    group.add_argument('--version',
                       action='version', version='%(prog)s ' + __version__)

    return parser.parse_args()


def summary():
    '''
    Calls the summary command in mkosi

    :return:
    '''
    summary = subprocess.run(['mkosi', 'summary'])
    return summary

def init(force=False):
    '''
    This function conducts the pre-flight checks and generates the required project structure.
    Passing "force=True" will override all current mkosi configs with defaults.

    build/ (btrfs subvol)
    mkosi.default
    mkosi.rootpw
    streams/
    buildroot/

    :return:
    '''

def check_btrfs():
    '''
    Check if cwd is on a btrfs filesystem.  Otherwise give error msg and quit.
    Run a variant of
    btrfs inspect-internal rootid .
    :return:
    '''
    butter = subprocess.run(['btrfs', 'inspect-internal', 'rootid', '.'],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            capture_output=False)
    if butter.returncode is 0:
        sys.stderr.write('Local directory is in a subvol\n')
        return True
    else:
        sys.stderr.write('Local directory is NOT in a btrfs subvol... Quiting.\n')
        sys.exit(1)


def paruse_args(argv=None):
    parser = create_parser()
    print('Call ' + parser.verb + ' action')
    return parser.verb


def main():
    #TODO: Remove this shit when done testing
    #paruse_args()
    check_btrfs()
    summary()


if __name__ == "__main__":
    main()

