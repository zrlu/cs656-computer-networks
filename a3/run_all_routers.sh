#!/bin/bash

./virtualrouter.sh localhost 2000 1 &
./virtualrouter.sh localhost 2000 2 &
./virtualrouter.sh localhost 2000 3 &
./virtualrouter.sh localhost 2000 4 &
./virtualrouter.sh localhost 2000 5 &
./virtualrouter.sh localhost 2000 6 &
./virtualrouter.sh localhost 2000 7 &

sleep 10

pkill virtualrouter.sh
pkill python3