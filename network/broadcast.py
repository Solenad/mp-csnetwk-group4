# network/broadcast.py
import socket
import base64
import os
import time
import subprocess
import platform
import ipaddress
from typing import Dict
from config import verbose_mode


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def get_subnet_broadcast():
    """
    Detect broadcast address for the interface used by get_local_ip().
    Works on Windows and Linux, ignores other adapters.
    """
    local_ip = get_local_ip()
    system = platform.system().lower()

    try:
        if system == "windows":
            output = subprocess.check_output(
                "ipconfig", encoding="utf-8", errors="ignore"
            )
            current_ip = None
            for line in output.splitlines():
                line = line.strip()
                if "IPv4 Address" in line or line.lower().startswith("ipv4 address"):
                    current_ip = line.split(":")[-1].strip()
                elif "Subnet Mask" in line or line.lower().startswith("subnet mask"):
                    mask = line.split(":")[-1].strip()
                    if current_ip == local_ip:
                        net = ipaddress.IPv4Network(f"{local_ip}/{mask}", strict=False)
                        return str(net.broadcast_address)
        elif system == "linux":
            output = subprocess.check_output(
                ["ip", "-4", "addr", "show", "scope", "global"], encoding="utf-8"
            )
            for line in output.splitlines():
                if local_ip in line:
                    parts = line.strip().split()
                    cidr = parts[1]
                    net = ipaddress.IPv4Network(cidr, strict=False)
                    return str(net.broadcast_address)

    except Exception as e:
        if verbose_mode:
            print(f"Could not detect broadcast: {e}")

    # Fallback guess: same /24
    return f"{'.'.join(local_ip.split('.')[:3])}.255"


def send_ping(my_info):
    """RFC-compliant PING message"""
    message = "TYPE: PING\n" f"USER_ID: {my_info['user_id']}\n\n"
    send_broadcast(message)


def send_profile(my_info: Dict) -> None:
    """Send PROFILE message with current port (RFC Section 5.1)"""
    message = (
        "TYPE: PROFILE\n"
        f"USER_ID: {my_info['user_id']}\n"
        f"DISPLAY_NAME: {my_info['username']}\n"
        f"STATUS: {my_info.get('status', 'Active')}\n"
        f"PORT: {my_info.get('port', 50999)}\n"
        f"AVATAR_TYPE: {my_info['avatar_type']}\n"
        f"AVATAR_ENCODING: base64\n"
        f"AVATAR_DATA: {my_info['avatar_data']}\n"
    )

    message += "\n\n"
    send_broadcast(message)


def get_mime_type(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
    }.get(ext, "application/octet-stream")


def send_broadcast(message, target_ports=None):
    """
    Sends a UDP broadcast to the detected subnet broadcast address.
    For testing, defaults to port 50999 only.
    """
    subnet_broadcast = get_subnet_broadcast()
    ports = target_ports if target_ports else [50999]  # fixed to main listening port
    local_ip = get_local_ip()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Bind the socket to the preferred local IP (ephemeral port 0) so outgoing uses that NIC
            try:
                sock.bind((local_ip, 0))
            except Exception as e:
                if verbose_mode:
                    print(
                        f"Could not bind broadcast socket to {local_ip}: {e}"
                    )

            for port in ports:
                if verbose_mode:
                    print(
                        f"[broadcast] sending from {local_ip} -> {subnet_broadcast}:{port}"
                    )
                sock.sendto(message.encode("utf-8"), (subnet_broadcast, port))
    except Exception as e:
        print(f"Broadcast failed: {e}")


def send_immediate_discovery(my_info):
    """Send initial discovery bursts per RFC"""
    for _ in range(3):
        send_profile(my_info)
        time.sleep(0.5)
    for _ in range(3):
        send_ping(my_info)
        time.sleep(0.5)


my_info = {
    "username": "User" + str(int(time.time()) % 1000),
    "hostname": socket.gethostname(),
    "user_id": f"User{int(time.time()) % 1000}@{get_local_ip()}",
    "status": "Available",
    "avatar_type": None,
    "avatar_data": None
}
