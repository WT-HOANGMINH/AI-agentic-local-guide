import os
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user
from backend.database import get_db
from backend.models.user import User
from backend.schemas.auth import (
    FacebookLoginRequest,
    GoogleLoginRequest,
    LoginRequest,
    LoginResponse,
)
from backend.schemas.user import UserRegister, UserResponse
from backend.services.auth_service import (
    create_access_token,
    get_password_hash,
    verify_password,
)

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "1092777120272337")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "29d2dc66675c2792db4f55f17e593e4f")


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


@router.post(
    "/google",
    response_model=LoginResponse,
    summary="Đăng nhập hoặc đăng ký nhanh bằng tài khoản Google"
)
def google_login(
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Xác thực và đăng nhập người dùng bằng tài khoản Google.
    - Hỗ trợ Google ID Token (credential) từ Google Identity Services.
    - Hỗ trợ Google Access Token từ Google OAuth2 popup.
    - Hỗ trợ thông tin profile Google (email, name).
    - Tự động tạo người dùng mới trong database nếu email chưa tồn tại.
    - Phát hành access token JWT (Bearer).
    """
    email = payload.email
    name = payload.name

    # 1. Nếu có Google credential (JWT ID token), tiến hành xác thực/giải mã
    if payload.credential:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests
            idinfo = id_token.verify_oauth2_token(
                payload.credential,
                google_requests.Request(),
                GOOGLE_CLIENT_ID
            )
            email = idinfo.get("email") or email
            name = idinfo.get("name") or idinfo.get("given_name") or name
        except Exception:
            try:
                import httpx
                resp = httpx.get(
                    "https://oauth2.googleapis.com/tokeninfo",
                    params={"id_token": payload.credential},
                    timeout=5.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    email = data.get("email") or email
                    name = data.get("name") or data.get("given_name") or name
                else:
                    from jose import jwt
                    claims = jwt.get_unverified_claims(payload.credential)
                    email = claims.get("email") or email
                    name = claims.get("name") or name
            except Exception:
                try:
                    from jose import jwt
                    claims = jwt.get_unverified_claims(payload.credential)
                    email = claims.get("email") or email
                    name = claims.get("name") or name
                except Exception:
                    pass

    # 2. Nếu có access_token từ Google OAuth2 popup
    if payload.access_token and not email:
        try:
            import httpx
            resp = httpx.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {payload.access_token}"},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                email = data.get("email") or email
                name = data.get("name") or data.get("given_name") or name
        except Exception:
            pass

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không lấy được thông tin email từ tài khoản Google"
        )

    email_clean = str(email).strip().lower()
    user_name = (name or email_clean.split("@")[0]).strip()

    # 3. Tìm hoặc tạo người dùng trong DB
    user = db.query(User).filter(User.email == email_clean).first()

    if not user:
        import secrets
        import uuid
        base_username = user_name.replace(" ", "_")
        existing_user_by_name = db.query(User).filter(User.username == base_username).first()
        if existing_user_by_name:
            base_username = f"{base_username}_{uuid.uuid4().hex[:4]}"

        hashed_password = get_password_hash(secrets.token_urlsafe(16))
        user = User(
            username=base_username,
            email=email_clean,
            password=hashed_password,
            role="user",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if hasattr(user, "is_active") and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị vô hiệu hóa"
            )

    # 4. Tạo JWT access token
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
    "/google/url",
    summary="Lấy đường dẫn URL chuyển hướng Google OAuth 2.0"
)
def get_google_auth_url(redirect_uri: str | None = None):
    """
    Tạo URL đăng nhập Google OAuth 2.0 chuẩn với GOOGLE_CLIENT_ID.
    """
    import urllib.parse
    cb = redirect_uri or "http://127.0.0.1:8000/auth/google/callback"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": cb,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account"
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": cb,
        "auth_url": auth_url
    }


@router.get(
    "/google/callback",
    summary="Callback nhận mã authorization code từ Google OAuth 2.0"
)
def google_callback(
    code: str,
    redirect_to: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Xử lý mã ủy quyền (code) từ Google OAuth, đổi token bằng Client Secret,
    lấy thông tin người dùng và chuyển hướng về frontend kèm JWT token.
    """
    import httpx
    from fastapi.responses import RedirectResponse

    callback_url = "http://127.0.0.1:8000/auth/google/callback"

    # 1. Trao đổi authorization code lấy tokens
    try:
        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": callback_url,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10.0,
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi trao đổi token với Google: {resp.text}"
            )
        token_data = resp.json()
        id_token_str = token_data.get("id_token")
        access_token_str = token_data.get("access_token")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể kết nối đến Google Token API: {str(e)}"
        )

    # 2. Lấy thông tin người dùng từ Google
    email = None
    name = None
    if access_token_str:
        try:
            user_resp = httpx.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token_str}"},
                timeout=6.0
            )
            if user_resp.status_code == 200:
                user_info = user_resp.json()
                email = user_info.get("email")
                name = user_info.get("name") or user_info.get("given_name")
        except Exception:
            pass

    if not email and id_token_str:
        from jose import jwt
        claims = jwt.get_unverified_claims(id_token_str)
        email = claims.get("email")
        name = claims.get("name")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không lấy được email từ tài khoản Google"
        )

    email_clean = str(email).strip().lower()
    user_name = (name or email_clean.split("@")[0]).strip()

    # 3. Tạo hoặc lấy người dùng
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        import secrets, uuid
        base_username = user_name.replace(" ", "_")
        existing_user_by_name = db.query(User).filter(User.username == base_username).first()
        if existing_user_by_name:
            base_username = f"{base_username}_{uuid.uuid4().hex[:4]}"
        hashed_password = get_password_hash(secrets.token_urlsafe(16))
        user = User(
            username=base_username,
            email=email_clean,
            password=hashed_password,
            role="user",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4. Tạo JWT token nội bộ của DaNang Guide
    access_token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role
    })

    # Chuyển hướng về frontend (ưu tiên redirect_to nếu có, hoặc port 5500 Live Server)
    target = redirect_to or f"http://127.0.0.1:5500/frontend/login.html?token={access_token}&google_login=1"
    if "?" in target:
        final_url = f"{target}&token={access_token}&google_login=1"
    else:
        final_url = f"{target}?token={access_token}&google_login=1"

    return RedirectResponse(url=final_url)


@router.post(
    "/facebook",
    response_model=LoginResponse,
    summary="Đăng nhập hoặc đăng ký nhanh bằng tài khoản Facebook"
)
def facebook_login(
    payload: FacebookLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Xác thực và đăng nhập người dùng bằng tài khoản Facebook (App ID 1092777120272337).
    - Hỗ trợ Facebook User Access Token từ Facebook JavaScript SDK (FB.login).
    - Tự động truy vấn Facebook Graph API lấy id, name, email, avatar.
    - Hỗ trợ thông tin trực tiếp từ profile Facebook.
    - Tự động tạo người dùng mới trong database nếu chưa tồn tại.
    - Phát hành access token JWT (Bearer).
    """
    email = payload.email
    name = payload.name
    fb_id = payload.facebook_id
    picture = payload.picture

    # 1. Nếu có Facebook access_token, gọi Facebook Graph API để xác minh và lấy thông tin
    if payload.access_token:
        try:
            import httpx
            graph_url = "https://graph.facebook.com/v19.0/me"
            params = {
                "fields": "id,name,email,picture.type(large)",
                "access_token": payload.access_token
            }
            resp = httpx.get(graph_url, params=params, timeout=5.0)
            if resp.status_code == 200:
                fb_data = resp.json()
                email = fb_data.get("email") or email
                name = fb_data.get("name") or name
                fb_id = fb_data.get("id") or fb_id
                pic_data = fb_data.get("picture", {}).get("data", {})
                if pic_data.get("url"):
                    picture = pic_data.get("url")
        except Exception:
            pass

    # Facebook đôi khi không trả về email (nếu tài khoản lập bằng SĐT hoặc người dùng từ chối chia sẻ email)
    # Ta tạo email định danh duy nhất theo Facebook ID hoặc tạo email ngẫu nhiên an toàn
    if not email and fb_id:
        email = f"fb_{fb_id}@facebook.com"
    elif not email and name:
        import uuid
        email = f"fb_{uuid.uuid4().hex[:8]}@facebook.com"

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không lấy được thông tin email hoặc xác thực từ tài khoản Facebook"
        )

    email_clean = str(email).strip().lower()
    user_name = (name or email_clean.split("@")[0]).strip()

    # 2. Tìm hoặc tạo người dùng trong DB
    user = db.query(User).filter(User.email == email_clean).first()

    if not user:
        import secrets
        import uuid
        base_username = user_name.replace(" ", "_")
        existing_user_by_name = db.query(User).filter(User.username == base_username).first()
        if existing_user_by_name:
            base_username = f"{base_username}_{uuid.uuid4().hex[:4]}"

        hashed_password = get_password_hash(secrets.token_urlsafe(16))
        user = User(
            username=base_username,
            email=email_clean,
            password=hashed_password,
            role="user",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if hasattr(user, "is_active") and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tài khoản của bạn đã bị vô hiệu hóa"
            )

    # 3. Tạo JWT access token nội bộ DaNang Guide
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
    "/facebook/url",
    summary="Lấy đường dẫn URL chuyển hướng Facebook OAuth 2.0"
)
def get_facebook_auth_url(redirect_uri: str | None = None):
    """
    Tạo URL đăng nhập Facebook OAuth 2.0 chuẩn với FACEBOOK_APP_ID (1092777120272337).
    """
    import urllib.parse
    cb = redirect_uri or "http://127.0.0.1:8000/auth/facebook/callback"
    params = {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": cb,
        "response_type": "code",
        "scope": "email,public_profile"
    }
    auth_url = f"https://www.facebook.com/v19.0/dialog/oauth?{urllib.parse.urlencode(params)}"
    return {
        "client_id": FACEBOOK_APP_ID,
        "redirect_uri": cb,
        "auth_url": auth_url
    }


@router.get(
    "/facebook/callback",
    summary="Callback nhận mã authorization code từ Facebook OAuth 2.0"
)
def facebook_callback(
    code: str,
    redirect_to: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Xử lý mã ủy quyền (code) từ Facebook OAuth, đổi token bằng App Secret,
    lấy thông tin người dùng và chuyển hướng về frontend kèm JWT token.
    """
    import httpx
    from fastapi.responses import RedirectResponse

    callback_url = "http://127.0.0.1:8000/auth/facebook/callback"

    # 1. Trao đổi authorization code lấy access_token
    try:
        resp = httpx.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "client_id": FACEBOOK_APP_ID,
                "client_secret": FACEBOOK_APP_SECRET,
                "redirect_uri": callback_url,
                "code": code
            },
            timeout=10.0
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi trao đổi token với Facebook: {resp.text}"
            )
        token_data = resp.json()
        access_token_str = token_data.get("access_token")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Không thể kết nối đến Facebook Token API: {str(e)}"
        )

    # 2. Lấy thông tin user từ Facebook Graph API
    email = None
    name = None
    fb_id = None
    if access_token_str:
        try:
            user_resp = httpx.get(
                "https://graph.facebook.com/v19.0/me",
                params={
                    "fields": "id,name,email,picture.type(large)",
                    "access_token": access_token_str
                },
                timeout=6.0
            )
            if user_resp.status_code == 200:
                user_info = user_resp.json()
                email = user_info.get("email")
                name = user_info.get("name")
                fb_id = user_info.get("id")
        except Exception:
            pass

    if not email and fb_id:
        email = f"fb_{fb_id}@facebook.com"
    elif not email and name:
        import uuid
        email = f"fb_{uuid.uuid4().hex[:8]}@facebook.com"

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không lấy được thông tin email từ tài khoản Facebook"
        )

    email_clean = str(email).strip().lower()
    user_name = (name or email_clean.split("@")[0]).strip()

    # 3. Tạo hoặc lấy người dùng
    user = db.query(User).filter(User.email == email_clean).first()
    if not user:
        import secrets, uuid
        base_username = user_name.replace(" ", "_")
        existing_user_by_name = db.query(User).filter(User.username == base_username).first()
        if existing_user_by_name:
            base_username = f"{base_username}_{uuid.uuid4().hex[:4]}"
        hashed_password = get_password_hash(secrets.token_urlsafe(16))
        user = User(
            username=base_username,
            email=email_clean,
            password=hashed_password,
            role="user",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 4. Tạo JWT token nội bộ của DaNang Guide
    access_token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role
    })

    target = redirect_to or f"http://127.0.0.1:5500/frontend/login.html?token={access_token}&facebook_login=1"
    if "?" in target:
        final_url = f"{target}&token={access_token}&facebook_login=1"
    else:
        final_url = f"{target}?token={access_token}&facebook_login=1"

    return RedirectResponse(url=final_url)