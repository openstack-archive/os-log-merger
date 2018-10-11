#!/bin/sh

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

DATA=oslogmerger/tests/functional/data

fail_func() {
   echo ${RED}FAILED${NC} test case $1 with output file $2
   cp $3/out.log $4/$2.failed_output
   echo $4/$2.failed_output created as reference
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
   PARAMS=$(echo $* | sed -e s%TDATA%${IN}%g)

   # run os-log-merger capturing the output, then conpare to what we expected
   os-log-merger $PARAMS >$TMP/out.log

   if [ ! -f $OUT/$OUT_FILE ]; then
        echo $RED
        echo output file $OUT/$OUT_FILE does not exist, creating an example file:
        echo ${OUT}/${OUT_FILE}.sample
        echo $NC
        cp $TMP/out.log ${OUT}/${OUT_FILE}.sample
        fail_func $TEST $OUT_FILE $TMP
   fi

   diff -u $OUT/$OUT_FILE $TMP/out.log || fail_func $TEST $OUT_FILE $TMP $OUT

   echo ${GREEN}PASSED${NC} test case $TEST / $OUT_FILE
   rm -rf $TMP

}

run_test 01-simple no-alias.log TDATA/metadata-agent.log TDATA/l3-agent.log
run_test 01-simple alias.log  TDATA/metadata-agent.log:META TDATA/l3-agent.log:L3

run_test 02-var-log-messages mixed.log TDATA/var_log_messages:messages \
                                       TDATA/nova-api.log:napi
run_test 02-var-log-messages mixed_ms.log TDATA/var_log_messages:messages \
                                          TDATA/var_log_messages_ms:messages2 \
                                          TDATA/nova-api.log:napi




