# -*- coding: utf-8 -*-
"""صفحة النظام والإعدادات الموحّدة — تدمج الإعدادات والمستخدمين والفحوص في 3 تبويبات."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
st.set_page_config(page_title="النظام والإعدادات", page_icon="⚙️", layout="wide")

from sidebar import render_sidebar, queue_state_updates, can_modify, require_modify
render_sidebar()

from auth_required import require_login, get_current_user_id, get_current_user_name
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

from page_runner import run_page

st.title("⚙️ النظام والإعدادات")
st.caption("الإعدادات وإدارة المستخدمين والفحوص في مكان واحد")

tab_settings, tab_users, tab_diag = st.tabs(["🔧 الإعدادات", "👤 المستخدمون", "🔍 الفحوص"])

with tab_settings:
    run_page("الإعدادات")
with tab_users:
    run_page("إدارة_المستخدمين")
with tab_diag:
    diag_type = st.selectbox("نوع الفحص:", options=[
        "🔍 فحص السلامة المحاسبية",
        "🩺 فحص الاتصال بقاعدة البيانات",
    ], key="diag_selector")
    diag_map = {
        "🔍 فحص السلامة المحاسبية": "فحص_السلامة",
        "🩺 فحص الاتصال بقاعدة البيانات": "فحص_الاتصال",
    }
    run_page(diag_map.get(diag_type, "فحص_السلامة"))
