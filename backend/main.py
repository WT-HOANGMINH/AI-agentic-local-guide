from fastapi import FastAPI
from sqlalchemy import text

from backend.database import engine, Base
from backend.models.user import User
from backend.routes.auth import router as auth_router


app = FastAPI(
    title="Agentic AI Local Guide",
    description="AI-powered local travel assistant for Da Nang",
    version="1.0.0"
)

app.include_router(auth_router)


Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "message": "Agentic AI Local Guide is running!"
    }


@app.get("/health")
def health():
    return {
        "status": "OK"
    }


@app.get("/db-test")
def database_test():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "OK",
            "database": "MySQL connected successfully"
        }

    except Exception as e:
        return {
            "status": "ERROR",
            "message": str(e)
        }