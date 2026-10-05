# session_auth.py
# تسجيل دخول دائم: يبقى المستخدم مسجلاً بعد Refresh (عبر Cookie + ملف جلسات)
# يتطلب Streamlit 1.37 أو أحدث (st.context.cookies)
import importlib
import json
import secrets
import time
from datetime import date, datetime
from enum import Enum
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

COOKIE_NAME = "techtoon_session"
SESSION_DAYS = 7
_STORE = Path(__file__).parent / ".sessions.json"


# ---------------------------------------------------------
# تحويل القيم الخاصة (Enum / datetime) من وإلى JSON
# حتى يعود قاموس المستخدم بنفس شكله الأصلي بعد Refresh
# ---------------------------------------------------------
def _encode(obj):
    if isinstance(obj, Enum):
        return {"__enum__": type(obj).__name__, "value": obj.value}
    if isinstance(obj, datetime):
        return {"__datetime__": obj.isoformat()}
    if isinstance(obj, date):
        return {"__date__": obj.isoformat()}
    return str(obj)


def _decode(d):
    if "__datetime__" in d:
        return datetime.fromisoformat(d["__datetime__"])
    if "__date__" in d:
        return date.fromisoformat(d["__date__"])
    if "__enum__" in d:
        try:
            cls = getattr(importlib.import_module("models"), d["__enum__"])
            return cls(d["value"])
        except Exception:
            return d["value"]
    return d


# ---------------------------------------------------------
# تخزين الجلسات (token -> بيانات المستخدم)
# ---------------------------------------------------------
def _load():
    try:
        data = json.loads(_STORE.read_text(encoding="utf-8"), object_hook=_decode)
    except Exception:
        return {}
    now = time.time()
    return {k: v for k, v in data.items() if v.get("expires", 0) > now}


def _save(data):
    _STORE.write_text(
        json.dumps(data, ensure_ascii=False, default=_encode), encoding="utf-8"
    )


# ---------------------------------------------------------
# التعامل مع الـ Cookie
# ---------------------------------------------------------
def _set_cookie(value, max_age):
    js = f"""
    var c = "{COOKIE_NAME}={value}; max-age={max_age}; path=/; SameSite=Lax";
    try {{ window.parent.document.cookie = c; }}
    catch (e) {{ document.cookie = c; }}
    """
    components.html(f"<script>{js}</script>", height=0)


def _read_cookie():
    try:
        return st.context.cookies.get(COOKIE_NAME)
    except Exception:
        return None


# ---------------------------------------------------------
# الدوال العامة
# ---------------------------------------------------------
def login_user(user):
    """استدعِها بعد نجاح التحقق من كلمة المرور."""
    token = secrets.token_urlsafe(32)
    data = _load()
    data[token] = {
        "user": user,
        "expires": time.time() + SESSION_DAYS * 86400,
    }
    _save(data)

    st.session_state.current_user = user
    st.session_state["_auth_token"] = token

    _set_cookie(token, SESSION_DAYS * 86400)
    time.sleep(1)  # نمهل المتصفح ليحفظ الـ Cookie قبل أي إعادة تشغيل


def restore_session():
    """تعيد المستخدم من الـ Cookie بعد Refresh. تُستدعى تلقائياً من render_sidebar."""
    if "current_user" in st.session_state:
        return True

    token = _read_cookie()
    if not token:
        return False

    entry = _load().get(token)
    if not entry:
        return False

    st.session_state.current_user = entry["user"]
    st.session_state["_auth_token"] = token
    return True


def logout_user():
    token = st.session_state.get("_auth_token") or _read_cookie()
    if token:
        data = _load()
        data.pop(token, None)
        _save(data)

    st.session_state.pop("current_user", None)
    st.session_state.pop("_auth_token", None)

    _set_cookie("", 0)  # max-age=0 يحذف الـ Cookie
    time.sleep(1)
