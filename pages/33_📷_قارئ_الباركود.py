"""
قارئ الباركود — Barcode Scanner
Lazy imports لتسريع بدء التطبيق.
"""

import streamlit as st
from datetime import datetime

# ⭐ لا نستورد opencv أو pyzbar هنا — فقط داخل الدوال

st.set_page_config(page_title="قارئ الباركود", page_icon="📷", layout="wide")

# التحقق من تفعيل الميزة
from feature_flags import barcode_enabled
if not barcode_enabled():
    st.warning("⚠️ ميزة قارئ الباركود غير مفعّلة في هذه النسخة.")
    st.stop()


# ============ دوال الاستيراد المتأخر ============
def _load_cv2():
    import cv2
    return cv2


def _load_pyzbar():
    from pyzbar import pyzbar
    return pyzbar


def _load_pil():
    from PIL import Image
    return Image


# ============ منطق المسح ============
def decode_barcode_from_image(image_file):
    """فك الباركود من صورة مرفوعة."""
    try:
        cv2 = _load_cv2()
        pyzbar = _load_pyzbar()
        Image = _load_pil()

        img = Image.open(image_file).convert("RGB")
        import numpy as np
        img_array = np.array(img)

        barcodes = pyzbar.decode(img_array)
        if not barcodes:
            return None

        results = []
        for b in barcodes:
            results.append({
                "data": b.data.decode("utf-8"),
                "type": b.type,
            })
        return results
    except Exception as e:
        st.error(f"⚠️ خطأ في فك الباركود: {e}")
        return None


def decode_barcode_from_camera():
    """التقاط صورة من الكاميرا وفك الباركود."""
    try:
        cv2 = _load_cv2()
        pyzbar = _load_pyzbar()
        import numpy as np

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return None

        barcodes = pyzbar.decode(frame)
        if not barcodes:
            return None
        return [{"data": b.data.decode("utf-8"), "type": b.type} for b in barcodes]
    except Exception as e:
        st.error(f"⚠️ تعذّر الوصول للكاميرا: {e}")
        return None


# ============ الواجهة ============
st.title("📷 قارئ الباركود")
st.caption("امسح باركود صنف لإضافته بسرعة إلى الفاتورة أو للمخزون.")

tab1, tab2, tab3 = st.tabs(["📤 رفع صورة", "📸 الكاميرا", "✍️ إدخال يدوي"])

with tab1:
    st.subheader("رفع صورة تحتوي على باركود")
    uploaded = st.file_uploader("اختر صورة", type=["png", "jpg", "jpeg"])
    if uploaded is not None:
        st.image(uploaded, caption="الصورة المرفوعة", use_container_width=True)
        if st.button("🔍 قراءة الباركود", type="primary"):
            with st.spinner("جارٍ التحليل..."):
                results = decode_barcode_from_image(uploaded)
            if results:
                for r in results:
                    st.success(f"✅ {r['type']}: `{r['data']}`")
                    st.session_state.setdefault("scan_log", []).append({
                        "time": datetime.now().isoformat(),
                        "data": r["data"],
                        "type": r["type"],
                    })
            else:
                st.warning("⚠️ لم يُعثر على باركود في الصورة.")

with tab2:
    st.subheader("التقاط من كاميرا الجهاز")
    st.info("💡 يعمل بشكل أفضل على الموبايل. اسمح للمتصفح باستخدام الكاميرا.")
    if st.button("📸 التقاط ومسح"):
        with st.spinner("جارٍ فتح الكاميرا..."):
            results = decode_barcode_from_camera()
        if results:
            for r in results:
                st.success(f"✅ {r['type']}: `{r['data']}`")
        else:
            st.warning("⚠️ لم يُعثر على باركود، أو الكاميرا غير متاحة.")

with tab3:
    st.subheader("إدخال يدوي")
    manual_code = st.text_input("أدخل كود الباركود", key="barcode_manual")
    if st.button("➕ إضافة") and manual_code:
        st.session_state.setdefault("scan_log", []).append({
            "time": datetime.now().isoformat(),
            "data": manual_code,
            "type": "MANUAL",
        })
        st.success(f"✅ تم الإضافة: {manual_code}")

# ============ سجل المسح ============
st.divider()
st.subheader("📋 سجل المسح")
log = st.session_state.get("scan_log", [])
if log:
    st.dataframe(log[::-1], use_container_width=True)
    if st.button("🗑️ مسح السجل"):
        st.session_state["scan_log"] = []
        st.rerun()
else:
    st.caption("لا توجد عمليات مسح بعد.")