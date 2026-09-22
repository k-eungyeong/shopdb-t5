import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from database import engine

# 학습용 프로젝트의 기본값입니다. 실제 서비스에서는 반드시 .env에 긴 임의 문자열을 넣으세요.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-development-secret-key")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
PASSWORD_ITERATIONS = int(os.getenv("PASSWORD_ITERATIONS", "260000"))

bearer_scheme = HTTPBearer(auto_error=False)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _b64_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    # passlib 계열 문자열에서 '.'가 '+' 대신 쓰이는 경우도 허용합니다.
    return base64.b64decode(data.replace(".", "+") + padding)


def hash_password(password: str) -> str:
    """비밀번호 원문을 PBKDF2-SHA256 해시 문자열로 변환합니다."""
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")

    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    salt_text = base64.b64encode(salt).decode("utf-8").rstrip("=")
    digest_text = base64.b64encode(digest).decode("utf-8").rstrip("=")
    return f"$pbkdf2-sha256${PASSWORD_ITERATIONS}${salt_text}${digest_text}"


def verify_password(password: str, stored_hash: str) -> bool:
    """DB의 PBKDF2-SHA256 해시와 사용자가 입력한 비밀번호를 비교합니다."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 5 or parts[1] != "pbkdf2-sha256":
            # 초기 샘플의 '$2b$buyer01' 같은 값은 실제 bcrypt 해시가 아니므로 로그인할 수 없습니다.
            return False
        iterations = int(parts[2])
        salt = _b64_decode(parts[3])
        expected = _b64_decode(parts[4])
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError, base64.binascii.Error):
        return False


def create_token(user_id: int, *, minutes: int | None = None, purpose: str = "access") -> str:
    """외부 라이브러리 없이 HS256 방식의 간단한 JWT를 만듭니다."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=minutes or JWT_EXPIRE_MINUTES)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "purpose": purpose,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    header_part = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_part}.{payload_part}".encode()
    signature = hmac.new(JWT_SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    return f"{header_part}.{payload_part}.{_b64url_encode(signature)}"


def decode_token(token: str, *, expected_purpose: str = "access") -> dict:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}".encode()
        expected = hmac.new(JWT_SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        actual = _b64url_decode(signature_part)
        if not hmac.compare_digest(expected, actual):
            raise ValueError("signature")

        payload = json.loads(_b64url_decode(payload_part))
        if payload.get("purpose") != expected_purpose:
            raise ValueError("purpose")
        if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="로그인이 만료되었거나 올바르지 않은 토큰입니다.") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
):
    """Authorization: Bearer <token>에서 현재 로그인 사용자를 찾아냅니다."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    payload = decode_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="올바르지 않은 로그인 정보입니다.") from exc

    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT user_id, org_id, login_id, user_name, email, phone, user_status, created_at
            FROM users
            WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().first()

        if user is None or user["user_status"] != "ACTIVE":
            raise HTTPException(status_code=401, detail="사용할 수 없는 회원 계정입니다.")

        roles = conn.execute(text("""
            SELECT r.role_code
            FROM user_roles ur
            INNER JOIN roles r ON r.role_id = ur.role_id
            WHERE ur.user_id = :user_id
            ORDER BY r.role_id
        """), {"user_id": user_id}).scalars().all()

    result = dict(user)
    result["roles"] = list(roles)
    return result
