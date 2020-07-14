
class packet:
    MAX_DATA_LENGTH = 500
    SEQ_NUM_MODULO = 32

    def __init__(self, type, seq_num, data):
        if len(data) > self.MAX_DATA_LENGTH:
            raise Exception("Data too large (max 500 char): ", len(data))

        self.type = type
        self.seq_num = seq_num % self.SEQ_NUM_MODULO
        self.data = data

    def get_udp_data(self):
        array = bytearray()
        array.extend(self.type.to_bytes(length=4, byteorder="big"))
        array.extend(self.seq_num.to_bytes(length=4, byteorder="big"))
        array.extend(len(self.data).to_bytes(length=4, byteorder="big"))
        array.extend(self.data.encode())
        return array

    @staticmethod
    def create_ack(seq_num):
        return packet(0, seq_num, "")

    @staticmethod
    def create_packet(seq_num, data):
        return packet(1, seq_num, data)

    @staticmethod
    def create_eot(seq_num):
        return packet(2, seq_num, "")

    @staticmethod
    def parse_udp_data(UDPdata):
        type = int.from_bytes(UDPdata[0:4], byteorder="big")
        seq_num = int.from_bytes(UDPdata[4:8], byteorder="big")
        length = int.from_bytes(UDPdata[8:12], byteorder="big")
        if type == 0:
            return packet.create_ack(seq_num)
        elif type == 2:
            return packet.create_eot(seq_num)
        else:
            UDPdata = UDPdata[12:12 + length].decode()
            return packet(type, seq_num, UDPdata)