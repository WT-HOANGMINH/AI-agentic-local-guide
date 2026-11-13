import hashlib
import json
from datetime import datetime, timedelta
from copy import deepcopy

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth_utils import get_current_user
from backend.database import get_db
from backend.models.itinerary import Itinerary, ItineraryIdempotency, ItineraryItem
from backend.models.place import Place
from backend.models.user import User
from backend.services.weather_analyzer import analyze_date, classify_hour, poi_allowed
from backend.services.weather_planner import profile_of
from backend.services.weather_service import TZ, get_weather_forecast
from backend.schemas.itinerary import (
    ItineraryCreate,
    ItineraryDetailResponse,
    ItineraryFromChatCreate,
    ItineraryGenerateRequest,
    ItineraryItemCreate,
    ItineraryItemResponse,
    ItineraryItemsReplace,
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
            "itinerary_data": it.itinerary_data,
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
        itinerary_data=(
            data.itinerary_data.model_dump(mode="json")
            if data.itinerary_data else None
        ),
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
    travel_date = req.travel_date or datetime.now(TZ).date()
    title = req.title or f"Hành trình Đà Nẵng {days} ngày {days-1} đêm ({req.travel_style})"
    desc = (
        f"Lịch trình {req.travel_style.lower()} được tạo tự động bởi Agentic Local Guide. "
        f"Mức ngân sách: ₫{'₫' * max(0, min(req.budget_level, 5)-1)}."
    )

    forecast = None
    weather_notice = ""
    try:
        forecast = get_weather_forecast(forecast_days=7)
    except RuntimeError:
        weather_notice = (
            "Chưa thể xác minh dự báo thời tiết trực tiếp; lịch trình dùng cách chọn địa điểm thông thường."
        )
    if forecast and forecast.get("is_stale"):
        weather_notice = (
            "Dữ liệu thời tiết đang cũ; không dùng dữ liệu này để ưu tiên hoặc loại bỏ địa điểm."
        )

    new_it = Itinerary(
        user_id=current_user.id,
        title=title,
        description=desc + (f" {weather_notice}" if weather_notice else ""),
        start_date=travel_date.isoformat(),
        end_date=(travel_date + timedelta(days=days - 1)).isoformat(),
        total_days=days,
        budget_level=req.budget_level,
        status="planning"
    )
    db.add(new_it)
    db.flush()

    # Lấy danh sách địa điểm theo các nhóm
    attractions = db.query(Place).filter(Place.is_active == True, Place.category == "tourist_attraction").all()
    restaurants = db.query(Place).filter(Place.is_active == True, Place.category == "restaurant").all()
    cafes = db.query(Place).filter(Place.is_active == True, Place.category == "cafe").all()
    others = db.query(Place).filter(Place.is_active == True, ~Place.category.in_(["tourist_attraction", "restaurant", "cafe"])).all()

    # Fallback nếu thiếu dữ liệu
    all_places = db.query(Place).filter(Place.is_active == True).all()

    if forecast and not forecast.get("is_stale"):
        forecast_dates = {row.get("date") for row in forecast.get("daily", [])}
        requested_dates = {
            (travel_date + timedelta(days=offset)).isoformat()
            for offset in range(days)
        }
        if requested_dates - forecast_dates:
            weather_notice = (
                "Dự báo hiện không bao phủ toàn bộ ngày đi; những ngày chưa có dữ liệu "
                "được xếp theo cách thông thường."
            )
            new_it.description = f"{desc} {weather_notice}"

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
    selected_ids = set()
    generated_days = []

    def slot_risk(day_iso, slot_time):
        if not forecast or forecast.get("is_stale"):
            return None
        start, end = [
            part.strip() for part in slot_time.split("-", maxsplit=1)
        ]
        start_minute = int(start[:2]) * 60 + int(start[3:])
        end_minute = int(end[:2]) * 60 + int(end[3:])
        risks = []
        for hour in forecast.get("hours", []):
            if not hour.get("time", "").startswith(day_iso):
                continue
            minute = int(hour["time"][11:13]) * 60 + int(hour["time"][14:16])
            if start_minute <= minute < end_minute:
                risks.append(classify_hour(hour)["risk"])
        return max(risks) if risks else None

    for day in range(1, days + 1):
        day_iso = (travel_date + timedelta(days=day - 1)).isoformat()
        plan_items = []
        for slot_idx, (slot_time, note, pool) in enumerate(time_slots, start=1):
            candidates = [place for place in pool if place.id not in selected_ids]
            if not candidates:
                candidates = [place for place in all_places if place.id not in selected_ids]

            risk = slot_risk(day_iso, slot_time)
            chosen_place = None
            if candidates:
                if "Buổi sáng" in note and attractions:
                    cursor = attr_idx
                    attr_idx += 1
                elif "ẩm thực" in note and restaurants:
                    cursor = rest_idx
                    rest_idx += 1
                elif "cà phê" in note and cafes:
                    cursor = cafe_idx
                    cafe_idx += 1
                else:
                    cursor = other_idx
                    other_idx += 1
                cursor %= len(candidates)

                def score_candidate(index_place):
                    index, place = index_place
                    profile = profile_of(place)
                    if risk is None or risk <= 1:
                        weather_penalty = 0
                        profile_penalty = 0
                    else:
                        weather_penalty = 0 if poi_allowed(profile, risk) else 1
                        profile_penalty = {
                            "indoor": 0,
                            "weather_dependent": 1,
                            "outdoor": 2,
                        }.get(profile, 1)
                    return (
                        weather_penalty,
                        profile_penalty if risk is not None and risk >= 2 else 0,
                        (index - cursor) % len(candidates),
                    )

                chosen_place = min(enumerate(candidates), key=score_candidate)[1]
                selected_ids.add(chosen_place.id)

            item_title = chosen_place.name if chosen_place else "Tự do khám phá"
            item_kind = (
                "meal" if "ẩm thực" in note else
                "cafe" if "cà phê" in note else
                "visit" if chosen_place else "free_time"
            )
            start_time, end_time = [
                part.strip() for part in slot_time.split("-", maxsplit=1)
            ]

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
            plan_items.append({
                "order": slot_idx,
                "kind": item_kind,
                "place_id": chosen_place.id if chosen_place else None,
                "title": item_title,
                "start_time": start_time,
                "end_time": end_time,
                "description": note,
                "address": chosen_place.address if chosen_place else None,
                "estimated_cost_vnd": (
                    150000.0 if "ẩm thực" in note
                    else 50000.0 if "cà phê" in note
                    else 0.0
                ),
            })
        generated_days.append({"day_number": day, "items": plan_items})

    new_it.itinerary_data = {
        "title": title,
        "description": new_it.description,
        "travel_date": travel_date.isoformat(),
        "duration_days": days,
        "budget": {"level": req.budget_level, "currency": "VND"},
        "preferences": {
            "travel_style": req.travel_style,
            "preferred_categories": req.preferred_categories,
            "weather_notice": weather_notice or None,
            "weather_source": forecast.get("source") if forecast else None,
            "weather_reference_url": (
                "https://open-meteo.com/en/docs" if forecast else None
            ),
            "weather_fetched_at": forecast.get("fetched_at") if forecast else None,
            "weather_cache_status": (
                "unavailable" if not forecast else
                "stale" if forecast.get("is_stale") else
                "cached" if forecast.get("from_cache") else "fresh"
            ),
            "weather_valid_from": min(
                (row["date"] for row in forecast.get("daily", []) if row.get("date")),
                default=None,
            ) if forecast else None,
            "weather_valid_until": max(
                (row["date"] for row in forecast.get("daily", []) if row.get("date")),
                default=None,
            ) if forecast else None,
            "weather_region": forecast.get("location", "Da Nang, Vietnam") if forecast else None,
        },
        "days": generated_days,
        "verified_data_only": True,
    }
    db.commit()
    db.refresh(new_it)
    return new_it


@router.post(
    "/from-chat",
    response_model=ItineraryDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Protected] Lưu lịch trình đầy đủ do chat AI tạo"
)
def save_chat_itinerary(
    data: ItineraryFromChatCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=128),
):
    plan = data.itinerary
    serialized_plan = json.dumps(
        plan.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    request_hash = hashlib.sha256(serialized_plan.encode("utf-8")).hexdigest()
    key = (idempotency_key or request_hash).strip()
    if not key:
        key = request_hash

    previous_request = db.query(ItineraryIdempotency).filter(
        ItineraryIdempotency.user_id == current_user.id,
        ItineraryIdempotency.idempotency_key == key,
    ).first()
    if previous_request:
        if previous_request.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Khóa lưu lịch trình đã được sử dụng cho nội dung khác.",
            )
        previous_itinerary = db.query(Itinerary).filter(
            Itinerary.id == previous_request.itinerary_id,
            Itinerary.user_id == current_user.id,
        ).first()
        if previous_itinerary:
            return previous_itinerary

    referenced_ids = {
        item.place_id
        for day in plan.days
        for item in day.items
        if item.place_id is not None
    }
    if referenced_ids:
        existing_ids = {
            place_id for (place_id,) in
            db.query(Place.id).filter(Place.id.in_(referenced_ids)).all()
        }
        missing_ids = referenced_ids - existing_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lịch trình có địa điểm không tồn tại.",
            )

    level = plan.budget.level
    budget_level = level if isinstance(level, int) and 1 <= level <= 5 else 2
    itinerary = Itinerary(
        user_id=current_user.id,
        title=plan.title,
        description=plan.description,
        start_date=plan.travel_date,
        total_days=plan.duration_days,
        budget_level=budget_level,
        status="planning",
        itinerary_data=plan.model_dump(mode="json"),
    )
    db.add(itinerary)
    db.flush()

    for day in plan.days:
        for item in day.items:
            time_slot = (
                f"{item.start_time}–{item.end_time}"
                if item.start_time and item.end_time
                else item.start_time or item.end_time
            )
            note_parts = [
                item.title,
                item.description,
                item.address,
            ]
            if item.transport_minutes_from_previous is not None:
                note_parts.append(
                    f"Di chuyển ước tính {item.transport_minutes_from_previous} phút"
                )
            db.add(ItineraryItem(
                itinerary_id=itinerary.id,
                place_id=item.place_id,
                day_number=day.day_number,
                order_index=item.order,
                time_slot=time_slot,
                notes="\n".join(part for part in note_parts if part),
                estimated_cost=item.estimated_cost_vnd,
            ))

    db.add(ItineraryIdempotency(
        user_id=current_user.id,
        idempotency_key=key,
        request_hash=request_hash,
        itinerary_id=itinerary.id,
    ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        previous_request = db.query(ItineraryIdempotency).filter(
            ItineraryIdempotency.user_id == current_user.id,
            ItineraryIdempotency.idempotency_key == key,
        ).first()
        if previous_request and previous_request.request_hash == request_hash:
            previous_itinerary = db.query(Itinerary).filter(
                Itinerary.id == previous_request.itinerary_id,
                Itinerary.user_id == current_user.id,
            ).first()
            if previous_itinerary:
                return previous_itinerary
        raise
    db.refresh(itinerary)
    return itinerary


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

    if itinerary.user_id != current_user.id:
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

    if itinerary.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền sửa lịch trình này"
        )

    update_dict = data.model_dump(exclude_unset=True)
    if isinstance(update_dict.get("itinerary_data"), dict):
        update_dict["itinerary_data"] = data.itinerary_data.model_dump(mode="json")
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

    if itinerary.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xóa lịch trình này"
        )

    db.query(ItineraryIdempotency).filter(
        ItineraryIdempotency.itinerary_id == itinerary.id
    ).delete(synchronize_session=False)
    db.delete(itinerary)
    db.commit()

    return {
        "status": "success",
        "message": f"Đã xóa thành công lịch trình id {itinerary_id}"
    }


# ==============================================================
# Quản lý từng điểm dừng chân (Items) trong lịch trình
# ==============================================================

@router.put(
    "/{itinerary_id}/items",
    response_model=ItineraryDetailResponse,
    summary="[Protected] Thay thế có giao dịch toàn bộ điểm dừng"
)
def replace_itinerary_items(
    itinerary_id: int,
    data: ItineraryItemsReplace,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    itinerary = db.query(Itinerary).filter(Itinerary.id == itinerary_id).first()
    if not itinerary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch trình")
    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền chỉnh sửa lịch trình")
    if any(item.day_number > itinerary.total_days for item in data.items):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ngày trong lịch trình vượt quá thời lượng chuyến đi")

    place_ids = {item.place_id for item in data.items if item.place_id is not None}
    places = {
        place.id: place
        for place in db.query(Place).filter(Place.id.in_(place_ids)).all()
    } if place_ids else {}
    if place_ids - places.keys():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Địa điểm không tồn tại")

    db.query(ItineraryItem).filter(
        ItineraryItem.itinerary_id == itinerary.id
    ).delete(synchronize_session=False)
    for item_data in data.items:
        db.add(ItineraryItem(
            itinerary_id=itinerary.id,
            place_id=item_data.place_id,
            day_number=item_data.day_number,
            order_index=item_data.order_index,
            time_slot=item_data.time_slot,
            notes=item_data.notes,
            estimated_cost=item_data.estimated_cost,
        ))

    grouped = {day: [] for day in range(1, itinerary.total_days + 1)}
    for item_data in sorted(
        data.items,
        key=lambda item: (item.day_number, item.order_index),
    ):
        place = places.get(item_data.place_id)
        start_time = end_time = None
        if item_data.time_slot:
            parts = item_data.time_slot.split("-", maxsplit=1)
            start_time = parts[0].strip()
            end_time = parts[1].strip() if len(parts) == 2 else None
        grouped.setdefault(item_data.day_number, []).append({
            "order": item_data.order_index,
            "kind": "visit",
            "place_id": item_data.place_id,
            "title": place.name if place else (item_data.notes or "Hoạt động"),
            "start_time": start_time,
            "end_time": end_time,
            "description": item_data.notes,
            "address": place.address if place else None,
            "estimated_cost_vnd": item_data.estimated_cost,
        })

    itinerary.itinerary_data = {
        "title": itinerary.title,
        "description": itinerary.description,
        "travel_date": itinerary.start_date,
        "duration_days": itinerary.total_days,
        "budget": {"level": itinerary.budget_level, "currency": "VND"},
        "preferences": {},
        "days": [
            {"day_number": day, "items": items}
            for day, items in sorted(grouped.items())
        ],
        "verified_data_only": True,
    }
    db.commit()
    db.refresh(itinerary)
    return itinerary


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

    if itinerary.user_id != current_user.id:
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

    if itinerary.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền chỉnh sửa lịch trình")

    item = db.query(ItineraryItem).filter(ItineraryItem.id == item_id, ItineraryItem.itinerary_id == itinerary_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy điểm dừng chân này")

    # Đồng bộ lịch trình AI trước khi xóa địa điểm
    plan = itinerary.itinerary_data

    if isinstance(plan, dict) and isinstance(plan.get("days"), list):
        updated_plan = deepcopy(plan)
        matching_items = []

        for day in updated_plan["days"]:
            if not isinstance(day, dict):
                continue

            if day.get("day_number") != item.day_number:
                continue

            activities = day.get("items", [])

            if not isinstance(activities, list):
                continue

            for index, activity in enumerate(activities):
                if not isinstance(activity, dict):
                    continue

                if activity.get("order") != item.order_index:
                    continue

                if activity.get("place_id") != item.place_id:
                    continue

                matching_items.append((day, index))

        # Chỉ cho phép xóa khi xác định đúng một hoạt động
        if len(matching_items) != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Không thể xác định chính xác hoạt động "
                    "trong lịch trình AI. Dữ liệu chưa bị xóa."
                )
            )

        matched_day, matched_index = matching_items[0]
        matched_day["items"].pop(matched_index)

        # Cập nhật JSON nhưng giữ nguyên metadata khác
        itinerary.itinerary_data = updated_plan

    # Xóa bản ghi địa điểm trong Database
    db.delete(item)
    db.commit()

    return {
        "status": "success",
        "message": f"Đã xóa điểm dừng chân {item_id}"
    }
