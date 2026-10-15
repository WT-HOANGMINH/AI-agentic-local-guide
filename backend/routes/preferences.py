from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user, require_admin
from backend.database import get_db
from backend.models.preference import UserPreference
from backend.models.user import User
from backend.schemas.preference import UserPreferenceResponse, UserPreferenceUpdate

router = APIRouter(
    prefix="/preferences",
    tags=["User Preferences"]
)


def _format_preference_response(pref: UserPreference) -> dict:
    """Chuyển đổi chuỗi phân cách trong DB thành mảng danh sách cho Pydantic."""
    fav_cats = [c.strip() for c in pref.favorite_categories.split(",") if c.strip()] if pref.favorite_categories else []
    interest_list = [i.strip() for i in pref.interests.split(",") if i.strip()] if pref.interests else []

    return {
        "id": pref.id,
        "user_id": pref.user_id,
        "favorite_categories": fav_cats,
        "preferred_price_level": pref.preferred_price_level,
        "dietary_preferences": pref.dietary_preferences,
        "travel_style": pref.travel_style,
        "interests": interest_list,
        "updated_at": pref.updated_at
    }


@router.get(
    "/me",
    response_model=UserPreferenceResponse,
    summary="[Protected] Xem sở thích du lịch của tài khoản hiện tại"
)
def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin cấu hình sở thích của người dùng đang đăng nhập.
    Nếu chưa từng tạo, hệ thống tự động khởi tạo bản ghi sở thích mặc định.
    """
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()

    if not pref:
        # Tự động tạo bản ghi mặc định cho người dùng
        pref = UserPreference(
            user_id=current_user.id,
            favorite_categories="tourist_attraction,restaurant,cafe",
            preferred_price_level=2,
            dietary_preferences="Đa dạng món ngon Đà Nẵng",
            travel_style="Khám phá tự do",
            interests="Biển, check-in, ẩm thực địa phương"
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)

    return _format_preference_response(pref)


@router.put(
    "/me",
    response_model=UserPreferenceResponse,
    summary="[Protected] Cập nhật sở thích du lịch cá nhân"
)
def update_my_preferences(
    pref_data: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cập nhật các tiêu chí sở thích (danh mục yêu thích, mức giá, phong cách du lịch...).
    Áp dụng kỹ thuật Upsert (tạo mới nếu chưa có, cập nhật nếu đã tồn tại).
    """
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()

    if not pref:
        pref = UserPreference(user_id=current_user.id)
        db.add(pref)

    if pref_data.favorite_categories is not None:
        pref.favorite_categories = ",".join([c.strip().lower() for c in pref_data.favorite_categories if c.strip()])

    if pref_data.preferred_price_level is not None:
        pref.preferred_price_level = pref_data.preferred_price_level

    if pref_data.dietary_preferences is not None:
        pref.dietary_preferences = pref_data.dietary_preferences.strip()

    if pref_data.travel_style is not None:
        pref.travel_style = pref_data.travel_style.strip()

    if pref_data.interests is not None:
        pref.interests = ",".join([i.strip() for i in pref_data.interests if i.strip()])

    db.commit()
    db.refresh(pref)

    return _format_preference_response(pref)


@router.delete(
    "/me",
    summary="[Protected] Đặt lại sở thích về mặc định"
)
def reset_my_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa sở thích tùy chỉnh và khôi phục về cài đặt mặc định."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()

    if pref:
        db.delete(pref)
        db.commit()

    return {
        "status": "success",
        "message": "Đã đặt lại sở thích du lịch về mặc định"
    }


@router.get(
    "/{user_id}",
    response_model=UserPreferenceResponse,
    summary="[Admin] Xem sở thích du lịch của một người dùng theo ID"
)
def get_user_preferences_by_id(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """[Quyền Quản trị viên] Xem hồ sơ sở thích của bất kỳ người dùng nào."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()

    if not pref:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng này chưa thiết lập sở thích cá nhân"
        )

    return _format_preference_response(pref)
