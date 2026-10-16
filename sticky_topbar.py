# sticky_topbar.py
import streamlit as st


def render_topbar():
    st.markdown("---")
    
    pages = [
        ("🛒 بيع", "4A_🛒_فواتير_البيع.py"),
        ("🛍️ شراء", "4B_🛍️_فواتير_الشراء.py"),
        ("💰 مدفوعات", "8_💰_المدفوعات.py"),
        ("📦 أصناف", "2_📦_الاصناف.py"),
        ("👥 عملاء", "3_👥_عملاء وموردين.py"),
        ("🏠 رئيسية", "app.py"),
    ]
    
    cols = st.columns(len(pages))
    for i, (label, fname) in enumerate(pages):
        with cols[i]:
            if fname == "app.py":
                st.page_link("app.py", label=label)
            else:
                st.page_link(f"pages/{fname}", label=label)
    
    st.markdown("---")
