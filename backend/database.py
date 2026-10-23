import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

# Cấu hình chuỗi kết nối MySQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:1234@localhost:3306/agentic_local_guide"
)

# Thử kết nối MySQL, nếu chưa khởi động MySQL thì tự động chuyển sang SQLite cục bộ an toàn
try:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )
    # Kiểm tra thử kết nối
    with engine.connect() as conn:
        pass
    print("[Database] Successfully connected to MySQL Database.")
except Exception as err:
    print(f"[Database] MySQL unavailable. Activating fallback local SQLite database: sqlite:///./local_guide.db")
    DATABASE_URL = "sqlite:///./local_guide.db"
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:1234@localhost:3306/agentic_local_guide?charset=utf8mb4"
)