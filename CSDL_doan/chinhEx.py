# loginEX.py - Chuyển thẳng qua giao diện khác, giữ sidebar của trang đó
import sys
from datetime import datetime
import traceback

import pyodbc
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem
from PyQt6.QtCore import Qt

# Import giao diện
from chinh_2 import Ui_MainWindow as Ui_Chinh

# Import các file EX
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


# =========================================================
# GIAO DIỆN TRANG CHỦ
# =========================================================
class MainWindow(QMainWindow):
    def __init__(self, username="", role=""):
        super().__init__()
        self.username = username
        self.role = role
        self.ui = Ui_Chinh()
        self.ui.setupUi(self)

        # Cập nhật thông tin người dùng
        if hasattr(self.ui, "userInfo"):
            self.ui.userInfo.setText(f"{username}\n{role}")
        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        # Kết nối các nút chức năng
        self.setup_connections()

        # Load dữ liệu thống kê
        self.load_thong_ke()
        self.load_bao_tri()
        self.load_bao_cao()

    def setup_connections(self):
        """Kết nối các nút trên sidebar với các trang chức năng"""
        # Trang chủ
        if hasattr(self.ui, "pushButton_10"):
            self.ui.pushButton_10.clicked.connect(self.open_trang_chu)

        # Quản lý cây
        if hasattr(self.ui, "pushButton_2"):
            self.ui.pushButton_2.clicked.connect(self.open_quan_ly_cay)

        # Loài thực vật
        if hasattr(self.ui, "pushButton_3"):
            self.ui.pushButton_3.clicked.connect(self.open_loai_thuc_vat)

        # Họ thực vật
        if hasattr(self.ui, "pushButton_4"):
            self.ui.pushButton_4.clicked.connect(self.open_ho_thuc_vat)

        # Khu trưng bày
        if hasattr(self.ui, "pushButton_5"):
            self.ui.pushButton_5.clicked.connect(self.open_khu_trung_bay)

        # Nhân viên
        if hasattr(self.ui, "pushButton_6"):
            self.ui.pushButton_6.clicked.connect(self.open_nhan_vien)

        # Phiếu chăm sóc
        if hasattr(self.ui, "pushButton"):
            self.ui.pushButton.clicked.connect(self.open_phieu_cham_soc)

        # Phiếu khảo sát
        if hasattr(self.ui, "pushButton_7"):
            self.ui.pushButton_7.clicked.connect(self.open_phieu_khao_sat)

        # Yêu cầu bảo trì
        if hasattr(self.ui, "pushButton_8"):
            self.ui.pushButton_8.clicked.connect(self.open_yeu_cau_bao_tri)

        # Báo cáo sự cố
        if hasattr(self.ui, "pushButton_9"):
            self.ui.pushButton_9.clicked.connect(self.open_bao_cao_su_co)

    # ==================== CÁC HÀM MỞ TRANG ====================
    def open_trang_chu(self):
        """Mở lại trang chủ"""
        self.window = MainWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_quan_ly_cay(self):
        """Mở Quản lý cây"""
        self.window = QuanLyCayWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_loai_thuc_vat(self):
        """Mở Loài thực vật"""
        self.window = LoaiThucVatWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_ho_thuc_vat(self):
        """Mở Họ thực vật"""
        self.window = HoThucVatWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_khu_trung_bay(self):
        """Mở Khu trưng bày"""
        self.window = KhuTrungBayWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_nhan_vien(self):
        """Mở Nhân viên"""
        self.window = NhanVienWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_phieu_cham_soc(self):
        """Mở Phiếu chăm sóc"""
        self.window = PhieuChamSocWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_phieu_khao_sat(self):
        """Mở Phiếu khảo sát"""
        self.window = PhieuKhaoSatWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_yeu_cau_bao_tri(self):
        """Mở Yêu cầu bảo trì"""
        self.window = YeuCauBaoTriWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_bao_cao_su_co(self):
        """Mở Báo cáo sự cố"""
        self.window = BaoCaoSuCoWindow(self.username, self.role)
        self.window.show()
        self.close()

    # ==================== LOAD DỮ LIỆU ====================
    def load_thong_ke(self):
        """Load số liệu thống kê lên các card"""
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM CAY")
            count_cay = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM LOAI_THUC_VAT")
            count_loai = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM HO_THUC_VAT")
            count_ho = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM KHU_TRUNG_BAY")
            count_khu = cursor.fetchone()[0]

            conn.close()

            # Cập nhật UI
            if hasattr(self.ui, "val1"):
                self.ui.val1.setText(str(count_cay if count_cay > 0 else 0))
            if hasattr(self.ui, "val2"):
                self.ui.val2.setText(str(count_loai if count_loai > 0 else 0))
            if hasattr(self.ui, "val3"):
                self.ui.val3.setText(str(count_ho if count_ho > 0 else 0))
            if hasattr(self.ui, "val4"):
                self.ui.val4.setText(str(count_khu if count_khu > 0 else 0))

        except Exception as e:
            print(f"Lỗi load thống kê: {e}")
            # Giữ giá trị mặc định từ UI

    def load_bao_tri(self):
        """Load danh sách yêu cầu bảo trì vào bảng"""
        if not hasattr(self.ui, "table_maintenance"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT TOP 5 yc.MABT, yc.MACAY, yc.NGAYTAO, yc.NOIDUNGBAOTRI, 
                       yc.MUCDOUUTIEN, nv.HOTEN
                FROM YEU_CAU_BAO_TRI yc
                LEFT JOIN NHAN_VIEN nv ON yc.MANV = nv.MANV
                ORDER BY yc.NGAYTAO DESC
            """)
            rows = cursor.fetchall()
            conn.close()

            self.ui.table_maintenance.setRowCount(0)

            for row_idx, row in enumerate(rows):
                self.ui.table_maintenance.insertRow(row_idx)
                for col_idx, value in enumerate(row):
                    self.ui.table_maintenance.setItem(
                        row_idx, col_idx,
                        QTableWidgetItem(str(value) if value else "")
                    )

        except Exception as e:
            print(f"Lỗi load bảo trì: {e}")

    def load_bao_cao(self):
        """Load danh sách báo cáo sự cố vào bảng"""
        if not hasattr(self.ui, "table_incidents"):
            return

        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT TOP 5 bc.MACAY, bc.MABC, bc.THOIGIANGUI, bc.MOTA, 
                       bc.MUCDONGUYHIEM, bc.TRANGTHAI
                FROM BAO_CAO_SU_CO bc
                ORDER BY bc.THOIGIANGUI DESC
            """)
            rows = cursor.fetchall()
            conn.close()

            self.ui.table_incidents.setRowCount(0)

            for row_idx, row in enumerate(rows):
                self.ui.table_incidents.insertRow(row_idx)
                for col_idx, value in enumerate(row):
                    self.ui.table_incidents.setItem(
                        row_idx, col_idx,
                        QTableWidgetItem(str(value) if value else "")
                    )

        except Exception as e:
            print(f"Lỗi load báo cáo: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(username="Nguyễn Văn A", role="Quản trị viên")
    window.show()
    sys.exit(app.exec())