from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import bindparam, text

from database import engine
from security import get_current_user

router = APIRouter(prefix="/admin/orders", tags=["admin-orders"])


class ShippingStatusUpdate(BaseModel):
    status: str


class BulkShippingStatusUpdate(BaseModel):
    order_ids: list[int] = Field(min_length=1, max_length=100)
    status: str


SHIPPING_RANK = {
    "PAID": 0,
    "PREPARING": 1,
    "SHIPPING": 2,
    "DELIVERED": 3,
}
EDITABLE_TARGETS = {"PREPARING", "SHIPPING", "DELIVERED"}
DELIVERY_VISIBLE_STATUSES = ("PAID", "PREPARING", "SHIPPING", "DELIVERED", "COMPLETED")


def _require_admin(current_user: dict = Depends(get_current_user)):
    """현재 로그인 사용자가 ADMIN 권한인지 서버에서 다시 확인합니다."""
    if "ADMIN" not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return current_user


def _validate_transition(current: str, target: str) -> None:
    """배송상태는 앞으로만 이동하게 하여 실수로 이전 단계로 되돌아가는 것을 막습니다."""
    if target not in EDITABLE_TARGETS:
        raise HTTPException(
            status_code=400,
            detail="배송 상태는 상품준비중, 배송중, 배송완료 중에서 선택해주세요.",
        )
    if current in {"CANCELLED", "REFUNDED", "COMPLETED"}:
        raise HTTPException(status_code=400, detail="취소·환불·구매완료 주문은 배송 상태를 변경할 수 없습니다.")
    if current not in SHIPPING_RANK:
        raise HTTPException(status_code=400, detail="결제가 완료된 주문부터 배송 상태를 변경할 수 있습니다.")
    if SHIPPING_RANK[target] < SHIPPING_RANK[current]:
        raise HTTPException(status_code=400, detail="배송 상태를 이전 단계로 되돌릴 수 없습니다.")


@router.get("")
def get_admin_orders(current_user: dict = Depends(_require_admin)):
    """
    관리자가 다른 회원들의 배송 대상 주문을 한 화면에서 조회합니다.

    새 배송 테이블을 만들지 않고 orders.order_status를 배송 진행 상태로 사용합니다.
    결제 전/취소/환불 주문은 배송관리 대상이 아니므로 목록에서 제외합니다.
    """
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                o.order_id,
                o.order_no,
                o.order_status,
                o.total_amount,
                o.receiver_name,
                o.receiver_phone,
                o.zipcode,
                o.shipping_address1,
                o.shipping_address2,
                o.ordered_at,
                o.updated_at,
                o.buyer_user_id,
                u.login_id AS buyer_login_id,
                u.user_name AS buyer_name,
                COUNT(oi.order_item_id) AS item_count,
                GROUP_CONCAT(
                    DISTINCT oi.product_name_snapshot
                    ORDER BY oi.order_item_id
                    SEPARATOR ', '
                ) AS product_names
            FROM orders o
            INNER JOIN users u ON u.user_id = o.buyer_user_id
            LEFT JOIN order_items oi ON oi.order_id = o.order_id
            WHERE o.buyer_user_id <> :admin_user_id
              AND o.order_status IN ('PAID', 'PREPARING', 'SHIPPING', 'DELIVERED', 'COMPLETED')
            GROUP BY
                o.order_id, o.order_no, o.order_status, o.total_amount,
                o.receiver_name, o.receiver_phone, o.zipcode,
                o.shipping_address1, o.shipping_address2,
                o.ordered_at, o.updated_at, o.buyer_user_id,
                u.login_id, u.user_name
            ORDER BY
                FIELD(o.order_status, 'SHIPPING', 'PREPARING', 'PAID', 'DELIVERED', 'COMPLETED'),
                o.ordered_at DESC,
                o.order_id DESC
        """), {"admin_user_id": current_user["user_id"]}).mappings().all()

    items = [dict(row) for row in rows]
    counts = {status: 0 for status in DELIVERY_VISIBLE_STATUSES}
    for item in items:
        status = item["order_status"]
        if status in counts:
            counts[status] += 1

    return {
        "count": len(items),
        "counts": counts,
        "items": items,
    }


@router.patch("/bulk-shipping-status")
def bulk_update_shipping_status(
    payload: BulkShippingStatusUpdate,
    current_user: dict = Depends(_require_admin),
):
    """관리자가 선택한 여러 주문의 배송상태를 한 번에 변경합니다."""
    target = payload.status.strip().upper()
    # 같은 주문번호가 중복 전달되어도 한 번만 처리합니다.
    order_ids = list(dict.fromkeys(payload.order_ids))

    if target not in EDITABLE_TARGETS:
        raise HTTPException(status_code=400, detail="변경할 배송 상태가 올바르지 않습니다.")

    stmt = text("""
        SELECT order_id, order_no, order_status, buyer_user_id
        FROM orders
        WHERE order_id IN :order_ids
        FOR UPDATE
    """).bindparams(bindparam("order_ids", expanding=True))

    with engine.begin() as conn:
        orders = conn.execute(stmt, {"order_ids": order_ids}).mappings().all()
        found = {row["order_id"] for row in orders}
        missing = [order_id for order_id in order_ids if order_id not in found]
        if missing:
            raise HTTPException(status_code=404, detail=f"찾을 수 없는 주문이 있습니다: {missing}")

        # 관리자 자신의 주문은 관리자 배송관리에서 변경하지 않습니다.
        if any(row["buyer_user_id"] == current_user["user_id"] for row in orders):
            raise HTTPException(status_code=400, detail="관리자 본인의 주문은 일괄 배송관리 대상에서 제외됩니다.")

        # 먼저 전부 검증한 뒤 UPDATE하여 일부만 변경되는 상황을 방지합니다.
        for row in orders:
            try:
                _validate_transition(row["order_status"], target)
            except HTTPException as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"주문 {row['order_no']}: {exc.detail}",
                ) from exc

        update_orders = text("""
            UPDATE orders
            SET order_status = :status
            WHERE order_id IN :order_ids
        """).bindparams(bindparam("order_ids", expanding=True))
        conn.execute(update_orders, {"status": target, "order_ids": order_ids})

        update_items = text("""
            UPDATE order_items
            SET item_status = :status
            WHERE order_id IN :order_ids
              AND item_status <> 'CANCELLED'
        """).bindparams(bindparam("order_ids", expanding=True))
        conn.execute(update_items, {"status": target, "order_ids": order_ids})

    return {
        "message": f"선택한 {len(order_ids)}건의 배송 상태를 {target}(으)로 변경했습니다.",
        "updated_count": len(order_ids),
        "order_ids": order_ids,
        "order_status": target,
    }


@router.patch("/{order_id}/shipping-status")
def update_shipping_status(
    order_id: int,
    payload: ShippingStatusUpdate,
    current_user: dict = Depends(_require_admin),
):
    """
    기존 orders.order_status 컬럼만 사용해 한 주문의 배송상태를 변경합니다.

    관리자 화면에서는 PAID → PREPARING → SHIPPING → DELIVERED 단계 중
    현재 단계와 같거나 뒤 단계로만 변경할 수 있습니다.
    """
    target = payload.status.strip().upper()

    with engine.begin() as conn:
        order = conn.execute(text("""
            SELECT order_id, order_no, order_status, buyer_user_id
            FROM orders
            WHERE order_id = :order_id
            FOR UPDATE
        """), {"order_id": order_id}).mappings().first()

        if order is None:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
        if order["buyer_user_id"] == current_user["user_id"]:
            raise HTTPException(status_code=400, detail="관리자 본인의 주문은 이 배송관리 화면에서 변경할 수 없습니다.")

        _validate_transition(order["order_status"], target)

        conn.execute(text("""
            UPDATE orders
            SET order_status = :status
            WHERE order_id = :order_id
        """), {"status": target, "order_id": order_id})

        conn.execute(text("""
            UPDATE order_items
            SET item_status = :status
            WHERE order_id = :order_id
              AND item_status <> 'CANCELLED'
        """), {"status": target, "order_id": order_id})

    return {
        "message": f"주문 {order['order_no']}의 배송 상태를 {target}으로 변경했습니다.",
        "order_id": order_id,
        "order_status": target,
    }

@router.patch("/{order_id}/correct-to-shipping")
def correct_delivered_to_shipping(
    order_id: int,
    current_user: dict = Depends(_require_admin),
):
    """관리자 실수 정정용: 배송완료 주문만 배송중으로 한 단계 되돌립니다.

    구매완료(COMPLETED) 이후에는 리뷰/정산 기준이 될 수 있으므로 되돌리지 않습니다.
    """
    with engine.begin() as conn:
        order = conn.execute(text("""
            SELECT order_id, order_no, order_status, buyer_user_id
            FROM orders WHERE order_id=:order_id FOR UPDATE
        """), {"order_id": order_id}).mappings().first()
        if order is None:
            raise HTTPException(status_code=404, detail="주문을 찾을 수 없습니다.")
        if order["buyer_user_id"] == current_user["user_id"]:
            raise HTTPException(status_code=400, detail="관리자 본인의 주문은 이 화면에서 정정할 수 없습니다.")
        if order["order_status"] != "DELIVERED":
            raise HTTPException(status_code=400, detail="배송완료 상태의 주문만 배송중으로 정정할 수 있습니다.")

        completed_item = conn.execute(text("""
            SELECT 1 FROM order_items
            WHERE order_id=:order_id AND item_status='COMPLETED' LIMIT 1
        """), {"order_id": order_id}).first()
        if completed_item:
            raise HTTPException(status_code=400, detail="구매완료된 상품이 포함되어 있어 배송상태를 되돌릴 수 없습니다.")

        conn.execute(text("UPDATE orders SET order_status='SHIPPING' WHERE order_id=:order_id"), {"order_id": order_id})
        conn.execute(text("""
            UPDATE order_items SET item_status='SHIPPING'
            WHERE order_id=:order_id AND item_status='DELIVERED'
        """), {"order_id": order_id})
    return {"message": f"주문 {order['order_no']}을 배송중 상태로 정정했습니다.", "order_id": order_id, "order_status": "SHIPPING"}
