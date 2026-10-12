# -*- coding: utf-8 -*-
"""صفحة النسخ الاحتياطي الموحّدة — تدمج النسخ المحلي والسحابي في 2 تبويبات."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
st.set_page_config(page_title="النسخ الاحتياطي", page_icon="💾", layout="wide")

from sidebar import render_sidebar
render_sidebar()

from auth_required import require_login, get_current_user_id, get_current_user_name
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

from page_runner import run_page

st.title("💾 النسخ الاحتياطي")
st.caption("نسخ احتياطي محلي وسحابي في مكان واحد")

tab_local, tab_cloud = st.tabs(["💽 محلي", "☁️ سحابي"])

with tab_local:
    run_page("النسخ_الاحتياطي")
with tab_cloud:
    run_page("النسخ_السحابي")
