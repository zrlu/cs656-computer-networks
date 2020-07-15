import sys
from socket import *
from logger import get_logger

# negotiation phase, returns r_port
def tcp(server_address, n_port, req_code, log):
    client_socket = socket(AF_INET, SOCK_STREAM)
    client_socket.connect((server_address, n_port))
    client_socket.send('{}'.format(req_code).encode())

    # no longer needed to write
    client_socket.shutdown(SHUT_WR)

    # read the port number given by the server
    recv_data = client_socket.recv(1024)

    # no longer needed to read
    client_socket.shutdown(SHUT_RD)

    # parse the port number into int
    r_port = int(recv_data.decode())

    # close the socket
    client_socket.close()

    return r_port

# transaction phase
def udp(server_address, r_port, message, log):
    client_socket = socket(AF_INET, SOCK_DGRAM)
    client_socket.sendto(message.encode(), (server_address, r_port))

    while 1:
        response, _ = client_socket.recvfrom(1024)
        
        # if no response, break the loop
        if not response:
            break
        
        # the server has received the 'TERMINATE' command and respond
        # with a signal that the client should wait for keyboard input
        # before exiting
        elif response.decode() == 'BYE':
            input()
            break
        
        # otherwise, print every message sent by the server
        else:
            print(response.decode())
    
    # shutdown the socket
    client_socket.shutdown(SHUT_RDWR)

    # close the socket
    client_socket.close()
    
if __name__ == '__main__':
    _, server_address, n_port, req_code, message = sys.argv
    log = get_logger('client', stdout=False)

    r_port = tcp(server_address, int(n_port), int(req_code), log)
    log.info('{}'.format(r_port))

    # the server sent port number 0
    if r_port == 0:
        print('Invalid req_code.')
        exit()
    
    # the server sent a valid port number for transaction phase
    else:
        udp(server_address, r_port, message, log)
    
