import socket
import threading

UDP_PORT = 2425
BUFFER_SIZE = 4096


def start_listening(callback):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", UDP_PORT))
    print(f"Listening on UDP PORT: {UDP_PORT}")

    def listen():
        while True:
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                print(f"[Received] from {addr}")
                callback(data.decode(errors="replace"), addr)
            except Exception as error:
                print(f"[Error] Listening failed: {error}")
                break

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()
    return sock
