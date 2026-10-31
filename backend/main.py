import mimetypes
import os
from urllib.parse import urlsplit

from fastapi.responses import RedirectResponse
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from backend.database import engine, Base
from backend.models.user import User
from backend.models.place import Place
from backend.models.preference import UserPreference
from backend.models.itinerary import Itinerary, ItineraryItem
from backend.models.favorite import Favorite

from backend.routes.auth import router as auth_router
from backend.routes.users import router as users_router
from backend.routes.places import router as places_router
from backend.routes.favorites import router as favorites_router
from backend.routes.preferences import router as preferences_router
from backend.routes.recommendations import router as recommendations_router
from backend.routes.itineraries import router as itineraries_router
from backend.routes.intents import router as intents_router
from backend.routes.ai_guide import router as ai_guide_router
from backend.routes.agent import router as agent_router


mimetypes.add_type("text/javascript", ".js")


# ==============================================================
# Khoi tao ung dung FastAPI
# ==============================================================

app = FastAPI(
    title="Agentic AI Local Guide",
    description=(
        "He thong Huong dan Du lich Thong minh Da Nang "
        "tich hop Agentic AI, lap lich trinh va quan ly diem den."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


def _configured_https_origins():
    origins = set()
    for variable in ("FRONTEND_URL", "PUBLIC_ORIGIN"):
        configured_url = os.getenv(variable, "").strip()
        if not configured_url:
            continue

        parsed = urlsplit(configured_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            continue

        hostname = parsed.hostname.lower()
        if ":" in hostname:
            hostname = f"[{hostname}]"
        port = parsed.port
        origins.add(
            f"https://{hostname}"
            + (f":{port}" if port and port != 443 else "")
        )
    return origins


# ============================================
# CSRF PROTECTION - DANANG GUIDE
# ============================================

@app.middleware("http")
async def csrf_origin_guard(request: Request, call_next):

    unsafe_methods = {"POST", "PUT", "PATCH", "DELETE"}

    session_cookie = request.cookies.get("danang_session")

    if request.method in unsafe_methods and session_cookie:

        app_env = os.getenv("APP_ENV", "development").lower()

        if app_env == "production":
            allowed_origins = _configured_https_origins()
        else:
            allowed_origins = {
                "http://127.0.0.1:5500",
                "http://localhost:5500",
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://localhost:3000",
                "http://127.0.0.1:8000",
                "http://localhost:8000"
            }

        request_origin = request.headers.get("origin")

        if not request_origin:
            referer = request.headers.get("referer")

            if referer:
                parsed = urlsplit(referer)
                request_origin = f"{parsed.scheme}://{parsed.netloc}"

        if request_origin not in allowed_origins:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "CSRF: request origin not allowed"
                }
            )

    return await call_next(request)

# ==============================================================
# API Validation & Global Error Handling
# ==============================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    details = []

    for error in exc.errors():
        loc = " -> ".join(
            str(item)
            for item in error.get("loc", [])
            if item != "body"
        )

        details.append(
            {
                "field": loc or "request_body",
                "message": error.get(
                    "msg",
                    "Du lieu khong hop le",
                ),
                "type": error.get("type"),
            }
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation Error",
            "status_code": 422,
            "details": details,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
        },
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(
    request: Request,
    exc: Exception,
):
    safe_msg = (
        str(exc)
        .encode("ascii", "replace")
        .decode("ascii")
    )

    print(
        f"[Internal Server Error] "
        f"{request.method} {request.url.path}: "
        f"{safe_msg[:150]}"
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": (
                "Da xay ra su co noi bo tren may chu. "
                "Vui long thu lai sau."
            ),
            "status_code": 500,
        },
    )


# ==============================================================
# CORS Configuration
# ==============================================================

cors_origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8080",
    "http://localhost:8080",
]
cors_origins.extend(sorted(_configured_https_origins() - set(cors_origins)))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=(
        r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================
# Register API Routes
# ==============================================================

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(places_router)
app.include_router(favorites_router)
app.include_router(preferences_router)
app.include_router(recommendations_router)
app.include_router(itineraries_router)

# API phan loai y dinh bang mo hinh AI da huan luyen
app.include_router(intents_router)

# API AI Local Guide: phan loai cau hoi va tim dia diem
app.include_router(ai_guide_router)

# API Chat cho frontend: POST /agent/chat (dung model intent da train)
app.include_router(agent_router)


# ==============================================================
# Mount Frontend
# ==============================================================

frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend",
)

if os.path.isdir(frontend_dir):
    app.mount(
        "/app",
        StaticFiles(directory=frontend_dir, html=True),
        name="frontend_app",
    )


# ==============================================================
# Initialize Database and Seed Demo Data
# ==============================================================

@app.on_event("startup")
def startup_event():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized successfully.")

        from backend.seed_places import (
            ensure_rating_column,
            ensure_place_detail_columns,
            normalize_place_categories,
        )

        ensure_rating_column()
        ensure_place_detail_columns()
        normalize_place_categories()

        from backend.database import SessionLocal
        from backend.services.auth_service import get_password_hash

        db = SessionLocal()

        try:
            # Tao tai khoan admin mau neu chua co tai khoan
            if (
                os.getenv("APP_ENV", "development").lower() == "development"
                and os.getenv("ENABLE_DEMO_ADMIN", "false").lower() == "true"
                and db.query(User).count() == 0
            ):
                demo_user = User(
                    username="admin",
                    email="admin@localguide.vn",
                    password=get_password_hash("admin123"),
                    role="admin",
                    is_active=True,
                )

                db.add(demo_user)
                db.commit()

                print(
                    "[Seeder] Demo admin account created: "
                    "admin@localguide.vn"
                )

            # Nap dia diem mau neu bang Place dang rong
            # (de nap day du hon, chay: python -X utf8 -m backend.seed_places)
            if db.query(Place).count() == 0:
                from backend.seed_places import main as seed_places_main
                seed_places_main()
                print("[Seeder] Khoi tao danh sach dia diem day du cho Da Nang.")

        finally:
            db.close()

    
    except Exception as error:
        # Production phai dung neu khoi tao database that bai
        if os.getenv("APP_ENV", "development").lower() == "production":
            raise

        # Local: hien thi canh bao de debug
        safe_msg = (
            str(error)
            .encode("ascii", "replace")
            .decode("ascii")
        )
        print(f"Database connection warning: {safe_msg}")

# ==============================================================
# Home API
# ==============================================================


@app.get("/")
def root():
    return RedirectResponse(
        url="/app/index.html",
        status_code=302
    )

# ==============================================================
# Backend Health Check
# ==============================================================

@app.get("/health")
def health():
    return {
        "status": "OK"
    }

# ==============================================================
# MySQL Connection Test
# ==============================================================

@app.get("/db-test")
def database_test():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "OK",
            "database": "MySQL connected successfully",
        }

    except Exception as error:
        safe_msg = (
            str(error)
            .encode("ascii", "replace")
            .decode("ascii")
        )

        print(f"Database connection error: {safe_msg}")

        return {
            "status": "ERROR",
            "message": "Unable to connect to the database",
        }