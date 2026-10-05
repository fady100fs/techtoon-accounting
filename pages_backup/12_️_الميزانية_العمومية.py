# pages/12_⚖️_الميزانية_العمومية.py
import streamlit as st
import pandas as pd
from sqlalchemy import func
from database import SessionLocal
import models
from auth_required import require_login
current_user = require_login()
st.set_page_config(page_title="الميزانية العمومية", page_icon="⚖️", layout="wide")
st.title("⚖️ الميزانية العمومية (Balance Sheet)")

db = SessionLocal()

try:
    st.markdown("""
    ### 📊 المعادلة المحاسبية الأساسية:
    **الأصول = الخصوم + حقوق الملكية**
    """)
    
    st.markdown("---")
    
    # حساب الأصول
    st.subheader("📈 الأصول (Assets)")
    
    assets_accounts = db.query(models.Account).filter(
        models.Account.type == 'ASSET'
    ).all()
    
    assets_data = []
    total_assets = 0.0
    
    for acc in assets_accounts:
        if acc.parent_id is None:
            continue
        
        debit_total = db.query(func.sum(models.JournalLine.debit)).filter(
            models.JournalLine.account_id == acc.id
        ).scalar() or 0.0
        
        credit_total = db.query(func.sum(models.JournalLine.credit)).filter(
            models.JournalLine.account_id == acc.id
        ).scalar() or 0.0
        
        balance = debit_total - credit_total
        total_assets += balance
        
        assets_data.append({
            "الحساب": f"{acc.code} - {acc.name}",
            "مدين": debit_total,
            "دائن": credit_total,
            "الرصيد": balance
        })
    
    if assets_data:
        assets_df = pd.DataFrame(assets_data)
        st.dataframe(assets_df, use_container_width=True)
    
    st.metric("إجمالي الأصول", f"{total_assets:,.2f} ج.م")
    
    st.markdown("---")
    
    # حساب الخصوم
    st.subheader("📉 الخصوم (Liabilities)")
    
    liabilities_accounts = db.query(models.Account).filter(
        models.Account.type == 'LIABILITY'
    ).all()
    
    liabilities_data = []
    total_liabilities = 0.0
    
    for acc in liabilities_accounts:
        if acc.parent_id is None:
            continue
        
        debit_total = db.query(func.sum(models.JournalLine.debit)).filter(
            models.JournalLine.account_id == acc.id
        ).scalar() or 0.0
        
        credit_total = db.query(func.sum(models.JournalLine.credit)).filter(
            models.JournalLine.account_id == acc.id
        ).scalar() or 0.0
        
        balance = credit_total - debit_total
        total_liabilities += balance
        
        liabilities_data.append({
            "الحساب": f"{acc.code} - {acc.name}",
            "مدين": debit_total,
            "دائن": credit_total,
            "الرصيد": balance
        })
    
    if liabilities_data:
        liabilities_df = pd.DataFrame(liabilities_data)
        st.dataframe(liabilities_df, use_container_width=True)
    
    st.metric("إجمالي الخصوم", f"{total_liabilities:,.2f} ج.م")
    
    st.markdown("---")
    
    # حساب حقوق الملكية
    st.subheader("👑 حقوق الملكية (Equity)")
    
    equity_accounts = db.query(models.Account).filter(
        models.Account.type == 'EQUITY'
    ).all()
    
    equity_data = []
    total_equity = 0.0
    
    for acc in equity_accounts:
        if acc.parent_id is None:
            continue
        
        debit_total = db.query(func.sum(models.JournalLine.debit)).filter(
            models.JournalLine.account_id == acc.id
        ).scalar() or 0.0
        
        credit_total = db.query(func.sum(models.JournalLine.credit)).filter(
            models.JournalLine.account_id == acc.id
        ).scalar() or 0.0
        
        balance = credit_total - debit_total
        total_equity += balance
        
        equity_data.append({
            "الحساب": f"{acc.code} - {acc.name}",
            "مدين": debit_total,
            "دائن": credit_total,
            "الرصيد": balance
        })
    
    # إضافة صافي الربح/الخسارة
    revenues = db.query(func.sum(models.JournalLine.credit)).join(
        models.Account
    ).filter(
        models.Account.type == 'REVENUE',
        models.JournalLine.credit > 0
    ).scalar() or 0.0
    
    expenses = db.query(func.sum(models.JournalLine.debit)).join(
        models.Account
    ).filter(
        models.Account.type == 'EXPENSE',
        models.JournalLine.debit > 0
    ).scalar() or 0.0
    
    net_profit = revenues - expenses
    
    equity_data.append({
        "الحساب": "صافي الربح/الخسارة",
        "مدين": 0.0,
        "دائن": net_profit if net_profit > 0 else 0.0,
        "الرصيد": net_profit
    })
    
    total_equity += net_profit
    
    if equity_data:
        equity_df = pd.DataFrame(equity_data)
        st.dataframe(equity_df, use_container_width=True)
    
    st.metric("إجمالي حقوق الملكية", f"{total_equity:,.2f} ج.م")
    
    st.markdown("---")
    
    # التحقق من توازن الميزانية
    st.subheader("✅ التحقق من توازن الميزانية")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("إجمالي الأصول", f"{total_assets:,.2f} ج.م")
    
    with col2:
        st.metric("الخصوم + حقوق الملكية", f"{total_liabilities + total_equity:,.2f} ج.م")
    
    with col3:
        difference = total_assets - (total_liabilities + total_equity)
        st.metric("الفرق", f"{difference:,.2f} ج.م")
    
    if abs(difference) < 0.01:
        st.success("✅ الميزانية متوازنة!")
    else:
        st.error(f"❌ الميزانية غير متوازنة! الفرق: {difference:,.2f} ج.م")
    
    st.markdown("---")
    
    # زر تصدير Excel
    if st.button(" تصدير الميزانية العمومية إلى Excel", type="primary"):
        try:
            from export_excel import export_balance_sheet_to_excel
            excel_path = export_balance_sheet_to_excel(
                assets_data=assets_data,
                liabilities_data=liabilities_data,
                equity_data=equity_data,
                total_assets=total_assets,
                total_liabilities=total_liabilities,
                total_equity=total_equity,
                net_profit=net_profit
            )
            st.success(f"تم التصدير: {excel_path}")
            
            with open(excel_path, "rb") as file:
                st.download_button(
                    label="⬇️ تحميل Excel",
                    data=file,
                    file_name=excel_path,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"خطأ في التصدير: {e}")

finally:
    db.close()