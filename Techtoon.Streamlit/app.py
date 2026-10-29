<<<<<<< HEAD
import streamlit as st
import database as db
from datetime import datetime, date

=======
ï»¿import streamlit as st
import database as db
from datetime import datetime, date

# ===== Page Config =====
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
st.set_page_config(
    page_title="Techtoon Accounting",
    page_icon="ðŸ“Š",
    layout="wide",
    initial_sidebar_state="expanded"
)

<<<<<<< HEAD
=======
# ===== Session State =====
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
if "user" not in st.session_state:
    st.session_state.user = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "dashboard"

<<<<<<< HEAD
=======
# ===== Login =====
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
def login_page():
    st.markdown("""
    <style>
    .main > div {padding-top: 2rem;}
<<<<<<< HEAD
    .stButton > button {width: 100%; border-radius: 8px; border: none; padding: 12px;}
=======
    .stButton > button {width: 100%; border-radius: 8px;}
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("## ðŸ“Š Techtoon Accounting")
        st.markdown("### Ù†Ø¸Ø§Ù… Ø§Ù„Ù…Ø­Ø§Ø³Ø¨Ø© - ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„")
        st.markdown("---")
        
        username = st.text_input("Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…", placeholder="Ø£Ø¯Ø®Ù„ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…")
        password = st.text_input("ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±", type="password", placeholder="Ø£Ø¯Ø®Ù„ ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±")
        
        if st.button("ðŸ” ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø¯Ø®ÙˆÙ„", use_container_width=True):
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
                            st.error("âŒ ÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ± ØºÙŠØ± ØµØ­ÙŠØ­Ø©")
                    else:
                        st.error("âŒ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ Ø£Ùˆ Ù…Ø¹Ø·Ù„")
                except Exception as e:
                    st.error(f"âŒ Ø®Ø·Ø£: {e}")
            else:
                st.warning("âš ï¸ Ø£Ø¯Ø®Ù„ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… ÙˆÙƒÙ„Ù…Ø© Ø§Ù„Ù…Ø±ÙˆØ±")

<<<<<<< HEAD
=======
# ===== Dashboard =====
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
def dashboard():
    st.title("ðŸ“Š Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…")
    
    try:
<<<<<<< HEAD
=======
        # Ù…Ø¨ÙŠØ¹Ø§Øª Ø§Ù„ÙŠÙˆÙ…
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
        cols, rows = db.execute_query(
            "SELECT COALESCE(SUM(total),0), COUNT(*) FROM invoices WHERE type=%s AND DATE(date)=CURRENT_DATE",
            ("sales",), fetch=True
        )
        today_sales = float(rows[0][0]) if rows else 0
        today_count = rows[0][1] if rows else 0
        
<<<<<<< HEAD
=======
        # Ø§Ù„ØªØ­ØµÙŠÙ„Ø§Øª
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
        cols2, rows2 = db.execute_query(
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE payment_type=%s AND DATE(date)=CURRENT_DATE",
            ("receipt",), fetch=True
        )
        collections = float(rows2[0][0]) if rows2 else 0
        
<<<<<<< HEAD
=======
        # Ø§Ù„Ø¯ÙŠÙˆÙ† Ø§Ù„Ù…Ø³ØªØ­Ù‚Ø©
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
        cols3, rows3 = db.execute_query(
            "SELECT COALESCE(SUM(total-paid_amount),0) FROM invoices WHERE type=%s AND paid_amount<total AND status<>%s",
            ("sales", "cancelled"), fetch=True
        )
        receivables = float(rows3[0][0]) if rows3 else 0
        
<<<<<<< HEAD
=======
        # Ø§Ù„Ù…ØµØ±ÙˆÙØ§Øª
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
        cols4, rows4 = db.execute_query(
            "SELECT COALESCE(SUM(amount),0) FROM expenses WHERE DATE(date)=CURRENT_DATE",
            (), fetch=True
        )
        expenses = float(rows4[0][0]) if rows4 else 0
        
<<<<<<< HEAD
=======
        # Ù‚ÙŠÙ…Ø© Ø§Ù„Ù…Ø®Ø²ÙˆÙ†
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
        cols5, rows5 = db.execute_query(
            "SELECT COALESCE(SUM(opening_quantity * COALESCE(avg_cost_price, cost_price, 0)),0) FROM items WHERE is_kit IS NOT TRUE",
            (), fetch=True
        )
        stock_value = float(rows5[0][0]) if rows5 else 0
        
<<<<<<< HEAD
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
        st.error(f"Ø®Ø·Ø£ ÙÙŠ ØªØ­Ù…ÙŠÙ„ Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª: {e}")
        today_sales = today_count = collections = receivables = expenses = stock_value = low_stock_count = overdue_count = 0
    
    if low_stock_count > 0:
        st.warning(f"âš ï¸ ØªÙ†Ø¨ÙŠÙ‡: {low_stock_count} ØµÙ†Ù Ø¨Ø§Ù„Ø­Ø¯ Ø§Ù„Ø£Ø¯Ù†Ù‰ Ù„Ù„Ù…Ø®Ø²ÙˆÙ†")
    if overdue_count > 0:
        st.error(f"ðŸ”” ØªÙ†Ø¨ÙŠÙ‡: {overdue_count} ÙØ§ØªÙˆØ±Ø© Ù…ØªØ£Ø®Ø±Ø© Ø§Ù„Ø³Ø¯Ø§Ø¯")
    
    col1, col2, col3, col4 = st.columns(4)
=======
    except Exception as e:
        st.error(f"Ø®Ø·Ø£ ÙÙŠ ØªØ­Ù…ÙŠÙ„ Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª: {e}")
        today_sales = today_count = collections = receivables = expenses = stock_value = 0
    
    # Ø¨Ø·Ø§Ù‚Ø§Øª Ø§Ù„Ù…Ø¤Ø´Ø±Ø§Øª
    col1, col2, col3 = st.columns(3)
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
    
    with col1:
        st.metric("ðŸ’° Ù…Ø¨ÙŠØ¹Ø§Øª Ø§Ù„ÙŠÙˆÙ…", f"{today_sales:,.2f}", f"{today_count} ÙØ§ØªÙˆØ±Ø©")
        st.metric("ðŸ’µ Ø§Ù„ØªØ­ØµÙŠÙ„Ø§Øª", f"{collections:,.2f}", "Ø§Ù„ÙŠÙˆÙ…")
<<<<<<< HEAD
=======
        st.metric("ðŸ“¦ Ù‚ÙŠÙ…Ø© Ø§Ù„Ù…Ø®Ø²ÙˆÙ†", f"{stock_value:,.2f}", "ØªÙƒÙ„ÙØ©")
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
    
    with col2:
        st.metric("ðŸ’³ Ø¯ÙŠÙˆÙ† Ø§Ù„Ø¹Ù…Ù„Ø§Ø¡", f"{receivables:,.2f}", "Ù…Ø³ØªØ­Ù‚Ø©")
        st.metric("ðŸ’¸ Ù…ØµØ±ÙˆÙØ§Øª Ø§Ù„ÙŠÙˆÙ…", f"{expenses:,.2f}", "Ù…ØµØ±ÙˆÙ")
    
    with col3:
<<<<<<< HEAD
        st.metric("ðŸ“¦ Ù‚ÙŠÙ…Ø© Ø§Ù„Ù…Ø®Ø²ÙˆÙ†", f"{stock_value:,.2f}", "ØªÙƒÙ„ÙØ©")
        st.metric("âš ï¸ Ù…Ø®Ø²ÙˆÙ† Ù…Ù†Ø®ÙØ¶", f"{low_stock_count} ØµÙ†Ù")
    
    with col4:
        st.metric("ðŸ”” ÙÙˆØ§ØªÙŠØ± Ù…ØªØ£Ø®Ø±Ø©", f"{overdue_count}", "ÙØ§ØªÙˆØ±Ø©")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
=======
        # Ø£ÙØ¶Ù„ 5 Ø£ØµÙ†Ø§Ù
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
        st.markdown("### ðŸ† Ø£ÙØ¶Ù„ Ø§Ù„Ø£ØµÙ†Ø§Ù Ù…Ø¨ÙŠØ¹Ø§Ù‹")
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
<<<<<<< HEAD
                import pandas as pd
                df = pd.DataFrame(rows, columns=["Ø§Ù„ØµÙ†Ù", "Ø§Ù„ÙƒÙ…ÙŠØ©", "Ø§Ù„Ø¥Ø¬Ù…Ø§Ù„ÙŠ"])
                st.dataframe(df, use_container_width=True, hide_index=True)
=======
                for i, row in enumerate(rows):
                    st.write(f"{i+1}. **{row[0]}** - {float(row[1]):.0f} ÙˆØ­Ø¯Ø© - {float(row[2]):,.2f}")
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
            else:
                st.info("Ù„Ø§ ØªÙˆØ¬Ø¯ Ù…Ø¨ÙŠØ¹Ø§Øª ÙÙŠ Ø¢Ø®Ø± 30 ÙŠÙˆÙ…")
        except:
            st.info("Ù„Ø§ ØªÙˆØ¬Ø¯ Ø¨ÙŠØ§Ù†Ø§Øª")
    
<<<<<<< HEAD
    with col2:
        st.markdown("### ðŸ“‹ Ø¢Ø®Ø± Ø§Ù„ÙÙˆØ§ØªÙŠØ±")
        try:
            cols, rows = db.execute_query(
                "SELECT i.invoice_number, i.date, i.type, COALESCE(p.name,''), i.total, i.status "
                "FROM invoices i LEFT JOIN parties p ON i.party_id=p.id "
                "ORDER BY i.date DESC LIMIT 5",
                (), fetch=True
            )
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=["Ø±Ù‚Ù…", "Ø§Ù„ØªØ§Ø±ÙŠØ®", "Ø§Ù„Ù†ÙˆØ¹", "Ø§Ù„Ø¹Ù…ÙŠÙ„", "Ø§Ù„Ø¥Ø¬Ù…Ø§Ù„ÙŠ", "Ø§Ù„Ø­Ø§Ù„Ø©"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Ù„Ø§ ØªÙˆØ¬Ø¯ ÙÙˆØ§ØªÙŠØ±")
        except:
            st.info("Ù„Ø§ ØªÙˆØ¬Ø¯ Ø¨ÙŠØ§Ù†Ø§Øª")

if st.session_state.user is None:
    login_page()
else:
=======
    st.markdown("---")
    
    # Ø¢Ø®Ø± Ø§Ù„ÙÙˆØ§ØªÙŠØ±
    st.markdown("### ðŸ“‹ Ø¢Ø®Ø± Ø§Ù„ÙÙˆØ§ØªÙŠØ±")
    try:
        cols, rows = db.execute_query(
            "SELECT i.invoice_number, i.date, i.type, COALESCE(p.name,''), i.total, i.status "
            "FROM invoices i LEFT JOIN parties p ON i.party_id=p.id "
            "ORDER BY i.date DESC LIMIT 10",
            (), fetch=True
        )
        if rows:
            import pandas as pd
            df = pd.DataFrame(rows, columns=["Ø±Ù‚Ù… Ø§Ù„ÙØ§ØªÙˆØ±Ø©", "Ø§Ù„ØªØ§Ø±ÙŠØ®", "Ø§Ù„Ù†ÙˆØ¹", "Ø§Ù„Ø¹Ù…ÙŠÙ„", "Ø§Ù„Ø¥Ø¬Ù…Ø§Ù„ÙŠ", "Ø§Ù„Ø­Ø§Ù„Ø©"])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Ù„Ø§ ØªÙˆØ¬Ø¯ ÙÙˆØ§ØªÙŠØ±")
    except Exception as e:
        st.error(f"Ø®Ø·Ø£: {e}")

# ===== Main =====
if st.session_state.user is None:
    login_page()
else:
    # Sidebar
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
    with st.sidebar:
        st.markdown(f"### ðŸ‘¤ {st.session_state.user['full_name']}")
        st.caption(f"Ø§Ù„Ø¯ÙˆØ±: {st.session_state.user['role']}")
        st.markdown("---")
        
<<<<<<< HEAD
        # Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ… (Ù…Ù†ÙØµÙ„Ø©)
        if st.button("ðŸ“Š Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…", use_container_width=True, key="nav_dashboard"):
            st.session_state.current_page = "dashboard"
            st.rerun()
            
        # Ù‚Ø§Ø¦Ù…Ø© Ù…Ù†Ø³Ø¯Ù„Ø©: Ø§Ù„Ù…Ø¨ÙŠØ¹Ø§Øª ÙˆØ§Ù„Ø¹Ù…Ù„Ø§Ø¡
        with st.expander("ðŸ“„ Ø§Ù„Ù…Ø¨ÙŠØ¹Ø§Øª ÙˆØ§Ù„Ø¹Ù…Ù„Ø§Ø¡", expanded=False):
            if st.button("ðŸ›’ Ø§Ù„ÙÙˆØ§ØªÙŠØ±", use_container_width=True, key="nav_invoices"):
                st.session_state.current_page = "invoices"
                st.rerun()
            if st.button("ðŸ‘¥ Ø§Ù„Ø¹Ù…Ù„Ø§Ø¡ ÙˆØ§Ù„Ù…ÙˆØ±Ø¯ÙŠÙ†", use_container_width=True, key="nav_parties"):
                st.session_state.current_page = "parties"
                st.rerun()
            if st.button("ðŸ’° Ø§Ù„Ù…Ø¯ÙÙˆØ¹Ø§Øª", use_container_width=True, key="nav_payments"):
                st.session_state.current_page = "payments"
                st.rerun()
                
        # Ù‚Ø§Ø¦Ù…Ø© Ù…Ù†Ø³Ø¯Ù„Ø©: Ø§Ù„Ù…Ø®Ø²ÙˆÙ† ÙˆØ§Ù„Ø¬Ø±Ø¯
        with st.expander("ðŸ“¦ Ø§Ù„Ù…Ø®Ø²ÙˆÙ† ÙˆØ§Ù„Ø¬Ø±Ø¯", expanded=True):
            if st.button("ðŸ“¦ Ø§Ù„Ø£ØµÙ†Ø§Ù", use_container_width=True, key="nav_items"):
                st.session_state.current_page = "items"
                st.rerun()
            if st.button("ðŸ“¦ Ø£Ø±ØµØ¯Ø© Ø§Ù„Ù…Ø®Ø²ÙˆÙ†", use_container_width=True, key="nav_stock_levels"):
                st.session_state.current_page = "stock_levels"
                st.rerun()
            if st.button("ðŸ“‹ Ø¬Ù„Ø³Ø§Øª Ø§Ù„Ø¬Ø±Ø¯", use_container_width=True, key="nav_stock_counts"):
                st.session_state.current_page = "stock_counts"
                st.rerun()
            if st.button("âš–ï¸ ØªØ³ÙˆÙŠØ§Øª Ø§Ù„Ù…Ø®Ø²ÙˆÙ†", use_container_width=True, key="nav_stock_adjustments"):
                st.session_state.current_page = "stock_adjustments"
                st.rerun()
            if st.button("ðŸ’£ Ø§Ù„Ø£ØµÙ†Ø§Ù Ø§Ù„ØªØ§Ù„ÙØ©", use_container_width=True, key="nav_damaged_items"):
                st.session_state.current_page = "damaged_items"
                st.rerun()
            if st.button("ðŸ—‘ï¸ Ø·Ù„Ø¨Ø§Øª Ø§Ù„Ø´Ø·Ø¨", use_container_width=True, key="nav_writeoff_requests"):
                st.session_state.current_page = "writeoff_requests"
                st.rerun()
                
        # Ù‚Ø§Ø¦Ù…Ø© Ù…Ù†Ø³Ø¯Ù„Ø©: Ø§Ù„Ù…Ø§Ù„ÙŠØ© ÙˆØ§Ù„ØªÙ‚Ø§Ø±ÙŠØ±
        with st.expander("ðŸ’¹ Ø§Ù„Ù…Ø§Ù„ÙŠØ© ÙˆØ§Ù„ØªÙ‚Ø§Ø±ÙŠØ±", expanded=False):
            if st.button("ðŸ“ˆ Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ±", use_container_width=True, key="nav_reports"):
                st.session_state.current_page = "reports"
                st.rerun()
=======
        if st.button("ðŸ“Š Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()
        if st.button("ðŸ›’ Ø§Ù„ÙÙˆØ§ØªÙŠØ±", use_container_width=True):
            st.session_state.current_page = "invoices"
            st.rerun()
        if st.button("ðŸ“¦ Ø§Ù„Ø£ØµÙ†Ø§Ù", use_container_width=True):
            st.session_state.current_page = "items"
            st.rerun()
        if st.button("ðŸ‘¥ Ø§Ù„Ø¹Ù…Ù„Ø§Ø¡ ÙˆØ§Ù„Ù…ÙˆØ±Ø¯ÙŠÙ†", use_container_width=True):
            st.session_state.current_page = "parties"
            st.rerun()
        if st.button("ðŸ’° Ø§Ù„Ù…Ø¯ÙÙˆØ¹Ø§Øª", use_container_width=True):
            st.session_state.current_page = "payments"
            st.rerun()
        if st.button("ðŸ“ˆ Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ±", use_container_width=True):
            st.session_state.current_page = "reports"
            st.rerun()
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
        
        st.markdown("---")
        if st.button("ðŸšª ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø®Ø±ÙˆØ¬", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    
<<<<<<< HEAD
=======
    # Page routing
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
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
<<<<<<< HEAD
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
=======
    elif page == "reports":
        import pages.reports as rep
        rep.show()
>>>>>>> 8325fba6af09ee66ab808da0e5526f6efad8e4c5
 