# pages/4B_🛍️_فواتير_الشراء.py
"""صفحة فواتير الشراء — منفصلة عن البيع"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import streamlit as st
st.set_page_config(page_title="فواتير الشراء", page_icon="🛍️", layout="wide")

try:
    from keyboard_nav import enable_enter_navigation, add_enter_hint
    enable_enter_navigation()
    add_enter_hint()
except Exception:
    pass

from invoice_page_common import render_invoice_page

render_invoice_page("purchase")
