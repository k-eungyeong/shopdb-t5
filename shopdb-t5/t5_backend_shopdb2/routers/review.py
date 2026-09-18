"""상품 리뷰 API.

리뷰 작성은 회원과 비회원 모두 가능합니다. JWT가 있으면 회원으로 확인하고,
토큰이 없으면 Body의 order_no와 receiver_phone으로 비회원 주문을 인증합니다.
"""

from datetime import datetime
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from auth.dependencies import CurrentUser, get_current_user, get_optional_current_user
from database import engine


router = APIRouter(prefix="/api", tags=["reviews"])


# ---------------------------------------------------------------------------
# 요청/응답 데이터 형식(Pydantic 스키마)
# ---------------------------------------------------------------------------
class ReviewCreate(BaseModel):
    """리뷰 등록 요청."""

    order_no: str | None = Field(default=None, max_length=40, description="비회원 주문번호")
    receiver_phone: str | None = Field(default=None, max_length=30, description="비회원 수령인 전화번호")
    order_item_id: int = Field(gt=0, description="주문 상품 번호")
    product_id: int = Field(gt=0, description="상품 번호")
    rating: int = Field(ge=1, le=5, description="평점(1~5)")
    review_txt: str = Field(min_length=1, max_length=5000, description="리뷰 내용")

class ReviewUpdate(BaseModel):
    """회원은 JWT, 비회원은 주문번호와 수령인 전화번호로 수정 권한을 확인합니다."""

    order_no: str | None = Field(default=None, max_length=40)
    receiver_phone: str | None = Field(default=None, max_length=30)
    rating: int | None = Field(default=None, ge=1, le=5)
    review_txt: str | None = Field(default=None, min_length=1, max_length=5000)

    @model_validator(mode="after")
    def check_update_value(self):
        if self.rating is None and self.review_txt is None:
            raise ValueError("rating 또는 review_txt 중 하나 이상 입력해야 합니다.")
        return self


class ReviewResponse(BaseModel):
    """리뷰 한 건 응답."""

    review_id: str
    order_item_id: int
    user_id: int | None
    product_id: int
    rating: int
    review_txt: str
    added_at: datetime


class ReviewListResponse(BaseModel):
    """페이지 정보가 포함된 리뷰 목록 응답."""

    items: list[ReviewResponse]
    page: int
    size: int
    total_items: int
    total_pages: int


class RatingDistribution(BaseModel):
    rating_5: int
    rating_4: int
    rating_3: int
    rating_2: int
    rating_1: int


class ReviewSummaryResponse(BaseModel):
    product_id: int
    average_rating: float
    review_count: int
    rating_distribution: RatingDistribution


# ---------------------------------------------------------------------------
# 내부 공통 함수
# ---------------------------------------------------------------------------
REVIEW_SELECT = """
    SELECT review_id, order_item_id, user_id, product_id,
           rating, review_txt, added_at
    FROM t5_product_reviews
"""


def _get_review(conn, review_id: str) -> dict | None:
    """리뷰 번호로 한 건을 조회하고, 없으면 None을 반환합니다."""

    row = conn.execute(
        text(REVIEW_SELECT + " WHERE review_id = :review_id"),
        {"review_id": review_id},
    ).mappings().first()
    return dict(row) if row else None


def _verify_purchased_order_item(
    conn,
    order_item_id: int,
    product_id: int,
    current_user: CurrentUser | None,
    order_no: str | None = None,
    receiver_phone: str | None = None,
) -> None:
    """주문상품·상품·구매자·배송완료 상태를 리뷰 저장 전에 확인합니다."""

    purchase = conn.execute(
        text(
            """
            SELECT o.buyer_user_id,
                   o.order_no,
                   o.order_status,
                   oi.item_status,
                   oi.product_id,
                   o.receiver_phone
            FROM order_items oi
            JOIN orders o ON o.order_id = oi.order_id
            WHERE oi.order_item_id = :order_item_id
            """
        ),
        {"order_item_id": order_item_id},
    ).mappings().first()

    if purchase is None:
        raise HTTPException(status_code=404, detail="주문 상품을 찾을 수 없습니다.")

    if purchase["product_id"] != product_id:
        raise HTTPException(
            status_code=400,
            detail="주문 상품과 리뷰 대상 상품이 일치하지 않습니다.",
        )

    # 첨부 DB에는 완료 상태가 COMPLETED이고, 향후 배송완료 상태는 DELIVERED를
    # 사용할 수 있으므로 두 값을 모두 실제 구매 완료 상태로 허용합니다.
    completed_statuses = {"DELIVERED", "COMPLETED"}
    if (
        purchase["order_status"] not in completed_statuses
        or purchase["item_status"] not in completed_statuses
    ):
        raise HTTPException(
            status_code=400,
            detail="배송이 완료된 구매 상품에만 리뷰를 작성할 수 있습니다.",
        )

    buyer_user_id = purchase["buyer_user_id"]
    if current_user is not None:
        if buyer_user_id != current_user.user_id:
            raise HTTPException(
                status_code=403,
                detail="로그인 회원과 해당 주문의 구매자가 일치하지 않습니다.",
            )
    else:
        if buyer_user_id is not None:
            raise HTTPException(
                status_code=403,
                detail="회원 주문의 리뷰를 작성하려면 로그인해야 합니다.",
            )
        normalized_input_phone = re.sub(r"\D", "", receiver_phone or "")
        normalized_order_phone = re.sub(r"\D", "", purchase["receiver_phone"] or "")
        if (
            not order_no
            or purchase["order_no"] != order_no.strip()
            or not normalized_input_phone
            or normalized_input_phone != normalized_order_phone
        ):
            raise HTTPException(
                status_code=403,
                detail="주문번호 또는 주문 전화번호가 일치하지 않습니다.",
            )


def _raise_integrity_error(exc: IntegrityError) -> None:
    """MySQL 제약조건 오류를 사용자가 이해하기 쉬운 HTTP 오류로 변환합니다."""

    message = str(exc.orig).lower()

    if "uq_t5_pr_order_item" in message or "duplicate entry" in message:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="해당 주문 상품에는 이미 리뷰가 등록되어 있습니다.",
        ) from exc

    if "foreign key constraint fails" in message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="존재하지 않는 사용자, 상품 또는 주문 상품 번호입니다.",
        ) from exc

    if "chk_t5_pr_string_rating" in message or "check constraint" in message:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="평점은 1점부터 5점까지만 입력할 수 있습니다.",
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="리뷰를 저장하는 중 데이터베이스 오류가 발생했습니다.",
    ) from exc


# ---------------------------------------------------------------------------
# 리뷰 CRUD API
# ---------------------------------------------------------------------------
@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="리뷰 작성",
)
def create_review(
    payload: ReviewCreate,
    current_user: CurrentUser | None = Depends(get_optional_current_user),
):
    """회원 또는 비회원이 실제 구매한 상품에 리뷰를 등록합니다.

    review_id는 현재 테이블 형식에 맞춰 RV_000001 형태로 자동 생성됩니다.
    order_item_id에는 UNIQUE 제약조건이 있어 주문 상품 하나당 리뷰 하나만
    등록할 수 있습니다. 회원은 JWT의 user_id를, 비회원은 NULL을 저장합니다.
    """

    review_txt = payload.review_txt.strip()
    if not review_txt:
        raise HTTPException(status_code=422, detail="리뷰 내용을 입력해 주세요.")

    try:
        with engine.begin() as conn:
            # 회원·비회원 모두 주문상품이 실제 구매·배송 완료된 상품인지 확인합니다.
            _verify_purchased_order_item(
                conn,
                payload.order_item_id,
                payload.product_id,
                current_user,
                payload.order_no,
                payload.receiver_phone,
            )

            # 기존 문자열 번호의 가장 큰 숫자 부분을 찾아 다음 번호를 만듭니다.
            # 예: RV_000005 다음은 RV_000006
            review_id = conn.execute(
                text(
                    """
                    SELECT CONCAT(
                        'RV_',
                        LPAD(
                            COALESCE(MAX(CAST(SUBSTRING_INDEX(review_id, '_', -1)
                                AS UNSIGNED)), 0) + 1,
                            6,
                            '0'
                        )
                    )
                    FROM t5_product_reviews
                    """
                )
            ).scalar_one()

            conn.execute(
                text(
                    """
                    INSERT INTO t5_product_reviews
                        (review_id, order_item_id, user_id, product_id,
                         rating, review_txt)
                    VALUES
                        (:review_id, :order_item_id, :user_id, :product_id,
                         :rating, :review_txt)
                    """
                ),
                {
                    "review_id": review_id,
                    "order_item_id": payload.order_item_id,
                    # 회원은 JWT의 사용자 번호, 비회원은 NULL을 저장합니다.
                    "user_id": current_user.user_id if current_user else None,
                    "product_id": payload.product_id,
                    "rating": payload.rating,
                    "review_txt": review_txt,
                },
            )

            review = _get_review(conn, review_id)
    except IntegrityError as exc:
        _raise_integrity_error(exc)

    return review


@router.get(
    "/products/{product_id}/reviews",
    response_model=ReviewListResponse,
    summary="상품별 리뷰 목록 조회",
)
def get_product_reviews(
    product_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    sort: Literal["latest", "rating_desc", "rating_asc"] = "latest",
):
    """특정 상품의 리뷰를 정렬 및 페이지 단위로 조회합니다."""

    order_by = {
        "latest": "added_at DESC, review_id DESC",
        "rating_desc": "rating DESC, added_at DESC",
        "rating_asc": "rating ASC, added_at DESC",
    }[sort]
    offset = (page - 1) * size

    with engine.connect() as conn:
        total_items = conn.execute(
            text(
                "SELECT COUNT(*) FROM t5_product_reviews "
                "WHERE product_id = :product_id"
            ),
            {"product_id": product_id},
        ).scalar_one()

        # ORDER BY는 위의 허용 목록에서만 선택되므로 사용자 입력이 SQL에
        # 직접 들어가지 않습니다.
        rows = conn.execute(
            text(
                REVIEW_SELECT
                + f" WHERE product_id = :product_id ORDER BY {order_by} "
                + "LIMIT :size OFFSET :offset"
            ),
            {"product_id": product_id, "size": size, "offset": offset},
        ).mappings().all()

    return {
        "items": [dict(row) for row in rows],
        "page": page,
        "size": size,
        "total_items": total_items,
        "total_pages": (total_items + size - 1) // size,
    }


@router.get(
    "/products/{product_id}/reviews/summary",
    response_model=ReviewSummaryResponse,
    summary="상품 리뷰 평점 통계",
)
def get_review_summary(product_id: int):
    """상품의 평균 평점, 리뷰 수, 점수별 리뷰 수를 반환합니다."""

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT COUNT(*) AS review_count,
                       COALESCE(ROUND(AVG(rating), 2), 0) AS average_rating,
                       SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) AS rating_5,
                       SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) AS rating_4,
                       SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) AS rating_3,
                       SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) AS rating_2,
                       SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS rating_1
                FROM t5_product_reviews
                WHERE product_id = :product_id
                """
            ),
            {"product_id": product_id},
        ).mappings().one()

    return {
        "product_id": product_id,
        "average_rating": float(row["average_rating"]),
        "review_count": row["review_count"],
        "rating_distribution": {
            "rating_5": row["rating_5"] or 0,
            "rating_4": row["rating_4"] or 0,
            "rating_3": row["rating_3"] or 0,
            "rating_2": row["rating_2"] or 0,
            "rating_1": row["rating_1"] or 0,
        },
    }


@router.get(
    "/users/me/reviews",
    response_model=ReviewListResponse,
    summary="사용자가 작성한 리뷰 조회",
)
def get_my_reviews(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    current_user: CurrentUser = Depends(get_current_user),
):
    """JWT로 확인된 현재 회원의 리뷰를 최신순으로 조회합니다."""

    user_id = current_user.user_id
    offset = (page - 1) * size
    with engine.connect() as conn:
        total_items = conn.execute(
            text("SELECT COUNT(*) FROM t5_product_reviews WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one()
        rows = conn.execute(
            text(
                REVIEW_SELECT
                + " WHERE user_id = :user_id "
                + "ORDER BY added_at DESC, review_id DESC "
                + "LIMIT :size OFFSET :offset"
            ),
            {"user_id": user_id, "size": size, "offset": offset},
        ).mappings().all()

    return {
        "items": [dict(row) for row in rows],
        "page": page,
        "size": size,
        "total_items": total_items,
        "total_pages": (total_items + size - 1) // size,
    }


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="리뷰 상세 조회",
)
def get_review(review_id: str):
    """리뷰 번호로 리뷰 한 건을 조회합니다."""

    with engine.connect() as conn:
        review = _get_review(conn, review_id)

    if review is None:
        raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
    return review


@router.patch(
    "/reviews/{review_id}",
    response_model=ReviewResponse,
    summary="리뷰 수정",
)
def update_review(
    review_id: str,
    payload: ReviewUpdate,
    current_user: CurrentUser | None = Depends(get_optional_current_user),
):
    """작성자 본인의 평점 또는 리뷰 내용을 수정합니다."""

    with engine.begin() as conn:
        current = _get_review(conn, review_id)
        if current is None:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
        expected_user_id = current_user.user_id if current_user else None
        if current["user_id"] != expected_user_id:
            raise HTTPException(
                status_code=403,
                detail="리뷰 작성자 인증 정보가 일치하지 않습니다.",
            )

        _verify_purchased_order_item(
            conn,
            current["order_item_id"],
            current["product_id"],
            current_user,
            payload.order_no,
            payload.receiver_phone,
        )

        rating = payload.rating if payload.rating is not None else current["rating"]
        review_txt = (
            payload.review_txt.strip()
            if payload.review_txt is not None
            else current["review_txt"]
        )
        if not review_txt:
            raise HTTPException(status_code=422, detail="리뷰 내용을 입력해 주세요.")

        conn.execute(
            text(
                """
                UPDATE t5_product_reviews
                SET rating = :rating, review_txt = :review_txt
                WHERE review_id = :review_id
                """
            ),
            {
                "rating": rating,
                "review_txt": review_txt,
                "review_id": review_id,
            },
        )
        updated = _get_review(conn, review_id)

    return updated


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="리뷰 삭제",
)
def delete_review(
    review_id: str,
    order_no: str | None = Query(default=None, max_length=40, description="비회원 주문번호"),
    receiver_phone: str | None = Query(default=None, max_length=30, description="비회원 수령인 전화번호"),
    current_user: CurrentUser | None = Depends(get_optional_current_user),
):
    """작성자 본인의 리뷰를 삭제합니다."""

    with engine.begin() as conn:
        current = _get_review(conn, review_id)
        if current is None:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
        expected_user_id = current_user.user_id if current_user else None
        if current["user_id"] != expected_user_id:
            raise HTTPException(
                status_code=403,
                detail="리뷰 작성자 인증 정보가 일치하지 않습니다.",
            )

        _verify_purchased_order_item(
            conn,
            current["order_item_id"],
            current["product_id"],
            current_user,
            order_no,
            receiver_phone,
        )

        conn.execute(
            text("DELETE FROM t5_product_reviews WHERE review_id = :review_id"),
            {"review_id": review_id},
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
