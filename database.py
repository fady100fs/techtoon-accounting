# database.py
# الاتصال بقاعدة بيانات Neon PostgreSQL السحابية
# يدعم:
#   - محليًا: قراءة DATABASE_URL من ملف .env
#   - على Streamlit Cloud: قراءة DATABASE_URL من st.secrets
import os
from pathlib import Path

# ==========================================
# 1. قراءة DATABASE_URL
# ==========================================
DATABASE_URL = None

# أ) نحاول من st.secrets أولاً (للنشر على Streamlit Cloud)
try:
    import streamlit as st
    if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
        DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    pass

# ب) لو مش موجود، نقرأ من .env (محليًا)
if not DATABASE_URL:
    try:
        from dotenv import load_dotenv
        _env_path = Path(__file__).parent / ".env"
        load_dotenv(dotenv_path=_env_path, override=False)
    except ImportError:
        pass
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# ج) لو مفيش الاتنين → خطأ واضح
if not DATABASE_URL:
    raise RuntimeError(
        "❌ لم يتم العثور على DATABASE_URL.\n"
        "محلياً: ضعه في ملف .env\n"
        "على Streamlit Cloud: ضعه في Secrets"
    )

# ==========================================
# 2. تحويل الرابط لصيغة SQLAlchemy + psycopg3
# ==========================================
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

# ==========================================
# 3. إنشاء المحرك (Connection Pool محسّن)
# ==========================================
from sqlalchemy import create_engine, event

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_timeout=30,
    isolation_level="AUTOCOMMIT",
)

# ==========================================
# 4. طبقة توافقية: دالة strftime لـ PostgreSQL
# ==========================================
# البرنامج بيستخدم func.strftime (خاص بـ SQLite) في بعض الصفحات.
# هنعرّف نسخة مكافئة في PostgreSQL تحوّل الصيغة لـ to_char.

_STRFTIME_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION strftime(fmt TEXT, ts TIMESTAMP)
RETURNS TEXT AS $$
DECLARE
    pg_fmt TEXT;
BEGIN
    IF ts IS NULL THEN RETURN NULL; END IF;
    pg_fmt := fmt;
    pg_fmt := REPLACE(pg_fmt, '%Y', 'YYYY');
    pg_fmt := REPLACE(pg_fmt, '%m', 'MM');
    pg_fmt := REPLACE(pg_fmt, '%d', 'DD');
    pg_fmt := REPLACE(pg_fmt, '%H', 'HH24');
    pg_fmt := REPLACE(pg_fmt, '%M', 'MI');
    pg_fmt := REPLACE(pg_fmt, '%S', 'SS');
    RETURN to_char(ts, pg_fmt);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION strftime(fmt TEXT, ts TIMESTAMPTZ)
RETURNS TEXT AS $$
BEGIN
    IF ts IS NULL THEN RETURN NULL; END IF;
    RETURN strftime(fmt, ts::timestamp);
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

@event.listens_for(engine, "connect")
def _ensure_strftime_function(dbapi_conn, connection_record):
    """عند كل اتصال جديد، نضمن وجود دالة strftime."""
    try:
        cursor = dbapi_conn.cursor()
        cursor.execute(_STRFTIME_FUNCTION_SQL)
        cursor.close()
        try:
            dbapi_conn.commit()
        except Exception:
            pass
    except Exception as e:
        print(f"⚠️ تحذير: إنشاء دالة strftime فشل: {e}")

# ==========================================
# 5. الجلسة والقاعدة
# ==========================================
from sqlalchemy.orm import sessionmaker, declarative_base

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()