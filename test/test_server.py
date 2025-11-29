import socket
import threading


HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'

DISCONNECT_MSG = 'DISCONNECTED'

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)


def handle_msg(conn, ADDR):
    # conn.send(("Hello client ").encode(FORMAT))
    connect = True
    while connect:
        msg_lenght = conn.recv(HEADER).decode(FORMAT)
        if msg_lenght:
            msg_lenght = int(msg_lenght)
            msg = conn.recv(msg_lenght).decode(FORMAT)
            print(msg)
            if msg == DISCONNECT_MSG:
                connect = False
            
    conn.close()

def recv_msg():
    

def start():
    # conn, ADDR = socket.listen()
    server.listen()
    while True:
        conn, ADDR = server.accept()
        t = threading.Thread(target=handle_msg, args=(conn, ADDR))
        t.start()



start()