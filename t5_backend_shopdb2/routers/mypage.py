from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/mypage", tags=["mypage"])


class ProfileUpdate(BaseModel):
    user_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    phone: str | None = Field(default=None, max_length=30)


class AddressPayload(BaseModel):
    address_name: str | None = Field(default=None, max_length=100)
    receiver_name: str | None = Field(default=None, max_length=100)
    receiver_phone: str | None = Field(default=None, max_length=30)
    zipcode: str | None = Field(default=None, max_length=20)
    address1: str | None = Field(default=None, max_length=300)
    address2: str | None = Field(default=None, max_length=300)
    default_yn: str = "N"


@router.get("/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    return current_user


@router.patch("/profile")
def update_profile(payload: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    email = payload.email.strip().lower()
    with engine.begin() as conn:
        duplicate = conn.execute(text("""
            SELECT user_id FROM users WHERE email=:email AND user_id<>:user_id LIMIT 1
        """), {"email": email, "user_id": current_user["user_id"]}).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="이미 다른 회원이 사용 중인 이메일입니다.")
        conn.execute(text("""
            UPDATE users
            SET user_name=:user_name, email=:email, phone=:phone
            WHERE user_id=:user_id
        """), {
            "user_name": payload.user_name.strip(),
            "email": email,
            "phone": payload.phone,
            "user_id": current_user["user_id"],
        })
    return {"message": "회원정보가 수정되었습니다."}


@router.get("/addresses")
def get_addresses(current_user: dict = Depends(get_current_user)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT address_id, address_name, receiver_name, receiver_phone, zipcode,
                   address1, address2, default_yn, created_at
            FROM user_addresses
            WHERE user_id=:user_id
            ORDER BY (default_yn='Y') DESC, address_id DESC
        """), {"user_id": current_user["user_id"]}).mappings().all()
    return {"items": [dict(row) for row in rows]}


def _normalize_default(value: str) -> str:
    return "Y" if str(value).upper() == "Y" else "N"


@router.post("/addresses", status_code=201)
def create_address(payload: AddressPayload, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    default_yn = _normalize_default(payload.default_yn)
    with engine.begin() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM user_addresses WHERE user_id=:user_id"), {"user_id": user_id}).scalar()
        if count == 0:
            default_yn = "Y"
        if default_yn == "Y":
            conn.execute(text("UPDATE user_addresses SET default_yn='N' WHERE user_id=:user_id"), {"user_id": user_id})
        result = conn.execute(text("""
            INSERT INTO user_addresses
                (user_id, address_name, receiver_name, receiver_phone, zipcode, address1, address2, default_yn)
            VALUES
                (:user_id, :address_name, :receiver_name, :receiver_phone, :zipcode, :address1, :address2, :default_yn)
        """), {"user_id": user_id, **payload.model_dump(exclude={"default_yn"}), "default_yn": default_yn})
        address_id = result.lastrowid
    return {"message": "배송지가 등록되었습니다.", "address_id": address_id}


@router.patch("/addresses/{address_id}")
def update_address(address_id: int, payload: AddressPayload, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    default_yn = _normalize_default(payload.default_yn)
    with engine.begin() as conn:
        owned = conn.execute(text("SELECT address_id FROM user_addresses WHERE address_id=:id AND user_id=:user_id"), {"id": address_id, "user_id": user_id}).first()
        if not owned:
            raise HTTPException(status_code=404, detail="배송지를 찾을 수 없습니다.")
        if default_yn == "Y":
            conn.execute(text("UPDATE user_addresses SET default_yn='N' WHERE user_id=:user_id"), {"user_id": user_id})
        conn.execute(text("""
            UPDATE user_addresses
            SET address_name=:address_name, receiver_name=:receiver_name, receiver_phone=:receiver_phone,
                zipcode=:zipcode, address1=:address1, address2=:address2, default_yn=:default_yn
            WHERE address_id=:address_id AND user_id=:user_id
        """), {**payload.model_dump(exclude={"default_yn"}), "default_yn": default_yn, "address_id": address_id, "user_id": user_id})
    return {"message": "배송지가 수정되었습니다."}


@router.patch("/addresses/{address_id}/default")
def set_default_address(address_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        owned = conn.execute(text("SELECT address_id FROM user_addresses WHERE address_id=:id AND user_id=:user_id"), {"id": address_id, "user_id": user_id}).first()
        if not owned:
            raise HTTPException(status_code=404, detail="배송지를 찾을 수 없습니다.")
        conn.execute(text("UPDATE user_addresses SET default_yn='N' WHERE user_id=:user_id"), {"user_id": user_id})
        conn.execute(text("UPDATE user_addresses SET default_yn='Y' WHERE address_id=:id AND user_id=:user_id"), {"id": address_id, "user_id": user_id})
    return {"message": "기본 배송지를 변경했습니다."}


@router.delete("/addresses/{address_id}")
def delete_address(address_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        row = conn.execute(text("SELECT default_yn FROM user_addresses WHERE address_id=:id AND user_id=:user_id"), {"id": address_id, "user_id": user_id}).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="배송지를 찾을 수 없습니다.")
        conn.execute(text("DELETE FROM user_addresses WHERE address_id=:id AND user_id=:user_id"), {"id": address_id, "user_id": user_id})
        if row["default_yn"] == "Y":
            next_id = conn.execute(text("SELECT address_id FROM user_addresses WHERE user_id=:user_id ORDER BY address_id LIMIT 1"), {"user_id": user_id}).scalar()
            if next_id:
                conn.execute(text("UPDATE user_addresses SET default_yn='Y' WHERE address_id=:id"), {"id": next_id})
    return {"message": "배송지를 삭제했습니다."}


@router.patch("/withdraw")
def withdraw(current_user: dict = Depends(get_current_user)):
    # 주문/결제 이력을 보존해야 하므로 DELETE가 아니라 상태만 WITHDRAWN으로 변경합니다.
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET user_status='WITHDRAWN' WHERE user_id=:user_id"), {"user_id": current_user["user_id"]})
    return {"message": "회원 탈퇴 처리되었습니다."}
