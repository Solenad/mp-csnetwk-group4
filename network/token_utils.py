import time

def generate_token(user_id: str, ttl: int, scope: str) -> str:
    expiry = int(time.time()) + ttl
    return f"{user_id}|{expiry}|{scope}"

def validate_token(token: str, expected_scope: str) -> bool:
    try:
        parts = token.split("|")
        if len(parts) != 3:
            return False

        user_id, expiry, scope = parts
        if scope != expected_scope:
            return False

        return int(expiry) > time.time()
    except:
        return False
