# -*- coding: utf-8 -*-
"""صفحة الموظفين والرواتب الموحّدة — تدمج الموظفين والقروض في 2 تبويبات."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
st.set_page_config(page_title="الموظفون والرواتب", page_icon="👥", layout="wide")

from sidebar import render_sidebar, queue_state_updates, can_modify, require_modify
render_sidebar()

from auth_required import require_login, get_current_user_id
current_user = require_login()
current_user_id = get_current_user_id()

from page_runner import run_page

st.title("👥 الموظفون والرواتب")
st.caption("إدارة الموظفين والرواتب والقروض والسلف في مكان واحد")

tab_staff, tab_loans = st.tabs(["👔 الموظفون والرواتب", "💼 القروض والسلف"])

with tab_staff:
    run_page("الموظفين_والرواتب")
with tab_loans:
    run_page("إدارة_القروض")
