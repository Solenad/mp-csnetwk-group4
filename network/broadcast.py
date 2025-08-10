# network/broadcast.py
import socket
import base64
import os
import time
import subprocess
import platform
import re
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
    Detect the LAN broadcast address without netifaces.
    Prefers 192.168.x.x (then other private ranges).
    Works on Windows and Linux.
    """
    system = platform.system().lower()

    try:
        if system == "windows":
            result = subprocess.run(
                ["ipconfig"], capture_output=True, text=True, check=True
            ).stdout

            # Find all IPv4 + mask pairs
            matches = re.findall(
                r"IPv4 Address.*?: (\d+\.\d+\.\d+\.\d+).*?"
                r"Subnet Mask.*?: (\d+\.\d+\.\d+\.\d+)",
                result,
                flags=re.DOTALL,
            )

            chosen_ip, chosen_mask = None, None
            for ip_str, mask_str in matches:
                if ip_str.startswith("192.168."):
                    chosen_ip, chosen_mask = ip_str, mask_str
                    break
                elif ipaddress.ip_address(ip_str).is_private:
                    chosen_ip, chosen_mask = ip_str, mask_str

            if chosen_ip and chosen_mask:
                net = ipaddress.IPv4Network(f"{chosen_ip}/{chosen_mask}", strict=False)
                return str(net.broadcast_address)

        elif system == "linux":
            result = subprocess.run(
                ["ip", "-4", "addr", "show", "scope", "global"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout

            candidates = []
            for line in result.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    parts = line.split()
                    ip_cidr = parts[1]
                    ip_str = ip_cidr.split("/")[0]
                    net = ipaddress.ip_network(ip_cidr, strict=False)
                    candidates.append((ip_str, str(net.broadcast_address)))

            # Prefer 192.168.x.x
            for ip_str, brd in candidates:
                if ip_str.startswith("192.168."):
                    return brd
            if candidates:
                return candidates[0][1]

    except Exception as e:
        if verbose_mode:
            print(f"Failed to detect broadcast: {e}")

    return "255.255.255.255"


# Removed get_interface_name and get_iface_broadcast (netifaces dependency)


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
    )

    avatar_path = my_info.get("avatar_path")
    if avatar_path and os.path.exists(avatar_path):
        try:
            with open(avatar_path, "rb") as f:
                avatar_data = base64.b64encode(f.read()).decode("utf-8")
                message += (
                    f"AVATAR_TYPE: {get_mime_type(avatar_path)}\n"
                    "AVATAR_ENCODING: base64\n"
                    f"AVATAR_DATA: {avatar_data}\n"
                )
        except Exception as e:
            if verbose_mode:
                print(f"Failed to include avatar: {e}")

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
    """
    subnet_broadcast = get_subnet_broadcast()
    ports = target_ports if target_ports else list(range(50999, 50999 + 100))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for port in ports:
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
}
