# ui/cli.py
from rich.console import Console
from rich.table import Table
from network import my_info
from network.message_sender import send_post, send_dm, send_follow, send_unfollow
from network.broadcast import send_profile
from network.peer_registry import get_peer_list
from ui.utils import print_info, print_error, print_prompt, print_success, print_verbose
import config
import time

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
    """Toggle global verbose mode in config"""
    if not args:
        # Toggle instead of just showing
        config.verbose_mode = not config.verbose_mode
        print_success(
            f"Verbose mode {
                      'enabled' if config.verbose_mode else 'disabled'}"
        )
    elif args[0] in ["on", "off"]:
        config.verbose_mode = args[0] == "on"
        print_success(
            f"Verbose mode {
                      'enabled' if config.verbose_mode else 'disabled'}"
        )
    else:
        print_error("Usage: verbose [on|off]")
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


command_registry = {
    "exit": cmd_exit,
    "whoami": cmd_whoami,
    "peers": cmd_peers,
    "send": cmd_send,
    "groups": cmd_groups,
    "help": cmd_help,
    "verbose": cmd_verbose,
}
