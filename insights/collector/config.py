from __future__ import absolute_import

import argparse
import copy
import logging
import os
import six
import json

from six.moves import configparser as ConfigParser

from insights.cleaner import DEFAULT_OBFUSCATIONS
from insights.collector.constants import InsightsConstants as constants
from insights.collector.utilities import verify_permissions, load_yaml, correct_format
from insights.specs.manifests import manifests, content_types


logger = logging.getLogger(__name__)
if six.PY2:
    # to avoid "No handler" issue of python 2.7
    # https://docs.python.org/2.7/howto/logging.html#configuring-logging-for-a-library
    logger.addHandler(logging.NullHandler())


DEFAULT_OPTS = {
    'check_results': {
        'default': False,
        'opt': ['--check-results'],
        'help': argparse.SUPPRESS,
        'action': "store_true",
        'group': 'actions',
    },
    'manifest': {
        'default': None,
        'opt': ['--manifest'],
        'help': 'Collect using the provided manifest',
        'action': 'store',
        'group': 'actions',
        'dest': 'manifest',
    },
    'cmd_timeout': {
        # non-CLI
        'default': constants.default_cmd_timeout
    },
    # 'compliance': {
    #     'default': False,
    #     'opt': ['--compliance'],
    #     'help': 'Scan the system using openscap and upload the report',
    #     'action': 'store_true',
    #     'group': 'actions',
    # },
    # 'compliance_policies': {
    #     'default': False,
    #     'opt': ['--compliance-policies'],
    #     'help': 'List the compliance policies assignable to the system',
    #     'action': 'store_true',
    #     'group': 'actions',
    # },
    # 'compliance_assign': {
    #     'default': None,
    #     'opt': ['--compliance-assign'],
    #     'help': 'Assign the system to a compliance policy with the specified ID',
    #     'action': 'store',
    #     'group': 'actions',
    # },
    # 'compliance_unassign': {
    #     'default': None,
    #     'opt': ['--compliance-unassign'],
    #     'help': 'Unassign the system from a compliance policy with the specified ID',
    #     'action': 'store',
    #     'group': 'actions',
    # },
    'obfuscation_list': {
        # non-CLI
        'default': None  # None is good for distinguishing explicit setting
    },
    'offline': {
        'default': False,
        'opt': ['--offline'],
        'help': 'offline mode for OSP use',
        'action': 'store_true',
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
    'quiet': {
        'default': False,
        'opt': ['--quiet'],
        'help': 'Only display error messages to stdout',
        'action': 'store_true',
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
    'show_results': {
        'default': False,
        'opt': ['--show-results'],
        'help': "Show insights about this host",
        'action': "store_true",
        'group': 'actions',
    },
    'verbose': {
        'default': False,
        'opt': ['--verbose'],
        'help': "DEBUG output to stdout",
        'action': "store_true",
    },
    'version': {
        'default': False,
        'opt': ['--version'],
        'help': "Display version",
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

        self.load_all()
        if args:
            self._update_dict(args[0])

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

        # zzz
        if 'no_gpg' in dict_ and dict_['no_gpg']:
            dict_['gpg'] = False

        unknown_opts = set(dict_.keys()).difference(set(DEFAULT_OPTS.keys()))
        if unknown_opts and self._print_errors:
            # only print error once
            logger.warning('WARNING: Unknown options: ' + ', '.join(list(unknown_opts)))
            if 'no_schedule' in unknown_opts:
                logger.warning(
                    'WARNING: Config option `no_schedule` has '
                    'been deprecated. To disable automatic '
                    'scheduling for Red Hat Insights, run '
                    '`insights-client --disable-schedule`'
                )
        for u in unknown_opts:
            dict_.pop(u, None)
        self.__dict__.update(dict_)

    def _load_config_file(self, fname=constants.default_conf_file):
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
        # self._imply_options()
        self.get_redact_conf()
        self._validate_options()
        return self

    def _validate_options(self):
        '''
        Make sure there are no conflicting or invalid options
        '''

        def _validate_obfuscation_options():
            if isinstance(self.obfuscation_list, six.string_types):
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

    def _imply_options(self):
        '''
        Some options enable others automatically
        '''
        self.no_upload = self.no_upload or self.offline
        self.auto_update = self.auto_update and not self.offline
        if (
            self.analyze_container
            or self.analyze_file
            or self.analyze_mountpoint
            or self.analyze_image_id
        ):
            self.analyze_container = True
        self.to_json = self.to_json or self.analyze_container
        self.register = self.register and not self.offline
        self.keep_archive = self.keep_archive or self.no_upload
        if self.to_json and self.quiet:
            self.diagnosis = True
        if self.test_connection:
            self.net_debug = True
        if self.payload or self.diagnosis or self.check_results or self.checkin:
            self.legacy_upload = False
            self._legacy_upload_reason = (
                "--payload, --diagnosis, --check-results and --checkin require non-legacy"
            )
        if self.payload and (self.logging_file == constants.default_log_file):
            self.logging_file = constants.default_payload_log
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
            self._legacy_upload_reason = "apps require non-legacy"
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
            self._legacy_upload_reason = "compliance requires non-legacy"
        if self.output_dir:
            # get full path
            self.output_dir = os.path.abspath(self.output_dir)
        if self.output_file:
            # get full path
            self.output_file = os.path.abspath(self.output_file)
            self._determine_filename_and_extension()
        if self._cli_opts and "ansible_host" in self._cli_opts and not self.register:
            # Specific use case, explained here:
            #
            #   Ansible hostname is, more or less, a second display name.
            #   However, there is no method in the legacy API to handle
            #   changes to the ansible hostname. So, if a user specifies
            #   --ansible-hostname on the CLI to change it like they would
            #   --display-name, in order to actually change it, we need to
            #   force disable legacy_upload to make the proper HTTP requests.
            #
            #   As of now, registration still needs to be tied to the legacy
            #   API, so if the user has legacy upload enabled (the default),
            #   we can't force disable it when registering. Thus, if
            #   specifying --ansible-hostname alongside --register, all the
            #   necessary legacy API calls will still be made, the
            #   ansible-hostname will be packed into the archive, and the
            #   rest will be handled by ingress. Incidentally, if legacy
            #   upload *is* disabled, the ansible hostname will also be
            #   included in the upload metadata.
            #
            #   The reason to explicitly look for ansible_host in the CLI
            #   parameters *only* is because, due to a customer request from
            #   long ago, a display_name specified in the config file should
            #   be applied as part of the upload, and conversely, specifying
            #   it on the command line (WITHOUT --register) should be a
            #   "once and done" option that does a single HTTP call to modify
            #   it. We are going to mimic that behavior with the Ansible
            #   hostname.
            #
            #   Therefore, only force legacy_upload to False when attempting
            #   to change Ansible hostname from the CLI, when not registering.
            self.legacy_upload = False
            self._legacy_upload_reason = "--ansible-host requires non-legacy"

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

    def load_redaction_file(self, fname):
        '''
        Load the YAML-style file-redaction.yaml
            or file-content-redaction.yaml files
        '''
        if fname not in (self.redaction_file, self.content_redaction_file):
            # invalid function use, should never get here in a production situation
            return None
        if not fname:
            # no filename defined, return nothing
            logger.debug('redaction_file or content_redaction_file is undefined')
            return None
        if not fname or not os.path.isfile(fname):
            if fname == self.redaction_file:
                logger.debug(
                    '%s not found. No files or commands will be skipped.', self.redaction_file
                )
            elif fname == self.content_redaction_file:
                logger.debug(
                    '%s not found. '
                    'No patterns will be skipped and no keyword obfuscation will occur.',
                    self.content_redaction_file,
                )
            return None
        try:
            verify_permissions(fname)
        except RuntimeError as e:
            if self.config.validate:
                # exit if permissions invalid and using --validate
                raise RuntimeError('ERROR: %s' % e)
            logger.warning('WARNING: %s', e)
        loaded = load_yaml(fname)
        if fname == self.redaction_file:
            err, msg = correct_format(loaded, ('commands', 'files', 'components'), fname)
        elif fname == self.content_redaction_file:
            err, msg = correct_format(loaded, ('patterns', 'keywords'), fname)
        if err:
            # YAML is correct but doesn't match the format we need
            raise RuntimeError('ERROR: ' + msg)
        return loaded

    def get_redact_conf(self):
        '''
        Try to load the the "new" version of
        remove.conf (file-redaction.yaml and file-content-redaction.yaml)
        '''
        rm_conf = {}
        redact_conf = self.load_redaction_file(self.redaction_file)
        content_redact_conf = self.load_redaction_file(self.content_redaction_file)

        rm_conf.update(redact_conf or {})
        rm_conf.update(content_redact_conf or {})
        # remove Nones, empty strings, and empty lists
        self.redact_conf = dict((k, v) for k, v in rm_conf.items() if v)

        if self.redact_conf and (
            '/etc/insights-client/machine-id' in self.redact_conf.get('files', [])
            or 'insights.specs.default.DefaultSpecs.machine_id'
            in self.redact_conf.get('components', [])
        ):
            logger.warning(
                "WARNING: Spec machine_id will be skipped for redaction; as it would cause issues, please remove it from %s.",
                self.redaction_file,
            )
        # return the RAW rm_conf
        return self.redact_conf

    def validate(self):
        '''
        Validate remove.conf and tags.conf
        '''
        self.get_tags_conf()
        success = self.get_rm_conf()
        if not success:
            logger.info('No contents in the blacklist configuration to validate.')
            return None
        # Using print here as this could contain sensitive information
        print('Blacklist configuration parsed contents:')
        print(json.dumps(success, indent=4))
        logger.info('Parsed successfully.')
        return True


if __name__ == '__main__':
    config = InsightsConfig(_print_errors=True)
    config.load_all()
    print(config)
