from __future__ import print_function
from __future__ import absolute_import

import errno
import json
import os
import logging
import tempfile
import shutil
import sys
import atexit
from requests import ConnectionError

from .. import package_info
from . import collector
from insights.collector.constants import InsightsConstants as constants
from insights.collector.config import InsightsConfig
from insights.collector.auto_config import try_auto_configuration
from insights.collector.utilities import (write_data_to_file,
                        write_to_disk,
                        get_tags,
                        write_tags,
                        migrate_tags,
                        get_rhel_version,
                        get_parent_process)

NETWORK = constants.custom_network_log_level
logger = logging.getLogger(__name__)

from os.path import isfile
import sys
import json
import logging
import logging.handlers
import os
import time
import six

from insights.util.rpm_vercmp import version_compare

from .utilities import (
    generate_machine_id,
    write_to_disk,
    write_registered_file,
    write_unregistered_file,
    delete_cache_files,
    determine_hostname,
    get_version_info,
)
from .collection_rules import InsightsUploadConf
from .core_collector import CoreCollector
from .connection import InsightsConnection
from .support import registration_check
from .constants import InsightsConstants as constants

NETWORK = constants.custom_network_log_level
LOG_FORMAT = "%(asctime)s %(levelname)8s %(name)s:%(lineno)s %(message)s"
logger = logging.getLogger(__name__)


class RotatingFileHandlerWithUMask(logging.handlers.RotatingFileHandler, object):
    """logging.handlers.RotatingFileHandler subclass with a modified
    file permission mask.
    """

    def __init__(self, umask, *args, **kwargs):
        self._umask = umask
        super(RotatingFileHandlerWithUMask, self).__init__(*args, **kwargs)

    def _open(self):
        """
        Overrides the logging library "_open" method with a custom
        file permission mask.
        """
        default_umask = os.umask(self._umask)
        try:
            return super(RotatingFileHandlerWithUMask, self)._open()
        finally:
            os.umask(default_umask)


class FileHandlerWithUMask(logging.FileHandler, object):
    """logging.FileHandler subclass with a modified
    file permission mask.
    """

    def __init__(self, umask, *args, **kwargs):
        self._umask = umask
        super(FileHandlerWithUMask, self).__init__(*args, **kwargs)

    def _open(self):
        """
        Overrides the logging library "_open" method with a custom
        file permission mask.
        """
        default_umask = os.umask(self._umask)
        try:
            return super(FileHandlerWithUMask, self)._open()
        finally:
            os.umask(default_umask)


def do_log_rotation():
    handler = get_file_handler()
    return handler.doRollover()


def get_file_handler(config):
    '''
    Sets up the logging file handler.
    Returns:
        RotatingFileHandler - client rpm version is older than 3.2.0.
        FileHandler - client rpm version is 3.2.0 or newer.
    '''
    log_file = config.logging_file
    log_dir = os.path.dirname(log_file)
    if not log_dir:
        log_dir = os.getcwd()
    elif not os.path.exists(log_dir):
        os.makedirs(log_dir, 0o700)
    # ensure the legacy rotating file handler is only used in older client versions
    # or if there is a problem retrieving the rpm version.
    rpm_version = get_version_info()['client_version']
    if not rpm_version or (
        version_compare(rpm_version, constants.rpm_version_before_logrotate) < 0
    ):
        file_handler = RotatingFileHandlerWithUMask(0o077, log_file, backupCount=3)
    else:
        file_handler = FileHandlerWithUMask(0o077, log_file)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return file_handler


def get_console_handler(config):
    if config.silent:
        target_level = logging.FATAL
    elif config.verbose:
        target_level = logging.DEBUG
    elif config.net_debug:
        target_level = NETWORK
    elif config.quiet:
        target_level = logging.ERROR
    else:
        target_level = logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(target_level)

    log_format = LOG_FORMAT if config.verbose else "%(message)s"
    handler.setFormatter(logging.Formatter(log_format))

    return handler


def configure_level(config):
    config_level = 'NETWORK' if config.net_debug else config.loglevel
    config_level = 'DEBUG' if config.verbose else config.loglevel

    init_log_level = logging.getLevelName(config_level)
    if type(init_log_level) in six.string_types:
        print("Invalid log level %s, defaulting to DEBUG" % config_level)
        init_log_level = logging.DEBUG

    logger.setLevel(init_log_level)
    logging.root.setLevel(init_log_level)

    if not config.verbose:
        logging.getLogger('insights.core.dr').setLevel(logging.WARNING)


def set_up_logging(config):
    logging.addLevelName(NETWORK, "NETWORK")
    if len(logging.root.handlers) == 0:
        logging.root.addHandler(get_console_handler(config))
        logging.root.addHandler(get_file_handler(config))
        configure_level(config)
        logger.debug("Logging initialized")


def __cleanup_local_files():
    write_unregistered_file()
    delete_cache_files()
    write_to_disk(constants.machine_id_file, delete=True)
    logger.debug('Unregistered and removed machine-id')


def get_machine_id():
    return generate_machine_id()


def get_branch_info(config):
    """
    Get branch info for a system
    returns (dict): {'remote_branch': -1, 'remote_leaf': -1}
    """
    # in the case we are running on offline mode
    # or we are analyzing a running container/image
    # or tar file, mountpoint, simply return the default branch info
    if config.offline:
        return constants.default_branch_info
    return config.branch_info


def collect(config):
    """
    All the heavy lifting done here
    """
    pc = InsightsUploadConf(config)
    dc = Collector(config)

    rm_conf = {}
    # Do not print collection relevant messages for compliance apiv2 options
    if not (config.compliance_policies or config.compliance_assign or config.compliance_unassign):
        rm_conf = pc.get_rm_conf()
        logger.info(
            'Starting to collect Insights data for %s' % determine_hostname(config.display_name)
        )

    dc.run_collection(rm_conf)

    return dc.done()


def get_connection(config):
    return InsightsConnection(config)


class Collector(object):

    def __init__(self, **kwargs):
        """
        The Insights client interface
        """
        self.config = InsightsConfig()

        self.set_up_logging()
        logger.debug(
            "path={path}, version={version}, arguments={arguments}".format(
                path=__file__,
                version=self.version(),
                arguments=" ".join(sys.argv[1:]),
            )
        )
        try_auto_configuration(self.config)
        self.initialize_tags()
        self.connection = None
        self.tmpdir = None

    def _net(func):
        def _init_connection(self, *args, **kwargs):
            # setup a request session
            if not self.config.offline and not self.connection:
                self.connection = client.get_connection(self.config)
            return func(self, *args, **kwargs)
        return _init_connection

    def set_up_logging(self):
        return client.set_up_logging(self.config)

    def version(self):
        return "%s-%s" % (package_info["VERSION"], package_info["RELEASE"])

    @_net
    def branch_info(self):
        """
            returns (dict): {'remote_leaf': -1, 'remote_branch': -1}
        """
        return client.get_branch_info(self.config, self.connection)

    def delete_tmpdir(self):
        if self.tmpdir:
            logger.debug("Deleting temp directory %s." % (self.tmpdir))
            shutil.rmtree(self.tmpdir, True)

    @_net
    def collect(self):
        # return collection results
        tar_file = client.collect(self.config)

        # it is important to note that --to-stdout is utilized via the wrapper RPM
        # this file is received and then we invoke shutil.copyfileobj
        return tar_file

    def copy_to_output_dir(self, insights_archive):
        '''
        Copy the collected data from temp to the directory
        specified by --output-dir

        Parameters:
            insights_archive - the path to the collected dir
        '''
        logger.debug('Copying collected data from %s to %s',
                     insights_archive, self.config.output_dir)
        try:
            shutil.copytree(insights_archive, self.config.output_dir)
        except OSError as e:
            if e.errno == 17:
                # dir exists already, see if it's empty
                if os.listdir(self.config.output_dir):
                    # we should never get here because of the check in config.py, but just in case
                    logger.error('ERROR: Could not write data to %s.', self.config.output_dir)
                    logger.error(e)
                    return
                else:
                    # if it's empty, copy the contents to it
                    for fil in os.listdir(insights_archive):
                        src_path = os.path.join(insights_archive, fil)
                        dst_path = os.path.join(self.config.output_dir, fil)
                        try:
                            if os.path.isfile(src_path):
                                shutil.copyfile(src_path, dst_path)
                            elif os.path.isdir(src_path):
                                shutil.copytree(src_path, dst_path)
                        except OSError as e:
                            logger.error(e)
                            # in case this happens partway through let the user know
                            logger.warning('WARNING: Directory copy may be incomplete.')
                            return
            else:
                # some other error
                logger.error(e)
                return
        logger.info('Collected data copied to %s', self.config.output_dir)

    def copy_to_output_file(self, insights_archive):
        '''
        Copy the collected archive from temp to the file
        specified by output-file

        insights_archive - the path to the collected archive
        '''
        logger.debug('Copying archive from %s to %s',
                     insights_archive, self.config.output_file)
        try:
            shutil.copyfile(insights_archive, self.config.output_file)
        except OSError as e:
            # file exists already
            logger.error('ERROR: Could not write data to %s', self.config.output_file)
            logger.error(e)
            return
        logger.info('Collected data copied to %s', self.config.output_file)

    def initialize_tags(self):
        '''
        Initialize the tags file if needed
        '''
        # migrate the old file if necessary
        migrate_tags()

        # initialize with group if group was specified
        if self.config.group:
            tags = get_tags()
            if tags is None:
                tags = {}
            tags["group"] = self.config.group
            write_tags(tags)


def _write_pid_files():
    for file, content in (
        (constants.pidfile, str(os.getpid())),  # PID in case we need to ping systemd
        (constants.ppidfile, get_parent_process())  # PPID so that we can grab the client execution method
    ):
        write_to_disk(file, content=content)
        atexit.register(write_to_disk, file, delete=True)
