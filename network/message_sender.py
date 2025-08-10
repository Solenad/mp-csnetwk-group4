# network/message_sender.py
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
    message_id = secrets.token_hex(4)
    token = f"{sender_info['user_id']}|{timestamp + DEFAULT_TTL}|broadcast"

    message = (
        "TYPE: POST\n"
        f"USER_ID: {sender_info['user_id']}\n"
        f"CONTENT: {content}\n"
        f"TTL: {DEFAULT_TTL}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TOKEN: {token}\n\n"
    )
    send_broadcast(message)


def send_dm(recipient_id: str, content: str, sender_info: Dict) -> bool:
    peer = get_peer(recipient_id)
    if not peer:
        try:
            _, address = recipient_id.split("@")
            ip, port = address.split(":")
            ip = ip.strip()
            port = int(port.strip())
        except Exception:
            print_error(f"Invalid recipient ID format: {recipient_id}")
            return False
    else:
        # parse port from the canonical user_id stored in peer
        try:
            _, address = peer["user_id"].split("@")
            ip_from_userid, port_from_userid = address.split(":")
            ip = peer.get("ip", ip_from_userid)
            port = int(port_from_userid)
        except Exception:
            ip = peer["ip"]
            port = peer["port"]

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
        f"TOKEN: {token}\n\n"
    )

    return send_unicast(message, (ip, port))


def send_follow(user_id_to_follow, sender_info):
    peers = get_peer_list()
    for peer in peers:
        if peer["user_id"] == user_id_to_follow:
            timestamp = int(time.time())
            message_id = secrets.token_hex(4)
            token = f"{sender_info['user_id']}|{
                timestamp + DEFAULT_TTL}|follow"

            message = (
                "TYPE: FOLLOW\n"
                f"MESSAGE_ID: {message_id}\n"
                f"FROM: {sender_info['user_id']}\n"
                f"TO: {peer['user_id']}\n"
                f"TIMESTAMP: {timestamp}\n"
                f"TOKEN: {token}\n\n"
            )

            # Parse port from user_id (canonical)
            try:
                _, address = peer["user_id"].split("@")
                _, port = address.split(":")
                peer_port = int(port)
            except Exception:
                peer_port = peer["port"]

            peer_ip = peer["ip"]

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
            message_id = secrets.token_hex(4)
            token = f"{sender_info['user_id']}|{
                timestamp + DEFAULT_TTL}|follow"

            message = (
                "TYPE: UNFOLLOW\n"
                f"MESSAGE_ID: {message_id}\n"
                f"FROM: {sender_info['user_id']}\n"
                f"TO: {peer['user_id']}\n"
                f"TIMESTAMP: {timestamp}\n"
                f"TOKEN: {token}\n\n"
            )

            try:
                _, address = peer["user_id"].split("@")
                _, port = address.split(":")
                peer_port = int(port)
            except Exception:
                peer_port = peer["port"]

            peer_ip = peer["ip"]

            print_verbose(
                f"Sending UNFOLLOW to {peer_ip}:{
                    peer_port} for {peer['user_id']}"
            )
            return send_unicast(message, (peer_ip, peer_port))
    print_error(f"User {user_id_to_unfollow} not found")
    return False


def send_ack(message_id: str, recipient_user_id: str):
    peer = get_peer(recipient_user_id)
    if not peer:
        try:
            _, address = recipient_user_id.split("@")
            ip, port = address.split(":")
            ip = ip.strip()
            port = int(port.strip())
        except Exception:
            print_error(
                f"Cannot send ACK — invalid user ID format: {
                    recipient_user_id}"
            )
            return False
    else:
        # prefer canonical port from user_id
        try:
            _, address = peer["user_id"].split("@")
            _, port = address.split(":")
            port = int(port)
        except Exception:
            port = peer["port"]
        ip = peer["ip"]

    ack_message = (
        "TYPE: ACK\n"
        f"MESSAGE_ID: {
            message_id}\n"
        "STATUS: RECEIVED\n\n"
    )
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(ack_message.encode("utf-8"), (ip, port))
        print_verbose(f"ACK sent to {recipient_user_id} for MESSAGE_ID {message_id}")
        return True
    except Exception as e:
        print_error(f"Failed to send ACK: {e}")
        return False
