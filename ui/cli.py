# ui/cli.py
from rich.console import Console
from rich.table import Table
from network import my_info
from network.message_sender import (
    send_post,
    send_dm,
    send_follow,
    send_unfollow,
    send_like,
    send_file_offer,
)
from network.broadcast import send_profile
from network.peer_registry import get_peer_list, get_peer
from network.tictactoe import send_invite, send_move
from ui.utils import print_info, print_error, print_prompt, print_success, print_verbose
import config
import time
from network.token_utils import generate_token
import base64
import os
from network.broadcast import get_mime_type

console = Console()


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
            if username in config.followed_users:
                print_error(f"You are already following {username}")
            elif send_follow(username, my_info):
                config.followed_users.add(username)
                print_success(f"Follow request sent to {username}")

    elif subcommand == "unfollow":
        if not subargs:
            print_error("Usage: send unfollow <username>")
        else:
            username = subargs[0]
            if username not in config.followed_users:
                print_error(f"You are not following {username}")
            elif send_unfollow(username, my_info):
                config.followed_users.remove(username)
                print_success(f"Unfollow request sent to {username}")

    elif subcommand == "hello":
        if subargs:
            print_error("Usage: send hello (no arguments needed)")
        else:
            if config.verbose_mode:
                from network.broadcast import get_subnet_broadcast

                print(
                    f"[hello] Sending PROFILE broadcast to {
                        get_subnet_broadcast()}:50999"
                )
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
        "exit                              - Exit the application",
        "whoami                            - Show your user ID, display name, and host",
        "peers                             - List known peers on the network",
        "send post <message>               - Broadcast a public post",
        "send dm <username> <message>      - Send a direct message",
        "send follow <username>            - Send a follow request",
        "send unfollow <username>          - Unfollow a user",
        "send hello                        - Broadcast your profile to the network",
        "groups                            - Group management (not implemented yet)",
        "ttt invite <username> <X|O>       - Invite a player to TicTacToe",
        "ttt move <game_id> <pos>          - Make a TicTacToe move",
        "verbose [on|off]                  - Toggle or set verbose mode (RFC-format output)",
        "test parse <message>              - Test message parsing",
        "test unicast <user> <msg>         - Test direct messaging",
        "test broadcast                    - Test broadcast functionality",
        "test token                        - Test token validation scenarios",
        "test all                          - Run all protocol compliance tests",
        "like <timestamp> [unlike]         - Like/unlike a post",
        "set_avatar <path>                 - Set your profile picture",
        "file send <user> <path> [desc]    - Send a file to user",
        "file accept <fileid>              - Accept incoming file transfer",
        "file reject <fileid>              - Reject incoming file transfer",
    ]
    for cmd in commands:
        if cmd:
            print(f" - {cmd}")
        else:
            print()
    return True


def cmd_verbose(args):
    """Toggle global verbose mode in config"""
    if not args:
        config.verbose_mode = not config.verbose_mode
        print_success(
            f"Verbose mode {'enabled' if config.verbose_mode else 'disabled'}"
        )
    elif args[0] in ["on", "off"]:
        config.verbose_mode = args[0] == "on"
        print_success(
            f"Verbose mode {'enabled' if config.verbose_mode else 'disabled'}"
        )
    else:
        print_error("Usage: verbose [on|off]")
    return True


def cmd_ttt(args):
    if not args:
        print_error("Usage: ttt <invite|move> ...")
        return True

    if args[0] == "invite" and len(args) == 3:
        _, username, symbol = args
        send_invite(username, symbol.upper(), my_info)
    elif args[0] == "move" and len(args) == 3:
        _, game_id, pos = args
        send_move(game_id, int(pos), my_info)
    else:
        print_error("Usage: ttt invite <username> <X|O> | ttt move <game_id> <pos>")
    return True


def cmd_test_token(_args):
    """Test token validation scenarios"""
    print_info("Token validation tests can only be run from the main application")
    return True


def cmd_test(args):
    """Protocol compliance testing"""
    if not args:
        print_error("Usage: test <parse|unicast|broadcast|token|all> [args]")
        return True

    subcmd = args[0]

    if subcmd == "parse":
        if len(args) < 2:
            print_error("Usage: test parse <message>")
            return True
        # Join rest of args as the message to parse
        message = " ".join(args[1:])
        if not message.endswith("\n\n"):
            print_error("Message missing terminator (\\n\\n)")
            return False
        lines = message.strip().splitlines()
        for line in lines:
            if ": " not in line:
                print_error(f"Invalid line: {line}")
                return False
        print_success("Message parse test passed")
        return True

    elif subcmd == "unicast":
        if len(args) < 3:
            print_error("Usage: test unicast <user_id> <message>")
            return True

        recipient = args[1]
        message = " ".join(args[2:])

        print_info(
            f"=== TEST UNICAST ===\nTo: {
                recipient}\nMessage: {message}"
        )

        if send_dm(recipient, message, my_info):
            print_success("DM sent successfully")
        else:
            print_error("Failed to send DM")

    elif subcmd == "broadcast":
        print_info("=== TEST BROADCAST ===")
        send_profile(my_info)
        print_success("Broadcast PROFILE message sent")

    elif subcmd == "token":
        user_id = my_info["user_id"]
        token = generate_token(user_id, "test")
        print_info(f"Generated token: {token}")
        # Add validation logic here if needed
        print_success("Token test completed")
        return True

    elif subcmd == "all":
        print_info("Running all protocol compliance tests...")
        # Run unicast test
        cmd_test(["unicast", "testuser@192.168.1.99:50999", "Test DM"])
        # Run parse test with valid message (properly split as one argument)
        cmd_test(["parse", "TYPE: POST\nCONTENT: Hello\n\n"])
        # Run broadcast test
        cmd_test(["broadcast"])
        # Run token test
        cmd_test(["token"])
        return True

    else:
        print_error(f"Unknown test command: {subcmd}")

    return True


def cmd_like(args):
    """Send a like to a post"""
    if len(args) < 1:
        print_error("Usage: like <post_timestamp> [unlike]")
        return True

    try:
        post_timestamp = int(args[0])
        action = "UNLIKE" if len(args) > 1 and args[1].lower() == "unlike" else "LIKE"

        if send_like(post_timestamp, my_info, action):
            verb = "unliked" if action == "UNLIKE" else "liked"
            print_success(
                f"Successfully {verb} post from {
                    time.ctime(post_timestamp)}"
            )
    except ValueError:
        print_error("Invalid timestamp - must be integer")
    return True


def cmd_set_avatar(args):
    """Set your profile picture"""
    if not args:
        print_error("Usage: set_avatar <image_path>")
        return True

    avatar_path = args[0]
    if not os.path.exists(avatar_path):
        print_error(f"File not found: {avatar_path}")
        return True

    try:
        with open(avatar_path, "rb") as f:
            my_info["avatar_data"] = base64.b64encode(f.read()).decode("utf-8")
            my_info["avatar_type"] = get_mime_type(avatar_path)
        print_success(
            f"Avatar set from {
                avatar_path}. Send 'hello' to update your profile."
        )
    except Exception as e:
        print_error(f"Failed to load avatar: {e}")
    return True


def cmd_show_avatar(args):
    """Display a peer's avatar if available"""
    if not args:
        print_error("Usage: show_avatar <username>")
        return True

    peer = get_peer(args[0])
    if not peer:
        print_error("Peer not found")
        return True

    if not peer.get("avatar_data"):
        print_error("Peer has no avatar")
        return True

    try:
        # Simple terminal display (could be enhanced with actual image display)
        print(f"\nAvatar for {peer['display_name']}:")
        print(f"Type: {peer['avatar_type']}")
        print(f"Size: {len(peer['avatar_data'])} bytes (base64)\n")
    except Exception as e:
        print_error(f"Failed to display avatar: {e}")
    return True


def cmd_file(args):
    """Handle file transfer commands"""
    if len(args) < 2:
        print_error("Usage: file send <recipient> <filepath> [description]")
        print_error("       file accept <fileid>")
        print_error("       file reject <fileid>")
        return True

    subcmd = args[0]

    if subcmd == "send":
        if len(args) < 3:
            print_error("Usage: file send <recipient> <filepath> [description]")
            return True

        recipient = args[1]
        filepath = args[2]
        description = " ".join(args[3:]) if len(args) > 3 else "No description"

        if send_file_offer(recipient, filepath, description, my_info):
            print_success(f"File offer sent for {filepath}")
        else:
            print_error("Failed to send file offer")

    elif subcmd == "accept":
        fileid = args[1]
        if fileid in config.incoming_files:
            print_success(f"Accepting file {fileid}")
            # The actual transfer happens automatically when chunks arrive
        else:
            print_error(f"No pending file with ID {fileid}")

    elif subcmd == "reject":
        fileid = args[1]
        if fileid in config.incoming_files:
            print_success(f"Rejected file {fileid}")
            del config.incoming_files[fileid]
        else:
            print_error(f"No pending file with ID {fileid}")

    else:
        print_error(f"Unknown file subcommand: {subcmd}")

    return True


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


def cmd_accept_file(args):
    """Handle 'y' command to accept file transfer"""
    if not config.pending_file_offer:
        print_error("No pending file offer to accept")
        return True

    fileid = config.pending_file_offer["fileid"]
    print_success(f"Accepting file {fileid}")
    # The transfer will proceed automatically as chunks arrive
    config.pending_file_offer = None
    return True


def cmd_reject_file(args):
    """Handle 'n' command to reject file transfer"""
    if not config.pending_file_offer:
        print_error("No pending file offer to reject")
        return True

    fileid = config.pending_file_offer["fileid"]
    print_success(f"Rejected file {fileid}")
    if fileid in config.incoming_files:
        del config.incoming_files[fileid]
    config.pending_file_offer = None
    return True


command_registry = {
    "exit": cmd_exit,
    "whoami": cmd_whoami,
    "peers": cmd_peers,
    "send": cmd_send,
    "groups": cmd_groups,
    "help": cmd_help,
    "verbose": cmd_verbose,
    "ttt": cmd_ttt,
    "test": cmd_test,
    "like": cmd_like,
    "set_avatar": cmd_set_avatar,
    "file": cmd_file,
    "y": cmd_accept_file,
    "n": cmd_reject_file,
}
