from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from database import engine


router = APIRouter(prefix="/wishlist", tags=["wishlist"])


class WishlistCreate(BaseModel):
    user_id: int
    product_id: int


@router.post("")
def add_wishlist(item: WishlistCreate):
    # 사용자 존재 여부 확인
    with engine.connect() as conn:
        user = conn.execute(
            text("""
                SELECT user_id
                FROM users
                WHERE user_id = :user_id
            """),
            {"user_id": item.user_id},
        ).fetchone()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="사용자를 찾을 수 없습니다.",
            )

        # 상품 존재 여부 확인
        product = conn.execute(
            text("""
                SELECT product_id
                FROM products
                WHERE product_id = :product_id
            """),
            {"product_id": item.product_id},
        ).fetchone()

        if product is None:
            raise HTTPException(
                status_code=404,
                detail="상품을 찾을 수 없습니다.",
            )

        # 이미 찜한 상품인지 확인
        existing = conn.execute(
            text("""
                SELECT wishlist_id
                FROM t5_wishlist_items
                WHERE user_id = :user_id
                  AND product_id = :product_id
            """),
            {
                "user_id": item.user_id,
                "product_id": item.product_id,
            },
        ).fetchone()

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="이미 찜한 상품입니다.",
            )

        # wishlist_id는 DB 트리거가 자동 생성
        conn.execute(
            text("""
                INSERT INTO t5_wishlist_items (
                    user_id,
                    product_id
                )
                VALUES (
                    :user_id,
                    :product_id
                )
            """),
            {
                "user_id": item.user_id,
                "product_id": item.product_id,
            },
        )

        conn.commit()

        # 트리거가 생성한 wishlist_id 조회
        created = conn.execute(
            text("""
                SELECT wishlist_id, user_id, product_id, added_at
                FROM t5_wishlist_items
                WHERE user_id = :user_id
                  AND product_id = :product_id
            """),
            {
                "user_id": item.user_id,
                "product_id": item.product_id,
            },
        ).mappings().first()

    return {
        "message": "찜 목록에 추가되었습니다.",
        "wishlist": dict(created),
    }


@router.get("")
def get_wishlist(user_id: int):
    with engine.connect() as conn:
        # 사용자 존재 여부 확인
        user = conn.execute(
            text("""
                SELECT user_id
                FROM users
                WHERE user_id = :user_id
            """),
            {"user_id": user_id},
        ).fetchone()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="사용자를 찾을 수 없습니다.",
            )

        result = conn.execute(
            text("""
                SELECT
                    w.wishlist_id,
                    w.user_id,
                    w.product_id,
                    p.product_code,
                    p.product_name,
                    p.short_description,
                    p.regular_price,
                    p.sale_price,
                    p.product_status,
                    w.added_at
                FROM t5_wishlist_items w
                INNER JOIN products p
                    ON w.product_id = p.product_id
                WHERE w.user_id = :user_id
                ORDER BY w.added_at DESC, w.wishlist_id DESC
            """),
            {"user_id": user_id},
        ).mappings().all()

    return {
        "user_id": user_id,
        "count": len(result),
        "items": [dict(row) for row in result],
    }


@router.get("/check")
def check_wishlist(user_id: int, product_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT
                    wishlist_id,
                    user_id,
                    product_id,
                    added_at
                FROM t5_wishlist_items
                WHERE user_id = :user_id
                  AND product_id = :product_id
            """),
            {
                "user_id": user_id,
                "product_id": product_id,
            },
        ).mappings().first()

    if result is None:
        return {
            "user_id": user_id,
            "product_id": product_id,
            "is_wishlisted": False,
        }

    return {
        "user_id": user_id,
        "product_id": product_id,
        "is_wishlisted": True,
        "wishlist": dict(result),
    }


@router.delete("/{wishlist_id}")
def delete_wishlist(wishlist_id: str):
    with engine.connect() as conn:
        existing = conn.execute(
            text("""
                SELECT wishlist_id
                FROM t5_wishlist_items
                WHERE wishlist_id = :wishlist_id
            """),
            {"wishlist_id": wishlist_id},
        ).fetchone()

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="찜 목록 항목을 찾을 수 없습니다.",
            )

        conn.execute(
            text("""
                DELETE FROM t5_wishlist_items
                WHERE wishlist_id = :wishlist_id
            """),
            {"wishlist_id": wishlist_id},
        )

        conn.commit()

    return {
        "message": "찜 목록에서 삭제되었습니다.",
        "wishlist_id": wishlist_id,
    }
