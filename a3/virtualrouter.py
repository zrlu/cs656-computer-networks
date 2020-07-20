"""virtualrouter.py: A virtual router with routing table."""

__author__      = "Ze Ran Lu (zrlu@uwaterloo.ca)"

import sys
import struct
import socket
from nfe import Link
from collections import defaultdict
import heapq
from logger import get_logger

class VirtualRouter:

    def __init__(self, nfe_ip, nfe_port, vrid):

        # The IP address of the NFE
        self.nfe_ip = nfe_ip

        # The port number of the NFE
        self.nfe_port = nfe_port

        # This virtual router's unique identifier
        self.router_id = vrid

        # Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Connected links
        self.neighbors = set()

        # Routing table
        self.routing_table = {}

        # A graph representing the topology database
        self.graph = defaultdict(dict)

        # All links
        self.links = defaultdict(set)

        # Link costs
        self.link_costs = {}

        # All received LSA
        self.lsa_seen_before = set()

        # Topology file
        self.topology_file = get_logger('topology_{}'.format(self.router_id))

        # Used to avoid duplicate topology when writing
        self.topology_update_buffer = ''

        # Routingtable file
        self.routingtable_file = get_logger('routingtable_{}'.format(self.router_id))

        # Used to avoid duplicate routing table when writing
        self.routingtable_update_buffer = ''


    # Send data to NFE
    def send(self, data):
        self.sock.sendto(data, (self.nfe_ip, self.nfe_port))


    # Receive from NFE
    def recv(self, size):
        return self.sock.recv(size)
    
    
    # Init phase
    def init(self):

        # Send 'init'
        data = struct.pack("!i", 1) # message type = 0x1
        data += struct.pack("!i", self.router_id) # router ID
        self.send(data)

        # Wait for 'init-reply'
        buffer = self.recv(4096)
        message_type = struct.unpack("!i", buffer[0:4])[0] # message type, 0x4
        nbr_links    = struct.unpack("!i", buffer[4:8])[0] # nbr links

        for i in range(nbr_links):
            link_id   =  struct.unpack("!i", buffer[8*(i+1)  :8*(i+1)+4])[0] # link_id
            link_cost =  struct.unpack("!i", buffer[8*(i+1)+4:8*(i+1)+8])[0] # link_cost
            self.neighbors.add(link_id)
            self.link_costs[link_id] = link_cost


    # Mark LSA as seen before
    def mark_as_seen_before(self, other_lsa):
        self.lsa_seen_before.add((other_lsa['router_id'], other_lsa['router_link_id'], other_lsa['router_link_cost']))


    # Check if this LSA is seen before
    def seen_before(self, other_lsa):
        return (other_lsa['router_id'], other_lsa['router_link_id'], other_lsa['router_link_cost']) in self.lsa_seen_before


    # Update graph
    def update_graph(self):
        for link_id, vertices in self.links.items():
            if len(vertices) == 2:
                v1, v2 = tuple(vertices)
                self.graph_add_link(v1, v2, link_id, self.link_costs[link_id])


    # Add a link to the graph
    def graph_add_link(self, u, v, link_id, link_cost):
        if u == v:
            return
        self.graph[u][v] = (link_id, link_cost)
        self.graph[v][u] = (link_id, link_cost)


    # Serialize a LSA message
    def LSA_serialize(self, sender_id, sender_link_id, router_id, router_link_id, router_link_cost):
        data =  struct.pack("!i", 3) # messate type = 0x3
        data += struct.pack("!i", sender_id) # sender ID
        data += struct.pack("!i", sender_link_id) # sender link id
        data += struct.pack("!i", router_id) # router ID
        data += struct.pack("!i", router_link_id) # router link id
        data += struct.pack("!i", router_link_cost) # router link cost
        return data


    # Parse LSA bytes and returns a dict
    def LSA_parse(self, buffer):
        lsa = {}
        lsa['message_type']     = struct.unpack("!i", buffer[0 : 4])[0] # message type, 0x3
        lsa['sender_id']        = struct.unpack("!i", buffer[4 : 8])[0] # sender ID
        lsa['sender_link_id']   = struct.unpack("!i", buffer[8 :12])[0] # sender link id
        lsa['router_id']        = struct.unpack("!i", buffer[12:16])[0] # router ID
        lsa['router_link_id']   = struct.unpack("!i", buffer[16:20])[0] # router link id
        lsa['router_link_cost'] = struct.unpack("!i", buffer[20:24])[0] # router link cost
        return lsa

    
    # Run dijkstra, returns the cost to target and next hop
    def dijkstra(self, graph, source, target):
        cost = defaultdict(lambda: float('inf'))
        cost[source] = 0
        parent = defaultdict(lambda: None)
        parent[source] = -1
        pq = [(0, source)]
        visited = set()
        
        while pq:
            current_cost, u = heapq.heappop(pq) # extract min

            if u in visited:
                continue
            visited.add(u)

            if u == target: # Early stop
                break

            for v in graph[u]:
                new_cost = current_cost + graph[u][v][1]
                if new_cost < cost[v]:
                    parent[v] = u
                    cost[v] = new_cost
                    heapq.heappush(pq, (new_cost, v))

        u, v = parent[target], target
        while u != source and u is not None:
            v = u
            u = parent[u] # Walk backward to find the next hop

        return cost[target], v


    # Update the graph and table based on the LSA received
    def update_from_LSA(self, lsa):

        # Update the graph
        self.links[lsa['router_link_id']].add(lsa['router_id'])
        self.links[lsa['sender_link_id']].add(lsa['sender_id'])
        self.links[lsa['sender_link_id']].add(self.router_id)
        self.link_costs[lsa['router_link_id']] = lsa['router_link_cost']
        self.update_graph()

        print(self.links)

        if len(self.graph) > 0:
            self.update_topology_file()

        graph = dict(self.graph)
        vertices = graph.keys()

        try:
            for target in vertices:
                if target != self.router_id:
                    # Update the routing table
                    cost, next_hop = self.dijkstra(graph, self.router_id, target)
                    self.routing_table[target] = (cost, next_hop)
        except KeyError:
            pass

        if len(self.routing_table) > 0:
            self.update_routingtable_file()

    
    # Propagate the LSA to other routers
    def propagate(self, router_id, router_link_id, router_link_cost):
        for link_id in self.neighbors:
            lsa_bytes = self.LSA_serialize(self.router_id, link_id, router_id, router_link_id, router_link_cost)
            print('Sending(F):{}'.format(self.LSA_str(self.LSA_parse(lsa_bytes))))
            self.send(lsa_bytes)


    # Get a string representation of LSA
    def LSA_str(self, lsa):
        fmt = 'SID({sender_id}),SLID({sender_link_id}),RID({router_id}),RLID({router_link_id}),LC({router_link_cost})'
        return fmt.format(**lsa)
    

    # Update the topology into file
    def update_topology_file(self):
        temp = ''
        if self.topology_update_buffer != '':
            temp += '\n'
        temp += 'TOPOLOGY'
        entries = []
        for router1 in self.graph:
            for router2 in self.graph[router1]:
                entries.append((router1, router2, self.graph[router1][router2][0], self.graph[router1][router2][1]))
        entries.sort()
        for entry in entries:
            temp += '\nrouter:{},router:{},linkid:{},cost:{}'.format(*entry)
        if self.topology_update_buffer != temp:
            self.topology_update_buffer = temp
            self.topology_file.info(self.topology_update_buffer)


    # Update the routing table file
    def update_routingtable_file(self):
        temp = ''
        if self.routingtable_update_buffer != '':
            temp += '\n'
        temp += 'ROUTING'
        entries = []
        for dest, (total_cost, next_hop) in self.routing_table.items():
            entries.append((dest, next_hop, total_cost))
        entries.sort()
        for entry in entries:
            temp += '\n{}:{},{}'.format(*entry)
        if self.routingtable_update_buffer != temp:
            self.routingtable_update_buffer = temp
            self.routingtable_file.info(self.routingtable_update_buffer)


    # Forwarding phase
    def forward(self):

        # Initial broadcast
        for link_id in self.neighbors:
            lsa_bytes = self.LSA_serialize(self.router_id, link_id, self.router_id, link_id, self.link_costs[link_id])
            print('Sending(E):{}'.format(self.LSA_str(self.LSA_parse(lsa_bytes))))
            self.send(lsa_bytes)
        
        while True:
            buffer = self.recv(4096)
            lsa = self.LSA_parse(buffer)
            print('Received:{}'.format(self.LSA_str(lsa)))

            # Drop LSA if it was seen before, otherwise add to record
            if self.seen_before(lsa):
                print('Dropping:{}'.format(self.LSA_str(lsa)))
                continue

            self.mark_as_seen_before(lsa)

            # Forward the LSA to neighbors, then update this router's states using this LSA, 
            self.propagate(lsa['router_id'], lsa['router_link_id'], lsa['router_link_cost'])
            self.update_from_LSA(lsa)


if __name__ == '__main__':
    _, nfe_ip, nfe_port, vrid = sys.argv
    vr = VirtualRouter(nfe_ip, int(nfe_port), int(vrid))
    vr.init()
    vr.forward()