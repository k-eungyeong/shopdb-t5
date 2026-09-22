from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine
from routers import auth, cart, wishlist, products, orders, reviews, mypage, payments, admin_orders, admin_center, seller_center


app = FastAPI(
    title="ShopDB2 API",
    description="ShopDB2 FastAPI Backend",
    version="1.0.0"
)


# -------------------------------------------------
# CORS 설정
# React(Vite) 프론트엔드에서 FastAPI 백엔드로 요청할 수 있도록 허용
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,

    # Vite 개발 서버 주소
    # localhost와 127.0.0.1 둘 다 허용
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------
# Router 등록
# -------------------------------------------------
app.include_router(auth.router)
app.include_router(cart.router)
app.include_router(wishlist.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(reviews.router)
app.include_router(mypage.router)
app.include_router(payments.router)
app.include_router(admin_orders.router)
app.include_router(admin_center.router)
app.include_router(seller_center.router)


# -------------------------------------------------
# 백엔드 연결 확인 API
# 주소:
# http://127.0.0.1:8000/
# -------------------------------------------------
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "message": "ShopDB2 백엔드 연결 성공"
    }


# -------------------------------------------------
# MySQL DB 연결 테스트
# 주소:
# http://127.0.0.1:8000/db-test
# -------------------------------------------------
@app.get("/db-test")
def db_test():

    with engine.connect() as conn:

        result = conn.execute(
            text("SELECT COUNT(*) FROM t5_carts")
        )

        count = result.scalar()

    return {
        "status": "ok",
        "message": "MySQL 데이터베이스 연결 성공",
        "t5_carts_row_count": count
    }