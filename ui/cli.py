from rich.console import Console
from rich.table import Table
from network import my_info
from network.message_sender import send_post, send_dm, send_follow, send_unfollow
from network.broadcast import send_profile
from network.peer_registry import get_peer_list
from ui.utils import print_info, print_error, print_prompt, print_success
from config import verbose_mode, followed_users
import time

console = Console()

import base64
import os
import tempfile
import webbrowser
from network.peer_registry import get_peer_list


def cmd_showpfp(args):
    if not args:
        print_error("Usage: showpfp <username|me>")
        return True

    # Get avatar from self or peers
    if args[0].lower() == "me":
        avatar_b64 = my_info.get("avatar_b64")
    else:
        avatar_b64 = None
        peers = get_peer_list()
        for peer in peers:
            if peer["display_name"].lower() == args[0].lower() or peer["user_id"] == args[0]:
                avatar_b64 = peer.get("avatar_b64")
                break

    if not avatar_b64:
        print_error("No avatar found for this user.")
        return True

    # Decode and display image
    try:
        img_data = base64.b64decode(avatar_b64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(img_data)
            tmp_path = tmp.name

        # Open image (cross-platform)
        if os.name == "nt":  # Windows
            os.startfile(tmp_path)
        elif os.name == "posix":
            subprocess.run(["xdg-open", tmp_path])
        else:
            print_success(f"Image saved at {tmp_path}")
    except Exception as e:
        print_error(f"Failed to display avatar: {e}")

    return True

def cmd_setpfp(args):
    if not args:
        print_error("Usage: setpfp <image_path>")
        return True

    img_path = args[0]
    if not os.path.isfile(img_path):
        print_error(f"File not found: {img_path}")
        return True

    with open(img_path, "rb") as f:
        avatar_b64 = base64.b64encode(f.read()).decode("utf-8")

    my_info["avatar_b64"] = avatar_b64
    print_success(f"Profile picture updated to {img_path}")

    # Broadcast to peers so they get your PFP

    return True


def cmd_whoami(_args):
    print_info(f"I am '{my_info['username']}' on '{my_info['hostname']}'")
    return True


def cmd_exit(_args):
    print_success("Exiting...")
    return False


def cmd_peers(_args):
    peers = get_peer_list(exclude_user_id=my_info.get("user_id"))
    if not peers:
        print_info("No peers known yet.")
        return True

    table = Table(title="Known Peers")
    table.add_column("User ID", style="cyan")
    table.add_column("Display Name", style="magenta")
    table.add_column("Address", style="green")
    table.add_column("Last Seen", style="yellow")

    for peer in peers:
        last_seen = time.strftime("%H:%M:%S", time.localtime(peer["last_seen"]))
        table.add_row(
            peer["user_id"],
            peer["display_name"],
            f"{peer['ip']}:{peer['port']}",
            last_seen,
        )
    console.print(table)
    return True


def cmd_send(args):
    if not args:
        print_error("Usage: send <post|dm|follow|unfollow|hello> [arguments]")
        return True

    subcommand = args[0]
    subargs = args[1:]

    if subcommand == "post":
        if not subargs:
            print_error("Usage: send post <message>")
        else:
            message = " ".join(subargs)
            send_post(message, my_info)
            print_success("Post sent successfully")

    elif subcommand == "dm":
        if len(subargs) < 2:
            print_error("Usage: send dm <username> <message>")
        else:
            recipient = subargs[0]
            message = " ".join(subargs[1:])
            if send_dm(recipient, message, my_info):
                print_success(f"DM sent to {recipient}")

    elif subcommand == "follow":
        if not subargs:
            print_error("Usage: send follow <username>")
        else:
            username = subargs[0]
            if username in followed_users:
                print_error(f"You are already following {username}")
            elif send_follow(username, my_info):
                followed_users.add(username)
                print_success(f"Follow request sent to {username}")

    elif subcommand == "unfollow":
        if not subargs:
            print_error("Usage: send unfollow <username>")
        else:
            username = subargs[0]
            if username not in followed_users:
                print_error(f"You are not following {username}")
            elif send_unfollow(username, my_info):
                followed_users.remove(username)
                print_success(f"Unfollow request sent to {username}")

    elif subcommand == "hello":
        if subargs:
            print_error("Usage: send hello (no arguments needed)")
        else:
            send_profile(my_info)
            print_success("Profile broadcast sent to network")

    else:
        print_error(
            "Unknown subcommand for send. Available: post, dm, follow, unfollow, hello"
        )

    return True


def cmd_groups(args):
    print_info("Groups not implemented yet.")
    return True


def cmd_help(_args):
    print_info("Available commands:")
    commands = [
        "exit - Exit the application",
        "whoami - Show your user information",
        "peers - List known peers",
        "send <post|dm|follow|hello> [arguments] - Send messages",
        "groups - Group management (not implemented)",
        "help - Show this help message",
        "verbose <on|off> - Toggle verbose mode",
    ]
    for cmd in commands:
        print(f" - {cmd}")
    return True


def cmd_verbose(args):
    global verbose_mode
    if not args or args[0] not in ["on", "off"]:
        print_info(
            f"Verbose mode is currently {'on' if verbose_mode else 'off'}"
        )
    else:
        verbose_mode = args[0] == "on"
        print_success(
            f"Verbose mode {'enabled' if verbose_mode else 'disabled'}"
        )
    return True


def print_verbose(msg):
    if verbose_mode:
        print_info(f"[VERBOSE] {msg}")


def start_cli(info):
    global my_info
    my_info = info
    print_info("CLI started. Type 'help' for commands.")

    while True:
        print_prompt()
        try:
            command_line = input()
            if not command_line.strip():
                continue

            parts = command_line.split()
            handler = command_registry.get(parts[0])
            if not handler:
                print_error(f"Unknown command: {parts[0]}")
                continue

            if not handler(parts[1:]):
                break

        except KeyboardInterrupt:
            print_error("\nInterrupted.")
            break


command_registry = {
    "exit": cmd_exit,
    "whoami": cmd_whoami,
    "peers": cmd_peers,
    "send": cmd_send,
    "groups": cmd_groups,
    "help": cmd_help,
    "verbose": cmd_verbose,
    "setpfp": cmd_setpfp,
    "showpfp": cmd_showpfp,
}
