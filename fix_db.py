import sys
sys.path.insert(0, ".")
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

# 1) رحّل فواتير INV- المتبقية
print("1) Migrating INV- invoices...")
rows = db.execute(text("SELECT id, invoice_number, type FROM invoices WHERE invoice_number LIKE 'INV-%' ORDER BY id")).fetchall()
print(f"   Found: {len(rows)}")

for r in rows:
    if r[2] == "sale":
        cnt = db.execute(text("SELECT COUNT(*) FROM invoices WHERE type='sale' AND invoice_number LIKE 'SAL-%'")).scalar()
        new = f"SAL-{cnt + 1:06d}"
    else:
        cnt = db.execute(text("SELECT COUNT(*) FROM invoices WHERE type='purchase' AND invoice_number LIKE 'PUR-%'")).scalar()
        new = f"PUR-{cnt + 1:06d}"
    
    db.execute(text("UPDATE invoices SET invoice_number = :n WHERE id = :i"), {"n": new, "i": r[0]})
    print(f"   {r[1]} -> {new}")

db.commit()

# 2) أصلح الأصناف بدون تصنيف
print("\n2) Fixing items without category...")
result = db.execute(text("UPDATE items SET category_id = 1 WHERE category_id IS NULL"))
updated = result.rowcount
db.commit()
print(f"   Updated: {updated} items")

# 3) تحقق
print("\n3) Verification:")
rows = db.execute(text("SELECT type, COUNT(*), MIN(invoice_number), MAX(invoice_number) FROM invoices GROUP BY type")).fetchall()
for r in rows:
    print(f"   {r[0]}: {r[1]} ({r[2]} .. {r[3]})")

inv_count = db.execute(text("SELECT COUNT(*) FROM invoices WHERE invoice_number LIKE 'INV-%'")).scalar()
print(f"\n   Remaining INV-: {inv_count}")

db.close()
print("\nDone!")