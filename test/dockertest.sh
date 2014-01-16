#!/bin/sh
cat $0
set -x

# Signal coverage report name, parsed by docker-ci
COVERAGE_FILE=$(date +"docker-registry-%Y%m%d%H%M%S")

cd /docker-registry
tox
exit_status=$?
if [ "$exit_status" -eq "0" ]; then
    mv reports /data/$COVERAGE_FILE; fi
exit $exit_status

