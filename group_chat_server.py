#!/usr/bin/env python3
import socket
import threading

HOST = "0.0.0.0"
PORT = 5001  # change if needed

# group_id -> list of (conn, user_id)
groups = {}
groups_lock = threading.Lock()


def broadcast(group_id, message, sender_conn=None):
    """
    Send 'message' to all clients in the given group_id,
    except optionally the sender_conn.
    """
    with groups_lock:
        clients = list(groups.get(group_id, []))  # snapshot

    for conn, _uid in clients:
        if conn is sender_conn:
            continue
        try:
            conn.sendall(message.encode())
        except OSError:
            # Broken pipe / disconnected client; cleanup happens elsewhere
            pass


def handle_client(conn, addr):
    print(f"[+] New connection from {addr}")

    try:
        conn.sendall(b"Welcome to the Group Chat Server!\r\n")
        conn.sendall(b"Enter your user id: ")
        user_id = conn.recv(1024).decode(errors="ignore").strip()
        if not user_id:
            conn.close()
            return

        conn.sendall(b"Enter group id to join (e.g., group1): ")
        group_id = conn.recv(1024).decode(errors="ignore").strip()
        if not group_id:
            conn.close()
            return

        # Add client to the chosen group (create if it doesn't exist)
        with groups_lock:
            groups.setdefault(group_id, [])
            groups[group_id].append((conn, user_id))
        print(f"[+] User '{user_id}' joined group '{group_id}' from {addr}")

        welcome = (
            f"\r\nYou joined group '{group_id}' as '{user_id}'.\r\n"
            "Type messages and press Enter to chat.\r\n"
            "Type '/quit' to leave.\r\n\r\n"
        )
        conn.sendall(welcome.encode())

        # Notify others in the group
        broadcast(group_id,
                  f"[Server] {user_id} has joined the group.\r\n",
                  sender_conn=conn)

        while True:
            data = conn.recv(1024)
            if not data:
                break  # client disconnected

            msg = data.decode(errors="ignore").strip()
            if not msg:
                continue

            if msg.lower() == "/quit":
                conn.sendall(b"Goodbye!\r\n")
                break

            # Relay message to other clients in the same group
            formatted = f"[{group_id}] {user_id}: {msg}\r\n"
            print(formatted.strip())
            broadcast(group_id, formatted, sender_conn=conn)

    except ConnectionResetError:
        # Client closed the connection abruptly
        pass
    finally:
        # Remove from groups
        removed_from = None
        with groups_lock:
            for gid, clients in list(groups.items()):
                new_list = [(c, uid) for (c, uid) in clients if c is not conn]
                if len(new_list) != len(clients):
                    groups[gid] = new_list
                    removed_from = gid
                    if not new_list:
                        del groups[gid]  # delete empty group
                    break

        if removed_from:
            print(f"[-] Connection from {addr} ({removed_from}) closed.")
            try:
                user = user_id if 'user_id' in locals() else str(addr)
                broadcast(removed_from,
                          f"[Server] {user} has left the group.\r\n",
                          sender_conn=None)
            except Exception:
                pass

        conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen()
        print(f"[*] Group chat server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client,
                                 args=(conn, addr),
                                 daemon=True)
            t.start()


if __name__ == "__main__":
    main()
