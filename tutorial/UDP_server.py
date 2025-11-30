import socket


SERVER = socket.gethostbyname(socket.gethostname())
PORT = 5050
HEADER = 64
FORMAT = 'utf-8'
ADDR  = (SERVER, PORT)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(ADDR)

while True:
    data, addr = s.recvfrom(HEADER)
    print(str(data))
    msg = ("Hello I am UDP Server. ").encode(FORMAT)
    s.sendto(msg, addr)