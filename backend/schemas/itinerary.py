from datetime import datetime
from pydantic import BaseModel, Field
from backend.schemas.place import PlaceResponse


class ItineraryItemBase(BaseModel):
    place_id: int | None = Field(default=None, description="ID địa điểm ghé thăm")
    day_number: int = Field(default=1, ge=1, description="Ngày thứ mấy trong chuyến đi")
    order_index: int = Field(default=1, ge=1, description="Thứ tự trong ngày")
    time_slot: str | None = Field(default=None, max_length=50, description="Khung giờ (vd: 08:30 - 10:30)")
    notes: str | None = Field(default=None, description="Ghi chú hoạt động")
    estimated_cost: float = Field(default=0.0, ge=0.0, description="Chi phí dự kiến (VND)")


class ItineraryItemCreate(ItineraryItemBase):
    pass


class ItineraryItemUpdate(BaseModel):
    place_id: int | None = None
    day_number: int | None = Field(default=None, ge=1)
    order_index: int | None = Field(default=None, ge=1)
    time_slot: str | None = None
    notes: str | None = None
    estimated_cost: float | None = Field(default=None, ge=0.0)


class ItineraryItemResponse(ItineraryItemBase):
    id: int
    itinerary_id: int
    place: PlaceResponse | None = None

    class Config:
        from_attributes = True


class ItineraryBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=150, description="Tiêu đề lịch trình (vd: Khám phá Đà Nẵng 3 ngày 2 đêm)")
    description: str | None = Field(default=None, description="Mô tả chi tiết chuyến đi")
    start_date: str | None = Field(default=None, description="Ngày bắt đầu (YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="Ngày kết thúc (YYYY-MM-DD)")
    total_days: int = Field(default=1, ge=1, le=30, description="Tổng số ngày dự kiến")
    budget_level: int = Field(default=2, ge=1, le=5, description="Mức ngân sách (1: Tiết kiệm đến 5: Cao cấp)")
    status: str = Field(default="planning", description="Trạng thái: planning, ongoing, completed, archived")


class ItineraryCreate(ItineraryBase):
    items: list[ItineraryItemCreate] = Field(default_factory=list, description="Danh sách các điểm dừng trong lịch trình")


class ItineraryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    total_days: int | None = Field(default=None, ge=1, le=30)
    budget_level: int | None = Field(default=None, ge=1, le=5)
    status: str | None = Field(default=None, description="planning, ongoing, completed, archived")


class ItineraryResponse(ItineraryBase):
    id: int
    user_id: int
    item_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ItineraryDetailResponse(ItineraryBase):
    id: int
    user_id: int
    items: list[ItineraryItemResponse] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class ItineraryGenerateRequest(BaseModel):
    days: int = Field(default=2, ge=1, le=7, description="Số ngày muốn đi du lịch Đà Nẵng (1-7 ngày)")
    budget_level: int = Field(default=2, ge=1, le=5, description="Mức chi tiêu từ 1 đến 5")
    travel_style: str = Field(default="Khám phá", description="Phong cách: Khám phá, Nghỉ dưỡng, Ẩm thực, Check-in")
    preferred_categories: list[str] = Field(
        default_factory=lambda: ["tourist_attraction", "cafe", "restaurant"],
        description="Các danh mục yêu thích"
    )
    title: str | None = Field(default=None, description="Tiêu đề tuỳ chỉnh nếu muốn")


class ItineraryListResponse(BaseModel):
    total: int
    itineraries: list[ItineraryResponse]
