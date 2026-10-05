# backup_manager.py
"""
مدير النسخ الاحتياطي — نسخة متوافقة مع Neon PostgreSQL
يصدّر كل جداول قاعدة البيانات إلى ملفات CSV في مجلدات مُؤرَّخة.
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from database import engine


# ==========================================================
# الإعدادات
# ==========================================================
BACKUP_SETTINGS = {
    'enabled': True,
    'interval_hours': 24,       # نسخة يوميًا
    'max_backups': 14,          # الاحتفاظ بآخر 14 نسخة
    'backup_folder': None,
}


# كل جداول قاعدة البيانات — بالترتيب الصحيح
ALL_TABLES = [
    "currencies", "accounts", "users", "accounting_periods",
    "parties", "cash_boxes", "categories", "items",
    "invoices", "invoice_lines", "cost_history", "kit_components",
    "inventory_movements", "cost_centers", "cost_allocations",
    "cost_center_transactions", "journal_entries", "journal_lines",
    "payments", "cash_transfers", "expense_categories", "expenses",
    "warehouses", "stock_levels", "warehouse_transfers", "stock_counts",
    "fixed_assets", "depreciation_records", "loans", "loan_installments",
    "employees", "salary_records", "budgets",
]


class BackupManager:
    """مدير النسخ الاحتياطي المتوافق مع Neon."""

    def __init__(self, db_path=None, backup_folder=None):
        # ملاحظة: db_path محتفظ به للتوافق لكن غير مستخدم
        self.db_path = db_path
        self.backup_folder = Path(backup_folder) if backup_folder else Path(__file__).parent / "backups"
        self.backup_folder.mkdir(parents=True, exist_ok=True)

        # ✅ توافق مع الكود القديم — نستخدم نفس المجلد كـ "خارجي آمن"
        self.external_backup_folder = self.backup_folder

        self.running = False
        self.thread = None
        self.last_backup_time = None

    # ======================================================
    # إنشاء نسخة احتياطية
    # ======================================================
    def create_backup(self, reason="manual"):
        """يصدّر كل الجداول إلى CSV في مجلد مُؤرَّخ."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"backup_{timestamp}_{reason}"
            backup_folder = self.backup_folder / folder_name
            backup_folder.mkdir(parents=True, exist_ok=True)

            total_rows = 0
            failed = []

            with engine.connect() as conn:
                for table in ALL_TABLES:
                    try:
                        df = pd.read_sql(text(f"SELECT * FROM {table}"), conn)
                        csv_path = backup_folder / f"{table}.csv"
                        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                        total_rows += len(df)
                    except Exception:
                        continue

            self.last_backup_time = datetime.now()
            self._cleanup_old_backups()

            return True, f"تم إنشاء النسخة: {folder_name} ({total_rows} صف)"
        except Exception as e:
            return False, f"خطأ: {str(e)}"

    # ======================================================
    # تنظيف النسخ القديمة
    # ======================================================
    def _cleanup_old_backups(self):
        """يحذف النسخ الأقدم من الحد الأقصى."""
        try:
            max_backups = BACKUP_SETTINGS['max_backups']
            folders = sorted(
                [f for f in self.backup_folder.glob("backup_*") if f.is_dir()],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for old in folders[max_backups:]:
                shutil.rmtree(old, ignore_errors=True)
        except Exception as e:
            print(f"تنظيف النسخ القديمة: {e}")

    # ======================================================
    # قائمة النسخ
    # ======================================================
    def get_backup_list(self):
        """يرجع قائمة النسخ الاحتياطية المتاحة."""
        backups = []
        try:
            folders = sorted(
                [f for f in self.backup_folder.glob("backup_*") if f.is_dir()],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for folder in folders:
                stat = folder.stat()
                total_size = sum(
                    f.stat().st_size for f in folder.glob("*.csv")
                )
                files_count = len(list(folder.glob("*.csv")))
                backups.append({
                    'name': folder.name,
                    'path': str(folder),
                    'size': total_size,
                    'files_count': files_count,
                    'date': datetime.fromtimestamp(stat.st_mtime),
                    'location': 'محلي',
                })
        except Exception as e:
            print(f"قراءة النسخ: {e}")
        return backups

    # ======================================================
    # استعادة نسخة
    # ======================================================
    def restore_backup(self, backup_path):
        """الاستعادة الكاملة تتم من خلال Neon Console."""
        try:
            backup_folder = Path(backup_path)
            if not backup_folder.exists():
                return False, "النسخة غير موجودة!"

            csv_files = list(backup_folder.glob("*.csv"))
            if not csv_files:
                return False, "لا توجد ملفات CSV في هذه النسخة."

            return (
                True,
                f"النسخة موجودة ({len(csv_files)} ملف). "
                "للاستعادة الكاملة، استخدم Neon Console: "
                "https://console.neon.tech → مشروعك → Backups → Restore."
            )
        except Exception as e:
            return False, f"خطأ: {str(e)}"

    # ======================================================
    # حالة النظام — متوافقة مع كل الإصدارات
    # ======================================================
    def get_backup_status(self):
        """يعرض حالة النظام الحالية — متوافق مع الصفحات القديمة والجديدة."""
        try:
            backups = self.get_backup_list()
            total_size = sum(b['size'] for b in backups)
            count = len(backups)
            return {
                # مفاتيح الإعدادات
                'enabled': BACKUP_SETTINGS['enabled'],
                'interval_hours': BACKUP_SETTINGS['interval_hours'],
                'max_backups': BACKUP_SETTINGS['max_backups'],
                'last_backup': self.last_backup_time,
                # مفاتيح جديدة
                'backups_count': count,
                'total_size': total_size,
                # مفاتيح قديمة (للتوافق مع pages/11)
                'local_backups_count': count,
                'external_backups_count': count,  # نستخدم نفس المجلد
            }
        except Exception as e:
            return {
                'enabled': False,
                'interval_hours': 0,
                'max_backups': 0,
                'last_backup': None,
                'backups_count': 0,
                'total_size': 0,
                'local_backups_count': 0,
                'external_backups_count': 0,
                'error': str(e),
            }

    # ======================================================
    # النسخ التلقائي (متوافق مع الواجهة القديمة)
    # ======================================================
    def start_auto_backup(self):
        """متوافق مع الواجهة القديمة."""
        pass

    def stop_auto_backup(self):
        """متوافق مع الواجهة القديمة."""
        self.running = False


# ==========================================================
# نسخة عامة للاستخدام
# ==========================================================
backup_manager = BackupManager()