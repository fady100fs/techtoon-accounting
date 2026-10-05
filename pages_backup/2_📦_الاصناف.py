# pages/2__الأصناف.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import Category
from services import (
    create_item, create_kit_item, import_items_from_file,
    export_import_template, export_items_to_excel, export_categories_to_excel,
    import_categories_from_file
)
from auth_required import require_login, get_current_user_id, get_current_user_name
import tempfile
import os

# ✅ 1. إعدادات الصفحة أولاً
st.set_page_config(page_title="الأصناف", page_icon="📦", layout="wide")

# ✅ 2. التحقق من الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

# ✅ 3. التنقل بـ Enter
from keyboard_nav import enable_enter_navigation, add_enter_hint
enable_enter_navigation()
add_enter_hint()

st.title(" إدارة الأصناف")
st.info(f" المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

if 'item_name' not in st.session_state:
    st.session_state.item_name = ""
if 'item_cost_price' not in st.session_state:
    st.session_state.item_cost_price = 0.0
if 'item_sell_price' not in st.session_state:
    st.session_state.item_sell_price = 0.0
if 'item_barcode' not in st.session_state:
    st.session_state.item_barcode = ""

tab1, tab2, tab3, tab4 = st.tabs([
    "➕ إضافة/تعديل صنف",
    "📋 قائمة الأصناف",
    "📥 استيراد وتصدير الأصناف",
    "🗂️ استيراد وتصدير التصنيفات"
])

# ==========================================
# التبويب 1: إضافة/تعديل صنف
# ==========================================
with tab1:
    st.subheader("➕ إضافة صنف جديد")
    
    item_type = st.radio("نوع الصنف:", ["صنف عادي", "صنف مدمج (Kit)"])
    
    name = st.text_input("اسم الصنف", value=st.session_state.item_name, key="input_name")
    
    all_categories = db.query(Category).filter(Category.is_active == True).all()
    category_options = {"بدون تصنيف": None}
    for cat in all_categories:
        category_options[cat.name] = cat.id
    
    selected_category_name = st.selectbox(
        "التصنيف:",
        options=list(category_options.values()),
        format_func=lambda x: next((k for k, v in category_options.items() if v == x), "بدون تصنيف"),
        key="input_category"
    )
    
    cost_price = st.number_input("سعر التكلفة", min_value=0.0, step=0.1, value=st.session_state.item_cost_price, key="input_cost")
    sell_price = st.number_input("سعر البيع", min_value=0.0, step=0.1, value=st.session_state.item_sell_price, key="input_sell")
    barcode = st.text_input("الباركود (اختياري)", value=st.session_state.item_barcode, key="input_barcode")
    
    if item_type == "صنف مدمج (Kit)":
        st.info("⚠️ الصنف المدمج يتكون من أصناف أخرى")
        all_items = db.query(models.Item).filter(models.Item.is_kit == False).all()
        item_names = [item.name for item in all_items]
        selected_components = st.multiselect("اختر المكونات:", item_names, key="input_components")
        components_data = []
        for comp_name in selected_components:
            qty = st.number_input(f"كمية {comp_name}", min_value=1, step=1, key=f"qty_{comp_name}")
            components_data.append({'item_name': comp_name, 'quantity': qty})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 حفظ الصنف", type="primary"):
            if not name:
                st.error("يرجى إدخال اسم الصنف")
            else:
                try:
                    if item_type == "صنف عادي":
                        item = create_item(name, cost_price, sell_price, barcode if barcode else None, created_by=current_user_id)
                        if selected_category_name:
                            item.category_id = selected_category_name
                            db.commit()
                    else:
                        if not components_data:
                            st.error("يرجى اختيار مكون واحد على الأقل")
                        else:
                            item = create_kit_item(name, components_data, sell_price, created_by=current_user_id)
                            if selected_category_name:
                                item.category_id = selected_category_name
                                db.commit()
                    
                    st.success(f"✅ تم الحفظ بنجاح!")
                    
                    st.session_state.item_name = ""
                    st.session_state.item_cost_price = 0.0
                    st.session_state.item_sell_price = 0.0
                    st.session_state.item_barcode = ""
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    
    with col2:
        if st.button("🧹 مسح الحقول"):
            st.session_state.item_name = ""
            st.session_state.item_cost_price = 0.0
            st.session_state.item_sell_price = 0.0
            st.session_state.item_barcode = ""
            st.rerun()
    
    with col3:
        if st.button("❌ إلغاء"):
            st.session_state.item_name = ""
            st.session_state.item_cost_price = 0.0
            st.session_state.item_sell_price = 0.0
            st.session_state.item_barcode = ""
            st.rerun()

# ==========================================
# التبويب 2: قائمة الأصناف
# ==========================================
with tab2:
    st.subheader("📋 قائمة الأصناف")
    
    all_categories = db.query(Category).filter(Category.is_active == True).all()
    filter_category = st.selectbox(
        "تصفية حسب التصنيف:",
        options=["الكل"] + [cat.name for cat in all_categories]
    )
    
    items_query = db.query(models.Item)
    if filter_category != "الكل":
        category = db.query(Category).filter(Category.name == filter_category).first()
        if category:
            items_query = items_query.filter(models.Item.category_id == category.id)
    
    items = items_query.all()
    
    if items:
        data = []
        for item in items:
            category = db.query(Category).filter(Category.id == item.category_id).first()
            movements = db.query(models.InventoryMovement).filter(models.InventoryMovement.item_id == item.id).all()
            current_stock = sum(m.quantity if m.type == 'in' else -m.quantity for m in movements)
            
            data.append({
                "ID": item.id,
                "الاسم": item.name,
                "التصنيف": category.name if category else "بدون",
                "النوع": "مدمج" if item.is_kit else "عادي",
                "سعر التكلفة": item.cost_price,
                "سعر البيع": item.sell_price,
                "الرصيد الحالي": current_stock,
                "الباركود": item.barcode or "-"
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("️ تعديل/حذف صنف")
        
        item_ids = [item.id for item in items]
        
        selected_item_id = st.selectbox(
            "اختر صنف:",
            options=item_ids,
            format_func=lambda x: next((f"{item.name}" for item in items if item.id == x), x)
        )
        
        if selected_item_id:
            selected_item = db.query(models.Item).filter(models.Item.id == selected_item_id).first()
            
            invoice_lines = db.query(models.InvoiceLine).filter(models.InvoiceLine.item_id == selected_item_id).all()
            is_used_in_invoices = len(invoice_lines) > 0
            
            st.markdown("---")
            st.subheader("✏️ تعديل الصنف")
            
            new_name = st.text_input("الاسم الجديد:", value=selected_item.name, key=f"edit_name_{selected_item_id}")
            new_cost = st.number_input("سعر التكلفة الجديد:", value=selected_item.cost_price, key=f"edit_cost_{selected_item_id}")
            new_sell = st.number_input("سعر البيع الجديد:", value=selected_item.sell_price, key=f"edit_sell_{selected_item_id}")
            new_barcode = st.text_input("الباركود الجديد:", value=selected_item.barcode or "", key=f"edit_barcode_{selected_item_id}")
            
            new_category = st.selectbox(
                "التصنيف الجديد:",
                options=["بدون تصنيف"] + [cat.name for cat in all_categories],
                index=0 if not selected_item.category_id else 1,
                key=f"edit_category_{selected_item_id}"
            )
            
            if st.button("💾 حفظ التعديلات", type="primary"):
                try:
                    selected_item.name = new_name
                    selected_item.cost_price = new_cost
                    selected_item.sell_price = new_sell
                    selected_item.barcode = new_barcode if new_barcode else None
                    
                    if new_category == "بدون تصنيف":
                        selected_item.category_id = None
                    else:
                        category = db.query(Category).filter(Category.name == new_category).first()
                        if category:
                            selected_item.category_id = category.id
                    
                    db.commit()
                    st.success(f"✅ تم تحديث الصنف بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
            
            st.markdown("---")
            st.subheader("🗑️ حذف الصنف")
            
            if is_used_in_invoices:
                st.error(f" لا يمكن حذف هذا الصنف! مستخدم في {len(invoice_lines)} فاتورة سابقة.")
            else:
                if st.button("🗑️ حذف الصنف", type="secondary"):
                    if st.checkbox("تأكيد الحذف؟"):
                        try:
                            db.query(models.KitComponent).filter(
                                models.KitComponent.kit_item_id == selected_item_id
                            ).delete()
                            db.query(models.KitComponent).filter(
                                models.KitComponent.component_item_id == selected_item_id
                            ).delete()
                            
                            db.query(models.InventoryMovement).filter(
                                models.InventoryMovement.item_id == selected_item_id
                            ).delete()
                            
                            db.delete(selected_item)
                            db.commit()
                            st.success(f"✅ تم حذف الصنف بنجاح!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ في الحذف: {e}")
    else:
        st.info("لا توجد أصناف.")

# ==========================================
# التبويب 3: استيراد وتصدير الأصناف
# ==========================================
with tab3:
    st.subheader("📤 تصدير الأصناف")
    
    st.info("""
    💡 **يتم تصدير:**
    - الكود (الباركود)
    - الاسم
    - أسعار التكلفة والبيع
    - التصنيف
    - الرصيد الافتتاحي
    - الحد الأدنى للمخزون
    """)
    
    if st.button(" تصدير جميع الأصناف إلى Excel", type="primary"):
        try:
            output_path, count = export_items_to_excel()
            st.success(f"✅ تم تصدير {count} صنف بنجاح!")
            
            with open(output_path, "rb") as file:
                st.download_button(
                    label="⬇️ تحميل ملف الأصناف",
                    data=file,
                    file_name=output_path,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"❌ خطأ في التصدير: {e}")
    
    st.markdown("---")
    st.subheader("📥 استيراد الأصناف من ملف")
    
    st.markdown("""
    ### الأعمدة المطلوبة:
    - `name`: اسم الصنف (مطلوب)
    - `barcode`: الباركود (اختياري)
    - `cost_price`: سعر التكلفة
    - `sell_price`: سعر البيع
    - `is_kit`: عادي/مدمج
    - `category`: التصنيف
    - `min_stock`: الحد الأدنى
    - `current_stock`: الرصيد الافتتاحي
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⬇️ تحميل قالب الأصناف"):
            try:
                template_path = export_import_template('items', 'template_items.xlsx')
                with open(template_path, "rb") as file:
                    st.download_button(
                        label="⬇️ تحميل القالب",
                        data=file,
                        file_name="template_items.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            except Exception as e:
                st.error(f"خطأ: {e}")
    
    with col2:
        uploaded_file = st.file_uploader("اختر ملف:", type=['xlsx', 'csv'], key="upload_items")
        
        if uploaded_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            if st.button("📥 استيراد", type="primary"):
                try:
                    count, errors = import_items_from_file(tmp_path, created_by=current_user_id)
                    st.success(f"✅ تم استيراد {count} صنف!")
                    if errors:
                        for error in errors[:5]:
                            st.write(f"- {error}")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")
                finally:
                    os.unlink(tmp_path)

# ==========================================
# التبويب 4: استيراد وتصدير التصنيفات
# ==========================================
with tab4:
    st.subheader("📤 تصدير التصنيفات")
    
    if st.button(" تصدير التصنيفات إلى Excel", type="primary"):
        try:
            output_path, count = export_categories_to_excel()
            st.success(f"✅ تم تصدير {count} تصنيف!")
            
            with open(output_path, "rb") as file:
                st.download_button(
                    label="⬇️ تحميل",
                    data=file,
                    file_name=output_path
                )
        except Exception as e:
            st.error(f" خطأ: {e}")
    
    st.markdown("---")
    st.subheader("📥 استيراد التصنيفات")
    
    uploaded_file = st.file_uploader("اختر ملف التصنيفات:", type=['xlsx', 'csv'], key="upload_categories")
    
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        if st.button(" استيراد التصنيفات", type="primary"):
            try:
                count, errors = import_categories_from_file(tmp_path, created_by=current_user_id)
                st.success(f"✅ تم استيراد {count} تصنيف!")
                st.rerun()
            except Exception as e:
                st.error(f"خطأ: {e}")
            finally:
                os.unlink(tmp_path)

db.close()