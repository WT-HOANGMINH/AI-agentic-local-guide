import mimetypes
import os

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

from backend.routes.auth import router as auth_router
from backend.routes.users import router as users_router
from backend.routes.places import router as places_router
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
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
    ],
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

        from backend.database import SessionLocal
        from backend.services.auth_service import get_password_hash

        db = SessionLocal()

        try:
            # Tao tai khoan admin mau neu chua co tai khoan
            if db.query(User).count() == 0:
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
            if db.query(Place).count() == 0:
                initial_places = [
                    Place(
                        name="Cau Rong Da Nang",
                        category="tourist_attraction",
                        address=(
                            "Duong Nguyen Van Linh, "
                            "Hai Chau, Da Nang"
                        ),
                        description=(
                            "Bieu tuong cua Da Nang, "
                            "noi tieng voi hoat dong phun lua "
                            "va phun nuoc vao mot so toi cuoi tuan."
                        ),
                        latitude=16.0611,
                        longitude=108.2272,
                        price_level=1,
                        opening_hours=(
                            "Mo ca ngay; can kiem tra lich "
                            "phun lua va phun nuoc"
                        ),
                        is_active=True,
                    ),
                    Place(
                        name="Sun World Ba Na Hills va Cau Vang",
                        category="tourist_attraction",
                        address="Hoa Vang, Da Nang",
                        description=(
                            "Khu du lich tren nui voi Cau Vang, "
                            "Lang Phap va canh quan nui."
                        ),
                        latitude=15.9988,
                        longitude=107.9877,
                        price_level=4,
                        opening_hours="Can kiem tra gio hoat dong",
                        is_active=True,
                    ),
                    Place(
                        name="Chua Linh Ung Ban Dao Son Tra",
                        category="tourist_attraction",
                        address="Bai But, Ban dao Son Tra, Da Nang",
                        description=(
                            "Ngoi chua huong bien voi tuong "
                            "Phat Ba Quan Am va tam nhin ra vinh Da Nang."
                        ),
                        latitude=16.1002,
                        longitude=108.2758,
                        price_level=1,
                        opening_hours="Can kiem tra gio tham quan",
                        is_active=True,
                    ),
                    Place(
                        name="Bai bien My Khe",
                        category="tourist_attraction",
                        address="Duong Vo Nguyen Giap, Da Nang",
                        description=(
                            "Bai bien voi bai cat dai, "
                            "phu hop tam bien va thu gian."
                        ),
                        latitude=16.0594,
                        longitude=108.2464,
                        price_level=1,
                        opening_hours="Can kiem tra dieu kien thoi tiet",
                        is_active=True,
                    ),
                    Place(
                        name="Banh Xeo Tom Nhay Ba Duong",
                        category="restaurant",
                        address="K280/23 Hoang Dieu, Da Nang",
                        description=(
                            "Quan banh xeo va nem lui dac trung "
                            "cua am thuc Da Nang."
                        ),
                        latitude=16.0592,
                        longitude=108.2173,
                        price_level=2,
                        opening_hours="Can kiem tra gio mo cua",
                        is_active=True,
                    ),
                    Place(
                        name="Mi Quang Ba Mua",
                        category="restaurant",
                        address="Tran Binh Trong, Hai Chau, Da Nang",
                        description=(
                            "Dia diem thuong thuc mi Quang, "
                            "mot mon dac san mien Trung."
                        ),
                        latitude=16.0645,
                        longitude=108.2198,
                        price_level=2,
                        opening_hours="Can kiem tra gio mo cua",
                        is_active=True,
                    ),
                    Place(
                        name="Trinh Ca Phe",
                        category="cafe",
                        address="Nguyen Huu Tho, Da Nang",
                        description=(
                            "Quan ca phe co khong gian xanh, "
                            "phong cach moc mac."
                        ),
                        latitude=16.0489,
                        longitude=108.2091,
                        price_level=2,
                        opening_hours="Can kiem tra gio mo cua",
                        is_active=True,
                    ),
                    Place(
                        name="Wonderlust Danang",
                        category="cafe",
                        address="Tran Phu, Hai Chau, Da Nang",
                        description=(
                            "Khong gian ca phe hien dai "
                            "gan khu vuc trung tam."
                        ),
                        latitude=16.0691,
                        longitude=108.2235,
                        price_level=2,
                        opening_hours="Can kiem tra gio mo cua",
                        is_active=True,
                    ),
                    Place(
                        name="Cho Han Da Nang",
                        category="shopping",
                        address="119 Tran Phu, Hai Chau, Da Nang",
                        description=(
                            "Cho truyen thong ban dac san, "
                            "thuc pham va qua luu niem."
                        ),
                        latitude=16.0682,
                        longitude=108.2248,
                        price_level=2,
                        opening_hours="Can kiem tra gio mo cua",
                        is_active=True,
                    ),
                    Place(
                        name="Cho Dem Son Tra",
                        category="shopping",
                        address="Mai Hac De, Son Tra, Da Nang",
                        description=(
                            "Khu cho dem voi cac gian hang "
                            "am thuc va hang luu niem."
                        ),
                        latitude=16.0617,
                        longitude=108.2325,
                        price_level=2,
                        opening_hours="Can kiem tra gio hoat dong",
                        is_active=True,
                    ),
                ]

                db.add_all(initial_places)
                db.commit()

                print(
                    f"[Seeder] Added {len(initial_places)} "
                    "sample places to the database."
                )

        finally:
            db.close()

    except Exception as error:
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
def home():
    return {
        "message": "Agentic AI Local Guide is running!"
    }


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