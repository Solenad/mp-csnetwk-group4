from colorama import init, Fore
from rich import print as rprint
from config import verbose_mode

init(autoreset=True)


def print_success(msg):
    print(Fore.GREEN + msg)


def print_error(msg):
    print(Fore.RED + "Error: " + msg)


def print_info(msg):
    print(Fore.CYAN + msg)


def print_prompt():
    rprint("[yellow]>> [/yellow]", end="", flush=True)


def print_verbose(message):
    if verbose_mode:
        print(f"[VERBOSE] {message}")
