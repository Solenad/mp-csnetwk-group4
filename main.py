# main.py
from network.socket_manager import start_listening
from network.broadcast import send_profile, my_info, send_immediate_discovery
from ui.cli import start_cli
from network.peer_registry import add_peer
import threading
import socket
from config import verbose_mode


def handle_message(message: str, addr: tuple) -> None:
    try:
        lines = [line.strip() for line in message.split("\n") if line.strip()]
        content = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                content[key.strip()] = value.strip()

        msg_type = content.get("TYPE")
        user_id = content.get("USER_ID") or content.get("FROM")

        if msg_type != "PROFILE":
            print(f"\n[DEBUG] Type is: {msg_type}\n")

        if user_id == my_info["user_id"]:
            return

        # Always update peer info
        add_peer(
            user_id=user_id,
            ip=addr[0],
            port=addr[1],
            display_name=content.get("DISPLAY_NAME", user_id.split("@")[0]),
        )

        if msg_type == "POST":
            print(
                f"\n[New Post] {content.get('DISPLAY_NAME', user_id)}: {
                    content.get('CONTENT', '')}\n>> ",
                end="",
                flush=True,
            )
        elif msg_type == "DM":
            token = content.get("TOKEN", "").split("|")
            if len(token) != 3 or token[2] != "chat":
                if verbose_mode:
                    print(
                        f"\n[WARNING] Invalid DM token from {
                            user_id}\n>> ",
                        end="",
                        flush=True,
                    )
                return
            print(
                f"\n[DM from {content['FROM']}]: {
                    content.get('CONTENT', '')}\n>> ",
                end="",
                flush=True,
            )

        elif msg_type in ["PING", "PROFILE"]:
            send_profile(my_info)

        elif msg_type == "FOLLOW":
            sender = content.get("FROM", user_id)
            print(f"\nUser {sender} has followed you\n>> ", end="", flush=True)

        elif msg_type == "UNFOLLOW":
            sender = content.get("FROM", user_id)
            print(f"\nUser {sender} has unfollowed you\n>> ", end="", flush=True)

    except Exception as e:
        if verbose_mode:
            print(f"[VERBOSE] Error processing message: {e}")


if __name__ == "__main__":
    sock, port = start_listening(handle_message)
    if not sock:
        exit(1)

    my_info.update(
        {
            "port": port,
            "user_id": f"{my_info['username']}@{socket.gethostbyname(socket.gethostname())}:{port}",
        }
    )

    # Send immediate discovery bursts
    threading.Thread(
        target=send_immediate_discovery, args=(my_info,), daemon=True
    ).start()
    start_cli(my_info)
