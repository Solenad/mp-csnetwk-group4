from colorama import init, Fore
from config import verbose_mode

init(autoreset=True)


def print_success(msg):
    print(Fore.GREEN + msg)


def print_error(msg):
    print(Fore.RED + "Error: " + msg)


def print_info(msg):
    print(Fore.CYAN + msg)


def print_prompt():
    print(Fore.YELLOW + ">>", end="")


def print_verbose(message):
    if verbose_mode:
        print(f"[VERBOSE] {message}")
