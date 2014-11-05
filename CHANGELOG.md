# Docker-registry

## 0.9.0

 * "loose" dependencies mechanism (DEPS=loose environment var will let you install without strictly versioned dependencies)
 * enhanced python version compatibility
 * enhanced style checking
 * enhanced testing
 * uniformized various gunicorn start stances
 * enhanced/cleaned-up debugging
 * removed unused endpoints and code
 * improved documentation
 * more complete CORS support (as en extra)
 * boto/gevent bugfixes
 * documentation improvements

## 0.8.1

 * security fixes (path traversing prevention and token validation)

## 0.8.0

 * configuration rehaul: https://github.com/docker/docker-registry/pull/444 - beware this breaks API for the drivers, and the core package has been updated accordingly to denote that
 * better redis error handling
 * improved coverage
 * experimental (undocumented) new-relic bundle support
 * bugsnag and new-relic are now installable as setup-tools "extras"
 * centralized version and other meta-informations
 * port / host and other gunicorn options are more consistent
 * mirroring fixes
 * tarfile: pax header and xattr support
 * some dependency requirements loosen (extras, test and style requirements)

## 0.7.3

 * [BUGFIX] fixed default value for standalone to true

## 0.7.2

 * [BUGFIX] fixed configuration handling on standalone mode

## 0.7.1

 * [BUGFIX] storage_path is now handled correctly to the filesystem storage driver
 * [BUGFIX] change standalone header when in mirroring mode (prevents client from sending basic auth headers and overwriting token)

## 0.7

Major architecture rehaul, with potentially breaking changes:

 * alternate storage drivers are now implemented as independent pip packages in their own github repositories
 * mainline docker-registry now only provide file and s3 storage
 * all dependencies have been upgraded to the latest available version (specifically flask, gevent, bugsnag)
 * updated and cleaned-up Dockerfile now uses latest Ubuntu LTS
 * largely enhanced configuration mechanism (setup-configs.sh is no more)
 * cookies are no longer used
 * CORS is now enabled on a number of endpoints
 * extras requirements
 * Cloudfront redirect experimental support

 * [BUGFIX] unicode issues. Depending on the storage driver you are using, you may encounter unicode issues on already published content (likely garbled content).
 * [BUGFIX] content-length fix for bytes ranges
 * [BUGFIX] tar not being seeked back to 0 after lzma read attempt
 * [BUGFIX] inconsistent cache-control headers
