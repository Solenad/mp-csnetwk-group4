from network.socket_manager import start_listening
from ui.cli import start_cli, update_peer
import socket

my_info = {"username": "Admin", "hostname": socket.gethostname()}


def handle_message(message, addr):
    print(f"[Received] {message} from {addr}")

    if message.startswith("LSNP|DISCOVER"):
        ip, port = addr
        response = f"LSNP|IAM|{my_info['username']}|{my_info['hostname']}"
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(response.encode(), addr)
        update_peer(addr, my_info["username"], my_info["hostname"])
    elif message.startswith("LSNP|IAM"):
        try:
            __, __, username, hostname = message.strip().split("|")
            update_peer(addr, username, hostname)
        except ValueError:
            print("[Error] Malformed IAM message")


if __name__ == "__main__":
    start_listening(my_info)
    start_cli(my_info)
