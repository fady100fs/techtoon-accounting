# settings_manager.py
"""
إدارة إعدادات التطبيق — مخزنة في قاعدة البيانات
+ طبقة Caching لتسريع الوصول
"""

import json
from datetime import datetime
from typing import Any, Optional

from database import SessionLocal
import models
from models import AppSetting


# ==========================================
# الإعدادات الافتراضية
# ==========================================
# البنية: key → (default_value, type, category, description)
DEFAULT_SETTINGS = {
    # ===== عام =====
    "company_name": ("شركتي", "text", "general", "اسم الشركة / المؤسسة"),
    "company_tagline": ("نظام محاسبة متكامل", "text", "general", "الشعار النصي"),
    "company_address": ("", "text", "general", "العنوان الكامل"),
    "company_phone": ("", "text", "general", "رقم الهاتف"),
    "company_email": ("", "text", "general", "البريد الإلكتروني"),
    "company_tax_id": ("", "text", "general", "الرقم الضريبي"),
    "company_website": ("", "text", "general", "الموقع الإلكتروني"),

    # ===== مالية =====
    "default_currency_id": ("1", "number", "financial", "معرّف العملة الافتراضية"),
    "default_tax_rate": ("14.0", "number", "financial", "نسبة الضريبة الافتراضية %"),
    "default_discount_rate": ("0.0", "number", "financial", "نسبة الخصم الافتراضية %"),
    "fiscal_year_start_month": ("1", "number", "financial", "شهر بداية السنة المالية"),
    "currency_decimal_places": ("2", "number", "financial", "عدد المنازل العشرية"),

    # ===== الفواتير =====
    "invoice_prefix": ("INV", "text", "invoice", "بادئة رقم الفاتورة"),
    "invoice_footer_text": ("شكراً لتعاملكم معنا", "text", "invoice", "نص أسفل الفاتورة"),
    "invoice_terms": ("", "text", "invoice", "الشروط والأحكام"),
    "invoice_show_logo": ("true", "bool", "invoice", "إظهار الشعار في الفاتورة"),

    # ===== الهوية =====
    "primary_color": ("#2563eb", "text", "branding", "اللون الأساسي"),
    "company_logo_base64": ("", "image", "branding", "شعار الشركة (Base64)"),

    # ===== التنبيهات =====
    "low_stock_alerts": ("true", "bool", "notifications", "تنبيه المخزون المنخفض"),
    "overdue_invoice_days": ("30", "number", "notifications", "أيام الفاتورة المتأخرة"),
    "credit_limit_alerts": ("true", "bool", "notifications", "تنبيه حد الائتمان"),

    # ===== النظام =====
    "system_version": ("1.0.0", "text", "system", "إصدار النظام"),
    "last_backup_at": ("", "text", "system", "آخر نسخة احتياطية"),
}


# ==========================================
# تهيئة الإعدادات الافتراضية
# ==========================================
def init_default_settings():
    """ينشئ الإعدادات الافتراضية إن لم تكن موجودة."""
    db = SessionLocal()
    try:
        existing_keys = {s.key for s in db.query(AppSetting).all()}
        added = 0

        for key, (value, s_type, cat, desc) in DEFAULT_SETTINGS.items():
            if key not in existing_keys:
                db.add(AppSetting(
                    key=key,
                    value=str(value),
                    setting_type=s_type,
                    category=cat,
                    description=desc,
                ))
                added += 1

        if added > 0:
            db.commit()
        return added
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ==========================================
# قراءة إعداد
# ==========================================
def get_setting(key: str, default: Any = None, cast: bool = True) -> Any:
    """يقرأ إعداد من قاعدة البيانات مع تحويل النوع.

    Args:
        key: مفتاح الإعداد
        default: القيمة الافتراضية إن لم يكن موجوداً
        cast: تحويل القيمة لنوعها الصحيح

    Returns:
        قيمة الإعداد (بعد التحويل)
    """
    db = SessionLocal()
    try:
        setting = db.query(AppSetting).filter(AppSetting.key == key).first()

        if not setting:
            # ارجع الافتراضي من DEFAULT_SETTINGS
            if key in DEFAULT_SETTINGS:
                return _cast_value(DEFAULT_SETTINGS[key][0], DEFAULT_SETTINGS[key][1]) if cast else DEFAULT_SETTINGS[key][0]
            return default

        if not cast:
            return setting.value

        return _cast_value(setting.value, setting.setting_type)
    finally:
        db.close()


def _cast_value(value: Any, setting_type: str) -> Any:
    """يحوّل القيمة من نص إلى نوعها الصحيح."""
    if value is None:
        return None
    if setting_type == "number":
        try:
            if "." in str(value):
                return float(value)
            return int(value)
        except (ValueError, TypeError):
            return 0
    elif setting_type == "bool":
        return str(value).lower() in ("true", "1", "yes", "on")
    elif setting_type == "json":
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return {}
    else:
        return str(value)


# ==========================================
# حفظ إعداد
# ==========================================
def set_setting(key: str, value: Any, user_id: Optional[int] = None, auto_init: bool = True) -> bool:
    """يحفظ إعداد.

    Args:
        key: مفتاح الإعداد
        value: القيمة الجديدة
        user_id: معرف المستخدم الذي عدّل
        auto_init: إنشاء السجل إن لم يكن موجوداً

    Returns:
        True عند النجاح
    """
    db = SessionLocal()
    try:
        setting = db.query(AppSetting).filter(AppSetting.key == key).first()

        # لو مش موجود، أنشئه
        if not setting:
            if not auto_init:
                return False

            if key in DEFAULT_SETTINGS:
                _, s_type, cat, desc = DEFAULT_SETTINGS[key]
            else:
                s_type, cat, desc = "text", "custom", None

            setting = AppSetting(
                key=key,
                value=str(value) if value is not None else "",
                setting_type=s_type,
                category=cat,
                description=desc,
            )
            db.add(setting)
        else:
            setting.value = str(value) if value is not None else ""
            setting.updated_at = datetime.now()
            if user_id:
                setting.updated_by = user_id

        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def set_many_settings(values_dict: dict, user_id: Optional[int] = None) -> int:
    """يحفظ عدة إعدادات دفعة واحدة."""
    db = SessionLocal()
    try:
        count = 0
        for key, value in values_dict.items():
            setting = db.query(AppSetting).filter(AppSetting.key == key).first()
            if setting:
                setting.value = str(value) if value is not None else ""
                setting.updated_at = datetime.now()
                if user_id:
                    setting.updated_by = user_id
                count += 1
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ==========================================
# قراءة كل الإعدادات
# ==========================================
def get_all_settings(category: Optional[str] = None) -> dict:
    """يرجع قاموس بكل الإعدادات (أو فئة معينة)."""
    db = SessionLocal()
    try:
        q = db.query(AppSetting)
        if category:
            q = q.filter(AppSetting.category == category)

        result = {}
        for s in q.all():
            result[s.key] = {
                "value": s.value,
                "cast_value": _cast_value(s.value, s.setting_type),
                "type": s.setting_type,
                "category": s.category,
                "description": s.description,
                "updated_at": s.updated_at,
                "updated_by": s.updated_by,
            }
        return result
    finally:
        db.close()


def get_settings_by_category() -> dict:
    """يرجع الإعدادات مجمّعة حسب الفئة."""
    all_s = get_all_settings()
    grouped = {}
    for key, data in all_s.items():
        cat = data["category"]
        if cat not in grouped:
            grouped[cat] = {}
        grouped[cat][key] = data
    return grouped


# ==========================================
# استعادة الافتراضي
# ==========================================
def reset_setting(key: str, user_id: Optional[int] = None) -> bool:
    """يستعيد إعداد لقيمته الافتراضية."""
    if key not in DEFAULT_SETTINGS:
        return False

    default_value = DEFAULT_SETTINGS[key][0]
    return set_setting(key, default_value, user_id)


def reset_category(category: str, user_id: Optional[int] = None) -> int:
    """يستعيد كل إعدادات فئة معينة."""
    count = 0
    for key, (value, _, cat, _) in DEFAULT_SETTINGS.items():
        if cat == category:
            set_setting(key, value, user_id)
            count += 1
    return count


def reset_all_settings(user_id: Optional[int] = None) -> int:
    """يستعيد كل الإعدادات للافتراضي."""
    count = 0
    for key, (value, _, _, _) in DEFAULT_SETTINGS.items():
        set_setting(key, value, user_id)
        count += 1
    return count


# ==========================================
# دوال مساعدة جاهزة للاستخدام
# ==========================================
def get_company_info() -> dict:
    """يرجع بيانات الشركة كقاموس (للاستخدام في PDF والفواتير)."""
    return {
        "name": get_setting("company_name", "شركتي"),
        "tagline": get_setting("company_tagline", ""),
        "address": get_setting("company_address", ""),
        "phone": get_setting("company_phone", ""),
        "email": get_setting("company_email", ""),
        "tax_id": get_setting("company_tax_id", ""),
        "website": get_setting("company_website", ""),
        "logo_base64": get_setting("company_logo_base64", ""),
        "primary_color": get_setting("primary_color", "#2563eb"),
    }


def get_financial_defaults() -> dict:
    """يرجع الإعدادات المالية الافتراضية (للفواتير الجديدة)."""
    return {
        "currency_id": int(get_setting("default_currency_id", 1)),
        "tax_rate": float(get_setting("default_tax_rate", 14.0)),
        "discount_rate": float(get_setting("default_discount_rate", 0.0)),
        "decimals": int(get_setting("currency_decimal_places", 2)),
    }


def get_invoice_defaults() -> dict:
    """يرجع إعدادات الفواتير الافتراضية."""
    return {
        "prefix": get_setting("invoice_prefix", "INV"),
        "footer": get_setting("invoice_footer_text", ""),
        "terms": get_setting("invoice_terms", ""),
        "show_logo": get_setting("invoice_show_logo", True),
    }


def get_notification_settings() -> dict:
    """يرجع إعدادات التنبيهات."""
    return {
        "low_stock": get_setting("low_stock_alerts", True),
        "overdue_days": int(get_setting("overdue_invoice_days", 30)),
        "credit_limit": get_setting("credit_limit_alerts", True),
    }