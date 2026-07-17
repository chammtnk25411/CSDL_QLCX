# phieuthongtinEx.py - Sửa lỗi setVisible trên layout
import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.uic import loadUi

import pyodbc
import config


def get_db_connection():
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
                return conn
            except:
                continue
        return None
    except:
        return None


class PhieuThongTinCayDialog(QDialog):
    """Dialog thêm/sửa thông tin cây"""

    def __init__(self, parent=None, edit_mode=False, data=None):
        super().__init__(parent)
        self.edit_mode = edit_mode
        self.data = data
        self.result_data = None

        self.setWindowTitle("Sửa thông tin cây" if edit_mode else "Thêm cây mới")
        self.resize(800, 550)

        # Load UI
        ui_path = os.path.join(os.path.dirname(__file__), 'phieuthongtin.ui')
        try:
            loadUi(ui_path, self)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể load UI: {str(e)}")
            self.reject()
            return

        # Ẩn các trường không dùng - SỬA: KHÔNG ẨN LAYOUT
        self.hide_unused_fields()

        # Load dữ liệu combobox từ database
        self.load_combobox_data()

        # Nếu là sửa, điền dữ liệu
        if edit_mode and data:
            self.fill_data(data)
        else:
            self.generate_auto_id()

        # Kết nối sự kiện
        if hasattr(self, 'btnLuu'):
            self.btnLuu.clicked.connect(self.save_data)
        if hasattr(self, 'btnHuy'):
            self.btnHuy.clicked.connect(self.reject)

    def hide_unused_fields(self):
        """Ẩn các trường không có trong database - CHỈ ẨN WIDGET, KHÔNG ẨN LAYOUT"""
        # Ẩn Tuổi cây - chỉ ẩn các widget
        if hasattr(self, 'lblTuoiCay'):
            self.lblTuoiCay.setVisible(False)
        if hasattr(self, 'txtTuoiCay'):
            self.txtTuoiCay.setVisible(False)
        if hasattr(self, 'lblDonViTuoi'):
            self.lblDonViTuoi.setVisible(False)
        # KHÔNG ẨN layTuoiInput - nó là QHBoxLayout, không có setVisible

        # Ẩn Tình trạng sức khỏe - chỉ ẩn các widget
        if hasattr(self, 'lblTinhTrangSucKhoe'):
            self.lblTinhTrangSucKhoe.setVisible(False)
        if hasattr(self, 'cboTinhTrangSucKhoe'):
            self.cboTinhTrangSucKhoe.setVisible(False)

    def load_combobox_data(self):
        """Load dữ liệu vào combobox từ database - XÓA DỮ LIỆU MẪU"""
        try:
            conn = get_db_connection()
            if not conn:
                print("⚠️ Không kết nối được database")
                return

            cursor = conn.cursor()

            # ===== LOAD LOẠI THỰC VẬT =====
            if hasattr(self, 'cboLoaiThucVat'):
                cursor.execute("SELECT MALOAI, TENTHUONGGOI FROM LOAI_THUC_VAT ORDER BY MALOAI")
                rows = cursor.fetchall()

                # Xóa tất cả dữ liệu cũ
                self.cboLoaiThucVat.clear()
                self.cboLoaiThucVat.addItem("Chọn loại thực vật", "")

                for row in rows:
                    self.cboLoaiThucVat.addItem(f"{row[0]} - {row[1]}", row[0])
                print(f"✅ Loaded {len(rows)} loại thực vật")

            # ===== LOAD KHU TRƯNG BÀY =====
            if hasattr(self, 'cboKhuTrungBay'):
                cursor.execute("SELECT MAKHU, TENKHU FROM KHU_TRUNG_BAY ORDER BY MAKHU")
                rows = cursor.fetchall()

                self.cboKhuTrungBay.clear()
                self.cboKhuTrungBay.addItem("Chọn khu trưng bày", "")

                for row in rows:
                    self.cboKhuTrungBay.addItem(f"{row[0]} - {row[1]}", row[0])
                print(f"✅ Loaded {len(rows)} khu trưng bày")

            conn.close()
        except Exception as e:
            print(f"❌ Lỗi load combobox: {e}")

    def generate_auto_id(self):
        """Tạo mã tự động"""
        try:
            conn = get_db_connection()
            if not conn:
                if hasattr(self, 'txtMaCay'):
                    self.txtMaCay.setText("C0001")
                return

            cursor = conn.cursor()
            cursor.execute("SELECT MAX(MACAY) FROM CAY")
            row = cursor.fetchone()
            conn.close()

            if hasattr(self, 'txtMaCay'):
                if row and row[0]:
                    last_id = row[0]
                    if last_id.startswith('C'):
                        num = int(last_id.replace('C', '')) + 1
                        self.txtMaCay.setText(f"C{num:04d}")
                    else:
                        self.txtMaCay.setText("C0001")
                else:
                    self.txtMaCay.setText("C0001")
        except:
            if hasattr(self, 'txtMaCay'):
                self.txtMaCay.setText("C0001")

    def fill_data(self, data):
        """Điền dữ liệu vào form khi sửa"""
        if not data:
            return

        print("=" * 60)
        print("🔄 ĐIỀN DỮ LIỆU VÀO FORM")
        print("=" * 60)

        # 1. Mã cây
        if hasattr(self, 'txtMaCay'):
            value = data.get('MACAY', '')
            self.txtMaCay.setText(str(value))
            self.txtMaCay.setEnabled(False)
            print(f"  📌 Mã cây: {value}")

        # 2. Tên cây
        if hasattr(self, 'txtTenCay'):
            value = data.get('TENCAY', '')
            self.txtTenCay.setText(str(value))
            print(f"  📌 Tên cây: {value}")

        # 3. Loại thực vật
        if hasattr(self, 'cboLoaiThucVat'):
            value = data.get('MALOAI', '')
            print(f"  📌 MALOAI cần chọn: {value}")

            if value:
                found = False
                for i in range(self.cboLoaiThucVat.count()):
                    item_data = self.cboLoaiThucVat.itemData(i)
                    if str(item_data) == str(value):
                        self.cboLoaiThucVat.setCurrentIndex(i)
                        found = True
                        print(f"  ✅ Đã chọn: {self.cboLoaiThucVat.currentText()}")
                        break
                if not found:
                    print(f"  ❌ Không tìm thấy MALOAI: {value}")

        # 4. Khu trưng bày
        if hasattr(self, 'cboKhuTrungBay'):
            value = data.get('MAKHU', '')
            print(f"  📌 MAKHU cần chọn: {value}")

            if value:
                found = False
                for i in range(self.cboKhuTrungBay.count()):
                    item_data = self.cboKhuTrungBay.itemData(i)
                    if str(item_data) == str(value):
                        self.cboKhuTrungBay.setCurrentIndex(i)
                        found = True
                        print(f"  ✅ Đã chọn: {self.cboKhuTrungBay.currentText()}")
                        break
                if not found:
                    print(f"  ❌ Không tìm thấy MAKHU: {value}")

        # 5. Ngày trồng
        if hasattr(self, 'dteNgayTrong'):
            value = data.get('NGAYTRONG', '')
            print(f"  📌 NGAYTRONG: {value}")

            if value:
                try:
                    if isinstance(value, str):
                        if '-' in value:
                            parts = value.split('-')
                            if len(parts) == 3:
                                qdate = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
                            else:
                                qdate = QDate.fromString(value, "yyyy-MM-dd")
                        else:
                            qdate = QDate.fromString(value, "yyyy-MM-dd")
                    elif hasattr(value, 'year'):
                        qdate = QDate(value.year, value.month, value.day)
                    else:
                        qdate = QDate.fromString(str(value), "yyyy-MM-dd")

                    if qdate.isValid():
                        self.dteNgayTrong.setDate(qdate)
                        print(f"  ✅ Đã set ngày: {qdate.toString('dd/MM/yyyy')}")
                    else:
                        print(f"  ❌ Ngày không hợp lệ: {value}")
                except Exception as e:
                    print(f"  ❌ Lỗi set ngày: {e}")

        # 6. Chiều cao
        if hasattr(self, 'txtChieuCao'):
            value = data.get('CHIEUCAO', '')
            if value:
                self.txtChieuCao.setText(str(value))
                print(f"  📌 Chiều cao: {value}")

        # 7. Đường kính
        if hasattr(self, 'txtDuongKinh'):
            value = data.get('DUONGKINH', '')
            if value:
                self.txtDuongKinh.setText(str(value))
                print(f"  📌 Đường kính: {value}")

        # 8. Tình trạng sinh trưởng
        if hasattr(self, 'cboTinhTrangSinhTruong'):
            value = data.get('TINHTRANGSINHTRUONG', '')
            print(f"  📌 Tình trạng sinh trưởng DB: {value}")

            # Xóa dữ liệu mẫu và thêm các giá trị hợp lệ
            self.cboTinhTrangSinhTruong.clear()
            valid_status = [
                "Chọn tình trạng",
                "Sinh trưởng tốt",
                "Cần theo dõi",
                "Bị sâu bệnh",
                "Nguy cấp",
                "Đang phục hồi"
            ]
            for status in valid_status:
                self.cboTinhTrangSinhTruong.addItem(status)

            if value:
                found = False
                for i in range(self.cboTinhTrangSinhTruong.count()):
                    if self.cboTinhTrangSinhTruong.itemText(i) == value:
                        self.cboTinhTrangSinhTruong.setCurrentIndex(i)
                        found = True
                        print(f"  ✅ Đã chọn tình trạng: {value}")
                        break
                if not found:
                    print(f"  ❌ Không tìm thấy tình trạng: {value}")

        # 9. Trạng thái hoạt động
        if hasattr(self, 'cboTrangThaiHoatDong'):
            value = data.get('TRANGTHAIHOATDONG', '')
            print(f"  📌 Trạng thái hoạt động DB: {value}")

            # Xóa dữ liệu mẫu và thêm các giá trị hợp lệ
            self.cboTrangThaiHoatDong.clear()
            valid_status = [
                "Chọn trạng thái",
                "Đang hoạt động",
                "Đã di dời",
                "Đã chết"
            ]
            for status in valid_status:
                self.cboTrangThaiHoatDong.addItem(status)

            if value:
                found = False
                for i in range(self.cboTrangThaiHoatDong.count()):
                    if self.cboTrangThaiHoatDong.itemText(i) == value:
                        self.cboTrangThaiHoatDong.setCurrentIndex(i)
                        found = True
                        print(f"  ✅ Đã chọn trạng thái: {value}")
                        break
                if not found:
                    print(f"  ❌ Không tìm thấy trạng thái: {value}")

        print("=" * 60)
        print("✅ HOÀN TẤT ĐIỀN DỮ LIỆU")
        print("=" * 60)

    def validate_data(self):
        """Kiểm tra dữ liệu"""
        if hasattr(self, 'txtMaCay') and not self.txtMaCay.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập mã cây!")
            return False

        if hasattr(self, 'txtTenCay') and not self.txtTenCay.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên cây!")
            return False

        if hasattr(self, 'cboLoaiThucVat') and self.cboLoaiThucVat.currentIndex() <= 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn loại thực vật!")
            return False

        if hasattr(self, 'cboKhuTrungBay') and self.cboKhuTrungBay.currentIndex() <= 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn khu trưng bày!")
            return False

        return True

    def save_data(self):
        """Lưu dữ liệu"""
        if not self.validate_data():
            return

        macay = self.txtMaCay.text().strip() if hasattr(self, 'txtMaCay') else ''
        tencay = self.txtTenCay.text().strip() if hasattr(self, 'txtTenCay') else ''
        maloai = self.cboLoaiThucVat.currentData() if hasattr(self, 'cboLoaiThucVat') else ''
        makhu = self.cboKhuTrungBay.currentData() if hasattr(self, 'cboKhuTrungBay') else ''

        ngaytrong = None
        if hasattr(self, 'dteNgayTrong'):
            ngaytrong = self.dteNgayTrong.date().toString("yyyy-MM-dd")

        chieucao = None
        if hasattr(self, 'txtChieuCao') and self.txtChieuCao.text():
            try:
                chieucao = float(self.txtChieuCao.text())
            except:
                chieucao = None

        duongkinh = None
        if hasattr(self, 'txtDuongKinh') and self.txtDuongKinh.text():
            try:
                duongkinh = float(self.txtDuongKinh.text())
            except:
                duongkinh = None

        tinhtrang = ''
        if hasattr(self, 'cboTinhTrangSinhTruong'):
            tinhtrang = self.cboTinhTrangSinhTruong.currentText()

        trangthai = ''
        if hasattr(self, 'cboTrangThaiHoatDong'):
            trangthai = self.cboTrangThaiHoatDong.currentText()

        self.result_data = {
            'MACAY': macay,
            'TENCAY': tencay,
            'MALOAI': maloai,
            'MAKHU': makhu,
            'NGAYTRONG': ngaytrong,
            'CHIEUCAO': chieucao,
            'DUONGKINH': duongkinh,
            'TINHTRANGSINHTRUONG': tinhtrang,
            'TRANGTHAIHOATDONG': trangthai,
            'VITRI': ''
        }

        print("=" * 60)
        print("💾 DỮ LIỆU LƯU:")
        print(self.result_data)
        print("=" * 60)

        self.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = PhieuThongTinCayDialog(edit_mode=False)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("Dữ liệu:", dialog.result_data)
    sys.exit()