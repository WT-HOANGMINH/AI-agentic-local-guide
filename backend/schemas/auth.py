from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="Email đăng nhập của người dùng")
    password: str = Field(..., min_length=1, description="Mật khẩu của người dùng")


class LoginResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer Token")
    token_type: str = Field(default="bearer", description="Loại token")
    user_id: int = Field(..., description="ID của người dùng")
    username: str = Field(..., description="Tên người dùng")
    email: EmailStr = Field(..., description="Email người dùng")
    role: str = Field(..., description="Vai trò người dùng (user / admin)")


class TokenPayload(BaseModel):
    sub: str | None = None
    username: str | None = None
    role: str | None = None
    exp: int | None = None