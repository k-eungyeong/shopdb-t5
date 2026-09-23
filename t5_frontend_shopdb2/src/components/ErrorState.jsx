import "./ErrorState.css";

// 여러 화면에서 반복되던 "오류 문구만 덩그러니 표시" 패턴을 하나로 모았습니다.
// message가 없으면 아무것도 그리지 않으므로, 기존 {error && ...} 자리에 그대로 넣어 쓸 수 있습니다.
function ErrorState({ message, onRetry, retryLabel = "다시 시도" }) {
  if (!message) return null;
  return (
    <div className="error-state" role="alert">
      <span className="error-state__icon" aria-hidden="true">!</span>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="error-state__retry" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}

export default ErrorState;
