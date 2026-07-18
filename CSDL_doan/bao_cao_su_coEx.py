# bao_cao_su_coEx.py - CHO PHÉP KHÁCH TẠO BÁO CÁO
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

# Danh sách cây mẫu
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

        self.username = username
        self.role = role
        self.is_guest = (role == "Khách tham quan")

        self._setup_ui()
        self._setup_connections()

        self.load_tree_combo()
        self.generate_ma_bc()

        self.statusBar().showMessage("Sẵn sàng.")

    def _setup_ui(self):
        """Thiết lập giao diện ban đầu"""
        self.fieldThoiGianGui.setDateTime(QtCore.QDateTime.currentDateTime())

        self.fieldMoTa.textChanged.connect(self._on_mota_changed)
        self._on_mota_changed()

        if self.username:
            self.userName.setText(self.username)
            self.sidebarUserLabel.setText(f"👤 {self.username}")
        if self.role:
            self.userRole.setText(self.role)
            self.sidebarRoleLabel.setText(self.role)

        # === CHO PHÉP KHÁCH TẠO BÁO CÁO ===
        # Khách vẫn có thể tạo báo cáo, nhưng không cần đăng nhập
        # Chỉ ẩn nút nếu là khách và không có username
        if self.is_guest and not self.username:
            self.btnSave.setVisible(True)
            self.btnSave.setEnabled(True)
            self.fieldCay.setEnabled(True)
            self.fieldMoTa.setEnabled(True)
            self.fieldMucDoNguyHiem.setEnabled(True)
            self.fieldTrangThai.setEnabled(True)
            self.setWindowTitle("BÁO CÁO SỰ CỐ - Khách tham quan")
        elif self.is_guest:
            # Khách đã đăng nhập
            self.btnSave.setVisible(True)
            self.btnSave.setEnabled(True)
            self.fieldCay.setEnabled(True)
            self.fieldMoTa.setEnabled(True)
            self.fieldMucDoNguyHiem.setEnabled(True)
            self.fieldTrangThai.setEnabled(True)
            self.setWindowTitle("BÁO CÁO SỰ CỐ - Khách tham quan")
        else:
            # Admin hoặc nhân viên
            self.btnSave.setVisible(True)
            self.btnSave.setEnabled(True)
            self.fieldCay.setEnabled(True)
            self.fieldMoTa.setEnabled(True)
            self.fieldMucDoNguyHiem.setEnabled(True)
            self.fieldTrangThai.setEnabled(True)
            self.setWindowTitle("BÁO CÁO SỰ CỐ")

    def _setup_connections(self):
        """Kết nối các sự kiện"""
        # Luôn cho phép lưu (kể cả khách)
        self.btnSave.clicked.connect(self.save_report)
        self.btnCancel.clicked.connect(self.cancel_form)

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
        """Load danh sách cây"""
        try:
            conn = get_db_connection()
            if not conn:
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
        """Tạo mã báo cáo tự động - TÌM SỐ NHỎ NHẤT CÒN TRỐNG"""
        try:
            print("=" * 50)
            print("DEBUG: BẮT ĐẦU TẠO MÃ BC")

            conn = get_db_connection()
            if not conn:
                self.fieldMABC.setText("BC01")
                print("DEBUG: Không kết nối DB -> BC01")
                return

            cursor = conn.cursor()

            # Lấy TẤT CẢ mã BC hiện có
            cursor.execute("""
                SELECT MABC 
                FROM BAO_CAO_SU_CO 
                WHERE MABC LIKE 'BC%' 
                ORDER BY MABC
            """)
            rows = cursor.fetchall()
            conn.close()

            print(f"DEBUG: Các mã BC trong DB: {[row[0] for row in rows]}")

            # Nếu chưa có dữ liệu, tạo BC01
            if not rows:
                self.fieldMABC.setText("BC01")
                print("DEBUG: Chưa có dữ liệu -> BC01")
                return

            # Tạo set các số đã tồn tại
            existing_nums = set()
            for row in rows:
                code = row[0]
                if code and code.startswith('BC'):
                    try:
                        num_str = code.replace('BC', '')
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
            new_code = f"BC{num:02d}"
            self.fieldMABC.setText(new_code)
            print(f"DEBUG: ✅ Tạo mã mới: {new_code}")
            print("=" * 50)

        except Exception as e:
            print(f"❌ Lỗi tạo mã BC: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: MAX + 1
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(MABC) FROM BAO_CAO_SU_CO WHERE MABC LIKE 'BC%'")
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    num_str = row[0].replace('BC', '')
                    if num_str.isdigit():
                        new_num = int(num_str) + 1
                        self.fieldMABC.setText(f"BC{new_num:02d}")
                        print(f"DEBUG: Fallback -> BC{new_num:02d}")
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
        """Lưu báo cáo vào database - CHO PHÉP KHÁCH"""
        if not self.validate_form():
            return

        # Lấy mã và kiểm tra trùng
        ma_bc = self.fieldMABC.text().strip()

        # Nếu mã trống, tạo mới
        if not ma_bc:
            self.generate_ma_bc()
            ma_bc = self.fieldMABC.text().strip()

        thoigiangui = self.fieldThoiGianGui.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        mota = self.fieldMoTa.toPlainText().strip()
        mucdo = self.fieldMucDoNguyHiem.currentText()
        trangthai = self.fieldTrangThai.currentText()

        # Lấy mã cây
        cay_text = self.fieldCay.currentText()
        if "(" in cay_text and ")" in cay_text:
            macay = cay_text.split("(")[1].split(")")[0].strip()
        else:
            macay = ""

        try:
            conn = get_db_connection()
            if not conn:
                QMessageBox.warning(self, "Lỗi", "Không thể kết nối database!")
                return

            cursor = conn.cursor()

            # === KIỂM TRA MÃ TRÙNG LẦN CUỐI ===
            cursor.execute("SELECT COUNT(*) FROM BAO_CAO_SU_CO WHERE MABC = ?", (ma_bc,))
            count = cursor.fetchone()[0]

            if count > 0:
                # Nếu trùng, tạo mã mới
                self.generate_ma_bc()
                ma_bc = self.fieldMABC.text().strip()
                # Kiểm tra lại
                cursor.execute("SELECT COUNT(*) FROM BAO_CAO_SU_CO WHERE MABC = ?", (ma_bc,))
                if cursor.fetchone()[0] > 0:
                    conn.close()
                    QMessageBox.critical(self, "Lỗi", "Không thể tạo mã tự động. Vui lòng thử lại!")
                    return

            # === LẤY HOẶC TẠO MÃ KHÁCH HÀNG ===
            makhach = self._get_or_create_makhach(cursor)
            if not makhach:
                # Nếu không có username, tạo khách vãng lai
                makhach = self._create_guest_customer(cursor)
                if not makhach:
                    conn.close()
                    QMessageBox.warning(self, "Lỗi", "Không thể tạo khách hàng!")
                    return

            # Map TRANGTHAI
            trangthai_map = {
                "Mới tiếp nhận": "Chờ xử lý",
                "Chờ xử lý": "Chờ xử lý",
                "Đang xử lý": "Đang xử lý",
                "Đã xử lý": "Đã xử lý",
                "Hoàn thành": "Đã xử lý"
            }
            trangthai_db = trangthai_map.get(trangthai, "Chờ xử lý")

            print("=" * 50)
            print("DEBUG THÔNG TIN LƯU BÁO CÁO:")
            print(f"MABC: {ma_bc}")
            print(f"THOIGIANGUI: {thoigiangui}")
            print(f"MOTA: {mota}")
            print(f"MUCDONGUYHIEM: {mucdo}")
            print(f"TRANGTHAI: {trangthai_db}")
            print(f"MAKHACH: {makhach}")
            print(f"MACAY: {macay}")
            print("=" * 50)

            # Insert
            cursor.execute("""
                INSERT INTO BAO_CAO_SU_CO (MABC, THOIGIANGUI, MOTA, MUCDONGUYHIEM, 
                                           TRANGTHAI, MAKHACH, MACAY)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (ma_bc, thoigiangui, mota, mucdo, trangthai_db, makhach, macay))

            conn.commit()
            conn.close()

            self.statusBar().showMessage(f"Đã lưu báo cáo {ma_bc}.", 5000)
            QMessageBox.information(self, "Thành công ✅",
                                    f"Đã lưu báo cáo sự cố thành công!\n\n"
                                    f"Mã báo cáo: {ma_bc}")

            self.reset_form(confirm=False)
            self.generate_ma_bc()

        except pyodbc.Error as e:
            error_msg = str(e)
            print(f"SQL ERROR: {error_msg}")

            if "PRIMARY KEY" in error_msg or "UNIQUE" in error_msg:
                if "EMAIL" in error_msg or "KHACH_THAM_QUAN" in error_msg:
                    # Lỗi UNIQUE trên EMAIL, thử tạo lại với email khác
                    try:
                        # Tạo khách mới với email duy nhất
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        makhach = self._create_guest_customer(cursor)
                        if makhach:
                            # Thử insert lại với khách mới
                            cursor.execute("""
                                INSERT INTO BAO_CAO_SU_CO (MABC, THOIGIANGUI, MOTA, MUCDONGUYHIEM, 
                                                           TRANGTHAI, MAKHACH, MACAY)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (ma_bc, thoigiangui, mota, mucdo, trangthai_db, makhach, macay))
                            conn.commit()
                            conn.close()
                            QMessageBox.information(self, "Thành công ✅",
                                                   f"Đã lưu báo cáo sự cố thành công!\n\n"
                                                   f"Mã báo cáo: {ma_bc}")
                            self.reset_form(confirm=False)
                            self.generate_ma_bc()
                            return
                    except:
                        pass
                # Tạo mã mới và thông báo
                self.generate_ma_bc()
                QMessageBox.warning(self, "Cảnh báo",
                                    f"Mã đã tồn tại. Đã tạo mã mới: {self.fieldMABC.text()}\n"
                                    f"Vui lòng lưu lại.")
            elif "CK_TrangThai_BCSC" in error_msg:
                QMessageBox.critical(self, "Lỗi CHECK Constraint",
                                     f"❌ Giá trị TRANGTHAI không hợp lệ!\n\n"
                                     f"Giá trị UI: '{trangthai}'\n"
                                     f"Giá trị gửi DB: '{trangthai_db}'\n"
                                     f"Giá trị cho phép: 'Chờ xử lý', 'Đang xử lý', 'Đã xử lý'")
            elif "CK_MucDo_BCSC" in error_msg:
                QMessageBox.critical(self, "Lỗi CHECK Constraint",
                                     f"❌ Giá trị MUCDONGUYHIEM không hợp lệ!\n\n"
                                     f"Giá trị: '{mucdo}'\n"
                                     f"Giá trị cho phép: 'Cao', 'Trung bình', 'Thấp'")
            else:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu:\n{error_msg}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Đã xảy ra lỗi: {str(e)}")

    def _get_or_create_makhach(self, cursor):
        """Lấy hoặc tạo mã khách hàng từ username"""
        if not self.username:
            return None

        cursor.execute(
            "SELECT MAKHACH FROM KHACH_THAM_QUAN WHERE HOTEN = ? OR TENDANGNHAP = ?",
            self.username, self.username
        )
        row = cursor.fetchone()
        if row:
            return row[0]

        # Tạo mới với email duy nhất
        return self._create_guest_customer(cursor, self.username)

    def _create_guest_customer(self, cursor, name=None):
        """Tạo khách hàng mới (cho khách vãng lai)"""
        try:
            # Lấy MAX MAKHACH
            cursor.execute("SELECT MAX(MAKHACH) FROM KHACH_THAM_QUAN")
            row = cursor.fetchone()
            if row and row[0]:
                num = int(row[0].replace('KH', '')) + 1
                new_id = f"KH{num:02d}"
            else:
                new_id = "KH01"

            # Tạo tên và email duy nhất
            if name:
                hoten = name
                tendangnhap = name.lower().replace(' ', '_')
                email = f"{tendangnhap}_{datetime.now().strftime('%Y%m%d%H%M%S')}@guest.com"
            else:
                hoten = "Khách vãng lai"
                tendangnhap = f"guest_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                email = f"{tendangnhap}@guest.com"

            cursor.execute("""
                INSERT INTO KHACH_THAM_QUAN (MAKHACH, HOTEN, DIENTHOAI, EMAIL, TENDANGNHAP, MATKHAU)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_id, hoten, '0900000000', email, tendangnhap, 'guest123'))

            return new_id

        except Exception as e:
            print(f"Lỗi tạo khách hàng: {e}")
            return None

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