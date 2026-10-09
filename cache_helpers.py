# -*- coding: utf-8 -*-
"""
cache_helpers.py — TTL طويل محلياً، قصير سحابياً.
"""
import os
import streamlit as st


class TTL:
    VERY_SHORT = 30
    SHORT      = 120
    MEDIUM     = 300
    LONG       = 900
    VERY_LONG  = 3600


def _get_ttl():
    mode = os.getenv("DEPLOY_MODE", "cloud").lower()
    if mode == "local":
        return int(os.getenv("LOCAL_CACHE_TTL", "1800"))
    return int(os.getenv("CLOUD_CACHE_TTL", "120"))


CACHE_TTL = _get_ttl()


def _get_read_session():
    from database import get_read_session
    return get_read_session()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_items_with_stock(limit: int = 5000):
    """Items with all fields expected by pages."""
    import models
    from sqlalchemy import func, case

    db = _get_read_session()
    try:
        items = db.query(models.Item).limit(limit).all()
        if not items:
            return []

        cat_map = {}
        try:
            cat_map = {c.id: (c.name or "") for c in db.query(models.Category).all()}
        except Exception:
            pass

        stock_map = {}
        try:
            rows = db.query(
                models.InventoryMovement.item_id,
                func.sum(case(
                    (models.InventoryMovement.type == "in", models.InventoryMovement.quantity),
                    else_=-models.InventoryMovement.quantity
                )).label("balance")
            ).group_by(models.InventoryMovement.item_id).all()
            stock_map = {iid: float(b or 0) for iid, b in rows}
        except Exception:
            try:
                rows2 = db.query(
                    models.StockLevel.item_id,
                    func.coalesce(func.sum(models.StockLevel.quantity), 0)
                ).group_by(models.StockLevel.item_id).all()
                stock_map = {iid: float(q or 0) for iid, q in rows2}
            except Exception:
                pass

        result = []
        for r in items:
            item_id = getattr(r, "id", None)
            cat_id = getattr(r, "category_id", None)
            result.append({
                "id": item_id,
                "name": getattr(r, "name", "") or "",
                "code": getattr(r, "code", "") or "",
                "barcode": getattr(r, "barcode", "") or "",
                "category_id": cat_id,
                "category_name": cat_map.get(cat_id, "N/A"),
                "cost_price": float(getattr(r, "cost_price", 0) or 0),
                "sell_price": float(getattr(r, "sell_price", 0) or 0),
                "avg_cost_price": float(getattr(r, "avg_cost_price", 0) or 0),
                "is_kit": bool(getattr(r, "is_kit", False)),
                "min_stock": float(getattr(r, "min_stock", 0) or 0),
                "current_stock": float(stock_map.get(item_id, 0.0)),
                "total_purchased_qty": float(getattr(r, "total_purchased_qty", 0) or 0),
                "price": float(getattr(r, "sell_price", 0) or 0),
                "unit": getattr(r, "unit", "") or "",
            })
        return result
    finally:
        db.close()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_invoices_index(limit: int = 500):
    import models
    db = _get_read_session()
    try:
        rows = db.query(models.Invoice).order_by(models.Invoice.id.desc()).limit(limit).all()
        return [{
            "id": r.id,
            "number": getattr(r, "invoice_number", None) or getattr(r, "number", None),
            "date": getattr(r, "date", None),
            "party_id": getattr(r, "party_id", None),
            "total": float(getattr(r, "net_amount", 0) or getattr(r, "total_amount", 0) or 0),
            "type": getattr(r, "type", None),
            "status": getattr(r, "status", None),
        } for r in rows]
    finally:
        db.close()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_payments_index(limit: int = 500):
    import models
    db = _get_read_session()
    try:
        rows = db.query(models.Payment).order_by(models.Payment.id.desc()).limit(limit).all()
        return [{
            "id": r.id,
            "number": getattr(r, "reference_number", None),
            "date": getattr(r, "date", None),
            "party_id": getattr(r, "party_id", None),
            "amount": float(getattr(r, "amount", 0) or 0),
            "method": getattr(r, "payment_method", None),
            "type": getattr(r, "payment_type", None),
        } for r in rows]
    finally:
        db.close()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_dashboard_kpis():
    import models
    from sqlalchemy import func
    db = _get_read_session()
    try:
        kpis = {}
        kpis["invoices_count"] = db.query(func.count(models.Invoice.id)).scalar() or 0
        kpis["parties_count"]  = db.query(func.count(models.Party.id)).scalar() or 0
        kpis["items_count"]    = db.query(func.count(models.Item.id)).scalar() or 0
        total = db.query(func.coalesce(func.sum(models.Invoice.net_amount), 0)).scalar()
        kpis["invoices_total"] = float(total or 0)
        total_pay = db.query(func.coalesce(func.sum(models.Payment.amount), 0)).scalar()
        kpis["payments_total"] = float(total_pay or 0)
        return kpis
    finally:
        db.close()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_stock_map():
    import models
    from sqlalchemy import func, case
    db = _get_read_session()
    try:
        rows = db.query(
            models.InventoryMovement.item_id,
            func.sum(case(
                (models.InventoryMovement.type == "in", models.InventoryMovement.quantity),
                else_=-models.InventoryMovement.quantity
            )).label("balance")
        ).group_by(models.InventoryMovement.item_id).all()
        return {iid: float(b or 0) for iid, b in rows}
    finally:
        db.close()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_inventory_summary():
    import models
    from sqlalchemy import func
    db = _get_read_session()
    try:
        rows = db.query(
            models.StockLevel.warehouse_id,
            func.count(func.distinct(models.StockLevel.item_id)).label("items"),
            func.coalesce(func.sum(models.StockLevel.quantity), 0).label("total_qty"),
        ).group_by(models.StockLevel.warehouse_id).all()
        return [{
            "warehouse_id": r.warehouse_id,
            "items": int(r.items or 0),
            "total_qty": float(r.total_qty or 0),
        } for r in rows]
    finally:
        db.close()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_active_categories():
    """يرجع قائمة tuples: [(id, name), ...] — حسب ما تتوقعه الصفحات."""
    import models
    db = _get_read_session()
    try:
        rows = db.query(models.Category).order_by(models.Category.name).all()
        return [(r.id, (r.name or "")) for r in rows]
    finally:
        db.close()



def invalidate_cache():
    st.cache_data.clear()


def invalidate_and_sync():
    invalidate_cache()
    try:
        from database import is_local_mode
        if is_local_mode():
            import threading
            from sync_manager import full_sync
            threading.Thread(target=full_sync, daemon=True).start()
    except Exception:
        pass

# ===== Aliases for backward compatibility =====
def invalidate_all():
    """Alias for invalidate_cache (legacy name)."""
    return invalidate_cache()


def clear_all_cache():
    """Alias for invalidate_cache."""
    return invalidate_cache()


def clear_cache():
    """Alias for invalidate_cache."""
    return invalidate_cache()


def refresh_all():
    """Alias for invalidate_and_sync."""
    return invalidate_and_sync()
