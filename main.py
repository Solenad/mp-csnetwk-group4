# main.py
from network.socket_manager import start_listening
from network.message_sender import send_ack
from network.broadcast import my_info, send_immediate_discovery
from ui.cli import start_cli
from network.peer_registry import add_peer
import threading
import socket
import config
from ui.utils import print_verbose, print_prompt
import time

PROFILE_RESEND_INTERVAL = 10


def handle_message(message: str, addr: tuple) -> None:
    try:
        # Parse message into key-value pairs
        content = {}
        for line in message.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                content[key.strip()] = value.strip()

        msg_type = content.get("TYPE")
        user_id = content.get("USER_ID") or content.get("FROM")

        if not user_id:
            if config.verbose_mode:
                print_verbose(f"[{time.time()}] Message without USER_ID ignored")
            return

        if user_id == my_info["user_id"]:
            if config.verbose_mode:
                print_verbose(f"[{time.time()}] Ignoring own message")
            return

        # Add/update peer information
        display_name = content.get("DISPLAY_NAME", user_id.split("@")[0])
        add_peer(
            user_id=user_id,
            ip=addr[0],
            port=content.get("PORT", addr[1]),
            display_name=display_name,
        )

        # Handle message types according to RFC
        if msg_type == "POST":
            if user_id in config.followed_users:
                if config.verbose_mode:
                    print_verbose(
                        f"\nTYPE: POST\n"
                        f"USER_ID: {user_id}\n"
                        f"CONTENT: {content.get('CONTENT', '')}\n"
                        f"TTL: {content.get('TTL', '')}\n"
                        f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                        f"TOKEN: {content.get('TOKEN', '')}\n"
                        f"TIMESTAMP: {content.get(
                            'TIMESTAMP', time.time())}\n\n"
                    )
                else:
                    print(f"\n{display_name}: {content.get('CONTENT', '')}\n")
                print_prompt()

        elif msg_type == "DM":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: DM\n"
                    f"FROM: {user_id}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"CONTENT: {content.get('CONTENT', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            else:
                print(
                    f"\n[DM from {display_name}]: {
                        content.get('CONTENT', '')}\n"
                )
            print_prompt()

            # Send ACK if needed
            if content.get("MESSAGE_ID"):
                send_ack(content["MESSAGE_ID"], user_id)

        elif msg_type == "PROFILE":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: PROFILE\n"
                    f"USER_ID: {user_id}\n"
                    f"DISPLAY_NAME: {display_name}\n"
                    f"STATUS: {content.get('STATUS', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n\n"
                )
            else:
                print(f"\n{display_name}: {content.get('STATUS', '')}\n")
            print_prompt()

        elif msg_type == "PING":
            if config.verbose_mode:
                print_verbose(f"\nTYPE: PING\n" f"USER_ID: {user_id}\n\n")

        elif msg_type == "FOLLOW":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: FOLLOW\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"FROM: {user_id}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            else:
                print(f"\nUser {display_name} has followed you\n")
            print_prompt()

        elif msg_type == "UNFOLLOW":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: UNFOLLOW\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"FROM: {user_id}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            else:
                print(f"\nUser {display_name} has unfollowed you\n")
            print_prompt()

        elif msg_type == "ACK":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: ACK\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"STATUS: {content.get('STATUS', '')}\n\n"
                    f"Field Descriptions:\n"
                    f"MESSAGE_ID: Identifier of original message.\n"
                    f"STATUS: e.g., RECEIVED.\n"
                )
            # Non-verbose: no output per RFC

        else:
            if config.verbose_mode:
                print_verbose(
                    f"[{time.time()}] Unknown message type: {
                        msg_type}\n{content}"
                )

    except Exception as e:
        if config.verbose_mode:
            print_verbose(f"[{time.time()}] Error processing message: {e}")


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
