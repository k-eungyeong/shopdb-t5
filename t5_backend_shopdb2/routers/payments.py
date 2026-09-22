from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])


class DevPaymentApprove(BaseModel):
    order_id: int
    payment_method: str = "CARD"


@router.get("/order/{order_id}")
def get_payment_order(order_id: int, current_user: dict = Depends(get_current_user)):
    with engine.connect() as conn:
        order = conn.execute(text("""
            SELECT order_id, order_no, order_status, product_amount, discount_amount, shipping_amount,
                   total_amount, receiver_name, receiver_phone, zipcode, shipping_address1,
                   shipping_address2, ordered_at
            FROM orders
            WHERE order_id=:order_id AND buyer_user_id=:user_id
        """), {"order_id": order_id, "user_id": current_user["user_id"]}).mappings().first()
        if order is None:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
        items = conn.execute(text("""
            SELECT order_item_id, product_id, variant_id, product_name_snapshot, sku_snapshot,
                   quantity, unit_price, item_amount, item_status
            FROM order_items WHERE order_id=:order_id ORDER BY order_item_id
        """), {"order_id": order_id}).mappings().all()
        payment = conn.execute(text("""
            SELECT payment_id, payment_method, payment_status, approved_amount, approved_at
            FROM payments WHERE order_id=:order_id ORDER BY payment_id DESC LIMIT 1
        """), {"order_id": order_id}).mappings().first()
    return {**dict(order), "items": [dict(i) for i in items], "payment": dict(payment) if payment else None}


@router.post("/dev-approve")
def approve_dev_payment(payload: DevPaymentApprove, current_user: dict = Depends(get_current_user)):
    """학습용 결제 승인. 실제 카드번호나 PG 결제 API를 호출하지 않습니다."""
    method = payload.payment_method.upper()
    if method not in {"CARD", "TRANSFER", "EASY_PAY"}:
        raise HTTPException(status_code=400, detail="지원하지 않는 결제 방법입니다.")

    user_id = current_user["user_id"]
    with engine.begin() as conn:
        order = conn.execute(text("""
            SELECT order_id, order_no, org_id, order_status, total_amount
            FROM orders
            WHERE order_id=:order_id AND buyer_user_id=:user_id
            FOR UPDATE
        """), {"order_id": payload.order_id, "user_id": user_id}).mappings().first()
        if order is None:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
        if order["order_status"] == "PAID":
            raise HTTPException(status_code=409, detail="이미 결제가 완료된 주문입니다.")
        if order["order_status"] != "PAYMENT_PENDING":
            raise HTTPException(status_code=400, detail=f"현재 주문 상태({order['order_status']})에서는 결제할 수 없습니다.")

        items = conn.execute(text("""
            SELECT order_item_id, product_id, variant_id, quantity
            FROM order_items WHERE order_id=:order_id ORDER BY order_item_id
        """), {"order_id": payload.order_id}).mappings().all()
        if not items:
            raise HTTPException(status_code=400, detail="주문 상품이 없습니다.")

        # 결제 직전에 재고를 다시 잠그고 확인합니다. 성공할 때만 stock_quantity를 차감합니다.
        for item in items:
            inventory = conn.execute(text("""
                SELECT inventory_id, org_id, stock_quantity, reserved_quantity
                FROM inventories
                WHERE variant_id=:variant_id
                  AND (stock_quantity-reserved_quantity) >= :quantity
                ORDER BY (org_id=:order_org_id) DESC, inventory_id ASC
                LIMIT 1
                FOR UPDATE
            """), {"variant_id": item["variant_id"], "quantity": item["quantity"], "order_org_id": order["org_id"]}).mappings().first()
            if inventory is None:
                raise HTTPException(status_code=400, detail="결제 직전 재고 확인에서 품절된 상품이 발견되었습니다.")
            conn.execute(text("""
                UPDATE inventories SET stock_quantity=stock_quantity-:quantity
                WHERE inventory_id=:inventory_id
            """), {"quantity": item["quantity"], "inventory_id": inventory["inventory_id"]})

        payment_key = f"dev_{uuid4().hex}"
        transaction_key = f"devtx_{uuid4().hex}"
        idempotency_key = f"idem_{uuid4().hex}"
        payment_result = conn.execute(text("""
            INSERT INTO payments
                (order_id, pg_provider, payment_key, pg_order_id, customer_key,
                 payment_type, payment_method, payment_status, requested_amount,
                 approved_amount, cancelled_amount, balance_amount, currency,
                 requested_at, approved_at)
            VALUES
                (:order_id, 'DEV', :payment_key, :order_no, :customer_key,
                 'NORMAL', :payment_method, 'DONE', :amount,
                 :amount, 0, 0, 'KRW', NOW(), NOW())
        """), {
            "order_id": order["order_id"],
            "payment_key": payment_key,
            "order_no": order["order_no"],
            "customer_key": f"user-{user_id}",
            "payment_method": method,
            "amount": order["total_amount"],
        })
        payment_id = payment_result.lastrowid
        conn.execute(text("""
            INSERT INTO payment_transactions
                (payment_id, transaction_key, transaction_type, transaction_status,
                 transaction_amount, pg_transaction_id, idempotency_key, request_json, response_json)
            VALUES
                (:payment_id, :transaction_key, 'APPROVE', 'SUCCESS', :amount,
                 :transaction_key, :idempotency_key,
                 JSON_OBJECT('mode','development','orderId',:order_no,'method',:payment_method),
                 JSON_OBJECT('status','DONE'))
        """), {
            "payment_id": payment_id,
            "transaction_key": transaction_key,
            "amount": order["total_amount"],
            "idempotency_key": idempotency_key,
            "order_no": order["order_no"],
            "payment_method": method,
        })
        conn.execute(text("UPDATE orders SET order_status='PAID' WHERE order_id=:order_id"), {"order_id": order["order_id"]})
        conn.execute(text("UPDATE order_items SET item_status='PAID' WHERE order_id=:order_id"), {"order_id": order["order_id"]})

        # 결제가 완료된 상품은 현재 회원의 장바구니에서 제거합니다.
        for item in items:
            conn.execute(text("""
                DELETE FROM t5_carts
                WHERE user_id=:user_id AND product_id=:product_id AND variant_id=:variant_id
            """), {"user_id": user_id, "product_id": item["product_id"], "variant_id": item["variant_id"]})

    return {
        "message": "개발용 결제가 승인되었습니다.",
        "payment_id": payment_id,
        "payment_status": "DONE",
        "order_status": "PAID",
        "approved_amount": order["total_amount"],
    }
