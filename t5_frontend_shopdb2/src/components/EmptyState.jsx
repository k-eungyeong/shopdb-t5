import { Link } from "react-router-dom";

// 여러 페이지에서 "텍스트만 덩그러니 표시"되던 빈 상태 화면을
// 아이콘 + 안내 문구 + 이동 CTA 버튼이 있는 형태로 통일했습니다.
function EmptyState({ icon = "📦", title, description, actionTo, actionLabel }) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon" aria-hidden="true">{icon}</span>
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {actionTo && actionLabel && (
        <Link to={actionTo} className="empty-state__cta">{actionLabel}</Link>
      )}
    </div>
  );
}

export default EmptyState;
