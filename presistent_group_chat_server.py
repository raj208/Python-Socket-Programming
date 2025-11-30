#!/usr/bin/env python3
import socket
import threading
import time
import json
import os

HOST = "0.0.0.0"
PORT = 5003  # change if needed

HISTORY_TTL_SECONDS = 15 * 60          # 15 minutes
HISTORY_FILE = "chat_history.json"     # persistent storage file

# group_id -> list of (conn, user_id)
groups = {}

# group_id -> list of {"ts": <float>, "text": <str>}
group_history = {}

# One lock to protect both 'groups' and 'group_history' + file writes
data_lock = threading.Lock()


# ---------- Persistence helpers ----------

def load_history_from_disk():
    """Load chat history from JSON file into memory (only keep last 15 minutes)."""
    global group_history
    if not os.path.exists(HISTORY_FILE):
        group_history = {}
        return

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Corrupted file or other issue; start fresh
        group_history = {}
        return

    now = time.time()
    pruned = {}
    for gid, msgs in data.items():
        new_list = []
        for m in msgs:
            ts = m.get("ts", now)
            txt = m.get("text", "")
            if now - ts <= HISTORY_TTL_SECONDS and txt:
                new_list.append({"ts": ts, "text": txt})
        if new_list:
            pruned[gid] = new_list

    group_history = pruned


def prune_history_locked(now=None):
    """Remove messages older than TTL from in-memory history (requires data_lock)."""
    global group_history
    if now is None:
        now = time.time()

    new_history = {}
    for gid, msgs in group_history.items():
        recent = [m for m in msgs if now - m["ts"] <= HISTORY_TTL_SECONDS]
        if recent:
            new_history[gid] = recent
    group_history = new_history


def save_history_locked():
    """Write current in-memory history to disk (requires data_lock)."""
    tmp_file = HISTORY_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(group_history, f)
    os.replace(tmp_file, HISTORY_FILE)


# ---------- Chat helpers ----------

def broadcast(group_id, message, sender_conn=None, save_to_history=True):
    """
    Send 'message' to all clients in group 'group_id',
    except optionally 'sender_conn'.
    If save_to_history is True, store message with timestamp
    in persistent history (only last 15 minutes kept).
    """
    with data_lock:
        # Save to history if it's a normal chat message
        if save_to_history:
            now = time.time()
            history = group_history.setdefault(group_id, [])
            history.append({"ts": now, "text": message})

            # Prune and persist
            prune_history_locked(now)
            save_history_locked()

        # Snapshot of current clients in that group
        clients = list(groups.get(group_id, []))

    # Send to all clients except the sender (outside the lock)
    for conn, _uid in clients:
        if conn is sender_conn:
            continue
        try:
            conn.sendall(message.encode())
        except OSError:
            # Ignore broken pipe; cleanup in handler
            pass


def send_previous_messages(conn, group_id):
    """
    Send previous messages (last 15 minutes) in this group
    to the newly joined client.
    """
    with data_lock:
        now = time.time()
        msgs = group_history.get(group_id, [])
        recent_msgs = [m["text"] for m in msgs if now - m["ts"] <= HISTORY_TTL_SECONDS]

    if not recent_msgs:
        conn.sendall(b"(No messages in this group in the last 15 minutes.)\r\n\r\n")
        return

    header = f"--- Messages in group '{group_id}' from last 15 minutes ---\r\n"
    conn.sendall(header.encode())
    for txt in recent_msgs:
        conn.sendall(txt.encode())
    conn.sendall(b"--- End of recent messages ---\r\n\r\n")


def handle_client(conn, addr):
    print(f"[+] New connection from {addr}")
    user_id = None
    group_id = None

    try:
        conn.sendall(
            b"Welcome to the Persistent Group Chat Server!\r\n"
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

        # Add client to the chosen group (create group if it doesn't exist)
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

        # Send last-15-minutes history for this group
        send_previous_messages(conn, group_id)

        # Notify others (do NOT store this in history)
        broadcast(
            group_id,
            f"[Server] {user_id} has joined the group.\r\n",
            sender_conn=conn,
            save_to_history=False,
        )

        # Main loop
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

            # Normal chat message
            formatted = f"[{group_id}] {user_id}: {msg}\r\n"
            print(formatted.strip())

            # Store & broadcast
            broadcast(group_id, formatted, sender_conn=conn, save_to_history=True)

    except ConnectionResetError:
        # Client closed connection abruptly
        pass
    finally:
        # Remove client from any group it was in
        removed_from = None
        with data_lock:
            for gid, clients in list(groups.items()):
                new_list = [(c, uid) for (c, uid) in clients if c is not conn]
                if len(new_list) != len(clients):
                    groups[gid] = new_list
                    removed_from = gid
                    if not new_list:
                        del groups[gid]
                    break

        if removed_from and user_id:
            print(f"[-] Connection from {addr} ({removed_from}) closed.")
            try:
                # Notify others (no history)
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
    # Load persistent history before accepting any clients
    load_history_from_disk()
    print("[*] Loaded history from disk.")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen()
        print(f"[*] Persistent group chat server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    main()
