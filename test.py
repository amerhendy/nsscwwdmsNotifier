import sys
import os
import sqlite3
import traceback
from datetime import datetime, timedelta
import pymssql
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA1
import base64
import re
import winreg
# ================== التشفير (نفس الأداة) ==================
DEFAULT_PASSWORD = "P@@Sw0rd"
DEFAULT_SALT = "S@LT&KEY"
DEFAULT_IV = "@1B2c3D4e5F6g7H8"
APP_VERSION = "1.0.0"
DB_VERSION = 1
def derive_key(password: str, salt: str, key_size_bytes: int = 32, iterations: int = 1000) -> bytes:
    return PBKDF2(
        password.encode('utf-8'),
        salt.encode('utf-8'),
        dkLen=key_size_bytes,
        count=iterations,
        hmac_hash_module=SHA1
    )

def zero_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    if pad_len == block_size:
        return data
    return data + b'\x00' * pad_len

def zero_unpad(data: bytes) -> bytes:
    return data.rstrip(b'\x00')

def encrypt_connection_string(plain_text: str) -> str:
    """تشفير النص بنفس طريقة الأداة."""
    key = derive_key(DEFAULT_PASSWORD, DEFAULT_SALT)
    iv_bytes = DEFAULT_IV.encode('utf-8')
    cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
    padded = zero_pad(plain_text.encode('utf-8'))
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_connection_string(encrypted_b64: str) -> str:
    """فك تشفير النص."""
    key = derive_key(DEFAULT_PASSWORD, DEFAULT_SALT)
    iv_bytes = DEFAULT_IV.encode('utf-8')
    cipher = AES.new(key, AES.MODE_CBC, iv_bytes)
    encrypted_bytes = base64.b64decode(encrypted_b64)
    decrypted = cipher.decrypt(encrypted_bytes)
    return zero_unpad(decrypted).decode('utf-8')

def parse_connection_string(conn_str: str):
    """استخراج الخادم، قاعدة البيانات، المستخدم، كلمة المرور من connection string."""
    data = {}
    for part in conn_str.split(';'):
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key.lower() in ['data source', 'server']:
                data['host'] = value
            elif key.lower() in ['initial catalog', 'database']:
                data['database'] = value
            elif key.lower() in ['user id', 'uid']:
                data['user'] = value
            elif key.lower() in ['password', 'pwd']:
                data['password'] = value
    return data

def build_connection_string(host, database, user, password):
    """بناء connection string من المكونات."""
    return f"Data Source={host};Initial Catalog={database};User ID={user};Password={password}"
# ================== إضافة دوال للتعامل مع التسجيل (Registry) في ويندوز ==================
def add_to_startup(app_name: str, app_path: str) -> bool:
    """إضافة البرنامج إلى مفتاح التشغيل التلقائي في ويندوز."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"❌ فشل إضافة البرنامج إلى Startup: {e}")
        return False

def remove_from_startup(app_name: str) -> bool:
    """حذف البرنامج من مفتاح التشغيل التلقائي."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        # القيمة غير موجودة أصلاً
        return True
    except Exception as e:
        print(f"❌ فشل حذف البرنامج من Startup: {e}")
        return False

def is_in_startup(app_name: str) -> bool:
    """التحقق مما إذا كان البرنامج مضافاً إلى التشغيل التلقائي."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        value, _ = winreg.QueryValueEx(key, app_name)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
# ================== دالة تحديد المسار ==================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# ================== تحديد مجلد التطبيق ==================
base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
APPDATA_DIR = os.path.join(base_dir, 'DMS_Notifier_Data')  
try:
    APPDATA_DIR = os.path.join(base_dir, 'DMS_Notifier_Data')  

    if not os.path.exists(APPDATA_DIR):
        os.makedirs(APPDATA_DIR, exist_ok=True)
except Exception:
    base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    APPDATA_DIR = os.path.join(base_dir, 'DMS_Notifier_Data')
    if not os.path.exists(APPDATA_DIR):
        os.makedirs(APPDATA_DIR, exist_ok=True)

LOCAL_DB_PATH = os.path.join(APPDATA_DIR, "dms_notifier.db")
year_ago = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

# ================== PyQt5 imports ==================
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QSystemTrayIcon,
    QMenu, QAction, QMessageBox, QDialog, QLineEdit, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QDateEdit,
    QGroupBox, QAbstractItemView, QFileDialog,QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, QDate, QEvent
from PyQt5.QtGui import QIcon, QColor, QPixmap, QPainter, QBrush, QClipboard

CHECK_INTERVAL_MS = 30 * 60 * 1000

# ================== استثناءات ==================
class SqlServerConnectionError(Exception):
    pass

# ================== اتصال SQL Server (ديناميكي) ==================
def get_sql_connection():
    """
    يتصل بـ SQL Server باستخدام بيانات الاتصال المخزنة مشفرة في قاعدة البيانات المحلية.
    """
    local_db = LocalDB()
    encrypted_conn_str = local_db.get_setting("db_conn_str")
    if not encrypted_conn_str:
        raise SqlServerConnectionError("لم يتم تكوين بيانات الاتصال بقاعدة البيانات.")

    try:
        conn_str = decrypt_connection_string(encrypted_conn_str)
    except Exception as e:
        raise SqlServerConnectionError(f"فشل فك تشفير بيانات الاتصال: {e}")

    settings = parse_connection_string(conn_str)
    host = settings.get('host')
    database = settings.get('database')
    user = settings.get('user')
    password = settings.get('password')

    if not all([host, database, user, password]):
        raise SqlServerConnectionError("بيانات الاتصال غير مكتملة بعد الفك.")

    try:
        conn = pymssql.connect(
            server=host,
            database=database,
            user=user,
            password=password,
            timeout=5
        )
        return conn
    except pymssql.OperationalError as e:
        raise SqlServerConnectionError(f"فشل الاتصال بقاعدة البيانات SQL Server:\n{str(e)}")
    except Exception as e:
        raise SqlServerConnectionError(f"خطأ غير متوقع أثناء الاتصال:\n{str(e)}")

# ================== قاعدة البيانات المحلية ==================
class LocalDB:
    def __init__(self, db_path=LOCAL_DB_PATH):
        self.db_path = db_path
        self._init_db()
        self._check_and_upgrade()


    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            # جدول الإصدارات (لتتبع إصدار قاعدة البيانات)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    updated_at TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS all_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    doc_id INTEGER NOT NULL,
                    doc_code TEXT,
                    subject TEXT,
                    sender_org TEXT,
                    receiver_org TEXT,
                    registration_date TEXT,
                    insert_date TEXT,
                    due_date TEXT,
                    year INTEGER,
                    is_late INTEGER,
                    is_closed INTEGER,
                    fetched_date TEXT,
                    UNIQUE(username, doc_id)
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_db_version(self):
        """استرجاع إصدار قاعدة البيانات الحالي، أو 0 إذا لم يكن موجوداً."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                return row[0]
            return 0
        except:
            return 0
        finally:
            conn.close()

    def _set_db_version(self, version):
        """تسجيل إصدار قاعدة البيانات الحالي."""
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO schema_version (version, updated_at) VALUES (?, ?)",
                (version, datetime.now().isoformat())
            )
            conn.commit()
        finally:
            conn.close()

    def _upgrade_db(self, current_version):
        """ترقية قاعدة البيانات من الإصدار الحالي إلى الإصدار المطلوب."""
        if current_version >= DB_VERSION:
            return  # لا حاجة للترقية

        print(f"⚠️ ترقية قاعدة البيانات من الإصدار {current_version} إلى {DB_VERSION}")
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            # تنفيذ التغييرات لكل إصدار
            if current_version < 1:
                # الإصدار 1 هو الإصدار الأولي (لا حاجة لتغيير، فقط نسجل)
                pass
            # إذا أضفنا إصدار 2 في المستقبل:
            # if current_version < 2:
            #     cur.execute("ALTER TABLE all_notifications ADD COLUMN new_column TEXT")
            #     print("✅ تمت ترقية الجدول all_notifications بإضافة عمود new_column")

            # حفظ الإصدار الجديد
            self._set_db_version(DB_VERSION)
            conn.commit()
            print(f"✅ تمت ترقية قاعدة البيانات إلى الإصدار {DB_VERSION}")
        except Exception as e:
            print(f"❌ فشل ترقية قاعدة البيانات: {e}")
            raise
        finally:
            conn.close()

    def _check_and_upgrade(self):
        """التحقق من الإصدار وتشغيل الترقية إذا لزم الأمر."""
        current = self._get_db_version()
        if current < DB_VERSION:
            self._upgrade_db(current)

    def get_setting(self, key, default=None):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default
        finally:
            conn.close()

    def set_setting(self, key, value):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, str(value)))
            conn.commit()
        finally:
            conn.close()

    def get_connection_settings(self):
        """استرجاع إعدادات الاتصال (كائن يحتوي على host, database, user, password)."""
        encrypted = self.get_setting("db_conn_str")
        if not encrypted:
            return None
        try:
            conn_str = decrypt_connection_string(encrypted)
            return parse_connection_string(conn_str)
        except Exception:
            return None

    def save_connection_settings(self, host, database, user, password):
        """حفظ إعدادات الاتصال مشفرة (ك connection string)."""
        conn_str = build_connection_string(host, database, user, password)
        encrypted = encrypt_connection_string(conn_str)
        self.set_setting("db_conn_str", encrypted)

    def get_current_user(self):
        return self.get_setting("current_user")

    def set_current_user(self, username):
        self.set_setting("current_user", username)

    def get_last_check(self, username):
        val = self.get_setting(f"last_check::{username}")
        if val:
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                return None
        return None

    def set_last_check(self, username, dt):
        self.set_setting(f"last_check::{username}", dt.isoformat())

    def save_notifications(self, username, documents):
        conn = self._get_conn()
        new_items = []
        try:
            cur = conn.cursor()
            fetched_date = datetime.now().isoformat()
            for doc in documents:
                try:
                    cur.execute("""
                        INSERT INTO all_notifications (
                            username, doc_id, doc_code, subject, sender_org,
                            receiver_org, insert_date, due_date,
                            year, is_late, is_closed, fetched_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        username,
                        doc["doc_id"],
                        doc["doc_code"],
                        doc["subject"],
                        doc["sender_org"],
                        doc["receiver_org"],
                        str(doc["insert_date"]) if doc["insert_date"] else None,
                        str(doc["insert_date"]) if doc["insert_date"] else None,
                        doc["year"],
                        int(doc["is_late"]),
                        int(doc["is_closed"]),
                        fetched_date,
                    ))
                    new_items.append(doc)
                except sqlite3.IntegrityError:
                    continue
            conn.commit()
        finally:
            conn.close()
        return new_items

    def get_all_notifications(self, username):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM all_notifications
                WHERE username = ?
                ORDER BY insert_date DESC
            """, (username,))
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_latest_notifications(self, username, limit=5):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM all_notifications
                WHERE username = ?
                ORDER BY insert_date DESC
                LIMIT ?
            """, (username, limit))
            return [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def get_distinct_sender_orgs(self, username):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT DISTINCT sender_org FROM all_notifications
                WHERE username = ? AND sender_org IS NOT NULL AND sender_org != ''
                ORDER BY sender_org
            """, (username,))
            return [row["sender_org"] for row in cur.fetchall()]
        finally:
            conn.close()
    
    def get_startup_setting(self) -> bool:
        """استرجاع إعداد التشغيل التلقائي."""
        val = self.get_setting("run_at_startup")
        return val.lower() == "true" if val else False

    def set_startup_setting(self, enabled: bool):
        """حفظ إعداد التشغيل التلقائي."""
        self.set_setting("run_at_startup", "true" if enabled else "false")


# ================== أيقونات الحالة ==================
def make_status_icon(color):
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, 16, 16)
    painter.end()
    return QIcon(pixmap)

def load_app_icon():
    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.blue)
    return QIcon(pixmap)

# ================== نافذة إعدادات الاتصال (مع دعم تحميل ملف) ==================
class ConnectionSettingsDialog(QDialog):
    def __init__(self, parent=None, initial_settings=None):
        super().__init__(parent)
        self.setWindowTitle("إعدادات الاتصال بقاعدة البيانات")
        self.setWindowIcon(load_app_icon())
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(450)

        layout = QFormLayout(self)

        # صف تحميل الملف المشفر
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("اختر ملف نصي يحتوي على connection string مشفرة")
        self.file_browse_btn = QPushButton("استعراض ملف الاتصال المشفر")
        self.file_browse_btn.clicked.connect(self.browse_file)
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.file_browse_btn)
        layout.addRow("تحميل من ملف مشفر:", file_layout)

        # حقول الإدخال اليدوي
        self.host_edit = QLineEdit()
        self.db_edit = QLineEdit()
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)

        if initial_settings:
            self.host_edit.setText(initial_settings.get('host', ''))
            self.db_edit.setText(initial_settings.get('database', ''))
            self.user_edit.setText(initial_settings.get('user', ''))
            self.pass_edit.setText(initial_settings.get('password', ''))

        layout.addRow("الخادم (Server):", self.host_edit)
        layout.addRow("قاعدة البيانات (Database):", self.db_edit)
        layout.addRow("اسم المستخدم (User):", self.user_edit)
        layout.addRow("كلمة المرور (Password):", self.pass_edit)

        # أزرار التحكم
        btn_layout = QHBoxLayout()
        self.test_btn = QPushButton("اختبار الاتصال")
        self.save_btn = QPushButton("حفظ")
        self.cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(self.test_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

        self.test_btn.clicked.connect(self.test_connection)
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def browse_file(self):
        """فتح ملف نصي يحتوي على connection string مشفرة، وفك تشفيرها وملء الحقول."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "اختر ملف الاتصال المشفر", "",
            "Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return
        self.file_path_edit.setText(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                encrypted_text = f.read().strip()
            # فك التشفير
            decrypted = decrypt_connection_string(encrypted_text)
            settings = parse_connection_string(decrypted)
            # ملء الحقول
            self.host_edit.setText(settings.get('host', ''))
            self.db_edit.setText(settings.get('database', ''))
            self.user_edit.setText(settings.get('user', ''))
            self.pass_edit.setText(settings.get('password', ''))
            QMessageBox.information(self, "تم التحميل", "تم تحميل بيانات الاتصال من الملف بنجاح.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل قراءة أو فك تشفير الملف:\n{str(e)}")

    def get_settings(self):
        return {
            'host': self.host_edit.text().strip(),
            'database': self.db_edit.text().strip(),
            'user': self.user_edit.text().strip(),
            'password': self.pass_edit.text().strip(),
        }

    def test_connection(self):
        settings = self.get_settings()
        if not all(settings.values()):
            QMessageBox.warning(self, "تنبيه", "الرجاء ملء جميع الحقول.")
            return
        try:
            conn = pymssql.connect(
                server=settings['host'],
                database=settings['database'],
                user=settings['user'],
                password=settings['password'],
                timeout=5
            )
            conn.close()
            QMessageBox.information(self, "نجاح", "تم الاتصال بنجاح.")
        except Exception as e:
            QMessageBox.critical(self, "فشل الاتصال", str(e))

# ================== دوال جلب البيانات من SQL Server ==================
def fetch_account_ids(username):
    query = """
        SELECT a.EmpID, a.PersonID, a.IsActive, a.OrganizationID
        FROM Accounts a
        WHERE a.UserName = %s
    """
    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, (username,))
        row = cursor.fetchone()
        if row is None:
            return None
        return (row[0], row[1], bool(row[2]), row[3])
    finally:
        conn.close()

def get_docs_ids_from_signatures(user_id=None, manager_id=None, OrganizationID=None):
    if user_id is None and manager_id is None:
        return []

    conditions = []
    params = []

    if manager_id is not None:
        conditions.append("PersonID = %s")
        params.append(manager_id)
        conditions.append("PersonIDFrom = %s")
        params.append(manager_id)

    if user_id is not None:
        conditions.append("EmpID = %s")
        params.append(user_id)

    if OrganizationID is not None:
        conditions.append("OrganizationFrom = %s")
        params.append(OrganizationID)
        conditions.append("OrganizationID = %s")
        params.append(OrganizationID)
        conditions.append("OrganizationID = %s")
        params.append(OrganizationID)

    where_clause = " OR ".join(conditions)

    sql = f"""
        SELECT DISTINCT DocumentID
        FROM Signatures
        WHERE {where_clause}
        ORDER BY DocumentID
    """

    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"❌ خطأ في جلب DocumentIDs من Signatures: {e}")
        return []
    finally:
        conn.close()

def get_docs_ids_from_documents(user_id=None, manager_id=None, OrganizationID=None):
    if user_id is None and manager_id is None:
        return []

    conditions = []
    params = []

    if user_id is not None:
        conditions.append("EmpID = %s")
        params.append(user_id)
        
    if manager_id is not None:
        conditions.append("PersonID = %s")
        params.append(manager_id)

    if OrganizationID is not None:
        conditions.append("OrganizationID = %s")
        params.append(OrganizationID)
        conditions.append("SenderOrganizationID = %s")
        params.append(OrganizationID)
        conditions.append("Owner = %s")
        params.append(OrganizationID)
        conditions.append("Owner = %s")
        params.append(OrganizationID)

    where_clause = " OR ".join(conditions)

    sql = f"""
        SELECT DISTINCT DocumentID
        FROM Documents
        WHERE ({where_clause})
          AND (
              (DocumentTypeID = 1 AND DocumentDirectionID = 1)
              OR DocumentTypeID = 2
          )
        ORDER BY DocumentID
    """

    conn = get_sql_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [row[0] for row in rows]
    except Exception as e:
        print(f"❌ خطأ في جلب DocumentIDs من Documents: {e}")
        return []
    finally:
        conn.close()

def fetch_documents_with_details(user_id, manager_id, last_check_time=None, OrganizationID=None):
    signaturesIDS = get_docs_ids_from_signatures(user_id, manager_id, OrganizationID)
    documentsIDS = get_docs_ids_from_documents(user_id, manager_id, OrganizationID)
    merged = list(dict.fromkeys(signaturesIDS + documentsIDS))
    return get_documents_info_by_ids(merged)

def get_documents_info_by_ids(doc_ids, date_from=year_ago, include_org_names=True, chunk_size=1000):
    if not doc_ids:
        return []

    all_results = []

    for i in range(0, len(doc_ids), chunk_size):
        chunk = doc_ids[i:i+chunk_size]
        placeholders = ','.join(['%s'] * len(chunk))
        params = list(chunk)

        sql = f"""
            SELECT 
                d.DocumentID,
                d.DocumentCode,
                d.Subject,
                d.InsertDate,
                d.ImportanceLevelDate,
                d.year,
                d.Cloesd
        """

        if include_org_names:
            sql += """,
                so.OrganizationName AS SenderOrg,
                ro.OrganizationName AS ReceiverOrg
            """

        sql += f"""
            FROM Documents d
        """

        if include_org_names:
            sql += """
                LEFT JOIN Organizations so ON d.SenderOrganizationID = so.OrganizationID
                LEFT JOIN Organizations ro ON d.OrganizationID = ro.OrganizationID
            """

        sql += f"""
            WHERE d.DocumentID IN ({placeholders})
              AND d.Cloesd = 0
              AND d.year BETWEEN YEAR(GETDATE()) - 1 AND YEAR(GETDATE()) + 1
        """

        if date_from is not None:
            sql += " AND d.InsertDate >= %s"
            params.append(date_from)
        else:
            sql += " AND d.InsertDate >= DATEADD(year, -1, GETDATE())"

        sql += " ORDER BY d.InsertDate DESC"

        conn = get_sql_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            results = []
            now = datetime.now()
            for row in rows:
                record = dict(zip(columns, row))
                InsertDate = record.get("InsertDate")
                #is_late = bool(InsertDate and InsertDate < now)
                late_days = (now - InsertDate).days if (InsertDate and InsertDate < now) else 0
                is_late = bool(late_days > 2)
                results.append({
                    "doc_id": record.get("DocumentID"),
                    "doc_code": record.get("DocumentCode"),
                    "subject": record.get("Subject"),
                    "sender_org": record.get("SenderOrg") or "",
                    "receiver_org": record.get("ReceiverOrg") or "",
                    "insert_date": record.get("InsertDate"),
                    "InsertDate": InsertDate,
                    "year": record.get("year"),
                    "is_late": is_late,
                    "late_days":late_days,
                    "is_closed": bool(record.get("Cloesd")),
                })
            all_results.extend(results)
        except Exception as e:
            print(f"❌ Error fetching document details: {e}")
        finally:
            conn.close()
    return all_results

# ================== نافذة عرض الإشعارات ==================
class NotificationDetailWindow(QDialog):
    COLUMNS = ["الكود", "الموضوع", "الجهة المرسلة", "تاريخ الاستحقاق", "السنة", "تاريخ الإدخال", "حالة التأخر"]

    def __init__(self, local_db: LocalDB, username: str, parent=None):
        super().__init__(parent)
        self.local_db = local_db
        self.username = username
        self.all_rows = []

        self.setWindowTitle("جميع الإشعارات")
        self.setWindowIcon(load_app_icon())
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(900, 600)

        main_layout = QVBoxLayout(self)

        filter_group = QGroupBox("فلترة")
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("بحث في الموضوع:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("اكتب للبحث...")
        self.search_input.textChanged.connect(self.apply_filters)  # البحث التلقائي أثناء الكتابة
        filter_layout.addWidget(self.search_input)

        filter_layout.addWidget(QLabel("من تاريخ:"))
        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("إلى تاريخ:"))
        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.setDate(QDate.currentDate().addYears(1))
        filter_layout.addWidget(self.date_to)

        filter_layout.addWidget(QLabel("الجهة المرسلة:"))
        self.org_combo = QComboBox()
        self.org_combo.addItem("الكل")
        filter_layout.addWidget(self.org_combo)

        self.apply_btn = QPushButton("تطبيق")
        self.reset_btn = QPushButton("إعادة تعيين")
        filter_layout.addWidget(self.apply_btn)
        filter_layout.addWidget(self.reset_btn)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        main_layout.addWidget(self.table)
        
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setSelectionBehavior(QTableWidget.SelectItems)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.installEventFilter(self)

        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        self.apply_btn.clicked.connect(self.apply_filters)
        self.reset_btn.clicked.connect(self.reset_filters)

        self.load_data()

    def load_data(self):
        self.all_rows = self.local_db.get_all_notifications(self.username)
        orgs = self.local_db.get_distinct_sender_orgs(self.username)
        self.org_combo.clear()
        self.org_combo.addItem("الكل")
        for org in orgs:
            self.org_combo.addItem(org)
        self.populate_table(self.all_rows)

    def populate_table(self, rows):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for row_data in rows:
            row_idx = self.table.rowCount()
            self.table.insertRow(row_idx)

            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row_data.get("doc_code") or "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row_data.get("subject") or "")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row_data.get("sender_org") or "")))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(row_data.get("due_date") or "")))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(row_data.get("year") or "")))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(row_data.get("insert_date") or "")))

            is_late = bool(row_data.get("is_late"))
            status_item = QTableWidgetItem("متأخر" if is_late else "في المدة")
            if is_late:
                status_item.setForeground(QColor("red"))
            else:
                status_item.setForeground(QColor("green"))
            self.table.setItem(row_idx, 6, status_item)

        self.table.setSortingEnabled(True)
        self.table.sortItems(5, Qt.DescendingOrder)

    def apply_filters(self):
        search_text = self.search_input.text().strip().lower()  # 🟢 نص البحث
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        selected_org = self.org_combo.currentText()

        filtered = []
        for row in self.all_rows:
            # 🟢 1. فلترة نص الموضوع
            subject = str(row.get("subject") or "").lower()
            if search_text and search_text not in subject:
                continue

            # 2. فلترة التاريخ
            insert_date_str = row.get("insert_date")
            if insert_date_str:
                try:
                    insert_date = datetime.fromisoformat(insert_date_str).date()
                except ValueError:
                    insert_date = None
            else:
                insert_date = None

            if insert_date and not (date_from <= insert_date <= date_to):
                continue

            # 3. فلترة الجهة
            if selected_org != "الكل" and row.get("sender_org") != selected_org:
                continue

            filtered.append(row)

        self.populate_table(filtered)

    def reset_filters(self):
        self.search_input.clear()  # 🟢 إفراغ صندوق البحث عند إعادة التعيين
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        self.date_to.setDate(QDate.currentDate().addYears(1))
        self.org_combo.setCurrentIndex(0)
        self.populate_table(self.all_rows)

    def eventFilter(self, obj, event):
        if obj == self.table and event.type() == QEvent.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key_C and (key_event.modifiers() & Qt.ControlModifier):
                self.copy_selected_cells()
                return True
        return super().eventFilter(obj, event)

    def show_context_menu(self, position):
        menu = QMenu()
        copy_action = QAction("نسخ", self)
        copy_action.triggered.connect(self.copy_selected_cells)
        menu.addAction(copy_action)
        menu.exec_(self.table.viewport().mapToGlobal(position))

    def copy_selected_cells(self):
        selected = self.table.selectedRanges()
        if not selected:
            return

        rows_data = []
        for selection in selected:
            for r in range(selection.topRow(), selection.bottomRow() + 1):
                row_cells = []
                for c in range(selection.leftColumn(), selection.rightColumn() + 1):
                    item = self.table.item(r, c)
                    row_cells.append(item.text() if item else "")
                rows_data.append("\t".join(row_cells))

        text_to_copy = "\n".join(rows_data)
        clipboard = QApplication.clipboard()
        clipboard.setText(text_to_copy)

# ================== نافذة تسجيل الدخول ==================
class LoginDialog(QDialog):
    def __init__(self, parent=None, current_username=""):
        super().__init__(parent)
        self.setWindowTitle("تسجيل الدخول / تبديل المستخدم")
        self.setWindowIcon(load_app_icon())
        self.setLayoutDirection(Qt.RightToLeft)
        self.username = None

        layout = QFormLayout(self)
        self.username_edit = QLineEdit(self)
        self.username_edit.setText(current_username or "")
        layout.addRow("اسم المستخدم:", self.username_edit)

        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("دخول")
        self.cancel_btn = QPushButton("إلغاء")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addRow(btn_layout)

        self.ok_btn.clicked.connect(self.accept_login)
        self.cancel_btn.clicked.connect(self.reject)

    def accept_login(self):
        text = self.username_edit.text().strip()
        if not text:
            QMessageBox.warning(self, "تنبيه", "الرجاء إدخال اسم المستخدم.")
            return
        self.username = text
        self.accept()

# ================== النافذة الرئيسية ==================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.local_db = LocalDB()
        if self.local_db.get_startup_setting():
            # إذا كان مفعلاً، تأكد من وجوده (بعد تحديث المسار)
            self.apply_startup_setting(enable=True)
        self.current_username = None
        self.current_user_id = None
        self.current_manager_id = None
        self.current_organization_id = None
        self.is_active = False
        self.tray_icon = None

        # التحقق من وجود إعدادات اتصال
        if not self.local_db.get_connection_settings():
            self.show_connection_settings(force=True)

        self.setWindowTitle("DMS Notifier - إشعارات المستندات")
        self.setWindowIcon(load_app_icon())   
        self.setLayoutDirection(Qt.RightToLeft)
        self.resize(480, 420)

        self._build_ui()
        self._build_tray_icon()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.auto_refresh)
        self.timer.start(CHECK_INTERVAL_MS)

        saved_user = self.local_db.get_current_user()
        if saved_user:
            self.login_as(saved_user, silent=True)

    def apply_startup_setting(self, enable: bool):
        """تطبيق إعداد بدء التشغيل (إضافة/حذف من Registry)."""
        app_name = "DMSNotifier"  # يمكن تغيير الاسم
        if enable:
            # المسار الكامل للملف التنفيذي الحالي
            exe_path = sys.executable if getattr(sys, 'frozen', False) else __file__
            add_to_startup(app_name, exe_path)
        else:
            remove_from_startup(app_name)
        self.local_db.set_startup_setting(enable)

    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        user_row = QHBoxLayout()
        self.status_label = QLabel()
        self.status_icon_label = QLabel()
        self.update_status_display(None, False)
        user_row.addWidget(self.status_icon_label)
        user_row.addWidget(self.status_label)
        user_row.addStretch()
        layout.addLayout(user_row)

        buttons_row = QHBoxLayout()
        self.login_btn = QPushButton("تسجيل الدخول / تبديل المستخدم")
        self.view_all_btn = QPushButton("عرض جميع الإشعارات")
        self.refresh_btn = QPushButton("تحديث يدوي")
        #self.settings_btn = QPushButton("إعدادات الاتصال")
        buttons_row.addWidget(self.login_btn)
        buttons_row.addWidget(self.view_all_btn)
        buttons_row.addWidget(self.refresh_btn)
        #buttons_row.addWidget(self.settings_btn)
        layout.addLayout(buttons_row)
        startup_layout = QHBoxLayout()
        self.startup_checkbox = QCheckBox("تشغيل البرنامج مع بدء تشغيل Windows")
        self.startup_checkbox.stateChanged.connect(self.on_startup_toggled)
        startup_layout.addWidget(self.startup_checkbox)
        startup_layout.addStretch()
        layout.addLayout(startup_layout)

        # تحديث حالة الـ checkbox من قاعدة البيانات
        self.startup_checkbox.setChecked(self.local_db.get_startup_setting())


        self.login_btn.clicked.connect(self.show_login_dialog)
        self.view_all_btn.clicked.connect(self.show_detail_window)
        self.refresh_btn.clicked.connect(self.manual_refresh)
        #self.settings_btn.clicked.connect(self.show_connection_settings)

        layout.addWidget(QLabel("آخر 5 إشعارات:"))
        self.recent_list = QListWidget()
        layout.addWidget(self.recent_list)

        self.setCentralWidget(central)
        footer_layout = QHBoxLayout()
        version_label = QLabel(f"الإصدار {APP_VERSION}")
        version_label.setAlignment(Qt.AlignLeft)
        version_label.setStyleSheet("color: gray; font-size: 10px;")
        footer_layout.addWidget(version_label)
        footer_layout.addStretch()
        layout.addLayout(footer_layout)

        self.setCentralWidget(central)


    def _build_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(load_app_icon())
        self.tray_icon.setToolTip("DMS Notifier")

        tray_menu = QMenu()
        show_action = QAction("إظهار النافذة", self)
        show_action.triggered.connect(self.show_and_raise)
        quit_action = QAction("خروج", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        QTimer.singleShot(1000, self._ensure_tray_icon_visible)

        self.tray_icon.setVisible(True)  

    def _ensure_tray_icon_visible(self):
        if not self.tray_icon.isVisible():
            self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def update_status_display(self, username, is_active):
        if username:
            self.status_label.setText(f"المستخدم الحالي: {username} - {'نشط' if is_active else 'غير نشط'}")
            self.status_icon_label.setPixmap(
                make_status_icon("#22c55e" if is_active else "#ef4444").pixmap(16, 16)
            )
        else:
            self.status_label.setText("لم يتم تسجيل الدخول بعد")
            self.status_icon_label.setPixmap(make_status_icon("#9ca3af").pixmap(16, 16))

    def show_login_dialog(self):
        dialog = LoginDialog(self, current_username=self.current_username or "")
        if dialog.exec_() == QDialog.Accepted and dialog.username:
            self.login_as(dialog.username)

    def login_as(self, username, silent=False):
        try:
            account = fetch_account_ids(username)
        except SqlServerConnectionError as e:
            QMessageBox.critical(self, "خطأ في الاتصال", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "خطأ غير متوقع", f"{e}\n\n{traceback.format_exc()}")
            return

        if account is None:
            if not silent:
                QMessageBox.warning(self, "تنبيه", f"لم يتم العثور على المستخدم '{username}' في النظام.")
            return

        [user_id, manager_id, isActive, OrganizationID] = account
        self.current_username = username
        self.current_user_id = user_id
        self.current_manager_id = manager_id
        self.current_organization_id = OrganizationID
        self.is_active = isActive

        self.local_db.set_current_user(username)
        self.update_status_display(username, isActive)

        self.refresh_recent_list()

        if not silent:
            self.manual_refresh()

    def manual_refresh(self):
        self._do_refresh(show_message_if_none=True)

    def auto_refresh(self):
        self._do_refresh(show_message_if_none=False)

    def _do_refresh(self, show_message_if_none=False):
        if not self.current_username:
            if show_message_if_none:
                QMessageBox.information(self, "تنبيه", "الرجاء تسجيل الدخول أولاً.")
            return

        last_check = self.local_db.get_last_check(self.current_username)

        try:
            documents = fetch_documents_with_details(
                self.current_user_id, self.current_manager_id, last_check, self.current_organization_id
            )
        except SqlServerConnectionError as e:
            QMessageBox.critical(self, "خطأ في الاتصال", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "خطأ غير متوقع", f"{e}\n\n{traceback.format_exc()}")
            return

        new_items = self.local_db.save_notifications(self.current_username, documents)
        self.local_db.set_last_check(self.current_username, datetime.now())

        self.refresh_recent_list()

        if new_items:
            self.notify_new_items(new_items)
        elif show_message_if_none:
            QMessageBox.information(self, "تحديث", "لا توجد مستندات جديدة.")

    def notify_new_items(self, new_items):
        count = len(new_items)
        first_subject = new_items[0].get("subject") or ""
        message = f"لديك {count} إشعار جديد" if count > 1 else "لديك إشعار جديد"
        self.tray_icon.showMessage(
            "DMS Notifier",
            f"{message}\n{first_subject}",
            QSystemTrayIcon.Information,
            5000
        )

    def refresh_recent_list(self):
        self.recent_list.clear()
        if not self.current_username:
            return
        latest = self.local_db.get_latest_notifications(self.current_username, limit=5)
        for item in latest:
            is_late = bool(item.get("is_late"))
            status = "متأخر" if is_late else "في المدة"
            text = f"[{status}] {item.get('doc_code') or ''} - {item.get('subject') or ''}"
            list_item = QListWidgetItem(text)
            if is_late:
                list_item.setForeground(QColor("red"))
            self.recent_list.addItem(list_item)

    def show_detail_window(self):
        if not self.current_username:
            QMessageBox.information(self, "تنبيه", "الرجاء تسجيل الدخول أولاً.")
            return
        dialog = NotificationDetailWindow(self.local_db, self.current_username, self)
        dialog.exec_()

    def show_connection_settings(self, force=False):
        """عرض نافذة إعدادات الاتصال."""
        current = self.local_db.get_connection_settings() or {}
        dialog = ConnectionSettingsDialog(self, current)
        if dialog.exec_() == QDialog.Accepted:
            settings = dialog.get_settings()
            if all(settings.values()):
                self.local_db.save_connection_settings(
                    settings['host'],
                    settings['database'],
                    settings['user'],
                    settings['password']
                )
                QMessageBox.information(self, "تم الحفظ", "تم حفظ إعدادات الاتصال بنجاح.")
            else:
                QMessageBox.warning(self, "تنبيه", "جميع الحقول مطلوبة.")
        # إذا كانت force=True ولم يتم الحفظ، نغلق التطبيق (لأنه لا يمكن الاستمرار)
        if force and not self.local_db.get_connection_settings():
            QMessageBox.critical(self, "خطأ", "لا يمكن تشغيل التطبيق بدون إعدادات اتصال صحيحة.")
            QApplication.quit()
            sys.exit(0)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "DMS Notifier",
            "البرنامج ما زال يعمل في الخلفية.",
            QSystemTrayIcon.Information,
            3000
        )

    
    def on_startup_toggled(self, state):
        """عند تغيير حالة الـ checkbox، نقوم بتحديث التسجيل وقاعدة البيانات."""
        enable = (state == Qt.Checked)
        self.apply_startup_setting(enable)

    def quit_app(self):
        self.tray_icon.hide()
        QApplication.quit()
        sys.exit(0)

# ================== تشغيل التطبيق ==================
def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        with open("error.log", "w") as f:
            f.write(f"{datetime.now()}: {str(e)}\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    main()