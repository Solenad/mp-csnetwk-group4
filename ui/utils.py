# ui/utils.py
from colorama import init, Fore
from rich import print as rprint
import config

init(autoreset=True)


def print_success(msg: str):
    print(Fore.GREEN + msg)


def print_error(msg: str):
    print(Fore.RED + "Error: " + msg)


def print_info(msg: str):
    print(Fore.CYAN + msg)


def print_prompt():
    rprint("[yellow]>> [/yellow]", end="", flush=True)


def print_verbose(message: str):
    if getattr(config, "verbose_mode", False):
        print(Fore.CYAN + str(message))
