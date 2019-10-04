#!/usr/bin/python3

import argparse
import subprocess
import sys
import os
import textwrap
import shutil
import tarfile
import secrets
from pathlib import Path
from distutils.dir_util import copy_tree

MKIMG_COMMANDS = ('init', 'build', 'clean', 'summary')
__version__ = '1'


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
        return True
    else:
        return False


def check_binaries():
    '''

    :param rpm:
    :return:
    '''

    apps = ['btrfs', 'mkosi', 'zstd', 'gzip']
    returns = list()

    for _ in apps:

        try:
            if shutil.which(_) is not None:
                returns += '          Binary ' \
                           + str(shutil.which(_)) \
                           + ' exists: ' \
                           + 'YES\n'
                status = True

            else:
                returns += '          Binary ' \
                           + _ \
                           + ' exists: ' \
                           + 'NO\n'
                status = False

        except shutil.Error:
            die('Error in binary search')

    return (returns, status)


def check_init():
    # Check for init lock file
    path = Path('.')
    file = path / '.init.lock'
    return file.exists()


def check_root():
    if os.getuid() != 0:
        die("Must be invoked as root.")


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


def paruse_args(argv=None):
    parser = create_parser()

    if parser.verb == 'init':
        init()
    elif parser.verb == 'summary':
        summary()
    elif parser.verb == 'build':
        build()
    elif parser.verb == 'clean':
        init(clean=True)
    else:
        return parser.verb


def preflight_checks():
    '''
    This checks for existence of required binaries, filesystems, files, etc.
    :return: str
    '''

    sys.stderr.write('PRE-FLIGHT CHECKLIST:\n')
    if check_btrfs():
        sys.stderr.write('          Current directory is a btrfs subvol: YES\n')
        checker = 0
    else:
        sys.stderr.write('          Current directory is a btrfs subvol: NO\n')
        checker = 1

    bins = check_binaries()
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

    :return:
    '''

    check_root()

    mydirs = ['streams', 'services', 'buildroot']
    myfiles = ['mkosi.default', 'mkosi.rootpw', '.init.lock']
    sudo_uid = int(os.environ['SUDO_UID'])
    sudo_gid = int(os.environ['SUDO_GID'])

    if clean:
        try:
            for file in myfiles:
                os.remove(file)

            for file in mydirs:
                shutil.rmtree(file)

            # Force remove btrfs subvolumes
            shutil.rmtree('build')

        except FileNotFoundError:
            die('No files found to remove')

    else:
        if check_init():
            die('Workspace is already initialized. Operation halted.')
        preflight_checks()
        sys.stderr.write('\nINITIALIZING PROJECT SPACE:\n')

        try:
            btrfs_do('build')
            os.chown('build', sudo_uid, sudo_gid)
            sys.stderr.write('          Created build subvolume\n')
        except OSError:
            die('Failed to create build subvolume')

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
            # create mkosi default config
            with open('mkosi.default', 'w') as f:
                f.write(textwrap.dedent(mkdefault))
                f.close()
            os.chown('mkosi.default', sudo_uid, sudo_gid)
            sys.stderr.write('          Created mkosi.default file\n')

            # create mkosi rootpw file
            with open('mkosi.rootpw', 'w') as f:
                f.write(mkrootpw)
                f.close()
            os.chmod('mkosi.rootpw', 0o600)
            os.chown('mkosi.rootpw', sudo_uid, sudo_gid)
            sys.stderr.write('          Created mkosi.default file\n')

            # Create init lock file
            Path('.init.lock').touch()
            os.chown('.init.lock', sudo_uid, sudo_gid)

        except OSError:
            die('Error in mkosi template file create')


def summary():
    '''
    Calls the summary command in mkosi.
    Pre-pended with mkimg data

    :return:
    '''

    preflight_checks()

    if check_init():
        sys.stderr.write('          Environment initialized: YES\n')
    else:
        sys.stderr.write('          Environment initialized: NO\n')

    # spacer... (should probably do this another way...)
    sys.stderr.write('\n')
    summary_output = subprocess.run(['mkosi', 'summary'])

    return summary_output


def btrfs_do(volume, command='subvol', action='create'):
    '''
    BTRFS utility function

    :param volume:
    :param command:
    :param action:
    :return:
    '''
    try:
        butter = subprocess.run(['btrfs', command, action, volume], stdout=subprocess.DEVNULL)

    except OSError:
        die('Error handling BTRFS object.')

    return butter


def build():
    # This function is still in a non-working state...
    '''
    Generate build id
    Kick off mkosi
    Create subvol in build
    Copy contents from buildroot to build subvol
    Set build/subvol to read only
    Compress build/subvol to sendstream file with zstd

    :return:
    '''

    if not check_init():
        die('Workspace is not initialized. Operation halted.')

    check_root()
    mycid = gen_cid()
    myvolume = 'build/' + mycid
    mybuildroot = 'buildroot/image/'
    myosrelease = mybuildroot + '/etc/os-release'
    btrfs_do(myvolume)
    subprocess.run('mkosi', subprocess.DEVNULL)

    sys.stderr.write('Preparing image...\n')

    # Add container id to /etc/os-release
    with open(myosrelease, 'a') as f:
        f.write('BUILD_ID="' + mycid + '"\n')

    copy_tree(mybuildroot, myvolume, preserve_symlinks=1, update=1)
    shutil.rmtree('buildroot/image')


def die(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


def gen_cid():
    '''
    We generate a 16 character string for the container-id
    This is the maximum length that nspawn allows

    :return:
    '''


    return secrets.token_hex(16)


def main():
    #TODO: Remove this shit when done testing
    paruse_args()


if __name__ == "__main__":
    main()

