#!/bin/bash
PYTHON=${1:-python}

rm -rf insights_core.egg-info insights.zip

cp MANIFEST.in.pkg MANIFEST.in
$PYTHON setup.py egg_info

mkdir -p tmp
cp -r insights_core.egg-info tmp/EGG-INFO
cp -r insights tmp

pushd tmp

find insights -path '*tests/*' -delete
find insights -name '*.pyc' -delete
git rev-parse --short HEAD > insights/COMMIT
find . -type f -exec touch -c -t 201801010000.00 {} \;
find . -type f -exec chmod 0444 {} \;
find . -type f -print | sort -df | xargs zip -X --no-dir-entries -r ../insights.zip

popd

rm -rf tmp
git checkout MANIFEST.in
