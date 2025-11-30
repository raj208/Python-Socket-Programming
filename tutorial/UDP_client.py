import socket


SERVER = socket.gethostbyname(socket.gethostname())
PORT = 5050
HEADER = 64
FORMAT = 'utf-8'
ADDR  = (SERVER, PORT)

c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# c.bind(ADDR)

msg = "Hello UDP Server, I am UDP client...."
c.sendto(msg.encode(FORMAT), ADDR)
data, addr = c.recvfrom(HEADER)
print(str(data))
c.close()