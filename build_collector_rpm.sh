#!/bin/bash
PYTHON=${1:-python}

rm -rf BUILD BUILDROOT RPMS SRPMS insights_core.egg-info
cp MANIFEST.in.collector MANIFEST.in
$PYTHON setup.py sdist
rpmbuild -ba -D "_topdir $PWD" -D "_sourcedir $PWD/dist" insights-collector.spec
rm -rf dist BUILD BUILDROOT
git checkout -- .
