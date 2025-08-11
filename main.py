# main.py
from network.socket_manager import start_listening
from network.message_sender import send_ack, send_file_received
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
from network.token_utils import (
    validate_token,
    verify_token_ip,
    revoke_token,
    revoked_tokens,
)
import threading
import config
import time
import base64
from ui.image_display import display_image
from network.group_manager import (
    handle_group_create,
    handle_group_update,
    handle_group_message,
)

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
            "REVOKE": "chat",
        }
        for line in message.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                content[key.strip()] = value.strip()

        msg_type = content.get("TYPE")
        user_id = content.get("USER_ID") or content.get("FROM")
        token = content.get("TOKEN", "")

        if not user_id:
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
            # Store avatar if present
            avatar_data = content.get("AVATAR_DATA")
            avatar_type = content.get("AVATAR_TYPE")

            # Update peer info with avatar
            add_peer(
                user_id=user_id,
                ip=addr[0],
                port=content.get("PORT", addr[1]),
                display_name=display_name,
                avatar_data=avatar_data,
                avatar_type=avatar_type,
            )
            if config.verbose_mode:
                avatar_info = ""
                if avatar_data:
                    avatar_info = (
                        f"AVATAR_TYPE: {avatar_type}\n"
                        f"AVATAR_SIZE: {len(avatar_data)} bytes\n"
                    )
                print_verbose(
                    f"\nTYPE: PROFILE\n"
                    f"USER_ID: {user_id}\n"
                    f"DISPLAY_NAME: {display_name}\n"
                    f"STATUS: {content.get('STATUS', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', time.time())}\n"
                    f"{avatar_info}\n"
                )
            else:

                status_msg = f"{display_name}: {content.get('STATUS', '')}"

                if avatar_data:
                    # Pass display_name here
                    if not display_image(avatar_data, display_name):
                        status_msg += " [🖼️]"
                print(f"\n{status_msg}\n")
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

        elif msg_type == "GROUP_CREATE":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: GROUP_CREATE\n"
                    f"FROM: {content.get('FROM', '')}\n"
                    f"GROUP_ID: {content.get('GROUP_ID', '')}\n"
                    f"GROUP_NAME: {content.get('GROUP_NAME', '')}\n"
                    f"MEMBERS: {content.get('MEMBERS', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', '')}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            handle_group_create(content, addr, my_info)

        elif msg_type == "GROUP_UPDATE":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: GROUP_UPDATE\n"
                    f"FROM: {content.get('FROM', '')}\n"
                    f"GROUP_ID: {content.get('GROUP_ID', '')}\n"
                    f"ADD: {content.get('ADD', '')}\n"
                    f"REMOVE: {content.get('REMOVE', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', '')}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            handle_group_update(content, addr, my_info)

        elif msg_type == "GROUP_MESSAGE":
            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: GROUP_MESSAGE\n"
                    f"FROM: {content.get('FROM', '')}\n"
                    f"GROUP_ID: {content.get('GROUP_ID', '')}\n"
                    f"CONTENT: {content.get('CONTENT', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', '')}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            handle_group_message(content, addr, my_info)
        elif msg_type == "LIKE":
            post_timestamp = content.get("POST_TIMESTAMP")
            action = content.get("ACTION", "LIKE").upper()
            from_user = content.get("FROM")

            if not post_timestamp or not from_user:
                print_error("Invalid LIKE: missing fields")
                return

            # Track other users' likes (optional)
            post_key = (from_user, post_timestamp)
            if action == "LIKE":
                config.liked_posts.add(post_key)
            else:
                config.liked_posts.discard(post_key)

            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: LIKE\n"
                    f"FROM: {from_user}\n"
                    f"POST_TIMESTAMP: {post_timestamp}\n"
                    f"ACTION: {action}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', '')}\n"
                    f"MESSAGE_ID: {content.get('MESSAGE_ID', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            else:
                if action == "LIKE":
                    print(
                        f"\n{display_name} liked your post from {
                            time.ctime(int(post_timestamp))}\n"
                    )
                else:
                    print(
                        f"\n{display_name} unliked your post from {
                            time.ctime(int(post_timestamp))}\n"
                    )
            print_prompt()

        # --- FILE_OFFER ---
        elif msg_type == "FILE_OFFER":
            if any(
                field not in content
                for field in ["FROM", "FILENAME", "FILESIZE", "FILEID"]
            ):
                print_error("Invalid FILE_OFFER: missing required fields")
                return

            fileid = content["FILEID"]

            config.pending_file_offer = {
                "fileid": fileid,
                "from": user_id,
                "filename": content["FILENAME"],
            }

            fileid = content["FILEID"]
            config.incoming_files[fileid] = {
                "from": user_id,
                "filename": content["FILENAME"],
                "filesize": int(content["FILESIZE"]),
                "filetype": content.get("FILETYPE", "application/octet-stream"),
                "description": content.get("DESCRIPTION", ""),
                "chunks": {},
                "received_chunks": 0,
            }

            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: FILE_OFFER\n"
                    f"FROM: {user_id}\n"
                    f"FILENAME: {content['FILENAME']}\n"
                    f"FILESIZE: {content['FILESIZE']}\n"
                    f"FILEID: {fileid}\n"
                    f"DESCRIPTION: {content.get('DESCRIPTION', '')}\n"
                    f"TIMESTAMP: {content.get('TIMESTAMP', '')}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )
            else:
                print(
                    f"\n{display_name} is sending you a file '{
                        content['FILENAME']}'. Do you accept? (Y/N)\n"
                )
            print_prompt()

        # --- FILE_CHUNK ---
        elif msg_type == "FILE_CHUNK":
            required_fields = ["FROM", "FILEID", "CHUNK_INDEX", "TOTAL_CHUNKS", "DATA"]
            if any(field not in content for field in required_fields):
                print_error("Invalid FILE_CHUNK: missing required fields")
                return

            fileid = content["FILEID"]
            if fileid not in config.incoming_files:
                if config.verbose_mode:
                    print_verbose(f"Ignoring FILE_CHUNK for unknown file ID {fileid}")
                return

            chunk_index = int(content["CHUNK_INDEX"])
            total_chunks = int(content["TOTAL_CHUNKS"])
            chunk_data = base64.b64decode(content["DATA"])

            # Store the chunk
            config.incoming_files[fileid]["chunks"][chunk_index] = chunk_data
            config.incoming_files[fileid]["received_chunks"] += 1

            if config.verbose_mode:
                print_verbose(
                    f"\nTYPE: FILE_CHUNK\n"
                    f"FROM: {user_id}\n"
                    f"FILEID: {fileid}\n"
                    f"CHUNK_INDEX: {chunk_index}\n"
                    f"TOTAL_CHUNKS: {total_chunks}\n"
                    f"CHUNK_SIZE: {len(chunk_data)}\n"
                    f"TOKEN: {content.get('TOKEN', '')}\n\n"
                )

            # Check if all chunks received
            if config.incoming_files[fileid]["received_chunks"] >= total_chunks:
                file_info = config.incoming_files[fileid]
                try:
                    # Reassemble file
                    with open(file_info["filename"], "wb") as f:
                        for i in range(total_chunks):
                            f.write(file_info["chunks"][i])

                    if not config.verbose_mode:
                        print(
                            f"\nFile transfer of {
                                file_info['filename']} is complete\n"
                        )

                    # Send acknowledgment
                    send_file_received(fileid, user_id, my_info)

                except Exception as e:
                    print_error(f"Failed to save file: {e}")
                    send_file_received(fileid, user_id, my_info, "ERROR")

                # Clean up
                del config.incoming_files[fileid]

        # --- FILE_RECEIVED ---
        elif msg_type == "FILE_RECEIVED":
            if "FILEID" not in content or "STATUS" not in content:
                print_error("Invalid FILE_RECEIVED: missing required fields")
                return

            fileid = content["FILEID"]
            if fileid in config.active_file_transfers:
                status = content["STATUS"]
                if status == "COMPLETE":
                    if config.verbose_mode:
                        print_verbose(
                            f"\nFile {fileid} successfully received by {
                                user_id}\n"
                        )
                    del config.active_file_transfers[fileid]
                else:
                    print_error(
                        f"\nFile transfer {
                            fileid} failed with status {status}\n"
                    )
            else:
                if config.verbose_mode:
                    print_verbose(
                        f"\nReceived FILE_RECEIVED for unknown file ID {
                            fileid}\n"
                    )

        else:
            print_error(f"Unknown message type: {msg_type}")
            if config.verbose_mode:
                print_verbose(f"Full message:\n{message}")
    except Exception as e:
        print_error(f"error processing message: {e}")
        if config.verbose_mode:
            print_verbose(f"full message:\n{message}")


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
