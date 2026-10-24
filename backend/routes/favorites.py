from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user
from backend.database import get_db
from backend.models.favorite import Favorite
from backend.models.place import Place
from backend.models.user import User
from backend.schemas.place import PlaceResponse

router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"]
)


@router.get(
    "",
    response_model=list[int],
    summary="[Protected] Lấy danh sách ID địa điểm yêu thích của người dùng"
)
@router.get(
    "/",
    response_model=list[int],
    include_in_schema=False
)
def get_user_favorites(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trả về mảng ID các địa điểm người dùng đã lưu vào danh sách yêu thích.
    Khớp chính xác với hợp đồng API của Frontend: [id1, id2, ...]
    """
    favs = (
        db.query(Favorite.place_id)
        .filter(Favorite.user_id == current_user.id)
        .all()
    )
    return [f[0] for f in favs]


@router.get(
    "/details",
    response_model=list[PlaceResponse],
    summary="[Protected] Lấy chi tiết toàn bộ các địa điểm yêu thích của người dùng"
)
def get_user_favorite_details(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trả về danh sách đầy đủ thông tin các địa điểm yêu thích để hiển thị trực tiếp.
    """
    places = (
        db.query(Place)
        .join(Favorite, Favorite.place_id == Place.id)
        .filter(
            Favorite.user_id == current_user.id,
            Place.is_active == True
        )
        .all()
    )
    return places


@router.post(
    "/{place_id}",
    summary="[Protected] Toggle lưu / bỏ lưu địa điểm yêu thích"
)
def toggle_favorite(
    place_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chuyển đổi trạng thái yêu thích:
    - Nếu đã yêu thích: Bỏ yêu thích
    - Nếu chưa yêu thích: Thêm vào danh sách yêu thích
    Body rỗng, trả về trạng thái hiện tại và danh sách ID đã cập nhật.
    """
    place = db.query(Place).filter(Place.id == place_id, Place.is_active == True).first()
    if not place:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy địa điểm này"
        )

    fav = (
        db.query(Favorite)
        .filter(
            Favorite.user_id == current_user.id,
            Favorite.place_id == place_id
        )
        .first()
    )

    if fav:
        db.delete(fav)
        db.commit()
        favorited = False
    else:
        new_fav = Favorite(user_id=current_user.id, place_id=place_id)
        db.add(new_fav)
        db.commit()
        favorited = True

    all_favs = (
        db.query(Favorite.place_id)
        .filter(Favorite.user_id == current_user.id)
        .all()
    )

    return {
        "favorited": favorited,
        "place_id": place_id,
        "place_ids": [f[0] for f in all_favs]
    }
