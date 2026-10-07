"""
النسخ الاحتياطي السحابي — Lazy imports.
"""

import streamlit as st
import os
from datetime import datetime
import io
import zipfile

st.set_page_config(page_title="النسخ السحابي", page_icon="☁️", layout="wide")

from feature_flags import s3_backup_enabled
if not s3_backup_enabled():
    st.warning("⚠️ ميزة النسخ السحابي غير مفعّلة في هذه النسخة.")
    st.stop()


# ============ Lazy Imports ============
def _load_boto3():
    import boto3
    from botocore.config import Config
    return boto3, Config


def get_s3_client():
    """إنشاء عميل S3 من الإعدادات."""
    boto3, Config = _load_boto3()

    endpoint = st.secrets.get("S3_ENDPOINT")
    access_key = st.secrets.get("S3_ACCESS_KEY")
    secret_key = st.secrets.get("S3_SECRET_KEY")
    region = st.secrets.get("S3_REGION", "us-east-1")

    if not all([endpoint, access_key, secret_key]):
        raise RuntimeError("إعدادات S3 غير مكتملة في secrets.toml")

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def list_backups():
    """عرض النسخ الموجودة."""
    s3 = get_s3_client()
    bucket = st.secrets.get("S3_BUCKET")
    resp = s3.list_objects_v2(Bucket=bucket, Prefix="backups/")
    return resp.get("Contents", [])


def upload_backup():
    """إنشاء ZIP ورفعه."""
    s3 = get_s3_client()
    bucket = st.secrets.get("S3_BUCKET")

    # إنشاء ZIP في الذاكرة
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", f"Backup {datetime.now().isoformat()}")
    buf.seek(0)

    key = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    s3.upload_fileobj(buf, bucket, key)
    return key


# ============ الواجهة ============
st.title("☁️ النسخ الاحتياطي السحابي")

if st.button("🔄 اختبار الاتصال"):
    try:
        s3 = get_s3_client()
        bucket = st.secrets.get("S3_BUCKET")
        s3.head_bucket(Bucket=bucket)
        st.success(f"✅ الاتصال ناجح — Bucket: {bucket}")
    except Exception as e:
        st.error(f"⚠️ فشل الاتصال: {e}")

if st.button("📤 رفع نسخة جديدة", type="primary"):
    try:
        with st.spinner("جارٍ الرفع..."):
            key = upload_backup()
        st.success(f"✅ تم الرفع: {key}")
    except Exception as e:
        st.error(f"⚠️ خطأ: {e}")

st.divider()
st.subheader("📋 النسخ الموجودة")
try:
    items = list_backups()
    if items:
        for obj in items:
            st.write(f"📦 {obj['Key']} — {obj['Size'] / 1024:.1f} KB")
    else:
        st.caption("لا توجد نسخ بعد.")
except Exception as e:
    st.warning(f"لم يتم تحميل القائمة: {e}")