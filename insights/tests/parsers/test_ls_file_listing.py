# -*- coding: UTF-8 -*-
import doctest

from insights.parsers import ls as ls_module
from insights.parsers.ls import FileListing, LSlan, LSlHFiles
from insights.tests import context_wrap

SINGLE_DIRECTORY = """
ls: cannot access ' _non_existing_': No such file or directory
/etc/pki/tls:
total 32
drwxr-xr-x.  5 root root  4096 Jun 28  2017 .
drwxr-xr-x. 15 root root  4096 Aug 10 09:42 ..
lrwxrwxrwx.  1 root root    49 Jun 28  2017 cert.pem -> /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem
drwxr-xr-x.  2 root root  4096 Jun 28  2017 certs
drwxr-xr-x.  2 root root  4096 Mar 29  2017 misc
-rw-r--r--.  1 root root 10923 Feb  7  2017 openssl.cnf
drwxr-xr-x.  2 root root  4096 Feb  7  2017 private
"""

MULTIPLE_DIRECTORIES = """
/etc/sysconfig:
total 96
drwxr-xr-x.  7 0 0 4096 Jul  6 23:41 .
drwxr-xr-x. 77 0 0 8192 Jul 13 03:55 ..
drwxr-xr-x.  2 0 0   41 Jul  6 23:32 cbq
drwxr-xr-x.  2 0 0    6 Sep 16  2015 console
-rw-------.  1 0 0 1390 Mar  4  2014 ebtables-config
-rw-r--r--.  1 0 0   72 Sep 15  2015 firewalld
lrwxrwxrwx.  1 0 0   17 Jul  6 23:32 grub -> /etc/default/grub
lrwxrwxrwx.  1 0 0   17 Jul  6 23:32 grubX

/etc/rc.d/rc3.d:
total 4
drwxr-xr-x.  2 0 0   58 Jul  6 23:32 .
drwxr-xr-x. 10 0 0 4096 Sep 16  2015 ..
lrwxrwxrwx.  1 0 0   20 Jul  6 23:32 K50netconsole -> ../init.d/netconsole
lrwxrwxrwx.  1 0 0   17 Jul  6 23:32 S10network -> ../init.d/network
lrwxrwxrwx.  1 0 0   15 Jul  6 23:32 S97rhnsd -> ../init.d/rhnsd
"""

COMPLICATED_FILES = """
/tmp:
total 16
dr-xr-xr-x.  2 0 0     4096 Mar  4 16:19 .
dr-xr-xr-x. 10 0 0     4096 Mar  4 16:19 ..
-rw-r--r--.  1 0 0   123891 Aug 25  2015 config-3.10.0-229.14.1.el7.x86_64
lrwxrwxrwx.  1 0 0       11 Aug  4  2014 menu.lst -> ./grub.conf
brw-rw----.  1 0 6 253,  10 Aug  4 16:56 dm-10
crw-------.  1 0 0 10,  236 Jul 25 10:00 control
srw-------.  1 26214 17738 0 Oct 19 08:48 geany_socket.c46453c2
-rw-rw-r--.  1 24306 24306 13895 Oct 21 15:42 File name with spaces in it!
-rw-rw-r--.  1 24306 24306 13895 Oct 21 15:42 Unicode ÅÍÎÏÓÔÒÚÆ☃ madness.txt
drwxr-xr-x+  2 0 0       41 Jul  6 23:32 additional_ACLs
-rw-rw----.  1 0 6 253,  10 Aug  4 16:56 comma in size currently valid
brw-rw----.  1 0 6  1048576 Aug  4 16:56 block dev with no comma also valid
-rwxr-xr-x.  2 0 0     1024 Jul  6 23:32 file_name_ending_with_colon:
lrwxrwxrwx.  1 0 0       11 Aug  4  2014 link with spaces -> ../file with spaces
"""

SELINUX_DIRECTORY = """
/boot:
total 3
-rw-r--r--. root root system_u:object_r:boot_t:s0      config-3.10.0-267
drwxr-xr-x. root root system_u:object_r:boot_t:s0      grub2
-rw-r--r--. root root system_u:object_r:boot_t:s0      initramfs-0-rescue
"""

FILES_CREATED_WITH_SELINUX_DISABLED = """
/dev/mapper:
total 2
lrwxrwxrwx 1 0 0 7 Apr 27 05:34 lv_cpwtk001_data01 -> ../dm-7
lrwxrwxrwx 1 0 0 7 Apr 27 05:34 lv_cpwtk001_redo01 -> ../dm-8
"""

BAD_DIRECTORY_ENTRIES = """
dr-xr-xr-x.  2 0 0     4096 Mar  4 16:19 dir entry with no dir header
total 3

/badness:
    -rwxr-xr-x. 0 0    1 Sep 12 2010 indented entry
xr-xr--r--. 0 0        1 Sep 12  2010 bad file type
-rxr-xr-x.  0 0        1 Sep 12  2010 missing user w permission
-rwxr-xr-x  0 0        1 Sep 12  2010 missing ACL dot
-rw-r--r--. user with spaces group 2 Oct 3 2011 user with spaces
-rw-r--r--. user group with spaces 2 Oct 3 2011 group with spaces
dr-xr-xr-x. -42 -63 1271 Jan  6  2008 Negative user and group numbers
dr-xr-xr-x. 1 7 123, 124, 125 Jan 6 2008 Three comma blocks in size
brw-rw----. 1 0 6 123456 Aug 4 16:56 two size blocks
prw-rw----. 1000 1000  0  6 2007 Month missing
prw-rw----. 1000 1000  0 No 6 2007 Month too short
prw-rw----. 1000 1000  0 November 6 2007 Month too long
prw-rw----. 1000 1000  0 Nov  2007 Day too long
prw-rw----. 1000 1000  0 Nov 126 2007 Day too long
prw-rw----. 1000 1000  0 Nov 126  Year missing
prw-rw----. 1000 1000  0 Nov 126 20107 Year too long
prw-rw----. 1000 1000  0 Nov 12 :56 Missing hour
prw-rw----. 1000 1000  0 Nov 12 723:56 Hour too long
prw-rw----. 1000 1000  0 Nov 12 23: Missing minute
prw-rw----. 1000 1000  0 Nov 12 23:3 Minute too short
prw-rw----. 1000 1000  0 Nov 12 23:357 Minute too long
-rw------ 1 root root 762 Sep 23 002 permission too short
bash: ls: command not found
-rw------ 1 root root 762 Se
-rw------- 1 ro:t root 762 Sep 23 002 colon in uid
-rw------- 1 root r:ot 762 Sep 23 002 colon in gid
-rwasdfas- 1 root root 762 Sep 23 002 bad permissions block
-rwx/----- 1 root root 762 Sep 23 002 slash in permissions block
-rwx------ 1 root root 762 Sep 23 002 /slashes/in/filename
/rwasdfas- 1 root root 762 Sep 23 002 slash in file type and no colon on end
/usr/bin/ls: cannot access /boot/grub2/grub.cfg: No such file or directory
cannot access /boot/grub2/grub.cfg: No such file or directory
No such file or directory
adsf
"""

FILE_LISTING_DOC = '''
        /boot:
        total 187380
        dr-xr-xr-x.  3 0 0   4096 Mar  4 16:19 .
        dr-xr-xr-x. 19 0 0   4096 Jul 14 09:10 ..
        -rw-r--r--.  1 0 0 123891 Aug 25  2015 config-3.10.0-229.14.1.el7.x86_64

        /etc/sysconfig:
        total 96
        drwxr-xr-x.  7 0 0 4096 Jul  6 23:41 .
        drwxr-xr-x. 77 0 0 8192 Jul 13 03:55 ..
        drwxr-xr-x.  2 0 0   41 Jul  6 23:32 cbq
        drwxr-xr-x.  2 0 0    6 Sep 16  2015 console
        -rw-------.  1 0 0 1390 Mar  4  2014 ebtables-config
        -rw-r--r--.  1 0 0   72 Sep 15  2015 firewalld
        lrwxrwxrwx.  1 0 0   17 Jul  6 23:32 grub -> /etc/default/grub
'''

LS_FILE_PERMISSIONS_DOC = '''
/bin/ls: cannot access /boot/grub/grub.conf: No such file or directory
/bin/ls: cannot access fstab_mounted.devices: No such file or directory
/bin/ls: cannot access pvs.devices: No such file or directory
-rw-r--r--. 1 root  root      46 Apr 24  2024 /etc/redhat-release
-rw-r--r--. 1 liuxc wheel 664118 Feb 20 14:40 /var/log/messages
brw-rw----. 1 root  disk 252, 1 May 16 01:30 /dev/vda1
'''
# Note - should we test for anomalous but parseable entries?  E.g. block
# devices without a major/minor number?  Or non-devices that have a comma in
# the size?  Permissions that don't make sense?  Dates that don't make sense
# but still fit the patterns?  What should the parser do with such entries?


def test_single_directory():
    # ctx = context_wrap(SINGLE_DIRECTORY, path='ls_-la_.etc.pki.tls')
    ctx = context_wrap(SINGLE_DIRECTORY)
    dirs = FileListing(ctx)

    assert '/etc/pki/tls' in dirs
    assert '/etc/pki/tls/certs' not in dirs
    assert '/etc/pki' not in dirs
    assert '/etc' not in dirs
    assert dirs['/etc/pki/tls']['name'] == '/etc/pki/tls'

    assert dirs.files_of('/etc/pki/tls') == ['cert.pem', 'openssl.cnf']
    assert dirs.dirs_of('/etc/pki/tls') == ['.', '..', 'certs', 'misc', 'private']
    assert dirs.total_of('/etc/pki/tls') == 32
    assert dirs.files_of('non-exist') == []
    assert dirs.dirs_of('non-exist') == []
    assert dirs.total_of('non-exist') == 0


def test_multiple_directories():
    dirs = FileListing(context_wrap(MULTIPLE_DIRECTORIES, path='ls_-la_.etc'))

    assert '/etc/sysconfig' in dirs
    assert '/etc/rc.d/rc3.d' in dirs
    assert '/etc/rc.d/rc4.d' not in dirs

    esc = dirs['/etc/sysconfig']
    assert sorted(esc.keys()) == sorted(['entries', 'files', 'dirs', 'specials', 'total', 'name'])

    assert dirs.files_of('/etc/sysconfig') == ['ebtables-config', 'firewalld', 'grub', 'grubX']
    assert dirs.dirs_of('/etc/sysconfig') == ['.', '..', 'cbq', 'console']
    assert dirs.specials_of('/etc/sysconfig') == []
    assert dirs.files_of('non-exist') == []
    assert dirs.dirs_of('non-exist') == []
    assert dirs.specials_of('non-exist') == []
    assert dirs.listing_of('non-exist') == {}
    assert dirs.total_of('non-exist') == 0
    assert dirs.dir_contains('non-exist', 'test') is False
    assert dirs.dir_entry('non-exist', 'test') == {}

    # Testing the main features
    listing = dirs.listing_of('/etc/sysconfig')
    assert listing['..'] == {
        'type': 'd',
        'perms': 'rwxr-xr-x.',
        'links': 77,
        'owner': '0',
        'group': '0',
        'size': 8192,
        'date': 'Jul 13 03:55',
        'name': '..',
        'dir': '/etc/sysconfig',
    }
    assert listing['cbq'] == {
        'type': 'd',
        'perms': 'rwxr-xr-x.',
        'links': 2,
        'owner': '0',
        'group': '0',
        'size': 41,
        'date': 'Jul  6 23:32',
        'name': 'cbq',
        'dir': '/etc/sysconfig',
    }
    assert listing['firewalld'] == {
        'type': '-',
        'perms': 'rw-r--r--.',
        'links': 1,
        'owner': '0',
        'group': '0',
        'size': 72,
        'date': 'Sep 15  2015',
        'name': 'firewalld',
        'dir': '/etc/sysconfig',
    }
    assert listing['grub'] == {
        'type': 'l',
        'perms': 'rwxrwxrwx.',
        'links': 1,
        'owner': '0',
        'group': '0',
        'size': 17,
        'date': 'Jul  6 23:32',
        'name': 'grub',
        'link': '/etc/default/grub',
        'dir': '/etc/sysconfig',
    }

    listing = dirs.listing_of('/etc/rc.d/rc3.d')
    assert listing['..'] == {
        'type': 'd',
        'perms': 'rwxr-xr-x.',
        'links': 10,
        'owner': '0',
        'group': '0',
        'size': 4096,
        'date': 'Sep 16  2015',
        'name': '..',
        'dir': '/etc/rc.d/rc3.d',
    }
    assert listing['K50netconsole'] == {
        'type': 'l',
        'perms': 'rwxrwxrwx.',
        'links': 1,
        'owner': '0',
        'group': '0',
        'size': 20,
        'date': 'Jul  6 23:32',
        'name': 'K50netconsole',
        'link': '../init.d/netconsole',
        'dir': '/etc/rc.d/rc3.d',
    }

    assert dirs.total_of('/etc/sysconfig') == 96
    assert dirs.total_of('/etc/rc.d/rc3.d') == 4

    assert dirs.dir_contains('/etc/sysconfig', 'firewalld')
    assert dirs.dir_entry('/etc/sysconfig', 'grub') == {
        'type': 'l',
        'perms': 'rwxrwxrwx.',
        'links': 1,
        'owner': '0',
        'group': '0',
        'size': 17,
        'date': 'Jul  6 23:32',
        'name': 'grub',
        'link': '/etc/default/grub',
        'dir': '/etc/sysconfig',
    }

    assert dirs.path_entry('/etc/sysconfig/cbq') == {
        'type': 'd',
        'perms': 'rwxr-xr-x.',
        'links': 2,
        'owner': '0',
        'group': '0',
        'size': 41,
        'date': 'Jul  6 23:32',
        'name': 'cbq',
        'dir': '/etc/sysconfig',
    }
    assert dirs.path_entry('no_slash') is None
    assert dirs.path_entry('/') is None
    assert dirs.path_entry('/foo') is None
    assert dirs.path_entry('/etc/sysconfig/notfound') is None


def test_raw_entry_of_permissions_of():
    dirs = FileListing(context_wrap(MULTIPLE_DIRECTORIES, path='ls_-la_.etc'))

    raw_entry = 'drwxr-xr-x. 77 0 0 8192 Jul 13 03:55 ..'
    assert dirs.raw_entry_of('/etc/sysconfig', '..') == raw_entry
    assert dirs.permissions_of('/etc/sysconfig', '..').line == raw_entry

    raw_entry = 'drwxr-xr-x. 2 0 0 41 Jul  6 23:32 cbq'
    assert dirs.raw_entry_of('/etc/sysconfig', 'cbq') == raw_entry
    assert dirs.permissions_of('/etc/sysconfig', 'cbq').line == raw_entry

    raw_entry = '-rw-r--r--. 1 0 0 72 Sep 15  2015 firewalld'
    assert dirs.raw_entry_of('/etc/sysconfig', 'firewalld') == raw_entry
    assert dirs.permissions_of('/etc/sysconfig', 'firewalld').line == raw_entry

    raw_entry = 'lrwxrwxrwx. 1 0 0 17 Jul  6 23:32 grub -> /etc/default/grub'
    assert dirs.raw_entry_of('/etc/sysconfig', 'grub') == raw_entry
    assert dirs.permissions_of('/etc/sysconfig', 'grub').line == raw_entry
    # abnormal case, no '->' for links
    raw_entry = 'lrwxrwxrwx. 1 0 0 17 Jul  6 23:32 grubX'
    assert dirs.raw_entry_of('/etc/sysconfig', 'grubX') == raw_entry
    assert dirs.permissions_of('/etc/sysconfig', 'grubX').line == raw_entry
    # no such target file
    dirs.raw_entry_of('/etc/sysconfig', 'test') is None
    dirs.permissions_of('/etc/sysconfig', 'test') is None
    # no such dir
    dirs.raw_entry_of('/etc/test', 'grub') is None
    dirs.permissions_of('/etc/test', 'grub') is None

    # New input
    dirs = FileListing(context_wrap(COMPLICATED_FILES))

    raw_entry = 'brw-rw----. 1 0 6 253, 10 Aug  4 16:56 dm-10'
    assert dirs.raw_entry_of('/tmp', 'dm-10') == raw_entry
    assert dirs.permissions_of('/tmp', 'dm-10').line == raw_entry

    # New input
    dirs = FileListing(context_wrap(SELINUX_DIRECTORY))

    raw_entry = 'drwxr-xr-x. root root system_u:object_r:boot_t:s0 grub2'
    assert dirs.raw_entry_of('/boot', 'grub2') == raw_entry
    # no permissions_of test

    # New input
    dirs = FileListing(context_wrap(FILES_CREATED_WITH_SELINUX_DISABLED))
    raw_entry = 'lrwxrwxrwx 1 0 0 7 Apr 27 05:34 lv_cpwtk001_data01 -> ../dm-7'
    assert dirs.raw_entry_of('/dev/mapper', 'lv_cpwtk001_data01') == raw_entry
    assert dirs.permissions_of('/dev/mapper', 'lv_cpwtk001_data01').line == raw_entry


def test_complicated_directory():
    dirs = FileListing(context_wrap(COMPLICATED_FILES))

    # Test the things we expect to be different:
    listing = dirs.listing_of('/tmp')
    assert listing['config-3.10.0-229.14.1.el7.x86_64']['type'] == '-'
    assert listing['menu.lst']['type'] == 'l'
    assert listing['menu.lst']['link'] == './grub.conf'
    assert dirs.dir_entry('/tmp', 'dm-10') == {
        'type': 'b',
        'perms': 'rw-rw----.',
        'links': 1,
        'owner': '0',
        'group': '6',
        'major': 253,
        'minor': 10,
        'date': 'Aug  4 16:56',
        'name': 'dm-10',
        'dir': '/tmp',
    }
    assert listing['dm-10']['type'] == 'b'
    assert listing['dm-10']['major'] == 253
    assert listing['dm-10']['minor'] == 10
    assert listing['control']['type'] == 'c'
    assert listing['control']['major'] == 10
    assert listing['control']['minor'] == 236
    assert listing['geany_socket.c46453c2']['type'] == 's'
    assert listing['geany_socket.c46453c2']['size'] == 0
    assert listing['link with spaces']['type'] == 'l'
    assert listing['link with spaces']['link'] == '../file with spaces'

    # Check that things that _shouldn't_ be there _aren't_
    assert 'size' not in listing['dm-10']
    assert 'size' not in listing['control']

    # Tricky file names
    assert 'File name with spaces in it!' in listing
    assert 'Unicode ÅÍÎÏÓÔÒÚÆ☃ madness.txt' in listing
    assert 'file_name_ending_with_colon:' in listing
    assert dirs.dir_contains('/tmp', 'File name with spaces in it!')
    assert dirs.dir_contains('/tmp', 'Unicode ÅÍÎÏÓÔÒÚÆ☃ madness.txt')
    assert dirs.dir_contains('/tmp', 'file_name_ending_with_colon:')

    # For devices missing a comma in their 'size', size is also unconverted
    assert 'block dev with no comma also valid' in listing
    assert listing['block dev with no comma also valid']['size'] == 1048576
    assert 'major' not in listing['block dev with no comma also valid']
    assert 'minor' not in listing['block dev with no comma also valid']

    # Extended ACLs
    assert 'additional_ACLs' in listing
    assert listing['additional_ACLs']['perms'] == 'rwxr-xr-x+'


def test_selinux_directory():
    dirs = FileListing(context_wrap(SELINUX_DIRECTORY))

    # Test that one entry is exactly what we expect it to be.
    expected = {
        'type': 'd',
        'perms': 'rwxr-xr-x.',
        'owner': 'root',
        'group': 'root',
        'se_user': 'system_u',
        'se_role': 'object_r',
        'se_type': 'boot_t',
        'se_mls': 's0',
        'name': 'grub2',
        'dir': '/boot',
    }
    actual = dirs.dir_entry('/boot', 'grub2')
    assert actual == expected


def test_files_created_with_selinux_disabled():
    dirs = FileListing(context_wrap(FILES_CREATED_WITH_SELINUX_DISABLED))

    # Test that one entry is exactly what we expect it to be.
    assert dirs.dir_entry('/dev/mapper', 'lv_cpwtk001_data01') == {
        'group': '0',
        'name': 'lv_cpwtk001_data01',
        'links': 1,
        'perms': 'rwxrwxrwx',
        'owner': '0',
        'link': '../dm-7',
        'date': 'Apr 27 05:34',
        'type': 'l',
        'dir': '/dev/mapper',
        'size': 7,
    }


def test_doc_example():
    env = {
        'ls_lan': LSlan(context_wrap(FILE_LISTING_DOC)),
        'ls_files': LSlHFiles(context_wrap(LS_FILE_PERMISSIONS_DOC)),
    }
    failed, total = doctest.testmod(ls_module, globs=env)
    assert failed == 0
