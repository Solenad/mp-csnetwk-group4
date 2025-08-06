from colorama import init, Fore

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
    print(f"[VERBOSE] {message}")