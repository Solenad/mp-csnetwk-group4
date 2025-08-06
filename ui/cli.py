from rich.console import Console
from rich.table import Table
from network.message_sender import send_post, send_dm, send_follow
from network.broadcast import my_info, send_profile
from ui.utils import print_info, print_error, print_prompt, print_success
from config import verbose_mode
from network.peer_registry import get_peer_list
import time

console = Console()


def cmd_whoami(_args):
    print_info(f"I am '{my_info['username']}' on '{my_info['hostname']}'")
    return True


def cmd_exit(_args):
    print_success("Exiting...")
    return False


def cmd_peers(_args):
    peers = get_peer_list()
    if not peers:
        print_info("No peers known yet.")
        return True

    table = Table(title="Known Peers")
    table.add_column("User ID", style="cyan")
    table.add_column("Display Name", style="magenta")
    table.add_column("IP:Port", style="green")
    table.add_column("Last Seen", style="yellow")

    for peer in peers:
        last_seen = time.strftime("%H:%M:%S", time.localtime(peer["last_seen"]))
        table.add_row(
            peer.get("user_id", "?"),
            peer.get("display_name", "?"),
            f"{peer['ip']}:{peer['port']}",
            last_seen,
        )
    console.print(table)
    return True


def cmd_send(args):
    if not args:
        print_error("Usage: send <post|dm|follow|hello> [arguments]")
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
            send_dm(recipient, message, my_info)
            print_success(f"DM sent to {recipient}")
    elif subcommand == "follow":
        if not subargs:
            print_error("Usage: send follow <username>")
        else:
            send_follow(subargs[0], my_info)
            print_success(f"Follow request sent to {subargs[0]}")
    elif subcommand == "hello":
        if subargs:
            print_error("Usage: send hello (no arguments needed)")
        else:
            send_profile(my_info)
            print_success("Profile broadcast sent to network")
    else:
        print_error("Unknown subcommand for send. Available: post, dm, follow, hello")
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
            f"Verbose mode is currently {
                'on' if verbose_mode else 'off'}"
        )
    else:
        verbose_mode = args[0] == "on"
        print_success(
            f"Verbose mode {
                'enabled' if verbose_mode else 'disabled'}"
        )
    return True


def print_verbose(msg):
    if verbose_mode:
        print_info(f"[VERBOSE] {msg}")


def start_cli(info):
    global my_info
    my_info = info
    print_info("CLI started. Type 'help' for commands.")

    def handle_command(command_line):
        parts = command_line.strip().split()
        if not parts:
            return True
        command = parts[0]
        args = parts[1:]
        handler = command_registry.get(command)
        if handler:
            return handler(args)
        else:
            print_error(f"Unknown command: {command}")
            return True

    while True:
        print_prompt()
        try:
            command_line = input()
        except KeyboardInterrupt:
            print_error("\nInterrupted.")
            break
        if not handle_command(command_line):
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
