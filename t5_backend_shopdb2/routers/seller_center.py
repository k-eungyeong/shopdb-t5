from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/seller", tags=["seller-center"])

PRODUCT_STATUSES = {"READY", "SALE", "SOLD_OUT", "STOPPED"}
SHIPPING_RANK = {"PAID": 0, "PREPARING": 1, "SHIPPING": 2, "DELIVERED": 3}
SHIPPING_TARGETS = {"PREPARING", "SHIPPING", "DELIVERED"}


def require_seller(current_user: dict = Depends(get_current_user)):
    if "SELLER" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="판매자 권한이 필요합니다.")
    with engine.connect() as conn:
        seller = conn.execute(text("""
            SELECT seller_id, company_name, seller_status, settlement_bank, settlement_account
            FROM seller_profiles WHERE user_id=:user_id
        """), {"user_id": current_user["user_id"]}).mappings().first()
    if seller is None:
        raise HTTPException(status_code=403, detail="판매자 프로필이 없습니다. 관리자에게 문의해주세요.")
    if seller["seller_status"] != "ACTIVE":
        raise HTTPException(status_code=403, detail="현재 판매 활동이 제한된 판매자 계정입니다.")
    result = dict(current_user)
    result["seller_profile"] = dict(seller)
    return result


class SellerProductCreate(BaseModel):
    category_id: int
    product_name: str = Field(min_length=1, max_length=200)
    short_description: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    regular_price: float = Field(ge=0)
    sale_price: float = Field(ge=0)
    product_status: str = "READY"
    sku_code: str | None = Field(default=None, max_length=100)
    option_name1: str | None = Field(default=None, max_length=100)
    option_value1: str | None = Field(default=None, max_length=100)
    option_name2: str | None = Field(default=None, max_length=100)
    option_value2: str | None = Field(default=None, max_length=100)
    additional_price: float = Field(default=0, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    safety_stock: int = Field(default=0, ge=0)


class SellerProductUpdate(BaseModel):
    category_id: int | None = None
    product_name: str | None = Field(default=None, min_length=1, max_length=200)
    short_description: str | None = Field(default=None, max_length=1000)
    description: str | None = None
    regular_price: float | None = Field(default=None, ge=0)
    sale_price: float | None = Field(default=None, ge=0)
    product_status: str | None = None


class VariantCreate(BaseModel):
    sku_code: str = Field(min_length=1, max_length=100)
    option_name1: str | None = Field(default=None, max_length=100)
    option_value1: str | None = Field(default=None, max_length=100)
    option_name2: str | None = Field(default=None, max_length=100)
    option_value2: str | None = Field(default=None, max_length=100)
    additional_price: float = Field(default=0, ge=0)
    stock_quantity: int = Field(default=0, ge=0)
    safety_stock: int = Field(default=0, ge=0)


class VariantUpdate(BaseModel):
    option_name1: str | None = None
    option_value1: str | None = None
    option_name2: str | None = None
    option_value2: str | None = None
    additional_price: float | None = Field(default=None, ge=0)
    active_yn: str | None = None
    stock_quantity: int | None = Field(default=None, ge=0)
    safety_stock: int | None = Field(default=None, ge=0)


class SellerShippingUpdate(BaseModel):
    status: str


class InquiryAnswer(BaseModel):
    answer_content: str = Field(min_length=2, max_length=5000)


def _validate_product_prices(regular_price, sale_price):
    if regular_price is not None and sale_price is not None and sale_price > regular_price:
        raise HTTPException(status_code=400, detail="판매가는 정상가보다 높을 수 없습니다.")


def _recalculate_order_status(conn, order_id: int):
    statuses = conn.execute(text("""
        SELECT item_status FROM order_items
        WHERE order_id=:order_id AND item_status NOT IN ('CANCELLED','REFUNDED')
    """), {"order_id": order_id}).scalars().all()
    if not statuses:
        return
    status_set = set(statuses)
    if status_set <= {"COMPLETED"}:
        target = "COMPLETED"
    elif status_set <= {"DELIVERED", "COMPLETED"}:
        target = "DELIVERED"
    elif status_set & {"SHIPPING", "DELIVERED", "COMPLETED"}:
        target = "SHIPPING"
    elif status_set & {"PREPARING"}:
        target = "PREPARING"
    elif status_set & {"PAID"}:
        target = "PAID"
    else:
        return
    conn.execute(text("UPDATE orders SET order_status=:status WHERE order_id=:order_id"),
                 {"status": target, "order_id": order_id})


@router.get("/dashboard")
def seller_dashboard(current_user: dict = Depends(require_seller)):
    seller_id = current_user["user_id"]
    with engine.connect() as conn:
        summary = conn.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM products WHERE seller_user_id=:seller_id AND product_status <> 'DELETED') AS product_count,
                (SELECT COUNT(DISTINCT oi.order_id) FROM order_items oi INNER JOIN products p ON p.product_id=oi.product_id
                 WHERE p.seller_user_id=:seller_id AND oi.item_status='PAID') AS paid_orders,
                (SELECT COUNT(DISTINCT oi.order_id) FROM order_items oi INNER JOIN products p ON p.product_id=oi.product_id
                 WHERE p.seller_user_id=:seller_id AND oi.item_status='PREPARING') AS preparing_orders,
                (SELECT COUNT(DISTINCT oi.order_id) FROM order_items oi INNER JOIN products p ON p.product_id=oi.product_id
                 WHERE p.seller_user_id=:seller_id AND oi.item_status='SHIPPING') AS shipping_orders,
                (SELECT COUNT(DISTINCT oi.order_id) FROM order_items oi INNER JOIN products p ON p.product_id=oi.product_id
                 WHERE p.seller_user_id=:seller_id AND oi.item_status IN ('DELIVERED','COMPLETED')) AS delivered_orders,
                (SELECT COALESCE(SUM(oi.item_amount),0) FROM order_items oi INNER JOIN products p ON p.product_id=oi.product_id
                 INNER JOIN orders o ON o.order_id=oi.order_id
                 WHERE p.seller_user_id=:seller_id AND oi.item_status IN ('DELIVERED','COMPLETED') AND DATE(o.ordered_at)=CURDATE()) AS today_sales,
                (SELECT COALESCE(SUM(oi.item_amount),0) FROM order_items oi INNER JOIN products p ON p.product_id=oi.product_id
                 INNER JOIN orders o ON o.order_id=oi.order_id
                 WHERE p.seller_user_id=:seller_id AND oi.item_status IN ('DELIVERED','COMPLETED')
                   AND DATE_FORMAT(o.ordered_at,'%Y-%m')=DATE_FORMAT(CURDATE(),'%Y-%m')) AS month_sales,
                (SELECT COALESCE(SUM(oi.item_amount),0) FROM order_items oi INNER JOIN products p ON p.product_id=oi.product_id
                 WHERE p.seller_user_id=:seller_id AND oi.item_status IN ('DELIVERED','COMPLETED')) AS completed_sales,
                (SELECT COUNT(*) FROM t5_product_reviews r INNER JOIN products p ON p.product_id=r.product_id
                 WHERE p.seller_user_id=:seller_id) AS review_count,
                (SELECT COUNT(*) FROM buyer_inquiries bi WHERE bi.org_id=:org_id AND bi.inquiry_status <> 'ANSWERED') AS pending_inquiries,
                (SELECT COUNT(*)
                   FROM inventories i INNER JOIN product_variants pv ON pv.variant_id=i.variant_id
                   INNER JOIN products p ON p.product_id=pv.product_id
                   WHERE p.seller_user_id=:seller_id AND pv.active_yn='Y'
                     AND GREATEST(i.stock_quantity-i.reserved_quantity,0) <= i.safety_stock) AS low_stock_variants
        """), {"seller_id": seller_id, "org_id": current_user.get("org_id")}).mappings().first()

        recent = conn.execute(text("""
            SELECT o.order_id, o.order_no, o.ordered_at, u.user_name AS buyer_name,
                   GROUP_CONCAT(oi.product_name_snapshot ORDER BY oi.order_item_id SEPARATOR ', ') AS product_names,
                   SUM(oi.item_amount) AS seller_amount,
                   GROUP_CONCAT(DISTINCT oi.item_status ORDER BY oi.item_status SEPARATOR ',') AS item_statuses
            FROM order_items oi
            INNER JOIN orders o ON o.order_id=oi.order_id
            INNER JOIN products p ON p.product_id=oi.product_id
            INNER JOIN users u ON u.user_id=o.buyer_user_id
            WHERE p.seller_user_id=:seller_id
            GROUP BY o.order_id, o.order_no, o.ordered_at, u.user_name
            ORDER BY o.ordered_at DESC, o.order_id DESC
            LIMIT 8
        """), {"seller_id": seller_id}).mappings().all()

        sales_trend = conn.execute(text("""
            WITH RECURSIVE dates AS (
                SELECT CURDATE() - INTERVAL 6 DAY AS d
                UNION ALL SELECT d + INTERVAL 1 DAY FROM dates WHERE d < CURDATE()
            )
            SELECT DATE_FORMAT(d.d,'%m-%d') AS label,
                   COALESCE((
                       SELECT SUM(oi.item_amount)
                       FROM order_items oi
                       INNER JOIN orders o ON o.order_id=oi.order_id
                       INNER JOIN products p ON p.product_id=oi.product_id
                       WHERE p.seller_user_id=:seller_id
                         AND oi.item_status IN ('DELIVERED','COMPLETED')
                         AND DATE(o.ordered_at)=d.d
                   ),0) AS sales
            FROM dates d ORDER BY d.d
        """), {"seller_id": seller_id}).mappings().all()

        low_stock = conn.execute(text("""
            SELECT p.product_id, p.product_name, pv.variant_id, pv.sku_code,
                   GREATEST(i.stock_quantity-i.reserved_quantity,0) AS available_stock, i.safety_stock
            FROM inventories i
            INNER JOIN product_variants pv ON pv.variant_id=i.variant_id
            INNER JOIN products p ON p.product_id=pv.product_id
            WHERE p.seller_user_id=:seller_id AND p.product_status <> 'DELETED' AND pv.active_yn='Y'
              AND GREATEST(i.stock_quantity-i.reserved_quantity,0) <= i.safety_stock
            ORDER BY available_stock ASC, p.product_id LIMIT 10
        """), {"seller_id": seller_id}).mappings().all()
    return {
        "summary": dict(summary),
        "recent_orders": [dict(row) for row in recent],
        "sales_trend": [dict(row) for row in sales_trend],
        "low_stock": [dict(row) for row in low_stock],
    }


@router.get("/products")
def seller_products(current_user: dict = Depends(require_seller)):
    with engine.connect() as conn:
        products = conn.execute(text("""
            SELECT p.product_id, p.product_code, p.product_name, p.short_description,
                   p.description, p.regular_price, p.sale_price, p.product_status,
                   p.category_id, c.category_name, p.created_at, p.updated_at
            FROM products p INNER JOIN categories c ON c.category_id=p.category_id
            WHERE p.seller_user_id=:seller_id AND p.product_status <> 'DELETED'
            ORDER BY p.created_at DESC, p.product_id DESC
        """), {"seller_id": current_user["user_id"]}).mappings().all()
        result = []
        for product in products:
            variants = conn.execute(text("""
                SELECT pv.variant_id, pv.sku_code, pv.option_name1, pv.option_value1,
                       pv.option_name2, pv.option_value2, pv.additional_price, pv.active_yn,
                       COALESCE(i.stock_quantity,0) AS stock_quantity,
                       COALESCE(i.reserved_quantity,0) AS reserved_quantity,
                       COALESCE(i.safety_stock,0) AS safety_stock
                FROM product_variants pv
                LEFT JOIN inventories i ON i.variant_id=pv.variant_id AND i.org_id=:org_id
                WHERE pv.product_id=:product_id
                ORDER BY pv.variant_id
            """), {"product_id": product["product_id"], "org_id": current_user.get("org_id")}).mappings().all()
            result.append({**dict(product), "variants": [dict(v) for v in variants]})
    return {"count": len(result), "items": result}


@router.post("/products", status_code=201)
def seller_create_product(payload: SellerProductCreate, current_user: dict = Depends(require_seller)):
    status = payload.product_status.strip().upper()
    if status not in PRODUCT_STATUSES:
        raise HTTPException(status_code=400, detail="올바르지 않은 상품 상태입니다.")
    _validate_product_prices(payload.regular_price, payload.sale_price)
    if current_user.get("org_id") is None:
        raise HTTPException(status_code=400, detail="판매자의 조직 정보가 없어 재고를 등록할 수 없습니다.")
    with engine.begin() as conn:
        category = conn.execute(text("SELECT 1 FROM categories WHERE category_id=:id AND active_yn='Y'"),
                                {"id": payload.category_id}).first()
        if not category:
            raise HTTPException(status_code=400, detail="사용할 수 없는 카테고리입니다.")
        product_code = f"P{datetime.now().strftime('%Y%m%d')}{uuid4().hex[:5].upper()}"
        result = conn.execute(text("""
            INSERT INTO products (seller_user_id, category_id, product_code, product_name,
                short_description, description, regular_price, sale_price, product_status)
            VALUES (:seller_id, :category_id, :product_code, :product_name,
                :short_description, :description, :regular_price, :sale_price, :product_status)
        """), {"seller_id": current_user["user_id"], "category_id": payload.category_id,
                "product_code": product_code, "product_name": payload.product_name.strip(),
                "short_description": payload.short_description, "description": payload.description,
                "regular_price": payload.regular_price, "sale_price": payload.sale_price,
                "product_status": status})
        product_id = result.lastrowid
        sku = (payload.sku_code or f"SKU-{product_code}-01").strip()
        try:
            vr = conn.execute(text("""
                INSERT INTO product_variants (product_id, sku_code, option_name1, option_value1,
                    option_name2, option_value2, additional_price, active_yn)
                VALUES (:product_id, :sku, :n1, :v1, :n2, :v2, :additional, 'Y')
            """), {"product_id": product_id, "sku": sku, "n1": payload.option_name1,
                    "v1": payload.option_value1, "n2": payload.option_name2,
                    "v2": payload.option_value2, "additional": payload.additional_price})
        except Exception as exc:
            raise HTTPException(status_code=409, detail="이미 사용 중인 SKU 코드입니다.") from exc
        conn.execute(text("""
            INSERT INTO inventories (org_id, variant_id, stock_quantity, reserved_quantity, safety_stock)
            VALUES (:org_id, :variant_id, :stock, 0, :safety)
        """), {"org_id": current_user["org_id"], "variant_id": vr.lastrowid,
                "stock": payload.stock_quantity, "safety": payload.safety_stock})
    return {"message": "상품이 등록되었습니다.", "product_id": product_id, "product_code": product_code}


@router.patch("/products/{product_id}")
def seller_update_product(product_id: int, payload: SellerProductUpdate, current_user: dict = Depends(require_seller)):
    data = payload.model_dump(exclude_none=True)
    if "product_status" in data:
        data["product_status"] = data["product_status"].strip().upper()
        if data["product_status"] not in PRODUCT_STATUSES:
            raise HTTPException(status_code=400, detail="올바르지 않은 상품 상태입니다.")
    with engine.begin() as conn:
        product = conn.execute(text("""
            SELECT regular_price, sale_price FROM products
            WHERE product_id=:product_id AND seller_user_id=:seller_id AND product_status <> 'DELETED'
        """), {"product_id": product_id, "seller_id": current_user["user_id"]}).mappings().first()
        if not product:
            raise HTTPException(status_code=404, detail="본인의 상품을 찾을 수 없습니다.")
        if "category_id" in data:
            exists = conn.execute(text("SELECT 1 FROM categories WHERE category_id=:id AND active_yn='Y'"), {"id": data["category_id"]}).first()
            if not exists:
                raise HTTPException(status_code=400, detail="사용할 수 없는 카테고리입니다.")
        regular = data.get("regular_price", product["regular_price"])
        sale = data.get("sale_price", product["sale_price"])
        _validate_product_prices(float(regular), float(sale))
        fields, params = [], {"product_id": product_id, "seller_id": current_user["user_id"]}
        for key, value in data.items():
            fields.append(f"{key}=:{key}")
            params[key] = value.strip() if isinstance(value, str) else value
        if not fields:
            raise HTTPException(status_code=400, detail="변경할 값이 없습니다.")
        conn.execute(text(f"UPDATE products SET {', '.join(fields)} WHERE product_id=:product_id AND seller_user_id=:seller_id"), params)
    return {"message": "상품이 수정되었습니다."}


@router.delete("/products/{product_id}")
def seller_delete_product(product_id: int, current_user: dict = Depends(require_seller)):
    with engine.begin() as conn:
        result = conn.execute(text("""
            UPDATE products SET product_status='DELETED'
            WHERE product_id=:product_id AND seller_user_id=:seller_id AND product_status <> 'DELETED'
        """), {"product_id": product_id, "seller_id": current_user["user_id"]})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="본인의 상품을 찾을 수 없습니다.")
        conn.execute(text("UPDATE product_variants SET active_yn='N' WHERE product_id=:product_id"), {"product_id": product_id})
    return {"message": "상품이 판매 목록에서 삭제되었습니다."}


@router.post("/products/{product_id}/variants", status_code=201)
def seller_create_variant(product_id: int, payload: VariantCreate, current_user: dict = Depends(require_seller)):
    if current_user.get("org_id") is None:
        raise HTTPException(status_code=400, detail="판매자 조직 정보가 없습니다.")
    with engine.begin() as conn:
        owner = conn.execute(text("SELECT 1 FROM products WHERE product_id=:pid AND seller_user_id=:sid AND product_status <> 'DELETED'"),
                             {"pid": product_id, "sid": current_user["user_id"]}).first()
        if not owner:
            raise HTTPException(status_code=404, detail="본인의 상품을 찾을 수 없습니다.")
        try:
            result = conn.execute(text("""
                INSERT INTO product_variants (product_id, sku_code, option_name1, option_value1,
                    option_name2, option_value2, additional_price, active_yn)
                VALUES (:pid, :sku, :n1, :v1, :n2, :v2, :price, 'Y')
            """), {"pid": product_id, "sku": payload.sku_code.strip(), "n1": payload.option_name1,
                    "v1": payload.option_value1, "n2": payload.option_name2,
                    "v2": payload.option_value2, "price": payload.additional_price})
        except Exception as exc:
            raise HTTPException(status_code=409, detail="이미 사용 중인 SKU 코드입니다.") from exc
        conn.execute(text("""
            INSERT INTO inventories (org_id, variant_id, stock_quantity, reserved_quantity, safety_stock)
            VALUES (:org, :variant, :stock, 0, :safety)
        """), {"org": current_user["org_id"], "variant": result.lastrowid,
                "stock": payload.stock_quantity, "safety": payload.safety_stock})
    return {"message": "옵션이 추가되었습니다.", "variant_id": result.lastrowid}


@router.patch("/variants/{variant_id}")
def seller_update_variant(variant_id: int, payload: VariantUpdate, current_user: dict = Depends(require_seller)):
    data = payload.model_dump(exclude_none=True)
    if "active_yn" in data:
        data["active_yn"] = data["active_yn"].strip().upper()
        if data["active_yn"] not in {"Y", "N"}:
            raise HTTPException(status_code=400, detail="옵션 사용 여부는 Y 또는 N이어야 합니다.")
    variant_fields = {k: v for k, v in data.items() if k not in {"stock_quantity", "safety_stock"}}
    inventory_fields = {k: v for k, v in data.items() if k in {"stock_quantity", "safety_stock"}}
    with engine.begin() as conn:
        owner = conn.execute(text("""
            SELECT pv.variant_id FROM product_variants pv
            INNER JOIN products p ON p.product_id=pv.product_id
            WHERE pv.variant_id=:vid AND p.seller_user_id=:sid AND p.product_status <> 'DELETED'
        """), {"vid": variant_id, "sid": current_user["user_id"]}).first()
        if not owner:
            raise HTTPException(status_code=404, detail="본인의 상품 옵션을 찾을 수 없습니다.")
        if variant_fields:
            fields = ", ".join(f"{k}=:{k}" for k in variant_fields)
            conn.execute(text(f"UPDATE product_variants SET {fields} WHERE variant_id=:vid"), {**variant_fields, "vid": variant_id})
        if inventory_fields:
            inv = conn.execute(text("SELECT inventory_id FROM inventories WHERE variant_id=:vid AND org_id=:org"),
                               {"vid": variant_id, "org": current_user.get("org_id")}).scalar()
            if inv:
                fields = ", ".join(f"{k}=:{k}" for k in inventory_fields)
                conn.execute(text(f"UPDATE inventories SET {fields} WHERE inventory_id=:iid"), {**inventory_fields, "iid": inv})
            else:
                conn.execute(text("""
                    INSERT INTO inventories (org_id, variant_id, stock_quantity, reserved_quantity, safety_stock)
                    VALUES (:org, :vid, :stock, 0, :safety)
                """), {"org": current_user.get("org_id"), "vid": variant_id,
                        "stock": inventory_fields.get("stock_quantity", 0), "safety": inventory_fields.get("safety_stock", 0)})
    return {"message": "옵션/재고가 수정되었습니다."}


@router.get("/orders")
def seller_orders(current_user: dict = Depends(require_seller)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT o.order_id, o.order_no, o.ordered_at, o.receiver_name, o.receiver_phone,
                   o.zipcode, o.shipping_address1, o.shipping_address2,
                   u.user_name AS buyer_name, u.login_id AS buyer_login_id,
                   oi.order_item_id, oi.product_id, oi.product_name_snapshot, oi.sku_snapshot,
                   oi.quantity, oi.item_amount, oi.item_status
            FROM order_items oi
            INNER JOIN orders o ON o.order_id=oi.order_id
            INNER JOIN products p ON p.product_id=oi.product_id
            INNER JOIN users u ON u.user_id=o.buyer_user_id
            WHERE p.seller_user_id=:seller_id
              AND oi.item_status IN ('PAID','PREPARING','SHIPPING','DELIVERED','COMPLETED')
            ORDER BY o.ordered_at DESC, o.order_id DESC, oi.order_item_id
        """), {"seller_id": current_user["user_id"]}).mappings().all()
    grouped = {}
    for row in rows:
        r = dict(row)
        oid = r["order_id"]
        if oid not in grouped:
            grouped[oid] = {k: r[k] for k in ["order_id", "order_no", "ordered_at", "receiver_name", "receiver_phone", "zipcode", "shipping_address1", "shipping_address2", "buyer_name", "buyer_login_id"]}
            grouped[oid]["items"] = []
        grouped[oid]["items"].append({k: r[k] for k in ["order_item_id", "product_id", "product_name_snapshot", "sku_snapshot", "quantity", "item_amount", "item_status"]})
    result = []
    for order in grouped.values():
        statuses = {item["item_status"] for item in order["items"]}
        if statuses <= {"COMPLETED"}:
            seller_status = "COMPLETED"
        elif statuses <= {"DELIVERED", "COMPLETED"}:
            seller_status = "DELIVERED"
        elif statuses & {"SHIPPING"}:
            seller_status = "SHIPPING"
        elif statuses & {"PREPARING"}:
            seller_status = "PREPARING"
        else:
            seller_status = "PAID"
        order["seller_status"] = seller_status
        order["seller_amount"] = sum(float(item["item_amount"] or 0) for item in order["items"])
        result.append(order)
    counts = {key: 0 for key in ["PAID", "PREPARING", "SHIPPING", "DELIVERED", "COMPLETED"]}
    for item in result:
        counts[item["seller_status"]] += 1
    return {"count": len(result), "counts": counts, "items": result}


@router.patch("/orders/{order_id}/shipping-status")
def seller_update_shipping(order_id: int, payload: SellerShippingUpdate, current_user: dict = Depends(require_seller)):
    target = payload.status.strip().upper()
    if target not in SHIPPING_TARGETS:
        raise HTTPException(status_code=400, detail="상품준비중, 배송중, 배송완료 중에서 선택해주세요.")
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT oi.order_item_id, oi.item_status
            FROM order_items oi
            INNER JOIN products p ON p.product_id=oi.product_id
            WHERE oi.order_id=:order_id AND p.seller_user_id=:seller_id
            FOR UPDATE
        """), {"order_id": order_id, "seller_id": current_user["user_id"]}).mappings().all()
        if not rows:
            raise HTTPException(status_code=404, detail="이 주문에 판매자님의 상품이 없습니다.")
        for row in rows:
            current = row["item_status"]
            if current in {"DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED"}:
                if current == target:
                    continue
                raise HTTPException(status_code=400, detail="이미 배송완료/구매완료된 상품은 이전 상태로 변경할 수 없습니다.")
            if current not in SHIPPING_RANK:
                raise HTTPException(status_code=400, detail="결제가 완료된 상품만 배송 처리할 수 있습니다.")
            if SHIPPING_RANK[target] < SHIPPING_RANK[current]:
                raise HTTPException(status_code=400, detail="배송 상태를 이전 단계로 되돌릴 수 없습니다.")
        conn.execute(text("""
            UPDATE order_items oi
            INNER JOIN products p ON p.product_id=oi.product_id
            SET oi.item_status=:status
            WHERE oi.order_id=:order_id AND p.seller_user_id=:seller_id
              AND oi.item_status NOT IN ('COMPLETED','CANCELLED','REFUNDED')
        """), {"status": target, "order_id": order_id, "seller_id": current_user["user_id"]})
        _recalculate_order_status(conn, order_id)
    return {"message": "판매 상품의 배송 상태가 변경되었습니다.", "order_id": order_id, "seller_status": target}


@router.get("/settlement")
def seller_settlement(current_user: dict = Depends(require_seller)):
    seller_id=current_user["user_id"]
    with engine.connect() as conn:
        summary = conn.execute(text("""
            SELECT
                COALESCE(SUM(CASE WHEN oi.item_status IN ('DELIVERED','COMPLETED') THEN oi.item_amount ELSE 0 END),0) AS settlement_target_amount,
                COALESCE(SUM(CASE WHEN oi.item_status IN ('DELIVERED','COMPLETED') AND DATE_FORMAT(o.ordered_at,'%Y-%m')=DATE_FORMAT(CURDATE(),'%Y-%m') THEN oi.item_amount ELSE 0 END),0) AS this_month_amount,
                COALESCE(SUM(CASE WHEN oi.item_status IN ('DELIVERED','COMPLETED') AND DATE(o.ordered_at)=CURDATE() THEN oi.item_amount ELSE 0 END),0) AS today_amount,
                COUNT(DISTINCT CASE WHEN oi.item_status IN ('DELIVERED','COMPLETED') THEN oi.order_id END) AS completed_order_count
            FROM order_items oi
            INNER JOIN orders o ON o.order_id=oi.order_id
            INNER JOIN products p ON p.product_id=oi.product_id
            WHERE p.seller_user_id=:seller_id
        """), {"seller_id": seller_id}).mappings().first()
        recent = conn.execute(text("""
            SELECT o.order_no, o.ordered_at, oi.product_name_snapshot, oi.quantity,
                   oi.item_amount, oi.item_status
            FROM order_items oi INNER JOIN orders o ON o.order_id=oi.order_id
            INNER JOIN products p ON p.product_id=oi.product_id
            WHERE p.seller_user_id=:seller_id AND oi.item_status IN ('DELIVERED','COMPLETED')
            ORDER BY o.ordered_at DESC, oi.order_item_id DESC LIMIT 50
        """), {"seller_id": seller_id}).mappings().all()
        top_products = conn.execute(text("""
            SELECT p.product_id,p.product_name,SUM(oi.quantity) AS sold_quantity,SUM(oi.item_amount) AS sales_amount
            FROM order_items oi INNER JOIN products p ON p.product_id=oi.product_id
            WHERE p.seller_user_id=:seller_id AND oi.item_status IN ('DELIVERED','COMPLETED')
            GROUP BY p.product_id,p.product_name
            ORDER BY sales_amount DESC,sold_quantity DESC LIMIT 10
        """), {"seller_id":seller_id}).mappings().all()
    profile = current_user["seller_profile"]
    return {"summary": dict(summary), "seller_profile": profile, "items": [dict(r) for r in recent],
            "top_products":[dict(r) for r in top_products],
            "notice": "현재 DB에는 수수료율/정산 지급 테이블이 없어 판매완료 상품금액을 정산 대상 매출로 표시합니다."}


@router.get("/inquiries")
def seller_inquiries(current_user: dict = Depends(require_seller)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT bi.inquiry_id, bi.category_code, bi.title, bi.content, bi.inquiry_status,
                   bi.secret_yn, bi.answer_content, bi.created_at, bi.answered_at,
                   u.user_name AS buyer_name, u.login_id AS buyer_login_id
            FROM buyer_inquiries bi
            INNER JOIN users u ON u.user_id=bi.user_id
            WHERE bi.org_id=:org_id
            ORDER BY (bi.inquiry_status <> 'ANSWERED') DESC, bi.created_at DESC, bi.inquiry_id DESC
        """), {"org_id": current_user.get("org_id")}).mappings().all()
    return {"count": len(rows), "items": [dict(r) for r in rows]}


@router.patch("/inquiries/{inquiry_id}/answer")
def answer_inquiry(inquiry_id: int, payload: InquiryAnswer, current_user: dict = Depends(require_seller)):
    with engine.begin() as conn:
        inquiry = conn.execute(text("SELECT inquiry_id FROM buyer_inquiries WHERE inquiry_id=:id AND org_id=:org_id"),
                               {"id": inquiry_id, "org_id": current_user.get("org_id")}).first()
        if not inquiry:
            raise HTTPException(status_code=404, detail="판매자 조직의 문의를 찾을 수 없습니다.")
        conn.execute(text("""
            UPDATE buyer_inquiries
            SET answer_content=:answer, answered_by_user_id=:seller_id,
                inquiry_status='ANSWERED', answered_at=NOW(), updated_at=NOW()
            WHERE inquiry_id=:id
        """), {"answer": payload.answer_content.strip(), "seller_id": current_user["user_id"], "id": inquiry_id})
    return {"message": "문의 답변이 등록되었습니다."}


@router.get("/reviews")
def seller_reviews(current_user: dict = Depends(require_seller)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT r.review_id, r.rating, r.review_txt, r.added_at,
                   p.product_id, p.product_name, u.user_name AS buyer_name,
                   oi.order_item_id
            FROM t5_product_reviews r
            INNER JOIN products p ON p.product_id=r.product_id
            INNER JOIN users u ON u.user_id=r.user_id
            INNER JOIN order_items oi ON oi.order_item_id=r.order_item_id
            WHERE p.seller_user_id=:seller_id
            ORDER BY r.added_at DESC, r.review_id DESC
        """), {"seller_id": current_user["user_id"]}).mappings().all()
    return {"count": len(rows), "items": [dict(r) for r in rows]}
