from math import atan2, cos, radians, sin, sqrt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user, require_admin
from backend.database import get_db
from backend.models.place import Place
from backend.models.user import User
from backend.schemas.place import (
    PlaceCreate,
    PlaceListResponse,
    PlaceNearbyItem,
    PlaceNearbyResponse,
    PlaceResponse,
    PlaceUpdate,
)

router = APIRouter(
    prefix="/places",
    tags=["Places"]
)


# ==============================================================
# 1. API Lấy danh sách & Tìm kiếm địa điểm (Public)
# ==============================================================
@router.get(
    "/",
    response_model=PlaceListResponse,
    summary="Tìm kiếm và lọc danh sách địa điểm"
)
def get_places(
    keyword: str | None = Query(
        default=None,
        description="Tìm theo tên hoặc mô tả địa điểm"
    ),
    category: str | None = Query(
        default=None,
        description="Lọc theo danh mục: tourist_attraction, restaurant, cafe, shopping..."
    ),
    max_price: int | None = Query(
        default=None,
        ge=1,
        le=5,
        description="Mức giá tối đa từ 1 đến 5"
    ),
    skip: int = Query(default=0, ge=0, description="Số lượng bản ghi bỏ qua"),
    limit: int = Query(default=50, ge=1, le=100, description="Số lượng bản ghi tối đa"),
    db: Session = Depends(get_db)
):
    """
    API công khai cho phép tìm kiếm và lọc danh sách địa điểm tại Đà Nẵng.
    Hỗ trợ phân trang, tìm kiếm từ khóa, danh mục và mức giá.
    """
    query = db.query(Place).filter(Place.is_active == True)

    # Tìm theo tên hoặc mô tả
    if keyword:
        search_term = f"%{keyword.strip()}%"
        query = query.filter(
            (Place.name.ilike(search_term))
            | (Place.description.ilike(search_term))
        )

    # Lọc theo danh mục
    if category:
        query = query.filter(
            Place.category == category.strip().lower()
        )

    # Lọc theo mức giá tối đa
    if max_price is not None:
        query = query.filter(
            Place.price_level <= max_price
        )

    total = query.count()
    places = query.order_by(Place.id.asc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "places": places
    }


# ==============================================================
# 2. API Tìm địa điểm gần tọa độ người dùng (Public)
# ==============================================================
@router.get(
    "/nearby",
    response_model=PlaceNearbyResponse,
    summary="Tìm địa điểm lân cận theo tọa độ GPS"
)
def get_nearby_places(
    latitude: float = Query(
        ...,
        ge=-90,
        le=90,
        description="Vĩ độ hiện tại của người dùng"
    ),
    longitude: float = Query(
        ...,
        ge=-180,
        le=180,
        description="Kinh độ hiện tại của người dùng"
    ),
    radius_km: float = Query(
        default=5.0,
        gt=0,
        le=50,
        description="Bán kính tìm kiếm tính theo kilômét (mặc định 5km)"
    ),
    category: str | None = Query(
        default=None,
        description="Lọc theo danh mục (tuỳ chọn)"
    ),
    db: Session = Depends(get_db)
):
    """
    API tính khoảng cách địa lý theo công thức Haversine để tìm
    các địa điểm nằm trong bán kính người dùng chọn và sắp xếp từ gần đến xa.
    """
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        earth_radius = 6371.0  # Bán kính trái đất (km)
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1))
            * cos(radians(lat2))
            * sin(dlon / 2) ** 2
        )
        a = max(0.0, min(1.0, a))
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return earth_radius * c

    query = db.query(Place).filter(
        Place.is_active == True,
        Place.latitude.isnot(None),
        Place.longitude.isnot(None)
    )

    if category:
        query = query.filter(
            Place.category == category.strip().lower()
        )

    all_places = query.all()
    nearby_places = []

    for place in all_places:
        distance = calculate_distance(
            latitude,
            longitude,
            place.latitude,
            place.longitude
        )

        if distance <= radius_km:
            item = PlaceNearbyItem(
                id=place.id,
                name=place.name,
                category=place.category,
                address=place.address,
                description=place.description,
                latitude=place.latitude,
                longitude=place.longitude,
                price_level=place.price_level,
                opening_hours=place.opening_hours,
                is_active=place.is_active,
                distance_km=round(distance, 2)
            )
            nearby_places.append(item)

    # Sắp xếp từ gần đến xa
    nearby_places.sort(key=lambda item: item.distance_km)

    return {
        "total": len(nearby_places),
        "radius_km": radius_km,
        "category": category.strip().lower() if category else None,
        "places": nearby_places
    }


# ==============================================================
# 3. API Quản trị POI cho Quản trị viên (Admin Only)
# ==============================================================
@router.get(
    "/admin/stats",
    summary="[Admin] Thống kê dữ liệu địa điểm du lịch Đà Nẵng"
)
def get_poi_stats(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    [Chỉ Quản trị viên] Báo cáo thống kê tổng quan về các điểm du lịch (POI):
    - Tổng số địa điểm
    - Số địa điểm đang hoạt động và đang ẩn
    - Phân bổ theo từng danh mục
    """
    total = db.query(Place).count()
    active = db.query(Place).filter(Place.is_active == True).count()
    inactive = total - active

    # Phân nhóm theo category
    from sqlalchemy import func
    cat_counts = (
        db.query(Place.category, func.count(Place.id))
        .group_by(Place.category)
        .all()
    )
    categories_breakdown = {cat: count for cat, count in cat_counts}

    return {
        "total_pois": total,
        "active_pois": active,
        "inactive_pois": inactive,
        "categories_breakdown": categories_breakdown
    }


@router.get(
    "/admin/all",
    response_model=PlaceListResponse,
    summary="[Admin] Lấy danh sách toàn bộ POI (bao gồm cả địa điểm đã ẩn)"
)
def get_all_pois_admin(
    status: str = Query(default="all", description="Lọc trạng thái: all, active, inactive"),
    category: str | None = Query(default=None, description="Lọc theo danh mục"),
    keyword: str | None = Query(default=None, description="Tìm theo tên/mô tả"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    [Chỉ Quản trị viên] Truy vấn toàn bộ POI trong hệ thống phục vụ công tác quản trị.
    """
    query = db.query(Place)

    if status == "active":
        query = query.filter(Place.is_active == True)
    elif status == "inactive":
        query = query.filter(Place.is_active == False)

    if category:
        query = query.filter(Place.category == category.strip().lower())

    if keyword:
        term = f"%{keyword.strip()}%"
        query = query.filter((Place.name.ilike(term)) | (Place.description.ilike(term)))

    total = query.count()
    places = query.order_by(Place.id.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "places": places
    }


# ==============================================================
# 4. API Lấy chi tiết một địa điểm theo ID (Public)
# ==============================================================
@router.get(
    "/{place_id}",
    response_model=PlaceResponse,
    summary="Xem chi tiết một địa điểm theo ID"
)
def get_place_detail(
    place_id: int,
    db: Session = Depends(get_db)
):
    """Lấy toàn bộ thông tin chi tiết của địa điểm theo ID."""
    place = (
        db.query(Place)
        .filter(
            Place.id == place_id,
            Place.is_active == True
        )
        .first()
    )

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy địa điểm này"
        )

    return place


# ==============================================================
# 5. API Tạo mới địa điểm (Admin Only)
# ==============================================================
@router.post(
    "/",
    response_model=PlaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Tạo mới địa điểm du lịch"
)
def create_place(
    place_data: PlaceCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    [Chỉ Quản trị viên] Thêm một địa điểm du lịch mới vào cơ sở dữ liệu.
    """
    new_place = Place(
        name=place_data.name.strip(),
        category=place_data.category.strip().lower(),
        address=place_data.address.strip(),
        description=place_data.description,
        latitude=place_data.latitude,
        longitude=place_data.longitude,
        price_level=place_data.price_level,
        opening_hours=place_data.opening_hours,
        is_active=True
    )

    db.add(new_place)
    db.commit()
    db.refresh(new_place)

    return new_place


# ==============================================================
# 6. API Cập nhật địa điểm (Admin Only)
# ==============================================================
@router.put(
    "/{place_id}",
    response_model=PlaceResponse,
    summary="[Admin] Cập nhật thông tin địa điểm"
)
def update_place(
    place_id: int,
    place_data: PlaceUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    [Chỉ Quản trị viên] Cập nhật thông tin địa điểm theo ID.
    Chỉ cập nhật những trường được truyền vào trong body request.
    """
    place = db.query(Place).filter(Place.id == place_id).first()

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy địa điểm cần cập nhật"
        )

    update_dict = place_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        if field == "category" and value:
            value = value.strip().lower()
        elif isinstance(value, str):
            value = value.strip()
        setattr(place, field, value)

    db.commit()
    db.refresh(place)

    return place


# ==============================================================
# 7. API Bật/Tắt trạng thái hiển thị (Admin Only)
# ==============================================================
@router.patch(
    "/{place_id}/toggle-status",
    response_model=PlaceResponse,
    summary="[Admin] Bật/tắt nhanh trạng thái hiển thị (Active/Inactive)"
)
def toggle_place_status(
    place_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    [Chỉ Quản trị viên] Bật hoặc tắt trạng thái hiển thị của địa điểm du lịch.
    """
    place = db.query(Place).filter(Place.id == place_id).first()

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy địa điểm này"
        )

    place.is_active = not place.is_active
    db.commit()
    db.refresh(place)

    return place


# ==============================================================
# 6. API Xóa địa điểm (Yêu cầu quyền Admin - Protected)
# ==============================================================
@router.delete(
    "/{place_id}",
    summary="[Admin] Xóa hoặc ẩn địa điểm"
)
def delete_place(
    place_id: int,
    permanent: bool = Query(
        default=False,
        description="Nếu True sẽ xóa vĩnh viễn khỏi Database, False sẽ ẩn (soft delete)"
    ),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    [Chỉ Quản trị viên] Xóa địa điểm.
    Mặc định thực hiện soft delete (is_active = False) để bảo tồn dữ liệu lịch sử.
    """
    place = db.query(Place).filter(Place.id == place_id).first()

    if place is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy địa điểm cần xóa"
        )

    if permanent:
        db.delete(place)
        message = f"Đã xóa vĩnh viễn địa điểm id {place_id} khỏi database"
    else:
        place.is_active = False
        message = f"Đã ẩn địa điểm id {place_id} (soft delete)"

    db.commit()

    return {
        "status": "success",
        "message": message
    }
