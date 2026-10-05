# pages/24_🏭_الأصول_الثابتة.py
import streamlit as st
import pandas as pd
from datetime import datetime
from database import SessionLocal
import models
from models import FixedAsset, DepreciationRecord, DepreciationMethod
from services import (
    create_fixed_asset, calculate_annual_depreciation,
    run_annual_depreciation, get_asset_depreciation_schedule,
    dispose_asset
)
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الأصول الثابتة", page_icon="", layout="wide")
st.title(" إدارة الأصول الثابتة")

st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "➕ إضافة أصل ثابت",
    "📋 قائمة الأصول",
    "📉 حساب الإهلاك",
    "📊 جدول الإهلاك",
    "🗑️ التخلص من أصل"
])

# ==========================================
# التبويب 1: إضافة أصل ثابت
# ==========================================
with tab1:
    st.subheader("➕ إضافة أصل ثابت جديد")
    
    st.info("""
    💡 **الأصول الثابتة:**
    - أصول طويلة الأجل (أكثر من سنة)
    - تُستهلك قيمتها تدريجياً عبر الإهلاك
    - أمثلة: مباني، سيارات، أجهزة، أثاث
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        asset_name = st.text_input("اسم الأصل:", placeholder="مثال: سيارة نقل، مبنى المكتب...")
        asset_code = st.text_input("كود الأصل:", placeholder="مثال: FA001, VEH001...")
        asset_category = st.selectbox(
            "التصنيف:",
            ["مباني", "سيارات", "أجهزة ومعدات", "أثاث", "أراضي", "أخرى"]
        )
        purchase_date = st.date_input("تاريخ الشراء:", value=datetime.now().date())
    
    with col2:
        purchase_cost = st.number_input("تكلفة الشراء:", min_value=0.01, step=1000.0, format="%.2f")
        salvage_value = st.number_input("قيمة الخردة (المتبقية):", min_value=0.0, step=100.0, format="%.2f", help="القيمة المتوقعة في نهاية العمر الإنتاجي")
        useful_life = st.number_input("العمر الإنتاجي (سنوات):", min_value=1, max_value=50, value=10, step=1)
        depreciation_method = st.selectbox(
            "طريقة الإهلاك:",
            options=[method.value for method in DepreciationMethod],
            format_func=lambda x: x
        )
    
    location = st.text_input("الموقع (اختياري):", placeholder="مثال: الفرع الرئيسي، المستودع...")
    responsible_person = st.text_input("الشخص المسؤول (اختياري):", placeholder="اسم المسؤول عن الأصل")
    notes = st.text_area("ملاحظات (اختياري):")
    
    if st.button("💾 إضافة الأصل", type="primary"):
        if not asset_name or not asset_code:
            st.error("يرجى إدخال اسم وكود الأصل")
        elif purchase_cost <= 0:
            st.error("يرجى إدخال تكلفة شراء صحيحة")
        elif useful_life <= 0:
            st.error("يرجى إدخال عمر إنتاجي صحيح")
        else:
            try:
                purchase_datetime = datetime.combine(purchase_date, datetime.min.time())
                actual_method = next(m for m in DepreciationMethod if m.value == depreciation_method)
                
                create_fixed_asset(
                    name=asset_name,
                    code=asset_code,
                    category=asset_category,
                    purchase_date=purchase_datetime,
                    purchase_cost=purchase_cost,
                    salvage_value=salvage_value,
                    useful_life_years=useful_life,
                    depreciation_method=actual_method,
                    location=location if location else None,
                    responsible_person=responsible_person if responsible_person else None,
                    notes=notes if notes else None,
                    created_by=current_user_id
                )
                
                st.success(f"✅ تم إضافة الأصل '{asset_name}' بنجاح!")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 2: قائمة الأصول
# ==========================================
with tab2:
    st.subheader(" قائمة الأصول الثابتة")
    
    assets = db.query(FixedAsset).all()
    
    if assets:
        data = []
        for asset in assets:
            data.append({
                "الكود": asset.code,
                "الاسم": asset.name,
                "التصنيف": asset.category,
                "تاريخ الشراء": asset.purchase_date.strftime("%Y-%m-%d"),
                "تكلفة الشراء": f"{asset.purchase_cost:,.2f}",
                "مجمع الإهلاك": f"{asset.accumulated_depreciation:,.2f}",
                "صافي القيمة": f"{asset.net_book_value:,.2f}",
                "الحالة": "✅ نشط" if asset.status == 'active' else " متوقف"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # إحصائيات
        total_cost = sum(a.purchase_cost for a in assets)
        total_depreciation = sum(a.accumulated_depreciation for a in assets)
        total_net_value = sum(a.net_book_value for a in assets)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("إجمالي تكلفة الأصول", f"{total_cost:,.2f} ج.م")
        with col2:
            st.metric("إجمالي مجمع الإهلاك", f"{total_depreciation:,.2f} ج.م")
        with col3:
            st.metric("إجمالي صافي القيمة", f"{total_net_value:,.2f} ج.م")
    else:
        st.info("لا توجد أصول ثابتة مسجلة.")

# ==========================================
# التبويب 3: حساب الإهلاك
# ==========================================
with tab3:
    st.subheader("📉 حساب الإهلاك السنوي")
    
    active_assets = db.query(FixedAsset).filter(FixedAsset.status == 'active').all()
    
    if not active_assets:
        st.info("لا توجد أصول نشطة لحساب إهلاكها.")
    else:
        st.info("""
        💡 **طرق الإهلاك:**
        - **الخطي:** مبلغ ثابت سنوياً = (التكلفة - قيمة الخردة) / العمر الإنتاجي
        - **المتناقص:** نسبة متناقصة من صافي القيمة الدفترية
        """)
        
        year = st.number_input("السنة المالية:", min_value=2020, max_value=2100, value=datetime.now().year, step=1)
        
        st.markdown("---")
        st.markdown("### 📊 حساب الإهلاك للأصول النشطة")
        
        if st.button("🧮 حساب الإهلاك", type="primary"):
            results = []
            for asset in active_assets:
                annual_dep = calculate_annual_depreciation(asset)
                results.append({
                    "الكود": asset.code,
                    "الاسم": asset.name,
                    "طريقة الإهلاك": asset.depreciation_method.value,
                    "الإهلاك السنوي": f"{annual_dep:,.2f} ج.م",
                    "صافي القيمة الحالي": f"{asset.net_book_value:,.2f} ج.م"
                })
            
            if results:
                df = pd.DataFrame(results)
                st.dataframe(df, use_container_width=True)
                
                total_annual = sum(r['الإهلاك السنوي'] for r in results)
                st.metric("إجمالي الإهلاك السنوي", f"{total_annual:,.2f} ج.م")
        
        st.markdown("---")
        st.markdown("### ✅ تسجيل الإهلاك الفعلي")
        
        st.warning("⚠️ هذا الإجراء سينشئ قيداً محاسبياً ويحدث قيم الأصول!")
        
        selected_asset_id = st.selectbox(
            "اختر أصلاً لتسجيل إهلاكه:",
            options=[a.id for a in active_assets],
            format_func=lambda x: next((f"{a.code} - {a.name}" for a in active_assets if a.id == x), x)
        )
        
        if selected_asset_id and st.button(" تسجيل الإهلاك", type="secondary"):
            try:
                record = run_annual_depreciation(
                    asset_id=selected_asset_id,
                    year=year,
                    created_by=current_user_id
                )
                st.success(f"✅ تم تسجيل إهلاك سنة {year} بنجاح!")
                st.info(f"مبلغ الإهلاك: {record.depreciation_amount:,.2f} ج.م")
                st.rerun()
            except Exception as e:
                st.error(f" خطأ: {e}")

# ==========================================
# التبويب 4: جدول الإهلاك
# ==========================================
with tab4:
    st.subheader(" جدول الإهلاك الكامل")
    
    all_assets = db.query(FixedAsset).all()
    
    if not all_assets:
        st.info("لا توجد أصول ثابتة.")
    else:
        selected_asset_id = st.selectbox(
            "اختر أصلاً:",
            options=[a.id for a in all_assets],
            format_func=lambda x: next((f"{a.code} - {a.name}" for a in all_assets if a.id == x), x)
        )
        
        if selected_asset_id:
            schedule_data = get_asset_depreciation_schedule(selected_asset_id)
            
            if schedule_data:
                asset = schedule_data['asset']
                schedule = schedule_data['schedule']
                
                st.markdown(f"### 📄 تفاصيل الأصل: {asset.name} ({asset.code})")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("تكلفة الشراء", f"{asset.purchase_cost:,.2f}")
                with col2:
                    st.metric("قيمة الخردة", f"{asset.salvage_value:,.2f}")
                with col3:
                    st.metric("العمر الإنتاجي", f"{asset.useful_life_years} سنة")
                with col4:
                    st.metric("طريقة الإهلاك", asset.depreciation_method.value)
                
                st.markdown("---")
                st.markdown("### 📈 جدول الإهلاك السنوي")
                
                if schedule:
                    df_schedule = pd.DataFrame(schedule)
                    st.dataframe(df_schedule, use_container_width=True)
                    
                    # رسم بياني
                    import plotly.express as px
                    
                    fig = px.line(
                        df_schedule,
                        x='السنة',
                        y='صافي القيمة الدفترية',
                        title='تطور صافي القيمة الدفترية',
                        markers=True
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("لا يوجد جدول إهلاك.")

# ==========================================
# التبويب 5: التخلص من أصل
# ==========================================
with tab5:
    st.subheader("🗑️ التخلص من أصل ثابت")
    
    st.warning("""
    ⚠️ **تنبيه مهم:**
    - التخلص من الأصل يعني بيعه أو إعدامه
    - سيتم إنشاء قيد محاسبي تلقائياً
    - لا يمكن التراجع عن هذا الإجراء
    """)
    
    active_assets = db.query(FixedAsset).filter(FixedAsset.status == 'active').all()
    
    if not active_assets:
        st.info("لا توجد أصول نشطة للتخلص منها.")
    else:
        selected_asset_id = st.selectbox(
            "اختر أصلاً للتخلص منه:",
            options=[a.id for a in active_assets],
            format_func=lambda x: next((f"{a.code} - {a.name} (صافي القيمة: {a.net_book_value:,.2f})" for a in active_assets if a.id == x), x)
        )
        
        if selected_asset_id:
            selected_asset = db.query(FixedAsset).filter(FixedAsset.id == selected_asset_id).first()
            
            st.markdown(f"### 📄 تفاصيل الأصل المحدد")
            st.write(f"**الاسم:** {selected_asset.name}")
            st.write(f"**الكود:** {selected_asset.code}")
            st.write(f"**تكلفة الشراء:** {selected_asset.purchase_cost:,.2f} ج.م")
            st.write(f"**مجمع الإهلاك:** {selected_asset.accumulated_depreciation:,.2f} ج.م")
            st.write(f"**صافي القيمة الدفترية:** {selected_asset.net_book_value:,.2f} ج.م")
            
            st.markdown("---")
            st.markdown("### 💰 تفاصيل التخلص")
            
            disposal_date = st.date_input("تاريخ التخلص:", value=datetime.now().date())
            disposal_value = st.number_input("قيمة البيع/التخلص:", min_value=0.0, step=100.0, format="%.2f")
            disposal_notes = st.text_area("ملاحظات:")
            
            if disposal_value > 0:
                gain_loss = disposal_value - selected_asset.net_book_value
                if gain_loss > 0:
                    st.success(f"💰 ربح من التخلص: {gain_loss:,.2f} ج.م")
                elif gain_loss < 0:
                    st.error(f"📉 خسارة من التخلص: {gain_loss:,.2f} ج.م")
                else:
                    st.info("لا ربح ولا خسارة")
            
            if st.button("🗑️ التخلص من الأصل", type="secondary"):
                if st.checkbox("️ أؤكد أنني أفهم أن هذا الإجراء لا يمكن التراجع عنه"):
                    try:
                        disposal_datetime = datetime.combine(disposal_date, datetime.min.time())
                        result = dispose_asset(
                            asset_id=selected_asset_id,
                            disposal_date=disposal_datetime,
                            disposal_value=disposal_value,
                            notes=disposal_notes if disposal_notes else None,
                            created_by=current_user_id
                        )
                        
                        st.success(f"✅ تم التخلص من الأصل '{selected_asset.name}' بنجاح!")
                        if result['gain_loss'] != 0:
                            st.info(f"الربح/الخسارة: {result['gain_loss']:,.2f} ج.م")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")

db.close()