# pages/19_🏦_الخزائن.py
import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import func
from database import SessionLocal
import models
from models import CashBox, CashBoxType, CashTransfer
from services import create_cash_box, get_cash_box_balance, transfer_between_cash_boxes
from auth_required import require_login, get_current_user_id, get_current_user_name

# التحقق من تسجيل الدخول
current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الخزائن", page_icon="🏦", layout="wide")
st.title("🏦 إدارة الخزائن والحسابات البنكية")

st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

db = SessionLocal()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💰 أرصدة الخزائن",
    "➕ إضافة خزينة جديدة",
    " تحويل بين الخزائن",
    "️ تعديل/حذف الخزائن",
    "📋 سجل التحويلات"
])

# ==========================================
# التبويب 1: أرصدة الخزائن
# ==========================================
with tab1:
    st.subheader("📊 أرصدة الخزائن الحالية")
    
    cash_boxes = db.query(CashBox).all()
    
    if cash_boxes:
        # عرض البطاقات
        cols = st.columns(min(len(cash_boxes), 4))
        total_balance = 0.0
        
        for idx, box in enumerate(cash_boxes):
            if not box.is_active:
                continue
            
            balance = get_cash_box_balance(box.id)
            total_balance += balance
            
            col_idx = idx % 4
            with cols[col_idx]:
                type_icon = {"نقدية": "💵", "بنك": "🏦", "محفظة إلكترونية": "📱", "أخرى": "💼"}.get(box.type.value, "")
                st.metric(
                    f"{type_icon} {box.name}",
                    f"{balance:,.2f} ج.م",
                    help=f"الكود: {box.code} | النوع: {box.type.value}"
                )
        
        st.markdown("---")
        st.subheader("💰 إجمالي الأرصدة")
        st.metric("إجمالي جميع الخزائن", f"{total_balance:,.2f} ج.م")
        
        st.markdown("---")
        st.subheader("📋 تفاصيل الخزائن")
        
        data = []
        for box in cash_boxes:
            balance = get_cash_box_balance(box.id)
            account = db.query(models.Account).filter(models.Account.id == box.account_id).first()
            data.append({
                "الكود": box.code,
                "الاسم": box.name,
                "النوع": box.type.value,
                "الحساب المرتبط": account.name if account else "-",
                "المسؤول": box.responsible_person or "-",
                "الرصيد الحالي": f"{balance:,.2f} ج.م",
                "الحد الأقصى": f"{box.max_limit:,.2f}" if box.max_limit else "غير محدد",
                "الحالة": "✅ نشط" if box.is_active else "⛔ معطل"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ لا توجد خزائن مسجلة. يرجى إضافة خزينة جديدة من التبويب التالي.")

# ==========================================
# التبويب 2: إضافة خزينة جديدة
# ==========================================
with tab2:
    st.subheader("➕ إضافة خزينة جديدة")
    
    st.info("""
    💡 **ملاحظة مهمة:**
    كل خزينة يجب أن ترتبط بحساب في شجرة الحسابات.
    سيتم إنشاء الحساب تلقائياً تحت حساب "الأصول المتداولة".
    """)
    
    box_name = st.text_input("اسم الخزينة:", placeholder="مثال: الخزينة الرئيسية، بنك الأهلي...", key="new_box_name")
    box_code = st.text_input("كود الخزينة:", placeholder="مثال: CB001, BANK01...", key="new_box_code")
    
    box_type = st.selectbox(
        "نوع الخزينة:",
        options=[type.value for type in CashBoxType],
        format_func=lambda x: x,
        key="new_box_type"
    )
    
    responsible_person = st.text_input("الشخص المسؤول (اختياري):", placeholder="اسم أمين الصندوق...", key="new_box_responsible")
    max_limit = st.number_input("الحد الأقصى للرصيد (اختياري):", min_value=0.0, step=1000.0, key="new_box_max")
    notes = st.text_area("ملاحظات (اختياري):", key="new_box_notes")
    
    if st.button("💾 إنشاء الخزينة", type="primary"):
        if not box_name or not box_code:
            st.error("يرجى إدخال اسم وكود الخزينة")
        else:
            try:
                current_assets = db.query(models.Account).filter(
                    models.Account.code == "1100"
                ).first()
                
                if not current_assets:
                    assets_parent = db.query(models.Account).filter(
                        models.Account.code == "1000"
                    ).first()
                    if assets_parent:
                        current_assets = models.Account(
                            code="1100", name="الأصول المتداولة",
                            type=models.AccountType.ASSET, parent_id=assets_parent.id
                        )
                        db.add(current_assets)
                        db.commit()
                
                account_code = f"11{box_code.zfill(4)}"
                cash_account = models.Account(
                    code=account_code, name=box_name,
                    type=models.AccountType.ASSET,
                    parent_id=current_assets.id if current_assets else None
                )
                db.add(cash_account)
                db.commit()
                
                actual_type = next(t for t in CashBoxType if t.value == box_type)
                
                create_cash_box(
                    name=box_name, code=box_code, box_type=actual_type,
                    account_id=cash_account.id,
                    responsible_person=responsible_person if responsible_person else None,
                    max_limit=max_limit if max_limit > 0 else None,
                    notes=notes if notes else None,
                    created_by=current_user_id
                )
                
                st.success(f"✅ تم إنشاء الخزينة '{box_name}' بنجاح!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 3: تحويل بين الخزائن
# ==========================================
with tab3:
    st.subheader("🔄 تحويل مبلغ بين خزينتين")
    
    cash_boxes = db.query(CashBox).filter(CashBox.is_active == True).all()
    
    if len(cash_boxes) < 2:
        st.warning("⚠️ يجب وجود خزينتين نشطتين على الأقل لإجراء التحويل.")
    else:
        box_options = {box.id: f"{box.name} ({box.code})" for box in cash_boxes}
        
        col1, col2 = st.columns(2)
        
        with col1:
            from_box_id = st.selectbox(
                "من خزينة:",
                options=list(box_options.keys()),
                format_func=lambda x: box_options[x],
                key="from_box"
            )
            from_balance = get_cash_box_balance(from_box_id)
            st.info(f"💰 الرصيد الحالي: {from_balance:,.2f} ج.م")
        
        with col2:
            to_box_id = st.selectbox(
                "إلى خزينة:",
                options=list(box_options.keys()),
                format_func=lambda x: box_options[x],
                key="to_box"
            )
            to_balance = get_cash_box_balance(to_box_id)
            st.info(f"💰 الرصيد الحالي: {to_balance:,.2f} ج.م")
        
        transfer_amount = st.number_input("مبلغ التحويل:", min_value=0.01, step=100.0, key="transfer_amount")
        transfer_notes = st.text_area("ملاحظات التحويل (اختياري):", key="transfer_notes")
        
        if st.button("🔄 تنفيذ التحويل", type="primary"):
            if from_box_id == to_box_id:
                st.error("❌ لا يمكن التحويل بين نفس الخزينة!")
            elif transfer_amount <= 0:
                st.error("❌ يرجى إدخال مبلغ صحيح!")
            elif transfer_amount > from_balance:
                st.error(f" الرصيد غير كافٍ! الرصيد المتاح: {from_balance:,.2f} ج.م")
            else:
                try:
                    transfer_between_cash_boxes(
                        from_cash_box_id=from_box_id,
                        to_cash_box_id=to_box_id,
                        amount=transfer_amount,
                        notes=transfer_notes,
                        created_by=current_user_id
                    )
                    st.success(f"✅ تم التحويل بنجاح: {transfer_amount:,.2f} ج.م")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

# ==========================================
# التبويب 4: تعديل/حذف الخزائن (جديد)
# ==========================================
with tab4:
    st.subheader("⚙️ تعديل وحذف الخزائن")
    
    st.info("""
    💡 **ملاحظات مهمة:**
    - يمكن تعديل بيانات الخزينة في أي وقت
    - لا يمكن حذف الخزينة إذا كان لها رصيد أو تحويلات
    - يمكن تعطيل الخزينة بدلاً من حذفها
    """)
    
    cash_boxes = db.query(CashBox).all()
    
    if not cash_boxes:
        st.info("لا توجد خزائن للتعديل.")
    else:
        # اختيار الخزينة
        box_options = {box.id: f"{box.name} ({box.code}) - {box.type.value}" for box in cash_boxes}
        
        selected_box_id = st.selectbox(
            "اختر خزينة:",
            options=list(box_options.keys()),
            format_func=lambda x: box_options[x],
            key="select_box_edit"
        )
        
        if selected_box_id:
            selected_box = db.query(CashBox).filter(CashBox.id == selected_box_id).first()
            
            if selected_box:
                # عرض معلومات الخزينة الحالية
                st.markdown("---")
                st.markdown("### 📄 معلومات الخزينة الحالية")
                
                current_balance = get_cash_box_balance(selected_box.id)
                account = db.query(models.Account).filter(models.Account.id == selected_box.account_id).first()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("الرصيد الحالي", f"{current_balance:,.2f} ج.م")
                with col2:
                    st.metric("النوع", selected_box.type.value)
                with col3:
                    st.metric("الحالة", "نشط" if selected_box.is_active else "معطل")
                
                st.write(f"**الكود:** {selected_box.code}")
                st.write(f"**الحساب المرتبط:** {account.name if account else '-'}")
                st.write(f"**تاريخ الإنشاء:** {selected_box.created_at.strftime('%Y-%m-%d %H:%M') if selected_box.created_at else '-'}")
                
                st.markdown("---")
                
                # تبويبات فرعية للتعديل والحذف
                edit_tab1, edit_tab2 = st.columns(2)
                
                with edit_tab1:
                    st.markdown("### ✏️ تعديل بيانات الخزينة")
                    
                    new_name = st.text_input(
                        "الاسم الجديد:",
                        value=selected_box.name,
                        key=f"edit_name_{selected_box_id}"
                    )
                    
                    new_responsible = st.text_input(
                        "الشخص المسؤول:",
                        value=selected_box.responsible_person or "",
                        key=f"edit_responsible_{selected_box_id}"
                    )
                    
                    new_max_limit = st.number_input(
                        "الحد الأقصى:",
                        min_value=0.0,
                        value=float(selected_box.max_limit) if selected_box.max_limit else 0.0,
                        step=1000.0,
                        key=f"edit_max_{selected_box_id}"
                    )
                    
                    new_notes = st.text_area(
                        "ملاحظات:",
                        value=selected_box.notes or "",
                        key=f"edit_notes_{selected_box_id}"
                    )
                    
                    new_is_active = st.checkbox(
                        "الخزينة نشطة",
                        value=selected_box.is_active,
                        key=f"edit_active_{selected_box_id}"
                    )
                    
                    if st.button("💾 حفظ التعديلات", type="primary"):
                        try:
                            selected_box.name = new_name
                            selected_box.responsible_person = new_responsible if new_responsible else None
                            selected_box.max_limit = new_max_limit if new_max_limit > 0 else None
                            selected_box.notes = new_notes if new_notes else None
                            selected_box.is_active = new_is_active
                            
                            # تحديث اسم الحساب المرتبط أيضاً
                            if account:
                                account.name = new_name
                            
                            db.commit()
                            st.success(f"✅ تم تحديث الخزينة '{new_name}' بنجاح!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ خطأ في التعديل: {e}")
                
                with edit_tab2:
                    st.markdown("### 🗑️ إدارة الخزينة")
                    
                    # التحقق من وجود تحويلات
                    transfers_count = db.query(CashTransfer).filter(
                        (CashTransfer.from_cash_box_id == selected_box_id) |
                        (CashTransfer.to_cash_box_id == selected_box_id)
                    ).count()
                    
                    # التحقق من وجود مدفوعات
                    payments_count = db.query(models.Payment).filter(
                        models.Payment.cash_box_id == selected_box_id
                    ).count()
                    
                    st.write(f"**عدد التحويلات:** {transfers_count}")
                    st.write(f"**عدد المدفوعات:** {payments_count}")
                    
                    st.markdown("---")
                    
                    # زر التعطيل/التفعيل
                    if selected_box.is_active:
                        if st.button(" تعطيل الخزينة", type="secondary"):
                            if st.checkbox("تأكيد تعطيل الخزينة؟", key=f"confirm_disable_{selected_box_id}"):
                                try:
                                    selected_box.is_active = False
                                    db.commit()
                                    st.success(f"✅ تم تعطيل الخزينة '{selected_box.name}'")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ خطأ: {e}")
                    else:
                        if st.button("✅ تفعيل الخزينة", type="secondary"):
                            try:
                                selected_box.is_active = True
                                db.commit()
                                st.success(f"✅ تم تفعيل الخزينة '{selected_box.name}'")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")
                    
                    st.markdown("---")
                    
                    # زر الحذف
                    st.warning("️ **تحذير:** الحذف نهائي ولا يمكن التراجع عنه!")
                    
                    can_delete = True
                    delete_reasons = []
                    
                    if current_balance != 0:
                        can_delete = False
                        delete_reasons.append(f"الخزينة لها رصيد ({current_balance:,.2f} ج.م)")
                    
                    if transfers_count > 0:
                        can_delete = False
                        delete_reasons.append(f"الخزينة لها {transfers_count} عملية تحويل")
                    
                    if payments_count > 0:
                        can_delete = False
                        delete_reasons.append(f"الخزينة لها {payments_count} عملية دفع/قبض")
                    
                    if not can_delete:
                        st.error("❌ **لا يمكن حذف هذه الخزينة للأسباب التالية:**")
                        for reason in delete_reasons:
                            st.write(f"- {reason}")
                        st.info("💡 الحل: قم بتعطيل الخزينة بدلاً من حذفها")
                    else:
                        if st.button("🗑️ حذف الخزينة نهائياً", type="secondary"):
                            if st.checkbox("⚠️ أؤكد أنني أفهم أن هذا الإجراء لا يمكن التراجع عنه", key=f"confirm_delete_{selected_box_id}"):
                                try:
                                    # حذف الحساب المرتبط
                                    if account:
                                        db.delete(account)
                                    
                                    # حذف الخزينة
                                    db.delete(selected_box)
                                    db.commit()
                                    
                                    st.success(f"✅ تم حذف الخزينة '{selected_box.name}' بنجاح!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ خطأ في الحذف: {e}")

# ==========================================
# التبويب 5: سجل التحويلات
# ==========================================
with tab5:
    st.subheader(" سجل التحويلات بين الخزائن")
    
    transfers = db.query(CashTransfer).order_by(CashTransfer.date.desc()).all()
    
    if transfers:
        data = []
        for transfer in transfers:
            from_box = db.query(CashBox).filter(CashBox.id == transfer.from_cash_box_id).first()
            to_box = db.query(CashBox).filter(CashBox.id == transfer.to_cash_box_id).first()
            
            data.append({
                "التاريخ": transfer.date.strftime("%Y-%m-%d %H:%M") if transfer.date else "-",
                "من": from_box.name if from_box else "-",
                "إلى": to_box.name if to_box else "-",
                "المبلغ": f"{transfer.amount:,.2f} ج.م",
                "ملاحظات": transfer.notes or "-"
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        total_transferred = sum(t.amount for t in transfers)
        st.metric("إجمالي التحويلات", f"{total_transferred:,.2f} ج.م")
    else:
        st.info("لا توجد تحويلات مسجلة.")

db.close()