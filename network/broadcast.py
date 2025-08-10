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
    system = platform.system().lower()

    try:
        if system == "windows":
            # Use ipconfig
            result = subprocess.run(
                ["ipconfig"], capture_output=True, text=True, check=True
            ).stdout

            # Extract IPv4 + subnet mask from ipconfig output
            ipv4_match = re.search(r"IPv4 Address.*?: (\d+\.\d+\.\d+\.\d+)", result)
            mask_match = re.search(r"Subnet Mask.*?: (\d+\.\d+\.\d+\.\d+)", result)

            if ipv4_match and mask_match:
                ip_str = ipv4_match.group(1)
                mask_str = mask_match.group(1)
                net = ipaddress.IPv4Network(f"{ip_str}/{mask_str}", strict=False)
                return str(net.broadcast_address)

        elif system == "linux":
            # Use ip command
            result = subprocess.run(
                ["ip", "-4", "addr", "show", "scope", "global"],
                capture_output=True,
                text=True,
                check=True,
            ).stdout

            for line in result.splitlines():
                line = line.strip()
                if line.startswith("inet "):
                    parts = line.split()
                    if "brd" in parts:
                        return parts[parts.index("brd") + 1]
                    else:
                        ip_cidr = parts[1]
                        net = ipaddress.ip_network(ip_cidr, strict=False)
                        return str(net.broadcast_address)

    except Exception as e:
        print(f"Failed to detect broadcast: {e}")

    # Fallback
    return "255.255.255.255"


def get_broadcast_ip():
    """
    Returns the broadcast IP of the default interface.
    Works on Linux (Fedora, Ubuntu, etc.).
    """
    try:
        # Get default interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()

        # Calculate broadcast from IP + netmask
        iface = get_interface_name(local_ip)
        if iface:
            return get_iface_broadcast(iface)
    except Exception as e:
        if verbose_mode:
            print(f"Error getting broadcast IP: {e}")
    return "255.255.255.255"


def get_interface_name(ip_addr):
    """
    Finds the interface name for a given IP address.
    """
    import netifaces

    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
        for addr in addrs:
            if addr.get("addr") == ip_addr:
                return iface
    return None


def get_iface_broadcast(iface_name):
    """
    Uses netifaces to get the broadcast address of an interface.
    """
    import netifaces

    addrs = netifaces.ifaddresses(iface_name).get(netifaces.AF_INET, [])
    for addr in addrs:
        if "broadcast" in addr:
            return addr["broadcast"]
    return "255.255.255.255"


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

    # Optional avatar handling
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

    # RFC requires messages to end with a blank line (i.e., \n\n)
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
    Sends a UDP broadcast to both the subnet broadcast address and the global broadcast.
    """
    subnet_broadcast = get_subnet_broadcast()
    # use a set to avoid duplicates
    broadcast_targets = {subnet_broadcast, "255.255.255.255"}

    ports = target_ports if target_ports else list(range(50999, 50999 + 100))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for target in broadcast_targets:
                for port in ports:
                    sock.sendto(message.encode("utf-8"), (target, port))
    except Exception as e:
        print(f"Broadcast failed: {e}")


def send_immediate_discovery(my_info):
    """Send initial discovery bursts per RFC"""
    # Send 3 quick PROFILEs first
    for _ in range(3):
        send_profile(my_info)
        time.sleep(0.5)
    # Then send PINGs to establish presence
    for _ in range(3):
        send_ping(my_info)
        time.sleep(0.5)


my_info = {
    "username": "User" + str(int(time.time()) % 1000),
    "hostname": socket.gethostname(),
    "user_id": f"User{int(time.time()) % 1000}@{get_local_ip()}",
    "status": "Available",
}
