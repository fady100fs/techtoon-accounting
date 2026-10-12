# -*- coding: utf-8 -*-
"""صفحة التقارير الموحّدة — تدمج 5 صفحات تقارير في 3 تبويبات."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
st.set_page_config(page_title="التقارير الموحدة", page_icon="📊", layout="wide")

from sidebar import render_sidebar
render_sidebar()

from auth_required import require_login
current_user = require_login()

from page_runner import run_page

st.title("📊 التقارير الموحدة")
st.caption("كل التقارير في مكان واحد: مالية، مخزون، مبيعات، أرباح، PDF")

tab_basic, tab_advanced, tab_pdf = st.tabs(["📊 أساسية", "📈 متقدمة", "📄 PDF"])

with tab_basic:
    run_page("التقارير")

with tab_advanced:
    report_type = st.selectbox("نوع التقرير المتقدم:", options=[
        "📈 تقارير متقدمة", "💰 تقرير الأرباح الدقيق", "📊 التقارير المالية",
    ], key="advanced_report_selector")
    report_map = {
        "📈 تقارير متقدمة": "تقارير_متقدمة",
        "💰 تقرير الأرباح الدقيق": "تقرير_الارباح",
        "📊 التقارير المالية": "التقارير_المالية",
    }
    run_page(report_map.get(report_type, "تقارير_متقدمة"))

with tab_pdf:
    run_page("تقارير_PDF")
