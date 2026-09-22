from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/cart", tags=["cart"])


class CartCreate(BaseModel):
    product_id: int
    variant_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class CartUpdate(BaseModel):
    quantity: int = Field(ge=1, le=99)


@router.post("")
def add_to_cart(payload: CartCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        item = conn.execute(text("""
            SELECT p.product_id, p.sale_price, p.product_status,
                   pv.variant_id, pv.additional_price,
                   COALESCE(SUM(GREATEST(i.stock_quantity - i.reserved_quantity, 0)), 0) AS available_stock
            FROM products p
            INNER JOIN product_variants pv ON pv.product_id = p.product_id
            LEFT JOIN inventories i ON i.variant_id = pv.variant_id
            WHERE p.product_id = :product_id
              AND pv.variant_id = :variant_id
              AND pv.active_yn = 'Y'
              AND p.product_status <> 'DELETED'
            GROUP BY p.product_id, p.sale_price, p.product_status, pv.variant_id, pv.additional_price
        """), {"product_id": payload.product_id, "variant_id": payload.variant_id}).mappings().first()

        if item is None:
            raise HTTPException(status_code=404, detail="상품 또는 옵션을 찾을 수 없습니다.")

        existing = conn.execute(text("""
            SELECT carts_id, quantity FROM t5_carts
            WHERE user_id = :user_id AND product_id = :product_id AND variant_id = :variant_id
            ORDER BY added_at DESC LIMIT 1
        """), {"user_id": user_id, "product_id": payload.product_id, "variant_id": payload.variant_id}).mappings().first()

        next_quantity = payload.quantity + (existing["quantity"] if existing else 0)
        if next_quantity > int(item["available_stock"] or 0):
            raise HTTPException(status_code=400, detail="선택한 수량보다 재고가 부족합니다.")

        sale_price = item["sale_price"] + item["additional_price"]
        if existing:
            conn.execute(text("""
                UPDATE t5_carts SET quantity = :quantity, sale_price = :sale_price
                WHERE carts_id = :carts_id AND user_id = :user_id
            """), {"quantity": next_quantity, "sale_price": sale_price, "carts_id": existing["carts_id"], "user_id": user_id})
        else:
            # carts_id는 기존 DB 트리거 trg_t5_carts_pk가 생성합니다.
            conn.execute(text("""
                INSERT INTO t5_carts (user_id, product_id, variant_id, sale_price, quantity)
                VALUES (:user_id, :product_id, :variant_id, :sale_price, :quantity)
            """), {"user_id": user_id, "product_id": payload.product_id, "variant_id": payload.variant_id, "sale_price": sale_price, "quantity": payload.quantity})

    return {"message": "장바구니에 담았습니다."}


@router.get("")
def get_cart(current_user: dict = Depends(get_current_user)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT c.carts_id, c.product_id, c.variant_id, c.sale_price, c.quantity, c.added_at,
                   p.product_name, p.short_description,
                   pv.sku_code, pv.option_name1, pv.option_value1, pv.option_name2, pv.option_value2,
                   COALESCE((SELECT SUM(GREATEST(i.stock_quantity - i.reserved_quantity, 0))
                             FROM inventories i WHERE i.variant_id = c.variant_id), 0) AS available_stock,
                   (SELECT COALESCE(f.thumbnail_url, f.public_url)
                    FROM product_images pi
                    INNER JOIN file_assets f ON f.file_id = pi.file_id
                    WHERE pi.product_id = p.product_id AND pi.active_yn = 'Y'
                    ORDER BY (pi.image_type = 'MAIN') DESC, pi.display_order, pi.product_image_id LIMIT 1) AS image
            FROM t5_carts c
            INNER JOIN products p ON p.product_id = c.product_id
            INNER JOIN product_variants pv ON pv.variant_id = c.variant_id
            WHERE c.user_id = :user_id
            ORDER BY c.added_at DESC
        """), {"user_id": current_user["user_id"]}).mappings().all()
    return {"items": [dict(row) for row in rows]}


@router.patch("/{carts_id}")
def update_cart(carts_id: str, payload: CartUpdate, current_user: dict = Depends(get_current_user)):
    with engine.begin() as conn:
        item = conn.execute(text("""
            SELECT c.variant_id,
                   COALESCE((SELECT SUM(GREATEST(i.stock_quantity - i.reserved_quantity, 0))
                             FROM inventories i WHERE i.variant_id = c.variant_id), 0) AS available_stock
            FROM t5_carts c
            WHERE c.carts_id = :carts_id AND c.user_id = :user_id
        """), {"carts_id": carts_id, "user_id": current_user["user_id"]}).mappings().first()
        if item is None:
            raise HTTPException(status_code=404, detail="장바구니 항목을 찾을 수 없습니다.")
        if payload.quantity > int(item["available_stock"] or 0):
            raise HTTPException(status_code=400, detail="재고보다 많은 수량을 선택할 수 없습니다.")
        conn.execute(text("""
            UPDATE t5_carts SET quantity = :quantity
            WHERE carts_id = :carts_id AND user_id = :user_id
        """), {"quantity": payload.quantity, "carts_id": carts_id, "user_id": current_user["user_id"]})
    return {"message": "수량을 변경했습니다."}


@router.delete("/{carts_id}")
def delete_cart(carts_id: str, current_user: dict = Depends(get_current_user)):
    with engine.begin() as conn:
        result = conn.execute(text("""
            DELETE FROM t5_carts WHERE carts_id = :carts_id AND user_id = :user_id
        """), {"carts_id": carts_id, "user_id": current_user["user_id"]})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="장바구니 항목을 찾을 수 없습니다.")
    return {"message": "삭제했습니다."}
