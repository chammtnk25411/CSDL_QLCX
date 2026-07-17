# yeu_cau_bao_triEx.py - Hoàn chỉnh với phân quyền
import sys
from datetime import datetime

import pyodbc
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem
from PyQt6.QtCore import QDate

import config
from yeu_cau_bao_tri import Ui_MainWindow


def get_db_connection():
    """Kết nối đến SQL Server"""
    try:
        conn = pyodbc.connect(
            f'DRIVER={{ODBC Driver 17 for SQL Server}};'
            f'SERVER={config.DB_SERVER};'
            f'DATABASE={config.DB_NAME};'
            f'Trusted_Connection=yes;'
        )
        return conn
    except Exception as e:
        raise Exception(f"Không thể kết nối database: {str(e)}")


class YeuCauBaoTriEx(QMainWindow):
    def __init__(self, username=None, role=None):
        super().__init__()
        self.username = username
        self.role = role

        # ===== PHÂN QUYỀN =====
        self.is_guest = (role == "Khách tham quan")
        self.is_admin_or_staff = (role in ["Quản trị viên", "Nhân viên"])

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Cập nhật thông tin người dùng
        if username:
            self.ui.userName.setText(username)
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if role:
            self.ui.userRole.setText(role)
            self.ui.sidebarRoleLabel.setText(role)

        self.setup_defaults()
        self.connect_signals()
        self.load_combo_data()
        self.setup_permissions()

    def setup_defaults(self):
        """Thiết lập mặc định"""
        self.ui.fieldNgayTao.setDate(QDate.currentDate())
        self.generate_ma_bt()

    def setup_permissions(self):
        """Phân quyền - Ẩn nút Lưu nếu là khách"""
        if self.is_guest:
            # Khách hàng: Ẩn nút Lưu và Hủy (chỉ xem)
            if hasattr(self.ui, "btnSave"):
                self.ui.btnSave.setVisible(False)
                self.ui.btnSave.setEnabled(False)
            if hasattr(self.ui, "btnCancel"):
                self.ui.btnCancel.setVisible(False)
                self.ui.btnCancel.setEnabled(False)
            # Disable các field nhập
            self.ui.fieldCay.setEnabled(False)
            self.ui.fieldNgayTao.setEnabled(False)
            self.ui.fieldNoiDungBaoTri.setEnabled(False)
            self.ui.fieldMucDoUuTien.setEnabled(False)
            self.ui.fieldTrangThai.setEnabled(False)
            self.ui.fieldNhanVienPhuTrach.setEnabled(False)
            self.setWindowTitle("YÊU CẦU BẢO TRÌ - Chế độ xem")
        else:
            if hasattr(self.ui, "btnSave"):
                self.ui.btnSave.setVisible(True)
                self.ui.btnSave.setEnabled(True)
            if hasattr(self.ui, "btnCancel"):
                self.ui.btnCancel.setVisible(True)
                self.ui.btnCancel.setEnabled(True)
            self.ui.fieldCay.setEnabled(True)
            self.ui.fieldNgayTao.setEnabled(True)
            self.ui.fieldNoiDungBaoTri.setEnabled(True)
            self.ui.fieldMucDoUuTien.setEnabled(True)
            self.ui.fieldTrangThai.setEnabled(True)
            self.ui.fieldNhanVienPhuTrach.setEnabled(True)
            self.setWindowTitle("YÊU CẦU BẢO TRÌ")

    def connect_signals(self):
        """Kết nối sự kiện"""
        # Các nút chức năng - chỉ kết nối nếu không phải khách
        if not self.is_guest:
            self.ui.btnCancel.clicked.connect(self.handle_cancel)
            self.ui.btnSave.clicked.connect(self.handle_save)

        self.ui.btnMenuToggle.clicked.connect(self.handle_toggle_menu)
        self.ui.fieldNoiDungBaoTri.textChanged.connect(self.handle_char_counter)

        # ===== KẾT NỐI CÁC NÚT SIDEBAR =====
        if hasattr(self.ui, "navTrangChu"):
            self.ui.navTrangChu.clicked.connect(self.open_trang_chu)
        if hasattr(self.ui, "navQuanLyCay"):
            self.ui.navQuanLyCay.clicked.connect(self.open_quan_ly_cay)
        if hasattr(self.ui, "navLoaiThucVat"):
            self.ui.navLoaiThucVat.clicked.connect(self.open_loai_thuc_vat)
        if hasattr(self.ui, "navHoThucVat"):
            self.ui.navHoThucVat.clicked.connect(self.open_ho_thuc_vat)
        if hasattr(self.ui, "navKhuTrungBay"):
            self.ui.navKhuTrungBay.clicked.connect(self.open_khu_trung_bay)
        if hasattr(self.ui, "navNhanVien"):
            self.ui.navNhanVien.clicked.connect(self.open_nhan_vien)
        if hasattr(self.ui, "navPhieuChamSoc"):
            self.ui.navPhieuChamSoc.clicked.connect(self.open_phieu_cham_soc)
        if hasattr(self.ui, "navPhieuKhaoSat"):
            self.ui.navPhieuKhaoSat.clicked.connect(self.open_phieu_khao_sat)
        if hasattr(self.ui, "navBaoCaoSuCo"):
            self.ui.navBaoCaoSuCo.clicked.connect(self.open_bao_cao_su_co)

    def load_combo_data(self):
        """Load dữ liệu vào combobox từ database"""
        try:
            conn = get_db_connection()
            if not conn:
                return

            cursor = conn.cursor()

            # Load cây
            cursor.execute("SELECT MACAY, TENCAY FROM CAY ORDER BY MACAY")
            rows = cursor.fetchall()
            self.ui.fieldCay.clear()
            self.ui.fieldCay.addItem("Chọn cây")
            for row in rows:
                self.ui.fieldCay.addItem(f"{row[1]} ({row[0]})")

            # Load nhân viên
            cursor.execute("SELECT MANV, HOTEN FROM NHAN_VIEN ORDER BY MANV")
            rows = cursor.fetchall()
            self.ui.fieldNhanVienPhuTrach.clear()
            self.ui.fieldNhanVienPhuTrach.addItem("Chọn nhân viên")
            for row in rows:
                self.ui.fieldNhanVienPhuTrach.addItem(f"{row[1]} ({row[0]})")

            conn.close()

        except Exception as e:
            print(f"Lỗi load combobox: {e}")

    def generate_ma_bt(self):
        """Tạo mã bảo trì tự động"""
        try:
            conn = get_db_connection()
            if not conn:
                self.ui.fieldMABT.setText("BT001")
                return

            cursor = conn.cursor()
            cursor.execute("SELECT MAX(MABT) FROM YEU_CAU_BAO_TRI")
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                last_id = row[0]
                if last_id.startswith('BT'):
                    num = int(last_id.replace('BT', '')) + 1
                    self.ui.fieldMABT.setText(f"BT{num:03d}")
                else:
                    self.ui.fieldMABT.setText("BT001")
            else:
                self.ui.fieldMABT.setText("BT001")
        except:
            self.ui.fieldMABT.setText("BT001")

    def handle_char_counter(self):
        """Hàm đếm và giới hạn số ký tự trong ô nội dung bảo trì"""
        text = self.ui.fieldNoiDungBaoTri.toPlainText()
        max_length = 500
        current_length = len(text)

        if current_length > max_length:
            text = text[:max_length]
            self.ui.fieldNoiDungBaoTri.setPlainText(text)

            cursor = self.ui.fieldNoiDungBaoTri.textCursor()
            cursor.setPosition(max_length)
            self.ui.fieldNoiDungBaoTri.setTextCursor(cursor)
            current_length = max_length

        self.ui.charCounter1.setText(f"{current_length}/{max_length}")

        # Đổi màu khi gần đầy
        if current_length >= max_length:
            self.ui.charCounter1.setStyleSheet("color: #e53935; font-size: 11px; font-weight: bold;")
        elif current_length >= int(max_length * 0.9):
            self.ui.charCounter1.setStyleSheet("color: #e08a1f; font-size: 11px;")
        else:
            self.ui.charCounter1.setStyleSheet("color: #9aa39d; font-size: 11px;")

    def handle_toggle_menu(self):
        """Hàm ẩn/hiện Sidebar khi nhấn nút Toggle"""
        is_visible = self.ui.sidebarFrame.isVisible()
        self.ui.sidebarFrame.setVisible(not is_visible)

    def handle_cancel(self):
        """Hàm xử lý khi nhấn nút Hủy bỏ - CHỈ ADMIN/NHÂN VIÊN"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền hủy bỏ!")
            return

        has_data = (
                self.ui.fieldCay.currentIndex() > 0 or
                self.ui.fieldNoiDungBaoTri.toPlainText().strip() or
                self.ui.fieldMucDoUuTien.currentIndex() > 0 or
                self.ui.fieldNhanVienPhuTrach.currentIndex() > 0
        )

        if has_data:
            reply = QMessageBox.question(
                self,
                'Xác nhận',
                'Bạn có chắc chắn muốn hủy bỏ? Các thay đổi chưa lưu sẽ bị mất.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.reset_form()
        else:
            self.close()

    def reset_form(self):
        """Reset form về trạng thái ban đầu"""
        self.ui.fieldNgayTao.setDate(QDate.currentDate())
        self.ui.fieldCay.setCurrentIndex(0)
        self.ui.fieldNoiDungBaoTri.clear()
        self.ui.fieldMucDoUuTien.setCurrentIndex(0)
        self.ui.fieldTrangThai.setCurrentIndex(0)
        self.ui.fieldNhanVienPhuTrach.setCurrentIndex(0)
        self.generate_ma_bt()
        self.ui.statusBar().showMessage("Đã làm mới biểu mẫu.", 3000)

    def handle_save(self):
        """Hàm xử lý khi nhấn nút Lưu - CHỈ ADMIN/NHÂN VIÊN"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền tạo yêu cầu bảo trì!")
            return

        # Lấy dữ liệu từ form
        ma_bt = self.ui.fieldMABT.text().strip()
        ngay_tao = self.ui.fieldNgayTao.date().toString("yyyy-MM-dd")
        cay_text = self.ui.fieldCay.currentText()
        noi_dung = self.ui.fieldNoiDungBaoTri.toPlainText().strip()
        muc_do = self.ui.fieldMucDoUuTien.currentText()
        trang_thai = self.ui.fieldTrangThai.currentText()
        nhan_vien_text = self.ui.fieldNhanVienPhuTrach.currentText()

        # Kiểm tra tính hợp lệ
        if self.ui.fieldCay.currentIndex() <= 0:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn cây!")
            return

        if not noi_dung:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập nội dung bảo trì!")
            return

        if self.ui.fieldMucDoUuTien.currentIndex() <= 0:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn mức độ ưu tiên!")
            return

        if self.ui.fieldNhanVienPhuTrach.currentIndex() <= 0:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn nhân viên phụ trách!")
            return

        # Lấy mã cây từ text
        macay = ""
        if "(" in cay_text and ")" in cay_text:
            macay = cay_text.split("(")[1].split(")")[0].strip()

        # Lấy mã nhân viên từ text
        manv = ""
        if "(" in nhan_vien_text and ")" in nhan_vien_text:
            manv = nhan_vien_text.split("(")[1].split(")")[0].strip()

        try:
            conn = get_db_connection()
            if not conn:
                QMessageBox.warning(self, "Lỗi", "Không thể kết nối database!")
                return

            cursor = conn.cursor()

            # Chèn vào database
            cursor.execute("""
                INSERT INTO YEU_CAU_BAO_TRI (MABT, MACAY, NGAYTAO, NOIDUNGBAOTRI, 
                                             MUCDOUUTIEN, TRANGTHAI, MANV)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ma_bt,
                macay,
                ngay_tao,
                noi_dung,
                muc_do,
                trang_thai,
                manv
            ))

            conn.commit()
            conn.close()

            QMessageBox.information(self, "Thành công ✅",
                                    f"Đã lưu yêu cầu bảo trì thành công!\n\n"
                                    f"Mã bảo trì: {ma_bt}\n"
                                    f"- Cây: {cay_text}\n"
                                    f"- Mức độ: {muc_do}\n"
                                    f"- Nhân viên: {nhan_vien_text}\n"
                                    f"- Trạng thái: {trang_thai}"
                                    )

            # Reset form
            self.reset_form()
            self.generate_ma_bt()

        except pyodbc.Error as e:
            error_msg = str(e)
            if "FOREIGN KEY" in error_msg:
                if "MACAY" in error_msg:
                    QMessageBox.critical(self, "Lỗi", "Mã cây không tồn tại trong hệ thống!")
                elif "MANV" in error_msg:
                    QMessageBox.critical(self, "Lỗi", "Mã nhân viên không tồn tại trong hệ thống!")
                else:
                    QMessageBox.critical(self, "Lỗi", f"Lỗi khóa ngoại: {error_msg}")
            elif "UNIQUE" in error_msg:
                QMessageBox.critical(self, "Lỗi", f"Mã bảo trì '{ma_bt}' đã tồn tại!")
            else:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu: {error_msg}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi: {str(e)}")

    # ==================== CÁC HÀM CHUYỂN TRANG ====================
    def open_trang_chu(self):
        try:
            from chinhEx import MainWindow as TrangChu
            self.window = TrangChu(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở trang chủ: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở trang chủ:\n{str(e)}")

    def open_quan_ly_cay(self):
        try:
            from quanlycayEx import QuanLyCayWindow
            self.window = QuanLyCayWindow(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở quản lý cây: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Quản lý cây:\n{str(e)}")

    def open_loai_thuc_vat(self):
        try:
            from LoaithucvatEx import MainWindow as LoaiThucVat
            self.window = LoaiThucVat(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở loài thực vật: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Loài thực vật:\n{str(e)}")

    def open_ho_thuc_vat(self):
        try:
            from HothucvatEx import MainWindow as HoThucVat
            self.window = HoThucVat(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở họ thực vật: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Họ thực vật:\n{str(e)}")

    def open_khu_trung_bay(self):
        try:
            from KhutrungbayEx import MainWindow as KhuTrungBay
            self.window = KhuTrungBay(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở khu trưng bày: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Khu trưng bày:\n{str(e)}")

    def open_nhan_vien(self):
        try:
            from NhanvienEx import MainWindow as NhanVien
            self.window = NhanVien(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở nhân viên: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Nhân viên:\n{str(e)}")

    def open_phieu_cham_soc(self):
        try:
            from phieu_cham_socEx import PhieuChamSocEx
            self.window = PhieuChamSocEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở phiếu chăm sóc: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Phiếu chăm sóc:\n{str(e)}")

    def open_phieu_khao_sat(self):
        try:
            from phieu_khao_satEx import PhieuKhaoSatEx
            self.window = PhieuKhaoSatEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở phiếu khảo sát: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Phiếu khảo sát:\n{str(e)}")

    def open_bao_cao_su_co(self):
        try:
            from bao_cao_su_coEx import MainWindow as BaoCaoSuCo
            self.window = BaoCaoSuCo(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở báo cáo sự cố: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể mở Báo cáo sự cố:\n{str(e)}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YeuCauBaoTriEx(username="Admin", role="Quản trị viên")
    window.show()
    sys.exit(app.exec())