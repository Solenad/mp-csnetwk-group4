import socket
from typing import Dict
import time
import secrets
from ui.utils import print_error, print_verbose
from config import verbose_mode
from network.peer_registry import get_peer

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
    """RFC-compliant DM with retry and ACK checking"""
    peer = get_peer(recipient_id)
    if not peer:
        print_error(f"Peer {recipient_id} not found")
        return False

    timestamp = int(time.time())
    message_id = secrets.token_hex(4)
    message = (
        "TYPE: DM\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {recipient_id}\n"
        f"CONTENT: {content}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TOKEN: {sender_info['user_id']}|{timestamp + DEFAULT_TTL}|chat\n"
        "\n"
    )

    # Try 3 times with delay (RFC recommends retries for UDP)
    for attempt in range(3):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(2.0)  # Wait for ACK
                sock.sendto(message.encode(), (peer["ip"], peer["port"]))

                # Wait for ACK per RFC
                data, _ = sock.recvfrom(4096)
                if f"MESSAGE_ID: {message_id}" in data.decode():
                    if verbose_mode:
                        print_verbose(f"DM to {recipient_id} confirmed")
                    return True

        except socket.timeout:
            print_error(f"DM attempt {attempt+1} timeout")
            continue
        except Exception as e:
            print_error(f"DM send error: {e}")
            continue

    print_error(f"Failed to deliver DM to {recipient_id} after 3 attempts")
    return False


def send_follow(username_to_follow, sender_info, peers):
    timestamp = int(time.time())
    for peer in peers.values():
        if peer.get("username") == username_to_follow:
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
            if send_unicast(message, (peer["ip"], 50999)):
                print_verbose(f"Follow request sent to {username_to_follow}")
            return
    print_error(f"User {username_to_follow} not found")


def send_broadcast(message):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(message.encode("utf-8"), ("255.255.255.255", 50999))
    except Exception as e:
        print_error(f"Broadcast failed: {e}")
