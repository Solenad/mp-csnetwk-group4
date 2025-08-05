import socket
import threading

BUFFER_SIZE = 4096


def start_listening(callback, preferred_port=2425):
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
            if sock:
                sock.close()

    if not sock:
        raise RuntimeError("Could not find available port")

    def listen():
        while True:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                if data:
                    callback(data.decode(errors="replace"), addr)
            except Exception as error:
                print(f"[Error] Listening failed: {error}")
                break

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    return sock, port
