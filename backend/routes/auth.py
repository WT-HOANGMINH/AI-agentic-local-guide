
import os
import hmac
import logging
import secrets
import urllib.parse
import uuid

import httpx

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

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

logger = logging.getLogger(__name__)

# ==============================================
# CONFIGURATION
# ==============================================

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

SESSION_COOKIE = "danang_session"
STATE_COOKIE = "google_oauth_state"
FACEBOOK_STATE_COOKIE = "facebook_oauth_state"

IS_PRODUCTION = (
    os.getenv("APP_ENV", "development").lower()
    == "production"
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# ==============================================
# REGISTER
# ==============================================

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
    existing_username = db.query(User).filter(
        User.username == user_data.username.strip()
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Tên người dùng đã được sử dụng"
        )

    existing_email = db.query(User).filter(
        User.email == user_data.email.strip().lower()
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email đã được đăng ký"
        )

    new_user = User(
        username=user_data.username.strip(),
        email=user_data.email.strip().lower(),
        password=get_password_hash(
            user_data.password
        ),
        role="user",
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ==============================================
# EMAIL LOGIN
# ==============================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Đăng nhập bằng email"
)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == login_data.email.strip().lower()
    ).first()

    if not user or not verify_password(
        login_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Email hoặc mật khẩu không chính xác"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản đã bị vô hiệu hóa"
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


# ==============================================
# CURRENT USER
# ==============================================

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin người dùng"
)
def read_current_user(
    current_user: User = Depends(get_current_user)
):
    return current_user


# ==============================================
# GOOGLE OAUTH CONFIG
# ==============================================

def google_callback_url():
    return os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/google/callback"
    )


def facebook_callback_url():
    return os.getenv(
        "FACEBOOK_REDIRECT_URI",
        "http://127.0.0.1:8000/auth/facebook/callback"
    )


def _session_cookie_samesite():
    return "none" if IS_PRODUCTION else "lax"


def _oauth_redirect_url(provider, success):
    frontend_url = (
        os.getenv("FRONTEND_URL") or os.getenv("PUBLIC_ORIGIN", "")
    ).strip().rstrip("/")
    if not frontend_url:
        page = "index.html" if success else "login.html"
        query = "?auth=success" if success else f"?auth=error&provider={provider}"
        return f"/app/{page}{query}"

    parsed = urllib.parse.urlsplit(frontend_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("FRONTEND_URL must be an absolute HTTP(S) URL.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("FRONTEND_URL must not contain credentials, query, or fragment.")
    if parsed.path not in {"", "/"}:
        raise RuntimeError("FRONTEND_URL must be an origin without a path.")

    page = "index.html" if success else "login.html"
    query = (
        f"?auth=success&provider={provider}"
        if success
        else f"?auth=error&provider={provider}"
    )
    return f"{frontend_url}/{page}{query}"


def _oauth_user(db, email, name, provider):
    user = db.query(User).filter(User.email == email).first()
    if user and not user.is_active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị vô hiệu hóa")
    if user and user.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin cần dùng phương thức đăng nhập riêng",
        )
    if user is None:
        username = (
            (name.replace(" ", "_")[:35] or f"{provider}_user")
            + "_"
            + uuid.uuid4().hex[:8]
        )
        user = User(
            username=username,
            email=email,
            password=get_password_hash(secrets.token_urlsafe(32)),
            role="user",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _oauth_session_response(user, provider):
    token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
    })
    response = RedirectResponse(
        url=_oauth_redirect_url(provider, success=True),
        status_code=303,
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite=_session_cookie_samesite(),
        max_age=3600,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


# ==============================================
# DISABLE OLD GOOGLE LOGIN
# ==============================================

@router.post("/google", status_code=410)
def legacy_google_login_disabled():
    raise HTTPException(
        status_code=410,
        detail="Hãy đăng nhập Google qua /auth/google/url"
    )


# ==============================================
# GOOGLE LOGIN URL
# ==============================================

@router.get("/google/url")
def get_google_auth_url(response: Response):

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail=(
                "Google OAuth chưa được cấu hình. Hãy thiết lập "
                "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET và GOOGLE_REDIRECT_URI."
            )
        )

    state = secrets.token_urlsafe(32)

    response.set_cookie(
        key=STATE_COOKIE,
        value=state,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=600,
        path="/"
    )

    response.headers["Cache-Control"] = "no-store"

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": google_callback_url(),
        "response_type": "code",
        "scope": "openid email profile",
        "prompt": "select_account",
        "state": state
    }

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode(params)
    )

    return {
        "auth_url": auth_url
    }


@router.get("/facebook/url")
def get_facebook_auth_url(response: Response):
    app_id = os.getenv("FACEBOOK_APP_ID", "").strip()
    app_secret = os.getenv("FACEBOOK_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail=(
                "Facebook OAuth chưa được cấu hình. Hãy thiết lập "
                "FACEBOOK_APP_ID, FACEBOOK_APP_SECRET và FACEBOOK_REDIRECT_URI."
            ),
        )

    state = secrets.token_urlsafe(32)
    response.set_cookie(
        key=FACEBOOK_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=600,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    version = os.getenv("FACEBOOK_GRAPH_VERSION", "v24.0")
    params = {
        "client_id": app_id,
        "redirect_uri": facebook_callback_url(),
        "response_type": "code",
        "scope": "email,public_profile",
        "state": state,
    }
    return {
        "auth_url": (
            f"https://www.facebook.com/{version}/dialog/oauth?"
            + urllib.parse.urlencode(params)
        )
    }


# ==============================================
# GOOGLE CALLBACK
# ==============================================

@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db)
):

    # 1. Kiểm tra OAuth state
    saved_state = request.cookies.get(STATE_COOKIE)

    if not saved_state or not hmac.compare_digest(
        saved_state,
        state
    ):
        raise HTTPException(
            status_code=400,
            detail="OAuth state không hợp lệ"
        )

    # 2. Trao đổi code lấy ID Token
    try:
        token_response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": google_callback_url()
            },
            timeout=15.0
        )

        token_response.raise_for_status()

        google_id_token = (
            token_response.json().get("id_token")
        )

        if not google_id_token:
            raise ValueError(
                "Google không trả về ID Token"
            )

        # 3. Xác minh Google ID Token
        claims = id_token.verify_oauth2_token(
            google_id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Không xác minh được đăng nhập Google"
        )

    # 4. Kiểm tra email
    email = claims.get("email")
    email_verified = claims.get("email_verified")

    if not email or email_verified is not True:
        raise HTTPException(
            status_code=403,
            detail="Email Google chưa được xác minh"
        )

    email = email.strip().lower()

    name = (
        claims.get("name")
        or email.split("@")[0]
    ).strip()

    # 5. Tìm tài khoản
    user = db.query(User).filter(
        User.email == email
    ).first()

    if user and not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản đã bị vô hiệu hóa"
        )

    # Không tự liên kết Google vào admin
    if user and user.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin cần dùng phương thức đăng nhập riêng"
        )

    # 6. Tạo user nếu chưa tồn tại
    if user is None:
        username = (
            (name.replace(" ", "_")[:35] or "google_user")
            + "_"
            + uuid.uuid4().hex[:8]
        )

        user = User(
            username=username,
            email=email,
            password=get_password_hash(
                secrets.token_urlsafe(32)
            ),
            role="user",
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    # 7. Tạo JWT nội bộ
    jwt_token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role
    })

    # 8. Redirect không chứa JWT
    redirect = RedirectResponse(
        url=_oauth_redirect_url("google", success=True),
        status_code=303
    )

    # 9. Lưu JWT trong HttpOnly cookie
    redirect.set_cookie(
        key=SESSION_COOKIE,
        value=jwt_token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite=_session_cookie_samesite(),
        max_age=3600,
        path="/"
    )

    # Xóa OAuth state
    redirect.delete_cookie(
        key=STATE_COOKIE,
        path="/"
    )

    redirect.headers["Cache-Control"] = "no-store"
    redirect.headers["Referrer-Policy"] = "no-referrer"

    return redirect


@router.get("/facebook/callback")
def facebook_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error or not code or not state:
        response = RedirectResponse(
            _oauth_redirect_url("facebook", success=False),
            status_code=303,
        )
        response.delete_cookie(FACEBOOK_STATE_COOKIE, path="/")
        return response

    saved_state = request.cookies.get(FACEBOOK_STATE_COOKIE)
    if not saved_state or not hmac.compare_digest(saved_state, state):
        raise HTTPException(
            status_code=400,
            detail="Facebook OAuth state không hợp lệ",
        )

    app_id = os.getenv("FACEBOOK_APP_ID", "").strip()
    app_secret = os.getenv("FACEBOOK_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise HTTPException(
            status_code=503,
            detail="Facebook OAuth chưa được cấu hình",
        )

    graph_base = (
        "https://graph.facebook.com/"
        + os.getenv("FACEBOOK_GRAPH_VERSION", "v24.0")
    )
    try:
        token_response = httpx.get(
            f"{graph_base}/oauth/access_token",
            params={
                "client_id": app_id,
                "client_secret": app_secret,
                "redirect_uri": facebook_callback_url(),
                "code": code,
            },
            timeout=15.0,
        )
        token_response.raise_for_status()
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise ValueError("Facebook did not return an access token")

        profile_response = httpx.get(
            f"{graph_base}/me",
            params={
                "fields": "id,name,email",
                "access_token": access_token,
            },
            timeout=15.0,
        )
        profile_response.raise_for_status()
        profile = profile_response.json()
    except (httpx.HTTPError, ValueError):
        logger.exception("Facebook OAuth token/profile verification failed")
        return RedirectResponse(
            _oauth_redirect_url("facebook", success=False),
            status_code=303,
        )

    email = profile.get("email")
    if not isinstance(email, str) or not email.strip():
        return RedirectResponse(
            _oauth_redirect_url("facebook", success=False),
            status_code=303,
        )

    user = _oauth_user(
        db,
        email.strip().lower(),
        str(profile.get("name") or email.split("@")[0]).strip(),
        "facebook",
    )
    response = _oauth_session_response(user, "facebook")
    response.delete_cookie(FACEBOOK_STATE_COOKIE, path="/")
    return response


# ==============================================
# LOGOUT
# ==============================================

@router.post("/logout")
def logout():

    response = Response(
        status_code=204
    )

    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/"
    )

    return response
