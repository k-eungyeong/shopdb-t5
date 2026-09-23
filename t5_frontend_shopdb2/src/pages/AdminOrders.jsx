import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  bulkUpdateAdminShippingStatus,
  correctAdminDeliveredToShipping,
  getAdminOrders,
  updateAdminShippingStatus,
} from "../api/shopApi";
import { useAuth } from "../auth/AuthContext";
import { money, statusText } from "../utils/format";
import "./AdminOrders.css";

const shippingRank = { PAID: 0, PREPARING: 1, SHIPPING: 2, DELIVERED: 3 };
const mutableStatuses = ["PAID", "PREPARING", "SHIPPING"];
const selectableStatuses = [
  { value: "PREPARING", label: "상품준비중" },
  { value: "SHIPPING", label: "배송중" },
  { value: "DELIVERED", label: "배송완료" },
];

const filterTabs = [
  { value: "ALL", label: "전체 배송주문" },
  { value: "PAID", label: "결제완료" },
  { value: "PREPARING", label: "상품준비중" },
  { value: "SHIPPING", label: "배송중" },
  { value: "DELIVERED", label: "배송완료" },
  { value: "COMPLETED", label: "구매완료" },
];

function nextStatus(current) {
  if (current === "PAID") return "PREPARING";
  if (current === "PREPARING") return "SHIPPING";
  if (current === "SHIPPING") return "DELIVERED";
  return "";
}

function AdminOrders() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [counts, setCounts] = useState({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [selectedStatus, setSelectedStatus] = useState({});
  const [checkedIds, setCheckedIds] = useState([]);
  const [bulkStatus, setBulkStatus] = useState("SHIPPING");
  const [bulkSaving, setBulkSaving] = useState(false);
  const [filter, setFilter] = useState("ALL");
  const [keyword, setKeyword] = useState("");

  const isAdmin = user?.roles?.includes("ADMIN");

  async function load() {
    try {
      setLoading(true);
      const data = await getAdminOrders();
      setOrders(data.items || []);
      setCounts(data.counts || {});
      setSelectedStatus(
        Object.fromEntries((data.items || []).map((order) => [order.order_id, nextStatus(order.order_status)])),
      );
      setCheckedIds([]);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin]);

  const filteredOrders = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    return orders.filter((order) => {
      const statusMatch = filter === "ALL" || order.order_status === filter;
      if (!statusMatch) return false;
      if (!q) return true;

      const haystack = [
        order.order_no,
        order.buyer_name,
        order.buyer_login_id,
        order.receiver_name,
        order.receiver_phone,
        order.product_names,
        order.shipping_address1,
        order.shipping_address2,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [orders, filter, keyword]);

  const checkableVisibleIds = filteredOrders
    .filter((order) => mutableStatuses.includes(order.order_status))
    .map((order) => order.order_id);

  const allVisibleChecked =
    checkableVisibleIds.length > 0 && checkableVisibleIds.every((id) => checkedIds.includes(id));

  function toggleAllVisible() {
    if (allVisibleChecked) {
      setCheckedIds((prev) => prev.filter((id) => !checkableVisibleIds.includes(id)));
    } else {
      setCheckedIds((prev) => Array.from(new Set([...prev, ...checkableVisibleIds])));
    }
  }

  function toggleOne(orderId) {
    setCheckedIds((prev) =>
      prev.includes(orderId) ? prev.filter((id) => id !== orderId) : [...prev, orderId],
    );
  }

  async function save(order) {
    const status = selectedStatus[order.order_id];
    if (!status) return;

    if (!window.confirm(`주문 ${order.order_no}의 상태를 '${statusText[status]}'(으)로 변경할까요?`)) {
      return;
    }

    try {
      setSavingId(order.order_id);
      setNotice("");
      const result = await updateAdminShippingStatus(order.order_id, status);
      setNotice(result.message);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingId(null);
    }
  }

  async function saveBulk() {
    if (checkedIds.length === 0) {
      setError("배송 상태를 변경할 주문을 먼저 선택해주세요.");
      return;
    }

    if (!window.confirm(`선택한 ${checkedIds.length}건을 '${statusText[bulkStatus]}' 상태로 변경할까요?`)) {
      return;
    }

    try {
      setBulkSaving(true);
      setNotice("");
      setError("");
      const result = await bulkUpdateAdminShippingStatus(checkedIds, bulkStatus);
      setNotice(result.message);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBulkSaving(false);
    }
  }

  async function correctDelivered(order) {
    if (!window.confirm(`주문 ${order.order_no}을 배송중 상태로 되돌릴까요?\n관리자 실수 정정용 기능입니다.`)) return;
    try {
      setSavingId(order.order_id); setError(""); setNotice("");
      const result = await correctAdminDeliveredToShipping(order.order_id);
      setNotice(result.message); await load();
    } catch (err) { setError(err.message); } finally { setSavingId(null); }
  }

  if (!isAdmin) {
    return (
      <div className="admin-orders-page">
        <div className="admin-empty">
          <h1>관리자 전용 페이지</h1>
          <p>ADMIN 권한이 있는 계정으로 로그인해야 다른 회원의 배송 상태를 관리할 수 있습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-orders-page">
      <div className="admin-orders-title">
        <div>
          <span>ADMIN DELIVERY CENTER</span>
          <h1>회원 주문 · 배송 관리</h1>
          <p>다른 회원의 결제완료 이후 주문을 한 화면에서 조회하고 배송 상태를 변경합니다.</p>
        </div>
        <div className="admin-orders-title-actions">
          <Link to="/admin" className="admin-back-button">← 관리자센터</Link>
          <button type="button" className="admin-refresh" onClick={load} disabled={loading}>
            {loading ? "조회 중..." : "↻ 새로고침"}
          </button>
        </div>
      </div>

      <section className="admin-summary" aria-label="배송 상태 요약">
        {[
          ["PAID", "결제완료", "배송 준비가 필요한 주문"],
          ["PREPARING", "상품준비중", "포장·출고 준비 중"],
          ["SHIPPING", "배송중", "현재 배송이 진행 중"],
          ["DELIVERED", "배송완료", "고객에게 배송 완료"],
        ].map(([status, label, description]) => (
          <button
            key={status}
            type="button"
            className={`admin-summary-card ${filter === status ? "is-active" : ""}`}
            onClick={() => setFilter(status)}
          >
            <small>{description}</small>
            <strong>{counts[status] || 0}<em>건</em></strong>
            <span>{label}</span>
          </button>
        ))}
      </section>

      <section className="admin-tools">
        <div className="admin-filter-tabs">
          {filterTabs.map((tab) => (
            <button
              key={tab.value}
              type="button"
              className={filter === tab.value ? "is-active" : ""}
              onClick={() => setFilter(tab.value)}
            >
              {tab.label}
              {tab.value !== "ALL" && <b>{counts[tab.value] || 0}</b>}
            </button>
          ))}
        </div>

        <div className="admin-search-row">
          <input
            type="search"
            placeholder="주문번호, 구매자, 상품명, 배송지 검색"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
          />
          <span>검색 결과 <b>{filteredOrders.length}</b>건</span>
        </div>
      </section>

      <section className="admin-bulk-bar">
        <div>
          <strong>선택 주문 일괄 변경</strong>
          <span>{checkedIds.length}건 선택됨</span>
        </div>
        <select value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value)}>
          {selectableStatuses.map((status) => (
            <option key={status.value} value={status.value}>{status.label}</option>
          ))}
        </select>
        <button type="button" onClick={saveBulk} disabled={bulkSaving || checkedIds.length === 0}>
          {bulkSaving ? "변경 중..." : "선택 주문 상태 변경"}
        </button>
      </section>

      {notice && <div className="admin-notice admin-notice--success">✓ {notice}</div>}
      {error && <div className="admin-notice admin-notice--error">{error}</div>}

      <div className="admin-orders-table-wrap">
        <table className="admin-orders-table">
          <colgroup>
            <col className="col-check" />
            <col className="col-order" />
            <col className="col-buyer" />
            <col className="col-address" />
            <col className="col-amount" />
            <col className="col-status" />
            <col className="col-action" />
          </colgroup>
          <thead>
            <tr>
              <th className="admin-check-cell">
                <input
                  type="checkbox"
                  aria-label="현재 목록 전체 선택"
                  checked={allVisibleChecked}
                  onChange={toggleAllVisible}
                  disabled={checkableVisibleIds.length === 0}
                />
              </th>
              <th>주문 / 상품</th>
              <th>구매자</th>
              <th>받는 분 / 배송지</th>
              <th>금액</th>
              <th>현재 배송상태</th>
              <th>상태 변경</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrders.map((order) => {
              const editable = mutableStatuses.includes(order.order_status);
              const currentRank = shippingRank[order.order_status];
              const choices = selectableStatuses.filter(
                (status) => currentRank !== undefined && shippingRank[status.value] > currentRank,
              );

              return (
                <tr key={order.order_id} className={order.order_status === "SHIPPING" ? "is-shipping" : ""}>
                  <td className="admin-check-cell">
                    <input
                      type="checkbox"
                      aria-label={`${order.order_no} 선택`}
                      checked={checkedIds.includes(order.order_id)}
                      onChange={() => toggleOne(order.order_id)}
                      disabled={!editable}
                    />
                  </td>
                  <td>
                    <b>{order.order_no}</b>
                    <small>{String(order.ordered_at).slice(0, 16).replace("T", " ")} · {order.item_count}개 상품</small>
                    <small className="admin-products">{order.product_names || "상품 정보 없음"}</small>
                  </td>
                  <td>
                    <b>{order.buyer_name}</b>
                    <small>{order.buyer_login_id}</small>
                  </td>
                  <td>
                    <b>{order.receiver_name} · {order.receiver_phone}</b>
                    <small>{order.zipcode ? `[${order.zipcode}] ` : ""}{order.shipping_address1} {order.shipping_address2}</small>
                  </td>
                  <td className="admin-money">{money(order.total_amount)}</td>
                  <td>
                    <span className={`admin-status admin-status--${String(order.order_status).toLowerCase()}`}>
                      {statusText[order.order_status] || order.order_status}
                    </span>
                    {order.order_status === "SHIPPING" && <small className="admin-live-label">● 현재 배송중</small>}
                  </td>
                  <td>
                    {editable && choices.length > 0 ? (
                      <div className="admin-shipping-control">
                        <select
                          value={selectedStatus[order.order_id] || choices[0]?.value || ""}
                          onChange={(e) =>
                            setSelectedStatus((prev) => ({ ...prev, [order.order_id]: e.target.value }))
                          }
                        >
                          {choices.map((status) => (
                            <option key={status.value} value={status.value}>{status.label}</option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => save(order)}
                          disabled={savingId === order.order_id}
                        >
                          {savingId === order.order_id ? "저장 중" : "변경"}
                        </button>
                      </div>
                    ) : order.order_status === "DELIVERED" ? (
                      <div className="admin-shipping-control">
                        <button type="button" className="admin-correct-button" onClick={() => correctDelivered(order)} disabled={savingId===order.order_id}>
                          {savingId===order.order_id ? "정정 중" : "배송중으로 정정"}
                        </button>
                      </div>
                    ) : (
                      <small>변경 불가</small>
                    )}
                  </td>
                </tr>
              );
            })}

            {!loading && filteredOrders.length === 0 && (
              <tr>
                <td colSpan="7" className="admin-no-results">조건에 맞는 배송 주문이 없습니다.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="admin-orders-help">
        ※ 별도 배송 테이블 없이 <code>orders.order_status</code>를 사용합니다. 실제 택배사 송장 이동경로 조회는 포함되지 않습니다.
      </p>
    </div>
  );
}

export default AdminOrders;
