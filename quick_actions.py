# quick_actions.py
import streamlit as st


def render_quick_actions():
    st.caption("⚡ إجراءات سريعة")
    
    pages = [
        ("🛒 بيع", "4A_🛒_فواتير_البيع.py"),
        ("🛍️ شراء", "4B_🛍️_فواتير_الشراء.py"),
        ("💰 دفعة", "8_💰_المدفوعات.py"),
        ("📦 صنف", "2_📦_الاصناف.py"),
    ]
    
    cols = st.columns(2)
    for i, (label, fname) in enumerate(pages):
        with cols[i % 2]:
            st.page_link(f"pages/{fname}", label=label)
    
    st.markdown("---")
