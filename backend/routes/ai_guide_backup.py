
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.intent_service import predict_intent
from backend.services.place_tool import search_places
from backend.services.llm_service import ask_llm


router = APIRouter(
    prefix="/api/ai-guide",
    tags=["AI Local Guide"],
)


class GuideRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Cau hoi du lich cua nguoi dung",
    )

    max_price: int = Field(
        default=5,
        ge=1,
        le=5,
        description="Muc gia toi da tu 1 den 5",
    )


def retrieve_places(intent: str, max_price: int) -> list[dict]:
    """Lay dia diem tu MySQL theo y dinh da nhan dien."""

    category_map = {
        "food": "restaurant",
        "attraction": "tourist_attraction",
        "cafe": "cafe",
    }

    # Cac y dinh can nhieu loai dia diem de lap ke hoach.
    if intent in {"itinerary", "transport"}:
        categories = [
            "tourist_attraction",
            "restaurant",
            "cafe",
        ]
    else:
        categories = [category_map.get(intent, "")]

    results = []
    seen_ids = set()

    for category in categories:
        places = search_places.invoke({
            "keyword": "",
            "category": category,
            "max_price": max_price,
        })

        for place in places:
            if place["id"] not in seen_ids:
                seen_ids.add(place["id"])
                results.append(place)

    return results


@router.post("/ask")
def ask_ai_guide(request: GuideRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Vui long nhap cau hoi.",
        )

    try:
        # Buoc 1: Mo hinh tu huan luyen nhan dien y dinh.
        prediction = predict_intent(message)
        intent = prediction["intent"]
        confidence = prediction["confidence"]

        # Buoc 2: Tim dia diem that trong MySQL.
        places = retrieve_places(
            intent=intent,
            max_price=request.max_price,
        )

        # Buoc 3: Gui cau hoi va du lieu truy xuat duoc cho Gemini.
        context = json.dumps(
            places,
            ensure_ascii=False,
            default=str,
        )

        llm_input = (
            "YEU CAU CUA NGUOI DUNG:\n"
            f"{message}\n\n"
            "Y DINH DO MO HINH TU HUAN LUYEN NHAN DIEN:\n"
            f"{intent}\n\n"
            "DANH SACH DIA DIEM TRUY XUAT TU MYSQL (JSON):\n"
            f"{context}\n\n"
            "HUONG DAN:\n"
            "- Tra loi bang tieng Viet tu nhien, huu ich.\n"
            "- Chi gioi thieu dia diem co trong JSON.\n"
            "- Khong tu bia dia diem, gia, gio mo cua hoac toa do.\n"
            "- Neu mot truong du lieu la null, hay noi ro chua co du lieu.\n"
            "- Neu danh sach rong, hay noi chua tim thay dia diem phu hop.\n"
            "- Neu lap lich trinh, sap xep cac dia diem thanh ke hoach hop ly.\n"
            "- Khong khang dinh da kiem tra thoi tiet, giao thong "
            "hoac tinh duoc tuyen duong neu chua co cong cu tuong ung.\n"
        )

        ai_answer = ask_llm(llm_input)

        # Buoc 4: Tra ve cau tra loi va dia diem cho frontend.
        return {
            "success": True,
            "message": ai_answer,
            "ai_answer": ai_answer,
            "intent": intent,
            "confidence": confidence,
            "places": places,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        print(
            f"AI guide error: {type(exc).__name__}: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail="Khong the xu ly yeu cau AI luc nay.",
        )
