"""JWT 액세스 토큰 생성 및 검증 함수.

로그인 API는 나중에 ``create_access_token``을 호출하여 토큰을 발급하면 됩니다.
"""

import os
import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import HTTPException, status


load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def _get_secret_key() -> str:
    """비밀키 누락을 조용히 넘기지 않고 설정 오류로 알려줍니다."""

    if not JWT_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="서버에 JWT_SECRET_KEY가 설정되지 않았습니다.",
        )
    return JWT_SECRET_KEY


def create_access_token(user_id: int, role: str | None = None) -> str:
    """로그인 성공 후 사용자 번호가 담긴 액세스 토큰을 생성합니다."""

    now = datetime.now(timezone.utc)
    payload: dict[str, str | int] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()
        ),
    }
    if role is not None:
        payload["role"] = role

    if JWT_ALGORITHM != "HS256":
        raise HTTPException(status_code=500, detail="현재 JWT_ALGORITHM은 HS256만 지원합니다.")

    header = {"alg": "HS256", "typ": "JWT"}
    header_part = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_part = _base64url_encode(
        json.dumps(payload, separators=(",", ":")).encode()
    )
    signing_input = f"{header_part}.{payload_part}"
    signature = hmac.new(
        _get_secret_key().encode(),
        signing_input.encode(),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict:
    """토큰의 서명과 만료시간을 검증한 후 내용을 반환합니다."""

    try:
        if JWT_ALGORITHM != "HS256":
            raise ValueError("unsupported algorithm")

        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}"
        expected_signature = hmac.new(
            _get_secret_key().encode(),
            signing_input.encode(),
            hashlib.sha256,
        ).digest()
        supplied_signature = _base64url_decode(signature_part)
        if not hmac.compare_digest(expected_signature, supplied_signature):
            raise ValueError("invalid signature")

        header = json.loads(_base64url_decode(header_part))
        if header.get("alg") != "HS256":
            raise ValueError("invalid algorithm")

        payload = json.loads(_base64url_decode(payload_part))
        expires_at = payload.get("exp")
        if not isinstance(expires_at, int):
            raise ValueError("missing expiration")
        if expires_at <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired token")
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인 토큰이 유효하지 않거나 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _base64url_encode(value: bytes) -> str:
    """JWT 규격에 맞게 패딩 없는 URL-safe Base64 문자열을 만듭니다."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _base64url_decode(value: str) -> bytes:
    """패딩이 생략된 JWT Base64 문자열을 바이트로 복원합니다."""

    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
