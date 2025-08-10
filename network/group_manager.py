# group_manager.py
import secrets
import time
from typing import Dict, List, Optional
from network.peer_registry import get_peer
from network.message_sender import send_unicast
from ui.utils import print_info, print_error

_groups: Dict[str, Dict] = {}  # group_id -> group_data

def create_group(group_name: str, creator_id: str, initial_members: List[str] = None) -> str:
    """Create a new group and return group_id"""
    group_id = f"GROUP_{secrets.token_hex(4)}"
    members = [creator_id]
    if initial_members:
        members.extend(initial_members)
    _groups[group_id] = {
        'id': group_id,
        'name': group_name,
        'creator': creator_id,
        'members': list(set(members)),  # Ensure unique members
        'messages': []
    }
    return group_id

def get_group(group_id: str) -> Optional[Dict]:
    """Get group data by ID"""
    return _groups.get(group_id)

def get_user_groups(user_id: str) -> List[Dict]:
    """Get all groups a user belongs to"""
    return [group for group in _groups.values() if user_id in group['members']]

def add_to_group(group_id: str, user_id: str) -> bool:
    """Add a user to a group with proper synchronization"""
    group = get_group(group_id)
    if not group:
        # Create a minimal group structure if it doesn't exist
        _groups[group_id] = {
            'id': group_id,
            'name': f"Group-{group_id}",
            'creator': None,
            'members': [],
            'messages': []
        }
        group = _groups[group_id]
    
    if user_id not in group['members']:
        group['members'].append(user_id)
        return True
    return False

def remove_from_group(group_id: str, user_id: str) -> bool:
    """Remove a user from a group"""
    group = get_group(group_id)
    if not group:
        return False
    if user_id in group['members']:
        group['members'].remove(user_id)
        return True
    return False

def send_group_update(group_id: str, updater_id: str, added_members: List[str] = None, removed_members: List[str] = None) -> bool:
    """Notify group members about membership changes"""
    group = get_group(group_id)
    if not group:
        return False
    
    added_members = added_members or []
    removed_members = removed_members or []
    
    message = (
        "TYPE: GROUP_UPDATE\n"
        f"GROUP_ID: {group_id}\n"
        f"GROUP_NAME: {group['name']}\n"
        f"FROM: {updater_id}\n"
        f"ADDED: {','.join(added_members)}\n"
        f"REMOVED: {','.join(removed_members)}\n"
        "\n"
    )
    
    for member in group['members']:
        if member != updater_id:
            peer = get_peer(member)
            if peer:
                send_unicast(message, (peer['ip'], peer['port']))
    return True

def send_group_message(group_id: str, content: str, sender_info: Dict) -> bool:
    """Send a message to a group"""
    group = get_group(group_id)
    if not group:
        return False
    
    message = (
        "TYPE: GROUP_MESSAGE\n"
        f"GROUP_ID: {group_id}\n"
        f"FROM: {sender_info['user_id']}\n"
        f"CONTENT: {content}\n"
        "\n"
    )
    
    group['messages'].append({
        'sender': sender_info['user_id'],
        'content': content,
        'timestamp': time.time()
    })
    
    for member in group['members']:
        if member != sender_info['user_id']:
            peer = get_peer(member)
            if peer:
                send_unicast(message, (peer['ip'], peer['port']))
    
    return True