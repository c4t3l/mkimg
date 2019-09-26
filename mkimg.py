#!/usr/bin/python3

import argparse
import subprocess
import sys
import os
import textwrap
from pathlib import Path

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

    sys.stderr.write('PRE-FLIGHT CHECKLIST:\n')
    if _check_btrfs():
        sys.stderr.write('          Current directory is a btrfs subvol: YES\n')
        checker = 0
    else:
        sys.stderr.write('          Current directory is a btrfs subvol: NO\n')
        checker = 1

    bins = _check_binaries()
    if bins[1]:
        for item in bins[0]:
            sys.stderr.write(item)

    else:
        for item in bins[0]:
            sys.stderr.write(item)
        checker = 1

    if checker != 0:
        die('''\n          #########################################################
          Some preflight checks failed.  Please check dependencies.
          #########################################################''')



def init(clean=False):
    '''
    This function conducts the pre-flight checks and generates the required project structure.
    Passing "clean=True" will override all current mkosi configs with defaults.

    build/ (btrfs subvol)
    mkosi.default
    mkosi.rootpw
    streams/
    buildroot/


    try:
        # Create target Directory
        os.mkdir(dirName)
        print("Directory " , dirName ,  " Created ")
    except FileExistsError:
        print("Directory " , dirName ,  " already exists")


    from pathlib import Path

    for filename in Path('src').glob('**/*.c'):
    print(filename)


    :return:
    '''

    check_root()

    mydirs = ['streams', 'services', 'buildroot']
    myfiles = ['mkosi.default', 'mkosi.rootpw']
    sudo_uid = int(os.environ['SUDO_UID'])
    sudo_gid = int(os.environ['SUDO_GID'])

    if clean:
        for file in myfiles:
            os.remove(file)

        for file in mydirs:
            os.removedirs(file)

        subprocess.run(['btrfs', 'subvol', 'delete', 'build'], stdout=subprocess.DEVNULL)

    else:
        preflight_checks()
        sys.stderr.write('\nINITIALIZING PROJECT SPACE:\n')

        try:
            subprocess.run(['btrfs', 'subvol', 'create', 'build'], stdout=subprocess.DEVNULL)
            os.chown('build', sudo_uid, sudo_gid)
            sys.stderr.write('          Created build subvolume\n')
        except OSError:
            sys.stderr.write('          Failed to create build subvolume\n')

        for directory in mydirs:
            try:
                os.mkdir(directory)
                os.chown(directory, sudo_uid, sudo_gid)
                sys.stderr.write('          Created ' + directory + ' directory \n')
            except FileExistsError:
                sys.stderr.write('          Failed to create ' + directory + ': It already exists.\n')

        mkrootpw = 'hello'
        mkdefault = '''\
                    [Distribution]
                    Distribution=centos
                    Release=7

                    [Output]
                    Format=directory
                    OutputDirectory=buildroot

                    [Packages]
                    Packages=yum
                             systemd
                             yum-utils
                             passwd
                    '''

        try:
            with open('mkosi.default', 'w') as f:
                f.write(textwrap.dedent(mkdefault))
                f.close()
            os.chown('mkosi.default', sudo_uid, sudo_gid)
            sys.stderr.write('          Created mkosi.default file\n')

            with open('mkosi.rootpw', 'w') as f:
                f.write(mkrootpw)
                f.close()
            os.chmod('mkosi.rootpw', 0o600)
            os.chown('mkosi.rootpw', sudo_uid, sudo_gid)
            sys.stderr.write('          Created mkosi.default file\n')
        except OSError:
            sys.stderr.write('          Error in mkosi template file create')


def _check_btrfs():
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
        return True
    else:
        return False


def _check_binaries():
    '''

    :param rpm:
    :return:
    '''

    apps = ['zstd', 'mkosi']
    returns = list()
    path = Path('/usr/bin')

    for _ in apps:
        posix = path / _

        if posix.exists():
            returns += '          Binary ' \
                    + str(posix.resolve()) \
                    + ' exists: ' \
                    + 'YES\n'
            status = True

        else:
            returns += '          Binary ' \
                    + str(posix.resolve()) \
                    + ' exists: ' \
                    + 'NO\n'
            status = False

    return (returns, status)


def paruse_args(argv=None):
    parser = create_parser()

    if parser.verb == 'init':
        init()
    elif parser.verb == 'summary':
        summary()
    elif parser.verb == 'clean':
        init(clean=True)
    else:
        return parser.verb


def die(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


def check_root():
    if os.getuid() != 0:
        die("Must be invoked as root.")

def main():
    #TODO: Remove this shit when done testing
    paruse_args()
    #_check_binaries()


if __name__ == "__main__":
    main()

