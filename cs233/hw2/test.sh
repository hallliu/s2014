#!/bin/bash

for f in `ls tests | grep "\.in"`
do
    ./run.sh < tests/$f | diff -u --ignore-all-space `echo tests/$f | sed 's/\.in/\.out/'` -
done
