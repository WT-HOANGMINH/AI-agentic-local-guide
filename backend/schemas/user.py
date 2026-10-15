from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập (3-50 ký tự)")
    email: EmailStr = Field(..., description="Email người dùng")
    password: str = Field(..., min_length=6, description="Mật khẩu tối thiểu 6 ký tự")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool = True
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50, description="Tên đăng nhập mới")
    email: EmailStr | None = Field(default=None, description="Email mới")


class UserRoleUpdate(BaseModel):
    role: str = Field(..., description="Vai trò mới (user hoặc admin)")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, description="Mật khẩu hiện tại")
    new_password: str = Field(..., min_length=6, description="Mật khẩu mới (tối thiểu 6 ký tự)")


class UserListResponse(BaseModel):
    total: int
    users: list[UserResponse]