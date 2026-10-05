# pages/11_💾_النسخ_الاحتياطي.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from backup_manager import backup_manager
from audit_log import get_audit_logs, get_audit_summary, log_action
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="النسخ الاحتياطي والأمان", page_icon="💾", layout="wide")
st.title("💾 النسخ الاحتياطي والأمان")

st.info(f" المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

tab1, tab2, tab3, tab4 = st.tabs([
    "💾 النسخ الاحتياطي",
    "🔄 الاستعادة",
    "📊 سجل العمليات",
    "⚙️ الإعدادات"
])

# ==========================================
# التبويب 1: النسخ الاحتياطي
# ==========================================
with tab1:
    st.subheader("💾 النسخ الاحتياطي")
    
    # حالة النسخ الاحتياطي
    status = backup_manager.get_backup_status()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("النسخ المحلية", status['local_backups_count'])
    with col2:
        st.metric("النسخ الخارجية", status['external_backups_count'])
    with col3:
        st.metric("آخر نسخة", 
                  status['last_backup'].strftime("%Y-%m-%d %H:%M") if status['last_backup'] else "لم تُنشأ")
    with col4:
        st.metric("الحجم الكلي", f"{status['total_size'] / 1024 / 1024:.2f} MB")
    
    st.markdown("---")
    
    # أزرار النسخ
    st.markdown("### 📝 إنشاء نسخة احتياطية")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 إنشاء نسخة احتياطية الآن", type="primary", use_container_width=True):
            success, message = backup_manager.create_backup("يدوي")
            if success:
                st.success(f"✅ {message}")
                log_action(
                    user_name=current_user_name,
                    user_id=current_user_id,
                    action_type="backup",
                    description="إنشاء نسخة احتياطية يدوية"
                )
                st.rerun()
            else:
                st.error(f"❌ {message}")
    
    with col2:
        if st.button(" تحديث القائمة", use_container_width=True):
            st.rerun()
    
    st.markdown("---")
    
    # قائمة النسخ الاحتياطية
    st.markdown("### 📋 النسخ الاحتياطية المتاحة")
    
    backups = backup_manager.get_backup_list()
    
    if backups:
        data = []
        for backup in backups:
            data.append({
                "الاسم": backup['name'],
                "التاريخ": backup['date'].strftime("%Y-%m-%d %H:%M:%S"),
                "الحجم": f"{backup['size'] / 1024:.2f} KB",
                "الموقع": backup['location']
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد نسخ احتياطية.")
    
    st.markdown("---")
    
    # معلومات المجلدات
    st.markdown("### 📁 مواقع التخزين")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**المجلد المحلي:**\n{backup_manager.backup_folder}")
    with col2:
        st.success(f"**المجلد الخارجي الآمن:**\n{backup_manager.external_backup_folder}")

# ==========================================
# التبويب 2: الاستعادة
# ==========================================
with tab2:
    st.subheader("🔄 استعادة نسخة احتياطية")
    
    st.warning("""
    ⚠️ **تنبيه مهم:**
    - الاستعادة ستستبدل قاعدة البيانات الحالية
    - سيتم إنشاء نسخة احتياطية تلقائية قبل الاستعادة
    - تأكد من اختيار النسخة الصحيحة
    """)
    
    backups = backup_manager.get_backup_list()
    
    if not backups:
        st.info("لا توجد نسخ احتياطية متاحة للاستعادة.")
    else:
        # اختيار النسخة
        backup_options = {
            f"{b['name']} ({b['date'].strftime('%Y-%m-%d %H:%M')} - {b['location']})": b['path']
            for b in backups
        }
        
        selected_backup = st.selectbox(
            "اختر نسخة احتياطية للاستعادة:",
            options=list(backup_options.keys())
        )
        
        if selected_backup:
            st.markdown("### 📄 تفاصيل النسخة المحددة")
            
            backup_path = backup_options[selected_backup]
            backup_info = next(b for b in backups if b['path'] == backup_path)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("الاسم", backup_info['name'])
            with col2:
                st.metric("التاريخ", backup_info['date'].strftime("%Y-%m-%d %H:%M"))
            with col3:
                st.metric("الحجم", f"{backup_info['size'] / 1024:.2f} KB")
            
            st.markdown("---")
            
            # تأكيد الاستعادة
            st.markdown("### ⚠️ تأكيد الاستعادة")
            
            confirm_1 = st.checkbox("أفهم أن الاستعادة ستستبدل قاعدة البيانات الحالية")
            confirm_2 = st.checkbox("أؤكد أنني اخترت النسخة الصحيحة")
            confirm_3 = st.checkbox("أوافق على إنشاء نسخة احتياطية تلقائية قبل الاستعادة")
            
            if st.button(" استعادة النسخة", type="primary", disabled=not (confirm_1 and confirm_2 and confirm_3)):
                success, message = backup_manager.restore_backup(backup_path)
                
                if success:
                    st.success(f"✅ {message}")
                    log_action(
                        user_name=current_user_name,
                        user_id=current_user_id,
                        action_type="restore",
                        description=f"استعادة نسخة: {backup_info['name']}"
                    )
                    st.info("🔄 يرجى إعادة تشغيل البرنامج")
                else:
                    st.error(f"❌ {message}")

# ==========================================
# التبويب 3: سجل العمليات
# ==========================================
with tab3:
    st.subheader("📊 سجل العمليات")
    
    # فلاتر
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_days = st.number_input("عرض آخر (أيام):", min_value=1, max_value=365, value=30)
    with col2:
        filter_user = st.text_input("تصفية حسب المستخدم:")
    with col3:
        filter_action = st.selectbox(
            "تصفية حسب النوع:",
            options=["الكل", "backup", "restore", "create", "update", "delete", "login"]
        )
    
    # ملخص
    st.markdown("### 📈 ملخص العمليات")
    
    summary = get_audit_summary(days=filter_days)
    
    if summary['by_action']:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**حسب نوع العملية:**")
            for item in summary['by_action']:
                st.write(f"- {item['action_type']}: {item['count']} عملية")
        
        with col2:
            st.markdown("**أكثر المستخدمين نشاطاً:**")
            for item in summary['top_users']:
                st.write(f"- {item['user_name']}: {item['count']} عملية")
    
    st.markdown("---")
    
    # قائمة العمليات
    st.markdown("### 📝 تفاصيل العمليات")
    
    action_filter = None if filter_action == "الكل" else filter_action
    
    logs = get_audit_logs(
        start_date=(datetime.now() - timedelta(days=filter_days)).isoformat(),
        user_name=filter_user if filter_user else None,
        action_type=action_filter,
        limit=100
    )
    
    if logs:
        data = []
        for log in logs:
            data.append({
                "التاريخ": log['timestamp'][:19] if log['timestamp'] else "-",
                "المستخدم": log['user_name'],
                "النوع": log['action_type'],
                "الوصف": log['description'],
                "النتيجة": "✅ نجاح" if log['success'] else "❌ فشل"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("لا توجد عمليات مسجلة في الفترة المحددة.")

# ==========================================
# التبويب 4: الإعدادات
# ==========================================
with tab4:
    st.subheader("⚙️ إعدادات النسخ الاحتياطي")
    
    st.info("""
    💡 **الإعدادات الحالية:**
    - النسخ التلقائي: مفعّل
    - الفترة: كل ساعة
    - عدد النسخ المحفوظة: 7
    - النسخ عند الإغلاق: مفعّل
    """)
    
    st.markdown("---")
    
    st.markdown("###  مواقع التخزين")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**المجلد المحلي:**")
        st.code(str(backup_manager.backup_folder))
    with col2:
        st.markdown("**المجلد الخارجي الآمن:**")
        st.code(str(backup_manager.external_backup_folder))
    
    st.markdown("---")
    
    st.markdown("### 🛡️ نصائح لحماية البيانات")
    
    st.markdown("""
    1. **النسخ الاحتياطي التلقائي** يعمل كل ساعة
    2. **نسخ خارجية آمنة** في مجلد منفصل
    3. **الاحتفاظ بـ 7 نسخ** احتياطية
    4. **سجل العمليات** لتتبع جميع التغييرات
    5. **تأكيد متعدد** قبل الحذف أو الاستعادة
    6. **نسخة أمان** قبل أي استعادة
    """)
    
    st.markdown("---")
    
    st.markdown("### 📊 إحصائيات النظام")
    
    from database import SessionLocal
    import models
    
    db = SessionLocal()
    try:
        total_invoices = db.query(models.Invoice).count()
        total_customers = db.query(models.Party).count()
        total_items = db.query(models.Item).count()
        total_users = db.query(models.User).count()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("الفواتير", total_invoices)
        with col2:
            st.metric("العملاء/الموردين", total_customers)
        with col3:
            st.metric("الأصناف", total_items)
        with col4:
            st.metric("المستخدمين", total_users)
    finally:
        db.close()