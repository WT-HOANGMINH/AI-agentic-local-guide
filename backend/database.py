
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

APP_ENV = os.getenv(
    "APP_ENV",
    "development"
).lower()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    ""
).strip()


def normalize_url(url):
    if url.startswith("postgres://"):
        return url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1
        )

    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1
        )

    return url


def connect_database(url):
    options = {
        "pool_pre_ping": True,
        "echo": False
    }

    if url.startswith("sqlite"):
        options["connect_args"] = {
            "check_same_thread": False
        }

    elif url.startswith("postgresql+psycopg://"):
        options["connect_args"] = {
            "connect_timeout": 10
        }

    db_engine = create_engine(
        url,
        **options
    )

    print("[Database] Checking connection...", flush=True)

    with db_engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    print("[Database] Connection verified.", flush=True)

    return db_engine


if APP_ENV == "production":

    if not DATABASE_URL:
        raise RuntimeError(
            "Production requires DATABASE_URL"
        )

    DATABASE_URL = normalize_url(
        DATABASE_URL
    )

    if not DATABASE_URL.startswith(
        "postgresql+psycopg://"
    ):
        raise RuntimeError(
            "Production requires PostgreSQL"
        )

    # Production: khong fallback sang SQLite
    engine = connect_database(
        DATABASE_URL
    )

    print(
        "[Database] PostgreSQL connected successfully"
    )

else:

    # Local: dung SQLite neu chua cau hinh DB
    if not DATABASE_URL:
        DATABASE_URL = "sqlite:///./local_guide.db"

    DATABASE_URL = normalize_url(
        DATABASE_URL
    )

    try:
        engine = connect_database(
            DATABASE_URL
        )

        print(
            "[Database] Local database connected"
        )

    except Exception as error:
        print(
            "[Database] Local connection failed:",
            type(error).__name__
        )

        DATABASE_URL = "sqlite:///./local_guide.db"

        engine = connect_database(
            DATABASE_URL
        )

        print(
            "[Database] Local SQLite activated"
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
