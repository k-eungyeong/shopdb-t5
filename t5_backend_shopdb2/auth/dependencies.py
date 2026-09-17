"""FastAPI 라우터에서 현재 로그인 사용자를 가져오는 의존성입니다."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from auth.security import decode_access_token


# Swagger의 Authorize 버튼에서 Bearer 토큰을 입력할 수 있게 합니다.
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: int
    role: str | None = None


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """Authorization 헤더의 JWT를 검증하고 로그인 사용자를 반환합니다."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요한 기능입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")

    try:
        user_id = int(subject)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 올바른 사용자 정보가 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return CurrentUser(user_id=user_id, role=payload.get("role"))
