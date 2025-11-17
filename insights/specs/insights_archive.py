from insights.core.spec_factory import glob_file, simple_file, head, first_file
from functools import partial
from insights.core.context import HostArchiveContext
from insights.specs import Specs

simple_file = partial(simple_file, context=HostArchiveContext)
glob_file = partial(glob_file, context=HostArchiveContext)
first_file = partial(first_file, context=HostArchiveContext)


class InsightsArchiveSpecs(Specs):
    # Client metadata specs/files
    uname = simple_file("insights_commands/uname_-a")
