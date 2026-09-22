from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewCreate(BaseModel):
    order_item_id: int
    product_id: int
    rating: int = Field(ge=1, le=5)
    review_txt: str = Field(min_length=2, max_length=2000)


@router.get("/eligibility/{product_id}")
def get_review_eligibility(product_id: int, current_user: dict = Depends(get_current_user)):
    """
    상품 상세 페이지에서 현재 로그인 회원이 이 상품에 리뷰를 쓸 수 있는지 확인합니다.

    핵심 규칙
    1) 실제로 본인이 구매한 order_items 여야 합니다.
    2) 해당 주문상품 상태가 DELIVERED(배송완료) 또는 COMPLETED(구매완료)여야 합니다.
    3) 같은 order_item_id 로 이미 리뷰를 작성했다면 다시 작성할 수 없습니다.

    SQL 테이블 구조는 변경하지 않고 기존 orders / order_items /
    t5_product_reviews 테이블만 조회합니다.
    """
    user_id = current_user["user_id"]

    with engine.connect() as conn:
        product_exists = conn.execute(text("""
            SELECT product_id
            FROM products
            WHERE product_id = :product_id
              AND product_status <> 'DELETED'
        """), {"product_id": product_id}).first()
        if product_exists is None:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

        # 같은 상품을 여러 번 구매할 수도 있으므로, 리뷰를 아직 쓰지 않은
        # 가장 최근의 배송완료/구매완료 주문상품 1건을 리뷰 대상으로 선택합니다.
        reviewable_item = conn.execute(text("""
            SELECT
                oi.order_item_id,
                oi.order_id,
                oi.product_id,
                oi.variant_id,
                oi.product_name_snapshot,
                oi.sku_snapshot,
                oi.quantity,
                o.order_no,
                o.order_status,
                o.ordered_at
            FROM order_items oi
            INNER JOIN orders o ON o.order_id = oi.order_id
            LEFT JOIN t5_product_reviews r ON r.order_item_id = oi.order_item_id
            WHERE o.buyer_user_id = :user_id
              AND oi.product_id = :product_id
              AND oi.item_status IN ('DELIVERED','COMPLETED')
              AND r.review_id IS NULL
            ORDER BY o.ordered_at DESC, oi.order_item_id DESC
            LIMIT 1
        """), {"user_id": user_id, "product_id": product_id}).mappings().first()

        summary = conn.execute(text("""
            SELECT
                SUM(CASE WHEN oi.item_status IN ('PAID','PREPARING','SHIPPING','DELIVERED','COMPLETED')
                         THEN 1 ELSE 0 END) AS purchased_count,
                SUM(CASE WHEN oi.item_status IN ('DELIVERED','COMPLETED')
                         THEN 1 ELSE 0 END) AS reviewable_count,
                SUM(CASE WHEN oi.item_status IN ('DELIVERED','COMPLETED') AND r.review_id IS NOT NULL
                         THEN 1 ELSE 0 END) AS reviewed_count
            FROM order_items oi
            INNER JOIN orders o ON o.order_id = oi.order_id
            LEFT JOIN t5_product_reviews r ON r.order_item_id = oi.order_item_id
            WHERE o.buyer_user_id = :user_id
              AND oi.product_id = :product_id
        """), {"user_id": user_id, "product_id": product_id}).mappings().first()

    if reviewable_item:
        return {
            "can_review": True,
            "message": "배송완료된 구매 상품입니다. 리뷰를 작성할 수 있습니다.",
            "order_item": dict(reviewable_item),
        }

    purchased_count = int(summary["purchased_count"] or 0)
    reviewable_count = int(summary["reviewable_count"] or 0)
    reviewed_count = int(summary["reviewed_count"] or 0)

    if reviewable_count > 0 and reviewed_count >= reviewable_count:
        message = "배송완료된 주문상품의 리뷰를 이미 작성했습니다."
    elif purchased_count > 0:
        message = "구매한 상품입니다. 판매자 또는 관리자가 배송완료로 변경하면 리뷰를 작성할 수 있습니다."
    else:
        message = "이 상품을 실제로 구매한 회원만 리뷰를 작성할 수 있습니다."

    return {
        "can_review": False,
        "message": message,
        "order_item": None,
    }


@router.post("")
def create_review(payload: ReviewCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        order_item = conn.execute(text("""
            SELECT oi.order_item_id, oi.product_id, oi.item_status, o.buyer_user_id, o.order_status
            FROM order_items oi
            INNER JOIN orders o ON o.order_id = oi.order_id
            WHERE oi.order_item_id = :order_item_id
        """), {"order_item_id": payload.order_item_id}).mappings().first()
        if order_item is None:
            raise HTTPException(status_code=404, detail="주문 상품을 찾을 수 없습니다.")
        if order_item["buyer_user_id"] != user_id:
            raise HTTPException(status_code=403, detail="본인의 주문에만 리뷰를 작성할 수 있습니다.")
        if order_item["product_id"] != payload.product_id:
            raise HTTPException(status_code=400, detail="주문 상품과 리뷰 상품이 일치하지 않습니다.")
        if order_item["item_status"] not in {"DELIVERED", "COMPLETED"}:
            raise HTTPException(status_code=400, detail="배송완료된 구매 상품에만 리뷰를 작성할 수 있습니다.")
        if conn.execute(text("SELECT review_id FROM t5_product_reviews WHERE order_item_id=:id"), {"id": payload.order_item_id}).first():
            raise HTTPException(status_code=409, detail="이미 리뷰가 작성된 주문 상품입니다.")

        # review_id는 기존 DB 트리거 trg_t5_reviews_pk가 생성합니다.
        conn.execute(text("""
            INSERT INTO t5_product_reviews (order_item_id, user_id, product_id, rating, review_txt)
            VALUES (:order_item_id, :user_id, :product_id, :rating, :review_txt)
        """), {**payload.model_dump(), "user_id": user_id})
        created = conn.execute(text("""
            SELECT review_id, order_item_id, user_id, product_id, rating, review_txt, added_at
            FROM t5_product_reviews WHERE order_item_id=:id
        """), {"id": payload.order_item_id}).mappings().first()
    return {"message": "리뷰가 등록되었습니다.", "review": dict(created)}

class ReviewUpdate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_txt: str = Field(min_length=2, max_length=2000)


@router.get("/mine")
def get_my_reviews(current_user: dict = Depends(get_current_user)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT r.review_id,r.order_item_id,r.product_id,r.rating,r.review_txt,r.added_at,
                   p.product_name,oi.sku_snapshot,o.order_no
            FROM t5_product_reviews r
            INNER JOIN products p ON p.product_id=r.product_id
            INNER JOIN order_items oi ON oi.order_item_id=r.order_item_id
            INNER JOIN orders o ON o.order_id=oi.order_id
            WHERE r.user_id=:user_id
            ORDER BY r.added_at DESC,r.review_id DESC
        """), {"user_id":current_user["user_id"]}).mappings().all()
    return {"count":len(rows),"items":[dict(r) for r in rows]}


@router.patch("/{review_id}")
def update_my_review(review_id: str, payload: ReviewUpdate, current_user: dict = Depends(get_current_user)):
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE t5_product_reviews SET rating=:rating,review_txt=:review_txt
            WHERE review_id=:review_id AND user_id=:user_id
        """), {"rating":payload.rating,"review_txt":payload.review_txt.strip(),"review_id":review_id,"user_id":current_user["user_id"]})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="본인이 작성한 리뷰를 찾을 수 없습니다.")
    return {"message":"리뷰가 수정되었습니다."}


@router.delete("/{review_id}")
def delete_my_review(review_id: str, current_user: dict = Depends(get_current_user)):
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM t5_product_reviews WHERE review_id=:id AND user_id=:user_id"), {"id":review_id,"user_id":current_user["user_id"]})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="본인이 작성한 리뷰를 찾을 수 없습니다.")
    return {"message":"리뷰가 삭제되었습니다. 배송완료 구매건이면 다시 작성할 수 있습니다."}
