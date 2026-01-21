"""
SCSIFWver - file ``/sys/class/scsi_host/host[0-9]*/fwrev``
==========================================================

This parser parses the content from fwver file from individual
SCSI hosts. This parser will return data in dictionary format.

Sample Content from ``/sys/class/scsi_host/host0/fwrev``::

    2.02X12 (U3H2.02X12), sli-3


Examples:
    >>> type(scsi_obj)
    <class 'insights.parsers.scsi_fwver.SCSIFWver'>
    >>> scsi_obj
    {'host0': ['2.02X12 (U3H2.02X12)', 'sli-3']}
    >>> scsi_obj.scsi_host
    'host0'
"""

from insights.core import Parser
from insights.core.plugins import parser
from insights.parsers import get_active_lines
from insights.specs import Specs


@parser(Specs.scsi_fwver)
class SCSIFWver(Parser, dict):
    """
    Parse `/sys/class/scsi_host/host[0-9]*/fwrev` file, return a dict
    contain `fwver` scsi host file info. "scsi_host" key is scsi host file
    parse from scsi host file name.

    Properties:
        scsi_host (str): scsi host file name derived from file path.
    """

    def __init__(self, context):
        self.scsi_host = context.path.rsplit("/")[-2]
        super(SCSIFWver, self).__init__(context)

    def parse_content(self, content):
        for line in get_active_lines(content):
            self[self.scsi_host] = [mode.strip() for mode in line.split(',')]

    @property
    def host_mode(self):
        """
        (list): It will return the scsi host modes when set else `None`.
        """
        return self[self.scsi_host]

    # Backward compatible
    data = property(lambda self: self)
