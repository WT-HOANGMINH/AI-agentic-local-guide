
import json
import re

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


def extract_json_object(text: str) -> dict:
    """Doc mot JSON object tu phan hoi cua Gemini."""

    text = text.strip()

    # Bo Markdown code fence neu Gemini tra ve kem theo.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("Phan hoi AI khong dung dinh dang JSON.")

    return data


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

        # Buoc 2: Lay danh sach dia diem tu MySQL.
        places = retrieve_places(
            intent=intent,
            max_price=request.max_price,
        )

        # Buoc 3: Chi cho Gemini chon ID tu danh sach cho phep.
        allowed_ids = {int(place["id"]) for place in places}
        context = json.dumps(
            places,
            ensure_ascii=False,
            default=str,
        )

        llm_input = (
            "Ban la AI Local Guide cho Da Nang.\n"
            "Du lieu dia diem duoi day la nguon duy nhat duoc phep su dung.\n"
            "Khong tu them dia diem, dia chi, gia, gio mo cua, toa do, "
            "thoi tiet hoac thong tin giao thong.\n\n"
            f"YEU CAU NGUOI DUNG:\n{message}\n\n"
            f"Y DINH DA NHAN DIEN: {intent}\n\n"
            f"DANH SACH MYSQL:\n{context}\n\n"
            "Hay tra ve duy nhat mot JSON object, khong co Markdown:\n"
            '{"answer":"Loi dan ngan bang tieng Viet",'
            '"place_ids":[1,2]}\n'
            "place_ids chi duoc chua ID nguyen co trong danh sach MYSQL.\n"
            "Khong tu tao ID. Neu khong co dia diem phu hop, dung [].\n"
            "answer khong duoc chua ten dia diem moi, dia chi, gia hoac "
            "gio mo cua tu suy doan.\n"
        )

        raw_answer = ask_llm(llm_input)
        generated = extract_json_object(raw_answer)

        # Buoc 4: Kiem tra ID Gemini tra ve.
        generated_ids = generated.get("place_ids", [])

        if not isinstance(generated_ids, list):
            generated_ids = []

        valid_ids = []
        for value in generated_ids:
            # Khong chap nhan bool, chuoi hoac ID khong ton tai.
            if type(value) is int and value in allowed_ids:
                if value not in valid_ids:
                    valid_ids.append(value)

        # Chi lay lai cac ban ghi da truy xuat tu MySQL.
        places_by_id = {
            int(place["id"]): place
            for place in places
        }
        selected_places = [
            places_by_id[place_id]
            for place_id in valid_ids
        ]

        # Khong dung nguyen van answer tu Gemini vi van co the bi bia.
        # Backend tu tao phan danh sach dia diem tu du lieu MySQL.
        if selected_places:
            lines = [
                "Goi y danh cho ban:",
            ]

            for index, place in enumerate(selected_places, start=1):
                lines.append(
                    f"{index}. {place['name']}"
                )

                if place.get("address"):
                    lines.append(
                        f"   Dia chi: {place['address']}"
                    )
                else:
                    lines.append(
                        "   Dia chi: chua co du lieu."
                    )

                if place.get("description"):
                    lines.append(
                        f"   Mo ta: {place['description']}"
                    )

                if place.get("price_level") is not None:
                    lines.append(
                        f"   Muc gia trong DB: {place['price_level']}/5"
                    )
                else:
                    lines.append(
                        "   Muc gia: chua co du lieu."
                    )

                if place.get("opening_hours"):
                    lines.append(
                        f"   Gio mo cua: {place['opening_hours']}"
                    )
                else:
                    lines.append(
                        "   Gio mo cua: chua co du lieu."
                    )

            ai_answer = "\n".join(lines)
        else:
            ai_answer = (
                "Minh chua tim thay dia diem phu hop trong "
                "du lieu hien co. Ban co the thu thay doi yeu cau."
            )

        # Buoc 5: Giu nguyen cac truong API de frontend hien tai su dung.
        return {
            "success": True,
            "message": ai_answer,
            "ai_answer": ai_answer,
            "intent": intent,
            "confidence": confidence,
            "places": selected_places,
        }

    except ValueError as exc:
        print(f"AI guide validation error: {exc}")
        raise HTTPException(
            status_code=502,
            detail="AI tra ve du lieu khong hop le. Vui long thu lai.",
        )

    except Exception as exc:
        print(
            f"AI guide error: {type(exc).__name__}: {exc}"
        )
        raise HTTPException(
            status_code=500,
            detail="Khong the xu ly yeu cau AI luc nay.",
        )
