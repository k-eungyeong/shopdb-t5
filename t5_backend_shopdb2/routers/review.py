from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from database import engine


# 이 파일의 API 주소는 모두 /reviews로 시작합니다.
router = APIRouter(prefix="/reviews", tags=["reviews"])


# 리뷰 등록 시 프론트엔드에서 보내는 데이터 형태입니다.
class ReviewCreate(BaseModel):
    order_item_id: int
    user_id: int
    product_id: int
    rating: int = Field(ge=1, le=5)
    review_txt: str = Field(min_length=1, max_length=5000)


# 리뷰 수정 시 보내는 데이터 형태입니다.
class ReviewUpdate(BaseModel):
    user_id: int
    rating: int = Field(ge=1, le=5)
    review_txt: str = Field(min_length=1, max_length=5000)


# 리뷰 등록: POST /reviews
@router.post("", status_code=201)
def create_review(item: ReviewCreate):
    if not item.review_txt.strip():
        raise HTTPException(status_code=422, detail="리뷰 내용을 입력하세요.")

    with engine.connect() as conn:
        # 주문상품, 주문자, 상품이 실제로 서로 일치하는지 확인합니다.
        # 프론트엔드가 잘못된 user_id나 product_id를 보내도 등록되지 않습니다.
        order_item = conn.execute(
            text("""
               SELECT
                  oi.order_item_id,
                  oi.product_id,
                  o.buyer_user_id
                FROM order_items AS oi
                INNER JOIN orders AS o
                    ON o.order_id = oi.order_id
                WHERE oi.order_item_id = :order_item_id
            """),
            {"order_item_id": item.order_item_id},
        ).mappings().first()

        if order_item is None:
            raise HTTPException(
                status_code=404,
                detail="주문상품을 찾을 수 없습니다.",
            )

        if order_item["buyer_user_id"] != item.user_id:
            raise HTTPException(
                status_code=403,
                detail="해당 주문상품의 구매자만 리뷰를 작성할 수 있습니다.",
            )

        if order_item["product_id"] != item.product_id:
            raise HTTPException(
                status_code=400,
                detail="주문상품과 리뷰 상품이 일치하지 않습니다.",
            )

        # 배송 상태(배송중/배송완료/구매확정)는 확인하지 않습니다.
        # order_items에 실제 구매 내역이 존재하고,
        # 구매자(user_id)와 상품(product_id)이 일치하면 구매 직후 바로 리뷰를 작성할 수 있습니다.

        # order_item_id에는 UNIQUE 제약조건이 있으므로 중복 여부를 먼저 확인합니다.
        existing = conn.execute(
            text("""
                SELECT review_id
                FROM t5_product_reviews
                WHERE order_item_id = :order_item_id
            """),
            {"order_item_id": item.order_item_id},
        ).first()

        if existing is not None:
            raise HTTPException(
                status_code=409,
                detail="이 주문상품에는 이미 리뷰가 등록되어 있습니다.",
            )

        try:
            # review_id는 trg_t5_reviews_pk 트리거가 자동으로 생성합니다.
            conn.execute(
                text("""
                    INSERT INTO t5_product_reviews (
                        order_item_id,
                        user_id,
                        product_id,
                        rating,
                        review_txt
                    )
                    VALUES (
                        :order_item_id,
                        :user_id,
                        :product_id,
                        :rating,
                        :review_txt
                    )
                """),
                {
                    "order_item_id": item.order_item_id,
                    "user_id": item.user_id,
                    "product_id": item.product_id,
                    "rating": item.rating,
                    "review_txt": item.review_txt.strip(),
                },
            )
            conn.commit()
        except IntegrityError:
            conn.rollback()
            raise HTTPException(
                status_code=409,
                detail="리뷰를 등록할 수 없습니다. 중복 리뷰 또는 참조 데이터를 확인하세요.",
            )

        # 트리거가 만든 review_id를 order_item_id로 다시 조회합니다.
        created = conn.execute(
            text("""
                SELECT
                    r.review_id,
                    r.order_item_id,
                    r.user_id,
                    u.user_name,
                    r.product_id,
                    p.product_name,
                    r.rating,
                    r.review_txt,
                    r.added_at
                FROM t5_product_reviews AS r
                INNER JOIN users AS u ON u.user_id = r.user_id
                INNER JOIN products AS p ON p.product_id = r.product_id
                WHERE r.order_item_id = :order_item_id
            """),
            {"order_item_id": item.order_item_id},
        ).mappings().first()

    return {
        "message": "리뷰가 등록되었습니다.",
        "review": dict(created),
    }


# 리뷰 전체 조회: GET /reviews?page=1&size=10
@router.get("")
def get_reviews(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
):
    offset = (page - 1) * size

    with engine.connect() as conn:
        total = conn.execute(
            text("SELECT COUNT(*) FROM t5_product_reviews")
        ).scalar_one()

        rows = conn.execute(
            text("""
                SELECT
                    r.review_id,
                    r.order_item_id,
                    r.user_id,
                    u.user_name,
                    r.product_id,
                    p.product_name,
                    r.rating,
                    r.review_txt,
                    r.added_at
                FROM t5_product_reviews AS r
                INNER JOIN users AS u ON u.user_id = r.user_id
                INNER JOIN products AS p ON p.product_id = r.product_id
                ORDER BY r.added_at DESC, r.review_id DESC
                LIMIT :size OFFSET :offset
            """),
            {"size": size, "offset": offset},
        ).mappings().all()

    return {
        "page": page,
        "size": size,
        "total": total,
        "items": [dict(row) for row in rows],
    }


# 상품별 리뷰 조회와 평균 평점: GET /reviews/product/1
@router.get("/product/{product_id}")
def get_product_reviews(
    product_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
):
    offset = (page - 1) * size

    with engine.connect() as conn:
        product = conn.execute(
            text("""
                SELECT product_id, product_name
                FROM products
                WHERE product_id = :product_id
            """),
            {"product_id": product_id},
        ).mappings().first()

        if product is None:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

        summary = conn.execute(
            text("""
                SELECT
                    COUNT(*) AS review_count,
                    COALESCE(ROUND(AVG(rating), 1), 0.0) AS average_rating
                FROM t5_product_reviews
                WHERE product_id = :product_id
            """),
            {"product_id": product_id},
        ).mappings().one()

        rows = conn.execute(
            text("""
                SELECT
                    r.review_id,
                    r.order_item_id,
                    r.user_id,
                    u.user_name,
                    r.product_id,
                    r.rating,
                    r.review_txt,
                    r.added_at
                FROM t5_product_reviews AS r
                INNER JOIN users AS u ON u.user_id = r.user_id
                WHERE r.product_id = :product_id
                ORDER BY r.added_at DESC, r.review_id DESC
                LIMIT :size OFFSET :offset
            """),
            {"product_id": product_id, "size": size, "offset": offset},
        ).mappings().all()

    return {
        "product": dict(product),
        "review_count": summary["review_count"],
        "average_rating": float(summary["average_rating"]),
        "page": page,
        "size": size,
        "items": [dict(row) for row in rows],
    }


# 리뷰 한 건 상세 조회: GET /reviews/RV_000001
# 고정 주소인 /product/{product_id}보다 아래에 두어 경로 충돌을 방지합니다.
@router.get("/{review_id}")
def get_review(review_id: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT
                    r.review_id,
                    r.order_item_id,
                    r.user_id,
                    u.user_name,
                    r.product_id,
                    p.product_name,
                    r.rating,
                    r.review_txt,
                    r.added_at
                FROM t5_product_reviews AS r
                INNER JOIN users AS u ON u.user_id = r.user_id
                INNER JOIN products AS p ON p.product_id = r.product_id
                WHERE r.review_id = :review_id
            """),
            {"review_id": review_id},
        ).mappings().first()

    if row is None:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")

    return {"review": dict(row)}


# 리뷰 수정: PATCH /reviews/RV_000001
@router.patch("/{review_id}")
def update_review(review_id: str, item: ReviewUpdate):
    if not item.review_txt.strip():
        raise HTTPException(status_code=422, detail="리뷰 내용을 입력하세요.")

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                UPDATE t5_product_reviews
                SET rating = :rating,
                    review_txt = :review_txt
                WHERE review_id = :review_id
                  AND user_id = :user_id
            """),
            {
                "review_id": review_id,
                "user_id": item.user_id,
                "rating": item.rating,
                "review_txt": item.review_txt.strip(),
            },
        )
        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="리뷰가 없거나 작성자가 일치하지 않습니다.",
            )

        updated = conn.execute(
            text("""
                SELECT review_id, order_item_id, user_id, product_id,
                       rating, review_txt, added_at
                FROM t5_product_reviews
                WHERE review_id = :review_id
            """),
            {"review_id": review_id},
        ).mappings().first()

    return {
        "message": "리뷰가 수정되었습니다.",
        "review": dict(updated),
    }


# 리뷰 삭제: DELETE /reviews/RV_000001?user_id=4
@router.delete("/{review_id}")
def delete_review(review_id: str, user_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                DELETE FROM t5_product_reviews
                WHERE review_id = :review_id
                  AND user_id = :user_id
            """),
            {"review_id": review_id, "user_id": user_id},
        )
        conn.commit()

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="리뷰가 없거나 작성자가 일치하지 않습니다.",
            )

    return {
        "message": "리뷰가 삭제되었습니다.",
        "review_id": review_id,
    }
