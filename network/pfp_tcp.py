# network/pfp_tcp.py
import socket
import threading
from network.peer_registry import get_peer

TCP_BUFFER_SIZE = 4096

def serve_profile_b64_and_get_port(username):
    """Start TCP server to send this user's PFP Base64."""
    peer = get_peer(username)
    pfp_b64 = peer.get("avatar_b64") or peer.get("pfp", "") or ""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("", 0))  # pick free port
    server.listen(1)
    port = server.getsockname()[1]

    def handler():
        try:
            conn, _ = server.accept()
            conn.sendall(pfp_b64.encode())
            conn.close()
        finally:
            server.close()

    threading.Thread(target=handler, daemon=True).start()
    return port

def receive_profile_b64_from(ip, port):
    """Fetch Base64 PFP from peer over TCP."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        chunks = []
        while True:
            data = sock.recv(TCP_BUFFER_SIZE)
            if not data:
                break
            chunks.append(data)
        sock.close()
        return b"".join(chunks).decode()
    except Exception as e:
        print(f"[PFP TCP] Receive error: {e}")
        return None