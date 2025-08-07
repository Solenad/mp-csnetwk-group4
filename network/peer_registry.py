# peer_registry.py
import time
from typing import Dict, List

_peer_registry: Dict[str, Dict] = {}


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
    user_id: str, ip: str, port: int, display_name: str = None
) -> None:
    _peer_registry[user_id] = {
        "user_id": user_id,
        "ip": ip,
        "port": port,
        "display_name": display_name or user_id.split("@")[0],
        "last_seen": time.time(),
    }


def remove_peer(user_id: str) -> None:
    _peer_registry.pop(user_id, None)


def clear_peers() -> None:
    _peer_registry.clear()


def update_last_seen(user_id: str) -> None:
    if user_id in _peer_registry:
        _peer_registry[user_id]["last_seen"] = time.time()
