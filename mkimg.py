#!/usr/bin/python3

import argparse
import subprocess
import sys
import os
import rpm

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
    Calls the summary command in mkosi.
    Pre-pended with mkimg data

    :return:
    '''
    summary = subprocess.run(['mkosi', 'summary'])
    return summary


def preflight_checks(verbose=False):
    '''
    This checks for existence of required binaries, filesystems, files, etc.
    If verbose is true, preflight prints out mkosi-style summary data for mkimg
    :return:
    '''

    _check_btrfs()
    _check_rpms()

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


def _check_btrfs():
    '''
    Check if cwd is on a btrfs filesystem.  Otherwise give error msg and quit.
    Run a variant of
    btrfs inspect-internal rootid .
    :return:
    '''
    env = os.environ
    butter = subprocess.run(['btrfs', 'inspect-internal', 'rootid', env['PWD']],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            capture_output=False)
    if butter.returncode is 0:
        return True
    else:
        return False


def _check_rpms(rpms):
    '''

    :param rpm:
    :return:
    '''

    rpmcheck = dict()
    mylist = list()
    myrpms = list()
    ts = rpm.TransactionSet()
    mi = ts.dbMatch()

    for item in mi:
        # grab all installed rpms and convert to str
        mylist.append(item['name'].decode('utf-8')
                      + '-' + item['version'].decode('utf-8')
                      + '-' + item['release'].decode('utf-8')
                      )

    # Add the list of found packages
    for p in rpms:
        myrpms.append(list(filter(lambda x: p in x, mylist)))
        rpmcheck.update(({
                            'packages': myrpms,
                            'status': True
                        }))
    print(rpmcheck)
    return rpmcheck


def paruse_args(argv=None):
    parser = create_parser()
    print('Call ' + parser.verb + ' action')
    return parser.verb


def main():
    #TODO: Remove this shit when done testing
    #paruse_args()
    #check_btrfs()
    #summary()
    _check_rpms(['btrfs', 'zstd'])


if __name__ == "__main__":
    main()

