# network/message_sender.py
import os
from network.peer_registry import get_peer_list, get_peer
from network.broadcast import send_broadcast, get_mime_type
from network.token_utils import generate_token
import socket
import config
from typing import Dict
import time
import secrets
import base64
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
    token = generate_token(sender_info["user_id"], "broadcast")

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
    token = generate_token(sender_info["user_id"], "chat")

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
            token = generate_token(sender_info["user_id"], "follow")

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
                f"Sending FOLLOW to {peer_ip}:{peer_port} for {peer['user_id']}"
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
            token = generate_token(sender_info["user_id"], "follow")

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
                f"Sending UNFOLLOW to {peer_ip}:{peer_port} for {peer['user_id']}"
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
                f"Cannot send ACK — invalid user ID format: {recipient_user_id}"
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


def send_like(post_timestamp: int, sender_info: Dict, action: str = "LIKE") -> bool:
    """Send a LIKE/UNLIKE message for a post. Returns success status."""
    # Check if already liked/unliked
    post_key = (sender_info["user_id"], post_timestamp)

    if action == "LIKE" and post_key in config.liked_posts:
        print_error("You've already liked this post")
        return False
    elif action == "UNLIKE" and post_key not in config.liked_posts:
        print_error("You haven't liked this post yet")
        return False

    timestamp = int(time.time())
    message_id = secrets.token_hex(4)
    token = generate_token(
        sender_info["user_id"], "broadcast", ttl=config.TOKEN_TTL["broadcast"]
    )

    message = (
        "TYPE: LIKE\n"
        f"FROM: {sender_info['user_id']}\n"
        f"POST_TIMESTAMP: {post_timestamp}\n"
        f"ACTION: {action}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TOKEN: {token}\n\n"
    )

    send_broadcast(message)

    # Update local state
    if action == "LIKE":
        config.liked_posts.add(post_key)
    else:
        config.liked_posts.discard(post_key)

    return True


def send_file_offer(
    recipient_id: str, filepath: str, description: str, sender_info: Dict
) -> bool:
    """Send a FILE_OFFER message to initiate file transfer"""
    if not os.path.exists(filepath):
        print_error(f"File not found: {filepath}")
        return False

    peer = get_peer(recipient_id)
    if not peer:
        print_error(f"Recipient {recipient_id} not found")
        return False

    try:
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        filetype = get_mime_type(filepath)
        fileid = secrets.token_hex(4)
        timestamp = int(time.time())
        token = generate_token(sender_info["user_id"], "file")

        message = (
            "TYPE: FILE_OFFER\n"
            f"FROM: {sender_info['user_id']}\n"
            f"TO: {recipient_id}\n"
            f"FILENAME: {filename}\n"
            f"FILESIZE: {filesize}\n"
            f"FILETYPE: {filetype}\n"
            f"FILEID: {fileid}\n"
            f"DESCRIPTION: {description}\n"
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

        if config.verbose_mode:
            print_verbose(
                f"Sending FILE_OFFER to {peer_ip}:{peer_port}\n"
                f" - File: {filename} ({filesize} bytes)\n"
                f" - ID: {fileid}\n"
            )

        if send_unicast(message, (peer_ip, peer_port)):
            # Store file info for chunking
            config.active_file_transfers[fileid] = {
                "filepath": filepath,
                "recipient": recipient_id,
                "chunk_size": 1024,  # 1KB chunks
                "total_chunks": (filesize // 1024) + (1 if filesize % 1024 else 0),
                "next_chunk": 0,
                "sender_info": sender_info,
            }
            return True
        return False

    except Exception as e:
        print_error(f"Failed to send file offer: {e}")
        return False


def send_file_chunk(fileid: str, chunk_index: int, sender_info: Dict) -> bool:
    """Send a single file chunk"""
    if fileid not in config.active_file_transfers:
        print_error(f"No active transfer for file ID {fileid}")
        return False

    transfer = config.active_file_transfers[fileid]
    filepath = transfer["filepath"]
    recipient_id = transfer["recipient"]
    chunk_size = transfer["chunk_size"]
    total_chunks = transfer["total_chunks"]

    peer = get_peer(recipient_id)
    if not peer:
        print_error(f"Recipient {recipient_id} not found")
        return False

    try:
        with open(filepath, "rb") as f:
            f.seek(chunk_index * chunk_size)
            chunk_data = f.read(chunk_size)

        if not chunk_data:
            return False  # No more data to send

        encoded_data = base64.b64encode(chunk_data).decode("utf-8")
        timestamp = int(time.time())
        token = generate_token(sender_info["user_id"], "file")

        message = (
            "TYPE: FILE_CHUNK\n"
            f"FROM: {sender_info['user_id']}\n"
            f"TO: {recipient_id}\n"
            f"FILEID: {fileid}\n"
            f"CHUNK_INDEX: {chunk_index}\n"
            f"TOTAL_CHUNKS: {total_chunks}\n"
            f"CHUNK_SIZE: {len(chunk_data)}\n"
            f"TOKEN: {token}\n"
            f"DATA: {encoded_data}\n\n"
        )

        # Parse port from user_id (canonical)
        try:
            _, address = peer["user_id"].split("@")
            _, port = address.split(":")
            peer_port = int(port)
        except Exception:
            peer_port = peer["port"]

        peer_ip = peer["ip"]

        if config.verbose_mode:
            print_verbose(
                f"Sending FILE_CHUNK {chunk_index+1}/{total_chunks} "
                f"for {fileid} to {peer_ip}:{peer_port}"
            )

        return send_unicast(message, (peer_ip, peer_port))

    except Exception as e:
        print_error(f"Failed to send file chunk: {e}")
        return False


def send_file_received(
    fileid: str, recipient_id: str, sender_info: Dict, status: str = "COMPLETE"
) -> bool:
    """Send FILE_RECEIVED acknowledgment"""
    peer = get_peer(recipient_id)
    if not peer:
        print_error(f"Recipient {recipient_id} not found")
        return False

    timestamp = int(time.time())

    message = (
        "TYPE: FILE_RECEIVED\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {recipient_id}\n"
        f"FILEID: {fileid}\n"
        f"STATUS: {status}\n"
        f"TIMESTAMP: {timestamp}\n\n"
    )

    # Parse port from user_id (canonical)
    try:
        _, address = peer["user_id"].split("@")
        _, port = address.split(":")
        peer_port = int(port)
    except Exception:
        peer_port = peer["port"]

    peer_ip = peer["ip"]

    if config.verbose_mode:
        print_verbose(
            f"Sending FILE_RECEIVED for {fileid} to {peer_ip}:{peer_port}\n"
            f" - Status: {status}"
        )

    return send_unicast(message, (peer_ip, peer_port))
