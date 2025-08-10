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


def send_ping(my_info, port=50999):
    """RFC-compliant PING message"""
    message = "TYPE: PING\n" f"USER_ID: {my_info['user_id']}\n\n"
    send_broadcast(message, target_ports=[port])


def send_profile(my_info: Dict, port=50999) -> None:
    message = (
        "TYPE: PROFILE\n"
        f"USER_ID: {my_info['user_id']}\n"
        f"DISPLAY_NAME: {my_info['username']}\n"
        f"STATUS: {my_info.get('status', 'Active')}\n"
        f"PORT: {my_info.get('port', port)}\n\n"
    )

    avatar_path = my_info.get("avatar_path")
    if avatar_path and os.path.exists(avatar_path):
        try:
            with open(avatar_path, "rb") as f:
                avatar_data = base64.b64encode(f.read()).decode("utf-8")
                message += (
                    f"AVATAR_TYPE: {get_mime_type(avatar_path)}\n"
                    "AVATAR_ENCODING: base64\n"
                    f"AVATAR_DATA: {avatar_data}\n\n"
                )
        except Exception as e:
            if verbose_mode:
                print(f"Failed to include avatar: {e}")

    message += "\n\n"
    send_broadcast(message, target_ports=[port])


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
    Use target_ports if specified, else use default port 50999.
    """
    subnet_broadcast = get_subnet_broadcast()
    ports = target_ports if target_ports else [50999]  # default port
    local_ip = get_local_ip()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Bind to 0.0.0.0 ephemeral port
            try:
                sock.bind(("0.0.0.0", 0))
            except Exception as e:
                if verbose_mode:
                    print(f"Could not bind broadcast socket: {e}")

            for port in ports:
                if verbose_mode:
                    print(
                        f"[broadcast] sending from {
                            local_ip} -> {subnet_broadcast}:{port}"
                    )
                sock.sendto(message.encode("utf-8"), (subnet_broadcast, port))
    except Exception as e:
        print(f"Broadcast failed: {e}")


def send_immediate_discovery(my_info, port=50999):
    for _ in range(3):
        send_profile(my_info, port=port)
        time.sleep(0.5)
    for _ in range(3):
        send_ping(my_info, port=port)
        time.sleep(0.5)


my_info = {
    "username": "User" + str(int(time.time()) % 1000),
    "hostname": socket.gethostname(),
    "user_id": f"User{int(time.time()) % 1000}@{get_local_ip()}",
    "status": "Available",
}
