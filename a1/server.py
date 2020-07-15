import sys
from socket import *
from selectors import DefaultSelector, EVENT_READ
import pdb
from logger import get_logger
from collections import defaultdict

# used for handling concurrent TCP connections
selector = DefaultSelector()

messages = []

# send a message via UDP
def send_message(socket, cli_addr, message):
    socket.sendto(message, cli_addr)

# send the entries in the message list via UDP
def send_message_list(socket, cli_addr):
    for m in messages:
        socket.sendto(m.encode(), cli_addr)
    socket.sendto(b'NO MSG', cli_addr)

# return handler to the TCP request
def request(client_socket_n, addr, req_code, log):

    def handle_request(key, mask):
        data = client_socket_n.recv(1024)
        if not data:
            client_socket_n.close()
            selector.unregister(client_socket_n)
        else:
            # the req_code from client
            req_code_recv = data.decode()

            if (req_code == req_code_recv):

                # req_code matches, create a socket for receiving UDP
                server_socket_r = socket(AF_INET, SOCK_DGRAM)

                # bind to a port, this is done automatically
                server_socket_r.bind(('', 0))
                _, r_port = server_socket_r.getsockname()

                # send r_port
                send_data = '{}'.format(r_port)
                client_socket_n.send(send_data.encode())

                # receive message from client
                message, cli_addr = server_socket_r.recvfrom(1024)

                m = message.decode()

                # a 'TERMINATE' message was received
                if m == 'TERMINATE':
                    
                    # send the message list
                    send_message_list(server_socket_r, cli_addr)

                    # tell the client that it should wait for keyboard input
                    send_message(server_socket_r, cli_addr, b'BYE')

                    # shutdown the socket
                    server_socket_r.shutdown(SHUT_RDWR)

                    # close the socket
                    server_socket_r.close()

                    # exit the program
                    exit()
                
                # a 'GET' message was received
                elif m == 'GET':

                    # send the message list
                    send_message_list(server_socket_r, cli_addr)

                    # send an empty message indicating there is no more data
                    send_message(server_socket_r, cli_addr, b'')

                # otherwise, it is a message that should be stored
                else:

                    # send the message list
                    send_message_list(server_socket_r, cli_addr)

                    # send an empty message indicating there is no more data
                    send_message(server_socket_r, cli_addr, b'')

                    # log the message
                    store_msg = '[{}]: {}'.format(r_port, message.decode())
                    messages.append(store_msg)
                    log.info(store_msg)

                server_socket_r.shutdown(SHUT_RDWR)
                server_socket_r.close()
            else:

                # req_code does not match
                client_socket_n.send('0'.encode())
                client_socket_n.close()

    return handle_request

# start the server
def serve(req_code, log):

    def  recv_client(key, mask):
        server_socket_n = key.fileobj

        # accept the connection on the server socket
        client_socket_n, addr = server_socket_n.accept()

        # get the handler for the client socket
        # pass req_code and log to the handler
        handler = request(client_socket_n, addr, req_code, log)

        # register the socket and the handler to the selector
        selector.register(client_socket_n, EVENT_READ, handler)

    # create a socket on the server side
    server_socket_n = socket(AF_INET, SOCK_STREAM)
    server_socket_n.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    # a free port will be allocated
    server_socket_n.bind(('', 0))
    
    # listen
    server_socket_n.listen(1)

    # register the server socket and its handler
    selector.register(server_socket_n, EVENT_READ, recv_client)
    _, n_port = server_socket_n.getsockname()

    # print the n_port
    log.info('[SERVER_PORT]: {}'.format(n_port))

    try:
        while True:

            # select events
            events = selector.select()

            # for each event ready, callback
            for key, mask in events:
                callback = key.data
                callback(key, mask)

    except KeyboardInterrupt:
        server_socket_n.close()

if __name__ == '__main__':
    _, req_code = sys.argv
    log = get_logger('server')
    serve(req_code, log)
