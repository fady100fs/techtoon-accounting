# pages/38_☁️_النسخ_السحابي.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sidebar import render_sidebar, can_modify, queue_state_updates
render_sidebar()

import streamlit as st
import pandas as pd
from datetime import datetime

from s3_backup import (
    init_s3_defaults,
    test_connection,
    upload_backup,
    list_backups,
    download_backup,
    delete_backup,
    cleanup_old_backups,
    get_s3_status,
    restore_from_zip,
)
from settings_manager import get_setting, set_setting, set_many_settings
from auth_required import require_login, get_current_user_id, get_current_user_name
from form_manager import clear_form, show_clear_hint

# ═══════════════════════════════════════════════════════════
# ✅ PFX: بادئة موحّدة لكل مفاتيح هذه الصفحة
# ═══════════════════════════════════════════════════════════
PFX = "s3_"


current_user = require_login()
current_user_id = get_current_user_id()
current_user_name = get_current_user_name()

st.set_page_config(page_title="النسخ السحابي", page_icon="☁️", layout="wide")
st.title("☁️ النسخ الاحتياطي السحابي")

show_clear_hint()  # 💡 الحقول ستُفرَّغ تلقائياً بعد كل عملية
st.info(f"👤 المستخدم: **{current_user_name}** | الدور: **{current_user['role'].value}**")

# تهيئة الإعدادات الافتراضية
try:
    init_s3_defaults()
except Exception:
    pass

is_readonly = not can_modify()


# ==========================================
# معلومات مزوّدي الخدمة
# ==========================================
with st.expander("💡 مزوّدو S3 مدعومون — اختر واحداً", expanded=False):
    st.markdown("""
    | المزوّد | المساحة المجانية | Endpoint URL | ملاحظات |
    |--------|------------------|--------------|---------|
    | **Backblaze B2** | 10 GB | `https://s3.us-east-005.backblazeb2.com` | ⭐ الأفضل |
    | **Supabase Storage** | 1 GB | `https://<project>.supabase.co/storage/v1/s3` | سهل |
    | **AWS S3** | 5 GB (12 شهر) | `https://s3.amazonaws.com` | مدفوع بعدها |
    | **Wasabi** | لا | `https://s3.wasabisys.com` | $6/TB |

    ### خطوات الإعداد (Backblaze B2):
    1. سجّل في [backblaze.com](https://www.backblaze.com/sign-up/cloud-storage)
    2. أنشئ Bucket جديد (Private)
    3. اذهب إلى **Application Keys** → **Add a New Application Key**
    4. انسخ: `keyID` و `applicationKey`
    5. من Bucket → **Endpoint**: انسخ URL
    6. الصقهم في النموذج أدناه
    """)


# ==========================================
# التبويبات
# ==========================================
tab_status, tab_config, tab_backup, tab_restore, tab_settings = st.tabs([
    "📊 الحالة",
    "⚙️ الإعدادات",
    "⬆️ رفع نسخة",
    "⬇️ الاستعادة",
    "🛠️ خيارات متقدمة",
])


# ==========================================
# التبويب 1: الحالة
# ==========================================
with tab_status:
    st.subheader("📊 حالة النظام السحابي")

    status = get_s3_status()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if status["boto3_available"]:
            st.metric("مكتبة boto3", "✅ جاهزة")
        else:
            st.metric("مكتبة boto3", "❌ ناقصة")
    with col2:
        st.metric("الحالة", "✅ مفعّل" if status["enabled"] else "⛔ معطّل")
    with col3:
        st.metric("Bucket", status["bucket"] or "—")
    with col4:
        st.metric("حد النسخ", status["max_backups"])

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 🔌 الإعدادات الحالية")
        st.write(f"**Endpoint:** `{status['endpoint'] or '—'}`")
        st.write(f"**Region:** `{status['region'] or '—'}`")
        st.write(f"**Prefix:** `{status['prefix'] or '—'}`")
        st.write(f"**بيانات الدخول:** {'✅ محفوظة' if status['credentials_set'] else '❌ غير محفوظة'}")

    with col_b:
        st.markdown("### 📅 آخر نسخة")
        if status["last_backup_at"]:
            try:
                last = datetime.fromisoformat(status["last_backup_at"])
                st.write(f"**التاريخ:** {last.strftime('%Y-%m-%d %H:%M')}")
                delta = datetime.now() - last
                hours = int(delta.total_seconds() / 3600)
                if hours < 24:
                    st.success(f"✅ آخر نسخة قبل {hours} ساعة")
                else:
                    st.warning(f"⚠️ آخر نسخة قبل {hours // 24} يوم")
            except Exception:
                st.write(status["last_backup_at"])
        else:
            st.warning("⚠️ لم يتم رفع أي نسخة بعد")

    if not status["boto3_available"]:
        st.error("""
        ❌ **مكتبة boto3 غير مثبتة!**
        
        أضف `boto3>=1.28.0` إلى `requirements.txt` ثم أعد النشر.
        """)

    # اختبار الاتصال
    st.markdown("---")
    if st.button("🔌 اختبار الاتصال", type="primary", use_container_width=True):
        with st.spinner("جاري الاتصال..."):
            ok, msg = test_connection()
        if ok:
            st.success(msg)
        else:
            st.error(msg)


# ==========================================
# التبويب 2: الإعدادات
# ==========================================
with tab_config:
    st.subheader("⚙️ إعدادات الاتصال بـ S3")

    if is_readonly:
        st.warning("⛔ تعديل الإعدادات متاح للمدير فقط.")

    with st.form("s3_config_form"):
        s3_enabled = st.checkbox(
            "تفعيل النسخ السحابي",
            value=get_setting("s3_enabled", False),
            key=f"{PFX}s3_cfg_enabled",
            disabled=is_readonly,
        )

        st.markdown("### 🔐 بيانات الاتصال")

        endpoint = st.text_input(
            "Endpoint URL:",
            value=get_setting("s3_endpoint_url", ""),
            placeholder="https://s3.us-east-005.backblazeb2.com",
            help="اتركه فارغاً لـ AWS S3",
            key=f"{PFX}s3_cfg_endpoint",
            disabled=is_readonly,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            region = st.text_input(
                "Region:",
                value=get_setting("s3_region", "us-east-1"),
                placeholder="us-east-005",
                key=f"{PFX}s3_cfg_region",
                disabled=is_readonly,
            )
        with col_b:
            bucket = st.text_input(
                "Bucket Name:",
                value=get_setting("s3_bucket", ""),
                placeholder="my-backup-bucket",
                key=f"{PFX}s3_cfg_bucket",
                disabled=is_readonly,
            )

        st.markdown("### 🔑 بيانات الدخول")

        col_c, col_d = st.columns(2)
        with col_c:
            access_key = st.text_input(
                "Access Key ID:",
                value=get_setting("s3_access_key", ""),
                type="default",
                key=f"{PFX}s3_cfg_access",
                disabled=is_readonly,
            )
        with col_d:
            secret_key = st.text_input(
                "Secret Access Key:",
                value=get_setting("s3_secret_key", ""),
                type="password",
                key=f"{PFX}s3_cfg_secret",
                disabled=is_readonly,
            )

        st.markdown("### 📁 مسار النسخ")

        prefix = st.text_input(
            "Prefix (بادئة المسار):",
            value=get_setting("s3_prefix", "techtoon-backups/"),
            help="مسار مجلد النسخ داخل الـ Bucket",
            key=f"{PFX}s3_cfg_prefix",
            disabled=is_readonly,
        )

        if st.form_submit_button(
            "💾 حفظ الإعدادات",
            type="primary",
            use_container_width=True,
            disabled=is_readonly,
        ):
            try:
                set_many_settings({
                    "s3_enabled": str(s3_enabled).lower(),
                    "s3_endpoint_url": endpoint.strip(),
                    "s3_region": region.strip() or "us-east-1",
                    "s3_bucket": bucket.strip(),
                    "s3_access_key": access_key.strip(),
                    "s3_secret_key": secret_key.strip(),
                    "s3_prefix": prefix.strip() or "techtoon-backups/",
                }, user_id=current_user_id)
                st.success("✅ تم حفظ الإعدادات.")
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()
            except Exception as e:
                st.error(f"❌ خطأ: {e}")

    # اختبار سريع
    st.markdown("---")
    if not is_readonly:
        col_x, col_y = st.columns([3, 1])
        with col_y:
            if st.button("🔌 اختبار الاتصال", use_container_width=True, key=f"{PFX}s3_test_btn"):
                with st.spinner("جاري الاختبار..."):
                    ok, msg = test_connection()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.info("""
    💡 **نصيحة:** بعد حفظ الإعدادات، اضغط **🔌 اختبار الاتصال** للتأكد من نجاح الربط.
    """)


# ==========================================
# التبويب 3: رفع نسخة
# ==========================================
with tab_backup:
    st.subheader("⬆️ رفع نسخة احتياطية جديدة")

    status = get_s3_status()

    if not status["enabled"]:
        st.warning("⛔ النسخ السحابي غير مفعّل. اذهب إلى تبويب **⚙️ الإعدادات**.")
    elif not status["credentials_set"]:
        st.warning("⚠️ بيانات الدخول غير محفوظة.")
    else:
        col_a, col_b = st.columns(2)
        with col_a:
            reason = st.selectbox(
                "السبب:",
                ["manual", "before_update", "before_restore", "daily", "weekly"],
                format_func=lambda x: {
                    "manual": "📝 يدوي",
                    "before_update": "🔄 قبل تحديث",
                    "before_restore": "↩️ قبل استعادة",
                    "daily": "📅 يومي",
                    "weekly": "📆 أسبوعي",
                }.get(x, x),
                key=f"{PFX}s3_backup_reason",
            )
        with col_b:
            st.write("")
            if st.button("⬆️ رفع نسخة الآن", type="primary", use_container_width=True):
                with st.spinner("جاري إنشاء ورفع النسخة... (قد يستغرق دقيقة)"):
                    ok, msg, info = upload_backup(reason=reason, created_by=current_user_id)

                if ok:
                    st.success(msg)
                    st.balloons()
                    st.markdown(f"""
                    **تفاصيل النسخة:**
                    - الملف: `{info['filename']}`
                    - الحجم: `{info['size_kb']:,.1f} KB`
                    - عدد الجداول: `{info['tables_count']}`
                    - إجمالي الصفوف: `{info['total_rows']:,}`
                    """)
                    clear_form(PFX)  # ✅ تفريغ الحقول
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("---")
        st.markdown("### 📋 النسخ السحابية المتاحة")

        with st.spinner("جاري جلب القائمة..."):
            backups = list_backups()

        if not backups:
            st.info("لا توجد نسخ سحابية بعد.")
        else:
            data = []
            for b in backups:
                data.append({
                    "الملف": b["filename"],
                    "الحجم": f"{b['size_kb']:,.1f} KB",
                    "التاريخ": b["last_modified"].strftime("%Y-%m-%d %H:%M") if hasattr(b["last_modified"], "strftime") else str(b["last_modified"])[:19],
                    "key": b["key"],
                })
            df = pd.DataFrame(data)
            st.dataframe(
                df.drop(columns=["key"]),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(f"📊 إجمالي: **{len(backups)}** نسخة")


# ==========================================
# التبويب 4: الاستعادة
# ==========================================
with tab_restore:
    st.subheader("⬇️ استعادة نسخة سحابية")

    status = get_s3_status()

    if not status["enabled"] or not status["credentials_set"]:
        st.warning("⛔ النسخ السحابي غير مفعّل أو بيانات الدخول ناقصة.")
    else:
        backups = list_backups()

        if not backups:
            st.info("لا توجد نسخ سحابية للاستعادة.")
        else:
            backup_opts = {
                b["key"]: f"{b['filename']} — {b['size_kb']:,.1f} KB — {b['last_modified'].strftime('%Y-%m-%d %H:%M')}"
                for b in backups
            }

            selected_key = st.selectbox(
                "اختر نسخة:",
                options=list(backup_opts.keys()),
                format_func=lambda x: backup_opts[x],
                key=f"{PFX}s3_restore_sel",
            )

            if selected_key:
                col_a, col_b = st.columns(2)

                # زر التنزيل
                with col_a:
                    st.markdown("### 📥 تنزيل فقط")
                    st.caption("لأخذ نسخة محلية بدون استعادة.")

                    if st.button("⬇️ تنزيل الملف", use_container_width=True, key=f"{PFX}s3_download_btn"):
                        with st.spinner("جاري التنزيل..."):
                            ok, msg, data = download_backup(selected_key)

                        if ok:
                            filename = selected_key.split("/")[-1]
                            st.success(f"✅ تم التنزيل: {filename}")
                            st.download_button(
                                label="⬇️ حفظ الملف",
                                data=data,
                                file_name=filename,
                                mime="application/zip",
                                key=f"{PFX}s3_download_file",
                            )
                        else:
                            st.error(msg)

                # زر الاستعادة
                with col_b:
                    st.markdown("### ⚠️ استعادة فعلية")
                    st.caption("⚠️ ستُضاف البيانات من النسخة إلى قاعدة البيانات الحالية.")

                    if not is_readonly:
                        st.warning("⚠️ الاستعادة عملية حساسة!")

                        confirm = st.checkbox(
                            "أؤكد أنني أريد الاستعادة",
                            key=f"{PFX}s3_restore_confirm",
                        )
                        dry_run = st.checkbox(
                            "وضع التجربة (بدون كتابة)",
                            value=True,
                            help="يعرض ما سيحدث دون تنفيذ",
                            key=f"{PFX}s3_restore_dry",
                        )

                        if st.button(
                            "🔄 استعادة",
                            type="primary",
                            disabled=not confirm,
                            use_container_width=True,
                            key=f"{PFX}s3_restore_btn",
                        ):
                            with st.spinner("جاري التنزيل والاستعادة..."):
                                ok, msg, data = download_backup(selected_key)

                                if not ok:
                                    st.error(msg)
                                else:
                                    report = restore_from_zip(data, dry_run=dry_run)

                                    if report["errors"]:
                                        st.error("⚠️ أخطاء:")
                                        for err in report["errors"][:5]:
                                            st.write(f"- {err}")

                                    st.success(
                                        f"✅ جداول مُعالجة: {len(report['tables_restored'])} | "
                                        f"صفوف: {report['rows_restored']:,} | "
                                        f"تخطي: {len(report['tables_skipped'])}"
                                    )

                                    if dry_run:
                                        st.info("💡 هذا كان **وضع تجربة**. لم يتم كتابة أي بيانات.")
                                    else:
                                        st.success("🎉 تمت الاستعادة الفعلية!")
                    else:
                        st.info("⛔ الاستعادة متاحة للمدير فقط.")


# ==========================================
# التبويب 5: خيارات متقدمة
# ==========================================
with tab_settings:
    st.subheader("🛠️ خيارات متقدمة")

    status = get_s3_status()

    with st.form("s3_advanced_form"):
        max_backups = st.number_input(
            "أقصى عدد نسخ محفوظة:",
            min_value=1, max_value=365,
            value=status["max_backups"],
            step=1,
            help="عند تجاوز هذا العدد، تُحذف الأقدم تلقائياً",
            key=f"{PFX}s3_max_backups",
            disabled=is_readonly,
        )

        auto_cleanup = st.checkbox(
            "حذف النسخ القديمة تلقائياً",
            value=status["auto_cleanup"],
            help="ينظف النسخ القديمة بعد كل رفع جديد",
            key=f"{PFX}s3_auto_cleanup",
            disabled=is_readonly,
        )

        if st.form_submit_button(
            "💾 حفظ",
            type="primary",
            use_container_width=True,
            disabled=is_readonly,
        ):
            try:
                set_many_settings({
                    "s3_max_backups": str(max_backups),
                    "s3_auto_cleanup": str(auto_cleanup).lower(),
                }, user_id=current_user_id)
                st.success("✅ تم الحفظ.")
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()
            except Exception as e:
                st.error(f"❌ {e}")

    st.markdown("---")

    # تنظيف يدوي
    st.markdown("### 🧹 تنظيف يدوي")
    st.caption("حذف النسخ الأقدم من الحد المحدد.")

    if not is_readonly:
        if st.button("🧹 تنظيف النسخ القديمة", use_container_width=True, key=f"{PFX}s3_cleanup_btn"):
            with st.spinner("جاري التنظيف..."):
                count, msg = cleanup_old_backups()
            if count > 0:
                st.success(msg)
                clear_form(PFX)  # ✅ تفريغ الحقول
                st.rerun()
            else:
                st.info(msg)

    st.markdown("---")

    # معلومات إضافية
    st.markdown("### 📊 معلومات النظام")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("boto3", "✅" if status["boto3_available"] else "❌")
    with col_b:
        st.metric("Bucket", status["bucket"] or "—")
    with col_c:
        st.metric("Prefix", status["prefix"] or "—")


# ==========================================
# تذييل
# ==========================================
st.markdown("---")
st.caption(
    f"🕐 آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
    f"👤 {current_user_name}"
)