#!/bin/bash

### BEGIN INIT INFO
# Provides:        docker-registry
# Required-Start:  $network $remote_fs $syslog
# Required-Stop:   $network $remote_fs $syslog
# Default-Start:   2 3 4 5
# Default-Stop:    0 1 6
# Short-Description: Start Docker-Registry
### END INIT INFO

# Author: Anastas Semenov <anapsix@random.io>
# Updated by: Dan Trujillo (dtrupenn)

PATH=/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/bin
. /etc/init.d/functions

# check is we are running as root
[ $(id -u) -ne 0 ] && echo "must run as root, exiting" && exit 1

# a way to figure out a service home directory, no matter where it's called from
self_path="$(readlink -e $0)"
self_dir="${self_path%%/${self_path##*/}}"

# load config if present/readable
[ -r /etc/default/docker-registry ] && . /etc/default/docker-registry

# MAKE SURE THIS PATH IS CORRECT
# it will default to repository location
# which will work if you are calling directly from repo path or even symlink to it
#DOCKER_REGISTRY_HOME=""  # path to docker-registry codebase

# set defaults if they are not set by config
[[ -z "$RUNAS" ]] && RUNAS=$(stat --format "%U" $self_path)                         # defaults to user owning this init script
[[ -z "$ACCESS_LOGFILE" ]] && ACCESS_LOGFILE=/var/log/docker/docker-registry.log    # will be chowned to $RUNAS
[[ -z "$ERROR_LOGFILE" ]] && ERROR_LOGFILE=/var/log/docker/docker-registry.log      # will be chowned to $RUNAS
[[ -z "$LOGFILE" ]] && LOGFILE=/var/log/docker/docker-registry.log                  # will be chowned to $RUNAS
[[ -z "$PIDFILE" ]] && PIDFILE=/var/run/docker-registry/docker-registry.pid         # path will created and chowned to $RUNAS
[[ -z "$LISTEN_IP" ]]            && LISTEN_IP="0.0.0.0"
[[ -z "$LISTEN_PORT" ]]          && LISTEN_PORT=5000
[[ -z "$GUNICORN_WORKERS" ]]     && GUNICORN_WORKERS=2
[[ -z "$DOCKER_REGISTRY_HOME" ]] && DOCKER_REGISTRY_HOME=${self_dir%/*}

NAME="Docker Registry"
DAEMON="/usr/bin/gunicorn"
DAEMON_OPTS="-D --error-logfile ${ERROR_LOGFILE} --access-logfile ${ACCESS_LOGFILE} --log-file ${LOGFILE} --pid ${PIDFILE} --max-requests 500 --graceful-timeout 3600 -t 3600 -k gevent -b ${LISTEN_IP}:${LISTEN_PORT} -w ${GUNICORN_WORKERS:-2} docker_registry.wsgi:application"

RED='\e[0;31m'
GREEN='\e[0;32m'
YELLOW='\e[0;33m'
PURPLE='\e[0;35m'
NC='\e[0m'

if [[ -z "${DOCKER_REGISTRY_HOME}" ]]; then
        echo "DOCKER_REGISTRY_HOME is not set, update this \"$(readlink -e $0)\" script or set it in /etc/default/docker-registry , exiting.."
	exit 1
else
	cd $DOCKER_REGISTRY_HOME
fi

#Loggers
log_daemon_msg() { logger "$@"; }
log_end_msg() { [ $1 -eq 0 ] && RES=OK; logger ${RES:=FAIL}; }

start_server() {
	[ -d ${PIDFILE%/*} ] || mkdir -p ${PIDFILE%/*} || return 1
	chown -R $RUNAS ${PIDFILE%/*} || return 1
	touch $LOGFILE && chown $RUNAS $LOGFILE || return 1
	touch $ERROR_LOGFILE && chown $RUNAS $ERROR_LOGFILE || return 1
	touch $ACCESS_LOGFILE && chown $RUNAS $ACCESS_LOGFILE || return 1
	#export SETTINGS_FLAVOR=prod
	RUN=`$DAEMON $DAEMON_OPTS`
	return $?
}

stop_server() {
	kill $(cat $PIDFILE)
	RETVAL=$?
	rm -f $PIDFILE
	return $RETVAL
}

reload_server() {
        kill -HUP $(cat $PIDFILE)
}

status_server() {
	if [ ! -r $PIDFILE ]; then
	  return 1
	elif ( kill -0 $(cat $PIDFILE) 2>/dev/null); then
	  return 0
	else
	  rm -f $PIDFILE
	  return 1
	fi
}

case $1 in
  start)
    if status_server; then
      /bin/echo -e "${NAME} is ${GREEN}already running${NC}" >&2
      exit 0
    else
      log_daemon_msg "Starting ${NAME}" "on port ${LISTEN_IP}:${LISTEN_PORT}"
      start_server
      sleep 1
      status_server
      log_end_msg $?
    fi
  ;;
  stop)
    if status_server; then
      log_daemon_msg "Stopping ${NAME}" # "on port ${LISTEN_IP}:${LISTEN_PORT}"
      stop_server
      log_end_msg $?
    else
      log_daemon_msg "${NAME}" "is not running"
      log_end_msg 0
    fi
  ;;
  restart)
    log_daemon_msg "Restarting ${NAME}" # "on port ${LISTEN_IP}:${LISTEN_PORT}"
    if status_server; then
        stop_server && sleep 1 || log_end_msg $?
    fi
    start_server
		log_end_msg $?
  ;;
  reload)
    if status_server; then
      log_daemon_msg "Reloading ${NAME}" # "on port ${LISTEN_IP}:${LISTEN_PORT}"
      reload_server
      log_end_msg $?
    else
      log_daemon_msg "${NAME}" "is not running"
      log_end_msg 1
    fi
  ;;
  status)
   /bin/echo -en "${NAME} is.. " >&2
   if status_server; then
     /bin/echo -e "${GREEN}running${NC}" >&2
     exit 0
   else
     /bin/echo -e "${RED}not running${NC}" >&2
     exit 1
   fi
  ;;
  *)
    echo "Usage: $0 {start|stop|restart|reload|status}" >&2
    exit 2
  ;;
esac

exit 0
