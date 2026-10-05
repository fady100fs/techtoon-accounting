# backup_manager.py
"""
مدير النسخ الاحتياطي التلقائي
يعمل في الخلفية ويحفظ نسخاً احتياطية تلقائياً
"""

import os
import shutil
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path

# إعدادات النسخ الاحتياطي
BACKUP_SETTINGS = {
    'enabled': True,
    'interval_hours': 1,  # نسخ كل ساعة
    'max_backups': 7,  # الاحتفاظ بـ 7 نسخ
    'backup_folder': None,  # سيتم تحديده تلقائياً
    'auto_backup_on_exit': True,  # نسخ عند الإغلاق
}


class BackupManager:
    """مدير النسخ الاحتياطي التلقائي"""
    
    def __init__(self, db_path=None, backup_folder=None):
        self.db_path = db_path or Path(__file__).parent / "accounting.db"
        self.backup_folder = backup_folder or Path(__file__).parent / "backups"
        self.backup_folder.mkdir(exist_ok=True)
        self.running = False
        self.thread = None
        self.last_backup_time = None
        
        # إنشاء مجلد آمن خارجي
        self.external_backup_folder = Path(__file__).parent.parent / "Techtoon_Backups"
        self.external_backup_folder.mkdir(exist_ok=True)
    
    def create_backup(self, reason="يدوي"):
        """إنشاء نسخة احتياطية"""
        try:
            if not self.db_path.exists():
                return False, "قاعدة البيانات غير موجودة!"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}_{reason}.db"
            
            # النسخ في المجلد المحلي
            local_backup = self.backup_folder / backup_name
            shutil.copy2(str(self.db_path), str(local_backup))
            
            # النسخ في المجلد الخارجي الآمن
            external_backup = self.external_backup_folder / backup_name
            shutil.copy2(str(self.db_path), str(external_backup))
            
            self.last_backup_time = datetime.now()
            
            # تنظيف النسخ القديمة
            self._cleanup_old_backups()
            
            return True, f"تم إنشاء نسخة احتياطية: {backup_name}"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def _cleanup_old_backups(self):
        """حذف النسخ القديمة والاحتفاظ بآخر 7 نسخ"""
        try:
            # النسخ المحلية
            local_backups = sorted(
                self.backup_folder.glob("backup_*.db"),
                key=os.path.getmtime,
                reverse=True
            )
            for backup in local_backups[self.backup_settings['max_backups']:]:
                backup.unlink()
            
            # النسخ الخارجية
            external_backups = sorted(
                self.external_backup_folder.glob("backup_*.db"),
                key=os.path.getmtime,
                reverse=True
            )
            for backup in external_backups[self.backup_settings['max_backups']:]:
                backup.unlink()
        except Exception as e:
            print(f"خطأ في تنظيف النسخ القديمة: {e}")
    
    def start_auto_backup(self):
        """بدء النسخ الاحتياطي التلقائي"""
        if not BACKUP_SETTINGS['enabled']:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._auto_backup_loop, daemon=True)
        self.thread.start()
    
    def stop_auto_backup(self):
        """إيقاف النسخ الاحتياطي التلقائي"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
    
    def _auto_backup_loop(self):
        """حلقة النسخ التلقائي"""
        interval = BACKUP_SETTINGS['interval_hours'] * 3600
        
        while self.running:
            try:
                success, message = self.create_backup("تلقائي")
                if success:
                    print(f"[{datetime.now()}] ✅ {message}")
                else:
                    print(f"[{datetime.now()}] ❌ {message}")
            except Exception as e:
                print(f"[{datetime.now()}] ❌ خطأ: {e}")
            
            # الانتظار حتى النسخة التالية
            for _ in range(int(interval)):
                if not self.running:
                    break
                time.sleep(1)
    
    def get_backup_list(self):
        """قائمة النسخ الاحتياطية المتاحة"""
        backups = []
        
        for backup_file in self.backup_folder.glob("backup_*.db"):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size': stat.st_size,
                'date': datetime.fromtimestamp(stat.st_mtime),
                'location': 'محلي'
            })
        
        for backup_file in self.external_backup_folder.glob("backup_*.db"):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size': stat.st_size,
                'date': datetime.fromtimestamp(stat.st_mtime),
                'location': 'خارجي آمن'
            })
        
        return sorted(backups, key=lambda x: x['date'], reverse=True)
    
    def restore_backup(self, backup_path):
        """استعادة نسخة احتياطية"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                return False, "ملف النسخة غير موجود!"
            
            # إنشاء نسخة من قاعدة البيانات الحالية قبل الاستعادة
            if self.db_path.exists():
                safety_backup = self.db_path.with_suffix('.db.before_restore')
                shutil.copy2(str(self.db_path), str(safety_backup))
            
            # استعادة النسخة
            shutil.copy2(str(backup_file), str(self.db_path))
            
            return True, "تمت الاستعادة بنجاح!"
        except Exception as e:
            return False, f"خطأ: {str(e)}"
    
    def get_backup_status(self):
        """حالة النسخ الاحتياطي"""
        return {
            'enabled': BACKUP_SETTINGS['enabled'],
            'interval_hours': BACKUP_SETTINGS['interval_hours'],
            'max_backups': BACKUP_SETTINGS['max_backups'],
            'last_backup': self.last_backup_time,
            'local_backups_count': len(list(self.backup_folder.glob("backup_*.db"))),
            'external_backups_count': len(list(self.external_backup_folder.glob("backup_*.db"))),
            'total_size': sum(
                f.stat().st_size 
                for f in self.backup_folder.glob("backup_*.db")
            )
        }


# إنشاء نسخة عامة من المدير
backup_manager = BackupManager()