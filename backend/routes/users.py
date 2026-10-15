from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user, require_admin
from backend.database import get_db
from backend.models.user import User
from backend.schemas.user import (
    ChangePasswordRequest,
    UserListResponse,
    UserResponse,
    UserRoleUpdate,
    UserUpdate,
)
from backend.services.auth_service import get_password_hash, verify_password

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Xem thông tin tài khoản cá nhân"
)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """Lấy thông tin tài khoản của người dùng hiện đang đăng nhập."""
    return current_user


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Cập nhật thông tin tài khoản cá nhân"
)
def update_my_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật username hoặc email của tài khoản đang đăng nhập."""
    if update_data.username is not None and update_data.username.strip() != current_user.username:
        new_username = update_data.username.strip()
        existing = db.query(User).filter(
            User.username == new_username,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tên người dùng này đã được sử dụng bởi tài khoản khác"
            )
        current_user.username = new_username

    if update_data.email is not None and update_data.email.strip().lower() != current_user.email:
        new_email = update_data.email.strip().lower()
        existing = db.query(User).filter(
            User.email == new_email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Địa chỉ email này đã được sử dụng bởi tài khoản khác"
            )
        current_user.email = new_email

    db.commit()
    db.refresh(current_user)
    return current_user


@router.put(
    "/me/password",
    summary="Đổi mật khẩu tài khoản cá nhân"
)
def change_my_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Thay đổi mật khẩu sau khi kiểm tra mật khẩu hiện tại."""
    if not verify_password(password_data.old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không đúng"
        )

    current_user.password = get_password_hash(password_data.new_password)
    db.commit()

    return {
        "status": "success",
        "message": "Đổi mật khẩu thành công"
    }


@router.get(
    "/",
    response_model=UserListResponse,
    summary="[Admin] Danh sách người dùng"
)
def list_users(
    skip: int = Query(default=0, ge=0, description="Số lượng bản ghi bỏ qua"),
    limit: int = Query(default=50, ge=1, le=100, description="Số lượng bản ghi tối đa"),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """[Quyền Quản trị viên] Xem toàn bộ danh sách người dùng trong hệ thống."""
    query = db.query(User)
    total = query.count()
    users = query.order_by(User.id.asc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "users": users
    }


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Xem thông tin chi tiết người dùng theo ID"
)
def get_user_detail(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xem thông tin chi tiết của một người dùng (Dành cho Admin hoặc chính chủ tài khoản)."""
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem thông tin tài khoản người dùng khác"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng này"
        )

    return user


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="[Admin] Cập nhật vai trò người dùng"
)
def update_user_role(
    user_id: int,
    role_data: UserRoleUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """[Quyền Quản trị viên] Phân quyền tài khoản (user hoặc admin)."""
    if role_data.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vai trò không hợp lệ. Chỉ chấp nhận 'user' hoặc 'admin'."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng"
        )

    user.role = role_data.role
    db.commit()
    db.refresh(user)

    return user


@router.delete(
    "/{user_id}",
    summary="[Admin] Xóa người dùng"
)
def delete_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """[Quyền Quản trị viên] Xóa người dùng khỏi hệ thống."""
    if admin_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bạn không thể tự xóa tài khoản quản trị của chính mình"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng cần xóa"
        )

    db.delete(user)
    db.commit()

    return {
        "status": "success",
        "message": f"Đã xóa thành công người dùng id {user_id}"
    }
