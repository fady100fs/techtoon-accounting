# -*- coding: utf-8 -*-
"""تشخيص + تشغيل المزامنة من Neon إلى SQLite."""
import os
os.environ["DEPLOY_MODE"] = "local"

print("=" * 65)
print("  SQLite Mirror — تشخيص وتشغيل المزامنة")
print("=" * 65)
print()

# ═══ 1. فحص sync_manager ═══
print("[1] فحص sync_manager.py:")
try:
    import sync_manager
    print(f"    SYNC_INTERVAL = {sync_manager.SYNC_INTERVAL}")
    
    tables = sync_manager._get_sync_tables_in_order()
    print(f"    عدد الجداول المُزامَنة: {len(tables)}")
    for t in tables:
        print(f"      - {t.__name__:30s} → {t.__tablename__}")
except Exception as e:
    print(f"    [FAIL] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    raise SystemExit(1)

print()

# ═══ 2. حالة المزامنة الحالية ═══
print("[2] حالة المزامنة الحالية:")
state = sync_manager.get_sync_state()
for k, v in state.items():
    print(f"    {k:20s} = {v}")

print()

# ═══ 3. تشغيل المزامنة الكاملة ═══
print("[3] تشغيل full_sync() — انتظر 30-60 ثانية...")
print()
result = sync_manager.full_sync(verbose=True)
print()
print(f"    النتيجة: {result}")

print()

# ═══ 4. حالة المزامنة بعد ═══
print("[4] حالة المزامنة بعد:")
state = sync_manager.get_sync_state()
for k, v in state.items():
    print(f"    {k:20s} = {v}")

print()

# ═══ 5. فحص SQLite بعد المزامنة ═══
print("[5] فحص SQLite بعد المزامنة:")
from local_mirror import get_local_session
import models

db = get_local_session()
try:
    checks = [
        ("Item", "الأصناف"),
        ("Invoice", "الفواتير"),
        ("Party", "الأطراف"),
        ("Payment", "المدفوعات"),
        ("Account", "الحسابات"),
        ("AppSetting", "الإعدادات"),
        ("CashBox", "الخزائن"),
        ("Category", "التصنيفات"),
        ("JournalEntry", "القيود"),
    ]
    total = 0
    for name, label in checks:
        m = getattr(models, name, None)
        if m is None:
            print(f"    {label:15s} = [model مفقود]")
            continue
        try:
            count = db.query(m).count()
            total += count
            icon = "✅" if count > 0 else "❌"
            print(f"    {icon} {label:15s} = {count} سجل")
        except Exception as e:
            print(f"    [FAIL] {label}: {e}")
    print()
    print(f"    المجموع: {total} سجل")
finally:
    db.close()

print()
print("=" * 65)
if state.get("ok"):
    print("  ✅ المزامنة نجحت!")
else:
    print("  ❌ المزامنة فشلت — افحص الأخطاء أعلاه")
print("=" * 65)
