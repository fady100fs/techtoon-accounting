# pages/16_🔔_مركز_التذكيرات.py
import streamlit as st
import pandas as pd
from reminders import get_overdue_invoices_reminders, export_reminders_to_excel
from auth_required import require_login
from datetime import datetime

# التحقق من تسجيل الدخول
current_user = require_login()

st.set_page_config(page_title="مركز التذكيرات", page_icon="🔔", layout="wide")
st.title("🔔 مركز التذكيرات والمتابعات الذكية")

st.info(f"👤 مرحباً **{current_user['full_name']}** | استخدم هذه الأدوات لمتابعة المستحقات والمخزون.")

tab1, tab2 = st.tabs(["💰 تذكير العملاء بالمستحقات", "📦 تذكيرات المخزون"])

with tab1:
    st.subheader("📩 تذكير العملاء بالفواتير المتأخرة")
    st.markdown("""
    يقوم النظام تلقائياً بالبحث عن الفواتير التي تجاوزت تاريخ الاستحقاق ولم يتم سدادها.
    يمكنك نسخ رسالة واتساب جاهزة أو تصدير القائمة كاملة.
    """)
    
    if st.button("🔄 تحديث قائمة المتأخرين", type="primary"):
        with st.spinner("جاري البحث في الفواتير..."):
            reminders = get_overdue_invoices_reminders()
            st.session_state.reminders = reminders
    
    if 'reminders' in st.session_state and st.session_state.reminders:
        reminders = st.session_state.reminders
        
        st.warning(f"⚠️ تم العثور على **{len(reminders)}** فاتورة متأخرة!")
        
        # عرض الجدول
        df = pd.DataFrame(reminders)
        display_df = df[['رقم الفاتورة', 'العميل', 'المبلغ', 'أيام التأخير']].copy()
        display_df['المبلغ'] = display_df['المبلغ'].apply(lambda x: f"{x:,.2f} ج.م")
        
        st.dataframe(display_df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📤 خيارات التصرف")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**1. تصدير القائمة إلى Excel:**")
            if st.button("📥 تحميل ملف Excel"):
                filename = f"Overdue_Reminders_{datetime.now().strftime('%Y%m%d')}.xlsx"
                export_reminders_to_excel(reminders, filename)
                with open(filename, "rb") as file:
                    st.download_button(
                        label="⬇️ تحميل الملف",
                        data=file,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        
        with col2:
            st.markdown("**2. إرسال تذكير عبر واتساب:**")
            selected_inv = st.selectbox("اختر فاتورة لإرسال تذكير:", df['رقم الفاتورة'].tolist())
            
            if selected_inv:
                row = df[df['رقم الفاتورة'] == selected_inv].iloc[0]
                st.write(f"**الرسالة الجاهزة لـ {row['العميل']}:**")
                st.code(row['رابط واتساب'].split('?text=')[1].replace('%0A', '\n'), language=None)
                
                st.markdown(f"[📱 اضغط هنا لفتح واتساب وإرسال الرسالة مباشرة]({row['رابط واتساب']})", unsafe_allow_html=True)
                
    else:
        st.success("✅ ممتاز! لا توجد فواتير متأخرة السداد حالياً.")

with tab2:
    st.subheader("📦 تذكيرات إعادة تخزين الأصناف")
    st.info("هذه الأصناف وصلت للحد الأدنى أو أقل، يُرجى طلب شراء جديد.")
    
    # إعادة استخدام منطق التنبيهات من ملف alerts.py إذا كان موجوداً، أو كتابته هنا ببساطة
    from alerts import get_low_stock_items
    low_stock = get_low_stock_items()
    
    if low_stock:
        data = []
        for item_info in low_stock:
            item = item_info['item']
            data.append({
                "الصنف": item.name,
                "الرصيد الحالي": item_info['current_stock'],
                "الحد الأدنى": item_info['min_stock'],
                "النقص المطلوب طلبه": item_info['shortage']
            })
        
        df_stock = pd.DataFrame(data)
        st.dataframe(df_stock, use_container_width=True)
        
        if st.button("📥 تصدير قائمة النواقص إلى Excel"):
            filename = f"Low_Stock_Reminders_{datetime.now().strftime('%Y%m%d')}.xlsx"
            df_stock.to_excel(filename, index=False, engine='xlsxwriter')
            with open(filename, "rb") as file:
                st.download_button(
                    label="⬇️ تحميل قائمة النواقص",
                    data=file,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.success("✅ جميع الأصناف في مستويات مخزون آمنة.")