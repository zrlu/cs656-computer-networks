import udp
from packet import packet
import time
from logger import get_logger


class Receiver:

    """
    A Receiver class for the GBN protocol
    """

    def __init__(self, emu_addr, emu_port, in_port, fn, seq_mod=packet.SEQ_NUM_MODULO):

        # IP address of the emulator
        self.emulator_addr = emu_addr

        # Port of the emulator (backward)
        self.emulator_port = emu_port

        # Port for accepting packets
        self.in_port = in_port

        # Sequence number modulo, default to packet.SEQ_NUM_MODULO (32)
        self.seq_modulo = seq_mod

        # State expectedseqnum
        self.expectedseqnum = 0

        # ACK to send (-1 if first arrived packet has seq_num != 0 )
        self.sndpkt = packet.create_ack(-1)

        # Socket for sending UDP packets
        self.sock_send = udp.sock_send()

        # Socket for receiving UDP packets
        self.sock_recv = udp.sock_recv(self.in_port)

        # Log file for arriving packets
        self.arrival_log = get_logger('arrival')

        # Filename for writing
        self.filename = fn

    
    # Increment expectedseqnum by one
    def incr_expectedseqnum(self):
        self.expectedseqnum = (self.expectedseqnum + 1) % self.seq_modulo


    # Unreliabily send a UDP packet
    def udt_send(self, pack):
        udp.send_packet(self.sock_send, self.emulator_addr, self.emulator_port, pack)
    

    # Unreliabily receive an UDP packet from the emulator
    def udt_recv(self):
        return udp.recv_packet(self.sock_recv)

    # Send an EOT
    def send_eot(self):
        self.sndpkt = packet.create_eot(self.expectedseqnum)
        self.udt_send(self.sndpkt)


    # Receive packets
    def loop(self):

        # Open a file to write
        with open(self.filename, 'w') as file:

            # Loop
            while True:
                
                pack = self.udt_recv()
                if pack:

                    # If it is a data packet
                    if pack.type == 1:
                        
                        # Log the seq_num
                        self.arrival_log.info('{}'.format(pack.seq_num))

                        # If this is expected
                        if pack.seq_num == self.expectedseqnum:

                            # Extract and write
                            file.write(data = pack.data)

                            # Create an ACK
                            self.sndpkt = packet.create_ack(self.expectedseqnum)

                            # Send ACK
                            self.udt_send(self.sndpkt)

                            # Increment
                            self.incr_expectedseqnum()

                        # Not expected
                        else:
                            
                            # Send the latest in-order packet
                            self.udt_send(self.sndpkt)

                    # If it is an EOT
                    elif pack.type == 2:

                        # Done
                        break

        # Send an EOT back
        self.send_eot()

        # Close the sockets
        self.sock_send.close()
        self.sock_recv.close()

        return 0


if __name__ == '__main__':
    # r = Receiver('127.0.0.1', 4000, 7654, 'tiny_copy.txt')
    r = Receiver('127.0.0.1', 4000, 7654, 'large_copy.txt')
    ret = r.loop()
    exit(ret)