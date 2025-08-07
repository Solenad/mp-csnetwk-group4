# socket_manager.py
import socket
import threading
import os

BUFFER_SIZE = 4096
BASE_PORT = 50999  # Default LSNP port
MAX_PORT_ATTEMPTS = 100  # How many ports to try before giving up


def start_listening(callback, preferred_port=50999):
    sock = None
    port = preferred_port

    while port < 65535:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("", port))
            print(f"Listening on UDP PORT: {port}")
            break
        except OSError:
            port += 1
    # Start listening in a thread
    def listen():
        while True:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                if data:
                    message = data.decode("utf-8").strip()
                    if message:
                        callback(message, addr)
            except Exception as e:
                print(f"[ERROR] Receiving data: {e}")
                break

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    return sock, port