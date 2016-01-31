#!/bin/sh

interface=$1

skip2() {
 # Yeah, I know tail --lines=+3 does exist, but that blocks
 # the output until the input finishes....
 read line
 read line
 while read line; do
	echo $line
 done
}

tcpdump_retry() {
    # removing dirt of the input that drives tcpdump crazy...
    interface=$1
    echo "Starting tcpdump retrier on interface '$interface'"
    while true;
    do
        tcpdump -i $interface -e -n -l 2>&1 | skip2
        sleep 1 # yield before retrying
    done
}

tcpdump_retry $interface| \
while read line; do
     echo "$(date +%Y-%m-%d\ %H:%M:%S.%03N) tcpdump DEBUG $line";
done

