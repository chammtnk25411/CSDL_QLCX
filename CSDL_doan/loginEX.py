# loginEX.py - Sửa lỗi kiểm tra username từ database
import sys
import json
import os
from datetime import datetime
import unicodedata
import re

import pyodbc
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QWidget, QDialog, QTableWidgetItem, QPushButton, \
    QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt

# Import giao diện
from login import Ui_LoginWindow
from sign import Ui_RegisterForm

# Import các trang chức năng
from chinhEx import MainWindow as TrangChuWindow
from quanlycayEx import QuanLyCayWindow
from LoaithucvatEx import MainWindow as LoaiThucVatWindow
from HothucvatEx import MainWindow as HoThucVatWindow
from KhutrungbayEx import MainWindow as KhuTrungBayWindow
from NhanvienEx import MainWindow as NhanVienWindow
from phieu_cham_socEx import PhieuChamSocEx as PhieuChamSocWindow
from phieu_khao_satEx import PhieuKhaoSatEx as PhieuKhaoSatWindow
from yeu_cau_bao_triEx import YeuCauBaoTriEx as YeuCauBaoTriWindow
from bao_cao_su_coEx import MainWindow as BaoCaoSuCoWindow

# =========================================================
# FILE LƯU THÔNG TIN ĐĂNG NHẬP (GHI NHỚ)
# =========================================================
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'login_config.json')

# =========================================================
# TÀI KHOẢN MẶC ĐỊNH (KHÔNG CẦN SQL)
# =========================================================
DEFAULT_ACCOUNTS = {
    "Quản trị viên": [
        {"username": "admin", "password": "123", "hoten": "Quản trị viên hệ thống"},
        {"username": "truongphong", "password": "123", "hoten": "Trưởng phòng"}
    ],
    "Nhân viên": [
        {"username": "staff", "password": "123", "hoten": "Nhân viên"},
        {"username": "nhanvien1", "password": "123", "hoten": "Nguyễn Văn A"}
    ]
}


def save_login_info(username, password, remember, role):
    data = {
        'username': username if remember else '',
        'password': password if remember else '',
        'remember': remember,
        'role': role if remember else ''
    }
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


def load_login_info():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except:
        pass
    return {'username': '', 'password': '', 'remember': False, 'role': ''}


# =========================================================
# KẾT NỐI SQL SERVER
# =========================================================
try:
    import config
except ImportError:
    config = None

_ODBC_DRIVER_CANDIDATES = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
]


def get_connection():
    if config is None:
        raise ConnectionError("Không tìm thấy file 'config.py'")
    server = getattr(config, "DB_SERVER", None)
    database_name = getattr(config, "DB_NAME", None)
    if not server or not database_name:
        raise ConnectionError("File 'config.py' đang thiếu DB_SERVER hoặc DB_NAME")

    for driver in _ODBC_DRIVER_CANDIDATES:
        try:
            conn_str = (
                f"DRIVER={{{driver}}};SERVER={server};DATABASE={database_name};"
                f"Trusted_Connection=yes;TrustServerCertificate=yes;"
            )
            return pyodbc.connect(conn_str, timeout=5)
        except:
            continue
    raise ConnectionError("Không thể kết nối SQL Server. Kiểm tra config.py")


def _rows_to_dicts(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class database:
    @staticmethod
    def get_all_nhanvien():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT MANV, HOTEN, CHUCVU, MATKHAU, EMAIL FROM NHAN_VIEN")
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def get_all_khachhang():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT MAKHACH, HOTEN, TENDANGNHAP, MATKHAU, EMAIL FROM KHACH_THAM_QUAN")
            result = _rows_to_dicts(cur)
            return result
        finally:
            conn.close()

    @staticmethod
    def check_username_exists(username):
        """Kiểm tra username đã tồn tại trong database chưa - TRẢ VỀ TRUE/FALSE"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM KHACH_THAM_QUAN WHERE TENDANGNHAP = ?", (username,))
            count = cur.fetchone()[0]
            print(f"DEBUG: Kiểm tra username '{username}' trong database: {count} bản ghi")
            return count > 0
        except Exception as e:
            print(f"DEBUG: Lỗi kiểm tra username: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def check_khachhang_login(tendangnhap, matkhau):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT MAKHACH, HOTEN, TENDANGNHAP, MATKHAU, EMAIL 
                FROM KHACH_THAM_QUAN 
                WHERE TENDANGNHAP = ? AND MATKHAU = ?
            """, (tendangnhap, matkhau))
            row = cur.fetchone()
            if row:
                columns = [col[0] for col in cur.description]
                return dict(zip(columns, row))
            return None
        finally:
            conn.close()

    @staticmethod
    def save_khachhang(hoten, tendangnhap, matkhau, dienthoai=None, email=None):
        conn = get_connection()
        try:
            cur = conn.cursor()

            # KIỂM TRA LẠI LẦN NỮA TRƯỚC KHI INSERT
            cur.execute("SELECT COUNT(*) FROM KHACH_THAM_QUAN WHERE TENDANGNHAP = ?", (tendangnhap,))
            count = cur.fetchone()[0]
            print(f"DEBUG: Kiểm tra lần cuối '{tendangnhap}': {count} bản ghi")

            if count > 0:
                raise Exception(f"Tên đăng nhập '{tendangnhap}' đã tồn tại!")

            # Tạo mã khách hàng
            cur.execute("SELECT MAX(MAKHACH) FROM KHACH_THAM_QUAN")
            row = cur.fetchone()
            if row and row[0]:
                num_str = row[0].replace('KH', '')
                if num_str.isdigit():
                    num = int(num_str) + 1
                else:
                    num = 21
                makh = f"KH{num:02d}"
            else:
                makh = "KH01"

            # Thêm khách hàng
            cur.execute("""
                INSERT INTO KHACH_THAM_QUAN (MAKHACH, HOTEN, DIENTHOAI, EMAIL, TENDANGNHAP, MATKHAU)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (makh, hoten, dienthoai, email, tendangnhap, matkhau))
            conn.commit()

            print(f"DEBUG: Đã thêm KH {makh} thành công!")
            return makh

        except pyodbc.Error as e:
            error_msg = str(e)
            print(f"DEBUG: Lỗi SQL: {error_msg}")
            if "UNIQUE" in error_msg.upper() or "UQ__KHACH_TH" in error_msg:
                raise Exception(f"Tên đăng nhập '{tendangnhap}' đã tồn tại!")
            raise Exception(f"Lỗi database: {error_msg}")
        finally:
            conn.close()


# =========================================================
# GIAO DIỆN ĐĂNG KÝ
# =========================================================
class SignWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_RegisterForm()
        self.ui.setupUi(self)

        # Kết nối sự kiện
        self.ui.registerButton.clicked.connect(self.register)

        if hasattr(self.ui, 'btnCancel'):
            self.ui.btnCancel.clicked.connect(self.reject)

        # Label hiển thị trạng thái
        self.status_label = QLabel(self)
        self.status_label.setStyleSheet("""
            font-size: 10pt;
            padding: 5px;
            margin-top: 5px;
        """)
        self.status_label.hide()

        # Thêm label sau ô username
        if hasattr(self.ui, 'txtUsername'):
            self.ui.txtUsername.textChanged.connect(self.check_username)
            parent_layout = self.ui.txtUsername.parent().layout()
            if parent_layout:
                index = parent_layout.indexOf(self.ui.txtUsername)
                if index >= 0:
                    parent_layout.insertWidget(index + 1, self.status_label)

        # Nút tạo tên tự động
        self.btn_auto = QPushButton("🔄 Tạo tên tự động")
        self.btn_auto.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.btn_auto.clicked.connect(self.auto_generate_username)

        if hasattr(self.ui, 'txtUsername'):
            parent_layout = self.ui.txtUsername.parent().layout()
            if parent_layout:
                for i in range(parent_layout.count()):
                    item = parent_layout.itemAt(i)
                    if item and item.widget() == self.ui.txtUsername:
                        h_layout = QHBoxLayout()
                        h_layout.addWidget(self.ui.txtUsername)
                        h_layout.addWidget(self.btn_auto)
                        h_layout.setSpacing(5)
                        parent_layout.insertLayout(i, h_layout)
                        parent_layout.takeAt(i + 1)
                        break

        self.setWindowTitle("Đăng ký tài khoản - Khách tham quan")
        self.setModal(True)
        self.setFixedSize(565, 750)

    def check_username(self):
        """Kiểm tra username - GỌI TRỰC TIẾP TỪ DATABASE"""
        if not hasattr(self.ui, 'txtUsername'):
            return

        username = self.ui.txtUsername.text().strip()

        if len(username) < 3:
            self.status_label.hide()
            return

        # Kiểm tra hợp lệ
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            self.status_label.setText("❌ Chỉ được chứa chữ cái, số và dấu gạch dưới (_)")
            self.status_label.setStyleSheet("color: #f44336; font-size: 10pt; padding: 5px;")
            self.status_label.show()
            return

        # ===== QUAN TRỌNG: KIỂM TRA TRỰC TIẾP TỪ DATABASE =====
        exists = database.check_username_exists(username)

        if exists:
            suggestions = self.suggest_username(username)
            if suggestions:
                suggest_text = " | ".join(suggestions[:3])
                self.status_label.setText(f"❌ Tên đã tồn tại! Gợi ý: {suggest_text}")
            else:
                self.status_label.setText(f"❌ Tên '{username}' đã tồn tại!")
            self.status_label.setStyleSheet("color: #f44336; font-size: 10pt; padding: 5px;")
            self.status_label.show()
        else:
            self.status_label.setText(f"✅ Tên '{username}' hợp lệ!")
            self.status_label.setStyleSheet("color: #4caf50; font-size: 10pt; padding: 5px;")
            self.status_label.show()

    def suggest_username(self, username):
        """Gợi ý tên đăng nhập - KIỂM TRA TỪ DATABASE"""
        suggestions = []
        base = username
        counter = 1

        match = re.match(r'^(.*?)(\d+)$', username)
        if match:
            base = match.group(1)
            start_num = int(match.group(2))
            counter = start_num + 1

        while len(suggestions) < 5:
            new_name = f"{base}{counter}"
            # KIỂM TRA TỪ DATABASE
            if not database.check_username_exists(new_name):
                suggestions.append(new_name)
            counter += 1

        return suggestions

    def auto_generate_username(self):
        """Tạo tên đăng nhập tự động từ họ tên - KIỂM TRA TỪ DATABASE"""
        hoten = self.ui.txtFullName.text().strip()
        if not hoten:
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng nhập họ và tên trước!")
            self.ui.txtFullName.setFocus()
            return

        base = self._generate_username(hoten)
        username = base
        counter = 1

        # KIỂM TRA TỪ DATABASE
        while database.check_username_exists(username):
            username = f"{base}{counter}"
            counter += 1

        self.ui.txtUsername.setText(username)
        self.ui.txtUsername.setFocus()
        self.ui.txtUsername.selectAll()
        self.check_username()

    def _generate_username(self, fullname):
        """Tạo tên đăng nhập từ họ tên"""
        name = fullname.lower()
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        name = re.sub(r'[^a-z0-9\s]', '', name)
        name = re.sub(r'\s+', '_', name)
        name = name.strip('_')

        if len(name) < 3:
            name = f"user_{name}"
        return name

    def register(self):
        """Đăng ký tài khoản"""
        hoten = self.ui.txtFullName.text().strip()
        tendangnhap = self.ui.txtUsername.text().strip()
        phone = self.ui.txtPhone.text().strip()
        email = self.ui.txtEmail.text().strip() if hasattr(self.ui, 'txtEmail') else ''
        password = self.ui.txtPassword.text().strip()
        confirm = self.ui.txtConfirmPassword.text().strip()

        # Kiểm tra họ tên
        if hoten == "":
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng nhập họ và tên!")
            self.ui.txtFullName.setFocus()
            return

        # Kiểm tra tên đăng nhập
        if tendangnhap == "":
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng nhập tên đăng nhập!")
            self.ui.txtUsername.setFocus()
            return

        if not re.match(r'^[a-zA-Z0-9_]+$', tendangnhap):
            QMessageBox.warning(self, "Thông báo", "❌ Tên đăng nhập chỉ được chứa chữ cái, số và dấu gạch dưới (_)!")
            self.ui.txtUsername.setFocus()
            return

        if len(tendangnhap) < 3:
            QMessageBox.warning(self, "Thông báo", "❌ Tên đăng nhập phải có ít nhất 3 ký tự!")
            self.ui.txtUsername.setFocus()
            return

        # ===== QUAN TRỌNG: KIỂM TRA TRỰC TIẾP TỪ DATABASE TRƯỚC KHI LƯU =====
        if database.check_username_exists(tendangnhap):
            suggestions = self.suggest_username(tendangnhap)
            msg = f"❌ Tên đăng nhập '{tendangnhap}' đã tồn tại!\n\n"
            if suggestions:
                msg += f"💡 Gợi ý:\n"
                for i, name in enumerate(suggestions[:5], 1):
                    msg += f"   {i}. {name}\n"
            QMessageBox.warning(self, "Thông báo", msg)
            self.ui.txtUsername.setFocus()
            self.ui.txtUsername.selectAll()
            return

        # Kiểm tra số điện thoại
        if phone == "":
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng nhập số điện thoại!")
            self.ui.txtPhone.setFocus()
            return

        if not phone.isdigit():
            QMessageBox.warning(self, "Thông báo", "❌ Số điện thoại chỉ được chứa chữ số!")
            self.ui.txtPhone.setFocus()
            return

        if len(phone) < 10:
            QMessageBox.warning(self, "Thông báo", "❌ Số điện thoại phải có ít nhất 10 chữ số!")
            self.ui.txtPhone.setFocus()
            return

        # Kiểm tra email
        if email and '@' not in email:
            QMessageBox.warning(self, "Thông báo", "❌ Email không hợp lệ!")
            self.ui.txtEmail.setFocus()
            return

        # Kiểm tra điều khoản
        if hasattr(self.ui, 'chkTerms') and not self.ui.chkTerms.isChecked():
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng đồng ý với điều khoản sử dụng!")
            return

        # Kiểm tra mật khẩu
        if password == "":
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng nhập mật khẩu!")
            self.ui.txtPassword.setFocus()
            return

        if password != confirm:
            QMessageBox.warning(self, "Thông báo", "❌ Mật khẩu xác nhận không khớp!")
            self.ui.txtConfirmPassword.setFocus()
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Thông báo", "❌ Mật khẩu phải có ít nhất 6 ký tự!")
            self.ui.txtPassword.setFocus()
            return

        try:
            # Lưu vào database
            makh = database.save_khachhang(
                hoten=hoten,
                tendangnhap=tendangnhap,
                matkhau=password,
                dienthoai=phone,
                email=email if email else None
            )

            msg = (
                f"✅ ĐĂNG KÝ THÀNH CÔNG!\n\n"
                f"👤 Họ tên: {hoten}\n"
                f"📋 Mã KH: {makh}\n"
                f"🔑 Tên đăng nhập: {tendangnhap}\n"
                f"📧 Email: {email if email else 'Không có'}\n"
                f"📱 SĐT: {phone}\n"
                f"🔒 Mật khẩu: {password}\n\n"
                f"👉 Vui lòng đăng nhập!"
            )

            QMessageBox.information(self, "Thành công ✅", msg)
            self.accept()

        except Exception as e:
            error_msg = str(e)
            print(f"DEBUG: Lỗi: {error_msg}")

            if "Tên đăng nhập" in error_msg and "tồn tại" in error_msg:
                QMessageBox.warning(self, "Lỗi",
                                    f"❌ {error_msg}\n\n💡 Vui lòng thử tên khác hoặc bấm 'Tạo tên tự động'!")
                self.ui.txtUsername.setFocus()
                self.ui.txtUsername.selectAll()
            else:
                QMessageBox.critical(self, "Lỗi ❌", f"Không thể đăng ký:\n{error_msg}")


# =========================================================
# GIAO DIỆN TRANG CHỦ
# =========================================================
class MainWindow(TrangChuWindow):
    def __init__(self, username, role):
        super().__init__(username, role)
        if hasattr(self, "ui") and hasattr(self.ui, "userInfo"):
            self.ui.userInfo.setText(f"{username}\n{role}")
        if hasattr(self, "ui") and hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self, "ui") and hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)


# =========================================================
# GIAO DIỆN ĐĂNG NHẬP
# =========================================================
class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_LoginWindow()
        self.ui.setupUi(self)
        self.role = None
        self.sign_window = None

        saved = load_login_info()
        if saved.get('remember'):
            self.ui.input_username.setText(saved.get('username', ''))
            self.ui.input_password.setText(saved.get('password', ''))
            self.ui.chk_remember.setChecked(True)
            saved_role = saved.get('role', '')
            if saved_role == "Quản trị viên":
                self.chooseAdmin()
            elif saved_role == "Nhân viên":
                self.chooseStaff()
            elif saved_role == "Khách tham quan":
                self.chooseGuest()

        self.ui.btn_role_admin.clicked.connect(self.chooseAdmin)
        self.ui.btn_role_staff.clicked.connect(self.chooseStaff)
        self.ui.btn_role_guest.clicked.connect(self.chooseGuest)
        self.ui.btn_login.clicked.connect(self.login)

        if hasattr(self.ui, 'btn_register'):
            self.ui.btn_register.clicked.connect(self.open_register)

        self.ui.input_username.returnPressed.connect(self.login)
        self.ui.input_password.returnPressed.connect(self.login)

    def chooseAdmin(self):
        self.role = "Quản trị viên"
        self.resetButton()
        self.ui.btn_role_admin.setStyleSheet(
            "QPushButton{background:#198754;color:white;border-radius:8px;font-weight:bold;}")
        self.setWindowTitle("Đăng nhập - Quản trị viên")

    def chooseStaff(self):
        self.role = "Nhân viên"
        self.resetButton()
        self.ui.btn_role_staff.setStyleSheet(
            "QPushButton{background:#198754;color:white;border-radius:8px;font-weight:bold;}")
        self.setWindowTitle("Đăng nhập - Nhân viên")

    def chooseGuest(self):
        self.role = "Khách tham quan"
        self.resetButton()
        self.ui.btn_role_guest.setStyleSheet(
            "QPushButton{background:#198754;color:white;border-radius:8px;font-weight:bold;}")
        self.setWindowTitle("Đăng nhập - Khách tham quan")

    def resetButton(self):
        self.ui.btn_role_admin.setStyleSheet(
            "QPushButton{background:#f4fbf7;border:1px solid #2d6a4f;border-radius:8px;color:#2d6a4f;font-weight:bold;}")
        self.ui.btn_role_staff.setStyleSheet(
            "QPushButton{background:#f0f9ff;border:1px solid #0369a1;border-radius:8px;color:#0369a1;font-weight:bold;}")
        self.ui.btn_role_guest.setStyleSheet(
            "QPushButton{background:#fffbeb;border:1px solid #b45309;border-radius:8px;color:#b45309;font-weight:bold;}")

    def open_register(self):
        if self.sign_window is None or not self.sign_window.isVisible():
            self.sign_window = SignWindow(self)
            self.sign_window.show()
        else:
            self.sign_window.raise_()
            self.sign_window.activateWindow()

    def check_default_account(self, username, password, role):
        """Kiểm tra tài khoản mặc định (không cần SQL)"""
        if role in DEFAULT_ACCOUNTS:
            for acc in DEFAULT_ACCOUNTS[role]:
                if acc["username"] == username and acc["password"] == password:
                    return acc["hoten"]
        return None

    def login(self):
        username = self.ui.input_username.text().strip()
        password = self.ui.input_password.text().strip()

        if self.role is None:
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng chọn quyền!")
            return

        if username == "":
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng nhập tên đăng nhập!")
            return
        if password == "":
            QMessageBox.warning(self, "Thông báo", "❌ Vui lòng nhập mật khẩu!")
            return

        # ===== KIỂM TRA TÀI KHOẢN MẶC ĐỊNH (KHÔNG CẦN SQL) =====
        default_hoten = self.check_default_account(username, password, self.role)
        if default_hoten:
            remember = self.ui.chk_remember.isChecked()
            save_login_info(username, password, remember, self.role)
            self.main_window = MainWindow(default_hoten, self.role)
            self.main_window.show()
            self.close()
            return

        # ===== KIỂM TRA KHÁCH THAM QUAN TỪ SQL =====
        if self.role == "Khách tham quan":
            try:
                khach = database.check_khachhang_login(username, password)
                if khach:
                    remember = self.ui.chk_remember.isChecked()
                    save_login_info(username, password, remember, self.role)
                    self.main_window = MainWindow(khach["HOTEN"], self.role)
                    self.main_window.show()
                    self.close()
                    return
                else:
                    QMessageBox.warning(self, "Đăng nhập thất bại ❌", "Sai tên đăng nhập hoặc mật khẩu!")
                    return
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể kết nối database:\n{str(e)}")
                return

        # ===== KIỂM TRA NHÂN VIÊN TỪ SQL =====
        try:
            all_staff = database.get_all_nhanvien()
            for staff in all_staff:
                if (staff["MANV"] == username or staff["EMAIL"] == username) and staff["MATKHAU"] == password:
                    if self.role == "Quản trị viên":
                        if staff["CHUCVU"] in ["Trưởng phòng", "Quản trị viên"]:
                            remember = self.ui.chk_remember.isChecked()
                            save_login_info(username, password, remember, self.role)
                            self.main_window = MainWindow(staff["HOTEN"], self.role)
                            self.main_window.show()
                            self.close()
                            return
                        else:
                            QMessageBox.warning(self, "Đăng nhập thất bại ❌", "Bạn không có quyền Quản trị viên!")
                            return
                    elif self.role == "Nhân viên":
                        if staff["CHUCVU"] not in ["Trưởng phòng", "Quản trị viên"]:
                            remember = self.ui.chk_remember.isChecked()
                            save_login_info(username, password, remember, self.role)
                            self.main_window = MainWindow(staff["HOTEN"], self.role)
                            self.main_window.show()
                            self.close()
                            return
                        else:
                            QMessageBox.warning(self, "Đăng nhập thất bại ❌", "Bạn không có quyền Nhân viên!")
                            return

            QMessageBox.warning(self, "Đăng nhập thất bại ❌", "Sai tên đăng nhập, mật khẩu hoặc vai trò!")

        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi kết nối SQL Server.\nChi tiết: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())