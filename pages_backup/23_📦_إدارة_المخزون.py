# pages/23_📦_إدارة_المخزون.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import Warehouse, StockLevel, WarehouseTransfer, StockCount
from services import (
    create_warehouse, get_stock_level, update_stock_level,
    transfer_between_warehouses, create_stock_count, get_warehouse_stock_report
)
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="إدارة المخزون", page_icon="", layout="wide")
st.title(" إدارة المخزون المتقدمة")

st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏭 إدارة المخازن",
    "📊 مستويات المخزون",
    "🔄 تحويل بين المخازن",
    "📋 الجرد الدوري",
    "📈 تقارير المخزون"
])

# ==========================================
# التبويب 1: إدارة المخازن
# ==========================================
with tab1:
    st.subheader("🏭 إدارة المخازن")
    
    sub_tab1, sub_tab2 = st.tabs(["➕ إضافة مخزن", " قائمة المخازن"])
    
    with sub_tab1:
        st.markdown("### ➕ إضافة مخزن جديد")
        
        warehouse_name = st.text_input("اسم المخزن:", placeholder="مثال: المخزن الرئيسي، فرع القاهرة...")
        warehouse_code = st.text_input("كود المخزن:", placeholder="مثال: WH001, BRANCH01...")
        warehouse_location = st.text_input("الموقع (اختياري):", placeholder="العنوان أو الموقع")
        warehouse_responsible = st.text_input("الشخص المسؤول (اختياري):", placeholder="اسم المسؤول")
        warehouse_notes = st.text_area("ملاحظات (اختياري):")
        
        if st.button("💾 إنشاء المخزن", type="primary"):
            if not warehouse_name or not warehouse_code:
                st.error("يرجى إدخال اسم وكود المخزن")
            else:
                try:
                    create_warehouse(
                        name=warehouse_name,
                        code=warehouse_code,
                        location=warehouse_location if warehouse_location else None,
                        responsible_person=warehouse_responsible if warehouse_responsible else None,
                        notes=warehouse_notes if warehouse_notes else None
                    )
                    st.success(f"✅ تم إنشاء المخزن '{warehouse_name}' بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")
    
    with sub_tab2:
        st.markdown("### 📋 قائمة المخازن")
        
        warehouses = db.query(Warehouse).all()
        
        if warehouses:
            data = []
            for wh in warehouses:
                stock_count = db.query(StockLevel).filter(
                    StockLevel.warehouse_id == wh.id,
                    StockLevel.quantity > 0
                ).count()
                
                data.append({
                    "الكود": wh.code,
                    "الاسم": wh.name,
                    "الموقع": wh.location or "-",
                    "المسؤول": wh.responsible_person or "-",
                    "عدد الأصناف": stock_count,
                    "الحالة": "✅ نشط" if wh.is_active else "⛔ معطل"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد مخازن مسجلة.")

# ==========================================
# التبويب 2: مستويات المخزون
# ==========================================
with tab2:
    st.subheader("📊 مستويات المخزون")
    
    warehouses = db.query(Warehouse).filter(Warehouse.is_active == True).all()
    
    if not warehouses:
        st.warning("⚠️ لا توجد مخازن نشطة!")
    else:
        selected_warehouse_id = st.selectbox(
            "اختر المخزن:",
            options=[wh.id for wh in warehouses],
            format_func=lambda x: next((wh.name for wh in warehouses if wh.id == x), x)
        )
        
        if selected_warehouse_id:
            report = get_warehouse_stock_report(selected_warehouse_id)
            
            if report:
                df = pd.DataFrame(report)
                st.dataframe(df, use_container_width=True)
                
                low_stock = len([r for r in report if r['status'] == 'منخفض'])
                good_stock = len([r for r in report if r['status'] == 'جيد'])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("أصناف بمخزون جيد", good_stock)
                with col2:
                    st.metric("أصناف بمخزون منخفض", low_stock)
            else:
                st.info("لا توجد أصناف في هذا المخزن.")

# ==========================================
# التبويب 3: تحويل بين المخازن
# ==========================================
with tab3:
    st.subheader("🔄 تحويل صنف بين مخزنين")
    
    warehouses = db.query(Warehouse).filter(Warehouse.is_active == True).all()
    
    if len(warehouses) < 2:
        st.warning("⚠️ يجب وجود مخزنين نشطين على الأقل!")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            from_warehouse_id = st.selectbox(
                "من مخزن:",
                options=[wh.id for wh in warehouses],
                format_func=lambda x: next((wh.name for wh in warehouses if wh.id == x), x)
            )
        
        with col2:
            to_warehouse_id = st.selectbox(
                "إلى مخزن:",
                options=[wh.id for wh in warehouses],
                format_func=lambda x: next((wh.name for wh in warehouses if wh.id == x), x)
            )
        
        items = db.query(models.Item).filter(models.Item.is_kit == False).all()
        item_dict = {item.id: item.name for item in items}
        
        selected_item_id = st.selectbox(
            "اختر الصنف:",
            options=list(item_dict.keys()),
            format_func=lambda x: item_dict[x]
        )
        
        if selected_item_id and from_warehouse_id:
            current_stock = get_stock_level(from_warehouse_id, selected_item_id)
            st.info(f"💰 الرصيد الحالي في المخزن المصدر: **{current_stock}**")
        
        quantity = st.number_input("الكمية المراد تحويلها:", min_value=1, step=1)
        transfer_notes = st.text_area("ملاحظات (اختياري):")
        
        if st.button("🔄 تنفيذ التحويل", type="primary"):
            if from_warehouse_id == to_warehouse_id:
                st.error("❌ لا يمكن التحويل بين نفس المخزن!")
            elif not selected_item_id:
                st.error("❌ يرجى اختيار صنف!")
            elif quantity <= 0:
                st.error("❌ يرجى إدخال كمية صحيحة!")
            else:
                try:
                    transfer_between_warehouses(
                        from_warehouse_id=from_warehouse_id,
                        to_warehouse_id=to_warehouse_id,
                        item_id=selected_item_id,
                        quantity=quantity,
                        notes=transfer_notes if transfer_notes else None,
                        created_by=current_user_id
                    )
                    st.success(f"✅ تم التحويل بنجاح!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 4: الجرد الدوري
# ==========================================
with tab4:
    st.subheader("📋 الجرد الدوري")
    
    st.info("""
    💡 **الجرد الدوري:**
    - قم بعد الأصناف فعلياً في المخزن
    - أدخل الكمية الفعلية
    - النظام سيحسب الفرق ويحدث المخزون تلقائياً
    """)
    
    warehouses = db.query(Warehouse).filter(Warehouse.is_active == True).all()
    
    if not warehouses:
        st.warning("⚠️ لا توجد مخازن نشطة!")
    else:
        selected_warehouse_id = st.selectbox(
            "اختر المخزن للجرد:",
            options=[wh.id for wh in warehouses],
            format_func=lambda x: next((wh.name for wh in warehouses if wh.id == x), x)
        )
        
        if selected_warehouse_id:
            stocks = db.query(StockLevel).filter(
                StockLevel.warehouse_id == selected_warehouse_id,
                StockLevel.quantity > 0
            ).all()
            
            if stocks:
                st.markdown("### 📝 أدخل الكميات الفعلية")
                
                for stock in stocks:
                    item = db.query(models.Item).filter(models.Item.id == stock.item_id).first()
                    if item:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{item.name}** ({item.barcode or 'بدون باركود'})")
                        with col2:
                            st.write(f"النظام: {stock.quantity}")
                        with col3:
                            counted = st.number_input(
                                "الفعلي:",
                                min_value=0,
                                value=int(stock.quantity),
                                step=1,
                                key=f"count_{stock.id}"
                            )
                        
                        if st.button("💾 حفظ", key=f"save_{stock.id}"):
                            try:
                                create_stock_count(
                                    warehouse_id=selected_warehouse_id,
                                    item_id=stock.item_id,
                                    counted_quantity=counted,
                                    counted_by=current_user_id
                                )
                                st.success(f"✅ تم تحديث مخزون '{item.name}'!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")
            else:
                st.info("لا توجد أصناف في هذا المخزن للجرد.")

# ==========================================
# التبويب 5: تقارير المخزون
# ==========================================
with tab5:
    st.subheader("📈 تقارير المخزون")
    
    report_tab1, report_tab2 = st.tabs(["📊 تقرير المخزون", "🔄 سجل التحويلات"])
    
    with report_tab1:
        st.markdown("### 📊 تقرير المخزون الشامل")
        
        warehouses = db.query(Warehouse).filter(Warehouse.is_active == True).all()
        
        if warehouses:
            all_stocks = []
            for wh in warehouses:
                stocks = db.query(StockLevel).filter(
                    StockLevel.warehouse_id == wh.id,
                    StockLevel.quantity > 0
                ).all()
                
                for stock in stocks:
                    item = db.query(models.Item).filter(models.Item.id == stock.item_id).first()
                    if item:
                        all_stocks.append({
                            "المخزن": wh.name,
                            "الصنف": item.name,
                            "الباركود": item.barcode or "-",
                            "الكمية": stock.quantity,
                            "الحد الأدنى": item.min_stock,
                            "الحالة": "⚠️ منخفض" if stock.quantity <= item.min_stock else "✅ جيد"
                        })
            
            if all_stocks:
                df = pd.DataFrame(all_stocks)
                st.dataframe(df, use_container_width=True)
                
                if st.button("📤 تصدير التقرير إلى Excel"):
                    df.to_excel("stock_report.xlsx", index=False)
                    with open("stock_report.xlsx", "rb") as file:
                        st.download_button(
                            label="⬇️ تحميل التقرير",
                            data=file,
                            file_name="stock_report.xlsx"
                        )
            else:
                st.info("لا توجد بيانات مخزون.")
        else:
            st.info("لا توجد مخازن نشطة.")
    
    with report_tab2:
        st.markdown("### 🔄 سجل التحويلات بين المخازن")
        
        transfers = db.query(WarehouseTransfer).order_by(
            WarehouseTransfer.date.desc()
        ).limit(50).all()
        
        if transfers:
            data = []
            for transfer in transfers:
                from_wh = db.query(Warehouse).filter(Warehouse.id == transfer.from_warehouse_id).first()
                to_wh = db.query(Warehouse).filter(Warehouse.id == transfer.to_warehouse_id).first()
                item = db.query(models.Item).filter(models.Item.id == transfer.item_id).first()
                
                data.append({
                    "التاريخ": transfer.date.strftime("%Y-%m-%d %H:%M"),
                    "من": from_wh.name if from_wh else "-",
                    "إلى": to_wh.name if to_wh else "-",
                    "الصنف": item.name if item else "-",
                    "الكمية": transfer.quantity,
                    "الحالة": transfer.status
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("لا توجد تحويلات مسجلة.")

db.close()