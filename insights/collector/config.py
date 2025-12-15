from __future__ import absolute_import

import argparse
import copy
import logging
import os
import six

from six.moves import configparser as ConfigParser

from insights.cleaner import DEFAULT_OBFUSCATIONS
from insights.client.utilities import get_rhel_version, get_egg_version_tuple
from insights.client.constants import InsightsConstants as constants
from insights.specs.manifests import manifests, content_types
from insights.util import parse_bool

logger = logging.getLogger(__name__)


DEFAULT_OPTS = {
    'base_url': {
        # non-CLI
        'default': constants.base_url
    },
    'branch_info': {
        # non-CLI
        'default': constants.default_branch_info
    },
    'branch_info_url': {
        # non-CLI
        'default': None
    },
    'cert_verify': {
        # non-CLI
        'default': None,
    },
    'cmd_timeout': {
        # non-CLI
        'default': constants.default_cmd_timeout
    },
    'manifest': {
        'default': None,
        'opt': ['--manifest'],
        'help': 'Collect using the provided manifest',
        'action': 'store',
        'group': 'actions',
        'dest': 'manifest',
    },
    'build_packagecache': {
        'default': False,
        'opt': ['--build-packagecache'],
        'help': 'Refresh the system package manager cache',
        'action': 'store_true',
        'group': 'actions',
    },
    'compliance': {
        'default': False,
        'opt': ['--compliance'],
        'help': 'Scan the system using openscap and upload the report',
        'action': 'store_true',
        'group': 'actions',
    },
    'compliance_policies': {
        'default': False,
        'opt': ['--compliance-policies'],
        'help': 'List the compliance policies assignable to the system',
        'action': 'store_true',
        'group': 'actions',
    },
    'compliance_assign': {
        'default': None,
        'opt': ['--compliance-assign'],
        'help': 'Assign the system to a compliance policy with the specified ID',
        'action': 'store',
        'group': 'actions',
    },
    'compliance_unassign': {
        'default': None,
        'opt': ['--compliance-unassign'],
        'help': 'Unassign the system from a compliance policy with the specified ID',
        'action': 'store',
        'group': 'actions',
    },
    'compressor': {
        'default': 'gz',
        'opt': ['--compressor'],
        'help': argparse.SUPPRESS,
        'action': 'store',
    },
    'conf': {
        'default': constants.default_conf_file,
        'opt': ['--conf', '-c'],
        'help': 'Pass a custom config file',
        'action': 'store',
    },
    'debug': {
        'default': False,  # Used by client wrapper script
        'opt': ['--debug-phases'],
        'help': argparse.SUPPRESS,
        'action': 'store_true',
        'dest': 'debug',
    },
    'keep_archive': {
        'default': False,
        'opt': ['--keep-archive'],
        'help': 'Store archive in /var/cache/insights-client/ after upload',
        'action': 'store_true',
        'group': 'debug',
    },
    'logging_file': {
        'default': constants.default_log_file,
        'opt': ['--logging-file'],
        'help': 'Path to log file location',
        'action': 'store',
    },
    'loglevel': {
        # non-CLI
        'default': 'DEBUG'
    },
    'net_debug': {
        'default': False,
        'opt': ['--net-debug'],
        'help': 'Log the HTTP method and URL every time a network call is made.',
        'action': 'store_true',
        'group': 'debug',
    },
    'obfuscation_list': {
        # non-CLI
        'default': None  # None is good for distinguishing explicit setting
    },
    'output_dir': {
        'default': None,
        'opt': ['--output-dir', '-od'],
        'help': 'Specify a directory to write collected data to (no compression).',
        'action': 'store',
    },
    'output_file': {
        'default': None,
        'opt': ['--output-file', '-of'],
        'help': 'Specify a compressed archive file to write collected data to.',
        'action': 'store',
    },
    'tags_file': {
        # non-CLI
        'default': os.path.join(constants.default_conf_dir, 'tags.yaml')
    },
    'redaction_file': {
        # non-CLI
        'default': os.path.join(constants.default_conf_dir, 'file-redaction.yaml')
    },
    'content_redaction_file': {
        # non-CLI
        'default': os.path.join(constants.default_conf_dir, 'file-content-redaction.yaml')
    },
    'ros_collect': {
        # non-CLI
        'default': False,
    },
    'verbose': {
        'default': False,
        'opt': ['--verbose'],
        'help': "DEBUG output to stdout",
        'action': "store_true",
    },
}

DEFAULT_KVS = dict((k, v['default']) for k, v in DEFAULT_OPTS.items())
DEFAULT_BOOLS = dict((k, v) for k, v in DEFAULT_KVS.items() if type(v) is bool).keys()


class InsightsConfig(object):
    '''
    Insights client configuration
    '''

    def __init__(self, *args, **kwargs):
        # this is only used to print configuration errors upon initial load
        self._print_errors = False
        if '_print_errors' in kwargs:
            self._print_errors = kwargs['_print_errors']

        self._init_attrs = copy.copy(dir(self))
        self._update_dict(DEFAULT_KVS)

        if args:
            self._update_dict(args[0])
        self._update_dict(kwargs)
        self._cli_opts = None
        self._imply_options()
        self._validate_options()

    def __str__(self):
        _str = '    '
        for key in dir(self):
            if not (key.startswith('_') or key in self._init_attrs or key in ['password', 'proxy']):
                # ignore built-ins, functions, and sensitive items
                val = getattr(self, key)
                _str += key + ': ' + str(val) + '\n    '
        return _str

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def _update_dict(self, dict_):
        '''
        Update without allowing undefined options or overwrite of class methods
        '''
        dict_ = dict((k, v) for k, v in dict_.items() if (k not in self._init_attrs))

        unknown_opts = set(dict_.keys()).difference(set(DEFAULT_OPTS.keys()))
        for u in unknown_opts:
            dict_.pop(u, None)
        self.__dict__.update(dict_)

    def _load_env(self):
        '''
        Options can be set as environment variables
        The formula for the key is `"INSIGHTS_%s" % key.upper()`
        In English, that's the uppercase version of the config key with
        "INSIGHTS_" prepended to it.
        '''

        def _boolify(v):
            if v.lower() == 'true':
                return True
            elif v.lower() == 'false':
                return False
            else:
                return v

        # put this warning here so the error msg only prints once
        if (
            os.environ.get('HTTP_PROXY')
            and not os.environ.get('HTTPS_PROXY')
            and self._print_errors
        ):
            logger.warning(
                'WARNING: HTTP_PROXY is unused by insights-client. Please use HTTPS_PROXY.'
            )

        # ignore these env as they are not config vars
        ignore = ['INSIGHTS_PHASE']

        insights_env_opts = dict(
            (k.lower().split("_", 1)[1], _boolify(v))
            for k, v in os.environ.items()
            if k.upper().startswith("INSIGHTS_") and k.upper() not in ignore
        )

        self._update_dict(insights_env_opts)

    def _load_config_file(self, fname=None):
        '''
        Load config from config file. If fname is not specified,
        config is loaded from the file named by InsightsConfig.conf
        '''
        parsedconfig = ConfigParser.RawConfigParser()
        try:
            parsedconfig.read(fname or self.conf)
        except ConfigParser.Error:
            if self._print_errors:
                logger.error('ERROR: Could not read configuration file, ' 'using defaults')
            return
        try:
            if parsedconfig.has_section(constants.app_name):
                d = dict(parsedconfig.items(constants.app_name))
            else:
                raise ConfigParser.Error
        except ConfigParser.Error:
            if self._print_errors:
                logger.error('ERROR: Could not read configuration file, ' 'using defaults')
            return
        for key in d:
            try:
                if key == 'retries' or key == 'cmd_timeout':
                    d[key] = parsedconfig.getint(constants.app_name, key)
                if key in DEFAULT_BOOLS and isinstance(d[key], six.string_types):
                    d[key] = parsedconfig.getboolean(constants.app_name, key)
            except ValueError as e:
                if self._print_errors:
                    logger.error(
                        'ERROR: {0}.\nCould not read configuration file, '
                        'using defaults'.format(e)
                    )
                return
        self._update_dict(d)

    def load_all(self):
        '''
        Helper function for actual Insights client use
        '''
        # check for custom conf file before loading conf
        self._load_config_file()
        self._load_env()
        self._imply_options()
        self._validate_options()
        return self

    def _validate_options(self):
        '''
        Make sure there are no conflicting or invalid options
        '''

        def _validate_obfuscation_options():
            # Re-format the new obfuscation_list
            if isinstance(self.obfuscation_list, str):
                obf_opt = set(
                    opt.strip() for opt in self.obfuscation_list.strip('\'"').split(',') if opt
                )
                self.obfuscation_list = sorted(obf_opt & DEFAULT_OBFUSCATIONS)
                invalid_opt = obf_opt - DEFAULT_OBFUSCATIONS
                if invalid_opt and self._print_errors:
                    logger.warning(
                        'WARNING: ignoring invalid obfuscate options: `{0}`, using: "obfuscation_list={1}".'.format(
                            '`, `'.join(invalid_opt), ','.join(self.obfuscation_list)
                        )
                    )

        # validate obfuscation options
        _validate_obfuscation_options()

        if self.output_dir and self.output_file:
            raise ValueError('Specify only one: --output-dir or --output-file.')
        if self.output_dir == '':
            # make sure an empty string is not given
            raise ValueError('--output-dir cannot be empty')
        if self.output_file == '':
            # make sure an empty string is not given
            raise ValueError('--output-file cannot be empty')
        if self.output_dir:
            if os.path.exists(self.output_dir):
                if os.path.isfile(self.output_dir):
                    raise ValueError('%s is a file.' % self.output_dir)
                if os.listdir(self.output_dir):
                    raise ValueError(
                        'Directory %s already exists and is not empty.' % self.output_dir
                    )
            parent_dir = os.path.dirname(self.output_dir.rstrip('/'))
            if not os.path.exists(parent_dir):
                raise ValueError(
                    'Cannot write to %s. Parent directory %s does not exist.'
                    % (self.output_dir, parent_dir)
                )
            if not os.path.isdir(parent_dir):
                raise ValueError(
                    'Cannot write to %s. %s is not a directory.' % (self.output_dir, parent_dir)
                )
            if self.obfuscation_list:
                if self._print_errors:
                    logger.warning(
                        'WARNING: Obfuscation reports will be created alongside the output directory.'
                    )
        if self.output_file:
            if os.path.exists(self.output_file):
                raise ValueError('File %s already exists.' % self.output_file)
            parent_dir = os.path.dirname(self.output_file.rstrip('/'))
            if not os.path.exists(parent_dir):
                raise ValueError(
                    'Cannot write to %s. Parent directory %s does not exist.'
                    % (self.output_file, parent_dir)
                )
            if not os.path.isdir(parent_dir):
                raise ValueError(
                    'Cannot write to %s. %s is not a directory.' % (self.output_file, parent_dir)
                )
            if self.obfuscation_list:
                if self._print_errors:
                    logger.warning(
                        'WARNING: Obfuscation reports will be created alongside the output archive.'
                    )

    def _imply_options(self):
        '''
        Some options enable others automatically
        '''
        self.keep_archive = self.keep_archive or self.no_upload
        if self.output_dir or self.output_file:
            # do not upload in this case
            self.no_upload = True
            # don't keep the archive or files in temp
            #   if we're writing it to a specified location
            self.keep_archive = False
        if self.compressor not in constants.valid_compressors:
            # set default compressor if an invalid one is supplied
            if self._print_errors:
                logger.warning(
                    'The compressor {0} is not supported. Using default: gz'.format(self.compressor)
                )
            self.compressor = 'gz'
        if self.app:
            # Get the manifest for the specified app
            self.manifest = manifests.get(self.app)
            self.content_type = content_types.get(self.app)
            self.legacy_upload = False
            self._set_app_config()
        if (
            self.compliance
            or self.compliance_policies
            or self.compliance_assign
            or self.compliance_unassign
        ):
            # Get the manifest for Compliance
            self.manifest = manifests.get('compliance')
            self.content_type = content_types.get('compliance')
            self.legacy_upload = False
        if self.output_dir:
            # get full path
            self.output_dir = os.path.abspath(self.output_dir)
        if self.output_file:
            # get full path
            self.output_file = os.path.abspath(self.output_file)
            self._determine_filename_and_extension()

    def _set_app_config(self):
        '''
        Set App specific insights config values that differ from the default values
        Config values may have been set manually however, so need to take that into consideration
        '''
        if self.app == 'malware-detection':
            # Add extra retries for malware, mainly because it could take a long time to run
            # and the results archive shouldn't be discarded after a single failed upload attempt
            if self.retries < 3:
                self.retries = 3

    def _determine_filename_and_extension(self):
        '''
        Attempt to automatically determine compressor
        and filename for --output-file based on the given config.
        '''

        def _tar_ext(comp):
            '''
            Helper function to generate .tar file extension
            '''
            ext = '' if comp == 'none' else '.%s' % comp
            return '.tar' + ext

        # make sure we're not attempting to write an existing directory first
        if os.path.isdir(self.output_file):
            raise ValueError('%s is a directory.' % self.output_file)

        # attempt to determine compressor from filename
        for x in constants.valid_compressors:
            if self.output_file.endswith(_tar_ext(x)):
                if self.compressor != x:
                    if self._print_errors:
                        logger.warning(
                            'The given output file {0} does not match the given compressor {1}. '
                            'Setting compressor to match the file extension.'.format(
                                self.output_file, self.compressor
                            )
                        )
                self.compressor = x
                return

        # if we don't return from the loop, we could
        #   not determine compressor from filename, so
        #   set the filename from the given
        #   compressor
        self.output_file = self.output_file + _tar_ext(self.compressor)


if __name__ == '__main__':
    config = InsightsConfig(_print_errors=True)
    config.load_all()
    print(config)
