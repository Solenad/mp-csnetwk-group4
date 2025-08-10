# main.py
from network.socket_manager import start_listening
from network.message_sender import send_ack
from network.broadcast import send_profile, my_info, send_immediate_discovery
from ui.cli import start_cli
from network.peer_registry import add_peer
import threading
import socket
from config import verbose_mode
from ui.utils import print_prompt
from network.peer_registry import add_peer
from network.group_manager import create_group, send_group_update, send_group_message, add_to_group, remove_from_group
from network.message_sender import send_group_create, send_unicast
from typing import Dict, List   

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
            avatar_b64=content.get("AVATAR_B64", "")
        )

        if msg_type == "POST":
            print(
                f"\n[POST] {content.get('DISPLAY_NAME', user_id)}: {content.get('CONTENT', '')}\n",
                end="",
                flush=True,
            )
            print_prompt()
            # Add to handle_message function in main.py
        elif msg_type == "GROUP_CREATE":
            group_id = content.get("GROUP_ID")
            group_name = content.get("GROUP_NAME")
            members = content.get("MEMBERS", "").split(",")
            
            if my_info['user_id'] in members:
                # Confirm we're actually a member
                if add_to_group(group_id, my_info['user_id']):
                    print(f"\n[GROUP] Joined group '{group_name}' (ID: {group_id})\n")
                    
                    # Send confirmation back to creator
                    if content.get("CREATOR") != my_info['user_id']:
                        ack_msg = (
                            "TYPE: GROUP_ACK\n"
                            f"GROUP_ID: {group_id}\n"
                            f"MEMBER: {my_info['user_id']}\n"
                            f"STATUS: JOINED\n"
                            "\n"
                        )
                        creator = content.get("CREATOR")
                        if creator:
                            peer = get_peer(creator)
                            if peer:
                                send_unicast(ack_msg, (peer['ip'], peer['port']))
                
                print_prompt()
    
        elif msg_type == "GROUP_ACK":
            group_id = content.get("GROUP_ID")
            member = content.get("MEMBER")
            status = content.get("STATUS")
            
            if status == "JOINED":
                print(f"\n[GROUP] {member.split('@')[0]} joined group {group_id}\n")
                print_prompt()

        elif msg_type == "GROUP_UPDATE":
            group_id = content.get("GROUP_ID")
            added = content.get("ADDED", "").split(",")
            removed = content.get("REMOVED", "").split(",")
            
            if user_id in added:
                add_to_group(group_id, user_id)
                print(f"\n[GROUP] Added to group '{content.get('GROUP_NAME')}'\n", end="", flush=True)
            elif user_id in removed:
                remove_from_group(group_id, user_id)
                print(f"\n[GROUP] Removed from group '{content.get('GROUP_NAME')}'\n", end="", flush=True)
            print_prompt()

        elif msg_type == "GROUP_MESSAGE":
            group_id = content.get("GROUP_ID")
            sender = content.get("FROM")
            message = content.get("CONTENT")
            
            if group_id in _groups and sender != my_info['user_id']:
                print(f"\n[GROUP {_groups[group_id]['name']}] {sender}: {message}\n", end="", flush=True)
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

def handle_profile_update(data):
    user_id = data["USER_ID"]
    if user_id not in peers:
        add_peer(
            user_id=user_id,
            ip=data["IP"],
            port=data["PORT"],
            display_name=data.get("DISPLAY_NAME", user_id.split("@")[0]),
            avatar_b64=data.get("avatar_b64", "")
        )
    else:
        peer = peers[user_id]
        peer["display_name"] = data.get("DISPLAY_NAME", peer["display_name"])
        if "avatar_b64" in data:
            peer["avatar_b64"] = data["avatar_b64"]  # update PFP


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
