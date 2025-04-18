#!/bin/bash
PYTHON=${1:-python}

rm -rf BUILD BUILDROOT RPMS SRPMS SPECS
rm -rf insights_core.egg-info
cp MANIFEST.in.pkg MANIFEST.in
$PYTHON setup.py sdist
rpmbuild -ba -D "_topdir $PWD" -D "_sourcedir $PWD/dist" insights-core.spec
rm -rf dist BUILD BUILDROOT SPECS
git checkout MANIFEST.in
