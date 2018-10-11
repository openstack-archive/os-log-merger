#!/bin/sh

DATA=oslogmerger/tests/functional/data

fail_func() {
   echo FAILED test case $1 with output file $2
   rm -rf $3
   exit 1
}

run_test() {

   TEST=$1
   OUT_FILE=$2
   IN=$DATA/$TEST/in
   OUT=$DATA/$TEST/out
   TMP=$(mktemp -d)

   shift 2

   # replace TDATA with the "in" directory for the test
   PARAMS=$(echo $* | sed --expression=s%TDATA%${IN}%g)

   # run os-log-merger capturing the output, then conpare to what we expected
   os-log-merger $PARAMS >$TMP/out.log

   diff -u $OUT/$OUT_FILE $TMP/out.log || fail_func $TEST $OUT_FILE $TMP

   echo PASSED test case $TEST / $OUT_FILE
   rm -rf $TMP

}

run_test 01-simple no-alias.log TDATA/metadata-agent.log TDATA/l3-agent.log
run_test 01-simple alias.log  TDATA/metadata-agent.log:META TDATA/l3-agent.log:L3




