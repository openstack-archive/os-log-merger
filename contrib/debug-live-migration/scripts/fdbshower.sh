#!/bin/sh

fdb_show_loop() {
    while true;
    do
        ovs-appctl fdb/show br-int
        ovs-ofctl dump-flows br-tun table=20 | grep "priority=1"
        sleep 1 # yield before retrying
    done
}

fdb_show_loop | \
while read line; do
     echo "$(date +%Y-%m-%d\ %H:%M:%S.%03N) ovs-fdb DEBUG $line";
done

