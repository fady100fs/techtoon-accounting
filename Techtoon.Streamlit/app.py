import streamlit as st
import database as db
from datetime import datetime, date

# ===== Page Config =====
st.set_page_config(
    page_title="Techtoon Accounting",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== Session State =====
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

# ===== Login =====
def login_page():
    st.markdown("""
    <style>
    .main > div {padding-top: 2rem;}
    .stButton > button {width: 100%; border-radius: 8px;}
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("## 📊 Techtoon Accounting")
        st.markdown("### نظام المحاسبة - تسجيل الدخول")
        st.markdown("---")
        
        username = st.text_input("اسم المستخدم", placeholder="أدخل اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password", placeholder="أدخل كلمة المرور")
        
        if st.button("🔐 تسجيل الدخول", use_container_width=True):
            if username and password:
                try:
                    cols, rows = db.execute_query(
                        "SELECT id, username, full_name, role, is_active, password_hash FROM users WHERE username=%s AND is_active=TRUE",
                        (username,), fetch=True
                    )
                    if rows:
                        user_data = rows[0]
                        if db.verify_password(password, user_data[5]):
                            st.session_state.user = {
                                "id": user_data[0],
                                "username": user_data[1],
                                "full_name": user_data[2],
                                "role": user_data[3]
                            }
                            st.rerun()
                        else:
                            st.error("❌ كلمة المرور غير صحيحة")
                    else:
                        st.error("❌ المستخدم غير موجود أو معطل")
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
            else:
                st.warning("⚠️ أدخل اسم المستخدم وكلمة المرور")

# ===== Dashboard =====
def dashboard():
    st.title("📊 لوحة التحكم")
    
    try:
        # مبيعات اليوم
        cols, rows = db.execute_query(
            "SELECT COALESCE(SUM(total),0), COUNT(*) FROM invoices WHERE type=%s AND DATE(date)=CURRENT_DATE",
            ("sales",), fetch=True
        )
        today_sales = float(rows[0][0]) if rows else 0
        today_count = rows[0][1] if rows else 0
        
        # التحصيلات
        cols2, rows2 = db.execute_query(
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type=%s AND DATE(date)=CURRENT_DATE",
            ("receipt",), fetch=True
        )
        collections = float(rows2[0][0]) if rows2 else 0
        
        # الديون المستحقة
        cols3, rows3 = db.execute_query(
            "SELECT COALESCE(SUM(total-paid_amount),0) FROM invoices WHERE type=%s AND paid_amount<total AND status<>%s",
            ("sales", "cancelled"), fetch=True
        )
        receivables = float(rows3[0][0]) if rows3 else 0
        
        # المصروفات
        cols4, rows4 = db.execute_query(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE DATE(date)=CURRENT_DATE",
            (), fetch=True
        )
        expenses = float(rows4[0][0]) if rows4 else 0
        
        # قيمة المخزون
        cols5, rows5 = db.execute_query(
            "SELECT COALESCE(SUM(opening_quantity * COALESCE(avg_cost_price, cost_price, 0)),0) FROM items WHERE is_kit IS NOT TRUE",
            (), fetch=True
        )
        stock_value = float(rows5[0][0]) if rows5 else 0
        
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
        today_sales = today_count = collections = receivables = expenses = stock_value = 0
    
    # بطاقات المؤشرات
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 مبيعات اليوم", f"{today_sales:,.2f}", f"{today_count} فاتورة")
        st.metric("💵 التحصيلات", f"{collections:,.2f}", "اليوم")
        st.metric("📦 قيمة المخزون", f"{stock_value:,.2f}", "تكلفة")
    
    with col2:
        st.metric("💳 ديون العملاء", f"{receivables:,.2f}", "مستحقة")
        st.metric("💸 مصروفات اليوم", f"{expenses:,.2f}", "مصروف")
    
    with col3:
        # أفضل 5 أصناف
        st.markdown("### 🏆 أفضل الأصناف مبيعاً")
        try:
            cols, rows = db.execute_query(
                "SELECT i.name, SUM(il.quantity) as qty, SUM(il.total) as total "
                "FROM invoice_lines il "
                "JOIN invoices inv ON il.invoice_id=inv.id "
                "JOIN items i ON il.item_id=i.id "
                "WHERE inv.type=%s AND inv.date >= CURRENT_DATE - INTERVAL '30 days' "
                "GROUP BY i.name ORDER BY total DESC LIMIT 5",
                ("sales",), fetch=True
            )
            if rows:
                for i, row in enumerate(rows):
                    st.write(f"{i+1}. **{row[0]}** - {float(row[1]):.0f} وحدة - {float(row[2]):,.2f}")
            else:
                st.info("لا توجد مبيعات في آخر 30 يوم")
        except:
            st.info("لا توجد بيانات")
    
    st.markdown("---")
    
    # آخر الفواتير
    st.markdown("### 📋 آخر الفواتير")
    try:
        cols, rows = db.execute_query(
            "SELECT i.invoice_number, i.date, i.type, COALESCE(p.name,''), i.total, i.status "
            "FROM invoices i LEFT JOIN parties p ON i.party_id=p.id "
            "ORDER BY i.date DESC LIMIT 10",
            (), fetch=True
        )
        if rows:
            import pandas as pd
            df = pd.DataFrame(rows, columns=["رقم الفاتورة", "التاريخ", "النوع", "العميل", "الإجمالي", "الحالة"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("لا توجد فواتير")
    except Exception as e:
        st.error(f"خطأ: {e}")

# ===== Main =====
if st.session_state.user is None:
    login_page()
else:
    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['full_name']}")
        st.caption(f"الدور: {st.session_state.user['role']}")
        st.markdown("---")
        
        if st.button("📊 لوحة التحكم", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()
        if st.button("🛒 الفواتير", use_container_width=True):
            st.session_state.current_page = "invoices"
            st.rerun()
        if st.button("📦 الأصناف", use_container_width=True):
            st.session_state.current_page = "items"
            st.rerun()
        if st.button("👥 العملاء والموردين", use_container_width=True):
            st.session_state.current_page = "parties"
            st.rerun()
        if st.button("💰 المدفوعات", use_container_width=True):
            st.session_state.current_page = "payments"
            st.rerun()
        if st.button("📈 التقارير", use_container_width=True):
            st.session_state.current_page = "reports"
            st.rerun()
        
        st.markdown("---")
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    
    # Page routing
    page = st.session_state.current_page
    
    if page == "dashboard":
        dashboard()
    elif page == "invoices":
        import pages.invoices as inv
        inv.show()
    elif page == "items":
        import pages.items as itm
        itm.show()
    elif page == "parties":
        import pages.parties as prt
        prt.show()
    elif page == "payments":
        import pages.payments as pmt
        pmt.show()
    elif page == "reports":
        import pages.reports as rep
        rep.show()
