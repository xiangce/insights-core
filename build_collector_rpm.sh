#!/bin/bash
PYTHON=${1:-python}

set -xe

rm -rf BUILD BUILDROOT RPMS SRPMS insights_core.egg-info
# RPM is only for collector for now, remove all depedencies for data processing
sed -i -e '/cachecontrol/d' -e '/defusedxml/d' -e '/jinja2/d' -e '/lockfile/d' -e '/redis/d' -e '/setuptools;/d' pyproject.toml setup.py
cp MANIFEST.in.collector MANIFEST.in
$PYTHON setup.py sdist
rpmbuild -D "_topdir $PWD" -D "_sourcedir $PWD/dist" -ba insights-collector.spec
rm -rf dist BUILD BUILDROOT
git checkout -- .
