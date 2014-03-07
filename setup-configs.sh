#!/bin/bash

check() {
        echo "Check: $1"
        if [ "$1" == "" ]; then
                echo "[ERROR] $2"
                exit 1
        fi
}

GUNICORN_WORKERS=${GUNICORN_WORKERS:-4}

if [ "$SETTINGS_FLAVOR" = "prod" ] ; then
    config=$(<config/config.yml);
    config=${config//boto_bucket: REPLACEME/boto_bucket: $S3_BUCKET};
    config=${config//s3_access_key: REPLACEME/s3_access_key: $AWS_ACCESS_KEY_ID};
    config=${config//s3_secret_key: REPLACEME/s3_secret_key: $AWS_SECRET_KEY};
    config=${config//s3_bucket: REPLACEME/s3_bucket: $S3_BUCKET};
    config=${config//s3_encrypt: REPLACEME/s3_encrypt: ${S3_ENCRYPT:-False}};
    config=${config//s3_secure: REPLACEME/s3_secure: ${S3_SECURE:-False}};
    printf '%s\n' "$config" >config/config.yml
elif [ "$SETTINGS_FLAVOR" = "openstack-swift" ] ; then
	check "$OS_USERNAME" 'Please specify $OS_USERNAME (or source your keystone_adminrc file)'
	check "$OS_PASSWORD" 'Please specify $OS_PASSWORD (or source your keystone_adminrc file)'
	check "$OS_TENANT_NAME" 'Please specify $OS_TENANT_NAME (or source your keystone_adminrc file)'
	check "$OS_AUTH_URL" 'Please specify $OS_AUTH_URL (or source your keystone_adminrc file)'
	check "$OS_REGION_NAME" 'Please specify $OS_REGION_NAME (e.g,: RegionOne)'
	check "$SWIFT_CONTAINER" 'Please specify $SWIFT_CONTAINER (e.g,: docker-registry)'
	check "$OS_GLANCE_URL" 'Please specify $OS_GLANCE_URL (e.g,: http://10.129.184.9:9292)'

    config=$(<config/config.yml);
    config=${config//swift_container: REPLACEME/swift_container: $SWIFT_CONTAINER};
    config=${config//swift_authurl: REPLACEME/swift_authurl: $OS_AUTH_URL};
    config=${config//swift_user: REPLACEME/swift_user: $OS_USERNAME};
    config=${config//swift_password: REPLACEME/swift_password: $OS_PASSWORD};
    config=${config//swift_tenant_name: REPLACEME/swift_tenant_name: $OS_TENANT_NAME};
    config=${config//swift_region_name: REPLACEME/swift_region_name: $OS_REGION_NAME};
    printf '%s\n' "$config" >config/config.yml
fi
