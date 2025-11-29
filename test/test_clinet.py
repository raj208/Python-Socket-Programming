import threading
import socket

HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
DISCONNECT_MSG = 'DISCONNECT'


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)

def send_msg():
    while True:
        msg = input("Enter your msg: ")
        msg = msg.encode(FORMAT)
        msg_len = len(msg)
        msg_len = str(msg_len).encode(FORMAT)
        msg_len +=b' '*(HEADER-len(msg_len))
        client.send(msg_len)
        client.send(msg)
        # server_msg = client.recv(2048).decode(FORMAT)
        # if server_msg:
        #     print(server_msg)
    
def recv_msg():
    while True:
        try:
            server_msg = client.recv(2048).decode(FORMAT)
            if server_msg:
                print(server_msg)
        except:
            break

t2 = threading.Thread(target=recv_msg)
t1 = threading.Thread(target=send_msg)


t2.start()

t1.start()
