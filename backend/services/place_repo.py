"""Điểm truy cập dữ liệu địa điểm duy nhất cho các dịch vụ AI (dễ thay thế khi kiểm thử)."""


def all_active(db):
    from backend.models.place import Place
    return db.query(Place).filter(Place.is_active.is_(True)).all()


def by_ids(db, ids):
    from backend.models.place import Place
    ids = list(ids)
    return db.query(Place).filter(Place.id.in_(ids)).all() if ids else []


def get(db, place_id):
    from backend.models.place import Place
    return db.get(Place, place_id)


def restaurants(db):
    return [p for p in all_active(db) if p.category == "restaurant"]
