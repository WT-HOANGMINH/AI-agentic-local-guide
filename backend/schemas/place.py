from pydantic import BaseModel, Field


class PlaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, description="Tên địa điểm")
    category: str = Field(..., min_length=1, max_length=50, description="Danh mục (tourist_attraction, restaurant, cafe, shopping...)")
    address: str = Field(..., min_length=1, max_length=255, description="Địa chỉ")
    description: str | None = Field(default=None, description="Mô tả về địa điểm")
    latitude: float | None = Field(default=None, ge=-90, le=90, description="Vĩ độ (Latitude)")
    longitude: float | None = Field(default=None, ge=-180, le=180, description="Kinh độ (Longitude)")
    price_level: int | None = Field(default=None, ge=1, le=5, description="Mức giá từ 1 đến 5")
    opening_hours: str | None = Field(default=None, max_length=100, description="Giờ mở cửa")


class PlaceCreate(PlaceBase):
    pass


class PlaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    category: str | None = Field(default=None, min_length=1, max_length=50)
    address: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    price_level: int | None = Field(default=None, ge=1, le=5)
    opening_hours: str | None = None
    is_active: bool | None = None


class PlaceResponse(PlaceBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class PlaceNearbyItem(PlaceResponse):
    distance_km: float


class PlaceListResponse(BaseModel):
    total: int
    places: list[PlaceResponse]


class PlaceNearbyResponse(BaseModel):
    total: int
    radius_km: float
    category: str | None = None
    places: list[PlaceNearbyItem]
