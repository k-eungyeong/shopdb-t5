from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/admin", tags=["admin-center"])

USER_STATUSES = {"ACTIVE", "INACTIVE", "SUSPENDED", "WITHDRAWN"}
SELLER_STATUSES = {"ACTIVE", "INACTIVE", "SUSPENDED", "PENDING"}
PRODUCT_STATUSES = {"READY", "SALE", "SOLD_OUT", "STOPPED", "DELETED"}


def require_admin(current_user: dict = Depends(get_current_user)):
    if "ADMIN" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return current_user


class MemberStatusUpdate(BaseModel):
    user_status: str


class SellerStatusUpdate(BaseModel):
    seller_status: str


class AdminProductUpdate(BaseModel):
    category_id: int | None = None
    regular_price: float | None = Field(default=None, ge=0)
    sale_price: float | None = Field(default=None, ge=0)
    product_status: str | None = None


class CategoryCreate(BaseModel):
    category_name: str = Field(min_length=1, max_length=100)
    parent_category_id: int | None = None
    display_order: int = 0


class CategoryUpdate(BaseModel):
    category_name: str | None = Field(default=None, min_length=1, max_length=100)
    display_order: int | None = None
    active_yn: str | None = None


@router.get("/dashboard")
def admin_dashboard(current_user: dict = Depends(require_admin)):
    """관리자 대시보드: 기존 테이블을 집계해 운영 현황과 최근 7일 매출을 보여줍니다."""
    with engine.connect() as conn:
        summary = conn.execute(text("""
            SELECT
                COALESCE((SELECT SUM(approved_amount) FROM payments
                          WHERE payment_status='DONE' AND DATE(approved_at)=CURDATE()), 0) AS today_sales,
                COALESCE((SELECT SUM(approved_amount) FROM payments
                          WHERE payment_status='DONE'
                            AND DATE_FORMAT(approved_at,'%Y-%m')=DATE_FORMAT(CURDATE(),'%Y-%m')), 0) AS month_sales,
                (SELECT COUNT(*) FROM users WHERE DATE(created_at)=CURDATE()) AS today_members,
                (SELECT COUNT(*) FROM users WHERE user_status='ACTIVE') AS active_members,
                (SELECT COUNT(*) FROM seller_profiles WHERE seller_status='ACTIVE') AS active_sellers,
                (SELECT COUNT(*) FROM products WHERE product_status <> 'DELETED') AS product_count,
                (SELECT COUNT(*) FROM orders WHERE DATE(ordered_at)=CURDATE()) AS today_orders,
                (SELECT COUNT(*) FROM orders WHERE order_status='PAID') AS paid_orders,
                (SELECT COUNT(*) FROM orders WHERE order_status='PREPARING') AS preparing_orders,
                (SELECT COUNT(*) FROM orders WHERE order_status='SHIPPING') AS shipping_orders,
                (SELECT COUNT(*) FROM orders WHERE order_status='DELIVERED') AS delivered_orders,
                (SELECT COUNT(*) FROM refund_requests WHERE refund_status IN ('REQUESTED','REVIEWING')) AS pending_refunds,
                (SELECT COUNT(*)
                   FROM inventories i
                   WHERE GREATEST(i.stock_quantity-i.reserved_quantity,0) <= i.safety_stock) AS low_stock_variants
        """)).mappings().first()

        recent_orders = conn.execute(text("""
            SELECT o.order_id, o.order_no, o.order_status, o.total_amount, o.ordered_at,
                   u.user_name AS buyer_name,
                   GROUP_CONCAT(DISTINCT oi.product_name_snapshot ORDER BY oi.order_item_id SEPARATOR ', ') AS product_names
            FROM orders o
            INNER JOIN users u ON u.user_id=o.buyer_user_id
            LEFT JOIN order_items oi ON oi.order_id=o.order_id
            GROUP BY o.order_id, o.order_no, o.order_status, o.total_amount, o.ordered_at, u.user_name
            ORDER BY o.ordered_at DESC, o.order_id DESC
            LIMIT 8
        """)).mappings().all()

        sales_trend = conn.execute(text("""
            WITH RECURSIVE dates AS (
                SELECT CURDATE() - INTERVAL 6 DAY AS d
                UNION ALL
                SELECT d + INTERVAL 1 DAY FROM dates WHERE d < CURDATE()
            )
            SELECT DATE_FORMAT(dates.d,'%m-%d') AS label,
                   COALESCE(SUM(p.approved_amount),0) AS sales
            FROM dates
            LEFT JOIN payments p ON DATE(p.approved_at)=dates.d AND p.payment_status='DONE'
            GROUP BY dates.d
            ORDER BY dates.d
        """)).mappings().all()

        low_stock = conn.execute(text("""
            SELECT p.product_id, p.product_name, pv.variant_id, pv.sku_code,
                   GREATEST(i.stock_quantity-i.reserved_quantity,0) AS available_stock,
                   i.safety_stock, COALESCE(sp.company_name,u.user_name) AS seller_name
            FROM inventories i
            INNER JOIN product_variants pv ON pv.variant_id=i.variant_id
            INNER JOIN products p ON p.product_id=pv.product_id
            INNER JOIN users u ON u.user_id=p.seller_user_id
            LEFT JOIN seller_profiles sp ON sp.user_id=p.seller_user_id
            WHERE p.product_status <> 'DELETED'
              AND pv.active_yn='Y'
              AND GREATEST(i.stock_quantity-i.reserved_quantity,0) <= i.safety_stock
            ORDER BY available_stock ASC, p.product_id
            LIMIT 10
        """)).mappings().all()

        top_products = conn.execute(text("""
            SELECT p.product_id,p.product_name,COALESCE(sp.company_name,u.user_name) AS seller_name,
                   SUM(oi.quantity) AS sold_quantity,SUM(oi.item_amount) AS sales_amount
            FROM order_items oi
            INNER JOIN products p ON p.product_id=oi.product_id
            INNER JOIN users u ON u.user_id=p.seller_user_id
            LEFT JOIN seller_profiles sp ON sp.user_id=p.seller_user_id
            WHERE oi.item_status IN ('PAID','PREPARING','SHIPPING','DELIVERED','COMPLETED')
            GROUP BY p.product_id,p.product_name,sp.company_name,u.user_name
            ORDER BY sold_quantity DESC,sales_amount DESC LIMIT 10
        """)).mappings().all()

    return {
        "summary": dict(summary),
        "recent_orders": [dict(row) for row in recent_orders],
        "sales_trend": [dict(row) for row in sales_trend],
        "low_stock": [dict(row) for row in low_stock],
        "top_products": [dict(row) for row in top_products],
    }


@router.get("/members")
def admin_members(current_user: dict = Depends(require_admin)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT u.user_id, u.login_id, u.user_name, u.email, u.phone, u.user_status,
                   u.org_id, ou.org_name, u.created_at,
                   GROUP_CONCAT(DISTINCT r.role_code ORDER BY r.role_id SEPARATOR ',') AS role_codes,
                   (SELECT COUNT(*) FROM orders o WHERE o.buyer_user_id=u.user_id AND o.order_status NOT IN ('CANCELLED')) AS order_count,
                   (SELECT COALESCE(SUM(o.total_amount),0) FROM orders o WHERE o.buyer_user_id=u.user_id AND o.order_status IN ('PAID','PREPARING','SHIPPING','DELIVERED','COMPLETED')) AS purchase_total
            FROM users u
            LEFT JOIN org_units ou ON ou.org_id=u.org_id
            LEFT JOIN user_roles ur ON ur.user_id=u.user_id
            LEFT JOIN roles r ON r.role_id=ur.role_id
            GROUP BY u.user_id, u.login_id, u.user_name, u.email, u.phone,
                     u.user_status, u.org_id, ou.org_name, u.created_at
            ORDER BY u.created_at DESC, u.user_id DESC
        """)).mappings().all()
    items = []
    for row in rows:
        item = dict(row)
        item["roles"] = [v for v in (item.pop("role_codes") or "").split(",") if v]
        items.append(item)
    return {"count": len(items), "items": items}


@router.patch("/members/{user_id}/status")
def update_member_status(user_id: int, payload: MemberStatusUpdate, current_user: dict = Depends(require_admin)):
    status = payload.user_status.strip().upper()
    if status not in USER_STATUSES:
        raise HTTPException(status_code=400, detail="올바르지 않은 회원 상태입니다.")
    if user_id == current_user["user_id"] and status != "ACTIVE":
        raise HTTPException(status_code=400, detail="현재 로그인한 관리자 본인 계정은 비활성화할 수 없습니다.")
    with engine.begin() as conn:
        result = conn.execute(text("UPDATE users SET user_status=:status WHERE user_id=:user_id"),
                              {"status": status, "user_id": user_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="회원을 찾을 수 없습니다.")
    return {"message": "회원 상태가 변경되었습니다.", "user_id": user_id, "user_status": status}


@router.get("/sellers")
def admin_sellers(current_user: dict = Depends(require_admin)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT sp.seller_id, sp.user_id, sp.company_name, sp.business_number,
                   sp.representative_name, sp.seller_status, sp.settlement_bank,
                   sp.settlement_account, sp.created_at,
                   u.login_id, u.user_name, u.email, u.phone, u.user_status,
                   COUNT(DISTINCT p.product_id) AS product_count,
                   COALESCE(SUM(CASE WHEN oi.item_status IN ('DELIVERED','COMPLETED') THEN oi.item_amount ELSE 0 END),0) AS completed_sales
            FROM seller_profiles sp
            INNER JOIN users u ON u.user_id=sp.user_id
            LEFT JOIN products p ON p.seller_user_id=sp.user_id AND p.product_status <> 'DELETED'
            LEFT JOIN order_items oi ON oi.product_id=p.product_id
            GROUP BY sp.seller_id, sp.user_id, sp.company_name, sp.business_number,
                     sp.representative_name, sp.seller_status, sp.settlement_bank,
                     sp.settlement_account, sp.created_at,
                     u.login_id, u.user_name, u.email, u.phone, u.user_status
            ORDER BY sp.created_at DESC, sp.seller_id DESC
        """)).mappings().all()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@router.patch("/sellers/{seller_id}/status")
def update_seller_status(seller_id: int, payload: SellerStatusUpdate, current_user: dict = Depends(require_admin)):
    status = payload.seller_status.strip().upper()
    if status not in SELLER_STATUSES:
        raise HTTPException(status_code=400, detail="올바르지 않은 판매자 상태입니다.")
    with engine.begin() as conn:
        result = conn.execute(text("UPDATE seller_profiles SET seller_status=:status WHERE seller_id=:seller_id"),
                              {"status": status, "seller_id": seller_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="판매자를 찾을 수 없습니다.")
    return {"message": "판매자 상태가 변경되었습니다.", "seller_id": seller_id, "seller_status": status}


@router.get("/products")
def admin_products(current_user: dict = Depends(require_admin)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT p.product_id, p.product_code, p.product_name, p.regular_price, p.sale_price,
                   p.product_status, p.category_id, c.category_name, p.seller_user_id,
                   COALESCE(sp.company_name, u.user_name) AS seller_name,
                   COALESCE(SUM(GREATEST(i.stock_quantity-i.reserved_quantity,0)),0) AS available_stock,
                   p.created_at, p.updated_at
            FROM products p
            INNER JOIN users u ON u.user_id=p.seller_user_id
            LEFT JOIN seller_profiles sp ON sp.user_id=p.seller_user_id
            INNER JOIN categories c ON c.category_id=p.category_id
            LEFT JOIN product_variants pv ON pv.product_id=p.product_id AND pv.active_yn='Y'
            LEFT JOIN inventories i ON i.variant_id=pv.variant_id
            WHERE p.product_status <> 'DELETED'
            GROUP BY p.product_id, p.product_code, p.product_name, p.regular_price, p.sale_price,
                     p.product_status, p.category_id, c.category_name, p.seller_user_id,
                     sp.company_name, u.user_name, p.created_at, p.updated_at
            ORDER BY p.created_at DESC, p.product_id DESC
        """)).mappings().all()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@router.patch("/products/{product_id}")
def admin_update_product(product_id: int, payload: AdminProductUpdate, current_user: dict = Depends(require_admin)):
    fields = []
    params = {"product_id": product_id}
    data = payload.model_dump(exclude_none=True)
    if "product_status" in data:
        status = data["product_status"].strip().upper()
        if status not in PRODUCT_STATUSES:
            raise HTTPException(status_code=400, detail="올바르지 않은 상품 상태입니다.")
        data["product_status"] = status
    if "category_id" in data:
        with engine.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM categories WHERE category_id=:id"), {"id": data["category_id"]}).first()
        if not exists:
            raise HTTPException(status_code=400, detail="카테고리를 찾을 수 없습니다.")
    if "regular_price" in data and "sale_price" in data and data["sale_price"] > data["regular_price"]:
        raise HTTPException(status_code=400, detail="판매가는 정상가보다 높을 수 없습니다.")
    for key, value in data.items():
        fields.append(f"{key}=:{key}")
        params[key] = value
    if not fields:
        raise HTTPException(status_code=400, detail="변경할 값이 없습니다.")
    with engine.begin() as conn:
        result = conn.execute(text(f"UPDATE products SET {', '.join(fields)} WHERE product_id=:product_id"), params)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    return {"message": "상품 정보가 변경되었습니다.", "product_id": product_id}


@router.get("/categories")
def admin_categories(current_user: dict = Depends(require_admin)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT c.category_id, c.parent_category_id, pc.category_name AS parent_name,
                   c.category_name, c.category_level, c.display_order, c.active_yn,
                   (SELECT COUNT(*) FROM products p WHERE p.category_id=c.category_id AND p.product_status <> 'DELETED') AS product_count
            FROM categories c
            LEFT JOIN categories pc ON pc.category_id=c.parent_category_id
            ORDER BY c.category_level, c.display_order, c.category_id
        """)).mappings().all()
    return {"count": len(rows), "items": [dict(row) for row in rows]}


@router.post("/categories", status_code=201)
def admin_create_category(payload: CategoryCreate, current_user: dict = Depends(require_admin)):
    level = 1
    with engine.begin() as conn:
        if payload.parent_category_id is not None:
            parent = conn.execute(text("SELECT category_level FROM categories WHERE category_id=:id"),
                                  {"id": payload.parent_category_id}).mappings().first()
            if not parent:
                raise HTTPException(status_code=400, detail="상위 카테고리를 찾을 수 없습니다.")
            level = int(parent["category_level"] or 1) + 1
        result = conn.execute(text("""
            INSERT INTO categories (parent_category_id, category_name, category_level, display_order, active_yn)
            VALUES (:parent_id, :name, :level, :display_order, 'Y')
        """), {"parent_id": payload.parent_category_id, "name": payload.category_name.strip(),
                "level": level, "display_order": payload.display_order})
    return {"message": "카테고리가 등록되었습니다.", "category_id": result.lastrowid}


@router.patch("/categories/{category_id}")
def admin_update_category(category_id: int, payload: CategoryUpdate, current_user: dict = Depends(require_admin)):
    data = payload.model_dump(exclude_none=True)
    if "active_yn" in data:
        data["active_yn"] = data["active_yn"].strip().upper()
        if data["active_yn"] not in {"Y", "N"}:
            raise HTTPException(status_code=400, detail="active_yn은 Y 또는 N이어야 합니다.")
    fields, params = [], {"category_id": category_id}
    for key, value in data.items():
        fields.append(f"{key}=:{key}")
        params[key] = value.strip() if isinstance(value, str) else value
    if not fields:
        raise HTTPException(status_code=400, detail="변경할 값이 없습니다.")
    with engine.begin() as conn:
        result = conn.execute(text(f"UPDATE categories SET {', '.join(fields)} WHERE category_id=:category_id"), params)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다.")
    return {"message": "카테고리가 변경되었습니다.", "category_id": category_id}


@router.get("/policies")
def admin_policies(current_user: dict = Depends(require_admin)):
    """현재 DB에 존재하는 운영정책을 조회합니다. 배너/공지 테이블은 없어 조회 범위에 포함하지 않습니다."""
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT cp.policy_id, cp.policy_code, cp.policy_name, cp.policy_version,
                   cp.policy_type, cp.effective_from, cp.effective_to, cp.active_yn,
                   ou.org_name
            FROM company_policies cp
            LEFT JOIN org_units ou ON ou.org_id=cp.org_id
            ORDER BY cp.effective_from DESC, cp.policy_id DESC
        """)).mappings().all()
        methods = conn.execute(text("""
            SELECT payment_method, COUNT(*) AS use_count
            FROM payments
            WHERE payment_method IS NOT NULL
            GROUP BY payment_method
            ORDER BY use_count DESC
        """)).mappings().all()
    return {"policies": [dict(row) for row in rows], "payment_methods": [dict(row) for row in methods]}

class RefundStatusUpdate(BaseModel):
    refund_status: str
    approved_amount: float | None = Field(default=None, ge=0)


@router.get("/refunds")
def admin_refunds(current_user: dict = Depends(require_admin)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT rr.refund_request_id, rr.order_id, o.order_no, rr.buyer_user_id,
                   u.user_name AS buyer_name, u.login_id AS buyer_login_id,
                   rr.refund_reason, rr.requested_amount, rr.approved_amount, rr.refund_status,
                   rr.requested_at, rr.approved_at, rr.completed_at,
                   GROUP_CONCAT(oi.product_name_snapshot ORDER BY oi.order_item_id SEPARATOR ', ') AS product_names
            FROM refund_requests rr
            INNER JOIN orders o ON o.order_id=rr.order_id
            INNER JOIN users u ON u.user_id=rr.buyer_user_id
            LEFT JOIN refund_items ri ON ri.refund_request_id=rr.refund_request_id
            LEFT JOIN order_items oi ON oi.order_item_id=ri.order_item_id
            GROUP BY rr.refund_request_id, rr.order_id, o.order_no, rr.buyer_user_id,
                     u.user_name,u.login_id,rr.refund_reason,rr.requested_amount,rr.approved_amount,
                     rr.refund_status,rr.requested_at,rr.approved_at,rr.completed_at
            ORDER BY FIELD(rr.refund_status,'REQUESTED','REVIEWING','APPROVED','REJECTED','COMPLETED'), rr.requested_at DESC
        """)).mappings().all()
    return {"count":len(rows),"items":[dict(r) for r in rows]}


@router.patch("/refunds/{refund_request_id}")
def update_refund(refund_request_id: int, payload: RefundStatusUpdate, current_user: dict = Depends(require_admin)):
    target = payload.refund_status.strip().upper()
    allowed = {"REVIEWING","APPROVED","REJECTED","COMPLETED"}
    if target not in allowed:
        raise HTTPException(status_code=400, detail="올바르지 않은 환불 상태입니다.")
    with engine.begin() as conn:
        rr = conn.execute(text("""
            SELECT refund_request_id,order_id,requested_amount,approved_amount,refund_status
            FROM refund_requests WHERE refund_request_id=:id FOR UPDATE
        """), {"id":refund_request_id}).mappings().first()
        if not rr:
            raise HTTPException(status_code=404, detail="환불 요청을 찾을 수 없습니다.")
        if rr["refund_status"] in {"REJECTED","COMPLETED"}:
            raise HTTPException(status_code=400, detail="이미 종료된 환불 요청입니다.")
        approved_amount = payload.approved_amount if payload.approved_amount is not None else rr["requested_amount"]
        if approved_amount > rr["requested_amount"]:
            raise HTTPException(status_code=400, detail="승인금액은 요청금액보다 클 수 없습니다.")

        if target == "REVIEWING":
            conn.execute(text("UPDATE refund_requests SET refund_status='REVIEWING' WHERE refund_request_id=:id"), {"id":refund_request_id})
        elif target == "REJECTED":
            conn.execute(text("UPDATE refund_requests SET refund_status='REJECTED' WHERE refund_request_id=:id"), {"id":refund_request_id})
        elif target == "APPROVED":
            conn.execute(text("""
                UPDATE refund_requests SET refund_status='APPROVED',approved_amount=:amount,approved_at=NOW()
                WHERE refund_request_id=:id
            """), {"id":refund_request_id,"amount":approved_amount})
        else:
            # 환불 완료 시 기존 재고를 복구하고 주문/결제 상태를 함께 맞춥니다.
            items = conn.execute(text("""
                SELECT ri.order_item_id,ri.refund_quantity,oi.variant_id
                FROM refund_items ri INNER JOIN order_items oi ON oi.order_item_id=ri.order_item_id
                WHERE ri.refund_request_id=:id
            """), {"id":refund_request_id}).mappings().all()
            for item in items:
                if item["variant_id"]:
                    inv = conn.execute(text("SELECT inventory_id FROM inventories WHERE variant_id=:vid ORDER BY inventory_id LIMIT 1 FOR UPDATE"), {"vid":item["variant_id"]}).scalar()
                    if inv:
                        conn.execute(text("UPDATE inventories SET stock_quantity=stock_quantity+:qty WHERE inventory_id=:iid"), {"qty":item["refund_quantity"],"iid":inv})
            conn.execute(text("UPDATE order_items SET item_status='REFUNDED' WHERE order_id=:oid AND item_status <> 'CANCELLED'"), {"oid":rr["order_id"]})
            conn.execute(text("UPDATE orders SET order_status='REFUNDED' WHERE order_id=:oid"), {"oid":rr["order_id"]})
            payment = conn.execute(text("SELECT payment_id,approved_amount FROM payments WHERE order_id=:oid AND payment_status='DONE' ORDER BY payment_id DESC LIMIT 1 FOR UPDATE"), {"oid":rr["order_id"]}).mappings().first()
            if payment:
                conn.execute(text("""
                    UPDATE payments SET payment_status='REFUNDED',cancelled_amount=:amount,balance_amount=0,cancelled_at=NOW()
                    WHERE payment_id=:pid
                """), {"amount":approved_amount,"pid":payment["payment_id"]})
                conn.execute(text("""
                    INSERT INTO payment_transactions(payment_id,transaction_type,transaction_status,transaction_amount,cancel_reason)
                    VALUES(:pid,'REFUND','DONE',:amount,'관리자 환불 완료')
                """), {"pid":payment["payment_id"],"amount":approved_amount})
            conn.execute(text("""
                UPDATE refund_requests SET refund_status='COMPLETED',approved_amount=:amount,
                       approved_at=COALESCE(approved_at,NOW()),completed_at=NOW()
                WHERE refund_request_id=:id
            """), {"id":refund_request_id,"amount":approved_amount})
    return {"message":f"환불 상태를 {target}(으)로 변경했습니다.","refund_status":target}


@router.get("/reviews")
def admin_reviews(current_user: dict = Depends(require_admin)):
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT r.review_id,r.rating,r.review_txt,r.added_at,r.user_id,r.product_id,
                   u.user_name AS buyer_name,u.login_id AS buyer_login_id,
                   p.product_name,COALESCE(sp.company_name,su.user_name) AS seller_name
            FROM t5_product_reviews r
            INNER JOIN users u ON u.user_id=r.user_id
            INNER JOIN products p ON p.product_id=r.product_id
            INNER JOIN users su ON su.user_id=p.seller_user_id
            LEFT JOIN seller_profiles sp ON sp.user_id=p.seller_user_id
            ORDER BY r.added_at DESC,r.review_id DESC
        """)).mappings().all()
    return {"count":len(rows),"items":[dict(r) for r in rows]}


@router.delete("/reviews/{review_id}")
def admin_delete_review(review_id: str, current_user: dict = Depends(require_admin)):
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM t5_product_reviews WHERE review_id=:id"), {"id":review_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="리뷰를 찾을 수 없습니다.")
    return {"message":"관리자 권한으로 리뷰를 삭제했습니다."}
