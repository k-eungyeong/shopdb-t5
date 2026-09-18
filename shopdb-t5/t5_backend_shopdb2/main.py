from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine
from routers import cart, review, wishlist


# FastAPI 애플리케이션은 한 번만 생성합니다.
app = FastAPI(
    title="ShopDB2 API",
    description="T5 쇼핑몰 백엔드 API",
    version="0.1.0",
)


# React 프론트엔드의 요청을 허용합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 장바구니, 리뷰, 찜 목록 라우터를 등록합니다.
app.include_router(cart.router)
app.include_router(review.router)
app.include_router(wishlist.router)


# 서버 실행 여부 확인
@app.get("/", tags=["System"])
def health_check():
    return {"status": "ok"}


# MySQL 연결 여부 확인
@app.get("/db-test", tags=["System"])
def db_test():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM t5_carts")
        )
        count = result.scalar()

    return {"t5_carts_row_count": count}