#!/bin/bash

cd $SERVICE_APPROOT

[ -d ~/env ] ||
    virtualenv --python=python2.7 ~/env || exit 1
. ~/env/bin/activate

[ -f requirements.txt ] &&
    pip install --download-cache=~/.pip-cache -r requirements.txt || exit 1

cp -R * ~/

cat > ~/profile << ENDPROFILE
. ~/env/bin/activate
export PYTHONPATH=~/
ENDPROFILE
