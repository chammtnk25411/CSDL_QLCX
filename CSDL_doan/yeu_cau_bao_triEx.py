# yeu_cau_bao_triEx.py - SỬA MÃ THÀNH YC
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

        self.is_guest = (role == "Khách tham quan")
        self.is_admin_or_staff = (role in ["Quản trị viên", "Nhân viên"])

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

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
        """Phân quyền"""
        if self.is_guest:
            if hasattr(self.ui, "btnSave"):
                self.ui.btnSave.setVisible(False)
                self.ui.btnSave.setEnabled(False)
            if hasattr(self.ui, "btnCancel"):
                self.ui.btnCancel.setVisible(False)
                self.ui.btnCancel.setEnabled(False)
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
        if not self.is_guest:
            self.ui.btnCancel.clicked.connect(self.handle_cancel)
            self.ui.btnSave.clicked.connect(self.handle_save)

        self.ui.btnMenuToggle.clicked.connect(self.handle_toggle_menu)
        self.ui.fieldNoiDungBaoTri.textChanged.connect(self.handle_char_counter)

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
        """Load dữ liệu vào combobox"""
        try:
            conn = get_db_connection()
            if not conn:
                return

            cursor = conn.cursor()

            cursor.execute("SELECT MACAY, TENCAY FROM CAY ORDER BY MACAY")
            rows = cursor.fetchall()
            self.ui.fieldCay.clear()
            self.ui.fieldCay.addItem("Chọn cây")
            for row in rows:
                self.ui.fieldCay.addItem(f"{row[1]} ({row[0]})")

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
        """Tạo mã bảo trì tự động - Định dạng YC (Yêu Cầu)"""
        try:
            conn = get_db_connection()
            if not conn:
                self.ui.fieldMABT.setText("YC01")
                return

            cursor = conn.cursor()

            # Lấy tất cả mã YC hiện có
            cursor.execute("""
                SELECT MABT 
                FROM YEU_CAU_BAO_TRI 
                WHERE MABT LIKE 'YC%' 
                ORDER BY MABT
            """)
            rows = cursor.fetchall()
            conn.close()

            print(f"DEBUG: Các mã YC trong DB: {[row[0] for row in rows]}")

            # Nếu chưa có dữ liệu, tạo YC01
            if not rows:
                self.ui.fieldMABT.setText("YC01")
                print("DEBUG: Chưa có dữ liệu -> tạo YC01")
                return

            # Tạo set các số đã tồn tại
            existing_nums = set()
            for row in rows:
                code = row[0]
                if code and code.startswith('YC'):
                    try:
                        num_str = code.replace('YC', '')
                        if num_str.isdigit():
                            existing_nums.add(int(num_str))
                    except:
                        continue

            print(f"DEBUG: Các số đã tồn tại: {sorted(existing_nums)}")

            # Tìm số nhỏ nhất còn trống (bắt đầu từ 1)
            num = 1
            while num in existing_nums:
                num += 1

            # Tạo mã mới với 2 chữ số
            new_code = f"YC{num:02d}"
            self.ui.fieldMABT.setText(new_code)
            print(f"DEBUG: ✅ Tạo mã mới: {new_code}")

        except Exception as e:
            print(f"❌ Lỗi tạo mã YC: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: MAX + 1
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(MABT) FROM YEU_CAU_BAO_TRI WHERE MABT LIKE 'YC%'")
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    num_str = row[0].replace('YC', '')
                    if num_str.isdigit():
                        self.ui.fieldMABT.setText(f"YC{int(num_str) + 1:02d}")
                    else:
                        self.ui.fieldMABT.setText("YC01")
                else:
                    self.ui.fieldMABT.setText("YC01")
            except:
                self.ui.fieldMABT.setText("YC01")

    def handle_char_counter(self):
        """Đếm ký tự"""
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

        if current_length >= max_length:
            self.ui.charCounter1.setStyleSheet("color: #e53935; font-size: 11px; font-weight: bold;")
        elif current_length >= int(max_length * 0.9):
            self.ui.charCounter1.setStyleSheet("color: #e08a1f; font-size: 11px;")
        else:
            self.ui.charCounter1.setStyleSheet("color: #9aa39d; font-size: 11px;")

    def handle_toggle_menu(self):
        """Ẩn/hiện Sidebar"""
        is_visible = self.ui.sidebarFrame.isVisible()
        self.ui.sidebarFrame.setVisible(not is_visible)

    def handle_cancel(self):
        """Hủy bỏ"""
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
        """Reset form"""
        self.ui.fieldNgayTao.setDate(QDate.currentDate())
        self.ui.fieldCay.setCurrentIndex(0)
        self.ui.fieldNoiDungBaoTri.clear()
        self.ui.fieldMucDoUuTien.setCurrentIndex(0)
        self.ui.fieldTrangThai.setCurrentIndex(0)
        self.ui.fieldNhanVienPhuTrach.setCurrentIndex(0)
        self.generate_ma_bt()

    def handle_save(self):
        """Lưu yêu cầu bảo trì"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền tạo yêu cầu bảo trì!")
            return

        ma_bt = self.ui.fieldMABT.text().strip()
        ngay_tao = self.ui.fieldNgayTao.date().toString("yyyy-MM-dd")
        cay_text = self.ui.fieldCay.currentText()
        noi_dung = self.ui.fieldNoiDungBaoTri.toPlainText().strip()
        muc_do = self.ui.fieldMucDoUuTien.currentText()
        trang_thai_ui = self.ui.fieldTrangThai.currentText()
        nhan_vien_text = self.ui.fieldNhanVienPhuTrach.currentText()

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

        # Map TRANGTHAI
        trang_thai_map = {
            "Mới tạo": "Chờ xử lý",
            "Đang xử lý": "Đang xử lý",
            "Hoàn thành": "Đã xử lý"
        }
        trang_thai = trang_thai_map.get(trang_thai_ui, "Chờ xử lý")

        # Lấy mã cây
        macay = ""
        if "(" in cay_text and ")" in cay_text:
            macay = cay_text.split("(")[1].split(")")[0].strip()

        # Lấy mã nhân viên
        manv = ""
        if "(" in nhan_vien_text and ")" in nhan_vien_text:
            manv = nhan_vien_text.split("(")[1].split(")")[0].strip()

        try:
            conn = get_db_connection()
            if not conn:
                QMessageBox.warning(self, "Lỗi", "Không thể kết nối database!")
                return

            cursor = conn.cursor()

            # Kiểm tra mã trùng
            cursor.execute("SELECT COUNT(*) FROM YEU_CAU_BAO_TRI WHERE MABT = ?", (ma_bt,))
            if cursor.fetchone()[0] > 0:
                self.generate_ma_bt()
                ma_bt = self.ui.fieldMABT.text().strip()

            print("=" * 50)
            print("DEBUG THÔNG TIN LƯU YÊU CẦU BẢO TRÌ:")
            print(f"MABT: {ma_bt}")
            print(f"MACAY: {macay}")
            print(f"NGAYTAO: {ngay_tao}")
            print(f"NOIDUNGBAOTRI: {noi_dung}")
            print(f"MUCDOUUTIEN: {muc_do}")
            print(f"TRANGTHAI: {trang_thai}")
            print(f"MANV: {manv}")
            print("=" * 50)

            # Insert
            cursor.execute("""
                INSERT INTO YEU_CAU_BAO_TRI (MABT, MACAY, NGAYTAO, NOIDUNGBAOTRI, 
                                             MUCDOUUTIEN, TRANGTHAI, MANV)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ma_bt, macay, ngay_tao, noi_dung, muc_do, trang_thai, manv))

            conn.commit()
            conn.close()

            QMessageBox.information(self, "Thành công ✅",
                                    f"Đã lưu yêu cầu bảo trì thành công!\n\n"
                                    f"Mã bảo trì: {ma_bt}")

            self.reset_form()
            self.generate_ma_bt()

        except pyodbc.Error as e:
            error_msg = str(e)
            print(f"SQL ERROR: {error_msg}")

            if "PRIMARY KEY" in error_msg or "UNIQUE" in error_msg:
                self.generate_ma_bt()
                QMessageBox.warning(self, "Cảnh báo",
                                    f"Mã đã tồn tại. Đã tạo mã mới: {self.ui.fieldMABT.text()}")
            elif "CK_TrangThai_YCBT" in error_msg:
                QMessageBox.critical(self, "Lỗi CHECK Constraint",
                                     f"❌ Giá trị TRANGTHAI không hợp lệ!\n\n"
                                     f"Giá trị UI: '{trang_thai_ui}'\n"
                                     f"Giá trị gửi DB: '{trang_thai}'\n"
                                     f"Giá trị cho phép: 'Chờ xử lý', 'Đang xử lý', 'Đã xử lý'")
            elif "CK_MucDo_YCBT" in error_msg:
                QMessageBox.critical(self, "Lỗi CHECK Constraint",
                                     f"❌ Giá trị MUCDOUUTIEN không hợp lệ!\n\n"
                                     f"Giá trị: '{muc_do}'\n"
                                     f"Giá trị cho phép: 'Khẩn cấp', 'Cao', 'Trung bình', 'Thấp'")
            else:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu:\n{error_msg}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi: {str(e)}")

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

    def open_bao_cao_su_co(self):
        try:
            from bao_cao_su_coEx import MainWindow as BaoCaoSuCo
            self.window = BaoCaoSuCo(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở báo cáo sự cố: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YeuCauBaoTriEx(username="Admin", role="Quản trị viên")
    window.show()
    sys.exit(app.exec())