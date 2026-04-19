from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt


def create_access_token(
    data: dict[str, Any],
    secret: str,
    algorithm: str,
    expires_delta: timedelta,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_token(token: str, secret: str, algorithm: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=[algorithm])


def verify_bearer_token(token: str, secret: str, algorithm: str) -> dict[str, Any]:
    try:
        return decode_token(token, secret, algorithm)
    except JWTError as exc:
        raise ValueError("invalid_token") from exc
