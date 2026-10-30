"""Bộ xếp hạng địa điểm: TF-IDF (n-gram ký tự, không dấu) học trên chính dữ liệu địa điểm của dự án."""
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.services import place_repo
from backend.services import planner as pl
from backend.services.slot_service import strip_accents

INTEREST_QUERY = {
    "beach": "bien bai tam beach", "nature": "thien nhien nui rung xanh",
    "culture": "van hoa chua bao tang lich su", "food": "am thuc an uong dac san",
    "sunset": "hoang hon ngam canh", "photo": "check in chup anh song ao",
}
MEAL_QUERY = {
    "breakfast": "an sang banh mi bun mi quang pho xoi",
    "lunch": "com mi quang bun ca",
    "dinner": "hai san nuong lau",
}


class PlaceRanker:
    def __init__(self, places):
        self.places, self.X = list(places), None
        if self.places:
            docs = [strip_accents(f"{p.name} {p.name} {p.description or ''} {p.category} "
                                  f"{getattr(p, 'zone', '') or ''} {p.address or ''}") for p in self.places]
            self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
            self.X = self.vec.fit_transform(docs)

    def score_map(self, query):
        if self.X is None:
            return {}
        sims = (self.X @ self.vec.transform([strip_accents(query)]).T).toarray().ravel()
        top = sims.max() or 1.0
        return {p.id: 0.8 * (s / top) + 0.2 * ((p.rating or 3.5) / 5) for p, s in zip(self.places, sims)}

    def rank(self, query, k=4, categories=None, anchor=None, exclude=()):
        sm, out = self.score_map(query), []
        for p in self.places:
            if p.id in exclude or (anchor is not None and p.id == anchor.id):
                continue
            if categories and p.category not in categories:
                continue
            s = sm.get(p.id, 0)
            if anchor is not None:
                s = 0.65 * s + 0.35 / (1 + pl.travel_min(anchor, p) / 15)   # ưu tiên gần điểm neo
            out.append((s, p))
        out.sort(key=lambda x: -x[0])
        return [p for _, p in out[:k]]


_cache = {"key": None, "ranker": None}


def get_ranker(db):
    rows = place_repo.all_active(db)
    key = (len(rows), max((p.id for p in rows), default=0))
    if _cache["key"] != key:
        _cache.update(key=key, ranker=PlaceRanker(rows))
    return _cache["ranker"]
