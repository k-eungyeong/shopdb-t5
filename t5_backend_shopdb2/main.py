from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from database import engine
from routers import cart, review, wishlist


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    # 3306은 MySQL 포트입니다. Vite React 개발 서버는 보통 5173을 사용합니다.
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cart.router)
app.include_router(wishlist.router)
app.include_router(review.router)


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT COUNT(*) FROM t5_carts")
        )
        count = result.scalar()

    return {"t5_carts_row_count": count}
