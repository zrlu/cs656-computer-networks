# CS 656 Computer Networks Assignment 3 (20578889)

# Python Version
Python 3.6.7.

# Dependency
No dependencies required. 

# Run NFE
```bash
 ./nfe.sh  localhost 2000 grading_topo.json # topology of 7 nodes
```

# Run virtual routers
```bash
./virtualrouter.sh localhost 2000 1 &
./virtualrouter.sh localhost 2000 2 &
./virtualrouter.sh localhost 2000 3 &
./virtualrouter.sh localhost 2000 4 &
./virtualrouter.sh localhost 2000 5 &
./virtualrouter.sh localhost 2000 6 &
./virtualrouter.sh localhost 2000 7 &
```