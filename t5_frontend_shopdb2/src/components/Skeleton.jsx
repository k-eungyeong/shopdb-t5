import "./Skeleton.css";

// 상품 카드 모양의 로딩 스켈레톤을 count개 만큼 그립니다.
// API 응답을 기다리는 동안 화면이 멈춘 것처럼 보이지 않도록, 실제 카드와 비슷한 형태를 미리 보여줍니다.
export function ProductGridSkeleton({ count = 8 }) {
  return (
    <div className="skeleton-grid" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-card" key={i}>
          <div className="skeleton-block skeleton-card__image" />
          <div className="skeleton-card__body">
            <div className="skeleton-block" />
            <div className="skeleton-block" />
            <div className="skeleton-block" />
          </div>
        </div>
      ))}
    </div>
  );
}

// 장바구니/주문 목록처럼 세로로 나열되는 리스트용 로딩 스켈레톤입니다.
export function ListSkeleton({ count = 3 }) {
  return (
    <div className="skeleton-row" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-block" key={i} />
      ))}
    </div>
  );
}
