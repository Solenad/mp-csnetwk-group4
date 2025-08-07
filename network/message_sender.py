from network.peer_registry import get_peer_list, get_peer
from network.broadcast import send_broadcast
import socket
from typing import Dict
import time
import secrets
from ui.utils import print_error, print_verbose

DEFAULT_TTL = 3600  # 1 hour default TTL per RFC


def send_unicast(message, recipient_addr):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(message.encode("utf-8"), recipient_addr)
        return True
    except Exception as e:
        print_error(f"Failed to send message: {e}")
        return False


def send_post(content, sender_info):
    timestamp = int(time.time())
    message = (
        "TYPE: POST\n"
        f"USER_ID: {sender_info['user_id']}\n"
        f"CONTENT: {content}\n"
        f"TTL: {DEFAULT_TTL}\n"
        f"MESSAGE_ID: {secrets.token_hex(4)}\n"
        f"TOKEN: {sender_info['user_id']}|{
            timestamp + DEFAULT_TTL}|broadcast\n"
        "\n"
    )
    send_broadcast(message)


def send_dm(recipient_id: str, content: str, sender_info: Dict) -> bool:
    peer = get_peer(recipient_id)
    if not peer:
        print_error(f"Peer {recipient_id} not found")
        return False

    timestamp = int(time.time())
    message_id = secrets.token_hex(4)
    token = f"{sender_info['user_id']}|{timestamp + DEFAULT_TTL}|chat"

    message = (
        "TYPE: DM\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {recipient_id}\n"
        f"CONTENT: {content}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TOKEN: {token}\n"
        "\n"
    )

    try:
        # Use unicast as specified in RFC
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(message.encode(), (peer["ip"], peer["port"]))
        print(f"\nDM sent to {recipient_id}\n>> ", end="", flush=True)
        return True
    except Exception as e:
        print_error(f"Failed to send DM: {e}")
        return False


def send_follow(user_id_to_follow, sender_info):
    peers = get_peer_list()
    for peer in peers:
        if peer["user_id"] == user_id_to_follow:
            timestamp = int(time.time())
            message = (
                "TYPE: FOLLOW\n"
                f"FROM: {sender_info['user_id']}\n"
                f"TO: {peer['user_id']}\n"
                f"TIMESTAMP: {timestamp}\n"
                f"MESSAGE_ID: {secrets.token_hex(4)}\n"
                f"TOKEN: {sender_info['user_id']}|{
                    timestamp + DEFAULT_TTL}|follow\n"
                "\n"
            )

            # Parse port from user_id, not from peer['port']
            host, port = peer["user_id"].split("@")[1].split(":")
            peer_ip = peer["ip"]
            peer_port = int(port)

            print_verbose(
                f"Sending FOLLOW to {peer_ip}:{
                    peer_port} for {peer['user_id']}"
            )

            return send_unicast(message, (peer_ip, peer_port))
    print_error(f"User {user_id_to_follow} not found")
    return False


def send_unfollow(user_id_to_unfollow, sender_info):
    peers = get_peer_list()
    for peer in peers:
        if peer["user_id"] == user_id_to_unfollow:
            timestamp = int(time.time())
            message = (
                "TYPE: UNFOLLOW\n"
                f"FROM: {sender_info['user_id']}\n"
                f"TO: {peer['user_id']}\n"
                f"TIMESTAMP: {timestamp}\n"
                f"MESSAGE_ID: {secrets.token_hex(4)}\n"
                f"TOKEN: {sender_info['user_id']}|{
                    timestamp + DEFAULT_TTL}|follow\n"
                "\n"
            )

            # Parse port from user_id, not from peer['port']
            host, port = peer["user_id"].split("@")[1].split(":")
            peer_ip = peer["ip"]
            peer_port = int(port)

            print_verbose(
                f"Sending UNFOLLOW to {peer_ip}:{
                    peer_port} for {peer['user_id']}"
            )

            return send_unicast(message, (peer_ip, peer_port))
    print_error(f"User {user_id_to_unfollow} not found")
    return False
