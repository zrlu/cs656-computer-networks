import dpkt
import socket
import sys

HANDSHAKE_TYPES = {
    'HelloRequest': 0,
    'ClientHello': 1,
    'ServerHello': 2,
    'NewSessionTicket': 4,
    'Certificate': 11,
    'ServerKeyExchange': 12,
    'CertificateRequest': 13,
    'ServerHelloDone': 14,
    'CertificateVerify': 15,
    'ClientKeyExchange': 16,
    'Finished': 20
}

RECORD_TYPES = {
    'TLSChangeCipherSpec' : 20,
    'TLSAlert' : 21,
    'TLSHandshake' : 22,
    'TLSAppData' : 23
}


def inv_key(key):
     src_ip, dst_ip, src_port, dst_port = key
     return (dst_ip, src_ip, dst_port, src_port)


class Flow:

    def __init__(self, ts_start, key):
        self.ts_start = ts_start
        self.ts_end = -1
        self.application_layer_protocol = None
        self.key = key
        src_ip, dst_ip, src_port, dst_port = key
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.src_port = src_port
        self.dst_port = dst_port
        self.client_pck_count = 0
        self.server_pck_count = 0
        self.client_bytes = 0
        self.server_bytes = 0

    def add_packet(self, ts, tcp_size, key):
        if key == self.key:
            self.client_pck_count += 1
            self.client_bytes += tcp_size
        elif key == inv_key(self.key):
            self.server_pck_count += 1
            self.server_bytes += tcp_size
        
        self.ts_end = max(self.ts_end, ts)

    def set_application_layer_protocol(self, protocol):
        self.application_layer_protocol = protocol
    
    def to_row(self):
        return ','.join(str(val) for val in [
            self.src_ip,
            self.dst_ip,
            self.src_port,
            self.dst_port,
            self.client_pck_count,
            self.client_bytes,
            self.client_bytes / self.client_pck_count,
            self.server_pck_count,
            self.server_bytes,
            self.server_bytes / self.server_pck_count,
            self.ts_end - self.ts_start,
            self.application_layer_protocol
        ])


if __name__ == '__main__':

    _, pcapng = sys.argv

    flows = []
    flows_temp = {}

    for ts, pkt in dpkt.pcapng.Reader(open(pcapng,'rb')):
        eth = dpkt.ethernet.Ethernet(pkt)
        if eth.type == dpkt.ethernet.ETH_TYPE_IP:
            ip = eth.data
            src_ip = socket.inet_ntoa(ip.src)
            dst_ip = socket.inet_ntoa(ip.dst)
            if ip.p == dpkt.ip.IP_PROTO_TCP:
                tcp = ip.data
                src_port = tcp.sport
                dst_port = tcp.dport
                
                # 4 tuple because we know it is TCP
                key = (src_ip, dst_ip, src_port, dst_port) 
                stream = tcp.data
                try:
                    tls = dpkt.ssl.TLS(stream)
                    for record in tls.records:
                        if record.type == RECORD_TYPES['TLSHandshake']:
                            handshake = dpkt.ssl.TLSHandshake(record.data)
                            if handshake.type == HANDSHAKE_TYPES['ClientHello']:

                                if key in flows_temp:
                                    flows.append(flows_temp[key])
                                flows_temp[key] = Flow(ts, key)

                            elif handshake.type == HANDSHAKE_TYPES['ServerHello']:
                                server_hello = handshake.data

                                if hasattr(server_hello, 'extensions'):
                                    for ext_name, ext_value in server_hello.extensions:
                                        if ext_name == 16:
                                            alpn = ext_value[3:]
                                            if inv_key(key) in flows_temp:
                                                flows_temp[inv_key(key)].set_application_layer_protocol(alpn.decode())
                                                break

                    if key in flows_temp:
                        flows_temp[key].add_packet(ts, len(ip.data), key)
                    elif inv_key(key) in flows_temp:
                        flows_temp[inv_key(key)].add_packet(ts, len(ip.data), key)

                except dpkt.NeedData:
                    pass
                except dpkt.ssl.SSL3Exception:
                    pass
                except Exception as e:
                    raise e


    for key, flow in flows_temp.items():
        flows.append(flow)

    for flow in flows:
        if flow.application_layer_protocol is not None:
            print(flow.to_row())