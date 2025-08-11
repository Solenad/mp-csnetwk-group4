# tictactoe.py
import time
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

games = {}  # GAMEID -> {board, players, turn, symbol_map, last_turn_received}


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
        return False

    timestamp = int(time.time())
    game_id = f"g{secrets.randbelow(256)}"
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

    send_unicast(message, (peer["ip"], int(peer["port"])))

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
    }

    print_success(f"Invite sent to {recipient_id} for game {game_id} as {symbol}")
    print_prompt()
    return True


def send_move(game_id, position, sender_info):
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

    send_unicast(message, (peer["ip"], int(peer["port"])))

    print_info(f"You played at position {position} in game {game_id}")
    print(format_board(game["board"]))
    print_prompt()

    winner, line = check_winner(game["board"])
    if winner:
        send_result(game_id, winner, line, sender_info)


def send_result(game_id, result, winning_line, sender_info):
    if game_id not in games:
        return

    game = games[game_id]
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

    send_unicast(message, (peer["ip"], int(peer["port"])))
    print_success(f"Game {game_id} ended: {result}")
    print_prompt()


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
    }

    print_info(f"{from_user} is inviting you to play tic-tac-toe (Game {game_id})")
    print_info(f"You are playing as {symbol}")
    print(format_board(games[game_id]["board"]))
    print_prompt()

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
        return

    game = games[game_id]
    if (game_id, turn) in game["last_turn_received"]:
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

    for attempt in range(retry_count):
        send_unicast(message, (peer["ip"], int(peer["port"])))

        # Wait for ACK with timeout
        ack_received = wait_for_ack(message_id, timeout=2)
        if ack_received:
            break

        if attempt == retry_count - 1:
            print_error("Move failed to reach opponent after multiple attempts")
            return False


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
    print_prompt()

    if "MESSAGE_ID" in content:
        send_ack(content["MESSAGE_ID"], content["FROM"])
