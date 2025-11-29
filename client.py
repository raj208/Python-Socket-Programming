import socket
# import threading


HEADER = 64
PORT = 5050
# SERVER = ""
SERVER = socket.gethostbyname(socket.gethostname())
# print(SERVER)
# ADDR = (SERVER, PORT)
FORMAT =  'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECTED"
ADDR = (SERVER, PORT)

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #famil, type(TCP)
# server.bind(ADDR)
client.connect(ADDR)


def send_msg(msg):
    message = msg.encode(FORMAT)  #msg to byte
    msg_lenght= len(message)   #msg_byte_lenght
    send_lenght = str(msg_lenght).encode(FORMAT)  #msg_byte_lenght to byte
    send_lenght+= b' '*(HEADER-len(send_lenght))  #PADDING
    client.send(send_lenght)
    client.send(message)
    print(client.recv(2048).decode(FORMAT))  #receiving server reply

send_msg("Hello World")


# send_msg(DISCONNECT_MESSAGE)

