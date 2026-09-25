from __future__ import annotations

import base64
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from starlette.background import BackgroundTask

from .db import Profile, SessionLocal, Translation, init_db
from .translations import seed_translations, translate, translate_name
from .word_export import export_profile

BASE_DIR = Path(__file__).resolve().parent.parent
EXPORT_DIR = BASE_DIR / "exports"
def _read_render_secret(name: str) -> str:
    path = Path("/etc/secrets") / name
    try:
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""
    except OSError:
        return ""


MANAGER_KEY = os.getenv("MANAGER_KEY") or _read_render_secret("manager_key") or "dev-manager-key-change-me"
MAX_PHOTO_BYTES = 5 * 1024 * 1024

# These fields are copied from the approved Word template and are not shown on the public form.
FIXED_RELIGION_VI = "Không"
FIXED_LANGUAGE_CHINESE = True
FIXED_LANGUAGE_TAIWANESE = False
FIXED_LANGUAGE_LEVEL = "basic"
FIXED_STUDIED_AT_CENTER = False

EXPORT_DIR.mkdir(parents=True, exist_ok=True)
init_db()
with SessionLocal() as _db:
    seed_translations(_db)

app = FastAPI(title="Worker Profile Form")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def _to_int(value: str | None):
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _bool(value: str | None) -> bool:
    return value in {"1", "true", "on", "yes", "Có", "co"}


def _format_birth_date(value: str) -> str:
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
        return dt.strftime("%Y/%m/%d")
    except Exception:
        return value.replace("-", "/")


def _calc_age(birth_date: str) -> int | None:
    try:
        dt = datetime.strptime(birth_date, "%Y/%m/%d").date()
    except Exception:
        return None
    today = date.today()
    return today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))


def _slug(text: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", text.strip())
    return text.strip("_") or "profile"


def _manager_guard(key: str):
    if key != MANAGER_KEY:
        raise HTTPException(status_code=404, detail="Not found")


def _family_job_value(job_type: str, other_value: str) -> str:
    """Convert the 3 public choices into the wording used in the Word output."""
    job_type = (job_type or "").strip().lower()
    if job_type == "agriculture":
        return "Nông Dân"
    if job_type == "industry":
        return "Công Nhân"
    if job_type == "other":
        return (other_value or "").strip()
    return ""


def _photo_to_data_uri(photo: UploadFile | None, raw: bytes) -> str:
    if not photo or not photo.filename or not raw:
        return ""
    suffix = Path(photo.filename).suffix.lower()
    mime = (photo.content_type or "").lower()
    allowed_suffixes = {".jpg", ".jpeg", ".png"}
    allowed_mimes = {"image/jpeg", "image/png"}
    if suffix not in allowed_suffixes or mime not in allowed_mimes:
        raise HTTPException(400, "Ảnh chỉ hỗ trợ JPG/JPEG/PNG")
    if len(raw) > MAX_PHOTO_BYTES:
        raise HTTPException(400, "Ảnh tối đa 5 MB")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _refresh_translations(db, p: Profile):
    """Re-apply the current approved dictionary before preview/export."""
    mapping = [
        ("education_zh", "education", p.education_vi),
        ("religion_zh", "religion", p.religion_vi),
        ("marital_status_zh", "marital_status", p.marital_status_vi),
        ("province_zh", "province", p.province_vi),
        ("father_job_zh", "job", p.father_job_vi),
        ("mother_job_zh", "job", p.mother_job_vi),
        ("spouse_job_zh", "job", p.spouse_job_vi),
        ("work_country_zh", "country", p.work_country_vi),
        ("work_description_zh", "work_description", p.work_description_vi),
    ]
    p.full_name_zh = translate_name(db, p.full_name_vi)
    for attr, category, vi in mapping:
        setattr(p, attr, translate(db, category, vi))
    db.commit()


@app.get("/", response_class=HTMLResponse)
def form_page(request: Request):
    return templates.TemplateResponse(request=request, name="form.html", context={})


@app.post("/submit")
async def submit_profile(
    code: str = Form("MS"),
    full_name_vi: str = Form(...),
    birth_date: str = Form(""),
    height_cm: str = Form(""),
    weight_kg: str = Form(""),
    education_vi: str = Form("Cấp III"),
    marital_status_vi: str = Form("Độc Thân"),
    province_vi: str = Form("TỈNH DAK LAK"),
    children_count: str = Form(""),
    sons_count: str = Form(""),
    daughters_count: str = Form(""),
    father_name: str = Form(""),
    father_birth_year: str = Form(""),
    father_job_type: str = Form(...),
    father_job_other: str = Form(""),
    mother_name: str = Form(""),
    mother_birth_year: str = Form(""),
    mother_job_type: str = Form(...),
    mother_job_other: str = Form(""),
    spouse_name: str = Form(""),
    spouse_birth_year: str = Form(""),
    spouse_job_type: str = Form(""),
    spouse_job_other: str = Form(""),
    siblings_count: str = Form(""),
    birth_order: str = Form(""),
    relatives_in_taiwan: Optional[str] = Form(None),
    work_country_vi: str = Form("Việt Nam"),
    work_period: str = Form(""),
    work_description_vi: str = Form("Làm nông"),
    taiwan_work_experience: Optional[str] = Form(None),
    has_passport: Optional[str] = Form(None),
    has_judicial_record: Optional[str] = Form(None),
    has_health_exam: Optional[str] = Form(None),
    smoking: Optional[str] = Form(None),
    alcohol: Optional[str] = Form(None),
    color_blind: Optional[str] = Form(None),
    tattoos: Optional[str] = Form(None),
    habit: Optional[str] = Form(None),
    photo: UploadFile | None = File(None),
):
    birth_date_fmt = _format_birth_date(birth_date) if birth_date else ""
    photo_raw = await photo.read() if photo and photo.filename else b""
    photo_value = _photo_to_data_uri(photo, photo_raw)

    father_job_vi = _family_job_value(father_job_type, father_job_other)
    mother_job_vi = _family_job_value(mother_job_type, mother_job_other)
    spouse_job_vi = _family_job_value(spouse_job_type, spouse_job_other)
    if not father_job_vi or not mother_job_vi:
        raise HTTPException(400, "Vui lòng chọn nghề nghiệp của cha và mẹ")
    if father_job_type == "other" and not father_job_other.strip():
        raise HTTPException(400, "Vui lòng nhập nghề khác của cha")
    if mother_job_type == "other" and not mother_job_other.strip():
        raise HTTPException(400, "Vui lòng nhập nghề khác của mẹ")
    if spouse_job_type == "other" and not spouse_job_other.strip():
        raise HTTPException(400, "Vui lòng nhập nghề khác của vợ/chồng")

    with SessionLocal() as db:
        profile = Profile(
            code=code.strip() or "MS",
            full_name_vi=full_name_vi.strip().upper(),
            full_name_zh=translate_name(db, full_name_vi),
            birth_date=birth_date_fmt,
            age=_calc_age(birth_date_fmt),
            height_cm=_to_int(height_cm),
            weight_kg=_to_int(weight_kg),
            education_vi=education_vi.strip(),
            education_zh=translate(db, "education", education_vi),
            religion_vi=FIXED_RELIGION_VI,
            religion_zh=translate(db, "religion", FIXED_RELIGION_VI),
            marital_status_vi=marital_status_vi.strip(),
            marital_status_zh=translate(db, "marital_status", marital_status_vi),
            province_vi=province_vi.strip(),
            province_zh=translate(db, "province", province_vi),
            language_chinese=FIXED_LANGUAGE_CHINESE,
            language_taiwanese=FIXED_LANGUAGE_TAIWANESE,
            language_level=FIXED_LANGUAGE_LEVEL,
            studied_at_center=FIXED_STUDIED_AT_CENTER,
            children_count=_to_int(children_count),
            sons_count=_to_int(sons_count),
            daughters_count=_to_int(daughters_count),
            father_name=father_name.strip().upper(),
            father_birth_year=_to_int(father_birth_year),
            father_job_vi=father_job_vi,
            father_job_zh=translate(db, "job", father_job_vi),
            mother_name=mother_name.strip().upper(),
            mother_birth_year=_to_int(mother_birth_year),
            mother_job_vi=mother_job_vi,
            mother_job_zh=translate(db, "job", mother_job_vi),
            spouse_name=spouse_name.strip().upper(),
            spouse_birth_year=_to_int(spouse_birth_year),
            spouse_job_vi=spouse_job_vi,
            spouse_job_zh=translate(db, "job", spouse_job_vi),
            siblings_count=_to_int(siblings_count),
            birth_order=_to_int(birth_order),
            relatives_in_taiwan=_bool(relatives_in_taiwan),
            work_country_vi=work_country_vi.strip(),
            work_country_zh=translate(db, "country", work_country_vi),
            work_period=work_period.strip(),
            work_description_vi=work_description_vi.strip(),
            work_description_zh=translate(db, "work_description", work_description_vi),
            taiwan_work_experience=_bool(taiwan_work_experience),
            has_passport=_bool(has_passport),
            has_judicial_record=_bool(has_judicial_record),
            has_health_exam=_bool(has_health_exam),
            smoking=_bool(smoking),
            alcohol=_bool(alcohol),
            color_blind=_bool(color_blind),
            tattoos=_bool(tattoos),
            habit=_bool(habit),
            form_date=date.today().strftime("%d/%m/%Y"),
            photo_path=photo_value,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        profile_id = profile.id
    return RedirectResponse(url=f"/success?id={profile_id}", status_code=303)


@app.get("/success", response_class=HTMLResponse)
def success_page(request: Request, id: int):
    return templates.TemplateResponse(request=request, name="success.html", context={"id": id})


@app.get("/manage/{key}", response_class=HTMLResponse)
def manage(request: Request, key: str, q: str = ""):
    _manager_guard(key)
    with SessionLocal() as db:
        stmt = select(Profile).order_by(Profile.id.desc())
        if q.strip():
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Profile.full_name_vi.ilike(like),
                    Profile.province_vi.ilike(like),
                    Profile.code.ilike(like),
                )
            )
        profiles = list(db.scalars(stmt).all())
    return templates.TemplateResponse(
        request=request,
        name="manage.html",
        context={"profiles": profiles, "key": key, "q": q},
    )


@app.get("/manage/{key}/dictionary", response_class=HTMLResponse)
def dictionary_page(request: Request, key: str):
    _manager_guard(key)
    with SessionLocal() as db:
        items = list(db.scalars(select(Translation).order_by(Translation.category, Translation.vi)).all())
    return templates.TemplateResponse(
        request=request,
        name="dictionary.html",
        context={"items": items, "key": key},
    )


@app.post("/manage/{key}/dictionary")
def dictionary_add(key: str, category: str = Form(...), vi: str = Form(...), zh: str = Form(...)):
    _manager_guard(key)
    category, vi, zh = category.strip(), vi.strip(), zh.strip()
    if not category or not vi or not zh:
        raise HTTPException(400, "Thiếu dữ liệu từ điển")
    with SessionLocal() as db:
        item = db.scalar(select(Translation).where(Translation.category == category, Translation.vi == vi))
        if item:
            item.zh = zh
        else:
            db.add(Translation(category=category, vi=vi, zh=zh))
        db.commit()
    return RedirectResponse(url=f"/manage/{key}/dictionary", status_code=303)


@app.get("/manage/{key}/profile/{profile_id}", response_class=HTMLResponse)
def profile_detail(request: Request, key: str, profile_id: int):
    _manager_guard(key)
    with SessionLocal() as db:
        p = db.get(Profile, profile_id)
        if not p:
            raise HTTPException(404, "Không tìm thấy hồ sơ")
        _refresh_translations(db, p)
        db.refresh(p)
        return templates.TemplateResponse(
            request=request,
            name="detail.html",
            context={"p": p, "key": key},
        )


@app.get("/manage/{key}/profile/{profile_id}/export")
def export_word(key: str, profile_id: int):
    _manager_guard(key)
    with SessionLocal() as db:
        p = db.get(Profile, profile_id)
        if not p:
            raise HTTPException(404, "Không tìm thấy hồ sơ")
        _refresh_translations(db, p)
        db.refresh(p)
        filename = f"{_slug(p.code)}_{_slug(p.full_name_vi)}_{_slug(p.birth_date[:4] if p.birth_date else '')}.docx"
        output = EXPORT_DIR / f"{profile_id}_{filename}"
        export_profile(p, output)

    def _cleanup():
        try:
            output.unlink(missing_ok=True)
        except Exception:
            pass

    return FileResponse(
        str(output),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        background=BackgroundTask(_cleanup),
    )


@app.post("/manage/{key}/profile/{profile_id}/delete")
def delete_profile(key: str, profile_id: int):
    _manager_guard(key)
    with SessionLocal() as db:
        p = db.get(Profile, profile_id)
        if not p:
            raise HTTPException(404, "Không tìm thấy hồ sơ")
        # Legacy local builds stored photos as file paths. Clean them up if they still exist.
        legacy_photo = p.photo_path or ""
        if legacy_photo and not legacy_photo.startswith("data:"):
            try:
                photo_file = Path(legacy_photo)
                if photo_file.is_file():
                    photo_file.unlink()
            except Exception:
                pass
        db.delete(p)
        db.commit()
    return RedirectResponse(url=f"/manage/{key}", status_code=303)


@app.get("/health")
def health():
    return {"ok": True}
