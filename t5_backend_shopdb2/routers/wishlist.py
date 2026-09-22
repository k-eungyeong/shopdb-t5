from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


class WishlistCreate(BaseModel):
    product_id: int


@router.post("")
def add_wishlist(item: WishlistCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        product = conn.execute(text("SELECT product_id FROM products WHERE product_id=:id AND product_status <> 'DELETED'"), {"id": item.product_id}).first()
        if product is None:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
        existing = conn.execute(text("""
            SELECT wishlist_id FROM t5_wishlist_items WHERE user_id=:user_id AND product_id=:product_id
        """), {"user_id": user_id, "product_id": item.product_id}).first()
        if existing:
            raise HTTPException(status_code=409, detail="이미 찜한 상품입니다.")
        conn.execute(text("""
            INSERT INTO t5_wishlist_items (user_id, product_id) VALUES (:user_id, :product_id)
        """), {"user_id": user_id, "product_id": item.product_id})
        created = conn.execute(text("""
            SELECT wishlist_id, product_id, added_at FROM t5_wishlist_items
            WHERE user_id=:user_id AND product_id=:product_id
        """), {"user_id": user_id, "product_id": item.product_id}).mappings().first()
    return {"message": "찜 목록에 추가되었습니다.", "wishlist": dict(created)}


@router.get("")
def get_wishlist(current_user: dict = Depends(get_current_user)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT w.wishlist_id, w.product_id, w.added_at,
                   p.product_code, p.product_name, p.short_description, p.regular_price, p.sale_price, p.product_status,
                   (SELECT COALESCE(f.thumbnail_url, f.public_url)
                    FROM product_images pi INNER JOIN file_assets f ON f.file_id=pi.file_id
                    WHERE pi.product_id=p.product_id AND pi.active_yn='Y'
                    ORDER BY (pi.image_type='MAIN') DESC, pi.display_order, pi.product_image_id LIMIT 1) AS image
            FROM t5_wishlist_items w
            INNER JOIN products p ON p.product_id=w.product_id
            WHERE w.user_id=:user_id
            ORDER BY w.added_at DESC
        """), {"user_id": current_user["user_id"]}).mappings().all()
    return {"items": [dict(r) for r in rows]}


@router.get("/check")
def check_wishlist(product_id: int, current_user: dict = Depends(get_current_user)):
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT wishlist_id, product_id, added_at FROM t5_wishlist_items
            WHERE user_id=:user_id AND product_id=:product_id
        """), {"user_id": current_user["user_id"], "product_id": product_id}).mappings().first()
    return {"is_wishlisted": row is not None, "wishlist": dict(row) if row else None}


@router.delete("/{wishlist_id}")
def delete_wishlist(wishlist_id: str, current_user: dict = Depends(get_current_user)):
    with engine.begin() as conn:
        result = conn.execute(text("""
            DELETE FROM t5_wishlist_items WHERE wishlist_id=:wishlist_id AND user_id=:user_id
        """), {"wishlist_id": wishlist_id, "user_id": current_user["user_id"]})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="찜 항목을 찾을 수 없습니다.")
    return {"message": "찜 목록에서 삭제했습니다."}
