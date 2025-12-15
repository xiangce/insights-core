import os

_user_home = os.path.expanduser('~')
_app_name = 'insights-collector'
_uid = os.getuid()
_user_cache = os.getenv('XDG_CACHE_HOME', default=os.path.join(_user_home, '.cache'))


def _log_dir():
    '''
    Get the insights-client log dir

    Default: /var/log/insights-client
    Non-root user: $XDG_CACHE_HOME/insights-client || $HOME/.cache/insights-client/log
    '''
    if _uid == 0:
        insights_log_dir = os.path.join(os.sep, 'var', 'log', _app_name)
    else:
        insights_log_dir = os.path.join(_user_cache, _app_name, 'log')
    return insights_log_dir


def _lib_dir():
    '''
    Get the insights-client egg cache dir

    Default: /var/lib/insights
    Non-root user: $XDG_CACHE_HOME/insights-client || $HOME/.cache/insights-client/lib
    '''
    if _uid == 0:
        insights_lib_dir = os.path.join(os.sep, 'var', 'lib', 'insights')
    else:
        insights_lib_dir = os.path.join(_user_cache, _app_name, 'lib')
    return insights_lib_dir


class InsightsConstants(object):
    app_name = _app_name
    package_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    command_blacklist = ('rm', 'kill', 'reboot', 'shutdown')
    default_conf_dir = os.getenv('INSIGHTS_CONF_DIR', default='/etc/insights-client')
    default_conf_file = os.path.join(default_conf_dir, 'insights-client.conf')
    default_tags_file = os.path.join(default_conf_dir, 'tags.yaml')
    log_dir = _log_dir()
    default_log_file = os.path.join(log_dir, app_name + '.log')
    base_url = 'cert-api.access.redhat.com/r/insights/platform'
    default_branch_info = {'remote_branch': -1, 'remote_leaf': -1}
    default_cmd_timeout = 120  # default command execution to two minutes, prevents long running commands that will hang
    sig_kill_ok = 100
    sig_kill_bad = 101
    cached_branch_info = os.path.join(default_conf_dir, '.branch_info')
    pidfile = os.path.join(os.sep, 'var', 'run', 'insights-client.pid')
    insights_tmp_path = os.path.join(os.sep, 'var', 'tmp')
    cache_dir = os.path.join(os.sep, 'var', 'cache', 'insights-client')
    insights_tmp_prefix = 'insights-client'
    ppidfile = os.path.join(os.sep, 'run', 'insights-client.ppid')
    valid_compressors = ("gz", "xz", "bz2", "none")
    rhsm_facts_dir = os.path.join(os.sep, 'etc', 'rhsm', 'facts')
    rhsm_facts_file = os.path.join(os.sep, rhsm_facts_dir, 'insights-client.facts')
    archive_filesize_max = 100 # In MB
