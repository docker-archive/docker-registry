#!/bin/sh
if [ "$SETTINGS_FLAVOR" = "prod" ] then
	sed -i /docker-registry/config.yml -e "s/s3_access_key: REPLACEME/s3_access_key: $AWS_ACCESS_KEY_ID"
	sed -i /docker-registry/config.yml -e "s/s3_secret_key: REPLACEME/s3_secret_key: $AWS_SECRET_KEY"
	sed -i /docker-registry/config.yml -e "s/s3_bucket: REPLACEME/s3_bucket: $S3_BUCKET"
	sed -i /docker-registry/config.yml -e "s/^secret_key: REPLACEME/secret_key: $WORKER_SECRET_KEY"
fi

gunicorn --access-logfile - --debug --max-requests 100 --graceful-timeout 3600 -t 3600 -k gevent -b 0.0.0.0:5000 -w 2 wsgi:application



