#!/bin/bash

cd $SERVICE_APPROOT

[ -d ~/env ] ||
    virtualenv --python=python2.7 ~/env || exit 1
. ~/env/bin/activate

pip install --download-cache=~/.pip-cache ./depends/docker-registry-core || exit 1
pip install --download-cache=~/.pip-cache file://`pwd`#egg=docker-registry[bugsnag] || exit 1

cp -R * ~/

cat > ~/profile << ENDPROFILE
. ~/env/bin/activate
ENDPROFILE
