import sys
import struct
import socket
from nfe import Link
from collections import defaultdict
import heapq
import pdb
import copy

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

        # Links
        self.links = {}

        # Routing table
        self.routing_table = {}

        # A graph representing the topology database
        self.graph = defaultdict(dict)

        # All received LSA
        self.all_lsa = []


    # Send data to NFE
    def send(self, data):
        self.sock.sendto(data, (self.nfe_ip, self.nfe_port))


    # Receive from NFE
    def recv(self, size):
        return self.sock.recv(size)
    
    
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
            self.links[link_id] = link_cost


    # Check if this LSA is seen before
    def seen_before(self, other):
        for lsa in self.all_lsa:
            if lsa['router_id'] == other['router_id'] and \
               lsa['router_link_id'] == other['router_link_id'] and \
               lsa['router_link_cost'] == other['router_link_cost']:
                return True
        return False


    # Add a link to the graph
    def add_link(self, u, v, cost):
        if u == v:
            return
        self.graph[u][v] = cost
        self.graph[v][u] = cost


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
            if u == target:
                break

            for v in graph[u]:
                new_cost = current_cost + graph[u][v]
                if new_cost < cost[v]:
                    parent[v] = u
                    cost[v] = new_cost
                    heapq.heappush(pq, (new_cost, v))

        u, v = parent[target], target
        while u != source:
            v = u
            u = parent[u]

        return cost[target], v


    # Update the graph and table based on the LSA received
    def update_from_LSA(self, lsa):

        # Update the graph
        self.add_link(lsa['sender_id'], lsa['router_id'], lsa['router_link_cost'])

        graph = dict(self.graph)
        vertices = graph.keys()

        for target in vertices:
            if target != self.router_id:
                try:
                    cost, next_hop = self.dijkstra(graph, self.router_id, target)
                    self.routing_table[target] = (cost, next_hop)

                except KeyError:
                    pass

        print(self.routing_table)

    
    # Propagate the LSA to other routers
    def propagate(self, router_id, router_link_id, router_link_cost):
        for link_id, _ in self.links.items():
            lsa_bytes = self.LSA_serialize(self.router_id, link_id, router_id, router_link_id, router_link_cost)
            self.send(lsa_bytes)


    # Forwarding phase
    def forward(self):

        # Initial broadcast
        for link_id, link_cost in self.links.items():
            lsa_bytes = self.LSA_serialize(self.router_id, link_id, self.router_id, link_id, link_cost)
            self.send(lsa_bytes)
        
        while True:
            buffer = self.recv(4096)
            lsa = self.LSA_parse(buffer)

            # Drop LSA if it was seen before, otherwise add to record
            if self.seen_before(lsa):
                continue
            else:
                self.all_lsa.append(lsa)                

            # Update this router's states using this LSA, then forward it to neighbors
            self.update_from_LSA(lsa)
            self.propagate(lsa['router_id'], lsa['router_link_id'], lsa['router_link_cost'])


if __name__ == '__main__':
    _, nfe_ip, nfe_port, vrid = sys.argv
    vr = VirtualRouter(nfe_ip, int(nfe_port), int(vrid))
    vr.init()
    vr.forward()