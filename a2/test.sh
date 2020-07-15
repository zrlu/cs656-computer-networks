#!/bin/bash

# test in local machine

emu_port_fow=5000
ack_port=9898
emu_port_bak=4000
in_port=7654
emu_ip=127.0.0.1
sender_ip=127.0.0.1
receiver_ip=127.0.0.1
TIMEFORMAT=%R

function killall {
    pkill nEmulator-linux
    pkill python3
    pkill sender.sh
    pkill receiver.sh
}

function test {

    killall 2>/dev/null
    infile=$1
    outfile="out/$1.2"
    maxdelay=$2
    discardprob=$3

    ./nEmulator-linux386 $emu_port_fow $receiver_ip $in_port $emu_port_bak $sender_ip $ack_port $maxdelay $discardprob 0 &
    ./receiver.sh $emu_ip $emu_port_bak $in_port $outfile &
    ./sender.sh $emu_ip $emu_port_fow $ack_port $infile

    echo $1 $2 $3 $(cat time.log)
    cmp $infile $outfile
    killall 2>/dev/null
}

function baseline {
    echo $1 baseline
    test $1 1 0
}

function nodelay {
    echo $1 nodelay
    test $1 1 0.1
    test $1 1 0.2
    test $1 1 0.3
    test $1 1 0.4
    test $1 1 0.5
}

function nodiscard {
    echo $1 nodiscard
    test $1 10 0
    test $1 20 0.1
    test $1 30 0.2
    test $1 40 0.3
    test $1 50 0.4
}

function delayanddiscard {
    echo $1 delayanddiscard
    test $1 20 0.1
    test $1 20 0.2
    test $1 20 0.3
    test $1 40 0.1
    test $1 40 0.2
    test $1 40 0.3
}

function testfile {
    baseline $1
    nodelay $1
    nodiscard $1
    delayanddiscard $1
}

testfile tiny.txt
testfile small.txt
testfile medium.txt
testfile large.txt