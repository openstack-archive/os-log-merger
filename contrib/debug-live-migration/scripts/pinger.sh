#!/bin/sh

ping -i 0.5 $1 | \
    while read pong; do
        echo "$(date +%Y-%m-%d\ %H:%M:%S.%03N) pinger DEBUG $pong";
    done
