import streamlit as st
import database as db
from datetime import datetime, date

st.set_page_config(
    page_title="Techtoon Accounting",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

def login_page():
    st.markdown("""
    <style>
    .main > div {padding-top: 2rem;}
    .stButton > button {width: 100%; border-radius: 8px; border: none; padding: 12px;}
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

def dashboard():
    st.title("📊 لوحة التحكم")
    
    try:
        cols, rows = db.execute_query(
            "SELECT COALESCE(SUM(total),0), COUNT(*) FROM invoices WHERE type=%s AND DATE(date)=CURRENT_DATE",
            ("sales",), fetch=True
        )
        today_sales = float(rows[0][0]) if rows else 0
        today_count = rows[0][1] if rows else 0
        
        cols2, rows2 = db.execute_query(
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type=%s AND DATE(date)=CURRENT_DATE",
            ("receipt",), fetch=True
        )
        collections = float(rows2[0][0]) if rows2 else 0
        
        cols3, rows3 = db.execute_query(
            "SELECT COALESCE(SUM(total-paid_amount),0) FROM invoices WHERE type=%s AND paid_amount<total AND status<>%s",
            ("sales", "cancelled"), fetch=True
        )
        receivables = float(rows3[0][0]) if rows3 else 0
        
        cols4, rows4 = db.execute_query(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE DATE(date)=CURRENT_DATE",
            (), fetch=True
        )
        expenses = float(rows4[0][0]) if rows4 else 0
        
        cols5, rows5 = db.execute_query(
            "SELECT COALESCE(SUM(opening_quantity * COALESCE(avg_cost_price, cost_price, 0)),0) FROM items WHERE is_kit IS NOT TRUE",
            (), fetch=True
        )
        stock_value = float(rows5[0][0]) if rows5 else 0
        
        cols6, rows6 = db.execute_query(
            "SELECT COUNT(*) FROM items WHERE is_active=TRUE AND is_kit IS NOT TRUE AND min_stock IS NOT NULL AND min_stock > 0 AND (opening_quantity + COALESCE((SELECT SUM(CASE WHEN type IN ('in','opening') THEN quantity WHEN type='out' THEN -quantity WHEN type='adjustment' THEN quantity ELSE 0 END) FROM inventory_movements WHERE item_id=items.id),0)) <= min_stock",
            (), fetch=True
        )
        low_stock_count = rows6[0][0] if rows6 else 0
        
        cols7, rows7 = db.execute_query(
            "SELECT COUNT(*) FROM invoices WHERE type=%s AND status<>%s AND due_date IS NOT NULL AND due_date < CURRENT_DATE AND paid_amount < total",
            ("sales", "cancelled"), fetch=True
        )
        overdue_count = rows7[0][0] if rows7 else 0
        
    except Exception as e:
        st.error(f"خطأ في تحميل البيانات: {e}")
        today_sales = today_count = collections = receivables = expenses = stock_value = low_stock_count = overdue_count = 0
    
    if low_stock_count > 0:
        st.warning(f"⚠️ تنبيه: {low_stock_count} صنف بالحد الأدنى للمخزون")
    if overdue_count > 0:
        st.error(f"🔔 تنبيه: {overdue_count} فاتورة متأخرة السداد")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 مبيعات اليوم", f"{today_sales:,.2f}", f"{today_count} فاتورة")
        st.metric("💵 التحصيلات", f"{collections:,.2f}", "اليوم")
    
    with col2:
        st.metric("💳 ديون العملاء", f"{receivables:,.2f}", "مستحقة")
        st.metric("💸 مصروفات اليوم", f"{expenses:,.2f}", "مصروف")
    
    with col3:
        st.metric("📦 قيمة المخزون", f"{stock_value:,.2f}", "تكلفة")
        st.metric("⚠️ مخزون منخفض", f"{low_stock_count} صنف")
    
    with col4:
        st.metric("🔔 فواتير متأخرة", f"{overdue_count}", "فاتورة")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
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
                import pandas as pd
                df = pd.DataFrame(rows, columns=["الصنف", "الكمية", "الإجمالي"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد مبيعات في آخر 30 يوم")
        except:
            st.info("لا توجد بيانات")
    
    with col2:
        st.markdown("### 📋 آخر الفواتير")
        try:
            cols, rows = db.execute_query(
                "SELECT i.invoice_number, i.date, i.type, COALESCE(p.name,''), i.total, i.status "
                "FROM invoices i LEFT JOIN parties p ON i.party_id=p.id "
                "ORDER BY i.date DESC LIMIT 5",
                (), fetch=True
            )
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=["رقم", "التاريخ", "النوع", "العميل", "الإجمالي", "الحالة"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد فواتير")
        except:
            st.info("لا توجد بيانات")

if st.session_state.user is None:
    login_page()
else:
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.user['full_name']}")
        st.caption(f"الدور: {st.session_state.user['role']}")
        st.markdown("---")
        
        if st.button("📊 لوحة التحكم", use_container_width=True, key="nav_dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
            
        with st.expander("📄 المبيعات والعملاء", expanded=False):
            if st.button("🛒 الفواتير", use_container_width=True, key="nav_invoices"):
                st.session_state.current_page = "invoices"
                st.rerun()
            if st.button("👥 العملاء والموردين", use_container_width=True, key="nav_parties"):
                st.session_state.current_page = "parties"
                st.rerun()
            if st.button("💰 المدفوعات", use_container_width=True, key="nav_payments"):
                st.session_state.current_page = "payments"
                st.rerun()
                
        with st.expander("📦 المخزون والجرد", expanded=True):
            if st.button("📦 الأصناف", use_container_width=True, key="nav_items"):
                st.session_state.current_page = "items"
                st.rerun()
            if st.button("📦 أرصدة المخزون", use_container_width=True, key="nav_stock_levels"):
                st.session_state.current_page = "stock_levels"
                st.rerun()
            if st.button("📋 جلسات الجرد", use_container_width=True, key="nav_stock_counts"):
                st.session_state.current_page = "stock_counts"
                st.rerun()
            if st.button("⚖️ تسويات المخزون", use_container_width=True, key="nav_stock_adjustments"):
                st.session_state.current_page = "stock_adjustments"
                st.rerun()
            if st.button("💣 الأصناف التالفة", use_container_width=True, key="nav_damaged_items"):
                st.session_state.current_page = "damaged_items"
                st.rerun()
            if st.button("🗑️ طلبات الشطب", use_container_width=True, key="nav_writeoff_requests"):
                st.session_state.current_page = "writeoff_requests"
                st.rerun()
                
        with st.expander("💹 المالية والتقارير", expanded=False):
            if st.button("📈 التقارير", use_container_width=True, key="nav_reports"):
                st.session_state.current_page = "reports"
                st.rerun()
        
        st.markdown("---")
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    
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
    elif page == "stock_levels":
        import pages.stock_levels as sl
        sl.show()
    elif page == "stock_counts":
        import pages.stock_counts as sc
        sc.show()
    elif page == "stock_adjustments":
        import pages.stock_adjustments as sa
        sa.show()
    elif page == "damaged_items":
        import pages.damaged_items as di
        di.show()
    elif page == "writeoff_requests":
        import pages.writeoff_requests as wr
        wr.show()
    elif page == "reports":
        import pages.reports as rep
        rep.show()