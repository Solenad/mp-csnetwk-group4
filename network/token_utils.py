import time


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
