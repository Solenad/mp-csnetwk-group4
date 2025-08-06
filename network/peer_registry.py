# peer_registry.py
import time
from typing import Dict, List

# Format: {user_id: {"ip": str, "port": int, "display_name": str, "last_seen": float}}
_peer_registry: Dict[str, Dict] = {}


def get_peer_list() -> List[Dict]:
    """Return list of all known peers"""
    return list(_peer_registry.values())


def get_peer(user_id: str) -> Dict:
    """Get specific peer by user_id"""
    return _peer_registry.get(user_id)


def add_peer(
    user_id: str, ip: str, port: int = 50999, display_name: str = None
) -> None:
    """Add or update a peer in the registry"""
    _peer_registry[user_id] = {
        "ip": ip,
        "port": port,
        "display_name": display_name or user_id.split("@")[0],
        "last_seen": time.time(),
    }


def remove_peer(user_id: str) -> None:
    """Remove a peer from the registry"""
    _peer_registry.pop(user_id, None)


def clear_peers() -> None:
    """Clear all peers from registry"""
    _peer_registry.clear()


def update_last_seen(user_id: str) -> None:
    """Update last seen timestamp for a peer"""
    if user_id in _peer_registry:
        _peer_registry[user_id]["last_seen"] = time.time()
