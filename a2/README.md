# CS 656 Assignment 2 (20578889)

## Python Version
- Python 3.6.7
- Python 3.6.9

## Test environment
Sender machine: `ubuntu1804-004`, IP: `129.97.167.47`
Emulator machine: `ubuntu1804-002`, IP: `129.97.167.34`
Receiver machine: `ubuntu1804-008`, IP: `129.97.167.27`


## How to run

Receiver machine:
```bash
./receiver.sh <emulator_ip> <emulator_backward_port> <data_recv_port> <write_path>

# Example
./receiver.sh 129.97.167.34 4000 7654 large_copy.txt
```

Emulator machine:
```bash
./nEmulator-linux386 <emulator_forward_port> <receiver_ip> <data_recv_port> <emulator_backward_port> <sender_ip> <ack_port> <max_delay> <discard_probability> <verbose>

# Example
./nEmulator-linux386 5000 129.97.167.27 7654 4000 129.97.167.47 9898 5 0.4 0
```

Sender machine:
```bash
./sender.sh <emulator_ip> <emulator_foward_port> <ack_port> <read_path>

# Example
./sender.sh 129.97.167.34 5000 9898 large.txt
```

Compare (should output nothing):
```
cmp large.txt large_copy.txt
```