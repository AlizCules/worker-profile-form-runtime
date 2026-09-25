import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

def _read_render_secret(name: str) -> str:
    path = Path("/etc/secrets") / name
    try:
        return path.read_text(encoding="utf-8").strip() if path.is_file() else ""
    except OSError:
        return ""


DATABASE_URL = os.getenv("DATABASE_URL") or _read_render_secret("database_url") or "sqlite:///./data/profiles.db"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    code: Mapped[str] = mapped_column(String(50), default="MS")

    full_name_vi: Mapped[str] = mapped_column(String(255))
    full_name_zh: Mapped[str] = mapped_column(String(255), default="")
    birth_date: Mapped[str] = mapped_column(String(20), default="")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[int | None] = mapped_column(Integer, nullable=True)

    education_vi: Mapped[str] = mapped_column(String(100), default="")
    education_zh: Mapped[str] = mapped_column(String(100), default="")
    religion_vi: Mapped[str] = mapped_column(String(100), default="")
    religion_zh: Mapped[str] = mapped_column(String(100), default="")
    marital_status_vi: Mapped[str] = mapped_column(String(100), default="")
    marital_status_zh: Mapped[str] = mapped_column(String(100), default="")
    province_vi: Mapped[str] = mapped_column(String(150), default="")
    province_zh: Mapped[str] = mapped_column(String(150), default="")

    language_chinese: Mapped[bool] = mapped_column(Boolean, default=False)
    language_taiwanese: Mapped[bool] = mapped_column(Boolean, default=False)
    language_level: Mapped[str] = mapped_column(String(30), default="basic")
    studied_at_center: Mapped[bool] = mapped_column(Boolean, default=False)

    children_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sons_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daughters_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    father_name: Mapped[str] = mapped_column(String(255), default="")
    father_birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    father_job_vi: Mapped[str] = mapped_column(String(150), default="")
    father_job_zh: Mapped[str] = mapped_column(String(150), default="")
    mother_name: Mapped[str] = mapped_column(String(255), default="")
    mother_birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mother_job_vi: Mapped[str] = mapped_column(String(150), default="")
    mother_job_zh: Mapped[str] = mapped_column(String(150), default="")
    spouse_name: Mapped[str] = mapped_column(String(255), default="")
    spouse_birth_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spouse_job_vi: Mapped[str] = mapped_column(String(150), default="")
    spouse_job_zh: Mapped[str] = mapped_column(String(150), default="")
    siblings_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    birth_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    relatives_in_taiwan: Mapped[bool] = mapped_column(Boolean, default=False)

    work_country_vi: Mapped[str] = mapped_column(String(150), default="")
    work_country_zh: Mapped[str] = mapped_column(String(150), default="")
    work_period: Mapped[str] = mapped_column(String(100), default="")
    work_description_vi: Mapped[str] = mapped_column(Text, default="")
    work_description_zh: Mapped[str] = mapped_column(Text, default="")
    taiwan_work_experience: Mapped[bool] = mapped_column(Boolean, default=False)

    has_passport: Mapped[bool] = mapped_column(Boolean, default=False)
    has_judicial_record: Mapped[bool] = mapped_column(Boolean, default=False)
    has_health_exam: Mapped[bool] = mapped_column(Boolean, default=False)

    smoking: Mapped[bool] = mapped_column(Boolean, default=False)
    alcohol: Mapped[bool] = mapped_column(Boolean, default=False)
    color_blind: Mapped[bool] = mapped_column(Boolean, default=False)
    tattoos: Mapped[bool] = mapped_column(Boolean, default=False)
    habit: Mapped[bool] = mapped_column(Boolean, default=False)

    form_date: Mapped[str] = mapped_column(String(20), default="")
    # Local legacy records can contain a path. New records store a data URI so cloud deploys
    # do not depend on an ephemeral filesystem for uploaded photos.
    photo_path: Mapped[str] = mapped_column(Text, default="")


class Translation(Base):
    __tablename__ = "translations"
    __table_args__ = (
        UniqueConstraint("category", "vi", name="uq_translation_category_vi"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    vi: Mapped[str] = mapped_column(String(255))
    zh: Mapped[str] = mapped_column(String(255))


def init_db():
    Base.metadata.create_all(bind=engine)
