"""
database.py — إعداد الاتصال بـ Neon PostgreSQL (نسخة محسّنة للأداء)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()


def _get_database_url() -> str:
    """قراءة الرابط من secrets أو من .env."""
    url = None

    # 1. محاولة st.secrets (على Streamlit Cloud)
    try:
        import streamlit as st
        url = st.secrets.get("DATABASE_URL")
    except Exception:
        pass

    # 2. الرجوع إلى متغيرات البيئة (.env محلياً)
    if not url:
        url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError(
            "DATABASE_URL غير موجود! أضفه في .env محلياً أو في secrets.toml على السحابة."
        )

    # توحيد الصيغة
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


# ============ إعداد Engine محسّن ============
DATABASE_URL = _get_database_url()

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=280,          # ⭐ يعيد الاتصال قبل نوم Neon (300s)
    pool_timeout=30,
    connect_args={
        "connect_timeout": 10,
        "application_name": "techtoon_accounting",
    },
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


# ⭐ هذا السطر الذي كان ناقصاً — مهم جداً لـ models.py
Base = declarative_base()


def get_db():
    """مولّد جلسة قاعدة بيانات."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    """جلسة مباشرة (للاستخدام السريع)."""
    return SessionLocal()

# ═══════════════════════════════════════════════════════
#  Helpers (auto-added) — تعمل مع Neon أو SQLite بأمان
# ═══════════════════════════════════════════════════════
import os as _os

def is_local_mode():
    """هل نحن في وضع محلي (SQLite Mirror)؟"""
    return _os.getenv("DEPLOY_MODE", "cloud").lower() == "local"


def _try_local():
    """محاولة تحميل SQLite Mirror بأمان — ترجع None عند الفشل."""
    try:
        from local_mirror import LocalSession, init_local_schema
        init_local_schema()
        return LocalSession
    except Exception:
        return None


_READ_SESSION_FACTORY = None
_READ_INIT_DONE = False


def get_read_session():
    """
    جلسة قراءة:
    - محلياً مع SQLite Mirror متاح → SQLite (سريع)
    - غير ذلك → Neon مباشرة
    """
    global _READ_SESSION_FACTORY, _READ_INIT_DONE
    if not _READ_INIT_DONE:
        _READ_INIT_DONE = True
        if is_local_mode():
            _READ_SESSION_FACTORY = _try_local()
    if _READ_SESSION_FACTORY is not None:
        return _READ_SESSION_FACTORY()
    return SessionLocal()


def get_write_session():
    """جلسة كتابة — Neon دائماً."""
    return SessionLocal()


def get_local_db_path():
    """مسار SQLite المحلي (إن وُجد)."""
    try:
        from local_mirror import LOCAL_DB_PATH
        return LOCAL_DB_PATH
    except Exception:
        return None
