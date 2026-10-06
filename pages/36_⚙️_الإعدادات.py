# pages/36_⚙️_الإعدادات.py
import sys
import base64
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, queue_state_updates, can_modify
render_sidebar()

import streamlit as st
from datetime import datetime

from database import SessionLocal
import models
from settings_manager import (
    init_default_settings,
    get_setting, set_setting, set_many_settings,
    get_all_settings, get_settings_by_category,
    reset_category, reset_all_settings,
    get_company_info,
)
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "settings_"


current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="الإعدادات", page_icon="⚙️", layout="wide")
st.title("⚙️ إعدادات النظام")

show_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

# ✅ تهيئة الإعدادات الافتراضية عند أول زيارة
try:
    added = init_default_settings()
    if added > 0:
        st.toast(f"✅ تم إنشاء {added} إعداد افتراضي.")
except Exception as e:
    st.warning(f"⚠️ تعذّر تهيئة الإعدادات الافتراضية: {e}")


# ==========================================
# التحقق من الصلاحية
# ==========================================
if not can_modify():
    st.warning("⛔ تعديل الإعدادات متاح للمدير فقط.")
    st.info("يمكنك الاطلاع على الإعدادات لكن لا يمكنك تعديلها.")

is_readonly = not can_modify()


# ==========================================
# التبويبات
# ==========================================
tab_gen, tab_fin, tab_inv, tab_brand, tab_notif, tab_tools = st.tabs([
    "🏢 عام",
    "💰 مالية",
    "🧾 الفواتير",
    "🎨 الهوية",
    "🔔 التنبيهات",
    "🛠️ أدوات",
])


# ==========================================
# التبويب 1: عام
# ==========================================
with tab_gen:
    st.subheader("🏢 بيانات الشركة / المؤسسة")
    st.caption("💡 هذه البيانات ستظهر في الفواتير والتقارير المطبوعة.")

    with st.form("settings_general_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            company_name = st.text_input(
                "اسم الشركة *:",
                value=get_setting("company_name", ""),
                key=f"{PFX}gen_company_name",
                disabled=is_readonly,
            )
            company_address = st.text_area(
                "العنوان:",
                value=get_setting("company_address", ""),
                key=f"{PFX}gen_company_address",
                height=80,
                disabled=is_readonly,
            )
            company_phone = st.text_input(
                "الهاتف:",
                value=get_setting("company_phone", ""),
                key=f"{PFX}gen_company_phone",
                disabled=is_readonly,
            )
        with col_b:
            company_tagline = st.text_input(
                "الشعار النصي:",
                value=get_setting("company_tagline", ""),
                key=f"{PFX}gen_company_tagline",
                help="نص قصير يظهر أسفل اسم الشركة",
                disabled=is_readonly,
            )
            company_email = st.text_input(
                "البريد الإلكتروني:",
                value=get_setting("company_email", ""),
                key=f"{PFX}gen_company_email",
                disabled=is_readonly,
            )
            company_website = st.text_input(
                "الموقع الإلكتروني:",
                value=get_setting("company_website", ""),
                key=f"{PFX}gen_company_website",
                disabled=is_readonly,
            )
            company_tax_id = st.text_input(
                "الرقم الضريبي:",
                value=get_setting("company_tax_id", ""),
                key=f"{PFX}gen_company_tax_id",
                disabled=is_readonly,
            )

        if st.form_submit_button(
            "💾 حفظ البيانات",
            type="primary",
            use_container_width=True,
            disabled=is_readonly,
        ):
            if not company_name.strip():
                st.error("❌ اسم الشركة مطلوب.")
            else:
                try:
                    set_many_settings({
                        "company_name": company_name.strip(),
                        "company_tagline": company_tagline.strip(),
                        "company_address": company_address.strip(),
                        "company_phone": company_phone.strip(),
                        "company_email": company_email.strip(),
                        "company_website": company_website.strip(),
                        "company_tax_id": company_tax_id.strip(),
                    }, user_id=current_user_id)
                    st.success("✅ تم حفظ البيانات بنجاح.")
                    clear_form(PFX)  # ✅ تفريغ الحقول
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 2: مالية
# ==========================================
with tab_fin:
    st.subheader("💰 الإعدادات المالية الافتراضية")
    st.caption("💡 تُستخدم كقيم افتراضية في الفواتير والقيود الجديدة.")

    # جلب العملات
    db = SessionLocal()
    try:
        currencies = db.query(models.Currency).all()
        currency_opts = {c.id: f"{c.name} ({c.symbol})" for c in currencies}
    finally:
        db.close()

    if not currency_opts:
        st.warning("⚠️ لا توجد عملات! أضف عملة أولاً من صفحة العملات.")

    with st.form("settings_financial_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            current_curr_id = int(get_setting("default_currency_id", 1))
            if current_curr_id not in currency_opts:
                current_curr_id = list(currency_opts.keys())[0] if currency_opts else 1

            default_currency = st.selectbox(
                "العملة الافتراضية:",
                options=list(currency_opts.keys()) if currency_opts else [1],
                format_func=lambda x: currency_opts.get(x, "—"),
                index=list(currency_opts.keys()).index(current_curr_id) if currency_opts and current_curr_id in currency_opts else 0,
                key=f"{PFX}fin_currency",
                disabled=is_readonly,
            )

            default_tax = st.number_input(
                "نسبة الضريبة الافتراضية %:",
                min_value=0.0, max_value=100.0,
                value=float(get_setting("default_tax_rate", 14.0)),
                step=0.5, format="%.2f",
                key=f"{PFX}fin_tax",
                disabled=is_readonly,
            )

        with col_b:
            default_discount = st.number_input(
                "نسبة الخصم الافتراضية %:",
                min_value=0.0, max_value=100.0,
                value=float(get_setting("default_discount_rate", 0.0)),
                step=0.5, format="%.2f",
                key=f"{PFX}fin_discount",
                disabled=is_readonly,
            )

            fiscal_start = st.selectbox(
                "شهر بداية السنة المالية:",
                options=list(range(1, 13)),
                format_func=lambda x: [
                    "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
                    "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
                ][x - 1],
                index=int(get_setting("fiscal_year_start_month", 1)) - 1,
                key=f"{PFX}fin_fiscal",
                disabled=is_readonly,
            )

            decimals = st.number_input(
                "عدد المنازل العشرية:",
                min_value=0, max_value=4,
                value=int(get_setting("currency_decimal_places", 2)),
                step=1,
                key=f"{PFX}fin_decimals",
                disabled=is_readonly,
            )

        if st.form_submit_button(
            "💾 حفظ الإعدادات المالية",
            type="primary",
            use_container_width=True,
            disabled=is_readonly,
        ):
            try:
                set_many_settings({
                    "default_currency_id": str(default_currency),
                    "default_tax_rate": str(default_tax),
                    "default_discount_rate": str(default_discount),
                    "fiscal_year_start_month": str(fiscal_start),
                    "currency_decimal_places": str(decimals),
                }, user_id=current_user_id)
                st.success("✅ تم حفظ الإعدادات المالية.")
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 3: الفواتير
# ==========================================
with tab_inv:
    st.subheader("🧾 إعدادات الفواتير")
    st.caption("💡 تُستخدم كقيم افتراضية عند إنشاء فواتير جديدة.")

    with st.form("settings_invoice_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            inv_prefix = st.text_input(
                "بادئة رقم الفاتورة:",
                value=get_setting("invoice_prefix", "INV"),
                key=f"{PFX}inv_prefix",
                help="مثال: INV, BILL, SALE...",
                disabled=is_readonly,
            )
            inv_footer = st.text_area(
                "نص أسفل الفاتورة:",
                value=get_setting("invoice_footer_text", ""),
                key=f"{PFX}inv_footer",
                height=80,
                disabled=is_readonly,
            )
        with col_b:
            inv_terms = st.text_area(
                "الشروط والأحكام:",
                value=get_setting("invoice_terms", ""),
                key=f"{PFX}inv_terms",
                height=140,
                disabled=is_readonly,
            )
            inv_show_logo = st.checkbox(
                "إظهار الشعار في الفاتورة",
                value=get_setting("invoice_show_logo", True),
                key=f"{PFX}inv_show_logo",
                disabled=is_readonly,
            )

        if st.form_submit_button(
            "💾 حفظ إعدادات الفواتير",
            type="primary",
            use_container_width=True,
            disabled=is_readonly,
        ):
            try:
                set_many_settings({
                    "invoice_prefix": inv_prefix.strip() or "INV",
                    "invoice_footer_text": inv_footer.strip(),
                    "invoice_terms": inv_terms.strip(),
                    "invoice_show_logo": str(inv_show_logo).lower(),
                }, user_id=current_user_id)
                st.success("✅ تم حفظ إعدادات الفواتير.")
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

    # معاينة
    st.markdown("---")
    st.markdown("### 👁️ معاينة الفاتورة")

    company = get_company_info()
    preview_html = f"""
    <div style="border: 2px solid {company['primary_color']}; padding: 20px; border-radius: 10px; background: #fafafa; direction: rtl;">
        <div style="display: flex; justify-content: space-between; align-items: start; border-bottom: 2px solid {company['primary_color']}; padding-bottom: 12px; margin-bottom: 16px;">
            <div>
                <h2 style="color: {company['primary_color']}; margin: 0;">{company['name']}</h2>
                <p style="margin: 2px 0; opacity: 0.7; font-size: 12px;">{company['tagline']}</p>
            </div>
            <div style="text-align: left; font-size: 12px;">
                <p style="margin: 2px 0;">📞 {company['phone'] or '—'}</p>
                <p style="margin: 2px 0;">📧 {company['email'] or '—'}</p>
                <p style="margin: 2px 0;">📍 {company['address'] or '—'}</p>
                <p style="margin: 2px 0;">🧾 {company['tax_id'] or '—'}</p>
            </div>
        </div>
        <div style="text-align: center; padding: 20px; opacity: 0.5;">
            <p style="font-size: 20px; font-weight: bold;">
                {get_setting('invoice_prefix', 'INV')}-000001
            </p>
            <p style="font-size: 12px;">(معاينة فقط — لن تُنشأ فاتورة فعلية)</p>
        </div>
        <div style="border-top: 1px dashed #ccc; padding-top: 12px; text-align: center; font-size: 12px; opacity: 0.7;">
            {get_setting('invoice_footer_text', '') or '—'}
        </div>
    </div>
    """
    st.markdown(preview_html, unsafe_allow_html=True)


# ==========================================
# التبويب 4: الهوية
# ==========================================
with tab_brand:
    st.subheader("🎨 الهوية البصرية")

    with st.form("settings_brand_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            primary_color = st.color_picker(
                "اللون الأساسي:",
                value=get_setting("primary_color", "#2563eb"),
                key=f"{PFX}brand_color",
                disabled=is_readonly,
            )
        with col_b:
            st.markdown("**الشعار الحالي:**")
            logo_b64 = get_setting("company_logo_base64", "")
            if logo_b64:
                try:
                    st.markdown(
                        f'<img src="data:image/png;base64,{logo_b64}" style="max-height: 100px; border-radius: 8px;" />',
                        unsafe_allow_html=True,
                    )
                except Exception:
                    st.info("⚠️ الشعار موجود لكن تعذّر عرضه.")
            else:
                st.info("لا يوجد شعار. ارفع صورة.")

        if st.form_submit_button(
            "💾 حفظ اللون",
            type="primary",
            use_container_width=True,
            disabled=is_readonly,
        ):
            try:
                set_setting("primary_color", primary_color, user_id=current_user_id)
                st.success("✅ تم حفظ اللون.")
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

    # رفع الشعار
    st.markdown("---")
    st.markdown("### 🖼️ رفع شعار جديد")
    st.caption("💡 صيغ مدعومة: PNG, JPG, JPEG. الحجم الأقصى: 500 KB.")

    uploaded_logo = st.file_uploader(
        "اختر صورة الشعار:",
        type=['png', 'jpg', 'jpeg'],
        key=f"{PFX}brand_logo_upload",
        disabled=is_readonly,
    )

    if uploaded_logo:
        if uploaded_logo.size > 500 * 1024:
            st.error("❌ حجم الصورة أكبر من 500 KB. اضغط الصورة أولاً.")
        else:
            try:
                image_bytes = uploaded_logo.read()
                b64 = base64.b64encode(image_bytes).decode('utf-8')

                st.markdown("**معاينة:**")
                st.markdown(
                    f'<img src="data:image/png;base64,{b64}" style="max-height: 150px; border-radius: 8px; border: 2px solid #ddd;" />',
                    unsafe_allow_html=True,
                )

                if st.button(
                    "💾 حفظ الشعار",
                    type="primary",
                    use_container_width=True,
                    disabled=is_readonly,
                    key=f"{PFX}save_logo_btn",
                ):
                    set_setting("company_logo_base64", b64, user_id=current_user_id)
                    st.success("✅ تم حفظ الشعار.")
                    clear_form(PFX)  # ✅ تفريغ الحقول
                    st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ في قراءة الصورة: {e}")

    if logo_b64 and not is_readonly:
        st.markdown("---")
        if st.button("🗑 حذف الشعار", type="secondary", key=f"{PFX}del_logo_btn"):
            set_setting("company_logo_base64", "", user_id=current_user_id)
            st.success("✅ تم حذف الشعار.")
            clear_form(PFX)  # ✅ تفريغ الحقول
            st.rerun()


# ==========================================
# التبويب 5: التنبيهات
# ==========================================
with tab_notif:
    st.subheader("🔔 إعدادات التنبيهات")
    st.caption("💡 تحكم في التنبيهات التي تظهر في صفحة التنبيهات.")

    with st.form("settings_notif_form"):
        low_stock = st.checkbox(
            "تفعيل تنبيه المخزون المنخفض",
            value=get_setting("low_stock_alerts", True),
            key=f"{PFX}notif_low_stock",
            disabled=is_readonly,
        )

        overdue_days = st.number_input(
            "عدد الأيام لاعتبار الفاتورة متأخرة:",
            min_value=1, max_value=365,
            value=int(get_setting("overdue_invoice_days", 30)),
            step=1,
            key=f"{PFX}notif_overdue",
            disabled=is_readonly,
        )

        credit_limit = st.checkbox(
            "تفعيل تنبيه تجاوز حد الائتمان",
            value=get_setting("credit_limit_alerts", True),
            key=f"{PFX}notif_credit",
            disabled=is_readonly,
        )

        if st.form_submit_button(
            "💾 حفظ التنبيهات",
            type="primary",
            use_container_width=True,
            disabled=is_readonly,
        ):
            try:
                set_many_settings({
                    "low_stock_alerts": str(low_stock).lower(),
                    "overdue_invoice_days": str(overdue_days),
                    "credit_limit_alerts": str(credit_limit).lower(),
                }, user_id=current_user_id)
                st.success("✅ تم حفظ إعدادات التنبيهات.")
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")


# ==========================================
# التبويب 6: أدوات
# ==========================================
with tab_tools:
    st.subheader("🛠️ أدوات الإعدادات")

    if is_readonly:
        st.info("⛔ الأدوات متاحة للمدير فقط.")
    else:
        # ===== استعادة فئة =====
        st.markdown("### 🔄 استعادة الإعدادات الافتراضية")

        col_a, col_b = st.columns(2)
        with col_a:
            cat_to_reset = st.selectbox(
                "اختر فئة لاستعادتها:",
                options=["general", "financial", "invoice", "branding", "notifications"],
                format_func=lambda x: {
                    "general": "🏢 عام",
                    "financial": "💰 مالية",
                    "invoice": "🧾 الفواتير",
                    "branding": "🎨 الهوية",
                    "notifications": "🔔 التنبيهات",
                }.get(x, x),
                key=f"{PFX}reset_category_sel",
            )

            if st.button(
                f"🔄 استعادة {cat_to_reset}",
                use_container_width=True,
                key=f"{PFX}reset_cat_btn",
            ):
                count = reset_category(cat_to_reset, user_id=current_user_id)
                st.success(f"✅ تم استعادة {count} إعداد.")
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()

        with col_b:
            st.markdown("**⚠️ خطر:**")
            st.caption("استعادة **كل** الإعدادات للقيم الافتراضية.")

            confirm_all = st.checkbox(
                "أؤكد استعادة كل الإعدادات",
                key=f"{PFX}confirm_reset_all",
            )

            if st.button(
                "🔄 استعادة الكل",
                type="secondary",
                disabled=not confirm_all,
                use_container_width=True,
                key=f"{PFX}reset_all_btn",
            ):
                count = reset_all_settings(user_id=current_user_id)
                st.success(f"✅ تم استعادة {count} إعداد.")
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()

        st.markdown("---")

        # ===== تصدير / استيراد الإعدادات =====
        st.markdown("### 📤 تصدير / استيراد الإعدادات")

        col_x, col_y = st.columns(2)
        with col_x:
            if st.button("📤 تصدير الإعدادات JSON", use_container_width=True, key=f"{PFX}export_settings"):
                import json
                all_s = get_all_settings()
                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "settings": {
                        k: v["value"]
                        for k, v in all_s.items()
                    }
                }
                json_str = json.dumps(export_data, ensure_ascii=False, indent=2)

                st.download_button(
                    label="⬇️ تحميل الملف",
                    data=json_str.encode('utf-8'),
                    file_name=f"settings_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    key=f"{PFX}download_settings_json",
                )

        with col_y:
            uploaded_settings = st.file_uploader(
                "📥 استيراد إعدادات:",
                type=['json'],
                key=f"{PFX}import_settings_file",
            )
            if uploaded_settings:
                if st.button("📥 استيراد", type="primary", key=f"{PFX}import_settings_btn"):
                    try:
                        import json
                        data = json.loads(uploaded_settings.read().decode('utf-8'))
                        settings_to_import = data.get("settings", {})
                        count = set_many_settings(settings_to_import, user_id=current_user_id)
                        st.success(f"✅ تم استيراد {count} إعداد.")
                        clear_form(PFX)  # ✅ تفريغ الحقول
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")

        st.markdown("---")

        # ===== إحصاءات =====
        st.markdown("### 📊 معلومات النظام")
        all_settings = get_all_settings()

        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("إجمالي الإعدادات", len(all_settings))
        with col_s2:
            categories = set(v["category"] for v in all_settings.values())
            st.metric("عدد الفئات", len(categories))
        with col_s3:
            modified = sum(1 for v in all_settings.values() if v["updated_at"])
            st.metric("معدّلة يدوياً", modified)


# ==========================================
# تذييل
# ==========================================
st.markdown("---")
st.caption(
    f"🕐 آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    f"👤 {current_user_name}"
)