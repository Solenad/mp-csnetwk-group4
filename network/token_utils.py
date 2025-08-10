# token_utils.py
import time
from typing import Set
import json
import os
import config

REVOKED_TOKENS_FILE = "revoked_tokens.json"


# In-memory revocation list
revoked_tokens: Set[str] = set()


def generate_token(user_id: str, scope: str, ttl: int = None) -> str:
    """Generate a new token with the given scope and TTL"""
    expiry = int(time.time()) + (
        ttl if ttl is not None else config.TOKEN_TTL.get(scope, 3600)
    )
    return f"{user_id}|{expiry}|{scope}"


def validate_token(token: str, expected_scope: str) -> bool:
    """Validate a token against the expected scope"""
    try:
        # Check if token is revoked
        if token in revoked_tokens:
            return False

        parts = token.split("|")
        if len(parts) != 3:
            return False

        user_id, expiry_str, scope = parts

        # Validate scope
        if scope != expected_scope:
            return False

        # Validate expiration
        expiry = int(expiry_str)
        if expiry < time.time():
            return False

        return True
    except (ValueError, AttributeError):
        return False


def verify_token_ip(token: str, source_ip: str) -> bool:
    """Verify the IP in token matches the sender's IP"""
    try:
        user_part = token.split("|")[0]
        token_ip = user_part.split("@")[1].split(":")[0]
        return token_ip == source_ip
    except (IndexError, AttributeError):
        return False


def load_revoked_tokens():
    if os.path.exists(REVOKED_TOKENS_FILE):
        with open(REVOKED_TOKENS_FILE) as f:
            return set(json.load(f))
    return set()


def save_revoked_tokens():
    with open(REVOKED_TOKENS_FILE, "w") as f:
        json.dump(list(revoked_tokens), f)


revoked_tokens = load_revoked_tokens()


def revoke_token(token: str) -> None:
    revoked_tokens.add(token)
    save_revoked_tokens()
