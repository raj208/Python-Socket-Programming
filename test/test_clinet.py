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

def send_msg(msg):
    msg = msg.encode(FORMAT)
    msg_len = len(msg)
    msg_len = str(msg_len).encode(FORMAT)
    msg_len +=b' '*(HEADER-len(msg_len))
    client.send(msg_len)
    client.send(msg)





send_msg("Hello World")
