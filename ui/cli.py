from colorama import init, Fore, style
from rich.console import Console
from rich.table import Table

colorama_init(autoreset=True)
console = Console()

known_peers = {}


def print_success(msg):
    print(Fore.GREEN + msg)


def print_error(msg):
    print(Fore.RED + "Error: " + msg)


def print_info(msg):
    print(Fore.CYAN + msg)


def print_prompt():
    print(Fore.YELLOW + ">>", end="")


def cmd_exit(_args):
    print_success("Exiting...")
    return False


def cmd_whoami(_args):
    print_info(f"Username: {my_info['username']}")


def cmd_peers(_args):
    if not known_peers:
        print_info("No peers known yet.")
        return True

    table = Table(title="Known Peers")
    table.add_column("Username", style="cyan")
    table.add_column("Hostname", style="magenta")
    table.add_column("Address", style="green")

    for (ip, port), peer in known_peers.items():
        table.add_row(
            peer.get("username", "?"), peer.get("hostname", "?"), f"{ip}:{port}"
        )
    console.print(table)
    return True


def cmd_send(args):
    print_info("Send not implemented yet.")
    return True


def cmd_groups(args):
    print_info("Groups not implemented yet.")
    return True


command_registry = {
    "exit": cmd_exit,
    "whoami": cmd_whoami,
    "peers": cmd_peers,
    "send": cmd_send,
    "groups": cmd_groups,
}


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
        print_error(f"Unknown command: '{command}'")
        return True


def update_peer(addr, username, hostname):
    known_peers[addr] = {"username": username, "hostname": hostname}


def start_cli():
    print_info("CLI started. Type 'help' for commands.")

    while True:
        print_prompt()
        try:
            command_line = input()
        except KeyboardInterrupt:
            print_error("\nInterrupted.")
            break

        if not handle_command(command_line):
            break
