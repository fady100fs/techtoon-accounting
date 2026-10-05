# pages/21_👤_إدارة_المستخدمين.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import User, UserRole
from auth import hash_password, verify_password, create_user, get_user_permissions
from auth_required import require_login, get_current_user_id, get_current_user_name, check_permission

# التحقق من تسجيل الدخول والصلاحية
current_user = require_login()

if not check_permission('can_manage_users'):
    st.error("⛔ ليس لديك صلاحية إدارة المستخدمين!")
    st.info(f"دورك الحالي: **{current_user['role'].value}** - هذه الصلاحية متاحة للمدير فقط.")
    st.stop()

current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="إدارة المستخدمين", page_icon="👤", layout="wide")
st.title("👤 إدارة المستخدمين والصلاحيات")

st.info(f" المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

# تهيئة session_state لتخزين قيم كلمات المرور
if 'change_old_password' not in st.session_state:
    st.session_state.change_old_password = ""
if 'change_new_password' not in st.session_state:
    st.session_state.change_new_password = ""
if 'change_confirm_password' not in st.session_state:
    st.session_state.change_confirm_password = ""

tab1, tab2, tab3 = st.tabs(["➕ إضافة مستخدم جديد", " قائمة المستخدمين", "🔐 تغيير كلمة المرور"])

# ==========================================
# التبويب 1: إضافة مستخدم جديد
# ==========================================
with tab1:
    st.subheader("➕ إضافة مستخدم جديد")
    
    st.markdown("""
    ### الأدوار المتاحة:
    - **مدير**: صلاحيات كاملة (إنشاء، تعديل، حذف، تقارير، إدارة مستخدمين، نسخ احتياطي)
    - **محاسب**: إنشاء، تعديل، تقارير، نسخ احتياطي، استيراد (بدون حذف)
    - **بائع**: إنشاء وتعديل الفواتير والأصناف فقط
    - **مشاهد**: عرض التقارير فقط
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        username = st.text_input("اسم المستخدم:", key="new_username_input")
        full_name = st.text_input("الاسم الكامل:", key="new_fullname_input")
        email = st.text_input("البريد الإلكتروني (اختياري):", key="new_email_input")
    
    with col2:
        password = st.text_input("كلمة المرور:", type="password", key="new_password_input")
        confirm_password = st.text_input("تأكيد كلمة المرور:", type="password", key="new_confirm_input")
        
        role = st.selectbox(
            "الدور الوظيفي:",
            options=[role.value for role in UserRole],
            format_func=lambda x: x
        )
    
    is_active = st.checkbox("تفعيل الحساب", value=True)
    
    st.markdown("---")
    st.subheader("📋 الصلاحيات الممنوحة لهذا الدور")
    
    selected_role = next((r for r in UserRole if r.value == role), UserRole.VIEWER)
    permissions = get_user_permissions(selected_role)
    
    perm_names = {
        'can_create': 'إنشاء بيانات جديدة',
        'can_edit': 'تعديل البيانات',
        'can_delete': 'حذف البيانات',
        'can_view_reports': 'عرض التقارير',
        'can_manage_users': 'إدارة المستخدمين',
        'can_backup': 'النسخ الاحتياطي',
        'can_import': 'استيراد البيانات'
    }
    
    cols = st.columns(2)
    for idx, (perm_key, perm_name) in enumerate(perm_names.items()):
        with cols[idx % 2]:
            status = "✅" if permissions.get(perm_key, False) else "❌"
            st.write(f"{status} {perm_name}")
    
    st.markdown("---")
    
    if st.button("➕ إنشاء المستخدم", type="primary"):
        if not username or not password or not full_name:
            st.error("❌ يرجى ملء جميع الحقول المطلوبة (اسم المستخدم، كلمة المرور، الاسم الكامل)")
        elif len(password) < 6:
            st.error("❌ كلمة المرور يجب أن تكون 6 أحرف على الأقل")
        elif password != confirm_password:
            st.error(" كلمتا المرور غير متطابقتين")
        else:
            try:
                existing = db.query(User).filter(User.username == username).first()
                if existing:
                    st.error("❌ اسم المستخدم موجود مسبقاً!")
                else:
                    actual_role = next(r for r in UserRole if r.value == role)
                    
                    new_user = User(
                        username=username,
                        password_hash=hash_password(password),
                        full_name=full_name,
                        email=email if email else None,
                        role=actual_role,
                        is_active=is_active,
                        created_at=datetime.now()
                    )
                    db.add(new_user)
                    db.commit()
                    
                    st.success(f"✅ تم إنشاء المستخدم '{full_name}' بنجاح!")
                    st.balloons()
                    st.rerun()
            except Exception as e:
                st.error(f" خطأ: {e}")

# ==========================================
# التبويب 2: قائمة المستخدمين
# ==========================================
with tab2:
    st.subheader(" قائمة المستخدمين")
    
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    if users:
        data = []
        for user in users:
            data.append({
                "ID": user.id,
                "اسم المستخدم": user.username,
                "الاسم الكامل": user.full_name,
                "البريد الإلكتروني": user.email or "-",
                "الدور": user.role.value,
                "الحالة": "نشط" if user.is_active else "معطل",
                "تاريخ الإنشاء": user.created_at.strftime("%Y-%m-%d") if user.created_at else "-",
                "آخر دخول": user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "لم يسجل دخول بعد"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("️ تعديل/حذف مستخدم")
        
        user_ids = [u.id for u in users]
        
        selected_user_id = st.selectbox(
            "اختر مستخدماً:",
            options=user_ids,
            format_func=lambda x: next((f"{u.full_name} ({u.username})" for u in users if u.id == x), x)
        )
        
        if selected_user_id:
            selected_user = db.query(User).filter(User.id == selected_user_id).first()
            
            if selected_user_id == current_user_id:
                st.warning("⚠️ لا يمكنك تعديل أو حذف حسابك الحالي من هنا. استخدم تبويب 'تغيير كلمة المرور' لتغيير كلمة المرور.")
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**تعديل بيانات المستخدم:**")
                    
                    new_full_name = st.text_input("الاسم الكامل:", value=selected_user.full_name, key=f"edit_name_{selected_user_id}")
                    new_email = st.text_input("البريد الإلكتروني:", value=selected_user.email or "", key=f"edit_email_{selected_user_id}")
                    new_role = st.selectbox(
                        "الدور الجديد:",
                        options=[role.value for role in UserRole],
                        index=[role.value for role in UserRole].index(selected_user.role.value),
                        key=f"edit_role_{selected_user_id}"
                    )
                    new_is_active = st.checkbox("تفعيل الحساب", value=selected_user.is_active, key=f"edit_active_{selected_user_id}")
                    
                    if st.button("💾 حفظ التعديلات", type="primary"):
                        try:
                            selected_user.full_name = new_full_name
                            selected_user.email = new_email if new_email else None
                            selected_user.role = next(r for r in UserRole if r.value == new_role)
                            selected_user.is_active = new_is_active
                            
                            db.commit()
                            st.success(f"✅ تم تحديث بيانات '{new_full_name}' بنجاح!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")
                
                with col2:
                    st.markdown("**حذف المستخدم:**")
                    st.warning("⚠️ سيتم حذف المستخدم نهائياً!")
                    st.info("ملاحظة: القيود المحاسبية التي أنشأها هذا المستخدم ستبقى مسجلة باسمه.")
                    
                    if st.button("🗑️ حذف المستخدم", type="secondary"):
                        if st.checkbox(f"تأكيد حذف '{selected_user.full_name}'؟"):
                            try:
                                db.delete(selected_user)
                                db.commit()
                                st.success(f"✅ تم حذف المستخدم '{selected_user.full_name}' بنجاح!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا يوجد مستخدمون.")

# ==========================================
# التبويب 3: تغيير كلمة المرور (باستخدام form)
# ==========================================
with tab3:
    st.subheader("🔐 تغيير كلمة المرور")
    
    st.info(f"تغيير كلمة المرور للمستخدم: **{current_user_name}**")
    
    # ✅ استخدام form لمنع فقدان القيم
    with st.form("change_password_form", clear_on_submit=True):
        old_password = st.text_input(
            "كلمة المرور الحالية:",
            type="password",
            help="أدخل كلمة المرور الحالية"
        )
        
        new_password = st.text_input(
            "كلمة المرور الجديدة:",
            type="password",
            help="6 أحرف على الأقل"
        )
        
        confirm_new_password = st.text_input(
            "تأكيد كلمة المرور الجديدة:",
            type="password",
            help="أعد إدخال كلمة المرور الجديدة"
        )
        
        # زر الإرسال داخل الـ form
        submit_button = st.form_submit_button("🔐 تغيير كلمة المرور", type="primary", use_container_width=True)
    
    # معالجة الإرسال
    if submit_button:
        if not old_password or old_password.strip() == "":
            st.error("❌ يرجى إدخال كلمة المرور الحالية")
        elif not new_password or new_password.strip() == "":
            st.error("❌ يرجى إدخال كلمة المرور الجديدة")
        elif not confirm_new_password or confirm_new_password.strip() == "":
            st.error("❌ يرجى تأكيد كلمة المرور الجديدة")
        elif len(new_password) < 6:
            st.error("❌ كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل")
        elif new_password != confirm_new_password:
            st.error("❌ كلمتا المرور الجديدتان غير متطابقتين")
        else:
            try:
                current_user_obj = db.query(User).filter(User.id == current_user_id).first()
                
                if not current_user_obj:
                    st.error("❌ المستخدم غير موجود في قاعدة البيانات!")
                elif not verify_password(old_password, current_user_obj.password_hash):
                    st.error("❌ كلمة المرور الحالية غير صحيحة!")
                else:
                    current_user_obj.password_hash = hash_password(new_password)
                    db.commit()
                    
                    st.success("✅ تم تغيير كلمة المرور بنجاح!")
                    st.balloons()
                    st.info("🔄 يرجى تسجيل الدخول مرة أخرى بكلمة المرور الجديدة")
                    
            except Exception as e:
                st.error(f"❌ خطأ: {e}")
                db.rollback()

db.close()