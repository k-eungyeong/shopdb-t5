"""HS256 JWT 생성 및 검증."""

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import HTTPException, status


load_dotenv()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def _secret() -> str:
    if not JWT_SECRET_KEY:
        raise HTTPException(status_code=500, detail="JWT_SECRET_KEY가 설정되지 않았습니다.")
    return JWT_SECRET_KEY


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(user_id: int, role: str | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, str | int] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    if role:
        payload["role"] = role
    header_part = _encode(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload_part = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_part}.{payload_part}"
    signature = hmac.new(_secret().encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_encode(signature)}"


def decode_access_token(token: str) -> dict:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected = hmac.new(_secret().encode(), signing_input.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _decode(signature_part)):
            raise ValueError("invalid signature")
        header = json.loads(_decode(header_part))
        payload = json.loads(_decode(payload_part))
        if header.get("alg") != "HS256" or payload.get("exp", 0) <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("invalid token")
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인 토큰이 유효하지 않거나 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
