#!/bin/sh
#
# Control script for the restsrv daemon

ERROR=0
PYTHON=python
RESTD=restd.py
PIDFILE=/var/log/restsrv/restd.pid

# Determine if restsrv is already running.
RUNNING=0
if [ -f $PIDFILE ]; then
    PID=`cat $PIDFILE`
    if [ "x$PID" != "x" ]; then
        if kill -0 $PID 2>/dev/null ; then
            # a process using PID is running
            if ps -p $PID -o args | grep restsrv > /dev/null 2>&1; then
                # that process is restsrv itself
                RUNNING=1
            fi
        fi
    fi
    if ["$RUNNING" = "0"]; then
        STATUS="restsrv (stale pid file removed) not running"
        rm -f $PIDFILE
    fi
else
    STATUS="restsrv (no pid) not running"
fi

ARGS=""
COMMAND=""
for ARG in $@; do
    case $ARG in
    start|stop|restart|graceful|status)
        COMMAND=$ARG
        ;;
    *)
        ARGS="$ARGS $ARG"
    esac
    fi
done

case $COMMAND in
start)
    echo "Starting restd"
    $RESTD $ARGS
    ERROR=$?
    ;;
stop)
    echo "Stopping restd"
    kill -TERM `cat $PIDFILE`
    ERROR=$?
    ;;
restart)
    echo "Restarting restd"
    kill -HUP `cat $PIDFILE`
    ;;
graceful)
    echo "Gracefully restarting restd"
    kill -USR1 `cat $PIDFILE`
    ;;
status)
    echo $STATUS
    ;;
*)
    $RESTD $ARGS
    ERROR=$?
esac

exit $ERROR