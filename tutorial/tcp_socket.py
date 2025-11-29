import socket
import sys

try: 
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
except socket.error as err:
    print("failde to create sockte")
    print(f"Reason {str(err)}")
    sys.exit()

print("Socket Created")
target_host = input("Enter the target host name: ")
target_port = input("Enter target port")

try:
    s.connect((target_host, int(target_port)))
    print(f"Socket Connected to {target_port} {target_host}")
    s.shutdown(2)
except socket.error as err:
    print(f"failed to connect to {target_host} and  port {target_port}")
    print(f"Reason {str(err)}")
    sys.exit()