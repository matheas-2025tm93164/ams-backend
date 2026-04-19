from __future__ import annotations

from datetime import timedelta

from shared.jwt_tokens import create_access_token, verify_bearer_token


def test_jwt_create_and_verify():
    secret = "x" * 32
    token = create_access_token(
        {"sub": "abc", "role": "resident"},
        secret,
        "HS256",
        timedelta(minutes=5),
    )
    payload = verify_bearer_token(token, secret, "HS256")
    assert payload["sub"] == "abc"
    assert payload["role"] == "resident"
