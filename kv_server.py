import socket
import threading


class KeyValueStore:
    """
    Thread-safe in-memory key-value store.
    """
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            return self._store.get(key)

    def put(self, key: str, value: str):
        with self._lock:
            self._store[key] = value

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False


class KeyValueServer:
    """
    Simple TCP key-value server that accepts GET, PUT, DELETE commands.

    Protocol (one request per line):
      - PUT <key> <value...>
      - GET <key>
      - DELETE <key>
      - QUIT   (close current client connection)

    Responses:
      - For successful PUT: "OK\n"
      - For GET when key exists: "VALUE <value>\n"
      - For GET when key missing: "NOT_FOUND\n"
      - For successful DELETE: "DELETED\n"
      - For DELETE when key missing: "NOT_FOUND\n"
      - For invalid commands: "ERROR <message>\n"
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.store = KeyValueStore()
        self._shutdown_event = threading.Event()

    def start(self):
        """
        Start the server and begin accepting connections.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv_sock:
            # Allow quick restart on the same port
            srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv_sock.bind((self.host, self.port))
            srv_sock.listen()
            print(f"[SERVER] Listening on {self.host}:{self.port}")

            try:
                while not self._shutdown_event.is_set():
                    try:
                        conn, addr = srv_sock.accept()
                    except OSError:
                        # Socket closed during shutdown
                        break
                    print(f"[SERVER] New connection from {addr}")
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr),
                        daemon=True,
                    )
                    client_thread.start()
            except KeyboardInterrupt:
                print("\n[SERVER] Shutting down (KeyboardInterrupt)...")
            finally:
                self._shutdown_event.set()
                print("[SERVER] Server stopped.")

    def handle_client(self, conn: socket.socket, addr):
        """
        Handle a single client connection.
        """
        with conn:
            file = conn.makefile("r")
            while True:
                line = file.readline()
                if not line:
                    print(f"[SERVER] Connection closed by {addr}")
                    break

                line = line.strip()
                if not line:
                    continue

                response = self.process_command(line)
                try:
                    conn.sendall((response + "\n").encode("utf-8"))
                except (BrokenPipeError, ConnectionResetError):
                    print(f"[SERVER] Connection lost with {addr}")
                    break

    def process_command(self, line: str) -> str:
        """
        Parse and execute a command string, return a response string.
        """
        parts = line.split()
        if not parts:
            return "ERROR Empty command"

        cmd = parts[0].upper()

        if cmd == "PUT":
            if len(parts) < 3:
                return "ERROR Usage: PUT <key> <value>"
            key = parts[1]
            value = " ".join(parts[2:])
            self.store.put(key, value)
            return "OK"

        elif cmd == "GET":
            if len(parts) != 2:
                return "ERROR Usage: GET <key>"
            key = parts[1]
            value = self.store.get(key)
            if value is None:
                return "NOT_FOUND"
            return f"VALUE {value}"

        elif cmd == "DELETE":
            if len(parts) != 2:
                return "ERROR Usage: DELETE <key>"
            key = parts[1]
            deleted = self.store.delete(key)
            return "DELETED" if deleted else "NOT_FOUND"

        elif cmd == "QUIT":
            # The client should close the connection after receiving this,
            # but we still send a confirmation.
            return "BYE"

        else:
            return f"ERROR Unknown command: {cmd}"


if __name__ == "__main__":
    # You can change host/port here if needed
    server = KeyValueServer(host="127.0.0.1", port=5000)
    server.start()
