import udp
from packet import packet
import threading
import time
from logger import get_logger
import sys


class Sender:

    """
    A Sender class for the GBN protocol
    """

    def __init__(self, emu_addr, emu_port, ack_port, fn, ws=10, seq_mod=packet.SEQ_NUM_MODULO, mdl=packet.MAX_DATA_LENGTH):

        # Maximum packet data size, default is packet.MAX_DATA_LENGTH (500)
        self.max_packet_data_size = mdl

        # IP address of the emulator
        self.emulator_addr = emu_addr

        # Port of the emulator (foward direction)
        self.emulator_port = emu_port

        # Port to receive acks
        self.ack_port = ack_port

        # Window size, default is 10
        self.window_size = ws

        # Sequence number modulo, default to packet.SEQ_NUM_MODULO (32)
        self.seq_modulo = seq_mod

        # Filename for reading
        self.filename = fn

        # State base
        self.base = 0

        # State nextseqnum
        self.nextseqnum = 0

        # Macket buffer for sending
        self.sndpkt = [None for _ in range(self.seq_modulo)]

        # A single timer
        self.timer = None

        # Socket for sending UDP packets
        self.sock_send = udp.sock_send()

        # Socket for receiving UDP packets
        self.sock_recv = udp.sock_recv(self.ack_port)

        # Log file for seq num
        self.seqnum_log = get_logger('seqnum')

        # Log file for acks
        self.ack_log = get_logger('ack')

        # If this flag is set, an EOT should be send to the receiver when there is no unacked packet
        self.should_send_eot = False

    # Returns an iterator of chunks
    def chunker(self):
        with open(self.filename, 'r') as file:
            chunk = file.read(self.max_packet_data_size)
            while chunk:
                yield chunk
                chunk = file.read(self.max_packet_data_size)


    # Increment the nextseqnum by one
    def incr_nextseqnum(self):
        self.nextseqnum = (self.nextseqnum + 1) % self.seq_modulo


    # Returns an iterator of unacked seq num
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

    # Start the timer, if exists, reset the timer
    def timer_start(self):
        if self.timer is not None:
            self.timer_stop()
        self.timer = threading.Timer(0.1, self.timeout_event)
        self.timer.start()


    # Call this function when timeout event occurs
    def timeout_event(self):
        self.timer_start()
        for i in self.unacked():
            pack = self.sndpkt[i]
            if pack is not None:
                self.udt_send(self.sndpkt[i])


    # Stop the timer
    def timer_stop(self):
        self.timer.cancel()

    
    # Unreliabily send an UDP packet to the emulator
    def udt_send(self, pack):
        udp.send_packet(self.sock_send, self.emulator_addr, self.emulator_port, pack)
        self.seqnum_log.info('{}'.format(pack.seq_num))

    
    # Unreliabily receive an UDP packet from the emulator
    def udt_recv(self):
        return udp.recv_packet(self.sock_recv)


    # Called for each chunk
    # See the FSM in the textbook
    def rdt_send(self, data):

        # If the window is not full
        if self.base <= self.nextseqnum and self.nextseqnum < self.base + self.window_size:

            # Create a packet
            self.sndpkt[self.nextseqnum] = packet.create_packet(self.nextseqnum, data)

            # Unreliabily send the packet
            self.udt_send(self.sndpkt[self.nextseqnum])

            # If the window is empty, no unacked packet
            if self.base == self.nextseqnum:
                self.timer_start()

            # Increment the nextseqnum
            self.incr_nextseqnum()

            # Not need to retry
            return False
        
        # If the window is full, return a signal for retry after a timeout
        else:
            return True
        
    
    # Send an EOT
    def send_eot(self):
        eot = packet.create_eot(self.nextseqnum)
        self.udt_send(eot)
        self.incr_nextseqnum()


    # Called when a packet is received
    # See the FSM in the textbook
    def rdt_rcv(self, recv_pack):

        # Update base
        self.base = (recv_pack.seq_num + 1) % self.seq_modulo

        # If the window is empty, no unacked packet
        if self.base == self.nextseqnum:

            # Stop the timer
            self.timer_stop()

            # If the flag is set, meaning that all chunks have been visited
            if self.should_send_eot:

                # Send EOT
                self.send_eot()

        else:
            self.timer_start()


    # A thread for sending packet
    def sending_thread(self):

        # For each chunk in the file
        for chunk in self.chunker():

            # Repeatedly send
            while self.rdt_send(chunk):

                # Window is full, retry after a timeout
                time.sleep(0.1)

        # All chunks have been visited, an EOT should be sent
        self.should_send_eot = True


    # Wait for packets, this runs in the main thread
    def wait_loop(self):
        while True:
            pack = self.udt_recv()

            # If it is an ACK
            if pack.type == 0:

                # Call rdt_rcv
                self.rdt_rcv(pack)

                # Log this ACK's seq_num
                self.ack_log.info('{}'.format(pack.seq_num))

            # It is a reply to EOT
            if pack.type == 2:

                # Break the loop
                break


    # Start the program
    def start(self):

        # Create a thread for sending packets
        t1 = threading.Thread(target=self.sending_thread)

        # Start the thread
        t1.start()

        # Wait for packets
        self.wait_loop()

        # Sockets can be closed now
        self.sock_recv.close()
        self.sock_send.close()

        # Thread join
        t1.join()

        return 0


if __name__ == '__main__':
    _, emu_addr, emu_port, ack_port, fn = sys.argv
    s = Sender(emu_addr, int(emu_port), int(ack_port), fn)
    ret = s.start()
    exit(ret)



        