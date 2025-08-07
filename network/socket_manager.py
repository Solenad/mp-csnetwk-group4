# socket_manager.py
import socket
import threading

BUFFER_SIZE = 4096
BASE_PORT = 50999  # Default LSNP port
MAX_PORT_ATTEMPTS = 100  # How many ports to try before giving up


def start_listening(callback):
    sock = None
    port = BASE_PORT

    for attempt in range(MAX_PORT_ATTEMPTS):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # Add this line to enable broadcast reception
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Bind to all interfaces explicitly
            sock.bind(("0.0.0.0", port))  # Changed from ('', port)
            print(f"Listening on UDP port {port}")
            break
        except OSError:
            port += 1
            if sock:
                sock.close()
            if attempt == MAX_PORT_ATTEMPTS - 1:
                print(
                    f"Error: Could not bind to port after {
                      MAX_PORT_ATTEMPTS} attempts"
                )
                return None, None

    def listen():
        while True:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                if data:
                    message = data.decode("utf-8").strip()
                    if message:
                        callback(message, addr)
            except Exception as e:
                print(f"Error receiving data: {e}")
                break

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    return sock, port  # Return the actual port being used
