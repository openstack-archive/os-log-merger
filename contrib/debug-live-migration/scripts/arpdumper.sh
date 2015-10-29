#!/bin/sh


tcpdump -e -n -l -i br-int arp 2>&1 | \
    while read line; do
        echo "$(date +%Y-%m-%d\ %H:%M:%S.%03N) tcpdump DEBUG $line";
    done
