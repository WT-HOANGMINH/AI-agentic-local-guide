from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.database import engine, Base
from backend.models.user import User
from backend.models.place import Place
from backend.routes.auth import router as auth_router
from backend.routes.places import router as places_router


# Khoi tao ung dung FastAPI
app = FastAPI(
    title="Agentic AI Local Guide",
    description="AI-powered local travel assistant for Da Nang",
    version="1.0.0"
)


# Cau hinh CORS de Frontend ket noi voi Backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dang ky cac API routes
app.include_router(auth_router)
app.include_router(places_router)


# Tao cac bang trong database neu chua ton tai
Base.metadata.create_all(bind=engine)


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