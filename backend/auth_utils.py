
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.services.auth_service import verify_access_token


optional_security = HTTPBearer(auto_error=False)

COOKIE_NAME = "danang_session"


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User:
    # Email Login: Bearer Token
    # Google Login: HttpOnly Cookie

    token = None

    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get(COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Bạn chưa đăng nhập"
        )

    payload = verify_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=401,
            detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn"
        )

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Token không hợp lệ"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Không tìm thấy tài khoản"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản đã bị vô hiệu hóa"
        )

    return user


def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> User | None:
    try:
        return get_current_user(
            request=request,
            credentials=credentials,
            db=db
        )
    except HTTPException:
        return None


def require_roles(allowed_roles: list[str]) -> Callable:

    def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập"
            )

        return current_user

    return role_checker


require_admin = require_roles(["admin"])
