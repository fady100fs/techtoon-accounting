# fix_db.py - إصلاح خطأ column i.cash_box_id does not exist
import psycopg2

CS = "host=ep-bitter-night-za726w59-pooler.c-2.eu-west-2.aws.neon.tech port=5432 dbname=neondb user=neondb_owner password=npg_K9nHVkY5OjRC sslmode=require"

SQL = [
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS cash_box_id INTEGER",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS warehouse_id INTEGER",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS party_id INTEGER",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS subtotal NUMERIC(14,2) DEFAULT 0",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS discount_amount NUMERIC(14,2) DEFAULT 0",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS tax_amount NUMERIC(14,2) DEFAULT 0",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS total NUMERIC(14,2) DEFAULT 0",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS paid_amount NUMERIC(14,2) DEFAULT 0",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'draft'",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS notes TEXT",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()",
    "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()",
    "ALTER TABLE invoice_lines ADD COLUMN IF NOT EXISTS invoice_id INTEGER",
    "ALTER TABLE invoice_lines ADD COLUMN IF NOT EXISTS item_id INTEGER",
    "ALTER TABLE invoice_lines ADD COLUMN IF NOT EXISTS quantity NUMERIC(14,3) DEFAULT 0",
    "ALTER TABLE invoice_lines ADD COLUMN IF NOT EXISTS price NUMERIC(14,2) DEFAULT 0",
    "ALTER TABLE invoice_lines ADD COLUMN IF NOT EXISTS discount NUMERIC(14,2) DEFAULT 0",
    "ALTER TABLE invoice_lines ADD COLUMN IF NOT EXISTS total NUMERIC(14,2) DEFAULT 0",
    """CREATE TABLE IF NOT EXISTS invoice_payments (
        id SERIAL PRIMARY KEY,
        invoice_id INTEGER NOT NULL,
        method TEXT NOT NULL DEFAULT 'cash',
        amount NUMERIC(14,2) NOT NULL DEFAULT 0,
        reference TEXT,
        cash_box_id INTEGER,
        bank_account_id INTEGER,
        payment_date TIMESTAMP DEFAULT NOW(),
        notes TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_invoices_cash_box ON invoices(cash_box_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoice_payments_invoice ON invoice_payments(invoice_id)",
]

conn = psycopg2.connect(CS)
conn.autocommit = True
cur = conn.cursor()
ok = 0
for stmt in SQL:
    try:
        cur.execute(stmt)
        ok += 1
    except Exception as e:
        if "already exists" in str(e).lower():
            ok += 1
        else:
            print(f"WARN: {e}")
cur.close()
conn.close()
print(f"Done! {ok}/{len(SQL)} statements executed successfully.")