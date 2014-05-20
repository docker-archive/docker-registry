# Docker-registry

## 0.7

Major architecture rehaul, with potentially breaking changes:

 * alternate storage drivers are now implemented as independent pip packages in their own github repositories
 * mainline docker-registry now only provide file and s3 storage
 * all dependencies have been upgraded to the latest available version (specifically flask, gevent, bugsnag)
 * updated and cleaned-up Dockerfile now uses latest Ubuntu LTS
 * largely enhanced configuration mechanism (setup-configs.sh is no more)
 * cookies are no longer used

 * [BUGFIX] unicode issues. Depending on the storage driver you are using, you may encounter unicode issues on already published content (likely garbled content).
 * [BUGFIX] content-length fix for bytes ranges

