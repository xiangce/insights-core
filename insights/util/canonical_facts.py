#!/usr/bin/env python

from __future__ import print_function

import json

from insights import rule, run, make_metadata, add_filter
from insights.combiners.cloud_instance import CloudInstance
from insights.combiners.cloud_provider import CloudProvider
from insights.core.dr import set_enabled, load_components
from insights.core.spec_cleaner import deep_clean
from insights.parsers.aws_instance_id import AWSInstanceIdDoc
from insights.parsers.azure_instance import AzureInstanceID, AzureInstanceType
from insights.parsers.client_metadata import MachineID
from insights.parsers.dmidecode import DMIDecode
from insights.parsers.etc_machine_id import EtcMachineId
from insights.parsers.gcp_instance_type import GCPInstanceType
from insights.parsers.hostname import Hostname
from insights.parsers.installed_rpms import InstalledRpms
from insights.parsers.ip import IPs
from insights.parsers.mac import MacAddress
from insights.parsers.rhsm_conf import RHSMConf
from insights.parsers.subscription_manager import SubscriptionManagerID, SubscriptionManagerFacts
from insights.parsers.yum import YumRepoList
from insights.specs import Specs


add_filter(SubscriptionManagerFacts, 'instance_id')
add_filter(RHSMConf, ['server', 'hostname'])


def _filter_falsy(dict_):
    return dict((k, v) for k, v in dict_.items() if v)


@rule(Specs.canonical_facts)
def canonical_facts(canonical_facts):
    facts = json.loads('\n'.join(canonical_facts.content))
    print('------------------', facts)
    return make_metadata(**_filter_falsy(facts))


def get_canonical_facts(path=None, config=None, redact_config=None):
    if path is None:
        load_components("insights.specs.default.DefaultSpecs")
        required_components = [
            AWSInstanceIdDoc,
            AzureInstanceID,
            AzureInstanceType,
            CloudInstance,
            CloudProvider,
            DMIDecode,
            EtcMachineId,
            GCPInstanceType,
            Hostname,
            IPs,
            InstalledRpms,
            MacAddress,
            MachineID,
            RHSMConf,
            SubscriptionManagerFacts,
            SubscriptionManagerID,
            YumRepoList,
            canonical_facts,
        ]
        for comp in required_components:
            set_enabled(comp, True)
        br = run(canonical_facts)
        d = br[canonical_facts]
        del d["type"]
        return deep_clean(d, config, redact_config)

    br = run(canonical_facts, root=path)
    d = br[canonical_facts]
    del d["type"]
    return d


if __name__ == "__main__":
    print(json.dumps(get_canonical_facts()))
