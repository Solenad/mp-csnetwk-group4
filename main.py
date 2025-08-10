# main.py
import network
from network.socket_manager import start_listening
from network.message_sender import send_ack
from network.broadcast import send_profile, my_info, send_immediate_discovery
from ui.cli import start_cli
from network.peer_registry import add_peer
import threading
import socket
from config import verbose_mode
from ui.utils import print_prompt
import network.pfp_tcp 

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

        # if msg_type != "PROFILE":
        #     print(f"[DEBUG] msg_type = {msg_type}")

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
                f"\n[POST] {content.get('DISPLAY_NAME', user_id)}: {content.get('CONTENT', '')}\n",
                end="",
                flush=True,
            )
            print_prompt()
        elif msg_type == "DM":
            token = content.get("TOKEN", "").split("|")
            if len(token) != 3 or token[2] != "chat":
                if verbose_mode:
                    print(
                        f"\n[WARNING] Invalid DM token from {user_id}\n>> ",
                        end="",
                        flush=True,
                    )
                return

            display_name = content.get("FROM", user_id).split("@")[0]
            print(
                f"\n[DM from {display_name}]: {content.get('CONTENT', '')}\n",
                end="",
                flush=True,
            )
            print_prompt()

            # Send ACK
            message_id = content.get("MESSAGE_ID")
            sender_id = content.get("FROM")
            if message_id and sender_id:
                send_ack(message_id, sender_id)

        elif msg_type == "PFP_REQUEST":
            # Someone wants our profile picture
            from network.pfp_tcp import serve_profile_b64_and_get_port
            from network.message_sender import send_udp_message  # small helper to send UDP text

            my_b64 = my_info.get("avatar_b64") or my_info.get("pfp", "") or ""
            if not my_b64:
                if verbose_mode:
                    print(f"[VERBOSE] No PFP to send to {user_id}")
            else:
                port = serve_profile_b64_and_get_port(my_info["username"])
                send_udp_message(addr[0], addr[1], f"TYPE:PFP_PORT\nPORT:{port}")

        elif msg_type == "PFP_PORT":
            # Connect via TCP and fetch the PFP Base64
            from network.pfp_tcp import receive_profile_b64_from
            try:
                tcp_port = int(content.get("PORT", "").strip())
                peer_ip = addr[0]
                b64 = receive_profile_b64_from(peer_ip, tcp_port)
                if b64:
                    update_peer_avatar(user_id, b64)
                    if verbose_mode:
                        print(f"[VERBOSE] Received PFP from {user_id} via TCP {tcp_port}")
                else:
                    if verbose_mode:
                        print(f"[VERBOSE] Failed to fetch PFP from {user_id} at {peer_ip}:{tcp_port}")
            except Exception as e:
                if verbose_mode:
                    print(f"[VERBOSE] Error processing PFP_PORT: {e}")
                        
        elif msg_type in ["PING", "PROFILE"]:
    # Store avatar if provided
            avatar_data = content.get("AVATAR_DATA")
            if avatar_data:
                from network.peer_registry import update_peer_avatar
                update_peer_avatar(user_id, avatar_data)

            send_profile(my_info)
        elif msg_type in ["PING", "PROFILE"]:
            send_profile(my_info)

        elif msg_type == "FOLLOW":
            sender = content.get("FROM", user_id)
            print(
                f"\n[FOLLOW] User {sender} has followed you\n",
                end="",
                flush=True,
            )
            print_prompt()

        elif msg_type == "UNFOLLOW":
            sender = content.get("FROM", user_id)
            print(
                f"\n[UNFOLLOW] User {sender} has unfollowed you\n",
                end="",
                flush=True,
            )
            print_prompt()
        elif msg_type == "ACK":
            if verbose_mode:
                print(
                    f"[VERBOSE] Received ACK for MESSAGE_ID: {content.get('MESSAGE_ID')}"
                )

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
