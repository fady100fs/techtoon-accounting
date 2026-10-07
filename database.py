"""
database.py — إعداد الاتصال بـ Neon PostgreSQL (نسخة محسّنة للأداء)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
    expire_on_commit=False,    # ⭐ يسرّع الاستعلامات بعد commit
)


def get_db():
    """مولّد جلسة قاعدة بيانات."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()