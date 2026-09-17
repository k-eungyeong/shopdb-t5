"""필수 또는 선택적으로 JWT 회원 정보를 가져오는 의존성."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from auth.security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: int
    role: str | None = None


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser | None:
    """토큰이 없으면 비회원, 있으면 검증된 회원을 반환합니다."""

    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 올바른 사용자 정보가 없습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return CurrentUser(user_id=user_id, role=payload.get("role"))


def get_current_user(
    current_user: CurrentUser | None = Depends(get_optional_current_user),
) -> CurrentUser:
    """로그인이 반드시 필요한 API에서 사용합니다."""

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요한 기능입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user
