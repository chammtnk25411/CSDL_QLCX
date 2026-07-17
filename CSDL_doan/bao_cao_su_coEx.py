# bao_cao_su_coEx.py
import sys
from datetime import datetime

import pyodbc
from PyQt6 import QtCore
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox

import config
from bao_cao_su_co import Ui_MainWindow


def get_db_connection(show_log=False):
    """Kết nối đến SQL Server"""
    try:
        drivers = [
            "ODBC Driver 18 for SQL Server",
            "ODBC Driver 17 for SQL Server",
            "SQL Server Native Client 11.0",
            "SQL Server"
        ]

        for driver in drivers:
            try:
                conn = pyodbc.connect(
                    f'DRIVER={{{driver}}};'
                    f'SERVER={config.DB_SERVER};'
                    f'DATABASE={config.DB_NAME};'
                    f'Trusted_Connection=yes;'
                    f'TrustServerCertificate=yes;'
                )
                if show_log:
                    print(f"✅ Kết nối thành công với driver: {driver}")
                return conn
            except pyodbc.Error as e:
                if show_log:
                    print(f"❌ Lỗi với driver {driver}: {e}")
                continue

        return None
    except Exception as e:
        if show_log:
            print(f"Lỗi kết nối SQL Server: {e}")
        return None


MAX_MOTA_LEN = 500

# Danh sách cây mẫu (mã, tên) để test khi không có kết nối SQL
SAMPLE_TREES = [
    ("C045", "Sao đen"),
    ("C012", "Bàng"),
    ("C078", "Phượng vĩ"),
    ("C023", "Bằng lăng"),
    ("C099", "Xà cừ"),
    ("C061", "Me tây"),
]


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, username=None, role=None):
        super().__init__()
        self.setupUi(self)

        # Lưu thông tin người dùng
        self.username = username
        self.role = role
        self.is_guest = (role == "Khách tham quan")

        # Thiết lập giao diện
        self._setup_ui()
        self._setup_connections()

        # Load dữ liệu cây vào combobox
        self.load_tree_combo()

        # Tạo mã báo cáo tự động
        self.generate_ma_bc()

        self.statusBar().showMessage("Sẵn sàng.")

    def _setup_ui(self):
        """Thiết lập giao diện ban đầu"""
        # Đặt thời gian mặc định là hiện tại
        self.fieldThoiGianGui.setDateTime(QtCore.QDateTime.currentDateTime())

        # Thiết lập char counter
        self.fieldMoTa.textChanged.connect(self._on_mota_changed)
        self._on_mota_changed()

        # Cập nhật thông tin người dùng
        if self.username:
            self.userName.setText(self.username)
            self.sidebarUserLabel.setText(f"👤 {self.username}")
        if self.role:
            self.userRole.setText(self.role)
            self.sidebarRoleLabel.setText(self.role)

    def _setup_connections(self):
        """Kết nối các sự kiện"""
        self.btnSave.clicked.connect(self.save_report)
        self.btnCancel.clicked.connect(self.cancel_form)

        # Kết nối các nút navigation
        self.navTrangChu.clicked.connect(self.open_trang_chu)
        self.navQuanLyCay.clicked.connect(self.open_quan_ly_cay)
        self.navLoaiThucVat.clicked.connect(self.open_loai_thuc_vat)
        self.navHoThucVat.clicked.connect(self.open_ho_thuc_vat)
        self.navKhuTrungBay.clicked.connect(self.open_khu_trung_bay)
        self.navNhanVien.clicked.connect(self.open_nhan_vien)
        self.navPhieuChamSoc.clicked.connect(self.open_phieu_cham_soc)
        self.navPhieuKhaoSat.clicked.connect(self.open_phieu_khao_sat)
        self.navYeuCauBaoTri.clicked.connect(self.open_yeu_cau_bao_tri)
        self.navActive.clicked.connect(self.open_bao_cao_su_co)

    def load_tree_combo(self):
        """Load danh sách cây từ database vào combobox"""
        try:
            conn = get_db_connection()
            if not conn:
                # Dùng dữ liệu mẫu
                self.fieldCay.clear()
                self.fieldCay.addItem("Chọn cây")
                for ma, ten in SAMPLE_TREES:
                    self.fieldCay.addItem(f"{ten} ({ma})")
                return

            cursor = conn.cursor()
            cursor.execute("SELECT MACAY, TENCAY FROM CAY ORDER BY MACAY")
            rows = cursor.fetchall()
            conn.close()

            self.fieldCay.clear()
            self.fieldCay.addItem("Chọn cây")
            for row in rows:
                self.fieldCay.addItem(f"{row[1]} ({row[0]})")

        except Exception as e:
            print(f"Lỗi load cây: {e}")
            self.fieldCay.clear()
            self.fieldCay.addItem("Chọn cây")
            for ma, ten in SAMPLE_TREES:
                self.fieldCay.addItem(f"{ten} ({ma})")

    def generate_ma_bc(self):
        """Tạo mã báo cáo tự động"""
        try:
            conn = get_db_connection()
            if not conn:
                self.fieldMABC.setText("BC01")
                return

            cursor = conn.cursor()
            cursor.execute("SELECT MAX(MABC) FROM BAO_CAO_SU_CO")
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                last_id = row[0]
                if last_id.startswith('BC'):
                    num = int(last_id.replace('BC', '')) + 1
                    self.fieldMABC.setText(f"BC{num:02d}")
                else:
                    self.fieldMABC.setText("BC01")
            else:
                self.fieldMABC.setText("BC01")
        except:
            self.fieldMABC.setText("BC01")

    def _on_mota_changed(self):
        """Xử lý thay đổi nội dung mô tả"""
        text = self.fieldMoTa.toPlainText()
        if len(text) > MAX_MOTA_LEN:
            cursor = self.fieldMoTa.textCursor()
            pos = cursor.position()
            trimmed = text[:MAX_MOTA_LEN]
            self.fieldMoTa.blockSignals(True)
            self.fieldMoTa.setPlainText(trimmed)
            cursor.setPosition(min(pos, len(trimmed)))
            self.fieldMoTa.setTextCursor(cursor)
            self.fieldMoTa.blockSignals(False)
            text = trimmed

        length = len(text)
        self.charCounter2.setText(f"{length}/{MAX_MOTA_LEN}")
        if length >= MAX_MOTA_LEN:
            self.charCounter2.setStyleSheet("color: #e53935; font-size: 11px; font-weight: bold;")
        elif length >= int(MAX_MOTA_LEN * 0.9):
            self.charCounter2.setStyleSheet("color: #e08a1f; font-size: 11px;")
        else:
            self.charCounter2.setStyleSheet("color: #9aa39d; font-size: 11px;")

    def _reset_field_style(self, widget):
        widget.setStyleSheet("")

    def _mark_invalid(self, widget):
        widget.setStyleSheet("border: 1px solid #e53935; border-radius: 6px;")

    def validate_form(self):
        """Kiểm tra dữ liệu form"""
        is_valid = True

        self._reset_field_style(self.fieldCay)
        self._reset_field_style(self.fieldMoTa)
        self._reset_field_style(self.fieldMucDoNguyHiem)

        if self.fieldCay.currentIndex() <= 0:
            self._mark_invalid(self.fieldCay)
            is_valid = False

        if not self.fieldMoTa.toPlainText().strip():
            self._mark_invalid(self.fieldMoTa)
            is_valid = False

        if self.fieldMucDoNguyHiem.currentIndex() <= 0:
            self._mark_invalid(self.fieldMucDoNguyHiem)
            is_valid = False

        if not is_valid:
            QMessageBox.warning(
                self, "Thiếu thông tin",
                "Vui lòng nhập đầy đủ các trường bắt buộc (đánh dấu *)."
            )
        return is_valid

    def save_report(self):
        """Lưu báo cáo vào database"""
        if not self.validate_form():
            return

        # Lấy dữ liệu từ form
        ma_bc = self.fieldMABC.text().strip()
        if not ma_bc:
            ma_bc = self._generate_new_code()
            self.fieldMABC.setText(ma_bc)

        thoigiangui = self.fieldThoiGianGui.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        mota = self.fieldMoTa.toPlainText().strip()
        mucdo = self.fieldMucDoNguyHiem.currentText()
        trangthai = self.fieldTrangThai.currentText()

        # Lấy mã cây từ combobox
        cay_text = self.fieldCay.currentText()
        macay = cay_text.split(" (")[0] if " (" in cay_text else ""
        if not macay:
            for ma, ten in SAMPLE_TREES:
                if ten in cay_text:
                    macay = ma
                    break

        try:
            conn = get_db_connection()
            if not conn:
                QMessageBox.warning(self, "Lỗi", "Không thể kết nối database!")
                return

            cursor = conn.cursor()

            # Lấy mã khách hàng từ username
            makhach = self._get_or_create_makhach(cursor)
            if not makhach:
                QMessageBox.warning(self, "Lỗi", "Không xác định được khách hàng!")
                conn.close()
                return

            # Chèn vào database
            cursor.execute("""
                INSERT INTO BAO_CAO_SU_CO (MABC, THOIGIANGUI, MOTA, MUCDONGUYHIEM, 
                                           TRANGTHAI, MAKHACH, MACAY)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ma_bc, thoigiangui, mota, mucdo, trangthai, makhach, macay))

            conn.commit()
            conn.close()

            self.statusBar().showMessage(f"Đã lưu báo cáo {ma_bc}.", 5000)
            QMessageBox.information(self, "Thành công",
                                    f"Đã lưu báo cáo sự cố với mã: {ma_bc}")

            # Reset form và tạo mã mới
            self.reset_form(confirm=False)
            self.generate_ma_bc()

        except pyodbc.Error as e:
            error_msg = str(e)
            if "FOREIGN KEY" in error_msg:
                if "MACAY" in error_msg:
                    QMessageBox.critical(self, "Lỗi", "Mã cây không tồn tại trong hệ thống!")
                elif "MAKHACH" in error_msg:
                    QMessageBox.critical(self, "Lỗi", "Lỗi xác thực khách hàng!")
                else:
                    QMessageBox.critical(self, "Lỗi", f"Lỗi khóa ngoại: {error_msg}")
            elif "UNIQUE" in error_msg:
                QMessageBox.critical(self, "Lỗi", f"Mã báo cáo '{ma_bc}' đã tồn tại!")
            else:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu: {error_msg}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi: {str(e)}")

    def _get_or_create_makhach(self, cursor):
        """Lấy hoặc tạo mã khách hàng từ username"""
        if not self.username:
            return None

        # Tìm khách hàng theo username
        cursor.execute(
            "SELECT MAKHACH FROM KHACH_THAM_QUAN WHERE HOTEN = ? OR TENDANGNHAP = ?",
            self.username, self.username
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        # Nếu chưa có, tạo mới
        cursor.execute("SELECT MAX(MAKHACH) FROM KHACH_THAM_QUAN")
        row = cursor.fetchone()
        if row and row[0]:
            num = int(row[0].replace('KH', '')) + 1
            new_id = f"KH{num:02d}"
        else:
            new_id = "KH01"

        tendangnhap = self.username.lower().replace(' ', '_')
        cursor.execute("""
            INSERT INTO KHACH_THAM_QUAN (MAKHACH, HOTEN, TENDANGNHAP, MATKHAU)
            VALUES (?, ?, ?, ?)
        """, (new_id, self.username, tendangnhap, "khach123"))

        return new_id

    def _generate_new_code(self):
        """Tạo mã mới khi chưa có"""
        try:
            conn = get_db_connection()
            if not conn:
                return "BC01"
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(MABC) FROM BAO_CAO_SU_CO")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                num = int(row[0].replace('BC', '')) + 1
                return f"BC{num:02d}"
            return "BC01"
        except:
            return "BC01"

    def cancel_form(self):
        """Xử lý hủy form"""
        has_data = (
                self.fieldMoTa.toPlainText().strip()
                or self.fieldCay.currentIndex() > 0
                or self.fieldMucDoNguyHiem.currentIndex() > 0
        )
        self.reset_form(confirm=has_data)

    def reset_form(self, confirm=True):
        """Reset form"""
        if confirm:
            reply = QMessageBox.question(
                self, "Xác nhận hủy bỏ",
                "Dữ liệu đang nhập sẽ không được lưu. Bạn có chắc muốn hủy bỏ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.fieldMABC.clear()
        self.fieldThoiGianGui.setDateTime(QtCore.QDateTime.currentDateTime())
        self.fieldCay.setCurrentIndex(0)
        self.fieldMoTa.clear()
        self.fieldMucDoNguyHiem.setCurrentIndex(0)
        self.fieldTrangThai.setCurrentIndex(0)
        for w in (self.fieldCay, self.fieldMoTa, self.fieldMucDoNguyHiem):
            self._reset_field_style(w)
        self.statusBar().showMessage("Đã làm mới biểu mẫu.", 3000)

    # ==================== CÁC HÀM MỞ TRANG ====================
    def open_trang_chu(self):
        try:
            from chinhEx import MainWindow as TrangChu
            self.window = TrangChu(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở trang chủ: {e}")

    def open_quan_ly_cay(self):
        try:
            from quanlycayEx import QuanLyCayWindow
            self.window = QuanLyCayWindow(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở quản lý cây: {e}")

    def open_loai_thuc_vat(self):
        try:
            from LoaithucvatEx import MainWindow as LoaiThucVat
            self.window = LoaiThucVat(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở loài thực vật: {e}")

    def open_ho_thuc_vat(self):
        try:
            from HothucvatEx import MainWindow as HoThucVat
            self.window = HoThucVat(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở họ thực vật: {e}")

    def open_khu_trung_bay(self):
        try:
            from KhutrungbayEx import MainWindow as KhuTrungBay
            self.window = KhuTrungBay(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở khu trưng bày: {e}")

    def open_nhan_vien(self):
        try:
            from NhanvienEx import MainWindow as NhanVien
            self.window = NhanVien(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở nhân viên: {e}")

    def open_phieu_cham_soc(self):
        try:
            from phieu_cham_socEx import PhieuChamSocEx
            self.window = PhieuChamSocEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở phiếu chăm sóc: {e}")

    def open_phieu_khao_sat(self):
        try:
            from phieu_khao_satEx import PhieuKhaoSatEx
            self.window = PhieuKhaoSatEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở phiếu khảo sát: {e}")

    def open_yeu_cau_bao_tri(self):
        try:
            from yeu_cau_bao_triEx import YeuCauBaoTriEx
            self.window = YeuCauBaoTriEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở yêu cầu bảo trì: {e}")

    def open_bao_cao_su_co(self):
        pass


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()