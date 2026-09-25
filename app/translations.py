"""Approved seed dictionary and DB-backed translation helpers."""
from sqlalchemy import select

from .db import Translation

SEED_TRANSLATIONS = {
    "education": {"Cấp III": "高中"},
    "religion": {"Không": "無"},
    "marital_status": {"Độc Thân": "未婚"},
    "province": {"TỈNH DAK LAK": "多樂省", "Đắk Lắk": "多樂省"},
    "job": {
        "Nông Dân": "农夫",
        "Nông dân": "农夫",
        "Công Nhân": "工人",
        "Công nhân": "工人",
    },
    "country": {"Việt Nam": "越南"},
    "work_description": {"Làm nông": "務農"},
    "name_token": {"ĐOÀN": "段", "THẾ": "世", "SỸ": "士"},
}


def seed_translations(db):
    changed = False
    for category, pairs in SEED_TRANSLATIONS.items():
        for vi, zh in pairs.items():
            exists = db.scalar(
                select(Translation).where(Translation.category == category, Translation.vi == vi)
            )
            if not exists:
                db.add(Translation(category=category, vi=vi, zh=zh))
                changed = True
    if changed:
        db.commit()


def translate(db, category: str, value: str | None) -> str:
    if not value:
        return ""
    value = value.strip()
    item = db.scalar(
        select(Translation).where(Translation.category == category, Translation.vi == value)
    )
    return item.zh if item else ""


def translate_name(db, full_name: str | None) -> str:
    if not full_name:
        return ""
    tokens = [t for t in full_name.upper().strip().split() if t]
    converted = []
    for token in tokens:
        item = db.scalar(
            select(Translation).where(
                Translation.category == "name_token", Translation.vi == token
            )
        )
        if not item:
            return ""
        converted.append(item.zh)
    return "".join(converted)
