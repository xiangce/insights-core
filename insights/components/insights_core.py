"""
Insights Core related Components
================================

<<<<<<< HEAD
CoreEgg - If collector is based on Egg
--------------------------------------

CoreRpm - If collector is based on Rpm
--------------------------------------
=======
Egg - If collector is based on Egg
----------------------------------

Rpm - If collector is based on Rpm
----------------------------------
>>>>>>> fa0afe9c (feat: add components Egg/Rpm to identify the current collector)
"""

from insights.core.exceptions import SkipComponent
from insights.core.plugins import component
from insights.parsers.installed_rpms import InstalledRpms, InstalledRpm


<<<<<<< HEAD
def _identify_collector(rpms):
=======
def _is_RPM_collector(rpms):
>>>>>>> cf802d30 (feat: add CoreEgg/CoreRpm to identify current collector)
    """
    Check the installed RPMs, it's RPM collector only when
    - insights-core is installed
    - insights-client is newer than specified minmum version
    """
<<<<<<< HEAD
    # TODO: add rhc
=======
>>>>>>> cf802d30 (feat: add CoreEgg/CoreRpm to identify current collector)
    min_client = {
        'el9': InstalledRpm('insights-client-3.9.3-1.el9'),
        'el10': InstalledRpm('insights-client-3.10.3-1.el10'),
    }

<<<<<<< HEAD
    if 'insights-client' in rpms:
        # Offically, insights-client.rpm must be installed
        cur_client = rpms.newest('insights-client')
        if 'insights-core' in rpms:
            # insights-core.rpm is installed
            for el, client in min_client.items():
                if el in cur_client.release and cur_client >= client:
                    # expected insights-client  is installed
                    # RPM is used
                    return 'RPM'
        # Egg is used
        return 'EGG'
    # Unknown
    return None
=======
    # insights-client must be installed
    cur_client = rpms.newest('insights-client')
    if 'insights-core' in rpms:
        # insights-core.rpm is installed
        for el, client in min_client.items():
            if el in cur_client.release and cur_client >= client:
                # insights-client that uses RPM is installed
                return True
    # Egg is used by default
    return False
>>>>>>> cf802d30 (feat: add CoreEgg/CoreRpm to identify current collector)


@component(InstalledRpms)
class CoreEgg(object):
    """
    This ``CoreEgg`` component will be skipped when insights-core RPM collector
    is used for this collection.

    Raises:
<<<<<<< HEAD
        SkipComponent: When RPM/Unknown collector is used.
    """

    def __init__(self, rpms):
        if _identify_collector(rpms) != 'EGG':
            raise SkipComponent('Egg is not used.')
=======
        SkipComponent: When RPM collector is used.
    """

    def __init__(self, rpms):
        if _is_RPM_collector(rpms):
            raise SkipComponent('core RPM is used.')
>>>>>>> cf802d30 (feat: add CoreEgg/CoreRpm to identify current collector)


@component(InstalledRpms)
class CoreRpm(object):
    """
    This ``CoreRpm`` component will be skipped when insights-core Egg collector
    is used for this collection.

    Raises:
<<<<<<< HEAD
        SkipComponent: When Egg/Unknown collector is used.
    """

    def __init__(self, rpms):
        if _identify_collector(rpms) != 'RPM':
            raise SkipComponent('RPM is not used.')
=======
        SkipComponent: When Egg collector is used.
    """

    def __init__(self, rpms):
        if _is_RPM_collector(rpms) is False:
            raise SkipComponent('core Egg is used.')
>>>>>>> cf802d30 (feat: add CoreEgg/CoreRpm to identify current collector)
