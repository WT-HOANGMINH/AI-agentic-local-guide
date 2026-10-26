import re
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user, get_optional_current_user
from backend.database import get_db
from backend.models.place import Place
from backend.models.preference import UserPreference
from backend.models.user import User
from backend.schemas.place import PlaceResponse
from backend.schemas.recommendation import (
    ChatRecommendationRequest,
    ChatRecommendationResponse,
    PersonalizedRecommendationResponse,
)

router = APIRouter(
    prefix="/recommendations",
    tags=["AI Recommendations"]
)


def _find_matching_places_in_db(db: Session, text: str, limit: int = 5) -> list[Place]:
    """Tìm các địa điểm trong cơ sở dữ liệu có tên hoặc danh mục xuất hiện trong văn bản hoặc câu hỏi."""
    all_places = db.query(Place).filter(Place.is_active == True).all()
    matched = []
    text_lower = text.lower()

    for p in all_places:
        if p.name.lower() in text_lower or (p.category and p.category.lower() in text_lower):
            matched.append(p)
        if len(matched) >= limit:
            break

    # Nếu không tìm thấy theo tên, lấy các địa điểm nổi bật mặc định
    if not matched:
        matched = all_places[:limit]

    return matched


@router.post(
    "/chat",
    response_model=ChatRecommendationResponse,
    summary="Hỏi đáp & Nhận gợi ý du lịch từ AI Agent (LangGraph ReAct + Gemini)"
)
def chat_with_recommendation_agent(
    req: ChatRecommendationRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint tương tác trực tiếp với AI Local Guide Agent.
    - Tự động tích hợp thông tin sở thích người dùng (nếu đã đăng nhập).
    - Sử dụng mô hình AI Agent (LangGraph + Gemini) để suy luận, tra cứu địa điểm và thời tiết.
    - Tự động kích hoạt cơ chế Smart Engine dự phòng nếu chưa cấu hình GEMINI_API_KEY hoặc mất kết nối.
    """
    user_prompt = req.message.strip()
    user_context = ""
    user_pref = None

    if current_user and req.use_preferences:
        user_pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
        if user_pref:
            favs = user_pref.favorite_categories or "Chung"
            price = f"₫{'₫' * max(0, min(user_pref.preferred_price_level or 2, 5) - 1)}"
            style = user_pref.travel_style or "Tự do"
            diet = user_pref.dietary_preferences or "Bình thường"
            user_context = (
                f"\n[Ghi chú sở thích của du khách: Danh mục ưu tiên={favs}, "
                f"Mức chi tiêu={price}, Phong cách={style}, Khẩu vị={diet}]"
            )

    full_agent_message = f"{user_prompt}{user_context}"

    try:
        # Thử gọi LangGraph AI Agent từ backend.agent
        from backend.agent import ask_agent
        agent_reply = ask_agent(full_agent_message)

        # Trích xuất các địa điểm liên quan từ cơ sở dữ liệu để gửi kèm cho giao diện
        suggested_places = _find_matching_places_in_db(db, agent_reply + " " + user_prompt, limit=5)

        return {
            "reply": agent_reply,
            "suggested_places": suggested_places,
            "source": "gemini_agent"
        }

    except Exception as agent_error:
        # Co che Smart Recommendation Engine du phong khi Gemini API chua co key hoac loi mang
        clean_err = str(agent_error).encode("ascii", "replace").decode("ascii")
        print(f"[Recommendation] AI Agent fallback activated: {clean_err[:120]}")

        # Tìm địa điểm phù hợp trong database
        query = db.query(Place).filter(Place.is_active == True)

        # Lọc theo sở thích nếu có
        if user_pref and user_pref.favorite_categories:
            cat_list = [c.strip().lower() for c in user_pref.favorite_categories.split(",") if c.strip()]
            if cat_list:
                query = query.filter(Place.category.in_(cat_list))

        matched_places = query.limit(4).all()
        if not matched_places:
            matched_places = db.query(Place).filter(Place.is_active == True).limit(4).all()

        places_bullets = "\n".join([
            f"- **{p.name}** ({p.category}): {p.address}. *{p.description or 'Địa điểm hấp dẫn tại Đà Nẵng.'}*"
            for p in matched_places
        ])

        pref_note = ""
        if current_user and user_pref:
            pref_note = f"\n*(Gợi ý được điều chỉnh dựa trên hồ sơ sở thích của bạn: phong cách {user_pref.travel_style or 'tự do'})*"

        fallback_reply = (
            f"Chào bạn! Tôi là trợ lý du lịch Đà Nẵng Local Guide. "
            f"Dưới đây là một số gợi ý địa điểm tuyệt vời nhất tại Đà Nẵng phù hợp với yêu cầu '{user_prompt}':\n\n"
            f"{places_bullets}\n\n"
            f"💡 **Mẹo du lịch:** Bạn có thể nhấp vào từng thẻ địa điểm trên bản đồ tương tác để xem chi tiết hướng dẫn đường đi qua Google Maps.{pref_note}"
        )

        return {
            "reply": fallback_reply,
            "suggested_places": matched_places,
            "source": "smart_recommendation_engine"
        }


@router.get(
    "/for-me",
    response_model=PersonalizedRecommendationResponse,
    summary="[Protected] Lấy danh sách địa điểm gợi ý theo hồ sơ sở thích cá nhân"
)
def get_personalized_recommendations(
    limit: int = Query(default=6, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Phân tích hồ sơ sở thích của người dùng và lọc ra danh sách địa điểm phù hợp nhất:
    - Lọc theo danh mục yêu thích (tourist_attraction, restaurant, cafe, shopping).
    - Lọc theo mức giá tối đa người dùng mong muốn.
    """
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()

    query = db.query(Place).filter(Place.is_active == True)

    fav_categories = []
    max_price = 5

    if pref:
        if pref.favorite_categories:
            fav_categories = [c.strip().lower() for c in pref.favorite_categories.split(",") if c.strip()]
            if fav_categories:
                query = query.filter(Place.category.in_(fav_categories))

        if pref.preferred_price_level:
            max_price = pref.preferred_price_level
            query = query.filter(Place.price_level <= max_price)

    places = query.limit(limit).all()

    # Nếu kết quả lọc quá ít, bổ sung thêm các địa điểm đang hoạt động khác
    if len(places) < limit:
        existing_ids = [p.id for p in places]
        additional = (
            db.query(Place)
            .filter(Place.is_active == True, ~Place.id.in_(existing_ids))
            .limit(limit - len(places))
            .all()
        )
        places.extend(additional)

    summary = (
        f"Gợi ý cá nhân hóa cho {current_user.username} dựa trên danh mục yêu thích "
        f"({', '.join(fav_categories) if fav_categories else 'Tất cả'}) và mức giá tối đa ₫{max_price}."
    )

    return {
        "user_id": current_user.id,
        "summary": summary,
        "favorite_categories": fav_categories,
        "preferred_price_level": max_price,
        "places": places
    }


@router.get(
    "/trending",
    response_model=list[PlaceResponse],
    summary="Lấy danh sách các địa điểm du lịch thịnh hành nhất tại Đà Nẵng"
)
def get_trending_places(
    limit: int = Query(default=6, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các địa điểm nổi bật và được yêu thích nhất."""
    return db.query(Place).filter(Place.is_active == True).order_by(Place.rating.desc().nullslast(), Place.id.asc()).limit(limit).all()


@router.get(
    "",
    response_model=list[PlaceResponse],
    summary="Lấy danh sách gợi ý địa điểm theo danh mục hoặc nổi bật"
)
@router.get(
    "/",
    response_model=list[PlaceResponse],
    include_in_schema=False
)
def get_recommendations_by_category(
    category: str | None = Query(default=None, description="Lọc theo danh mục: all, tourist_attraction, restaurant, cafe, shopping hoặc tiếng Việt"),
    limit: int = Query(default=8, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Trả về danh sách địa điểm đề xuất theo danh mục hoặc nổi bật.
    Hỗ trợ cả danh mục chuẩn (tourist_attraction, restaurant, cafe, shopping) và danh mục tiếng Việt từ Frontend.
    """
    category_alias = {
        "tham quan": "tourist_attraction",
        "biển": "tourist_attraction",
        "thiên nhiên": "tourist_attraction",
        "văn hóa": "tourist_attraction",
        "ẩm thực": "restaurant",
        "quán ăn": "restaurant",
        "cà phê": "cafe",
        "mua sắm": "shopping",
    }

    query = db.query(Place).filter(Place.is_active == True)

    if category and category.strip().lower() != "all":
        cat_clean = category.strip().lower()
        db_cat = category_alias.get(cat_clean, cat_clean)
        query = query.filter(Place.category == db_cat)

        topic_words = {
            "biển": ["biển", "bãi"],
            "thiên nhiên": ["rừng", "núi", "đèo", "bán đảo", "suối", "thác", "hồ", "ghềnh"],
            "văn hóa": ["phố cổ", "chùa", "bảo tàng", "nhà thờ", "thánh địa", "làng", "công viên văn hóa"]
        }
        words = topic_words.get(cat_clean)
        if words:
            from sqlalchemy import or_
            filters = [Place.name.ilike(f"%{w}%") for w in words] + [Place.description.ilike(f"%{w}%") for w in words]
            query = query.filter(or_(*filters))

    return query.order_by(Place.rating.desc().nullslast(), Place.id.asc()).limit(limit).all()

