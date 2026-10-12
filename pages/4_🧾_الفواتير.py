# -*- coding: utf-8 -*-
"""صفحة الفواتير الموحّدة — تدمج فواتير البيع والشراء والفهرس في 3 تبويبات."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
st.set_page_config(page_title="الفواتير", page_icon="🧾", layout="wide")

from sidebar import render_sidebar, queue_state_updates
render_sidebar()

from auth_required import require_login, get_current_user_id
current_user = require_login()
current_user_id = get_current_user_id()

from page_runner import run_page

st.title("🧾 الفواتير")
st.caption("إدارة فواتير البيع والشراء وفهرس كل الفواتير في مكان واحد")

tab_sale, tab_purchase, tab_index = st.tabs(["📤 فواتير البيع", "📥 فواتير الشراء", "📋 فهرس الفواتير"])

with tab_sale:
    run_page("فواتير_البيع")
with tab_purchase:
    run_page("فواتير_الشراء")
with tab_index:
    run_page("فهرس_الفواتير")
