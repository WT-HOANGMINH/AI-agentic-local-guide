from datetime import datetime
from pydantic import BaseModel, Field


class UserPreferenceUpdate(BaseModel):
    favorite_categories: list[str] | None = Field(
        default=None,
        description="Danh sách danh mục yêu thích (vd: tourist_attraction, cafe, restaurant, shopping)"
    )
    preferred_price_level: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Mức giá ưu tiên (1: Bình dân đến 5: Thượng lưu)"
    )
    dietary_preferences: str | None = Field(
        default=None,
        max_length=150,
        description="Sở thích ăn uống (vd: Hải sản, Ăn chay, Không cay)"
    )
    travel_style: str | None = Field(
        default=None,
        max_length=100,
        description="Phong cách du lịch (vd: Khám phá, Nghỉ dưỡng, Tiết kiệm)"
    )
    interests: list[str] | None = Field(
        default=None,
        description="Danh sách từ khóa sở thích (vd: ['Biển', 'Check-in', 'Lịch sử'])"
    )


class UserPreferenceResponse(BaseModel):
    id: int
    user_id: int
    favorite_categories: list[str] = Field(default_factory=list)
    preferred_price_level: int | None = 2
    dietary_preferences: str | None = None
    travel_style: str | None = None
    interests: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
