from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from backend.database import get_db
from backend.models.user import User
from backend.schemas.user import UserRegister, UserResponse
from backend.schemas.auth import LoginRequest, LoginResponse


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


@router.post("/register", response_model=UserResponse)
def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    existing_username = db.query(User).filter(
        User.username == user_data.username
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already exists"
        )

    existing_email = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    hashed_password = pwd_context.hash(user_data.password)

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password=hashed_password,
        role="user"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == login_data.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not pwd_context.verify(
        login_data.password,
        user.password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    return {
        "access_token": "temporary-token",
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }