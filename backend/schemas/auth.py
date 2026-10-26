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


class GoogleLoginRequest(BaseModel):
    credential: str | None = Field(default=None, description="Google OAuth ID Token từ Google Identity Services")
    access_token: str | None = Field(default=None, description="Google OAuth Access Token từ Google OAuth2 Client")
    email: EmailStr | None = Field(default=None, description="Email tài khoản Google")
    name: str | None = Field(default=None, description="Họ tên người dùng Google")
    picture: str | None = Field(default=None, description="Ảnh đại diện Google")
    google_id: str | None = Field(default=None, description="Google Subject ID")


class FacebookLoginRequest(BaseModel):
    access_token: str | None = Field(default=None, description="Facebook OAuth Access Token")
    signed_request: str | None = Field(default=None, description="Facebook signed_request parameter")
    email: EmailStr | None = Field(default=None, description="Email tài khoản Facebook")
    name: str | None = Field(default=None, description="Họ tên người dùng Facebook")
    picture: str | None = Field(default=None, description="Ảnh đại diện Facebook")
    facebook_id: str | None = Field(default=None, description="Facebook User ID")