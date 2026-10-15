from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from backend.database import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # Danh mục ưu tiên (lưu dạng chuỗi phân cách bởi dấu phẩy, vd: "tourist_attraction,cafe,restaurant")
    favorite_categories = Column(String(255), nullable=True)

    # Mức giá mong muốn (1: Bình dân đến 5: Cao cấp)
    preferred_price_level = Column(Integer, default=2, nullable=True)

    # Sở thích ăn uống (vd: "Hải sản, Ăn chay, Đồ ngọt, Không cay...")
    dietary_preferences = Column(String(150), nullable=True)

    # Phong cách du lịch (vd: "Khám phá, Nghỉ dưỡng, Phượt, Gia đình...")
    travel_style = Column(String(100), nullable=True)

    # Sở thích chi tiết (vd: "Bãi biển, Check-in sống ảo, Văn hóa lịch sử...")
    interests = Column(String(255), nullable=True)

    # Thời gian cập nhật
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
