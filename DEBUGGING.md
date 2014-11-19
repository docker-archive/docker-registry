# TLDR

## Basics

`docker info`

`docker version`

Have docker daemon started in debug mode: `docker -d -D`


## Your private registry

Copy your launch command (eg: `docker run registry...`).

Copy your configuration file, if you are not using the default one.

Restart your private registry in debug mode (add `-e DEBUG=true` to your docker launch command).

`curl -svn --trace-time https://MYREGISTRY/_ping`

## Testing the speed of the official registry

```
VICTIM=tianon/speedtest
LAYER=71e62a8beff35bb692f64fb2e04bf1d6d19f5262500ad05dd95b1a95dcb5599d
SIGNATURE="`curl -iv -o/dev/null -H "X-Docker-Token: true" "https://registry.hub.docker.com/v1/repositories/$VICTIM/images" 2>&1 | awk '{print $3}' | grep signature | tr -d "\r\n"`"
CF_URL="`curl -iv -o/dev/null -H "Authorization: Token $SIGNATURE" https://registry-1.docker.io/v1/images/$LAYER/layer 2>&1 | awk '{print $3}' | grep cloudfront | sed -e 's/\r\n//g' | tr -d "\r\n"`"
echo "*************"
echo "CF delivery:"
echo "*************"
time curl  -svnoo --trace-time "${CF_URL}"

echo "*************"
echo "Resolving:"
echo "*************"
dig resolver-identity.cloudfront.net

echo "*************"
echo "RAW S3:"
echo "*************"
time curl -svnoo --trace-time http://kamilc-us-west-1.s3.amazonaws.com/test200m

echo "*************"
echo "RAW HTTP:"
echo "*************"
time curl -svnoo --trace-time http://mirrors.sonic.net/centos/7/isos/x86_64/CentOS-7.0-1406-x86_64-NetInstall.iso

```
