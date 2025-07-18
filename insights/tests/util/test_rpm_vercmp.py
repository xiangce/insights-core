# -*- coding: utf-8 -*-
import pytest
from insights.util.rpm_vercmp import _rpm_vercmp


# data copied from
# https://raw.githubusercontent.com/rpm-software-management/rpm/master/tests/rpmvercmp.at

DEFAULT_DATA = """
m4_define([RPMVERCMP],[
AT_SETUP([rpmvercmp($1, $2) = $3])
AT_KEYWORDS([vercmp])
AT_CHECK([
AT_SKIP_IF([$LUA_DISABLED])
runroot rpm --eval '%{lua: print(rpm.vercmp("$1", "$2"))}'], [0], [$3
], [])
AT_CLEANUP
])

AT_BANNER([RPM version comparison])

RPMVERCMP(1.0, 1.0, 0)
RPMVERCMP(1.0, 2.0, -1)
RPMVERCMP(2.0, 1.0, 1)

RPMVERCMP(2.0.1, 2.0.1, 0)
RPMVERCMP(2.0, 2.0.1, -1)
RPMVERCMP(2.0.1, 2.0, 1)

RPMVERCMP(2.0.1a, 2.0.1a, 0)
RPMVERCMP(2.0.1a, 2.0.1, 1)
RPMVERCMP(2.0.1, 2.0.1a, -1)

RPMVERCMP(5.5p1, 5.5p1, 0)
RPMVERCMP(5.5p1, 5.5p2, -1)
RPMVERCMP(5.5p2, 5.5p1, 1)

RPMVERCMP(5.5p10, 5.5p10, 0)
RPMVERCMP(5.5p1, 5.5p10, -1)
RPMVERCMP(5.5p10, 5.5p1, 1)

RPMVERCMP(10xyz, 10.1xyz, -1)
RPMVERCMP(10.1xyz, 10xyz, 1)

RPMVERCMP(xyz10, xyz10, 0)
RPMVERCMP(xyz10, xyz10.1, -1)
RPMVERCMP(xyz10.1, xyz10, 1)

RPMVERCMP(xyz.4, xyz.4, 0)
RPMVERCMP(xyz.4, 8, -1)
RPMVERCMP(8, xyz.4, 1)
RPMVERCMP(xyz.4, 2, -1)
RPMVERCMP(2, xyz.4, 1)

RPMVERCMP(5.5p2, 5.6p1, -1)
RPMVERCMP(5.6p1, 5.5p2, 1)

RPMVERCMP(5.6p1, 6.5p1, -1)
RPMVERCMP(6.5p1, 5.6p1, 1)

RPMVERCMP(6.0.rc1, 6.0, 1)
RPMVERCMP(6.0, 6.0.rc1, -1)

RPMVERCMP(10b2, 10a1, 1)
RPMVERCMP(10a2, 10b2, -1)

RPMVERCMP(1.0aa, 1.0aa, 0)
RPMVERCMP(1.0a, 1.0aa, -1)
RPMVERCMP(1.0aa, 1.0a, 1)

RPMVERCMP(10.0001, 10.0001, 0)
RPMVERCMP(10.0001, 10.1, 0)
RPMVERCMP(10.1, 10.0001, 0)
RPMVERCMP(10.0001, 10.0039, -1)
RPMVERCMP(10.0039, 10.0001, 1)

RPMVERCMP(4.999.9, 5.0, -1)
RPMVERCMP(5.0, 4.999.9, 1)

RPMVERCMP(20101121, 20101121, 0)
RPMVERCMP(20101121, 20101122, -1)
RPMVERCMP(20101122, 20101121, 1)

RPMVERCMP(2_0, 2_0, 0)
RPMVERCMP(2.0, 2_0, 0)
RPMVERCMP(2_0, 2.0, 0)

dnl RhBug:178798 case
RPMVERCMP(a, a, 0)
RPMVERCMP(a+, a+, 0)
RPMVERCMP(a+, a_, 0)
RPMVERCMP(a_, a+, 0)
RPMVERCMP(+a, +a, 0)
RPMVERCMP(+a, _a, 0)
RPMVERCMP(_a, +a, 0)
RPMVERCMP(+_, +_, 0)
RPMVERCMP(_+, +_, 0)
RPMVERCMP(_+, _+, 0)
RPMVERCMP(+, _, 0)
RPMVERCMP(_, +, 0)

dnl Basic testcases for tilde sorting
RPMVERCMP(1.0~rc1, 1.0~rc1, 0)
RPMVERCMP(1.0~rc1, 1.0, -1)
RPMVERCMP(1.0, 1.0~rc1, 1)
RPMVERCMP(1.0~rc1, 1.0~rc2, -1)
RPMVERCMP(1.0~rc2, 1.0~rc1, 1)
RPMVERCMP(1.0~rc1~git123, 1.0~rc1~git123, 0)
RPMVERCMP(1.0~rc1~git123, 1.0~rc1, -1)
RPMVERCMP(1.0~rc1, 1.0~rc1~git123, 1)

dnl Basic testcases for caret sorting
RPMVERCMP(1.0^, 1.0^, 0)
RPMVERCMP(1.0^, 1.0, 1)
RPMVERCMP(1.0, 1.0^, -1)
RPMVERCMP(1.0^git1, 1.0^git1, 0)
RPMVERCMP(1.0^git1, 1.0, 1)
RPMVERCMP(1.0, 1.0^git1, -1)
RPMVERCMP(1.0^git1, 1.0^git2, -1)
RPMVERCMP(1.0^git2, 1.0^git1, 1)
RPMVERCMP(1.0^git1, 1.01, -1)
RPMVERCMP(1.01, 1.0^git1, 1)
RPMVERCMP(1.0^20160101, 1.0^20160101, 0)
RPMVERCMP(1.0^20160101, 1.0.1, -1)
RPMVERCMP(1.0.1, 1.0^20160101, 1)
RPMVERCMP(1.0^20160101^git1, 1.0^20160101^git1, 0)
RPMVERCMP(1.0^20160102, 1.0^20160101^git1, 1)
RPMVERCMP(1.0^20160101^git1, 1.0^20160102, -1)

dnl Basic testcases for tilde and caret sorting
RPMVERCMP(1.0~rc1^git1, 1.0~rc1^git1, 0)
RPMVERCMP(1.0~rc1^git1, 1.0~rc1, 1)
RPMVERCMP(1.0~rc1, 1.0~rc1^git1, -1)
RPMVERCMP(1.0^git1~pre, 1.0^git1~pre, 0)
RPMVERCMP(1.0^git1, 1.0^git1~pre, 1)
RPMVERCMP(1.0^git1~pre, 1.0^git1, -1)

dnl These are included here to document current, arguably buggy behaviors
dnl for reference purposes and for easy checking against  unintended
dnl behavior changes.
dnl
dnl AT_BANNER([RPM version comparison oddities])
dnl RhBug:811992 case
dnl RPMVERCMP(1b.fc17, 1b.fc17, 0)
dnl RPMVERCMP(1b.fc17, 1.fc17, -1)
dnl RPMVERCMP(1.fc17, 1b.fc17, 1)
dnl RPMVERCMP(1g.fc17, 1g.fc17, 0)
dnl RPMVERCMP(1g.fc17, 1.fc17, 1)
dnl RPMVERCMP(1.fc17, 1g.fc17, -1)

dnl Non-ascii characters are considered equal so these are all the same, eh...
dnl RPMVERCMP(1.1.α, 1.1.α, 0)
dnl RPMVERCMP(1.1.α, 1.1.β, 0)
dnl RPMVERCMP(1.1.β, 1.1.α, 0)
dnl RPMVERCMP(1.1.αα, 1.1.α, 0)
dnl RPMVERCMP(1.1.α, 1.1.ββ, 0)
dnl RPMVERCMP(1.1.ββ, 1.1.αα, 0)
"""


def convert(data):
    f = "RPMVERCMP("
    lines = [l for l in data.splitlines() if f in l]
    tuples = [
        tuple(c.strip() for c in l[len(f) + l.find(f) :].rstrip(")").split(",")) for l in lines
    ]
    return [(l, r, int(i)) for (l, r, i) in tuples]


@pytest.fixture
def rpm_data():
    return convert(DEFAULT_DATA)


def test_rpm_vercmp(rpm_data):
    for l, r, expected in rpm_data:
        actual = _rpm_vercmp(l, r)
        assert actual == expected, (l, r, actual, expected)
