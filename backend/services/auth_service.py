import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

import bcrypt
from jose import jwt, JWTError


load_dotenv()

APP_ENV = os.getenv(
    "APP_ENV",
    "development"
).strip().lower()

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    ""
).strip()

# Production bat buoc co khoa JWT manh
if APP_ENV == "production":

    if (
        len(SECRET_KEY) < 32
        or SECRET_KEY == "agentic-ai-local-guide-secret-key"
    ):
        raise RuntimeError(
            "Production requires a strong SECRET_KEY"
        )

# Cho phep khoa cu khi kiem thu Local
elif not SECRET_KEY:
    SECRET_KEY = "agentic-ai-local-guide-secret-key"

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu người dùng nhập có khớp với mật khẩu đã hash."""
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Tạo mật khẩu đã hash bằng bcrypt."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Tạo JWT access token với thời hạn expire."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_access_token(token: str) -> dict | None:
    """Giải mã và xác minh tính hợp lệ của JWT token."""
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except JWTError:
        return None
    except Exception:
        return None