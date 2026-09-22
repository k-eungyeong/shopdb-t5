from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import engine
from security import create_token, get_current_user, hash_password, verify_password
from fastapi import Depends

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    login_id: str = Field(min_length=4, max_length=100)
    password: str = Field(min_length=8, max_length=100)
    user_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    phone: str | None = Field(default=None, max_length=30)


class LoginRequest(BaseModel):
    login_id: str
    password: str


def _public_user(row) -> dict:
    return {
        "user_id": row["user_id"],
        "org_id": row["org_id"],
        "login_id": row["login_id"],
        "user_name": row["user_name"],
        "email": row["email"],
        "phone": row["phone"],
        "user_status": row["user_status"],
    }


@router.post("/signup", status_code=201)
def signup(payload: SignupRequest):
    try:
        password_hash = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with engine.begin() as conn:
        duplicate = conn.execute(text("""
            SELECT login_id, email
            FROM users
            WHERE login_id = :login_id OR email = :email
            LIMIT 1
        """), {"login_id": payload.login_id.strip(), "email": payload.email.lower()}).mappings().first()
        if duplicate:
            if duplicate["login_id"] == payload.login_id.strip():
                raise HTTPException(status_code=409, detail="이미 사용 중인 아이디입니다.")
            raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.")

        # orders.org_id가 NOT NULL이므로 학습용 신규 회원은 활성 조직 하나를 기본 연결합니다.
        default_org = conn.execute(text("""
            SELECT org_id FROM org_units
            WHERE active_yn = 'Y'
            ORDER BY (org_type = 'HEADQUARTER') DESC, org_id
            LIMIT 1
        """)).scalar()

        result = conn.execute(text("""
            INSERT INTO users (org_id, login_id, password_hash, user_name, email, phone, user_status)
            VALUES (:org_id, :login_id, :password_hash, :user_name, :email, :phone, 'ACTIVE')
        """), {
            "org_id": default_org,
            "login_id": payload.login_id.strip(),
            "password_hash": password_hash,
            "user_name": payload.user_name.strip(),
            "email": payload.email.lower(),
            "phone": payload.phone,
        })
        user_id = result.lastrowid

        buyer_role_id = conn.execute(text("SELECT role_id FROM roles WHERE role_code = 'BUYER' LIMIT 1")).scalar()
        if buyer_role_id is not None:
            conn.execute(text("""
                INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)
            """), {"user_id": user_id, "role_id": buyer_role_id})

        user = conn.execute(text("""
            SELECT user_id, org_id, login_id, user_name, email, phone, user_status
            FROM users WHERE user_id = :user_id
        """), {"user_id": user_id}).mappings().first()

    token = create_token(user_id)
    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}


@router.post("/login")
def login(payload: LoginRequest):
    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT user_id, org_id, login_id, password_hash, user_name, email, phone, user_status
            FROM users
            WHERE login_id = :login_id
        """), {"login_id": payload.login_id.strip()}).mappings().first()

    if user is None or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 올바르지 않습니다.")
    if user["user_status"] != "ACTIVE":
        raise HTTPException(status_code=403, detail="현재 사용할 수 없는 회원 계정입니다.")

    token = create_token(user["user_id"])
    return {"access_token": token, "token_type": "bearer", "user": _public_user(user)}


@router.post("/logout")
def logout():
    # JWT는 서버 세션을 저장하지 않으므로 프론트에서 토큰을 삭제하면 로그아웃됩니다.
    return {"message": "로그아웃되었습니다."}


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user

# =========================================================
# 2단계: 비밀번호 찾기 / 재설정 / 로그인 후 비밀번호 변경
# DB 테이블을 추가하지 않기 위해 인증번호는 FastAPI 메모리에 10분만 보관합니다.
# 운영 서비스에서는 Redis 같은 별도 임시 저장소를 사용하는 것이 좋습니다.
# =========================================================
import os
import secrets
import smtplib
import hmac
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from security import decode_token

PASSWORD_RESET_DEV_MODE = os.getenv("PASSWORD_RESET_DEV_MODE", "true").lower() == "true"
RESET_CODE_MINUTES = 10
_password_reset_codes: dict[str, dict] = {}


class PasswordResetRequest(BaseModel):
    login_id: str
    email: str


class PasswordResetVerify(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)


class PasswordResetConfirm(BaseModel):
    reset_token: str
    new_password: str = Field(min_length=8, max_length=100)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=100)


def _send_reset_code(email: str, code: str) -> bool:
    """SMTP 환경변수가 설정되어 있으면 실제 이메일로 인증번호를 보냅니다."""
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM", user or "noreply@t5shop.local")
    if not host or not user or not password:
        return False

    msg = EmailMessage()
    msg["Subject"] = "[T5 SHOP] 비밀번호 재설정 인증번호"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(f"T5 SHOP 인증번호는 {code} 입니다. {RESET_CODE_MINUTES}분 안에 입력해주세요.")

    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    return True


@router.post("/password-reset/request")
def request_password_reset(payload: PasswordResetRequest):
    email = payload.email.strip().lower()
    login_id = payload.login_id.strip()
    with engine.connect() as conn:
        user = conn.execute(text("""
            SELECT user_id, email FROM users
            WHERE login_id=:login_id AND email=:email AND user_status='ACTIVE'
        """), {"login_id": login_id, "email": email}).mappings().first()

    # 계정 존재 여부를 자세히 노출하지 않는 것이 보안상 안전합니다.
    if user is None:
        return {"message": "입력한 정보와 일치하는 계정이 있다면 인증 절차가 진행됩니다."}

    code = f"{secrets.randbelow(1_000_000):06d}"
    _password_reset_codes[email] = {
        "user_id": user["user_id"],
        "code": code,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_MINUTES),
    }

    emailed = False
    try:
        emailed = _send_reset_code(email, code)
    except Exception:
        # 학습용 프로젝트에서는 SMTP 오류 때문에 API 전체가 중단되지 않게 합니다.
        emailed = False

    response = {
        "message": "인증번호가 생성되었습니다.",
        "delivery": "email" if emailed else "development",
        "expires_in_minutes": RESET_CODE_MINUTES,
    }
    # SMTP 미설정 개발환경에서만 화면으로 인증번호를 확인할 수 있게 합니다.
    if not emailed and PASSWORD_RESET_DEV_MODE:
        response["dev_code"] = code
    return response


@router.post("/password-reset/verify")
def verify_password_reset(payload: PasswordResetVerify):
    email = payload.email.strip().lower()
    saved = _password_reset_codes.get(email)
    if saved is None:
        raise HTTPException(status_code=400, detail="인증번호를 먼저 요청해주세요.")
    if datetime.now(timezone.utc) > saved["expires_at"]:
        _password_reset_codes.pop(email, None)
        raise HTTPException(status_code=400, detail="인증번호가 만료되었습니다. 다시 요청해주세요.")
    if not hmac.compare_digest(saved["code"], payload.code.strip()):
        raise HTTPException(status_code=400, detail="인증번호가 올바르지 않습니다.")

    _password_reset_codes.pop(email, None)
    reset_token = create_token(saved["user_id"], minutes=10, purpose="password_reset")
    return {"message": "본인 확인이 완료되었습니다.", "reset_token": reset_token}


@router.post("/password-reset/confirm")
def confirm_password_reset(payload: PasswordResetConfirm):
    decoded = decode_token(payload.reset_token, expected_purpose="password_reset")
    try:
        user_id = int(decoded["sub"])
        new_hash = hash_password(payload.new_password)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE users SET password_hash=:password_hash
            WHERE user_id=:user_id AND user_status='ACTIVE'
        """), {"password_hash": new_hash, "user_id": user_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="회원 정보를 찾을 수 없습니다.")
    return {"message": "새 비밀번호로 변경되었습니다. 다시 로그인해주세요."}


@router.patch("/password")
def change_password(payload: PasswordChangeRequest, current_user: dict = Depends(get_current_user)):
    with engine.begin() as conn:
        stored_hash = conn.execute(text("SELECT password_hash FROM users WHERE user_id=:user_id"), {"user_id": current_user["user_id"]}).scalar()
        if not stored_hash or not verify_password(payload.current_password, stored_hash):
            raise HTTPException(status_code=400, detail="현재 비밀번호가 올바르지 않습니다.")
        if verify_password(payload.new_password, stored_hash):
            raise HTTPException(status_code=400, detail="새 비밀번호는 현재 비밀번호와 다르게 입력해주세요.")
        try:
            new_hash = hash_password(payload.new_password)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        conn.execute(text("UPDATE users SET password_hash=:password_hash WHERE user_id=:user_id"), {"password_hash": new_hash, "user_id": current_user["user_id"]})
    return {"message": "비밀번호가 변경되었습니다."}
