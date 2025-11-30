import socket
import threading
import time


class KeyValueStore:
    """
    Thread-safe in-memory key-value store with optional TTL per key.
    Internally stores: key -> (value, expiry_timestamp or None)
    """
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def _get_unlocked(self, key: str):
        """
        Internal: assumes lock is held.
        Returns value if present and not expired, else None.
        """
        record = self._store.get(key)
        if record is None:
            return None

        value, expiry = record
        if expiry is not None and expiry <= time.time():
            # Expired – delete and treat as missing
            del self._store[key]
            return None
        return value

    def get(self, key: str):
        with self._lock:
            return self._get_unlocked(key)

    def put(self, key: str, value: str, ttl: float | None = None):
        """
        Store a key with optional TTL (in seconds).
        If ttl is None, key does not expire.
        """
        expiry = None
        if ttl is not None:
            expiry = time.time() + ttl
        with self._lock:
            self._store[key] = (value, expiry)

    def delete(self, key: str) -> bool:
        """
        Delete a key if it exists and is not expired.
        Returns True if a key was deleted, False otherwise.
        """
        with self._lock:
            record = self._store.get(key)
            if record is None:
                return False

            value, expiry = record
            if expiry is not None and expiry <= time.time():
                # Already expired – clean up and treat as not found
                del self._store[key]
                return False

            del self._store[key]
            return True

    def cleanup_expired(self):
        """
        Remove all expired keys in one sweep.
        Called periodically by server background thread.
        """
        now = time.time()
        with self._lock:
            to_delete = [
                k for k, (v, expiry) in self._store.items()
                if expiry is not None and expiry <= now
            ]
            for k in to_delete:
                del self._store[k]


class KeyValueServer:
    """
    Simple TCP key-value server that accepts GET, PUT, PUTEX, DELETE commands.

    Protocol (one request per line):
      - PUT <key> <value...>
      - PUTEX <key> <ttl_seconds> <value...>
      - GET <key>
      - DELETE <key>
      - QUIT

    Responses:
      - PUT / PUTEX success: "OK"
      - GET (exists): "VALUE <value>"
      - GET (missing/expired): "NOT_FOUND"
      - DELETE (success): "DELETED"
      - DELETE (missing/expired): "NOT_FOUND"
      - QUIT: "BYE"
      - invalid: "ERROR <message>"
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.store = KeyValueStore()
        self._shutdown_event = threading.Event()

        # Start background cleaner thread for expired keys
        self._cleaner_thread = threading.Thread(
            target=self._cleanup_loop,
            args=(1.0,),  # interval in seconds
            daemon=True,
        )
        self._cleaner_thread.start()

    def _cleanup_loop(self, interval: float):
        """
        Periodically clean up expired keys until shutdown.
        """
        while not self._shutdown_event.is_set():
            time.sleep(interval)
            self.store.cleanup_expired()

    def start(self):
        """
        Start the server and begin accepting connections.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv_sock:
            srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv_sock.bind((self.host, self.port))
            srv_sock.listen()
            print(f"[SERVER] Listening on {self.host}:{self.port}")

            try:
                while not self._shutdown_event.is_set():
                    try:
                        conn, addr = srv_sock.accept()
                    except OSError:
                        break  # socket closed
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
            self.store.put(key, value)  # no TTL
            return "OK"

        elif cmd == "PUTEX":
            # PUTEX <key> <ttl_seconds> <value...>
            if len(parts) < 4:
                return "ERROR Usage: PUTEX <key> <ttl_seconds> <value>"
            key = parts[1]
            ttl_str = parts[2]
            try:
                ttl = float(ttl_str)
            except ValueError:
                return "ERROR ttl_seconds must be a number"

            if ttl <= 0:
                return "ERROR ttl_seconds must be > 0"

            value = " ".join(parts[3:])
            self.store.put(key, value, ttl=ttl)
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
            return "BYE"

        else:
            return f"ERROR Unknown command: {cmd}"


if __name__ == "__main__":
    server = KeyValueServer(host="127.0.0.1", port=5000)
    server.start()
