#!/bin/sh
echo "$(date +%Y-%m-%d\ %H:%M:%S.%03N) $(hostname -s) DEBUG $*" \
                        >>/var/log/ansible-debug.log
