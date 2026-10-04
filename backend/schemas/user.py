from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True