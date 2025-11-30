#!/usr/bin/env python3
import socket
import threading

HOST = "0.0.0.0"   # Listen on all interfaces
PORT = 5000        # You can change this port if needed


def handle_client(conn, addr):
    """
    Handle a single client connection.
    Whatever the client sends, we send back (echo).
    """
    print(f"[+] New connection from {addr}")

    # Optional greeting message for telnet clients
    welcome_msg = (
        "Welcome to the Python Echo Server!\r\n"
        "Whatever you type will be echoed back.\r\n"
        "Type Ctrl+] then 'quit' in telnet to disconnect.\r\n\r\n"
    )
    try:
        conn.sendall(welcome_msg.encode())

        while True:
            data = conn.recv(1024)
            if not data:
                # Client closed connection
                break

            # Echo back the received data to the same client
            conn.sendall(data)

    except ConnectionResetError:
        # Client forcibly closed the connection
        pass
    finally:
        print(f"[-] Connection closed: {addr}")
        conn.close()


def main():
    # Create a TCP socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        # Allow quick reuse of the address after the program exits
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind and listen
        server_sock.bind((HOST, PORT))
        server_sock.listen()
        print(f"[*] Echo server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server_sock.accept()
            # Create a new thread so multiple clients can be served concurrently
            client_thread = threading.Thread(
                target=handle_client, args=(conn, addr), daemon=True
            )
            client_thread.start()


if __name__ == "__main__":
    main()
