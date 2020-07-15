from packet import packet
from socket import *
import sys


# Create a socket for sending UDP packets
def sock_send():
    sock = socket(AF_INET, SOCK_DGRAM)
    return sock


# Create a socket for receiving UDP packets
def sock_recv(port):
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('', port))
    return sock


# Send packet using a socket
def send_packet(sock, addr, port, pack):
    udp_data = pack.get_udp_data()
    sock.sendto(udp_data, (addr, port))


# Receive packet from socket
def recv_packet(sock):
    udp_data, src_addr = sock.recvfrom(1024)
    pack = packet.parse_udp_data(udp_data)
    return pack
