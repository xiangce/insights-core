# -*- coding: utf-8 -*-
"""
subscription-manager commands
=============================

Parsers for parsing output of the ``subscription-manager`` commands.

SubscriptionManagerID - command ``subscription-manager identity``
-----------------------------------------------------------------

SubscriptionManagerFacts - command ``subscription-manager facts``
-----------------------------------------------------------------

SubscriptionManagerStatus - command ``subscription-manager status``
-------------------------------------------------------------------

SubscriptionManagerSyspurpose - command ``subscription-manager syspurpose``
---------------------------------------------------------------------------
"""

import uuid

from insights.core import CommandParser, JSONParser
from insights.core.exceptions import SkipComponent
from insights.core.filters import add_filter
from insights.core.plugins import parser
from insights.specs import Specs

add_filter(
    Specs.subscription_manager_facts,
    [
        'conversions.activity',
        'image-builder.osbuild-composer.api-type',
        'instance_id',
    ],
)


def _local_kv_split(lines):
    ret = dict()
    for line in lines:
        # handle full-width colon
        line = line.replace('：', ': ')
        if ': ' in line:
            key, val = [_l.strip() for _l in line.split(': ', 1)]
            ret[key] = val
    if ret:
        return ret
    raise SkipComponent


@parser(Specs.subscription_manager_id)
class SubscriptionManagerID(CommandParser, dict):
    """
    Reads the output of subscription-manager identity and retrieves the UUID

    Example output::

        system identity: 6655c27c-f561-4c99-a23f-111111111111
        name: rhel7.localdomain
        org name: 1234567
        org ID: 1234567

    Examples::
        >>> type(subman_id)
        <class 'insights.parsers.subscription_manager.SubscriptionManagerID'>
        >>> subman_id.identity == '6655c27c-f561-4c99-a23f-111111111111'
        True
        >>> subman_id.get('org ID') == '1234567'
        True
        >>> subman_id.uuid == '6655c27c-f561-4c99-a23f-111111111111'
        True
    """

    def parse_content(self, content):
        self.update(_local_kv_split(content))

    @property
    def identity(self):
        """
        Returns the value of 'system identity'.
        Multiple language support is from:
        - https://github.com/candlepin/subscription-manager/tree/main/po
        """
        SYSID_MULT_LANG = [
            'system identity',  # en first
            'identidad de sistema',
            'identidade do sistema',
            'identità del sistema',
            'identité du système',
            'Systemidentität',
            'идентификация системы',
            'तंत्र पहचान',
            'प्रणाली ओळख',
            'চিস্টেম পৰিচয়',
            'সিস্টেম পরিচয়',
            'ਸਿਸਟਮ ਸ਼ਨਾਖਤ',
            'સિસ્ટમ ઓળખ',
            'ତନ୍ତ୍ର ପରିଚୟ',
            'கணினி அடையாளம்',
            'వ్యవస్థ గుర్తింపు',
            'ವ್ಯವಸ್ಥೆಯ ಗುರುತು',
            'സിസ്റ്റം ഐഡന്റിറ്റി',
            'სისტემის იდენტიფიკატორი',
            'システム ID',
            '系統身份',
            '系统身份',
            '시스템 ID',
        ]
        for name in SYSID_MULT_LANG:
            if name in self:
                return self[name]

    @property
    def uuid(self):
        """
        Returns the UUID of 'system identity' in standard format (32 digits separated by hyphens).
        """
        if self.identity:
            return str(uuid.UUID(self.identity))


@parser(Specs.subscription_manager_facts)
class SubscriptionManagerFacts(CommandParser, dict):
    """
    Class for parsing the output of `subscription-manager facts` command.

    Typical output of the command is::

        aws_instance_id: 567890567890
        network.ipv6_address: ::1
        uname.sysname: Linux
        uname.version: #1 SMP PREEMPT Fri Sep 2 16:07:40 EDT 2022
        virt.host_type: rhev, kvm
        virt.is_guest: True

    Examples:
        >>> type(rhsm_facts)
        <class 'insights.parsers.subscription_manager.SubscriptionManagerFacts'>
        >>> rhsm_facts['aws_instance_id']
        '567890567890'
    """

    def parse_content(self, content):
        self.update(_local_kv_split(content))


@parser(Specs.subscription_manager_status)
class SubscriptionManagerStatus(CommandParser, dict):
    """
    Reads the output of subscription-manager status

    Example output::

        +-------------------------------------------+
           System Status Details
        +-------------------------------------------+
        Overall Status: Disabled
        Content Access Mode is set to Simple Content Access. This host has access to content, regardless of subscription status.

        System Purpose Status: Disabled

    Examples::
        >>> type(subman_status)
        <class 'insights.parsers.subscription_manager.SubscriptionManagerStatus'>
        >>> subman_status['Overall Status'] == 'Disabled'
        True
        >>> subman_status['Content Access Mode'] == 'Simple Content Access'
        True
        >>> subman_status['System Purpose Status'] == 'Disabled'
        True
    """

    def parse_content(self, content):
        self.unparsed_lines = []
        for line in content:
            line = line.strip()

            if not line:
                continue

            if ': ' in line:
                key, val = [_l.strip() for _l in line.split(': ', 1)]
                self[key] = val
            elif line.startswith('Content Access Mode is set to'):
                self['Content Access Mode'] = (
                    line.split('.', 1)[0].split('Content Access Mode is set to')[1].strip()
                )
            elif line.startswith("Red Hat Enterprise Linux for Virtual Datacenters"):
                subscription_type = line.split(',')[1].strip(':').strip() if ',' in line else ''
                self['Red Hat Enterprise Linux for Virtual Datacenters'] = subscription_type
            elif "Guest has not been reported on any host" in line:
                self.unparsed_lines.append(line)

        if not self:
            raise SkipComponent


@parser(Specs.subscription_manager_syspurpose)
class SubscriptionManagerSyspurpose(CommandParser, JSONParser):
    """
    Reads the output of subscription-manager syspurpose

    Example output::

        {
          "addons": [],
          "role": "Red Hat Enterprise Linux Server",
          "service_level_agreement": "Standard",
          "usage": "Development/Test"
        }

    Examples::
        >>> type(subman_syspurpose)
        <class 'insights.parsers.subscription_manager.SubscriptionManagerSyspurpose'>
        >>> subman_syspurpose.get('role') == 'Red Hat Enterprise Linux Server'
        True
        >>> subman_syspurpose['service_level_agreement'] == 'Standard'
        True
        >>> subman_syspurpose['usage'] == 'Development/Test'
        True
    """

    pass
