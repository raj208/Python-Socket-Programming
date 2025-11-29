import socket
import threading


HEADER = 64
PORT = 5050
# SERVER = ""
SERVER = socket.gethostbyname(socket.gethostname())
# print(SERVER)
ADDR = (SERVER, PORT)
FORMAT =  'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECTED"


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #famil(iv4), type(TCP)
server.bind(ADDR)

def handle_client(conn, addr):
    print(f"[NEW CONNECTIOIN] {addr} connected. ")
    connected = True
    while connected:
        msg_lenght = conn.recv(HEADER).decode(FORMAT)
        
        if msg_lenght:
            # print(f"Printing msg_lenght inside if condition  RAW {msg_lenght} type of {type(msg_lenght)}")
            msg_lenght = int(msg_lenght)
            # print(f"Printing msg_lenght inside if condition  INT {type(msg_lenght)}")
            msg = conn.recv(msg_lenght).decode(FORMAT)
            # print(f"Printing {msg}")
            if msg == DISCONNECT_MESSAGE:
                connected = False

            print(f"[{addr}] {msg}")
            conn.send("Msg received".encode(FORMAT))
    conn.close()



def start():
    server.listen()
    print(f"[LISTENING] server is listening on {SERVER}")
    while True:
        conn, addr = server.accept()  #conn-> socket for that client
        thread = threading.Thread(target=handle_client, args = (conn, addr))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() -1 }")



print("[STARTING] server is starting...")

try:
    start()
except KeyboardInterrupt:
    print("\n[SHUTTING DOWN] Server is closing...")
    server.close()
    print("[CLOSED] Server closed successfully.")