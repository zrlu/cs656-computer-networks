from packet import packet
from socket import *


def sock_send():
    sock = socket(AF_INET, SOCK_DGRAM)
    return sock


def sock_recv(port):
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('', port))
    return sock


def send_packet(sock, addr, port, pack):
    udp_data = pack.get_udp_data()
    sock.sendto(udp_data, (addr, port))


def recv_packet(sock):
    udp_data, src_addr = sock.recvfrom(1024)
    pack = packet.parse_udp_data(udp_data)
    return pack
