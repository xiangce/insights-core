"""
This module defines all datasources used by standard Red Hat Insight components.

To define data sources that override the components in this file, create a
`insights.core.spec_factory.SpecFactory` with "insights.specs" as the constructor
argument. Data sources created with that factory will override components in
this file with the same `name` keyword argument. This allows overriding the
data sources that standard Insights `Parsers` resolve against.
"""

import logging
from insights.core.spec_factory import (
    first_of,
    simple_command,
    simple_file,
)
from insights.specs import SpecSet

logger = logging.getLogger(__name__)

class DefaultSpecs(SpecSet):
    # Dependent specs that aren't in the registry
    redhat_release = simple_file("/etc/redhat-release")
    uname = first_of(
        [simple_command("/usr/bin/uname -a"), simple_command("/bin/uname -a")]  # RHEL 6
    )
