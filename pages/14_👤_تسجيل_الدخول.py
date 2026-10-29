# pages/14_👤_تسجيل_الدخول.py
# صفحة "حسابي": معلومات المستخدم الحالي.
# (شاشة تسجيل الدخول نفسها أصبحت في app.py)
import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent))

st.set_page_config(page_title="حسابي", page_icon="👤", layout="wide")

from session_auth import logout_user
from sidebar import render_sidebar, role_label

render_sidebar()  # يحوّل لشاشة الدخول إن لم يكن مسجلاً

user = st.session_state.current_user

st.title("👤 حسابي")
st.success(f"مرحباً **{user['full_name']}**!")

st.markdown("---")
st.subheader("معلومات الحساب")

col1, col2 = st.columns(2)

with col1:
    st.write(f"**اسم المستخدم:** {user['username']}")
    st.write(f"**الاسم الكامل:** {user['full_name']}")
    st.write(f"**البريد الإلكتروني:** {user['email'] or 'غير محدد'}")

with col2:
    st.write(f"**الدور:** {role_label(user)}")
    st.write(f"**تاريخ الإنشاء:** {user['created_at'].strftime('%Y-%m-%d') if user['created_at'] else '-'}")
    st.write(f"**آخر دخول:** {user['last_login'].strftime('%Y-%m-%d %H:%M') if user['last_login'] else 'أول دخول'}")

st.markdown("---")

if st.button("🚪 تسجيل الخروج", type="primary"):
    logout_user()
    st.rerun()