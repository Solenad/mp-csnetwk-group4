from network.socket_manager import start_listening
from network.broadcast import my_info
from ui.cli import start_cli, update_peer
import socket
import time


def handle_message(message, addr):
    print(f"[Received] {message} from {addr}")

    if message.startswith("LSNP|DISCOVER"):
        ip, port = addr
        response = f"LSNP|IAM|{my_info['username']}|{my_info['hostname']}"
        sock = socket.AF_INET
        dgram = socket.SOCK_DGRAM
        socket.socket(sock, dgram).sendto(response.encode(), addr)
        update_peer(addr, my_info["username"], my_info["hostname"])
    elif message.startswith("LSNP|IAM"):
        try:
            __, __, username, hostname = message.strip().split("|")
            update_peer(addr, username, hostname)
        except ValueError:
            print("[Error] Malformed IAM message")
    elif message.startswith("LSNP/1.0"):
        lines = message.split("\n")
        msg_type = None
        content = {}

        for line in lines:
            if line.startswith("TYPE:"):
                msg_type = line.split(":")[1].strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                content[key.strip()] = value.strip()

        if msg_type == "POST":
            print(
                f"\n[New Post] From {content['USER_ID']}: {content['CONTENT']}\n>> ",
                end="",
                flush=True,
            )
        elif msg_type == "DM":
            print(
                f"\n[New DM] From {content['FROM']}: {content['CONTENT']}\n>> ",
                end="",
                flush=True,
            )
        elif msg_type == "FOLLOW":
            print(
                f"\n[New Follower] {content['FROM']} followed you\n>> ",
                end="",
                flush=True,
            )
        elif msg_type == "PROFILE":
            pass


if __name__ == "__main__":
    start_listening(handle_message)
    time.sleep(0.2)

    start_cli(my_info)
