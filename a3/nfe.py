import socket
import struct
import sys
import json

"""                                ___
                               ,-""   `.
                             ,'  _   e )`-._
                            /  ,' `-._<.===-'
                           /  /
                          /  ;
              _          /   ;
 (`._    _.-"" ""--..__,'    |
 <_  `-""                     \
  <`-                          :
   (__   <__.                  ;
     `-.   '-.__.      _.'    /
        \      `-.__,-'    _,'
         `._    ,    /__,-'
            ""._\__,'< <____
                 | |  `----.`.
                 | |        \ `.
                 ; |___      \-``
                 \   --<
                  `.`.<
                    `-'
                    oh, hello there
"""

class VirtualRouter: # holds data pertaining to UDP messages (and links (ip, port) of sender to a virtual router id)
    def __init__(self, address, router_id):
        self.address = address
        self.router_id = router_id


class Neighbour:  # router's neighbour
    def __init__(self, router_id, link):
        self.id = router_id
        self.link = link


class Router:
    def __init__(self, id):
        self.id = id
        self.neighbours = []
    def add_neighbour(self, other_router_id, link):
        self.neighbours.append(Neighbour(other_router_id, link))
    def __str__(self):
        return "Router #{}".format(self.id)


class Link:
    def __init__(self, id, cost):
        self.id = id
        self.cost = cost
    def __str__(self):
        return "<Link id={} cost={}>".format(self.id, self.cost)
    def __repr__(self):
        return str(self)


class Topology:
    def __init__(self, topology_description):
        self.routers = []
        self.links = []
        self.router_pairs = []
        self.original_topo_format = topology_description['links'] # needed for validation in other modules

        self.parse_topology_description(topology_description)
        self.validate_no_self_connection()
        self.validate_only_1_link()
        self.validate_connected()

    # why json.load() doesn't have a flag for this, I cannot fathom
    @staticmethod
    def dup_key_verify(ordered_pairs):
        dict = {}
        for key, val in ordered_pairs:
            if key in dict:
                raise Exception("JSON contains duplicate link id {}".format(key))
            else:
                dict[key] = val
        return dict

    def parse_topology_description(self, topology_description):
        # JSON part we care about looks like this:
        #  "link_id": [["router_id1", "router_id2"], "link_cost"]
        # "links":
        # {
        #     "1": [["1", "2"], "10"],
        #     "2": [["2", "3"], "20"],
        #     "3": [["1", "4"], "30"],
        #     "4": [["1", "3"], "55"]
        # }

        if(len(topology_description['links'])) == 0:
            raise Exception("The topology file seems to have no links; emulator needs at least one link between two routers")

        for link_id_data, link_data in topology_description['links'].items():
            link_id = int(link_id_data)
            router_id1, router_id2 = int(link_data[0][0]), int(link_data[0][1])
            link_cost = int(link_data[1])

            # populate link info
            link = Link(link_id, link_cost)
            self.links.append(link)

            # populate router info
            self.add_router_connection(router_id1, link, router_id2)
            self.add_router_connection(router_id2, link, router_id1)

            #for later validation
            self.router_pairs.append([router_id1, router_id2])

    def validate_no_self_connection(self):
        for r in self.routers:
            for neighbour in r.neighbours:
                if r.id == neighbour.id:
                    raise Exception("Router {} connects to itself".format(r.id))

    def validate_only_1_link(self):
        # validate only 1 link between two routers
        # sorting the pairs so that [2,1] becomes [1,2], such that comparison is simpler
        # it's awkward but sort() is in-place
        [pair.sort() for pair in self.router_pairs]

        # it's n^2 but given the expected size, good enough
        for index1, pair1 in enumerate(self.router_pairs):
            for index2, pair2 in enumerate(self.router_pairs):
                if index1 != index2 and pair1 == pair2:
                    raise Exception("There is more than 1 link between router ids {}".format(pair1))

    def validate_connected(self):
        # validate they're all connected
        visited = []
        to_be_visited = [self.routers[0]]
        while len(to_be_visited) > 0:
            to_be_visited_temp = []
            for router in to_be_visited:
                visited.append(router) # we visited this router
                for neighbour in router.neighbours:
                    # don't wanna to visit in the future what we've already visited or already planning to visit
                    neighbour_router_id = neighbour.id
                    already_visited_ids = [visited_router.id for visited_router in visited]
                    to_be_visited_ids = [visited_router.id for visited_router in (to_be_visited + to_be_visited_temp)]
                    if (neighbour_router_id not in already_visited_ids) and (neighbour_router_id not in to_be_visited_ids):
                        to_be_visited_temp.append(self.get_router_by_id(neighbour.id))
            to_be_visited = to_be_visited_temp

        if len(visited) != len(self.routers):
            raise Exception("The network seems to be partitioned i.e. there are 'islands' of inter-connected routers i.e. if we start at one router, we cannot visit every other router by hoping across links")

    def get_router_by_id(self, id):
        for router in self.routers:
            if router.id == id:
                return router
        raise Exception("Emulator has messed something while validating if the topology is connected, I'm sorry. Try another topology")

    def add_router_connection(self, router_id, link, other_router_id):
        router = None
        # does this router already exist?
        for r in self.routers:
            if r.id == router_id:
                router = r
                break
        else:
            # no? let's create it and add it to our collection
            router = Router(router_id)
            self.routers.append(router)
        router.add_neighbour(other_router_id, link)


def main():
    ip, port, topology = parse_args()
    listen_loop(ip, port, topology)



def parse_args():
    if len(sys.argv) != 4:
        print("Emulator needs to bind a port on localhost and read in a topology file")
        print("Usage: emulator ip port topology-file")
        print("e.g. emulator 127.0.0.1 8080 ./topology.json")
        sys.exit(-1)

    topology = None
    filepath = sys.argv[3]
    port = sys.argv[2]
    ip = sys.argv[1]
    try:
        port = int(port)
        if port > 65535 or port < 1:
            print("Argument error: first argument `port` needs to be a port number between 1 and 65535")
            sys.exit(-1)
    except ValueError:
        print("Argument error: first argument `port` needs to be a port number between 1 and 65535")
        sys.exit(-1)

    try:
        with open(filepath) as fd:
            topology = Topology(json.load(fd, object_pairs_hook=Topology.dup_key_verify))
    except Exception as e:
        print("Either couldn't open {} or couldn't parse JSON to construct desired topology: {}".format(filepath, str(e)))
        sys.exit(-1)

    return ip, port, topology


def listen_loop(ip, port, topology):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip, port))

    clients = []
    expected_clients = len(topology.routers)

    # Waiting for init messages; noting down which router id goes with which udp client
    print("Emulator is waiting for init messages from {} virtual routers (virtual routers are identified by their source IP and port)".format(expected_clients))
    while len(clients) != expected_clients:
        buffer, address = sock.recvfrom(4096)

        if len(buffer) < 4:
            print("UDP message is only {} byte(s) long. The emulator expects at least 4 bytes, as that's the size of the message type. Byte(s) received: {}".format(address, len(buffer), ' '.join('0x{:02x}'.format(byte) for byte in buffer)))
            continue

        message_type_buffer = buffer[:4]
        message_type = struct.unpack("!i", message_type_buffer)[0]
        if message_type not in [1,2,3]:
            print("UDP message has an unknown message_type (the first four bytes). Message type received: {} ({})".format(message_type, ' '.join('0x{:02x}'.format(byte) for byte in message_type_buffer)))
            continue

        if message_type != 1:
            print("The message type is valid but at this init phase, only Init messages are accepted.")
            continue

        if len(buffer) != 8:
            print("Init message is {} bytes long, expected to be 8 bytes".format(len(buffer)))
            continue

        router_id_buffer = buffer[4:8]
        router_id = struct.unpack("!i", router_id_buffer)[0]

        if router_id not in [r.id for r in topology.routers]:
            print("Received Init from router id {} but that router id is not in the topology, ignoring".format(router_id))
            continue

        if router_id in [c.router_id for c in clients]:
            print("Received Init from router id {} but that router id has already been received, ignoring".format(router_id))
            continue
        print("Received Init from virtual router id {} correctly, from udp (ip, port) {})".format(router_id, address))
        clients.append(VirtualRouter(address, router_id))

    # Sending the clients their info
    print("Emulator sending link info to virtual routers")
    for client in clients:
        router = topology.get_router_by_id(client.router_id)
        # int32 type (0x4)
        # int32 nbrLinks
        # int32 link_id
        # int32 link_cost
        router_links = [n.link for n in router.neighbours]

        data = struct.pack("!i", 4) # message type, 0x4
        data += struct.pack("!i", len(router_links))  # nbr links

        for link in router_links:
            data += struct.pack("!i", link.id) # link_id
            data += struct.pack("!i", link.cost)  # link_cost
        print("Sending data to virtual router {}".format(client.router_id))
        sock.sendto(data, client.address)

    # Forwarding
    print("Emulator forwarding traffic between virtual routers")

    while True:
        buffer, address = sock.recvfrom(4096)
        for client in clients:
            if client.address == address:
                router = topology.get_router_by_id(client.router_id)
                break
        else:
            print("Received data from virtual router (ip, port) {} but that virtual router did not send an init message during the init phase, ignoring".format(address))
            continue

        # int32 type (0x3)
        # int32 sender_id
        # int32 sender_link_id
        # int32 router_id
        # int32 router_link_id
        # int32 router_link_cost
        if len(buffer) != (6 * 4): # 7 fields, 32-bit (4 bytes) each
            print("Virtual Router {} - message length is {} but that doesn't match expected size, ignoring".format(router.id, len(buffer)))
            continue

        data = struct.unpack("!iiiiii", buffer)
        message_type = data[0]
        if message_type != 3:
            print("Virtual Router {} - message type is {} but that that's not the expected message type, ignoring".format(router.id, message_type))
            continue

        sender_link_id = data[2]

        # the virtual router whose LSA message we just received wants that LSA forwarded to some neighbouring router
        # virtual router  a link id gives
        # i.e. which neighbouring router is this going to, based on the link id of the sending router?
        for neighbour in router.neighbours:
            if sender_link_id == neighbour.link.id:
                # found the neighbour its destined for, let's find that neighbour's address in clients
                for client in clients:
                    if client.router_id == neighbour.id:
                        neighbour_address = client.address
                        break
                else:
                    raise Exception("The emulator couldn't find an address it should have been able to find, sorry. This is a bug. Try another topology")
                sock.sendto(buffer, neighbour_address)
                print(".", end='', flush=True)
                break
        else:
            print("Virtual Router {} - message cannot be forwarded, the sender_link_id is invalid, ignoring (emulator doesn't know through which of its link "
                  "the virtual router would like to send the message)".format(router.id))
            print(sender_link_id, router.id, [n.link.id for n in router.neighbours])
            continue

if __name__ == '__main__':
    main()

