import socket
import time
import secrets
from network.peer_registry import get_peer_list
from ui.utils import print_error, print_verbose

DEFAULT_TTL = 3600


def send_message_to_peers(message, sender_info):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for peer in get_peer_list():
        print_verbose(
            f"Sending message to {
                      peer['username']}@{peer['address'][0]}:{peer['address'][1]}"
        )
        sock.sendto(message.encode(), peer["address"])
    sock.close()


def send_post(content, sender_info):
    user_id = sender_info["user_id"]
    timestamp = int(time.time())
    ttl = DEFAULT_TTL
    message_id = secrets.token_hex(8)
    token = f"{user_id}|{timestamp + ttl}|broadcast"

    message = (
        "LSNP/1.0\n"
        "TYPE: POST\n"
        f"USER_ID: {user_id}\n"
        f"CONTENT: {content}\n"
        f"TTL: {ttl}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TOKEN: {token}\n"
    )

    print_verbose(f"Creating POST message:\n{message}")
    send_message_to_peers(message, sender_info)
    print_verbose(f"Broadcast post: {content}")


def send_dm(recipient_username, content, sender_info):
    for peer in get_peer_list():
        if peer["username"] == recipient_username:
            from_id = sender_info["user_id"]
            to_id = peer["user_id"]
            timestamp = int(time.time())
            message_id = secrets.token_hex(8)
            token = f"{from_id}|{timestamp + DEFAULT_TTL}|chat"

            message = (
                "LSNP/1.0\n"
                "TYPE: DM\n"
                f"FROM: {from_id}\n"
                f"TO: {to_id}\n"
                f"CONTENT: {content}\n"
                f"TIMESTAMP: {timestamp}\n"
                f"MESSAGE_ID: {message_id}\n"
                f"TOKEN: {token}\n"
            )

            print_verbose(f"Creating DM message:\n{message}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode(), peer["address"])
            sock.close()
            print_verbose(f"Sent DM to {recipient_username}: {content}")
            return

    print_error(f"User '{recipient_username}' not found in peer list.")


def send_follow(username_to_follow, sender_info):
    for peer in get_peer_list():
        if peer["username"] == username_to_follow:
            from_id = sender_info["user_id"]
            to_id = peer["user_id"]
            timestamp = int(time.time())
            message_id = secrets.token_hex(8)
            token = f"{from_id}|{timestamp + DEFAULT_TTL}|follow"

            message = (
                "LSNP/1.0\n"
                "TYPE: FOLLOW\n"
                f"MESSAGE_ID: {message_id}\n"
                f"FROM: {from_id}\n"
                f"TO: {to_id}\n"
                f"TIMESTAMP: {timestamp}\n"
                f"TOKEN: {token}\n"
            )

            print_verbose(f"Creating FOLLOW message:\n{message}")
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(message.encode(), peer["address"])
            sock.close()
            print_verbose(f"Sent follow request to {username_to_follow}")
            return

    print_error(f"User '{username_to_follow}' not found in peer list.")
