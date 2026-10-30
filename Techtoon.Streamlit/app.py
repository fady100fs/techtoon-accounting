import streamlit as st
import database as db
from datetime import datetime, date

st.set_page_config(page_title="Techtoon Accounting", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

if "user" not in st.session_state: st.session_state.user = None
if "current_page" not in st.session_state: st.session_state.current_page = "dashboard"

def login_page():
    st.markdown("""<style>.main > div {padding-top: 2rem;} .stButton > button {width: 100%; border-radius: 8px;}</style>""", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("## 📊 Techtoon Accounting")
        st.markdown("### تسجيل الدخول")
        st.markdown("---")
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("🔐 تسجيل الدخول", use_container_width=True):
            if username and password:
                try:
                    _, rows = db.execute_query("SELECT id, username, full_name, role, is_active, password_hash FROM users WHERE username=%s AND is_active=TRUE", (username,), fetch=True)
                    if rows:
                        if db.verify_password(password, rows[0][5]):
                            st.session_state.user = {"id": rows[0][0], "username": rows[0][1], "full_name": rows[0][2], "role": rows[0][3]}
                            st.rerun()
                        else: st.error("❌ كلمة المرور غير صحيحة")
                    else: st.error("❌ المستخدم غير موجود")
                except Exception as e: st.error(f"❌ خطأ: {e}")

def dashboard():
    st.title("📊 لوحة التحكم")
    try:
        _, r1 = db.execute_query("SELECT COALESCE(SUM(total),0), COUNT(*) FROM invoices WHERE type='sales' AND DATE(date)=CURRENT_DATE", fetch=True)
        _, r2 = db.execute_query("SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type='receipt' AND DATE(date)=CURRENT_DATE", fetch=True)
        _, r3 = db.execute_query("SELECT COALESCE(SUM(total-paid_amount),0) FROM invoices WHERE type='sales' AND paid_amount<total AND status<>'cancelled'", fetch=True)
        _, r4 = db.execute_query("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE DATE(date)=CURRENT_DATE", fetch=True)
        _, r5 = db.execute_query("SELECT COALESCE(SUM(opening_quantity * COALESCE(avg_cost_price, cost_price, 0)),0) FROM items WHERE is_kit IS NOT TRUE", fetch=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 مبيعات اليوم", f"{float(r1[0][0]):,.2f}", f"{r1[0][1]} فاتورة")
        c2.metric("💳 ديون العملاء", f"{float(r3[0][0]):,.2f}")
        c3.metric("📦 قيمة المخزون", f"{float(r5[0][0]):,.2f}")
        c4.metric("💸 مصروفات اليوم", f"{float(r4[0][0]):,.2f}")
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📋 آخر الفواتير")
            _, rows = db.execute_query("SELECT i.invoice_number, i.date, COALESCE(p.name,''), i.total, i.status FROM invoices i LEFT JOIN parties p ON i.party_id=p.id ORDER BY i.date DESC LIMIT 5", fetch=True)
            if rows:
                import pandas as pd
                st.dataframe(pd.DataFrame(rows, columns=["رقم", "التاريخ", "العميل", "الإجمالي", "الحالة"]), use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"خطأ: {e}")

if st.session_state.user is None: login_page()
else:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['full_name']}")
        st.caption(f"الدور: {st.session_state.user['role']}")
        st.markdown("---")
        if st.button("📊 لوحة التحكم", use_container_width=True): st.session_state.current_page = "dashboard"; st.rerun()
        with st.expander("📄 المبيعات والعملاء"):
            if st.button("🛒 الفواتير", use_container_width=True): st.session_state.current_page = "invoices"; st.rerun()
            if st.button("👥 العملاء", use_container_width=True): st.session_state.current_page = "parties"; st.rerun()
            if st.button("💰 المدفوعات", use_container_width=True): st.session_state.current_page = "payments"; st.rerun()
        with st.expander("📦 المخزون والجرد", expanded=True):
            if st.button("📦 الأصناف", use_container_width=True): st.session_state.current_page = "items"; st.rerun()
            if st.button("📦 أرصدة المخزون", use_container_width=True): st.session_state.current_page = "stock_levels"; st.rerun()
            if st.button("📋 جلسات الجرد", use_container_width=True): st.session_state.current_page = "stock_counts"; st.rerun()
            if st.button("⚖️ تسويات المخزون", use_container_width=True): st.session_state.current_page = "stock_adjustments"; st.rerun()
            if st.button("💣 الأصناف التالفة", use_container_width=True): st.session_state.current_page = "damaged_items"; st.rerun()
            if st.button("🗑️ طلبات الشطب", use_container_width=True): st.session_state.current_page = "writeoff_requests"; st.rerun()
        with st.expander("💹 المالية والتقارير"):
            if st.button("📈 التقارير", use_container_width=True): st.session_state.current_page = "reports"; st.rerun()
        st.markdown("---")
        if st.button("🚪 تسجيل الخروج", use_container_width=True): st.session_state.user = None; st.rerun()

    page = st.session_state.current_page
    if page == "dashboard": dashboard()
    elif page == "invoices":
        import pages.invoices as m; m.show()
    elif page == "items":
        import pages.items as m; m.show()
    elif page == "parties":
        import pages.parties as m; m.show()
    elif page == "payments":
        import pages.payments as m; m.show()
    elif page == "stock_levels":
        import pages.stock_levels as m; m.show()
    elif page == "stock_counts":
        import pages.stock_counts as m; m.show()
    elif page == "stock_adjustments":
        import pages.stock_adjustments as m; m.show()
    elif page == "damaged_items":
        import pages.damaged_items as m; m.show()
    elif page == "writeoff_requests":
        import pages.writeoff_requests as m; m.show()
    elif page == "reports":
        import pages.reports as m; m.show()