from network.socket_manager import start_listening
from network.broadcast import send_profile, my_info
from ui.cli import start_cli
from network.peer_registry import add_peer, update_last_seen
import threading
import time
from config import verbose_mode  # Import verbose_mode from config


def handle_message(message: str, addr: tuple) -> None:
    try:
        lines = [line.strip() for line in message.split("\n") if line.strip()]
        # This is your message dictionary (renamed from msg_dict for clarity)
        content = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                content[key.strip()] = value.strip()

        msg_type = content.get("TYPE")
        if not msg_type:
            return

        user_id = content.get("USER_ID")
        if not user_id:
            return

        # Update peer information
        if msg_type == "PROFILE":
            add_peer(
                user_id=user_id,
                ip=addr[0],
                port=int(content.get("PORT", 50999)),
                display_name=content.get("DISPLAY_NAME"),
            )
        else:
            update_last_seen(user_id)

        # Handle message types using 'content' instead of 'msg_dict'
        if msg_type == "POST":
            print(
                f"\n[New Post] {content.get('USER_ID')}: {
                    content.get('CONTENT')}"
            )
        elif msg_type == "DM":
            if content.get("FROM") and content.get("CONTENT"):
                print(f"\n[DM from {content['FROM']}]: {content['CONTENT']}")
        elif msg_type == "FOLLOW":
            print(f"\n{content.get('FROM')} followed you!")
        elif msg_type == "PING":
            pass  # Silent handling of PINGs

    except Exception as e:
        if verbose_mode:
            print(f"[VERBOSE] Error processing message: {e}")


def periodic_broadcast():
    """Send periodic broadcasts for peer discovery"""
    while True:
        send_profile(my_info)
        time.sleep(300)  # Every 5 minutes


if __name__ == "__main__":
    sock, port = start_listening(handle_message)
    if not sock:
        exit(1)

    my_info["port"] = port  # Store the actual port being used

    broadcast_thread = threading.Thread(target=periodic_broadcast, daemon=True)
    broadcast_thread.start()

    start_cli(my_info)
