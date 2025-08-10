# main.py
from network.socket_manager import start_listening
from network.message_sender import send_ack
from network.broadcast import send_ping, send_profile, my_info, get_local_ip
from ui.cli import start_cli
from network.peer_registry import add_peer
from network.tictactoe import handle_invite, handle_move, handle_result
from ui.utils import print_verbose, print_prompt
import threading
import socket
import config
import time

PROFILE_RESEND_INTERVAL = 10


def handle_message(message: str, addr: tuple) -> None:
    try:
        # Parse message into key-value pairs
        content = {}
        for line in message.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                content[key.strip()] = value.strip()

        msg_type = content.get("TYPE")
        user_id = content.get("USER_ID") or content.get("FROM")

        if not user_id:
            return

        if user_id == my_info["user_id"]:
            return

        if addr[0] == get_local_ip():
            return

        # Add/update peer info
        display_name = content.get("DISPLAY_NAME", user_id.split("@")[0])
        add_peer(
            user_id=user_id,
            ip=addr[0],
            port=content.get("PORT", addr[1]),
            display_name=display_name,
        )

        # --- POST ---
        if msg_type == "POST":
            if user_id in config.followed_users:
                if config.verbose_mode:
                    print_verbose(
                        f"\nTYPE: POST\n"
                        f"USER_ID: {user_id}\n"
                        f"CONTENT: {content.get('CONTENT', '')}\n"
                        f"TTL: {content.get('TTL', '')}\n"
                        f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                        f"TOKEN: {content.get('TOKEN', '')}\n"
                        f"TIMESTAMP: {content.get(
                            'TIMESTAMP', time.time())}\n\n"
                    )
                else:
                    print(f"\n{display_name}: {content.get('CONTENT', '')}\n")
                print_prompt()

        # --- DM ---
        elif msg_type == "DM":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: DM\n"
                    f"FROM: {user_id}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"CONTENT: {content.get('CONTENT', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            else:
                print(
                    f"\n[DM from {display_name}]: {
                        content.get('CONTENT', '')}\n"
                )
            print_prompt()
            if content.get("MESSAGE_ID"):
                send_ack(content["MESSAGE_ID"], user_id)

        # --- PROFILE ---
        elif msg_type == "PROFILE":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: PROFILE\n"
                    f"USER_ID: {user_id}\n"
                    f"DISPLAY_NAME: {display_name}\n"
                    f"STATUS: {content.get('STATUS', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n\n"
                )
            else:
                print(
                    f"\n{display_name}: {
                        content.get('STATUS', '')}\n"
                )
            print_prompt()

        # --- PING ---
        elif msg_type == "PING" and addr[0] != get_local_ip():
            if config.verbose_mode:
                print_verbose(f"\nTYPE: PING\nUSER_ID: {user_id}\n\n")
            send_profile(my_info)

        # --- FOLLOW ---
        elif msg_type == "FOLLOW":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: FOLLOW\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"FROM: {user_id}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            else:
                print(f"\n{display_name} has followed you\n")
            print_prompt()

        # --- UNFOLLOW ---
        elif msg_type == "UNFOLLOW":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: UNFOLLOW\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"FROM: {user_id}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            else:
                print(f"\n{display_name} has unfollowed you\n")
            print_prompt()

        # --- ACK ---
        elif msg_type == "ACK":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: ACK\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"STATUS: {content.get('STATUS', '')}\n\n"
                )

        # --- TicTacToe ---
        elif msg_type == "TICTACTOE_INVITE":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: TICTACTOE_INVITE\n"
                    f"FROM: {content.get('FROM', '')}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"GAMEID: {content.get('GAMEID', '')}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"SYMBOL: {content.get('SYMBOL', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            handle_invite(content, addr, my_info)
            print_prompt()

        elif msg_type == "TICTACTOE_MOVE":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: TICTACTOE_MOVE\n"
                    f"FROM: {content.get('FROM', '')}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"GAMEID: {content.get('GAMEID', '')}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"POSITION: {content.get('POSITION', '')}\n"
                    f"SYMBOL: {content.get('SYMBOL', '')}\n"
                    f"TURN: {content.get('TURN', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            handle_move(content, addr, my_info)
            print_prompt()

        elif msg_type == "TICTACTOE_RESULT":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: TICTACTOE_RESULT\n"
                    f"FROM: {content.get('FROM', '')}\n"
                    f"TO: {content.get('TO', '')}\n"
                    f"GAMEID: {content.get('GAMEID', '')}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"RESULT: {content.get('RESULT', '')}\n"
                    f"SYMBOL: {content.get('SYMBOL', '')}\n"
                    f"WINNING_LINE: {content.get('WINNING_LINE', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', '')}\n\n"
                )
            handle_result(content, addr, my_info)
            print_prompt()

        else:
            if config.verbose_mode:
                print_verbose(
                    f"[{time.time()}] Unknown message type: {
                        msg_type}\n{content}"
                )

    except Exception as e:
        if config.verbose_mode:
            print_verbose(f"[{time.time()}] Error processing message: {e}")


if __name__ == "__main__":
    sock, port = start_listening(handle_message)
    if not sock:
        exit(1)

    my_info.update(
        {
            "port": port,
            "user_id": f"{my_info['username']}@{socket.gethostbyname(socket.gethostname())}:{port}",
        }
    )

    def ping_loop():
        while True:
            send_ping(my_info)
            time.sleep(300)

    threading.Thread(target=ping_loop, daemon=True).start()
    start_cli(my_info)
