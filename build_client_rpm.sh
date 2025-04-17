#!/bin/bash
PYTHON=${1:-python}

rm -rf dist BUILD BUILDROOT SPECS RPMS SRPMS
rm -rf insights_core.egg-info
cp MANIFEST.in.client MANIFEST.in

find insights -name '*.pyc' -delete
find insights -path '*tests/*' -delete
rm -rf insights/archive

git rev-parse --short HEAD > insights/COMMIT
$PYTHON setup.py sdist
rename insights_core insights-core dist/insights_core*

rpmbuild -ba -D "_topdir $PWD" -D "_sourcedir $PWD/dist" insights-core.spec

rm -rf dist BUILD BUILDROOT SPECS

git checkout MANIFEST.in insights
