# main.py
from network.socket_manager import start_listening
from network.broadcast import send_profile, my_info
from ui.cli import start_cli
from network.peer_registry import add_peer, update_last_seen
import threading
import socket
import time
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
        if not msg_type or not user_id:
            return

        # Skip our own messages
        if user_id == my_info["user_id"]:
            return

        # Add/update peer for any message type (RFC Section 6: User Discovery)
        add_peer(
            user_id=user_id,
            ip=addr[0],
            port=int(content.get("PORT", my_info.get("port", 50999))),
            display_name=content.get("DISPLAY_NAME", user_id.split("@")[0]),
        )
        update_last_seen(user_id)

        if msg_type == "POST":
            print(
                f"\n[New Post] {content.get('DISPLAY_NAME', user_id)}: {
                    content.get('CONTENT', '')}\n>> ",
                end="",
                flush=True,
            )
        elif msg_type == "DM" and content.get("FROM") and content.get("CONTENT"):
            print(f"\n[DM from {content['FROM']}]: {content['CONTENT']}")
        elif msg_type == "FOLLOW":
            print(f"\n{content.get('FROM')} followed you!")
        elif msg_type == "PING":
            # Send our profile in response to PING (RFC Section 6)
            send_profile(my_info)

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
            "user_id": f"{my_info['username']}@{socket.gethostbyname(socket.gethostname())}",
        }
    )

    threading.Thread(
        target=lambda: [send_profile(my_info), time.sleep(300)], daemon=True
    ).start()
    start_cli(my_info)
