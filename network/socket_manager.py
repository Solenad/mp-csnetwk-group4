import socket
import threading

BUFFER_SIZE = 4096
LSNP_PORT = 50999  # Standard port per RFC


def start_listening(callback):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        sock.bind(("", LSNP_PORT))
        print(f"Listening on UDP port {LSNP_PORT}")
    except OSError as e:
        print(f"Failed to bind to port {LSNP_PORT}: {e}")
        return None, None

    def listen():
        while True:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                if data:
                    message = data.decode("utf-8").strip()
                    if message:  # Only process non-empty messages
                        callback(message, addr)
            except Exception as e:
                print(f"Error receiving data: {e}")
                break

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    return sock, LSNP_PORT
