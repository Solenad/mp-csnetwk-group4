# tictactoe.py
import time
import config
import secrets
from ui.utils import print_info, print_error, print_success, print_prompt
from network.message_sender import send_unicast, send_ack
from network.peer_registry import get_peer

WINNING_COMBINATIONS = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
]

games = (
    {}
)  # GAMEID -> {board, players, turn, symbol_map, last_turn_received, last_activity}


def format_board(board):
    def symbol(pos):
        return board[pos] if board[pos] else str(pos)

    rows = [
        f"{symbol(0)} | {symbol(1)} | {symbol(2)}",
        f"{symbol(3)} | {symbol(4)} | {symbol(5)}",
        f"{symbol(6)} | {symbol(7)} | {symbol(8)}",
    ]
    return "\n---------\n".join(rows)


def check_winner(board):
    for a, b, c in WINNING_COMBINATIONS:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a], (a, b, c)
    if all(board):
        return "DRAW", None
    return None, None


def send_invite(recipient_id, symbol, sender_info):
    peer = get_peer(recipient_id)
    if not peer:
        print_error(f"Unknown recipient: {recipient_id}")
        print_info("Make sure the user is online and you've spelled their ID correctly")
        return False

    timestamp = int(time.time())
    game_id = f"g{secrets.randbelow(1000)}"  # Larger range for game IDs
    message_id = secrets.token_hex(4)
    token = f"{sender_info['user_id']}|{timestamp + 3600}|game"

    message = (
        "TYPE: TICTACTOE_INVITE\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {recipient_id}\n"
        f"GAMEID: {game_id}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"SYMBOL: {symbol}\n"
        f"TIMESTAMP: {timestamp}\n"
        f"TOKEN: {token}\n\n"
    )

    try:
        # Try direct send first without waiting for ACK for invites
        if send_unicast(message, (peer["ip"], int(peer["port"]))):
            games[game_id] = {
                "board": [None] * 9,
                "players": {
                    sender_info["user_id"]: symbol,
                    recipient_id: "O" if symbol == "X" else "X",
                },
                "turn": 1,
                "symbol_map": {
                    symbol: sender_info["user_id"],
                    "O" if symbol == "X" else "X": recipient_id,
                },
                "last_turn_received": set(),
                "last_activity": time.time(),
            }
            print_success(f"Invite sent to {recipient_id} for game {game_id}")
            return True
        else:
            print_error("Failed to send invite")
            return False
    except Exception as e:
        print_error(f"Error sending invite: {str(e)}")
        return False


def send_unicast_with_retry(
    message, recipient_addr, message_id, recipient_id, max_retries=3
):
    for attempt in range(max_retries):
        if send_unicast(message, recipient_addr):
            # Wait for ACK with timeout
            start_time = time.time()
            while time.time() - start_time < 2:  # 2 second timeout
                if message_id in config.received_acks:
                    config.received_acks.remove(message_id)
                    return True
                time.sleep(0.1)

            if attempt == max_retries - 1:
                print_error(
                    f"Failed to get ACK from {
                        recipient_id} after {max_retries} attempts"
                )
                return False
        else:
            if attempt == max_retries - 1:
                print_error(
                    f"Failed to send message to {
                        recipient_id} after {max_retries} attempts"
                )
                return False
        time.sleep(1)  # Wait before retrying
    return False


def send_move(game_id, position, sender_info, max_retries=3):
    if game_id not in games:
        print_error("Unknown game ID.")
        return False

    game = games[game_id]
    symbol = game["players"].get(sender_info["user_id"])
    if not symbol:
        print_error("You are not part of this game.")
        return False

    if game["board"][position] is not None:
        print_error("Position already taken.")
        return False

    game["board"][position] = symbol
    turn = game["turn"]
    game["turn"] += 1
    game["last_activity"] = time.time()

    peer_id = [p for p in game["players"] if p != sender_info["user_id"]][0]
    peer = get_peer(peer_id)
    if not peer:
        print_error(f"Unknown peer {peer_id}")
        return False

    message_id = secrets.token_hex(4)
    token = f"{sender_info['user_id']}|{int(time.time()) + 3600}|game"

    message = (
        "TYPE: TICTACTOE_MOVE\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {peer_id}\n"
        f"GAMEID: {game_id}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"POSITION: {position}\n"
        f"SYMBOL: {symbol}\n"
        f"TURN: {turn}\n"
        f"TOKEN: {token}\n\n"
    )

    if not send_unicast_with_retry(
        message, (peer["ip"], int(peer["port"])), message_id, peer_id, max_retries
    ):
        # Revert the move if we couldn't confirm it was received
        game["board"][position] = None
        game["turn"] -= 1
        return False

    print_info(f"You played at position {position} in game {game_id}")
    print(format_board(game["board"]))
    print_prompt()

    winner, line = check_winner(game["board"])
    if winner:
        send_result(game_id, winner, line, sender_info)

    return True


def send_result(game_id, result, winning_line, sender_info, max_retries=3):
    if game_id not in games:
        return

    game = games[game_id]
    game["last_activity"] = time.time()
    symbol = game["players"].get(sender_info["user_id"], "?")
    peer_id = [p for p in game["players"] if p != sender_info["user_id"]][0]
    peer = get_peer(peer_id)
    if not peer:
        return

    message_id = secrets.token_hex(4)
    token = f"{sender_info['user_id']}|{int(time.time()) + 3600}|game"

    winning_line_str = ",".join(map(str, winning_line)) if winning_line else ""

    message = (
        "TYPE: TICTACTOE_RESULT\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {peer_id}\n"
        f"GAMEID: {game_id}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"RESULT: {result}\n"
        f"SYMBOL: {symbol}\n"
        f"WINNING_LINE: {winning_line_str}\n"
        f"TIMESTAMP: {int(time.time())}\n\n"
    )

    if send_unicast_with_retry(
        message, (peer["ip"], int(peer["port"])), message_id, peer_id, max_retries
    ):
        print_success(f"Game {game_id} ended: {result}")
        print_prompt()
        # Clean up game after result is acknowledged
        if game_id in games:
            del games[game_id]


def handle_invite(content, addr, my_info):
    from_user = content["FROM"]
    game_id = content["GAMEID"]
    symbol = "O" if content["SYMBOL"] == "X" else "X"

    games[game_id] = {
        "board": [None] * 9,
        "players": {from_user: content["SYMBOL"], my_info["user_id"]: symbol},
        "turn": 1,
        "symbol_map": {content["SYMBOL"]: from_user, symbol: my_info["user_id"]},
        "last_turn_received": set(),
        "last_activity": time.time(),
    }

    print_success(f"\n{from_user} is inviting you to play Tic-Tac-Toe (Game {game_id})")
    print_info(f"You are playing as {symbol}")
    print(format_board(games[game_id]["board"]))
    print_prompt()

    # Always send ACK for invites
    if "MESSAGE_ID" in content:
        send_ack(content["MESSAGE_ID"], from_user)


def handle_move(content, addr, my_info):
    game_id = content["GAMEID"]
    turn = int(content["TURN"])
    position = int(content["POSITION"])
    symbol = content["SYMBOL"]
    from_user = content["FROM"]

    if game_id not in games:
        print_error(f"Move for unknown game {game_id}")
        print_prompt()
        # Send state request if we don't know about this game
        send_state_request(game_id, from_user, my_info)
        return

    game = games[game_id]
    game["last_activity"] = time.time()

    # Check if we're missing any previous moves
    expected_turn = game["turn"]
    if turn > expected_turn:
        print_info(
            f"Missing moves detected (expected turn {
                expected_turn}, got {turn})"
        )
        request_missing_moves(game_id, expected_turn, turn - 1, from_user, my_info)
        return
    elif turn < expected_turn:
        # Already processed this move
        if "MESSAGE_ID" in content:
            send_ack(content["MESSAGE_ID"], from_user)
        print_prompt()
        return

    game["last_turn_received"].add((game_id, turn))
    game["board"][position] = symbol
    game["turn"] = turn + 1

    print_info(f"Opponent played at position {position} in game {game_id}")
    print(format_board(game["board"]))
    print_prompt()

    winner, line = check_winner(game["board"])
    if winner:
        send_result(game_id, winner, line, my_info)

    if "MESSAGE_ID" in content:
        send_ack(content["MESSAGE_ID"], from_user)


def handle_result(content, addr, my_info):
    game_id = content["GAMEID"]
    result = content["RESULT"]
    symbol = content["SYMBOL"]
    line = content.get("WINNING_LINE", "")

    print_success(f"Game {game_id} Result: {result} ({symbol})")
    if line:
        print_info(f"Winning line: {line}")

    if game_id in games:
        print(format_board(games[game_id]["board"]))
        del games[game_id]  # Clean up completed game
    print_prompt()

    if "MESSAGE_ID" in content:
        send_ack(content["MESSAGE_ID"], content["FROM"])


# New functions for state synchronization


def send_state_request(game_id, requester_id, sender_info):
    peer = get_peer(requester_id)
    if not peer:
        return False

    message_id = secrets.token_hex(4)
    token = f"{sender_info['user_id']}|{int(time.time()) + 3600}|game"

    message = (
        "TYPE: TICTACTOE_STATE_REQUEST\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {requester_id}\n"
        f"GAMEID: {game_id}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TIMESTAMP: {int(time.time())}\n"
        f"TOKEN: {token}\n\n"
    )

    return send_unicast_with_retry(
        message, (peer["ip"], int(peer["port"])), message_id, requester_id
    )


def send_state_response(game_id, requester_id, sender_info):
    if game_id not in games:
        return False

    peer = get_peer(requester_id)
    if not peer:
        return False

    game = games[game_id]
    board_str = ",".join([s if s else "" for s in game["board"]])
    message_id = secrets.token_hex(4)
    token = f"{sender_info['user_id']}|{int(time.time()) + 3600}|game"

    message = (
        "TYPE: TICTACTOE_STATE_RESPONSE\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {requester_id}\n"
        f"GAMEID: {game_id}\n"
        f"BOARD: {board_str}\n"
        f"TURN: {game['turn']}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TIMESTAMP: {int(time.time())}\n"
        f"TOKEN: {token}\n\n"
    )

    return send_unicast_with_retry(
        message, (peer["ip"], int(peer["port"])), message_id, requester_id
    )


def request_missing_moves(game_id, from_turn, to_turn, requester_id, sender_info):
    peer = get_peer(requester_id)
    if not peer:
        return False

    message_id = secrets.token_hex(4)
    token = f"{sender_info['user_id']}|{int(time.time()) + 3600}|game"

    message = (
        "TYPE: TICTACTOE_MOVE_REQUEST\n"
        f"FROM: {sender_info['user_id']}\n"
        f"TO: {requester_id}\n"
        f"GAMEID: {game_id}\n"
        f"FROM_TURN: {from_turn}\n"
        f"TO_TURN: {to_turn}\n"
        f"MESSAGE_ID: {message_id}\n"
        f"TIMESTAMP: {int(time.time())}\n"
        f"TOKEN: {token}\n\n"
    )

    return send_unicast_with_retry(
        message, (peer["ip"], int(peer["port"])), message_id, requester_id
    )


def check_timeouts():
    current_time = time.time()
    for game_id, game in list(games.items()):
        if current_time - game["last_activity"] > 60:  # 60 seconds timeout
            print_error(f"Game {game_id} timed out due to inactivity")
            del games[game_id]
