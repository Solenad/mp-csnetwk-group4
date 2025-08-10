# main.py
from network.socket_manager import start_listening
from network.message_sender import send_ack
from network.broadcast import (
    send_ping,
    send_profile,
    my_info,
    get_local_ip,
    send_immediate_discovery,
)
from ui.cli import start_cli
from network.peer_registry import add_peer
from network.tictactoe import handle_invite, handle_move, handle_result
from ui.utils import print_verbose, print_prompt, print_error
from network.token_utils import validate_token, verify_token_ip, revoke_token
import threading
import config
import time

PROFILE_RESEND_INTERVAL = 10
initial_discovery = True


def validate_message(message: str) -> bool:
    """Validate basic message structure"""
    if not message.endswith("\n\n"):
        print_error("Invalid message: missing terminator (\\n\\n)")
        return False

    lines = message.splitlines()
    if len(lines) < 2:  # At least TYPE:... and terminator
        print_error("Invalid message: too short")
        return False

    if not any(line.startswith("TYPE:") for line in lines):
        print_error("Invalid message: missing TYPE field")
        return False

    return True


def handle_message(message: str, addr: tuple) -> None:
    try:
        if not validate_message(message):
            return

        # Parse message into key-value pairs
        content = {}
        token_validation_map = {
            "POST": "broadcast",
            "DM": "chat",
            "FOLLOW": "follow",
            "UNFOLLOW": "follow",
            "FILE_OFFER": "file",
            "FILE_CHUNK": "file",
            "TICTACTOE_INVITE": "game",
            "TICTACTOE_MOVE": "game",
            "TICTACTOE_RESULT": "game",
            "LIKE": "broadcast",
            "GROUP_CREATE": "group",
            "GROUP_UPDATE": "group",
            "GROUP_MESSAGE": "group",
            "REVOKE": "chat",  # REVOKE uses chat scope per RFC
        }
        for line in message.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                content[key.strip()] = value.strip()

        msg_type = content.get("TYPE")
        user_id = content.get("USER_ID") or content.get("FROM")
        token = content.get("TOKEN", "")

        if not user_id:
            print_error("Invalid message: missing USER_ID/FROM field")
            return

        if user_id == my_info["user_id"]:
            return

        # Handle REVOKE message first since it doesn't need token validation
        if msg_type == "REVOKE":
            revoke_token(token)
            if config.verbose_mode:
                print_verbose(f"\nTYPE: REVOKE\nTOKEN: {token}\n\n")
            return

        # Validate token for all other message types
        if msg_type in token_validation_map:
            expected_scope = token_validation_map[msg_type]
            is_valid = validate_token(token, expected_scope)

            if config.verbose_mode:
                validation_status = "VALID" if is_valid else "INVALID"
                reason = ""
                if not is_valid:
                    try:
                        parts = token.split("|")
                        if len(parts) != 3:
                            reason = "Malformed token format"
                        elif token in revoked_tokens:
                            reason = "Token revoked"
                        elif int(parts[1]) < time.time():
                            reason = "Token expired"
                        elif parts[2] != expected_scope:
                            reason = f"Scope mismatch (expected {
                                expected_scope})"
                    except (ValueError, IndexError):
                        reason = "Invalid token structure"

                print_verbose(
                    f"TOKEN VALIDATION: {validation_status}\n"
                    f" - Token: {token}\n"
                    f" - Expected scope: {expected_scope}\n"
                    f" - Reason: {reason if reason else 'Valid token'}\n"
                )

            if not is_valid:
                print_error(f"Invalid token for {msg_type}")
                return

            # Verify token IP matches sender IP
            if not verify_token_ip(token, addr[0]):
                print_error("Token IP does not match sender IP")
                if config.verbose_mode:
                    try:
                        token_ip = token.split("|")[0].split("@")[1].split(":")[0]
                        print_verbose(
                            f"IP MISMATCH: Token claims {
                                token_ip} but came from {addr[0]}\n"
                        )
                    except (IndexError, AttributeError):
                        print_verbose("Invalid token format for IP verification\n")
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
            if "CONTENT" not in content:
                print_error("Invalid POST: missing CONTENT field")
                return

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
            if "CONTENT" not in content:
                print_error("Invalid DM: missing CONTENT field")
                return

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
            if initial_discovery:
                return
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: PROFILE\n"
                    f"USER_ID: {user_id}\n"
                    f"DISPLAY_NAME: {display_name}\n"
                    f"STATUS: {content.get('STATUS', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n\n"
                )
            else:
                print(f"\n{display_name}: {content.get('STATUS', '')}\n")
            print_prompt()

        # --- PING ---
        elif msg_type == "PING":
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

        else:
            print_error(f"Unknown message type: {msg_type}")
            if config.verbose_mode:
                print_verbose(f"Full message:\n{message}")

    except Exception as e:
        print_error(f"Error processing message: {e}")
        if config.verbose_mode:
            print_verbose(f"Full message:\n{message}")


if __name__ == "__main__":
    sock, port = start_listening(handle_message)
    if not sock:
        exit(1)

    my_info.update(
        {
            "port": port,
            "user_id": f"{my_info['username']}@{get_local_ip()}:{port}",
        }
    )

    def limited_discovery():
        global initial_discovery
        start_time = time.time()
        while time.time() - start_time < 5:
            send_immediate_discovery(my_info, port=port)  # Pass port here
            time.sleep(1)
        initial_discovery = False

    threading.Thread(target=limited_discovery, daemon=True).start()

    def ping_loop():
        while True:
            send_ping(my_info, port=port)  # Pass port here too
            time.sleep(300)

    threading.Thread(target=ping_loop, daemon=True).start()
    start_cli(my_info)
