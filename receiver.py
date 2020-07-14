import udp
from packet import packet
import time
from logger import get_logger

class Receiver:

    def __init__(self, emu_addr, emu_port, in_port, fn, seq_mod=packet.SEQ_NUM_MODULO):
        self.emulator_addr = emu_addr
        self.emulator_port = emu_port
        self.in_port = in_port
        self.seq_modulo = seq_mod
        self.expectedseqnum = 0
        self.total_acked = 0
        self.sndpkt = packet.create_ack(0)
        self.sock_send = udp.sock_send()
        self.sock_recv = udp.sock_recv(self.in_port)
        self.arrival_log = get_logger('arrival')
        self.filename = fn

    
    def incr_expectedseqnum(self):
        self.expectedseqnum = (self.expectedseqnum + 1) % self.seq_modulo


    def udt_send(self, pack):
        udp.send_packet(self.sock_send, self.emulator_addr, self.emulator_port, pack)
    

    def udt_recv(self):
        return udp.recv_packet(self.sock_recv)


    def rdt_rcv(self, recv_pack, file):
        data = recv_pack.data
        file.write(data)
        if self.total_acked == 0 and recv_pack.seq_num != 0:
            self.sndpkt = packet.create_ack(-1)
        else:
            self.sndpkt = packet.create_ack(self.expectedseqnum)
        self.udt_send(self.sndpkt)
        self.total_acked += 1
        self.incr_expectedseqnum()


    def send_eot(self):
        self.sndpkt = packet.create_eot(self.expectedseqnum)
        self.udt_send(self.sndpkt)

    def loop(self):
        with open(self.filename, 'w') as file:
            while True:
                pack = self.udt_recv()
                if pack:
                    if pack.type == 1 and pack.seq_num == self.expectedseqnum:
                        self.arrival_log.info('{}'.format(pack.seq_num))
                        self.rdt_rcv(pack, file)
                    elif pack.type == 2:
                        break

        self.send_eot()
        self.sock_send.close()
        self.sock_recv.close()


if __name__ == '__main__':
    r = Receiver('127.0.0.1', 4000, 7654, 'tiny_copy.txt')
    r.loop()