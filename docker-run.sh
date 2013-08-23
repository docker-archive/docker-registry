#!/bin/bash
if [[ -z "$GUNICORN_WORKERS" ]]
	then
		GUNICORN_WORKERS=2
fi

if [ "$SETTINGS_FLAVOR" = "prod" ] 
	then
		config=$(<config.yml); 
		config=${config//s3_access_key: REPLACEME/s3_access_key: $AWS_ACCESS_KEY_ID}; 
		config=${config//s3_secret_key: REPLACEME/s3_secret_key: $AWS_SECRET_KEY}; 
		config=${config//s3_bucket: REPLACEME/s3_bucket: $S3_BUCKET}; 
		config=${config//secret_key: REPLACEME/secret_key: $WORKER_SECRET_KEY}; 
		printf '%s\n' "$config" >config.yml
fi

gunicorn --access-logfile - --debug --max-requests 100 --graceful-timeout 3600 -t 3600 -k gevent -b 0.0.0.0:5000 -w $GUNICORN_WORKERS wsgi:application



