# network/peer_registry.py
import time
from typing import Dict, List

_peer_registry: Dict[str, Dict] = {}


def _normalize_user_id_and_port(user_id: str, port_hint: int = None):
    """
    Ensure the stored user_id contains a port (username@ip:port).
    If user_id already contains a port, return it. Otherwise, append port_hint if given.
    """
    try:
        username, address = user_id.split("@", 1)
        if ":" in address:
            ip, port = address.split(":", 1)
            return f"{username}@{ip}:{int(port)}", int(port)
        else:
            if port_hint is not None:
                return f"{username}@{address}:{int(port_hint)}", int(port_hint)
            return user_id, port_hint
    except Exception:
        return user_id, port_hint


def get_peer_list(exclude_user_id: str = None) -> List[Dict]:
    """Return list of all known peers, optionally excluding a user"""
    if exclude_user_id:
        return [
            peer
            for peer in _peer_registry.values()
            if peer["user_id"] != exclude_user_id
        ]
    return list(_peer_registry.values())


def get_peer(user_id: str) -> Dict:
    return _peer_registry.get(user_id)


def add_peer(
    user_id: str, ip: str, port: int = 50999, display_name: str = None
) -> None:
    canonical_user_id, canonical_port = _normalize_user_id_and_port(user_id, port)
    if canonical_port is None:
        canonical_port = port

    now = time.time()
    existing = _peer_registry.get(canonical_user_id)
    entry = {
        "user_id": canonical_user_id,
        "ip": ip,
        "port": canonical_port,
        "display_name": display_name or canonical_user_id.split("@")[0],
        "last_seen": now,
        # <-- new
        "last_profile_sent": existing["last_profile_sent"] if existing else 0,
    }
    if existing:
        existing.update(entry)
    else:
        _peer_registry[canonical_user_id] = entry


def remove_peer(user_id: str) -> None:
    _peer_registry.pop(user_id, None)


def clear_peers() -> None:
    _peer_registry.clear()


def update_last_seen(user_id: str) -> None:
    if user_id in _peer_registry:
        _peer_registry[user_id]["last_seen"] = time.time()
