# pages/20_🗂️_التصنيفات.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import Category
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="التصنيفات", page_icon="🗂️", layout="wide")
st.title("🗂️ إدارة تصنيفات الأصناف")

st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2 = st.tabs(["➕ إضافة/تعديل تصنيف", "📋 قائمة التصنيفات"])

# ==========================================
# التبويب 1: إضافة/تعديل تصنيف
# ==========================================
with tab1:
    st.subheader(" إضافة تصنيف جديد")
    
    st.info("""
    💡 **ملاحظة مهمة:**
    - التصنيفات تساعد في تنظيم الأصناف وتسهيل البحث عنها
    - يمكن إضافة تصنيفات فرعية تحت تصنيفات رئيسية
    - حذف أو تعديل التصنيف لا يؤثر على الأصناف المرتبطة به
    """)
    
    category_name = st.text_input("اسم التصنيف:", placeholder="مثال: أدوات مكتبية، مواد غذائية...")
    category_description = st.text_area("الوصف (اختياري):", placeholder="وصف مختصر للتصنيف...")
    
    # اختيار التصنيف الأب (للتصنيفات الفرعية)
    all_categories = db.query(Category).filter(Category.is_active == True).all()
    category_options = {"بدون (تصنيف رئيسي)": None}
    for cat in all_categories:
        category_options[cat.name] = cat.id
    
    parent_category = st.selectbox(
        "التصنيف الأب (اختياري):",
        options=list(category_options.values()),
        format_func=lambda x: next((k for k, v in category_options.items() if v == x), "بدون")
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(" إضافة التصنيف", type="primary"):
            if not category_name:
                st.error("يرجى إدخال اسم التصنيف")
            else:
                try:
                    # التحقق من عدم التكرار
                    existing = db.query(Category).filter(Category.name == category_name).first()
                    if existing:
                        st.error("هذا التصنيف موجود مسبقاً!")
                    else:
                        new_category = Category(
                            name=category_name,
                            description=category_description if category_description else None,
                            parent_id=parent_category,
                            is_active=True,
                            created_at=datetime.now()
                        )
                        db.add(new_category)
                        db.commit()
                        st.success(f"✅ تم إضافة التصنيف '{category_name}' بنجاح!")
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    
    with col2:
        if st.button("🧹 مسح الحقول"):
            st.rerun()
    
    st.markdown("---")
    st.subheader("️ تعديل تصنيف موجود")
    
    if all_categories:
        selected_category_id = st.selectbox(
            "اختر تصنيفاً للتعديل:",
            options=[cat.id for cat in all_categories],
            format_func=lambda x: next((cat.name for cat in all_categories if cat.id == x), x)
        )
        
        if selected_category_id:
            selected_category = db.query(Category).filter(Category.id == selected_category_id).first()
            
            new_name = st.text_input("الاسم الجديد:", value=selected_category.name, key=f"edit_name_{selected_category_id}")
            new_description = st.text_area("الوصف الجديد:", value=selected_category.description or "", key=f"edit_desc_{selected_category_id}")
            
            if st.button("حفظ التعديلات", type="primary"):
                if not new_name:
                    st.error("يرجى إدخال اسم التصنيف")
                else:
                    try:
                        # التحقق من عدم التكرار (باستثناء التصنيف الحالي)
                        existing = db.query(Category).filter(
                            Category.name == new_name,
                            Category.id != selected_category_id
                        ).first()
                        
                        if existing:
                            st.error("هذا الاسم مستخدم لتصنيف آخر!")
                        else:
                            selected_category.name = new_name
                            selected_category.description = new_description if new_description else None
                            db.commit()
                            st.success(f"✅ تم تحديث التصنيف بنجاح!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد تصنيفات للتعديل.")

# ==========================================
# التبويب 2: قائمة التصنيفات
# ==========================================
with tab2:
    st.subheader("📋 قائمة التصنيفات")
    
    all_categories = db.query(Category).order_by(Category.name).all()
    
    if all_categories:
        # عرض التصنيفات الرئيسية والفرعية
        main_categories = [cat for cat in all_categories if cat.parent_id is None]
        
        for main_cat in main_categories:
            with st.expander(f"📁 {main_cat.name}", expanded=True):
                if main_cat.description:
                    st.write(f"**الوصف:** {main_cat.description}")
                
                # عرض التصنيفات الفرعية
                sub_categories = [cat for cat in all_categories if cat.parent_id == main_cat.id]
                
                if sub_categories:
                    st.markdown("**التصنيفات الفرعية:**")
                    for sub_cat in sub_categories:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f" {sub_cat.name}")
                            if sub_cat.description:
                                st.caption(sub_cat.description)
                        with col2:
                            # عدد الأصناف في هذا التصنيف
                            items_count = db.query(models.Item).filter(
                                models.Item.category_id == sub_cat.id
                            ).count()
                            st.write(f"📦 {items_count} صنف")
                        with col3:
                            if st.button("🗑️", key=f"del_sub_{sub_cat.id}"):
                                if st.checkbox(f"تأكيد حذف '{sub_cat.name}'؟", key=f"confirm_del_sub_{sub_cat.id}"):
                                    # التحقق من عدم وجود أصناف مرتبطة
                                    items_in_category = db.query(models.Item).filter(
                                        models.Item.category_id == sub_cat.id
                                    ).all()
                                    
                                    if items_in_category:
                                        st.warning(f"⚠️ يوجد {len(items_in_category)} صنف في هذا التصنيف. سيتم إزالة التصنيف من الأصناف دون حذفها.")
                                    
                                    # إزالة التصنيف من الأصناف (بدون حذف الأصناف)
                                    for item in items_in_category:
                                        item.category_id = None
                                    
                                    # حذف التصنيفات الفرعية لهذا التصنيف
                                    db.query(Category).filter(Category.parent_id == sub_cat.id).delete()
                                    
                                    # حذف التصنيف
                                    db.delete(sub_cat)
                                    db.commit()
                                    st.success(f"✅ تم حذف التصنيف '{sub_cat.name}' بنجاح!")
                                    st.rerun()
                else:
                    st.info("لا توجد تصنيفات فرعية.")
                
                st.markdown("---")
                
                # زر حذف التصنيف الرئيسي
                if st.button(f"🗑️ حذف التصنيف الرئيسي '{main_cat.name}'", key=f"del_main_{main_cat.id}"):
                    if st.checkbox(f"تأكيد حذف '{main_cat.name}' وجميع تصنيفاته الفرعية؟", key=f"confirm_del_main_{main_cat.id}"):
                        try:
                            # إزالة التصنيف من جميع الأصناف المرتبطة
                            items_in_category = db.query(models.Item).filter(
                                models.Item.category_id == main_cat.id
                            ).all()
                            for item in items_in_category:
                                item.category_id = None
                            
                            # حذف التصنيفات الفرعية
                            db.query(Category).filter(Category.parent_id == main_cat.id).delete()
                            
                            # حذف التصنيف الرئيسي
                            db.delete(main_cat)
                            db.commit()
                            st.success(f"✅ تم حذف التصنيف '{main_cat.name}' بنجاح!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ: {e}")
    else:
        st.info("لا توجد تصنيفات مسجلة.")

db.close()