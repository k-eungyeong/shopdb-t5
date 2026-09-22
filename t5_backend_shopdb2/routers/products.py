from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from database import engine

router = APIRouter(prefix="/products", tags=["products"])


PRODUCT_LIST_BASE = """
    SELECT
        p.product_id, p.seller_user_id, p.category_id, c.category_name,
        p.product_code, p.product_name, p.short_description, p.description,
        p.regular_price, p.sale_price, p.product_status, p.created_at, p.updated_at,
        (SELECT COALESCE(f.thumbnail_url, f.public_url)
           FROM product_images pi INNER JOIN file_assets f ON f.file_id=pi.file_id
          WHERE pi.product_id=p.product_id AND pi.active_yn='Y'
          ORDER BY (pi.image_type='MAIN') DESC, pi.display_order, pi.product_image_id LIMIT 1) AS image,
        COALESCE((SELECT SUM(GREATEST(i.stock_quantity-i.reserved_quantity,0))
                    FROM product_variants pv LEFT JOIN inventories i ON i.variant_id=pv.variant_id
                   WHERE pv.product_id=p.product_id AND pv.active_yn='Y'),0) AS available_stock,
        COALESCE((SELECT ROUND(AVG(r.rating),1) FROM t5_product_reviews r WHERE r.product_id=p.product_id),0) AS avg_rating,
        (SELECT COUNT(*) FROM t5_product_reviews r WHERE r.product_id=p.product_id) AS review_count,
        COALESCE((SELECT SUM(oi.quantity) FROM order_items oi
                   WHERE oi.product_id=p.product_id AND oi.item_status IN ('PAID','PREPARING','SHIPPING','DELIVERED','COMPLETED')),0) AS sales_count
    FROM products p
    INNER JOIN categories c ON c.category_id=p.category_id
    WHERE p.product_status <> 'DELETED'
      AND (:category_id IS NULL OR p.category_id=:category_id)
      AND (:keyword='' OR p.product_name LIKE :keyword_like OR COALESCE(p.short_description,'') LIKE :keyword_like)
      AND (:min_price IS NULL OR p.sale_price>=:min_price)
      AND (:max_price IS NULL OR p.sale_price<=:max_price)
"""

SORT_SQL = {
    "latest": "p.created_at DESC, p.product_id DESC",
    "price_low": "p.sale_price ASC, p.product_id DESC",
    "price_high": "p.sale_price DESC, p.product_id DESC",
    "rating": "avg_rating DESC, review_count DESC, p.product_id DESC",
    "reviews": "review_count DESC, avg_rating DESC, p.product_id DESC",
    "sales": "sales_count DESC, review_count DESC, p.product_id DESC",
    "stock": "available_stock DESC, p.product_id DESC",
}


@router.get("")
def get_products(
    keyword: str = Query(default="", max_length=100),
    category_id: int | None = None,
    sort: str = Query(default="latest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=60),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="최소 가격은 최대 가격보다 클 수 없습니다.")
    order_by = SORT_SQL.get(sort, SORT_SQL["latest"])
    params = {
        "keyword": keyword.strip(), "keyword_like": f"%{keyword.strip()}%",
        "category_id": category_id, "min_price": min_price, "max_price": max_price,
    }
    count_sql = text("""
        SELECT COUNT(*) AS total FROM products p
        WHERE p.product_status <> 'DELETED'
          AND (:category_id IS NULL OR p.category_id=:category_id)
          AND (:keyword='' OR p.product_name LIKE :keyword_like OR COALESCE(p.short_description,'') LIKE :keyword_like)
          AND (:min_price IS NULL OR p.sale_price>=:min_price)
          AND (:max_price IS NULL OR p.sale_price<=:max_price)
    """)
    offset = (page-1)*page_size
    with engine.connect() as conn:
        total = conn.execute(count_sql, params).scalar_one()
        rows = conn.execute(text(PRODUCT_LIST_BASE + f" ORDER BY {order_by} LIMIT :limit OFFSET :offset"),
                            {**params, "limit": page_size, "offset": offset}).mappings().all()
    items=[]
    for row in rows:
        item=dict(row)
        item["is_sold_out"] = int(item.get("available_stock") or 0) <= 0
        items.append(item)
    return {
        "count": len(items), "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1)//page_size), "sort": sort, "items": items,
    }


@router.get("/categories")
def get_categories():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT category_id, parent_category_id, category_name, category_level, display_order
            FROM categories
            WHERE active_yn = 'Y'
            ORDER BY category_level, display_order, category_id
        """)).mappings().all()
    return {"items": [dict(row) for row in rows]}


@router.get("/{product_id}")
def get_product(product_id: int):
    with engine.connect() as conn:
        product = conn.execute(text("""
            SELECT
                p.product_id,
                p.seller_user_id,
                p.category_id,
                c.category_name,
                p.product_code,
                p.product_name,
                p.short_description,
                p.description,
                p.regular_price,
                p.sale_price,
                p.product_status,
                p.created_at,
                p.updated_at,
                (
                    SELECT COALESCE(f.public_url, f.thumbnail_url)
                    FROM product_images pi
                    INNER JOIN file_assets f ON f.file_id = pi.file_id
                    WHERE pi.product_id = p.product_id
                      AND pi.active_yn = 'Y'
                    ORDER BY (pi.image_type = 'MAIN') DESC, pi.display_order ASC, pi.product_image_id ASC
                    LIMIT 1
                ) AS image
            FROM products p
            INNER JOIN categories c ON c.category_id = p.category_id
            WHERE p.product_id = :product_id
              AND p.product_status <> 'DELETED'
        """), {"product_id": product_id}).mappings().first()

        if product is None:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

        variants = conn.execute(text("""
            SELECT
                pv.variant_id,
                pv.sku_code,
                pv.option_name1,
                pv.option_value1,
                pv.option_name2,
                pv.option_value2,
                pv.additional_price,
                COALESCE(SUM(GREATEST(i.stock_quantity - i.reserved_quantity, 0)), 0) AS available_stock
            FROM product_variants pv
            LEFT JOIN inventories i ON i.variant_id = pv.variant_id
            WHERE pv.product_id = :product_id
              AND pv.active_yn = 'Y'
            GROUP BY
                pv.variant_id, pv.sku_code, pv.option_name1, pv.option_value1,
                pv.option_name2, pv.option_value2, pv.additional_price
            ORDER BY pv.variant_id
        """), {"product_id": product_id}).mappings().all()

        reviews = conn.execute(text("""
            SELECT
                r.review_id,
                r.order_item_id,
                r.user_id,
                u.user_name,
                r.rating,
                r.review_txt,
                r.added_at
            FROM t5_product_reviews r
            INNER JOIN users u ON u.user_id = r.user_id
            WHERE r.product_id = :product_id
            ORDER BY r.added_at DESC, r.review_id DESC
        """), {"product_id": product_id}).mappings().all()

        rating = conn.execute(text("""
            SELECT ROUND(AVG(rating), 1) AS avg_rating, COUNT(*) AS review_count
            FROM t5_product_reviews
            WHERE product_id = :product_id
        """), {"product_id": product_id}).mappings().first()

    return {
        **dict(product),
        "variants": [dict(row) for row in variants],
        "reviews": [dict(row) for row in reviews],
        "avg_rating": rating["avg_rating"] or 0,
        "review_count": rating["review_count"],
    }
