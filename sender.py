import udp
from packet import packet
import threading
import time
from logger import get_logger
import pdb

class Sender:

    def __init__(self, emu_addr, emu_port, ack_port, fn, ws=10, seq_mod=packet.SEQ_NUM_MODULO, mdl=packet.MAX_DATA_LENGTH):
        self.max_packet_data_size = mdl
        self.emulator_addr = emu_addr
        self.emulator_port = emu_port
        self.ack_port = ack_port
        self.window_size = ws
        self.seq_modulo = seq_mod
        self.filename = fn
        self.base = 0
        self.nextseqnum = 0
        self.sndpkt = [None for _ in range(self.seq_modulo)]
        self.timer = None
        self.total_acked = 0
        self.sock_send = udp.sock_send()
        self.sock_recv = udp.sock_recv(self.ack_port)
        self.seqnum_log = get_logger('seqnum')
        self.ack_log = get_logger('ack')
        self.timer_lock = threading.Lock()
        self.state_lock = threading.Lock()

    
    def chunker(self):
        with open(self.filename, 'r') as file:
            chunk = file.read(self.max_packet_data_size)
            while chunk:
                yield chunk
                chunk = file.read(self.max_packet_data_size)

    def incr_nextseqnum(self):
        self.nextseqnum = (self.nextseqnum + 1) % self.seq_modulo

    def unacked(self):
        start = self.base
        end = self.nextseqnum
        if start <= end:
            for i in range(start, end):
                yield i
        else:
            for i in range(start, self.seq_modulo):
                yield i
            for i in range(0, end):
                yield i


    def timer_start(self):
        if self.timer is not None:
            self.timer_stop()
        self.timer = threading.Timer(0.1, self.timeout_event)
        self.timer.start()


    def timeout_event(self):
        self.timer_start()
        for i in self.unacked():
            self.udt_send(self.sndpkt[i])


    def timer_stop(self):
        self.timer.cancel()

    
    def udt_send(self, pack):
        udp.send_packet(self.sock_send, self.emulator_addr, self.emulator_port, pack)
        self.seqnum_log.info('{}'.format(pack.seq_num))

    
    def udt_recv(self):
        return udp.recv_packet(self.sock_recv)


    def rdt_send(self, data):

        if self.base <= self.nextseqnum and self.nextseqnum < self.base + self.window_size:
            self.sndpkt[self.nextseqnum] = packet.create_packet(self.nextseqnum, data)
            self.udt_send(self.sndpkt[self.nextseqnum])
            if self.base == self.nextseqnum:
                self.timer_start()
            self.incr_nextseqnum()
            return False
        else:
            return True
        
    
    def send_eot(self):
        eot = packet.create_eot(self.nextseqnum)
        self.udt_send(eot)
        self.incr_nextseqnum()


    def rdt_rcv(self, recv_pack):
        self.base = (recv_pack.seq_num + 1) % self.seq_modulo
        if self.base == self.nextseqnum:
            self.timer_stop()
        else:
            self.timer_start()
        self.total_acked += 1


    def sending_thread(self):
        self.state_lock.acquire()
        for chunk in self.chunker():
            while self.rdt_send(chunk):
                time.sleep(0.1)
        self.send_eot()
        self.state_lock.release()
        print('sending_thread done')


    def wait_loop(self):
        while True:
            pack = self.udt_recv()
            if pack.type == 0:
                self.rdt_rcv(pack)
                self.ack_log.info('{}'.format(pack.seq_num))
            if pack.type == 2:
                break


    def start(self):
        t1 = threading.Thread(target=self.sending_thread)
        t1.start()

        self.wait_loop()

        self.sock_recv.close()
        self.sock_send.close()

        t1.join()

        self.timer_stop()
        return 0


if __name__ == '__main__':
    s = Sender('127.0.0.1', 5000, 9898, 'large.txt')
    ret = s.start()
    exit(ret)



        