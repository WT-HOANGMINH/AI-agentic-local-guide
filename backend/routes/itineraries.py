from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user
from backend.database import get_db
from backend.models.itinerary import Itinerary, ItineraryItem
from backend.models.place import Place
from backend.models.user import User
from backend.schemas.itinerary import (
    ItineraryCreate,
    ItineraryDetailResponse,
    ItineraryGenerateRequest,
    ItineraryItemCreate,
    ItineraryItemResponse,
    ItineraryItemUpdate,
    ItineraryListResponse,
    ItineraryResponse,
    ItineraryUpdate,
)

router = APIRouter(
    prefix="/itineraries",
    tags=["Trip Itineraries"]
)


@router.get(
    "/",
    response_model=ItineraryListResponse,
    summary="[Protected] Lấy danh sách lịch trình của người dùng hiện tại"
)
def get_user_itineraries(
    status_filter: str | None = Query(default=None, alias="status", description="Lọc theo trạng thái: planning, ongoing, completed"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách các chuyến đi / lịch trình du lịch của chính người dùng."""
    query = db.query(Itinerary).filter(Itinerary.user_id == current_user.id)

    if status_filter:
        query = query.filter(Itinerary.status == status_filter.strip().lower())

    total = query.count()
    records = query.order_by(Itinerary.created_at.desc()).offset(skip).limit(limit).all()

    # Thống kê item_count cho mỗi itinerary
    result = []
    for it in records:
        it_dict = {
            "id": it.id,
            "user_id": it.user_id,
            "title": it.title,
            "description": it.description,
            "start_date": it.start_date,
            "end_date": it.end_date,
            "total_days": it.total_days,
            "budget_level": it.budget_level,
            "status": it.status,
            "item_count": len(it.items),
            "created_at": it.created_at,
            "updated_at": it.updated_at
        }
        result.append(it_dict)

    return {
        "total": total,
        "itineraries": result
    }


@router.post(
    "/",
    response_model=ItineraryDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Protected] Tạo lịch trình chuyến đi mới"
)
def create_itinerary(
    data: ItineraryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tạo lịch trình du lịch mới cùng danh sách các địa điểm dừng chân ban đầu."""
    new_itinerary = Itinerary(
        user_id=current_user.id,
        title=data.title.strip(),
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        total_days=data.total_days,
        budget_level=data.budget_level,
        status=data.status or "planning"
    )

    db.add(new_itinerary)
    db.commit()
    db.refresh(new_itinerary)

    # Thêm các items nếu có
    if data.items:
        for item_data in data.items:
            item = ItineraryItem(
                itinerary_id=new_itinerary.id,
                place_id=item_data.place_id,
                day_number=item_data.day_number,
                order_index=item_data.order_index,
                time_slot=item_data.time_slot,
                notes=item_data.notes,
                estimated_cost=item_data.estimated_cost or 0.0
            )
            db.add(item)
        db.commit()
        db.refresh(new_itinerary)

    return new_itinerary


@router.post(
    "/generate-smart",
    response_model=ItineraryDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Protected] AI Smart Generator: Tự động khởi tạo lịch trình tối ưu tại Đà Nẵng"
)
def generate_smart_itinerary(
    req: ItineraryGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Công cụ AI thông minh tự động xây dựng lịch trình du lịch Đà Nẵng tối ưu:
    - Sắp xếp logic theo các buổi: Sáng (tham quan/check-in) -> Trưa (ẩm thực) -> Chiều (biển/nghỉ dưỡng) -> Tối (cầu Rồng/chợ đêm).
    - Tự động lấy các địa điểm tốt nhất từ cơ sở dữ liệu Đà Nẵng và lưu trực tiếp vào tài khoản người dùng.
    """
    days = req.days
    title = req.title or f"Hành trình Đà Nẵng {days} ngày {days-1} đêm ({req.travel_style})"
    desc = (
        f"Lịch trình {req.travel_style.lower()} được tạo tự động bởi Agentic Local Guide. "
        f"Mức ngân sách: ₫{'₫' * max(0, min(req.budget_level, 5)-1)}."
    )

    new_it = Itinerary(
        user_id=current_user.id,
        title=title,
        description=desc,
        total_days=days,
        budget_level=req.budget_level,
        status="planning"
    )
    db.add(new_it)
    db.commit()
    db.refresh(new_it)

    # Lấy danh sách địa điểm theo các nhóm
    attractions = db.query(Place).filter(Place.is_active == True, Place.category == "tourist_attraction").all()
    restaurants = db.query(Place).filter(Place.is_active == True, Place.category == "restaurant").all()
    cafes = db.query(Place).filter(Place.is_active == True, Place.category == "cafe").all()
    others = db.query(Place).filter(Place.is_active == True, ~Place.category.in_(["tourist_attraction", "restaurant", "cafe"])).all()

    # Fallback nếu thiếu dữ liệu
    all_places = db.query(Place).filter(Place.is_active == True).all()

    time_slots = [
        ("08:30 - 11:30", "Buổi sáng tham quan, chụp ảnh và check-in", attractions),
        ("12:00 - 13:30", "Thưởng thức ẩm thực trưa đặc sản Đà Nẵng", restaurants),
        ("14:30 - 16:30", "Thư giãn ngắm cảnh, cà phê view đẹp", cafes),
        ("17:30 - 21:00", "Khám phá phố đêm, cầu Rồng hoặc bãi biển", attractions + others)
    ]

    attr_idx = 0
    rest_idx = 0
    cafe_idx = 0
    other_idx = 0

    for day in range(1, days + 1):
        for slot_idx, (slot_time, note, pool) in enumerate(time_slots, start=1):
            chosen_place = None
            if pool:
                if "Buổi sáng" in note and attractions:
                    chosen_place = attractions[attr_idx % len(attractions)]
                    attr_idx += 1
                elif "ẩm thực" in note and restaurants:
                    chosen_place = restaurants[rest_idx % len(restaurants)]
                    rest_idx += 1
                elif "cà phê" in note and cafes:
                    chosen_place = cafes[cafe_idx % len(cafes)]
                    cafe_idx += 1
                else:
                    chosen_place = pool[other_idx % len(pool)]
                    other_idx += 1
            elif all_places:
                chosen_place = all_places[(day + slot_idx) % len(all_places)]

            item = ItineraryItem(
                itinerary_id=new_it.id,
                place_id=chosen_place.id if chosen_place else None,
                day_number=day,
                order_index=slot_idx,
                time_slot=slot_time,
                notes=f"Ngày {day}: {note}. Gợi ý: {chosen_place.name if chosen_place else 'Tự do khám phá'}.",
                estimated_cost=150000.0 if "ẩm thực" in note else (50000.0 if "cà phê" in note else 0.0)
            )
            db.add(item)

    db.commit()
    db.refresh(new_it)
    return new_it


@router.get(
    "/{itinerary_id}",
    response_model=ItineraryDetailResponse,
    summary="[Protected] Xem chi tiết một lịch trình du lịch"
)
def get_itinerary_detail(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xem chi tiết toàn bộ các điểm dừng chân trong chuyến đi theo ID."""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()

    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch trình này"
        )

    # Đảm bảo chỉ chủ sở hữu hoặc admin mới xem được
    if itinerary.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập lịch trình này"
        )

    return itinerary


@router.put(
    "/{itinerary_id}",
    response_model=ItineraryDetailResponse,
    summary="[Protected] Cập nhật thông tin lịch trình"
)
def update_itinerary(
    itinerary_id: int,
    data: ItineraryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật tiêu đề, mô tả, ngày tháng hoặc trạng thái chuyến đi."""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()

    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch trình để cập nhật"
        )

    if itinerary.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền sửa lịch trình này"
        )

    update_dict = data.model_dump(exclude_unset=True)
    for field, val in update_dict.items():
        setattr(itinerary, field, val)

    db.commit()
    db.refresh(itinerary)
    return itinerary


@router.delete(
    "/{itinerary_id}",
    summary="[Protected] Xóa một lịch trình"
)
def delete_itinerary(
    itinerary_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa lịch trình và toàn bộ các điểm dừng chân liên quan."""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()

    if not itinerary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy lịch trình để xóa"
        )

    if itinerary.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xóa lịch trình này"
        )

    db.delete(itinerary)
    db.commit()

    return {
        "status": "success",
        "message": f"Đã xóa thành công lịch trình id {itinerary_id}"
    }


# ==============================================================
# Quản lý từng điểm dừng chân (Items) trong lịch trình
# ==============================================================

@router.post(
    "/{itinerary_id}/items",
    response_model=ItineraryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Protected] Thêm một điểm dừng chân vào lịch trình"
)
def add_itinerary_item(
    itinerary_id: int,
    item_data: ItineraryItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Thêm một địa điểm vào ngày cụ thể trong chuyến đi."""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch trình")

    if itinerary.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền chỉnh sửa lịch trình")

    if item_data.place_id:
        place = db.query(Place).filter(Place.id == item_data.place_id).first()
        if not place:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Địa điểm không tồn tại")

    new_item = ItineraryItem(
        itinerary_id=itinerary.id,
        place_id=item_data.place_id,
        day_number=item_data.day_number,
        order_index=item_data.order_index,
        time_slot=item_data.time_slot,
        notes=item_data.notes,
        estimated_cost=item_data.estimated_cost
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return new_item


@router.delete(
    "/{itinerary_id}/items/{item_id}",
    summary="[Protected] Xóa một điểm dừng chân khỏi lịch trình"
)
def delete_itinerary_item(
    itinerary_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa một địa điểm khỏi chuyến đi."""
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch trình")

    if itinerary.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền chỉnh sửa lịch trình")

    item = db.query(ItineraryItem).filter(ItineraryItem.id == item_id, ItineraryItem.itinerary_id == itinerary_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy điểm dừng chân này")

    db.delete(item)
    db.commit()

    return {"status": "success", "message": f"Đã xóa điểm dừng chân {item_id}"}
