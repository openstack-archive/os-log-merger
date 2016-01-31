#!/bin/sh

# the br-int inteface is generally down
ip link set dev br-int up

# this will catch broadcast ARP packets
tcpdump -e -n -l -i br-int 'arp' 2>&1 | \
    while read line; do
        echo "$(date +%Y-%m-%d\ %H:%M:%S.%03N) tcpdump DEBUG $line";
    done
