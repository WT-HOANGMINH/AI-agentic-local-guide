from pydantic import BaseModel, Field
from backend.schemas.place import PlaceResponse


class ChatRecommendationRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Câu hỏi hoặc yêu cầu tư vấn địa điểm du lịch tại Đà Nẵng",
        example="Gợi ý cho tôi vài quán ăn ngon và quán cà phê đẹp gần Cầu Rồng"
    )
    use_preferences: bool = Field(
        default=True,
        description="Nếu đã đăng nhập, tự động tích hợp hồ sơ sở thích cá nhân vào câu trả lời"
    )
    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
        description="Vĩ độ hiện tại của người dùng (tùy chọn)"
    )
    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
        description="Kinh độ hiện tại của người dùng (tùy chọn)"
    )


class ChatRecommendationResponse(BaseModel):
    reply: str = Field(..., description="Nội dung tư vấn chi tiết từ AI Agent")
    suggested_places: list[PlaceResponse] = Field(
        default_factory=list,
        description="Danh sách các địa điểm phù hợp trong cơ sở dữ liệu Đà Nẵng"
    )
    source: str = Field(
        default="gemini_agent",
        description="Nguồn xử lý: 'gemini_agent' (AI ReAct Agent) hoặc 'smart_recommendation_engine' (Engine thông minh dự phòng)"
    )


class PersonalizedRecommendationResponse(BaseModel):
    user_id: int
    summary: str
    favorite_categories: list[str] = Field(default_factory=list)
    preferred_price_level: int | None = None
    places: list[PlaceResponse]
