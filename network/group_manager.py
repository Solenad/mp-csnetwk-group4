# network/group_manager.py
import time
from typing import Dict, List, Set
from network.message_sender import send_unicast, send_ack
from network.peer_registry import get_peer
from network.token_utils import generate_token
from ui.utils import print_info, print_error, print_success
import config
import secrets

# Local storage for group information
_groups: Dict[str, Dict] = {}  # GROUP_ID -> {name, creator, members, last_updated}

def create_group(group_id: str, group_name: str, members: List[str], creator_info: Dict) -> bool:
    """Create a new group with the specified members"""
    if group_id in _groups:
        print_error(f"Group {group_id} already exists")
        return False

    # Ensure creator is included in members
    creator_id = creator_info["user_id"]
    if creator_id not in members:
        members.append(creator_id)

    # Store group info locally
    _groups[group_id] = {
        "name": group_name,
        "creator": creator_id,
        "members": set(members),
        "last_updated": time.time()
    }

    # Generate and send GROUP_CREATE message to all members
    timestamp = int(time.time())
    message_id = secrets.token_hex(4)
    token = generate_token(creator_id, "group")

    message = (
        "TYPE: GROUP_CREATE\n"
        f"FROM: {creator_id}\n"
        f"GROUP_ID: {group_id}\n"
        f"GROUP_NAME: {group_name}\n"
        f"MEMBERS: {','.join(members)}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TOKEN: {token}\n\n"
    )

    # Send to each member
    for member in members:
        if member == creator_id:
            continue  # No need to send to self
        peer = get_peer(member)
        if peer:
            send_unicast(message, (peer["ip"], peer["port"]))
        else:
            print_error(f"Could not find peer {member} to send group invite")

    print_success(f"Group {group_name} created with ID {group_id}")
    return True

def update_group(group_id: str, add_members: List[str], remove_members: List[str], updater_info: Dict) -> bool:
    """Update group membership by adding and/or removing members"""
    if group_id not in _groups:
        print_error(f"Group {group_id} does not exist")
        return False

    group = _groups[group_id]
    if updater_info["user_id"] != group["creator"]:
        print_error("Only group creator can update membership")
        return False

    # Update local membership
    current_members = group["members"]
    
    # Add new members
    for member in add_members:
        if member:  # Skip empty strings
            current_members.add(member)
    
    # Remove specified members
    for member in remove_members:
        if member in current_members:
            current_members.remove(member)

    group["last_updated"] = time.time()

    # Generate and send GROUP_UPDATE message to all members
    timestamp = int(time.time())
    message_id = secrets.token_hex(4)
    token = generate_token(updater_info["user_id"], "group")

    message = (
        "TYPE: GROUP_UPDATE\n"
        f"FROM: {updater_info['user_id']}\n"
        f"GROUP_ID: {group_id}\n"
        f"ADD: {','.join(add_members) if add_members else ''}\n"
        f"REMOVE: {','.join(remove_members) if remove_members else ''}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TOKEN: {token}\n\n"
    )

    # Send to all current members (including new ones)
    for member in current_members:
        if member == updater_info["user_id"]:
            continue  # No need to send to self
        peer = get_peer(member)
        if peer:
            send_unicast(message, (peer["ip"], peer["port"]))
        else:
            print_error(f"Could not find peer {member} to send group update")

    print_success(f"Group {group_id} membership updated")
    return True

def send_group_message(group_id: str, content: str, sender_info: Dict) -> bool:
    """Send a message to all members of a group"""
    if group_id not in _groups:
        print_error(f"Group {group_id} does not exist")
        return False

    if sender_info["user_id"] not in _groups[group_id]["members"]:
        print_error("You are not a member of this group")
        return False

    members = _groups[group_id]["members"]
    timestamp = int(time.time())
    message_id = secrets.token_hex(4)
    token = generate_token(sender_info["user_id"], "group")

    message = (
        "TYPE: GROUP_MESSAGE\n"
        f"FROM: {sender_info['user_id']}\n"
        f"GROUP_ID: {group_id}\n"
        f"CONTENT: {content}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TOKEN: {token}\n\n"
    )

    # Send to each member except sender
    for member in members:
        if member == sender_info["user_id"]:
            continue
        peer = get_peer(member)
        if peer:
            send_unicast(message, (peer["ip"], peer["port"]))
        else:
            print_error(f"Could not find peer {member} to send group message")

    print_success(f"Message sent to group {group_id}")
    return True

def get_user_groups(user_id: str) -> List[Dict]:
    """Return all groups that the user belongs to"""
    return [
        {"id": gid, "name": info["name"], "members": len(info["members"])}
        for gid, info in _groups.items()
        if user_id in info["members"]
    ]

def get_group_members(group_id: str) -> Set[str]:
    """Return all members of a specific group"""
    if group_id not in _groups:
        return set()
    return _groups[group_id]["members"]

def handle_group_create(content: Dict, addr: tuple, my_info: Dict) -> None:
    """Handle incoming GROUP_CREATE message"""
    group_id = content["GROUP_ID"]
    group_name = content["GROUP_NAME"]
    members = content["MEMBERS"].split(",")
    creator = content["FROM"]

    # Add to local group registry
    _groups[group_id] = {
        "name": group_name,
        "creator": creator,
        "members": set(members),
        "last_updated": time.time()
    }

    print_info(f"\nYou've been added to group '{group_name}' (ID: {group_id}) by {creator}")
    print_info(f"Members: {', '.join(members)}\n")

    # Send ACK if message has MESSAGE_ID
    if "MESSAGE_ID" in content:
        send_ack(content["MESSAGE_ID"], creator)

def handle_group_update(content: Dict, addr: tuple, my_info: Dict) -> None:
    """Handle incoming GROUP_UPDATE message"""
    group_id = content["GROUP_ID"]
    if group_id not in _groups:
        return

    # Get added and removed members
    added = content.get("ADD", "").split(",") if content.get("ADD") else []
    removed = content.get("REMOVE", "").split(",") if content.get("REMOVE") else []

    # Update local membership
    current_members = _groups[group_id]["members"]
    updated_members = current_members.union(added) - set(removed)
    _groups[group_id]["members"] = updated_members
    _groups[group_id]["last_updated"] = time.time()

    print_info(f"\nGroup '{_groups[group_id]['name']}' membership updated:")
    if added:
        print_info(f"Added: {', '.join(added)}")
    if removed:
        print_info(f"Removed: {', '.join(removed)}")
    print()

    # Send ACK if message has MESSAGE_ID
    if "MESSAGE_ID" in content:
        send_ack(content["MESSAGE_ID"], content["FROM"])

def handle_group_message(content: Dict, addr: tuple, my_info: Dict) -> None:
    """Handle incoming GROUP_MESSAGE"""
    group_id = content["GROUP_ID"]
    if group_id not in _groups or content["FROM"] not in _groups[group_id]["members"]:
        return

    sender = content["FROM"]
    group_name = _groups[group_id]["name"]
    message = content["CONTENT"]

    print(f"\n[Group {group_name} from {sender}]: {message}\n")

    # Send ACK if message has MESSAGE_ID
    if "MESSAGE_ID" in content:
        send_ack(content["MESSAGE_ID"], sender)