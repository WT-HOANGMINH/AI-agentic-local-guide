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


# Khoi tao ung dung FastAPI
app = FastAPI(
    title="Agentic AI Local Guide",
    description="Hệ thống Hướng dẫn Du lịch Thông minh Đà Nẵng tích hợp Trí tuệ Nhân tạo Đa tác nhân (Agentic AI), Lập lịch trình & Quản lý Điểm đến.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ==============================================================
# API Validation & Global Error Handling
# ==============================================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Format lỗi xác thực dữ liệu Pydantic thành chuẩn phản hồi thống nhất, thân thiện.
    """
    details = []
    for error in exc.errors():
        loc = " -> ".join([str(x) for x in error.get("loc", []) if x != "body"])
        msg = error.get("msg", "Dữ liệu không hợp lệ")
        details.append({
            "field": loc or "request_body",
            "message": msg,
            "type": error.get("type")
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Lỗi xác thực dữ liệu đầu vào (Validation Error)",
            "status_code": 422,
            "details": details
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Chuẩn hóa toàn bộ HTTPException của ứng dụng thành định dạng nhất quán.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code
        },
        headers=getattr(exc, "headers", None)
    )


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    """
    Bắt mọi ngoại lệ chưa được xử lý để ngăn chặn lộ thông tin nội bộ và crash Windows CP1252.
    """
    safe_msg = str(exc).encode("ascii", "replace").decode("ascii")
    print(f"[Internal Server Error] {request.method} {request.url.path}: {safe_msg[:150]}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Đã xảy ra sự cố nội bộ trên máy chủ. Vui lòng liên hệ quản trị viên.",
            "status_code": 500
        }
    )


# Cau hinh CORS de Frontend ket noi voi Backend
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
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dang ky cac API routes
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(places_router)
app.include_router(preferences_router)
app.include_router(recommendations_router)
app.include_router(itineraries_router)

# Mount Frontend static files tai /app de truy cap truc tiep tren trinh duyet
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend_app")



# Khoi tao database an toan khi ung dung bat dau
@app.on_event("startup")
def startup_event():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized successfully.")

        from backend.database import SessionLocal
        from backend.services.auth_service import get_password_hash

        db = SessionLocal()
        try:
            # Khoi tao tai khoan Admin mau neu chua co tai khoan nao
            if db.query(User).count() == 0:
                demo_user = User(
                    username="admin",
                    email="admin@localguide.vn",
                    password=get_password_hash("admin123"),
                    role="admin",
                    is_active=True
                )
                db.add(demo_user)
                db.commit()
                print("[Seeder] Da tao tai khoan mau: admin@localguide.vn / admin123")

            # Khoi tao cac dia diem Da Nang mau neu database chua co
            if db.query(Place).count() == 0:
                initial_places = [
                    Place(
                        name="Cầu Rồng Đà Nẵng",
                        category="tourist_attraction",
                        address="Đường Nguyễn Văn Linh, P. Phước Ninh, Q. Hải Châu, Đà Nẵng",
                        description="Biểu tượng kiến trúc độc đáo của thành phố với khả năng phun lửa và phun nước vào 21:00 tối thứ 7 và Chủ nhật hàng tuần.",
                        latitude=16.0611,
                        longitude=108.2272,
                        price_level=1,
                        opening_hours="Mở cả ngày (Phun lửa 21:00 Thứ 7 & CN)",
                        is_active=True
                    ),
                    Place(
                        name="Sun World Bà Nà Hills & Cầu Vàng",
                        category="tourist_attraction",
                        address="Xã Hòa Phú, Huyện Hòa Vang, Đà Nẵng",
                        description="Quần thể du lịch nghỉ dưỡng trên đỉnh núi Chúa với Cầu Vàng trứ danh thế giới, Làng Pháp cổ kính và khí hậu 4 mùa trong 1 ngày.",
                        latitude=15.9988,
                        longitude=107.9877,
                        price_level=4,
                        opening_hours="07:30 - 21:30 hàng ngày",
                        is_active=True
                    ),
                    Place(
                        name="Chùa Linh Ứng - Bán Đảo Sơn Trà",
                        category="tourist_attraction",
                        address="Bãi Bụt, Bán đảo Sơn Trà, P. Thọ Quang, Q. Sơn Trà, Đà Nẵng",
                        description="Ngôi chùa thanh tịnh hướng biển với tượng Phật Bà Quan Âm cao 67 mét sừng sững nhìn ra biển Đông và toàn cảnh vịnh Đà Nẵng.",
                        latitude=16.1002,
                        longitude=108.2758,
                        price_level=1,
                        opening_hours="06:00 - 20:30 hàng ngày",
                        is_active=True
                    ),
                    Place(
                        name="Bãi biển Mỹ Khê",
                        category="tourist_attraction",
                        address="Đường Võ Nguyên Giáp, P. Phước Mỹ, Q. Sơn Trà, Đà Nẵng",
                        description="Được tạp chí Forbes bình chọn là một trong những bãi biển quyến rũ nhất hành tinh với bãi cát trắng mịn và làn nước trong xanh.",
                        latitude=16.0594,
                        longitude=108.2464,
                        price_level=1,
                        opening_hours="Mở cả ngày",
                        is_active=True
                    ),
                    Place(
                        name="Bánh Xèo Tôm Nhảy Bà Dưỡng",
                        category="restaurant",
                        address="K280/23 Hoàng Diệu, P. Bình Hiên, Q. Hải Châu, Đà Nẵng",
                        description="Thương hiệu bánh xèo giòn rụm nổi tiếng nhiều thập kỷ tại Đà Nẵng, nước chấm gan mè béo ngậy đặc trưng kèm nem lụi thơm lừng.",
                        latitude=16.0592,
                        longitude=108.2173,
                        price_level=2,
                        opening_hours="09:30 - 21:30",
                        is_active=True
                    ),
                    Place(
                        name="Mì Quảng Bà Mua",
                        category="restaurant",
                        address="19-21 Trần Bình Trọng, Q. Hải Châu, Đà Nẵng",
                        description="Đặc sản mì Quảng gia truyền với tôm thịt đậm đà, trứng cút, gà ta và rau sống tươi ngon cùng bánh tráng mè nướng giòn.",
                        latitude=16.0645,
                        longitude=108.2198,
                        price_level=2,
                        opening_hours="06:30 - 22:00",
                        is_active=True
                    ),
                    Place(
                        name="Trình Cà Phê - Không Gian Xanh & Vintage",
                        category="cafe",
                        address="34/4 Nguyễn Hữu Thọ, P. Hòa Thuận Nam, Q. Hải Châu, Đà Nẵng",
                        description="Quán cà phê mộc mạc phong cách vintage với cà phê bơ đặc sản béo ngậy, sân vườn xanh mát yên tĩnh để làm việc và thư giãn.",
                        latitude=16.0489,
                        longitude=108.2091,
                        price_level=2,
                        opening_hours="07:00 - 22:30",
                        is_active=True
                    ),
                    Place(
                        name="Wonderlust Danang - Cà phê Concept",
                        category="cafe",
                        address="96 Trần Phú, P. Hải Châu 1, Q. Hải Châu, Đà Nẵng",
                        description="Không gian kiến trúc mở hiện đại ngập tràn ánh sáng tự nhiên với trần kính lớn, đồ uống thanh mát và bánh ngọt chuẩn vị.",
                        latitude=16.0691,
                        longitude=108.2235,
                        price_level=2,
                        opening_hours="07:30 - 23:00",
                        is_active=True
                    ),
                    Place(
                        name="Chợ Hàn Đà Nẵng",
                        category="shopping",
                        address="119 Đường Trần Phú, P. Hải Châu 1, Q. Hải Châu, Đà Nẵng",
                        description="Khu chợ truyền thống sầm uất ngay trung tâm thành phố, thiên đường mua sắm đặc sản Đà Nẵng như chả bò, mắm nêm, mực rim và quà lưu niệm.",
                        latitude=16.0682,
                        longitude=108.2248,
                        price_level=2,
                        opening_hours="06:00 - 19:00",
                        is_active=True
                    ),
                    Place(
                        name="Chợ Đêm Sơn Trà",
                        category="shopping",
                        address="Đường Mai Hắc Đế, P. An Hải Trung, Q. Sơn Trà, Đà Nẵng (gần Cầu Rồng)",
                        description="Khu chợ đêm sôi động với hàng trăm gian hàng ẩm thực đường phố, hải sản nướng thơm nức mũi và đồ thủ công mỹ nghệ.",
                        latitude=16.0617,
                        longitude=108.2325,
                        price_level=2,
                        opening_hours="18:00 - 24:00 hàng ngày",
                        is_active=True
                    )
                ]
                db.add_all(initial_places)
                db.commit()
                print(f"[Seeder] Da nap thanh cong {len(initial_places)} dia diem vao Database.")
        finally:
            db.close()

    except Exception as error:
        print(f"Database connection warning on startup: {error}")



# API trang chu
@app.get("/")
def home():
    return {
        "message": "Agentic AI Local Guide is running!"
    }


# API kiem tra Backend
@app.get("/health")
def health():
    return {
        "status": "OK"
    }


# API kiem tra ket noi MySQL
@app.get("/db-test")
def database_test():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "OK",
            "database": "MySQL connected successfully"
        }

    except Exception as error:
        print(f"Database connection error: {error}")

        return {
            "status": "ERROR",
            "message": "Unable to connect to the database"
        }