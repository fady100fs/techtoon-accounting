"""
صفحة Ping — لإبقاء Streamlit Cloud و Neon مستيقظين.
لا تشارك رابطها مع العملاء.
"""

import streamlit as st
from datetime import datetime
import time

st.set_page_config(page_title="Ping", page_icon="🩺", layout="centered")

t0 = time.time()
db_status = "unknown"
try:
    from database import engine
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    db_status = "✅ متصلة"
    db_time = round((time.time() - t0) * 1000)
except Exception as e:
    db_status = f"❌ خطأ: {str(e)[:100]}"
    db_time = -1

st.write("OK")
st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption(f"💾 قاعدة البيانات: {db_status} ({db_time} ms)")