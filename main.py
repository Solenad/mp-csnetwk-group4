from network.socket_manager import start_listening
from network.broadcast import send_profile, my_info
from ui.cli import start_cli
import socket
import threading
import time


def handle_message(message, addr):
    try:
        # Parse message into key-value pairs
        msg_dict = {}
        for line in message.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                msg_dict[key.strip()] = value.strip()

        msg_type = msg_dict.get("TYPE")
        if not msg_type:
            return

        if msg_type == "PROFILE":
            print(
                f"\n[New Profile] {msg_dict.get('DISPLAY_NAME')} ({
                    msg_dict.get('USER_ID')}): {msg_dict.get('STATUS')}"
            )
        elif msg_type == "POST":
            print(
                f"\n[New Post] {msg_dict.get('USER_ID')}: {
                    msg_dict.get('CONTENT')}"
            )
        elif msg_type == "DM":
            if msg_dict.get("FROM") and msg_dict.get("CONTENT"):
                print(f"\n[DM from {msg_dict['FROM']}]: {msg_dict['CONTENT']}")
        elif msg_type == "FOLLOW":
            print(f"\n{msg_dict.get('FROM')} followed you!")
        elif msg_type == "PING":
            pass  # Silent handling of PINGs

    except Exception as e:
        print(f"Error processing message: {e}")


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

    def periodic_broadcast():
        while True:
            send_profile(my_info)  # Pass the actual port
            time.sleep(300)

    broadcast_thread = threading.Thread(target=periodic_broadcast, daemon=True)
    broadcast_thread.start()

    start_cli(my_info)
