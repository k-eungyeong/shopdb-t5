from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from database import engine

router = APIRouter(prefix="/cart", tags=["cart"])


# ---- 요청 body 형태를 정의하는 스키마 ----
class CartCreate(BaseModel):
    user_id: int
    product_id: int
    variant_id: int
    quantity: int = 1   # quantity를 안 보내면 기본값 1


class CartUpdate(BaseModel):
    quantity: int


# ---- 1. 담기 (POST /cart) ----
@router.post("")
def add_to_cart(payload: CartCreate):
    with engine.connect() as conn:
        # 가격은 클라이언트가 보내는 게 아니라 서버가 products 테이블에서 직접 조회
        price_row = conn.execute(
            text("SELECT sale_price FROM products WHERE product_id = :pid"),
            {"pid": payload.product_id}
        ).fetchone()

        if not price_row:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다")

        sale_price = price_row[0]

        conn.execute(
            text("""
                INSERT INTO t5_carts (user_id, product_id, variant_id, sale_price, quantity)
                VALUES (:user_id, :product_id, :variant_id, :sale_price, :quantity)
            """),
            {
                "user_id": payload.user_id,
                "product_id": payload.product_id,
                "variant_id": payload.variant_id,
                "sale_price": sale_price,
                "quantity": payload.quantity,
            }
        )
        conn.commit()   # INSERT/UPDATE/DELETE는 commit() 안 하면 실제로 저장 안 됨

    return {"message": "장바구니에 담았습니다"}


# ---- 2. 조회 (GET /cart?user_id=4) ----
@router.get("")
def get_cart(user_id: int):
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM t5_carts WHERE user_id = :user_id"),
            {"user_id": user_id}
        ).mappings().all()

    return {"items": [dict(row) for row in rows]}


# ---- 3. 수량 변경 (PATCH /cart/{carts_id}) ----
@router.patch("/{carts_id}")
def update_cart(carts_id: str, payload: CartUpdate):
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE t5_carts SET quantity = :quantity WHERE carts_id = :carts_id"),
            {"quantity": payload.quantity, "carts_id": carts_id}
        )
        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="해당 장바구니 항목을 찾을 수 없습니다")

    return {"message": "수량을 변경했습니다"}


# ---- 4. 삭제 (DELETE /cart/{carts_id}) ----
@router.delete("/{carts_id}")
def delete_cart(carts_id: str):
    with engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM t5_carts WHERE carts_id = :carts_id"),
            {"carts_id": carts_id}
        )
        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="해당 장바구니 항목을 찾을 수 없습니다")

    return {"message": "삭제했습니다"}