from fastapi import FastAPI
from sqlalchemy import text
from database import engine
from routers import cart, review

app = FastAPI(
    title="ShopDB2 API",
    description="T5 쇼핑몰 백엔드 API",
    version="0.1.0",
)

app.include_router(cart.router)
app.include_router(review.router)

@app.get("/")
def health_check():
    return {"status": "ok"}

@app.get("/db-test")
def db_test():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM t5_carts"))
        count = result.scalar()
    return {"t5_carts_row_count": count}
