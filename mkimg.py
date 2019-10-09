#!/usr/bin/python3

import argparse
import subprocess
import sys
import os
import textwrap
import shutil
import secrets
import time
import fileinput
from pathlib import Path
from distutils.dir_util import copy_tree

MKIMG_COMMANDS = ('init', 'info', 'build', 'clean', 'destroy', 'summary', 'compose')
__version__ = '2019.1'


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
        clean()
    elif parser.verb == 'destroy':
        clean(destroy=True)
    elif parser.verb == 'info':
        info()
    elif parser.verb == 'compose':
        compose()
    else:
        return parser.verb


def set_ownership(path):
    '''
    Fix ownership after sudo calls...

    :param path:
    :return:
    '''
    sudo_uid = int(os.environ['SUDO_UID'])
    sudo_gid = int(os.environ['SUDO_GID'])

    return os.chown(path, sudo_uid, sudo_gid)


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


def clean(destroy=False):
    '''
    Remove working files.  This funciton mirrors mkosi clean..

    :return:
    '''

    try:
        check_root()
        mysubvols = os.listdir('build')
        mydirs = ['streams', 'services', 'buildroot']
        myfiles = ['mkosi.default', 'mkosi.rootpw', '.init.lock']

    except FileNotFoundError:
        die('No files found to remove')

    if destroy:
        try:
            for file in myfiles:
                os.remove(file)

            for directory in mydirs:
                shutil.rmtree(directory)

            # Force remove btrfs subvolumes
            for volume in mysubvols:
                btrfs_do('build/' + volume, action='delete')
            shutil.rmtree('build')

        except FileNotFoundError:
            die('No files found to remove')

    else:
        try:
            # Force remove btrfs subvolumes
            if len(mysubvols) == 0:
                sys.stderr.write('No volumes found for removal.\n')
            else:
                for volume in mysubvols:
                    btrfs_do('build/' + volume, action='delete')
                    sys.stderr.write(f'Removing output volume {volume}.\n')

        except FileNotFoundError:
            die('No files found to remove')


def init():
    '''
    This function conducts the pre-flight checks and generates the required project structure.

    build/ (btrfs subvol)
    mkosi.default
    mkosi.rootpw
    mkosi.cache/
    streams/
    buildroot/

    :return:
    '''

    check_root()

    mydirs = ['streams', 'services', 'buildroot', 'mkosi.cache']
    myfiles = ['mkosi.default', 'mkosi.rootpw', '.init.lock']

    if check_init():
        die('Workspace is already initialized. Operation halted.')
    preflight_checks()
    sys.stderr.write('\nINITIALIZING PROJECT SPACE:\n')

    try:
        btrfs_do('build')
        set_ownership('build')
        sys.stderr.write('          Created build subvolume\n')
    except OSError:
        die('Failed to create build subvolume')

    for directory in mydirs:
        try:
            os.mkdir(directory)
            set_ownership(directory)
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
        set_ownership('mkosi.default')
        sys.stderr.write('          Created mkosi.default file\n')

        # create mkosi rootpw file
        with open('mkosi.rootpw', 'w') as f:
            f.write(mkrootpw)
            f.close()
        os.chmod('mkosi.rootpw', 0o600)
        set_ownership('mkosi.rootpw')
        sys.stderr.write('          Created mkosi.default file\n')

        # Create init lock file
        Path('.init.lock').touch()
        set_ownership('.init.lock')

    except OSError:
        die('Error in mkosi template file create')


def info():
    mydirs = ['build', 'streams', 'services']
    preflight_checks()

    sys.stderr.write('PROJECT LISTING:\n')
    for directory in mydirs:
        mydir = os.listdir(directory)
        for item in mydir:
            sys.stderr.write('          ' + directory + '/' + item + '\n')


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


def btrfs_do(volume, command='subvol', action='create', *args):
    '''
    BTRFS utility function

    :param volume:
    :param command:
    :param action:
    :return:
    '''
    try:
        butter = subprocess.run(['btrfs', command, action, volume, *args], stdout=subprocess.DEVNULL)

    except OSError as e:
        print(str(e))
        die('Error handling BTRFS object.')

    return butter


def compress_subvol(subvol, dest):
    '''
    This compresses the subvol into a zstd sendstreamm at dest

    :param subvol:
    :return None:

    '''

    try:
        proc_send = subprocess.Popen(['btrfs', 'send', subvol],
                                     stdout=subprocess.PIPE, shell=False
                                     )
        proc_stream = subprocess.Popen(['zstd', '-v', '-o', dest],
                                       stdin=proc_send.stdout, stdout=subprocess.PIPE, shell=False
                                       )
        proc_send.stdout.close()
        proc_stream.communicate()[0]
        set_ownership(dest)
    except OSError as e:
        print(str(e))
        die('Error in subvolume compress')


def timeit(method):
    def timed(*args, **kw):
        tstart = time.time()
        result = method(*args, **kw)
        telapsed = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            sys.stderr.write(f'Build time: {(((telapsed - tstart) * 1000) / 1000)} s\n')
        return result

    return timed


@timeit
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
    mysendstream = 'streams/' + mycid + '.sendstream.zst'
    btrfs_do(myvolume)
    subprocess.run('mkosi', subprocess.DEVNULL)

    sys.stderr.write('Preparing image...\n')
    sys.stderr.write('Copying buildroot...\n')
    copy_tree(mybuildroot, myvolume, preserve_symlinks=1, update=1)
    osrelease(mycid)
    shutil.rmtree('buildroot/image')

    # Set subvolume to read-only mode for transport
    sys.stderr.write('Preparing subvol for transport...\n')
    btrfs_do(myvolume, 'property', 'set', 'ro', 'true')

    compress_subvol(myvolume, mysendstream)
    sys.stderr.write('Image build complete!!\n')


@timeit
def compose():
    '''
    Create sendstream diffs from a parent subvol.

    Generate snapshot ID
    Snapshot from parent
    Add PARENT_BUILD_ID and PARENT_ID to /etc/os-release
    Do work on snapshot vol
    Set snapshot to read-only
    Send btrfs parent/child diff to .zst file

    :return:
    '''
    try:
        prefix = 'build/'
        parent_id = '57136fb8e1c02d0da9ae2b441ec4aa80'
        parent_volume = prefix + parent_id
        mycid = gen_cid()
        myvolume = prefix + mycid

        # Generate snapshot from parent
        btrfs_do(parent_volume, 'subvolume', 'snapshot', myvolume)

        # Update the os-release file to reflect the new container ids
        osrelease(mycid, update=True)
        osrelease(mycid)

        # TODO: Read and execute commands from BUILD file
        sys.stderr.write(f'Created image {mycid} from {parent_id}\n')

        # Prepare to send to stream
        btrfs_do(myvolume, 'property', 'set', 'ro', 'true')



    except OSError as e:
        print(str(e))


def osrelease(cid, update=False):
    '''
    This updates /etc/os-release within the container

    :param arg:
    :return:
    '''

    subvol = 'build/' + cid
    myosrelease = subvol +'/etc/os-release'

    if update:
        for line in fileinput.input([myosrelease], inplace=True):
            print(line.replace('BUILD_ID', 'PARENT_ID'), end='')

    else:
        with open(myosrelease, 'a') as f:
            f.write('BUILD_ID="' + cid + '"\n')


def die(message):
    sys.stderr.write(message + "\n")
    sys.exit(1)


def gen_cid():
    '''
    We generate a 32 character string for the container-id.
    This id is also added to os-release as BUILD_ID

    :return:
    '''

    return secrets.token_hex(16)


def main():
    paruse_args()


if __name__ == "__main__":
    main()

