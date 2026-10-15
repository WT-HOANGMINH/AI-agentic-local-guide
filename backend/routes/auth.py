from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user
from backend.database import get_db
from backend.models.user import User
from backend.schemas.auth import LoginRequest, LoginResponse
from backend.schemas.user import UserRegister, UserResponse
from backend.services.auth_service import (
    create_access_token,
    get_password_hash,
    verify_password,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới"
)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Đăng ký tài khoản người dùng mới với username, email và password.
    Mật khẩu sẽ được băm bằng thuật toán bcrypt an toàn.
    """
    existing_username = db.query(User).filter(
        User.username == user_data.username.strip()
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên người dùng (username) đã được sử dụng"
        )

    existing_email = db.query(User).filter(
        User.email == user_data.email.strip().lower()
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Địa chỉ email đã được đăng ký"
        )

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        username=user_data.username.strip(),
        email=user_data.email.strip().lower(),
        password=hashed_password,
        role="user",
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Đăng nhập nhận JWT Token"
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Đăng nhập bằng email và mật khẩu. Trả về access token JWT (Bearer).
    """
    user = db.query(User).filter(
        User.email == login_data.email.strip().lower()
    ).first()

    if not user or not verify_password(login_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị vô hiệu hóa"
        )

    access_token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin tài khoản đang đăng nhập"
)
def read_current_user(
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint bảo vệ bằng JWT Token: Trả về thông tin của tài khoản đang xác thực.
    """
    return current_user