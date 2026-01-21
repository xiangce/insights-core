"""
CephOsdTree
===========

Combiner provides the information about ceph osd tree. It
uses the results of the ``CephOsdTree``, ``CephInsights`` and ``CephOsdTreeText`` parsers.
The order from most preferred to least preferred is ``CephOsdTree``, ``CephInsights``, ``CephOsdTreeText``.

Examples:
    >>> type(cot)
    <class 'insights.combiners.ceph_osd_tree.CephOsdTree'>
    >>> cot['nodes'][0]['children']
    [-7, -3, -5, -9]
"""

from insights.core.plugins import combiner
from insights.parsers.ceph_cmd_json_parsing import CephOsdTree as CephOsdTreeParser
from insights.parsers.ceph_insights import CephInsights
from insights.parsers.ceph_osd_tree_text import CephOsdTreeText


@combiner([CephOsdTreeParser, CephInsights, CephOsdTreeText])
class CephOsdTree(dict):
    """
    Combiner provides the information about ceph osd tree. It
    uses the results of the ``CephOsdTree``, ``CephInsights`` and ``CephOsdTreeText`` parsers.
    The order from most preferred to least preferred is ``CephOsdTree``, ``CephInsights``, ``CephOsdTreeText``.
    """

    def __init__(self, cot, ci, cott):
        if cot:
            self.update(cot.data)
        elif ci:
            self.update(ci['osd_tree'])
        else:
            self.update(cott)

    data = property(lambda self: self)
