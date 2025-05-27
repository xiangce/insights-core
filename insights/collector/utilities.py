"""
Utility functions
"""

from __future__ import absolute_import
import datetime
import errno
import json
import logging
import os
import shlex
import six
import stat
import sys
import tarfile
import threading
import time
import uuid
import yaml

from subprocess import Popen, PIPE, STDOUT

try:
    from yaml import CDumper as Dumper
except ImportError:
    from yaml import Dumper

from insights import package_info
from insights.collector import cert_auth
from insights.collector.constants import InsightsConstants as constants

from insights.core.context import Context
from insights.parsers.os_release import OsRelease
from insights.parsers.redhat_release import RedhatRelease
from insights.util.hostname import determine_hostname  # noqa: F401

logger = logging.getLogger(__name__)


def get_time():
    return datetime.datetime.isoformat(datetime.datetime.now())


def correct_format(parsed_data, expected_keys, filename):
    '''
    Ensure the parsed file matches the needed format
    Returns True, <message> on error
    Returns False, None on success
    '''

    # validate keys are what we expect
    def is_list_of_strings(data):
        '''
        Helper function for correct_format()
        '''
        if data is None:
            # nonetype, no data to parse. treat as empty list
            return True
        if not isinstance(data, list):
            return False
        for l in data:
            if not isinstance(l, six.string_types):
                return False
        return True

    keys = parsed_data.keys()
    invalid_keys = set(keys).difference(expected_keys)
    if invalid_keys:
        return True, (
            'Unknown section(s) in %s: ' % filename
            + ', '.join(invalid_keys)
            + '\nValid sections are '
            + ', '.join(expected_keys)
            + '.'
        )

    # validate format (lists of strings)
    for k in expected_keys:
        if k in parsed_data:
            if k == 'patterns' and isinstance(parsed_data['patterns'], dict):
                if 'regex' not in parsed_data['patterns']:
                    return (
                        True,
                        'Patterns section contains an object but the "regex" key was not specified.',
                    )
                if 'regex' in parsed_data['patterns'] and len(parsed_data['patterns']) > 1:
                    return True, 'Unknown keys in the patterns section. Only "regex" is valid.'
                if not is_list_of_strings(parsed_data['patterns']['regex']):
                    return True, 'regex section under patterns must be a list of strings.'
                continue
            if not is_list_of_strings(parsed_data[k]):
                return True, '%s section must be a list of strings.' % k
    return False, None


def verify_permissions(f):
    '''
    Verify 600 permissions on a file
    '''
    mode = stat.S_IMODE(os.stat(f).st_mode)
    if not mode == 0o600:
        raise RuntimeError("Invalid permissions on %s. " "Expected 0600 got %s" % (f, oct(mode)))
    logger.debug("Correct file permissions on %s", f)


def write_to_disk(filename, delete=False, content=None):
    """
    Write filename out to disk
    """
    if not os.path.exists(os.path.dirname(filename)):
        return
    if content is None:
        content = get_time()

    if delete:
        if os.path.lexists(filename):
            logger.debug("Removing '%s'" % filename)
            try:
                os.remove(filename)
            except OSError as err:
                # Only raise the exception if it's not
                # a missing file error (ENOENT), which can be
                # ignored since nothing needs to be removed.
                if err.errno != errno.ENOENT:
                    raise err
    else:
        logger.debug("Writing '%s'" % filename)
        with open(filename, 'wb') as f:
            f.write(content.encode('utf-8'))


def generate_machine_id(new=False, destination_file=constants.machine_id_file):
    """Generate a machine-id if /etc/insights-client/machine-id does not exist.

    :param new: Force generate a new ID.
    :type new: bool
    :param destination_file: Path to the file the ID should be written to.
    :type destination_file: str

    :returns: The machine ID
    :rtype: str
    """
    machine_id = None  # type: str | None

    if os.path.isfile(destination_file) and not new:
        with open(destination_file, "r") as f:
            machine_id = f.read()
        logger.debug("Using existing machine-id: '%s'." % machine_id)

    if not machine_id:
        machine_id = _get_rhsm_identity()
        if machine_id:
            logger.debug("Using subscription-manager identity as machine-id: '%s'." % machine_id)
            write_to_disk(destination_file, content=machine_id)

    if not machine_id:
        machine_id = str(uuid.uuid4())
        logger.debug("Creating fresh machine-id: '%s'." % machine_id)
        write_to_disk(destination_file, content=machine_id)
    try:
        # Old versions (redhat-access-insights) could save the UUID without hyphens,
        # and that could mess up Inventory via e.g. `insights-client --check-results`.
        # See RHBZ#1998560 for more details.
        return str(uuid.UUID(str(machine_id).strip(), version=4))
    except ValueError as exc:
        logger.error("Invalid machine ID: '%s'." % machine_id)
        logger.error("Error details: %s", str(exc))
        logger.error(
            "Please delete the file '%s' and rerun the client with '--register'." % destination_file
        )
        sys.exit(constants.sig_kill_bad)


def machine_id_exists(destination_file=constants.machine_id_file):
    """
    Get the machine-id or None if /etc/insights-client/machine-id it does not exists
    """
    return os.path.isfile(destination_file)


def write_data_to_file(data, filepath):
    '''
    Write data to file
    '''
    try:
        os.makedirs(os.path.dirname(filepath), 0o700)
    except OSError:
        pass

    write_to_disk(filepath, content=data)


def _get_rhsm_identity():
    """Get the subscription-manager identity certificate UUID.

    :returns: The subscription-manager UUID, or None if not found.
    :rtype: str | None
    """
    if cert_auth.RHSM_CONFIG is None:
        return None

    try:
        cert = cert_auth.rhsmCertificate.read()  # type: cert_auth.rhsmCertificate
        subscription_manager_uuid = cert.getConsumerId()  # type: str
    except Exception:
        return None

    logger.debug("Found subscription-manager UUID in '%s/%s'.", cert.PATH, cert.CERT)
    return subscription_manager_uuid


def run_command_get_output(cmd):
    proc = Popen(shlex.split(cmd), stdout=PIPE, stderr=STDOUT)
    stdout, stderr = proc.communicate()

    return {'status': proc.returncode, 'output': stdout.decode('utf-8', 'ignore')}


def modify_config_file(updates):
    '''
    Update the config file with certain things
    '''
    cmd = '/bin/sed '
    for key in updates:
        cmd = cmd + '-e \'s/^#*{key}.*=.*$/{key}={value}/\' '.format(key=key, value=updates[key])
    cmd = cmd + constants.default_conf_file
    status = run_command_get_output(cmd)
    write_to_disk(constants.default_conf_file, content=status['output'])


def get_version_info():
    '''
    Get the insights client and core versions for archival
    '''
    version_info = {}
    version_info['core_version'] = '%s-%s' % (package_info['VERSION'], package_info['RELEASE'])
    version_info['client_version'] = None
    return version_info


def get_egg_version_tuple():
    '''
    Return the core egg version as a tuple of integers.
    E.g. for insights-core-3.5.25-1, returns (3, 5, 25)
    '''
    egg_ver = get_version_info()['core_version'].split('-')[0]
    return tuple([int(i) for i in egg_ver.split('.')])


def print_egg_versions():
    '''
    Log all available eggs' versions
    '''
    versions = get_version_info()
    logger.debug('Client version: %s', versions['client_version'])
    logger.debug('Core version: %s', versions['core_version'])
    logger.debug('All egg versions:')
    eggs = [
        os.getenv('EGG'),
        '/var/lib/insights/newest.egg',
        '/var/lib/insights/last_stable.egg',
        '/etc/insights-client/rpm.egg',
    ]
    if not sys.executable:
        logger.debug('Python executable not found.')
        return

    for egg in eggs:
        if egg is None:
            logger.debug('ENV egg not defined.')
            continue
        if not os.path.exists(egg):
            logger.debug('%s not found.', egg)
            continue
        try:
            proc = Popen(
                [
                    sys.executable,
                    '-c',
                    'from insights import package_info; print(\'%s-%s\' % (package_info[\'VERSION\'], package_info[\'RELEASE\']))',
                ],
                env={'PYTHONPATH': egg, 'PATH': os.getenv('PATH')},
                stdout=PIPE,
                stderr=STDOUT,
            )
        except OSError:
            logger.debug('Could not start python.')
            return
        stdout, stderr = proc.communicate()
        exit_code = proc.wait()

        if exit_code == 0:
            version = stdout.decode('utf-8', 'ignore').strip()
            logger.debug('%s: %s', egg, version)
        else:
            logger.debug('%s: Could not read egg version.', egg)


def read_pidfile():
    '''
    Read the pidfile we wrote at launch
    '''
    pid = None
    try:
        with open(constants.pidfile) as pidfile:
            pid = pidfile.read()
    except IOError:
        logger.debug('Could not open pidfile for reading.')
    return pid


def _systemd_notify(pid):
    '''
    Ping the systemd watchdog with the main PID so that
    the watchdog doesn't kill the process
    '''
    try:
        proc = Popen(['/usr/bin/systemd-notify', '--pid=' + str(pid), 'WATCHDOG=1'])
    except OSError as e:
        logger.debug('Could not launch systemd-notify: %s', str(e))
        return False
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        logger.debug('systemd-notify returned %s', proc.returncode)
        return False
    return True


def systemd_notify_init_thread():
    '''
    Use a thread to periodically ping systemd instead
    of calling it on a per-command basis
    '''
    pid = read_pidfile()
    if not pid:
        logger.debug('No PID specified.')
        return
    if not os.getenv('NOTIFY_SOCKET'):
        # running standalone, not via systemd job
        return
    if not os.path.exists('/usr/bin/systemd-notify'):
        # RHEL 6, no systemd
        return

    def _sdnotify_loop():
        while True:
            # run sdnotify every 30 seconds
            if not _systemd_notify(pid):
                # end the loop if something goes wrong
                break
            time.sleep(30)

    sdnotify_thread = threading.Thread(target=_sdnotify_loop, args=())
    sdnotify_thread.daemon = True
    sdnotify_thread.start()


def load_yaml(filename):
    try:
        with open(filename) as f:
            loaded_yaml = yaml.safe_load(f)
        if loaded_yaml is None:
            logger.debug('%s is empty.', filename)
            return {}
    except (yaml.YAMLError, yaml.parser.ParserError) as e:
        # can't parse yaml from conf
        raise RuntimeError(
            'ERROR: Cannot parse %s.\n'
            'If using any YAML tokens such as [] in an expression, '
            'be sure to wrap the expression in quotation marks.\n\nError details:\n%s\n'
            % (filename, e)
        )
    if not isinstance(loaded_yaml, dict):
        # loaded data should be a dict with at least one key
        raise RuntimeError('ERROR: Invalid YAML loaded.')
    return loaded_yaml


def get_tags(tags_file_path=constants.default_tags_file):
    '''
    Load tag data from the tags file.

    Returns: a dict containing tags defined on the host.
    '''
    tags = None

    if os.path.isfile(tags_file_path):
        try:
            tags = load_yaml(tags_file_path)
        except RuntimeError:
            logger.error("Invalid YAML. Unable to load %s", tags_file_path)
            return None
    else:
        logger.debug("%s does not exist", tags_file_path)

    return tags


def write_tags(tags, tags_file_path=constants.default_tags_file):
    """
    Writes tags to tags_file_path

    Arguments:
      - tags (dict): the tags to write
      - tags_file_path (string): path to which tag data will be written

    Returns: None
    """
    with open(tags_file_path, mode="w+") as f:
        data = yaml.dump(tags, Dumper=Dumper, default_flow_style=False)
        f.write(data)


def migrate_tags():
    '''
    We initially released the tags feature with the tags file set as
    tags.conf, but soon after switched it over to tags.yaml. There may be
    installations out there with tags.conf files, so rename the files.
    '''
    tags_conf = os.path.join(constants.default_conf_dir, 'tags.conf')
    tags_yaml = os.path.join(constants.default_conf_dir, 'tags.yaml')

    if os.path.exists(tags_yaml):
        # current default file exists, do nothing
        return
    if os.path.exists(tags_conf):
        # old file exists and current does not
        logger.info(
            'Tags file %s detected. This filename is deprecated; please use %s. The file will be renamed automatically.',
            tags_conf,
            tags_yaml,
        )
        try:
            os.rename(tags_conf, tags_yaml)
        except OSError as e:
            logger.error(e)


def get_parent_process():
    '''
    Get parent process of the client

    Returns: string
    '''
    ppid = os.getppid()
    output = run_command_get_output('cat /proc/%s/status' % ppid)
    if output['status'] == 0:
        name = output['output'].splitlines()[0].split('\t')[1]
        return name
    else:
        return "unknown"


def _read_file(path):
    # type: (str) -> list[str]
    with open(path, mode="r") as f:
        return f.readlines()


def os_release_info():
    '''
    Use insights-core to fetch the os-release or redhat-release info

    Returns a tuple of OS name and version
    '''
    os_family = "Unknown"
    os_release = ""
    for p in ["/etc/os-release", "/etc/redhat-release"]:
        try:
            data = _read_file(p)  # type: list[str]

            ctx = Context(content=data, path=p, relative_path=p)
            if p == "/etc/os-release":
                rls = OsRelease(ctx)
                os_family = rls.data.get("NAME")
                os_release = rls.data.get("VERSION_ID")
            elif p == "/etc/redhat-release":
                rls = RedhatRelease(ctx)
                os_family = rls.product
                os_release = rls.version
            break
        except IOError:
            continue
        except Exception as e:
            logger.warning("Failed to detect OS version: %s", e)
    return os_family, os_release


def get_rhel_version():
    # type: () -> int
    """Reads /etc/os-release to determine RHEL version.

    For RHEL, the major version is always returned.

    For CentOS, the major version is always returned.

    For Fedora, the latest known RHEL version is returned.
    RHEL 10 was branched from Fedora 40; until RHEL 11 is branched,
    this method returns `10` for all Fedora versions.

    :returns: Major RHEL version (or an equivalent for non-RHEL systems)
    :raises ValueError: Version could not be determined.
    """
    distribution, release = os_release_info()
    if distribution == "Unknown":
        raise ValueError("Could not determine distribution family.")
    if release == "":
        raise ValueError("Could not determine version of '{}'.".format(distribution))

    _distribution = distribution.lower()  # type: str
    if _distribution.startswith("red hat enterprise linux") or _distribution.startswith("centos"):
        version = int(release.split(".")[0])
    elif _distribution.startswith("fedora"):
        version = 10
    else:
        raise ValueError("Unknown distribution '{}'.".format(distribution))

    if "red hat enterprise linux" not in _distribution:
        logger.debug("'{}' version '{}' matches RHEL {}.".format(distribution, release, version))
    return version


def largest_spec_in_archive(archive_file):
    logger.info("Checking for large files...")
    tar_file = tarfile.open(archive_file, 'r')
    largest_fsize = 0
    largest_file_name = ""
    largest_spec = ""
    # get the name of the archive
    name = os.path.basename(archive_file).split(".tar.gz")[0]
    # get the archives from inside meta_data directory
    metadata_top = os.path.join(name, "meta_data/")
    data_top = os.path.join(name, "data")
    for file in tar_file.getmembers():
        if metadata_top in file.name:
            file_extract = tar_file.extractfile(file.name)
            specs_metadata = json.load(file_extract)
            results = specs_metadata.get("results", [])
            if not results:
                continue
            if not isinstance(results, list):
                # specs with only one resulting file are not in list form
                results = [results]
            for result in results:
                # get the path of the spec result and check its filesize
                fname = result.get("object", {}).get("relative_path")
                abs_fname = os.path.join('.', data_top, fname)
                # get the archives from inside data directory
                data_file = tar_file.getmember(abs_fname)
                if data_file.size > largest_fsize:
                    largest_fsize = data_file.size
                    largest_file_name = fname
                    largest_spec = specs_metadata["name"]
    return (largest_file_name, largest_fsize, largest_spec)


def size_in_mb(num_bytes):
    return float(num_bytes) / (1024 * 1024)
