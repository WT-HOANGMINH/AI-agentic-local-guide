"""
Kiểm tra và sửa lịch trình theo dự báo THEO GIỜ.

Với mỗi điểm tham quan trong một ngày của lịch trình:
  1. lấy khung giờ (start-end) của điểm đó,
  2. tra rủi ro thời tiết của các giờ đó (weather_analyzer.classify_hour),
  3. nếu điểm ngoài trời / phụ thuộc thời tiết rơi vào giờ mưa to, dông, gió mạnh
     -> đổi sang một điểm TRONG NHÀ có thật trong dữ liệu (gần nhất),
  4. điểm do chính người dùng yêu cầu thì KHÔNG tự bỏ: giữ lại và cảnh báo rõ.

Module này không import planner/DB: mọi thao tác thực tế (replan, tra địa điểm)
được truyền vào dưới dạng hàm, nên test được độc lập.
Không có dữ liệu thì không kết luận: dữ liệu cũ (stale) không dùng để đổi lịch.
"""
from __future__ import annotations

from backend.enrich_weather_profile import classify as classify_profile
from backend.services.weather_analyzer import (
    analyze_date,
    classify_hour,
    poi_allowed,
    recommend_transport,
)
from backend.services.weather_chat import summary_lines


def profile_of(place) -> str:
    """indoor | outdoor | weather_dependent. Ưu tiên cột weather_profile, không có thì suy ra."""
    value = getattr(place, "weather_profile", None)
    if value:
        return value
    return classify_profile(place.name, place.category,
                            getattr(place, "description", "") or "",
                            getattr(place, "address", "") or "")


def hour_risks(forecast: dict, iso: str) -> dict[int, dict]:
    return {int(h["time"][11:13]): classify_hour(h)
            for h in forecast["hours"] if h["time"].startswith(iso)}


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def window_risk(hr: dict[int, dict], start: str, end: str) -> dict | None:
    """Giờ xấu nhất trong khung [start, end). None nếu không có dữ liệu giờ nào."""
    s, e = _to_min(start), _to_min(end)
    hours = range(s // 60, max(s // 60, (e - 1) // 60) + 1)
    items = [hr[h] for h in hours if h in hr]
    return max(items, key=lambda c: c["risk"]) if items else None


def find_affected(day: dict, by_id: dict, hr: dict, protected=frozenset()) -> list[dict]:
    """Điểm tham quan không hợp thời tiết trong khung giờ được xếp (bỏ qua điểm trong nhà)."""
    attr_ids = set(day.get("attr_ids", []))
    out = []
    for s in day.get("stops", []):
        pid = s.get("id")
        if pid is None or pid not in attr_ids or not s.get("start") or not s.get("end"):
            continue
        place = by_id.get(pid)
        if place is None:
            continue
        prof = profile_of(place)
        if prof == "indoor":
            continue
        w = window_risk(hr, s["start"], s["end"])
        if w is not None and not poi_allowed(prof, w["risk"]):
            out.append({"stop": s, "place": place, "profile": prof, "risk": w["risk"],
                        "label": w["label"], "protected": pid in protected})
    return out


def _safe_minutes(travel_min, a, b) -> float:
    try:
        return float(travel_min(a, b))
    except Exception:
        return 10 ** 6


def pick_indoor_alternative(anchor, pool, used_ids, travel_min):
    cands = [p for p in pool if p.id not in used_ids and profile_of(p) == "indoor"]
    if not cands:
        return None
    return min(cands, key=lambda p: _safe_minutes(travel_min, anchor, p))


def nearest_backups(anchor, backups_pool, travel_min, n=2) -> list[str]:
    cands = [p for p in backups_pool if profile_of(p) == "indoor" and p.id != anchor.id]
    cands.sort(key=lambda p: _safe_minutes(travel_min, anchor, p))
    return [p.name for p in cands[:n]]


def adjust_day(*, idx, iso, forecast, get_day, by_id_fn, used_ids_fn, replan, pool,
               travel_min, protected=frozenset(), backups_pool=(), max_iter=4) -> dict:
    """
    get_day()      -> dict của ngày hiện tại trong kế hoạch (luôn lấy bản mới nhất)
    by_id_fn()     -> {id: Place} của kế hoạch hiện tại
    used_ids_fn()  -> tập id điểm tham quan đang có trong cả kế hoạch
    replan(old_id, new_id) -> thực hiện đổi, trả về kết quả replan_day (có thể có 'dropped')
    """
    a = analyze_date(forecast, iso)
    report = {"date": iso, "analysis": a, "available": bool(a.get("available")),
              "changes": [], "unresolved": [], "stale": bool(forecast.get("is_stale")),
              "risk": a.get("max_risk", 0)}
    if not report["available"] or report["stale"]:
        return report                      # không có / dữ liệu cũ: không đổi lịch dựa trên đó

    hr = hour_risks(forecast, iso)
    tried: set = set()
    for _ in range(max_iter):
        todo = [x for x in find_affected(get_day(), by_id_fn(), hr, protected)
                if not x["protected"] and x["place"].id not in tried]
        if not todo:
            break
        x = todo[0]
        old = x["place"]
        tried.add(old.id)
        alt = pick_indoor_alternative(old, pool, used_ids_fn(), travel_min)
        if alt is None:
            continue
        try:
            res = replan(old.id, alt.id)
        except Exception:
            continue
        placed = next((s for s in get_day()["stops"] if s.get("id") == alt.id), None)
        report["changes"].append({
            "old": old.name, "new": alt.name, "label": x["label"],
            "start": placed.get("start") if placed else None,
            "end": placed.get("end") if placed else None,
            "dropped": list((res or {}).get("dropped") or []),
        })

    by_id = by_id_fn()
    for x in find_affected(get_day(), by_id, hr, protected):
        if x["protected"]:
            reason = "protected"
        elif pick_indoor_alternative(x["place"], pool, used_ids_fn(), travel_min) is None:
            reason = "no_indoor"
        else:
            reason = "replan_failed"
        report["unresolved"].append({
            "name": x["place"].name, "start": x["stop"]["start"], "end": x["stop"]["end"],
            "label": x["label"], "risk": x["risk"], "reason": reason,
            "backups": nearest_backups(x["place"], backups_pool, travel_min),
        })
    return report


_REASON = {
    "protected": "đây là điểm bạn yêu cầu nên mình giữ lại",
    "no_indoor": "dữ liệu hiện chưa có điểm tham quan trong nhà phù hợp để thay",
    "replan_failed": "mình chưa xếp lại được lịch với điểm thay thế",
}


def day_block(label: str, report: dict, forecast: dict) -> str:
    """Đoạn thời tiết cho một ngày của lịch trình, toàn bộ lấy từ số liệu thật."""
    a = report["analysis"]
    if not report["available"]:
        last = forecast["daily"][-1]["date"] if forecast.get("daily") else "?"
        return (f"Thời tiết {label}: nguồn dự báo của mình chỉ có đến {last}, nên chưa kiểm tra "
                "được ngày này. Bạn xem lại dự báo gần ngày đi nhé.")

    lines = [
        f"Thời tiết {label} ở Đà Nẵng (Open-Meteo, cập nhật {a['fetched_at']}; "
        "https://open-meteo.com/en/docs):"
    ]
    lines += summary_lines(a)

    if report["stale"]:
        lines.append(
            f"⚠ Đây là dữ liệu cũ (lưu cách đây {forecast.get('stale_minutes', '?')} phút) vì mình "
            "không kết nối được nguồn dự báo, nên mình KHÔNG dùng nó để đổi lịch trình. "
            "Bạn kiểm tra lại dự báo trước khi đi."
        )
        return "\n".join(lines)

    risk = a["max_risk"]
    for c in report["changes"]:
        when = f" ({c['start']}–{c['end']})" if c.get("start") else ""
        lines.append(f"- Đã đổi “{c['old']}” sang “{c['new']}”{when} vì khung giờ đó dự báo "
                     f"{c['label'].lower()}.")
        if c["dropped"]:
            lines.append("  (Do đổi nên không còn đủ thời gian cho: " + ", ".join(c["dropped"]) + ".)")
    for u in report["unresolved"]:
        extra = f" Chỗ trong nhà gần đó có thể ghé: {', '.join(u['backups'])}." if u["backups"] else ""
        lines.append(f"- “{u['name']}” ({u['start']}–{u['end']}) vẫn là điểm ngoài trời dù khung giờ "
                     f"này dự báo {u['label'].lower()}: {_REASON[u['reason']]}.{extra}")

    if risk >= 3:
        lines.append("Ưu tiên an toàn: nên cân nhắc hoãn các hoạt động ngoài trời. Open-Meteo không có "
                     "cảnh báo chính thức, bạn nên xem thêm bản tin của Trung tâm Dự báo Khí tượng "
                     "Thủy văn Quốc gia.")
    elif risk == 0 and not report["changes"]:
        lines.append("Dự báo ổn nên mình giữ nguyên lịch trình.")
    lines.append("- Phương tiện: " + recommend_transport(risk))
    if risk >= 1:
        lines.append("Nhớ mang ô hoặc áo mưa, giày chống trơn và bọc điện thoại nhé!")
    lines.append("Dự báo luôn có sai số, bạn kiểm tra lại trước khi đi.")
    return "\n".join(lines)
