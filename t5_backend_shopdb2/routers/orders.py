from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderCreate(BaseModel):
    address_id: int


def _load_order_items(conn, order_id: int):
    return conn.execute(text("""
        SELECT oi.order_item_id, oi.product_id, oi.variant_id, oi.product_name_snapshot,
               oi.sku_snapshot, oi.quantity, oi.unit_price, oi.item_amount, oi.item_status,
               r.review_id, r.rating, r.review_txt
        FROM order_items oi
        LEFT JOIN t5_product_reviews r ON r.order_item_id = oi.order_item_id
        WHERE oi.order_id = :order_id
        ORDER BY oi.order_item_id
    """), {"order_id": order_id}).mappings().all()


@router.get("")
def get_orders(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    with engine.connect() as conn:
        orders = conn.execute(text("""
            SELECT o.order_id, o.order_no, o.order_status, o.product_amount, o.discount_amount,
                   o.shipping_amount, o.total_amount, o.receiver_name, o.receiver_phone, o.zipcode,
                   o.shipping_address1, o.shipping_address2, o.ordered_at
            FROM orders o
            WHERE o.buyer_user_id = :user_id
            ORDER BY o.ordered_at DESC, o.order_id DESC
        """), {"user_id": user_id}).mappings().all()

        result = []
        for order in orders:
            items = _load_order_items(conn, order["order_id"])
            result.append({**dict(order), "items": [dict(item) for item in items]})
    return {"count": len(result), "items": result}


@router.post("", status_code=201)
def create_order(payload: OrderCreate, current_user: dict = Depends(get_current_user)):
    """현재 로그인 회원의 장바구니를 주문서로 변환합니다. 결제는 5단계에서 처리합니다."""
    user_id = current_user["user_id"]
    with engine.begin() as conn:
        address = conn.execute(text("""
            SELECT address_id, receiver_name, receiver_phone, zipcode, address1, address2
            FROM user_addresses
            WHERE address_id=:address_id AND user_id=:user_id
        """), {"address_id": payload.address_id, "user_id": user_id}).mappings().first()
        if address is None:
            raise HTTPException(status_code=404, detail="선택한 배송지를 찾을 수 없습니다.")

        cart_items = conn.execute(text("""
            SELECT c.carts_id, c.product_id, c.variant_id, c.quantity,
                   p.product_name, p.product_status, p.sale_price,
                   pv.sku_code, pv.additional_price,
                   COALESCE((SELECT SUM(GREATEST(i.stock_quantity-i.reserved_quantity,0))
                             FROM inventories i WHERE i.variant_id=c.variant_id),0) AS available_stock
            FROM t5_carts c
            INNER JOIN products p ON p.product_id=c.product_id
            INNER JOIN product_variants pv ON pv.variant_id=c.variant_id AND pv.product_id=c.product_id
            WHERE c.user_id=:user_id AND p.product_status <> 'DELETED' AND pv.active_yn='Y'
            ORDER BY c.added_at, c.carts_id
        """), {"user_id": user_id}).mappings().all()
        if not cart_items:
            raise HTTPException(status_code=400, detail="장바구니가 비어 있습니다.")

        product_amount = 0
        prepared = []
        for item in cart_items:
            if item["quantity"] > int(item["available_stock"] or 0):
                raise HTTPException(status_code=400, detail=f"'{item['product_name']}' 상품의 재고가 부족합니다.")
            unit_price = item["sale_price"] + item["additional_price"]
            item_amount = unit_price * item["quantity"]
            product_amount += item_amount
            prepared.append({**dict(item), "unit_price": unit_price, "item_amount": item_amount})

        shipping_amount = 0 if product_amount >= 50000 else 3000
        discount_amount = 0
        total_amount = product_amount - discount_amount + shipping_amount
        org_id = current_user.get("org_id")
        if org_id is None:
            org_id = conn.execute(text("SELECT org_id FROM org_units WHERE active_yn='Y' ORDER BY org_id LIMIT 1")).scalar()
        if org_id is None:
            raise HTTPException(status_code=500, detail="주문을 처리할 조직 정보가 없습니다.")

        order_no = f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"
        result = conn.execute(text("""
            INSERT INTO orders
                (order_no, buyer_user_id, org_id, order_status, product_amount, discount_amount,
                 shipping_amount, total_amount, receiver_name, receiver_phone, zipcode,
                 shipping_address1, shipping_address2)
            VALUES
                (:order_no, :buyer_user_id, :org_id, 'PAYMENT_PENDING', :product_amount, :discount_amount,
                 :shipping_amount, :total_amount, :receiver_name, :receiver_phone, :zipcode,
                 :shipping_address1, :shipping_address2)
        """), {
            "order_no": order_no,
            "buyer_user_id": user_id,
            "org_id": org_id,
            "product_amount": product_amount,
            "discount_amount": discount_amount,
            "shipping_amount": shipping_amount,
            "total_amount": total_amount,
            "receiver_name": address["receiver_name"],
            "receiver_phone": address["receiver_phone"],
            "zipcode": address["zipcode"],
            "shipping_address1": address["address1"],
            "shipping_address2": address["address2"],
        })
        order_id = result.lastrowid

        for item in prepared:
            conn.execute(text("""
                INSERT INTO order_items
                    (order_id, product_id, variant_id, product_name_snapshot, sku_snapshot,
                     quantity, unit_price, item_amount, item_status)
                VALUES
                    (:order_id, :product_id, :variant_id, :product_name, :sku_code,
                     :quantity, :unit_price, :item_amount, 'ORDERED')
            """), {
                "order_id": order_id,
                "product_id": item["product_id"],
                "variant_id": item["variant_id"],
                "product_name": item["product_name"],
                "sku_code": item["sku_code"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "item_amount": item["item_amount"],
            })

    return {
        "message": "주문서가 생성되었습니다. 아직 결제 전 상태입니다.",
        "order_id": order_id,
        "order_no": order_no,
        "order_status": "PAYMENT_PENDING",
        "product_amount": product_amount,
        "shipping_amount": shipping_amount,
        "total_amount": total_amount,
    }

@router.get("/{order_id}")
def get_order_detail(order_id: int, current_user: dict = Depends(get_current_user)):
    with engine.connect() as conn:
        order = conn.execute(text("""
            SELECT o.order_id, o.order_no, o.org_id, o.order_status, o.product_amount,
                   o.discount_amount, o.shipping_amount, o.total_amount, o.receiver_name,
                   o.receiver_phone, o.zipcode, o.shipping_address1, o.shipping_address2,
                   o.ordered_at, o.updated_at
            FROM orders o
            WHERE o.order_id=:order_id AND o.buyer_user_id=:user_id
        """), {"order_id": order_id, "user_id": current_user["user_id"]}).mappings().first()
        if order is None:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
        items = _load_order_items(conn, order_id)
        payment = conn.execute(text("""
            SELECT payment_id, pg_provider, payment_method, payment_status, requested_amount,
                   approved_amount, cancelled_amount, approved_at, cancelled_at
            FROM payments
            WHERE order_id=:order_id
            ORDER BY payment_id DESC LIMIT 1
        """), {"order_id": order_id}).mappings().first()
        refund = conn.execute(text("""
            SELECT refund_request_id,refund_reason,requested_amount,approved_amount,refund_status,requested_at,approved_at,completed_at
            FROM refund_requests WHERE order_id=:order_id
            ORDER BY refund_request_id DESC LIMIT 1
        """), {"order_id":order_id}).mappings().first()
    return {**dict(order), "items": [dict(i) for i in items], "payment": dict(payment) if payment else None, "refund": dict(refund) if refund else None}


@router.post("/{order_id}/cancel")
def cancel_order(order_id: int, current_user: dict = Depends(get_current_user)):
    """결제대기 주문 또는 상품준비 전 PAID 주문을 취소합니다."""
    with engine.begin() as conn:
        order = conn.execute(text("""
            SELECT order_id, order_no, org_id, buyer_user_id, order_status, total_amount
            FROM orders
            WHERE order_id=:order_id AND buyer_user_id=:user_id
            FOR UPDATE
        """), {"order_id": order_id, "user_id": current_user["user_id"]}).mappings().first()
        if order is None:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
        if order["order_status"] not in {"ORDERED", "PAYMENT_PENDING", "PAID"}:
            raise HTTPException(status_code=400, detail="상품 준비가 시작된 주문은 이 화면에서 취소할 수 없습니다.")

        items = conn.execute(text("""
            SELECT order_item_id, variant_id, quantity
            FROM order_items WHERE order_id=:order_id ORDER BY order_item_id
        """), {"order_id": order_id}).mappings().all()

        if order["order_status"] == "PAID":
            payment = conn.execute(text("""
                SELECT payment_id, approved_amount, payment_status
                FROM payments
                WHERE order_id=:order_id AND payment_status='DONE'
                ORDER BY payment_id DESC LIMIT 1
                FOR UPDATE
            """), {"order_id": order_id}).mappings().first()
            if payment is None:
                raise HTTPException(status_code=409, detail="결제 승인 기록을 찾을 수 없어 자동 취소할 수 없습니다.")

            # 5단계 결제와 같은 우선순위로 재고 행을 찾아 수량을 되돌립니다.
            for item in items:
                inventory = conn.execute(text("""
                    SELECT inventory_id
                    FROM inventories
                    WHERE variant_id=:variant_id
                    ORDER BY (org_id=:order_org_id) DESC, inventory_id ASC
                    LIMIT 1
                    FOR UPDATE
                """), {"variant_id": item["variant_id"], "order_org_id": order["org_id"]}).mappings().first()
                if inventory:
                    conn.execute(text("""
                        UPDATE inventories SET stock_quantity=stock_quantity+:quantity
                        WHERE inventory_id=:inventory_id
                    """), {"quantity": item["quantity"], "inventory_id": inventory["inventory_id"]})

            cancel_key = f"cancel_{uuid4().hex}"
            conn.execute(text("""
                UPDATE payments
                SET payment_status='CANCELED', cancelled_amount=approved_amount,
                    balance_amount=0, cancelled_at=NOW()
                WHERE payment_id=:payment_id
            """), {"payment_id": payment["payment_id"]})
            conn.execute(text("""
                INSERT INTO payment_transactions
                    (payment_id, transaction_key, transaction_type, transaction_status,
                     transaction_amount, pg_transaction_id, idempotency_key, cancel_reason,
                     request_json, response_json)
                VALUES
                    (:payment_id, :transaction_key, 'CANCEL', 'SUCCESS', :amount,
                     :transaction_key, :idempotency_key, '고객 주문 취소',
                     JSON_OBJECT('mode','development','orderId',:order_no),
                     JSON_OBJECT('status','CANCELED'))
            """), {
                "payment_id": payment["payment_id"],
                "transaction_key": cancel_key,
                "amount": payment["approved_amount"],
                "idempotency_key": f"idem_{uuid4().hex}",
                "order_no": order["order_no"],
            })

        conn.execute(text("UPDATE orders SET order_status='CANCELLED' WHERE order_id=:order_id"), {"order_id": order_id})
        conn.execute(text("UPDATE order_items SET item_status='CANCELLED' WHERE order_id=:order_id"), {"order_id": order_id})

    return {"message": "주문이 취소되었습니다.", "order_status": "CANCELLED"}


@router.post("/{order_id}/complete")
def complete_order(order_id: int, current_user: dict = Depends(get_current_user)):
    """배송완료(DELIVERED) 주문을 고객이 직접 구매완료(COMPLETED)로 확정합니다."""
    with engine.begin() as conn:
        order = conn.execute(text("""
            SELECT order_id, order_no, buyer_user_id, order_status
            FROM orders
            WHERE order_id=:order_id AND buyer_user_id=:user_id
            FOR UPDATE
        """), {
            "order_id": order_id,
            "user_id": current_user["user_id"],
        }).mappings().first()

        if order is None:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")

        if order["order_status"] == "COMPLETED":
            return {
                "message": "이미 구매완료된 주문입니다.",
                "order_status": "COMPLETED",
            }

        if order["order_status"] != "DELIVERED":
            raise HTTPException(
                status_code=400,
                detail="배송완료 상태의 주문만 구매완료로 변경할 수 있습니다.",
            )

        # 기존 orders/order_items 컬럼만 사용합니다. SQL 테이블 구조는 변경하지 않습니다.
        conn.execute(text("""
            UPDATE orders
            SET order_status='COMPLETED'
            WHERE order_id=:order_id
        """), {"order_id": order_id})

        conn.execute(text("""
            UPDATE order_items
            SET item_status='COMPLETED'
            WHERE order_id=:order_id
              AND item_status <> 'CANCELLED'
        """), {"order_id": order_id})

    return {
        "message": "구매완료 처리되었습니다. 이제 구매한 상품의 리뷰를 작성할 수 있습니다.",
        "order_status": "COMPLETED",
    }

class RefundCreate(BaseModel):
    refund_reason: str


@router.post("/{order_id}/refund", status_code=201)
def request_refund(order_id: int, payload: RefundCreate, current_user: dict = Depends(get_current_user)):
    """기존 refund_requests/refund_items를 이용해 주문 전체 환불을 신청합니다."""
    reason = payload.refund_reason.strip()
    if len(reason) < 2:
        raise HTTPException(status_code=400, detail="환불 사유를 입력해주세요.")
    with engine.begin() as conn:
        order = conn.execute(text("""
            SELECT order_id, order_no, buyer_user_id, order_status, total_amount
            FROM orders WHERE order_id=:order_id AND buyer_user_id=:user_id FOR UPDATE
        """), {"order_id": order_id, "user_id": current_user["user_id"]}).mappings().first()
        if not order:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
        if order["order_status"] not in {"DELIVERED", "COMPLETED"}:
            raise HTTPException(status_code=400, detail="배송완료 또는 구매완료 주문만 환불을 신청할 수 있습니다.")
        exists = conn.execute(text("""
            SELECT refund_request_id, refund_status FROM refund_requests
            WHERE order_id=:order_id AND refund_status IN ('REQUESTED','REVIEWING','APPROVED')
            ORDER BY refund_request_id DESC LIMIT 1
        """), {"order_id": order_id}).mappings().first()
        if exists:
            raise HTTPException(status_code=409, detail="이미 처리 중인 환불 신청이 있습니다.")

        result = conn.execute(text("""
            INSERT INTO refund_requests(order_id,buyer_user_id,refund_reason,requested_amount,refund_status)
            VALUES(:order_id,:buyer_user_id,:reason,:amount,'REQUESTED')
        """), {"order_id": order_id, "buyer_user_id": current_user["user_id"], "reason": reason, "amount": order["total_amount"]})
        refund_request_id = result.lastrowid
        items = conn.execute(text("""
            SELECT order_item_id, quantity, item_amount FROM order_items
            WHERE order_id=:order_id AND item_status <> 'CANCELLED'
        """), {"order_id": order_id}).mappings().all()
        for item in items:
            conn.execute(text("""
                INSERT INTO refund_items(refund_request_id,order_item_id,refund_quantity,refund_amount)
                VALUES(:rid,:oid,:qty,:amount)
            """), {"rid": refund_request_id, "oid": item["order_item_id"], "qty": item["quantity"], "amount": item["item_amount"]})
    return {"message":"환불 신청이 접수되었습니다.","refund_request_id":refund_request_id,"refund_status":"REQUESTED"}
