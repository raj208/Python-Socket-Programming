#!/usr/bin/env python3
import socket
import threading

HOST = "0.0.0.0"
PORT = 5002  # choose any free port

# group_id -> list of (conn, user_id)
groups = {}

# group_id -> list of previous chat messages (strings with \r\n)
group_history = {}

# One lock to protect both structures
data_lock = threading.Lock()


def broadcast(group_id, message, sender_conn=None, save_to_history=True):
    """
    Send 'message' to all clients in the given group_id,
    except optionally the sender_conn.
    Optionally store the message in the group's history.
    """
    with data_lock:
        # Save in history if required
        if save_to_history:
            history = group_history.setdefault(group_id, [])
            history.append(message)
            # Optional: limit history length
            # if len(history) > 200:
            #     history.pop(0)

        # Take a snapshot of current clients in that group
        clients = list(groups.get(group_id, []))

    # Send to all clients except the sender
    for conn, _uid in clients:
        if conn is sender_conn:
            continue
        try:
            conn.sendall(message.encode())
        except OSError:
            # If sending fails, ignore; cleanup happens in handler
            pass


def send_previous_messages(conn, group_id):
    """
    When a client joins a group, send all previous messages in that group
    (chat history) to this client.
    """
    with data_lock:
        history = list(group_history.get(group_id, []))

    if not history:
        conn.sendall(b"(No previous messages in this group yet.)\r\n\r\n")
        return

    header = f"--- Previous messages in group '{group_id}' ---\r\n"
    conn.sendall(header.encode())
    for msg in history:
        # each msg already has \r\n at the end
        conn.sendall(msg.encode())
    conn.sendall(b"--- End of previous messages ---\r\n\r\n")


def handle_client(conn, addr):
    print(f"[+] New connection from {addr}")

    try:
        conn.sendall(
            b"Welcome to the Group Chat Server with History!\r\n"
            b"Enter your user id: "
        )
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
        with data_lock:
            groups.setdefault(group_id, [])
            groups[group_id].append((conn, user_id))
            # Ensure group_history entry exists too
            group_history.setdefault(group_id, [])

        print(f"[+] User '{user_id}' joined group '{group_id}' from {addr}")

        conn.sendall(
            f"\r\nYou joined group '{group_id}' as '{user_id}'.\r\n"
            "Type messages and press Enter to chat.\r\n"
            "Type '/quit' to leave.\r\n\r\n".encode()
        )

        # Send previous messages to this new client (Objective 3)
        send_previous_messages(conn, group_id)

        # Notify others in the group (do NOT store this in history)
        broadcast(
            group_id,
            f"[Server] {user_id} has joined the group.\r\n",
            sender_conn=conn,
            save_to_history=False,
        )

        # Main loop: receive messages from this client
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

            # User chat message: format and broadcast to others
            formatted = f"[{group_id}] {user_id}: {msg}\r\n"
            print(formatted.strip())
            # Store in history + send to other clients in the group
            broadcast(group_id, formatted, sender_conn=conn, save_to_history=True)

    except ConnectionResetError:
        # Client closed connection abruptly
        pass
    finally:
        # Remove from groups
        with data_lock:
            for gid, clients in groups.items():
                new_list = [(c, uid) for (c, uid) in clients if c is not conn]
                if len(new_list) != len(clients):
                    groups[gid] = new_list
                    removed_from = gid
                    break
            else:
                removed_from = None

        if removed_from:
            print(f"[-] Connection from {addr} ({removed_from}) closed.")
            try:
                # Notify others (do NOT store this in history)
                broadcast(
                    removed_from,
                    f"[Server] {user_id} has left the group.\r\n",
                    sender_conn=None,
                    save_to_history=False,
                )
            except Exception:
                pass

        conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen()
        print(f"[*] Group chat server with history listening on {HOST}:{PORT}")

        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    main()
