import sys
import struct
import socket
from nfe import Link

class VirtualRouter:

    def __init__(self, nfe_ip, nfe_port, vrid):

        # The IP address of the NFE
        self.nfe_ip = nfe_ip

        # The port number of the NFE
        self.nfe_port = nfe_port

        # This virtual router's unique identifier
        self.virtual_router_id = vrid

        # Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Links
        self.links = []


    # Send data to NFE
    def send(self, data):
        self.sock.sendto(data, (self.nfe_ip, self.nfe_port))
    

    # Receive from NFE
    def recv(self, size):
        return self.sock.recv(size)
    
    
    def init(self):

        # Send 'init'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data = struct.pack("!i", 1) # message type = 0x1
        data += struct.pack("!i", self.virtual_router_id) # router ID
        sock.sendto(data, (self.nfe_ip, self.nfe_port))

        # Wait for 'init-reply'
        buffer = self.recv(4096)

        message_type = struct.unpack("!i", buffer[0:4])[0] # message type, 0x4
        nbr_links    = struct.unpack("!i", buffer[4:8])[0] # nbr links

        for i in range(nbr_links):
            link_id   =  struct.unpack("!i", buffer[8*(i+1)  :8*(i+1)+4])[0] # link_id
            link_cost =  struct.unpack("!i", buffer[8*(i+1)+4:8*(i+1)+8])[0] # link_cost
            link = Link(link_id, link_cost)
            self.links.append(link)


if __name__ == '__main__':
    _, nfe_ip, nfe_port, vrid = sys.argv
    vr = VirtualRouter(nfe_ip, int(nfe_port), int(vrid))
    vr.init()