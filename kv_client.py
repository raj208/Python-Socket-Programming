import socket
import sys


def main(host: str = "127.0.0.1", port: int = 5000):
    """
    Simple interactive client for the key-value server.

    Type commands like:
      PUT mykey some value
      GET mykey
      DELETE mykey
      QUIT

    Press Ctrl+C to exit.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            print(f"[CLIENT] Connected to {host}:{port}")
            print("Type commands (PUT/GET/DELETE/QUIT). Ctrl+C to exit.\n")

            while True:
                try:
                    cmd = input("> ")
                except EOFError:
                    print("\n[CLIENT] EOF - closing.")
                    break
                except KeyboardInterrupt:
                    print("\n[CLIENT] Keyboard interrupt - closing.")
                    break

                if not cmd.strip():
                    continue

                # Ensure newline-terminated command
                sock.sendall((cmd.strip() + "\n").encode("utf-8"))

                # Read server response (one line)
                data = b""
                while not data.endswith(b"\n"):
                    chunk = sock.recv(4096)
                    if not chunk:
                        print("[CLIENT] Server closed the connection.")
                        return
                    data += chunk
                response = data.decode("utf-8").rstrip("\n")
                print(response)

                if cmd.strip().upper() == "QUIT":
                    print("[CLIENT] Closing connection.")
                    break

    except ConnectionRefusedError:
        print(f"[CLIENT] Could not connect to {host}:{port} (is the server running?).")


if __name__ == "__main__":
    host = "127.0.0.1"
    port = 5000
    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])
    main(host, port)
