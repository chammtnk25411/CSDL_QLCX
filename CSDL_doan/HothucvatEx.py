# HothucvatEx.py
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QTableWidgetItem,
    QPushButton, QWidget, QHBoxLayout, QLabel, QDialog, QTableWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.uic import loadUi
import pyodbc
import config
from PhieuhoEx import FamilyInfoDialog


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


class MainWindow(QMainWindow):
    def __init__(self, username=None, role=None, parent=None):
        super().__init__(parent)

        # Lưu thông tin người dùng
        self.username = username
        self.role = role

        # Kiểm tra quyền
        if role is None:
            self.is_admin_or_staff = True
            self.is_guest = False
        else:
            self.is_admin_or_staff = self.role in ["Quản trị viên", "Nhân viên"]
            self.is_guest = self.role == "Khách tham quan"

        # Load UI
        ui_path = os.path.join(os.path.dirname(__file__), 'Hothucvat.ui')
        try:
            loadUi(ui_path, self)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể load UI: {str(e)}")
            sys.exit(1)

        # Cập nhật thông tin người dùng
        if hasattr(self, "sidebarUserLabel"):
            self.sidebarUserLabel.setText(f"👤 {username}" if username else "👤 Nguyễn Văn A")
        if hasattr(self, "sidebarRoleLabel"):
            self.sidebarRoleLabel.setText(role if role else "Quản trị viên")

        # Biến dữ liệu
        self.data = []
        self.filtered_data = []
        self.current_page = 0
        self.items_per_page = 8

        # Thiết lập bảng
        self.setup_table()

        # Kết nối sự kiện
        self.setup_connections()

        # Phân quyền các nút chức năng
        self.setup_permissions()

        # Load dữ liệu
        self.load_data()

    def setup_table(self):
        """Thiết lập bảng"""
        self.tableWidget.setColumnWidth(0, 80)  # Mã họ
        self.tableWidget.setColumnWidth(1, 150)  # Tên họ
        self.tableWidget.setColumnWidth(2, 300)  # Mô tả
        self.tableWidget.setColumnWidth(3, 130)  # Thao tác

        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tableWidget.setRowCount(0)

    def setup_connections(self):
        """Kết nối sự kiện"""
        self.searchButton.clicked.connect(self.search_families)
        self.searchInput.returnPressed.connect(self.search_families)
        self.addButton.clicked.connect(self.add_family)
        self.refreshButton.clicked.connect(self.refresh_data)

        self.page1Button.clicked.connect(lambda: self.go_to_page(0))
        self.page2Button.clicked.connect(lambda: self.go_to_page(1))
        self.page3Button.clicked.connect(lambda: self.go_to_page(2))
        self.pageLastButton.clicked.connect(lambda: self.go_to_page(19))
        self.pageNextButton.clicked.connect(self.next_page)

        # Kết nối các nút sidebar
        if hasattr(self, "homeButton"):
            self.homeButton.clicked.connect(self.open_trang_chu)
        if hasattr(self, "plantManagementButton"):
            self.plantManagementButton.clicked.connect(self.open_quan_ly_cay)
        if hasattr(self, "speciesButton"):
            self.speciesButton.clicked.connect(self.open_loai_thuc_vat)
        if hasattr(self, "familyButton"):
            self.familyButton.clicked.connect(self.open_ho_thuc_vat)
        if hasattr(self, "exhibitionButton"):
            self.exhibitionButton.clicked.connect(self.open_khu_trung_bay)
        if hasattr(self, "staffButton"):
            self.staffButton.clicked.connect(self.open_nhan_vien)
        if hasattr(self, "careButton"):
            self.careButton.clicked.connect(self.open_phieu_cham_soc)
        if hasattr(self, "surveyButton"):
            self.surveyButton.clicked.connect(self.open_phieu_khao_sat)
        if hasattr(self, "maintenanceButton"):
            self.maintenanceButton.clicked.connect(self.open_yeu_cau_bao_tri)
        if hasattr(self, "reportButton"):
            self.reportButton.clicked.connect(self.open_bao_cao_su_co)

    def setup_permissions(self):
        """Phân quyền"""
        if self.is_guest:
            self.addButton.setVisible(False)
            self.addButton.setEnabled(False)
            self.setWindowTitle("QUẢN LÝ HỌ THỰC VẬT - Chế độ xem")
        else:
            self.addButton.setVisible(True)
            self.addButton.setEnabled(True)
            self.setWindowTitle("QUẢN LÝ HỌ THỰC VẬT")

    def go_to_page(self, page):
        total_pages = (len(self.filtered_data) + self.items_per_page - 1) // self.items_per_page
        if page < total_pages:
            self.current_page = page
            self.display_data()

    def next_page(self):
        total_pages = (len(self.filtered_data) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.display_data()

    def load_data(self):
        """Load dữ liệu từ database"""
        try:
            conn = get_db_connection()
            if not conn:
                self.load_sample_data()
                return

            cursor = conn.cursor()
            cursor.execute("SELECT MAHO, TENHO, MOTA FROM HO_THUC_VAT ORDER BY MAHO")
            rows = cursor.fetchall()
            conn.close()

            self.data = []
            for row in rows:
                self.data.append({
                    'MAHO': row[0],
                    'TENHO': row[1],
                    'MOTA': row[2] if row[2] else ''
                })

            self.filtered_data = self.data.copy()
            self.display_data()

        except Exception as e:
            print(f"Lỗi load dữ liệu: {e}")
            self.load_sample_data()

    def load_sample_data(self):
        """Dữ liệu mẫu khi không kết nối được database"""
        self.data = [
            {'MAHO': 'HF001', 'TENHO': 'Họ Dầu', 'MOTA': 'Cây gỗ lớn, lá đơn, nhựa thơm'},
            {'MAHO': 'HF002', 'TENHO': 'Họ Đậu', 'MOTA': 'Lá kép, quả đậu, hạt'},
            {'MAHO': 'HF003', 'TENHO': 'Họ Hòa thảo', 'MOTA': 'Thân rỗng, lá hẹp, bông'},
            {'MAHO': 'HF004', 'TENHO': 'Họ Lan', 'MOTA': 'Hoa đẹp, biểu sinh'},
            {'MAHO': 'HF005', 'TENHO': 'Họ Thông', 'MOTA': 'Cây lá kim, nhựa thông'},
            {'MAHO': 'HF006', 'TENHO': 'Họ Sim', 'MOTA': 'Lá có dầu thơm'},
            {'MAHO': 'HF007', 'TENHO': 'Họ Cúc', 'MOTA': 'Đầu hoa, quả bế'},
            {'MAHO': 'HF008', 'TENHO': 'Họ Tre', 'MOTA': 'Thân rỗng, đốt'}
        ]
        self.filtered_data = self.data.copy()
        self.display_data()

    def display_data(self):
        """Hiển thị dữ liệu lên bảng"""
        self.tableWidget.setRowCount(0)

        start = self.current_page * self.items_per_page
        end = min(start + self.items_per_page, len(self.filtered_data))
        current_data = self.filtered_data[start:end]

        for row, family in enumerate(current_data):
            self.tableWidget.insertRow(row)

            self.tableWidget.setItem(row, 0, QTableWidgetItem(family['MAHO']))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(family['TENHO']))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(family.get('MOTA', '')))

            # Cột Thao tác
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(8)

            if self.is_admin_or_staff:
                btn_edit = QPushButton("Sửa")
                btn_edit.setFixedSize(45, 25)
                btn_edit.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #0078d4;
                        border: 1px solid #0078d4;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #0078d4;
                        color: white;
                    }
                """)
                btn_edit.clicked.connect(lambda checked, f=family: self.edit_family(f))

                btn_delete = QPushButton("Xóa")
                btn_delete.setFixedSize(45, 25)
                btn_delete.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #d13438;
                        border: 1px solid #d13438;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #d13438;
                        color: white;
                    }
                """)
                btn_delete.clicked.connect(lambda checked, f=family: self.delete_family(f))

                action_layout.addWidget(btn_edit)
                action_layout.addWidget(btn_delete)
            else:
                label_viewonly = QLabel("👁 Chỉ xem")
                label_viewonly.setStyleSheet("""
                    QLabel {
                        color: #6c757d;
                        font-size: 12px;
                        font-weight: bold;
                        background-color: #f8f9fa;
                        padding: 3px 8px;
                        border-radius: 4px;
                        border: 1px solid #dee2e6;
                    }
                """)
                label_viewonly.setAlignment(Qt.AlignmentFlag.AlignCenter)
                action_layout.addWidget(label_viewonly)

            action_layout.addStretch()
            self.tableWidget.setCellWidget(row, 3, action_widget)

        self.update_pagination()

    def update_pagination(self):
        total = len(self.filtered_data)
        if total == 0:
            self.paginationLabel.setText("Không tìm thấy họ nào")
            return

        start = self.current_page * self.items_per_page + 1
        end = min(start + self.items_per_page - 1, total)
        self.paginationLabel.setText(f"Hiển thị {start} đến {end} trong tổng số {total} họ")

        total_pages = (total + self.items_per_page - 1) // self.items_per_page
        self.page1Button.setEnabled(total_pages >= 1)
        self.page2Button.setEnabled(total_pages >= 2)
        self.page3Button.setEnabled(total_pages >= 3)
        self.pageLastButton.setEnabled(total_pages >= 20)
        self.pageNextButton.setEnabled(self.current_page < total_pages - 1)

    def search_families(self):
        keyword = self.searchInput.text().strip().lower()

        if keyword == '':
            self.filtered_data = self.data.copy()
        else:
            self.filtered_data = [
                family for family in self.data
                if keyword in family['MAHO'].lower() or
                   keyword in family['TENHO'].lower() or
                   keyword in family.get('MOTA', '').lower()
            ]

        self.current_page = 0
        self.display_data()

    def refresh_data(self):
        self.searchInput.clear()
        self.load_data()

    def add_family(self):
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền thêm họ thực vật!")
            return

        existing_ids = [f['MAHO'] for f in self.data]
        dialog = FamilyInfoDialog(self, edit_mode=False, existing_ids=existing_ids)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    conn = get_db_connection()
                    if not conn:
                        QMessageBox.warning(self, "Lỗi", "Không thể kết nối database!")
                        return

                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO HO_THUC_VAT (MAHO, TENHO, MOTA)
                        VALUES (?, ?, ?)
                    """, (data['MAHO'], data['TENHO'], data['MOTA']))
                    conn.commit()
                    conn.close()

                    self.load_data()
                    QMessageBox.information(self, "Thành công", f"Đã thêm họ {data['TENHO']}")

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể thêm họ: {str(e)}")

    def edit_family(self, family):
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền sửa thông tin họ thực vật!")
            return

        dialog = FamilyInfoDialog(self, edit_mode=True, family_data=family)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    conn = get_db_connection()
                    if not conn:
                        QMessageBox.warning(self, "Lỗi", "Không thể kết nối database!")
                        return

                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE HO_THUC_VAT 
                        SET TENHO = ?, MOTA = ?
                        WHERE MAHO = ?
                    """, (data['TENHO'], data['MOTA'], family['MAHO']))
                    conn.commit()
                    conn.close()

                    self.load_data()
                    QMessageBox.information(self, "Thành công", f"Đã cập nhật họ {data['TENHO']}")

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật họ: {str(e)}")

    def delete_family(self, family):
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền xóa họ thực vật!")
            return

        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM LOAI_THUC_VAT WHERE MAHO = ?", (family['MAHO'],))
                count = cursor.fetchone()[0]
                conn.close()

                if count > 0:
                    QMessageBox.warning(self, "Cảnh báo",
                                        f"Họ '{family['TENHO']}' đang có {count} loài thực vật sử dụng.\n"
                                        "Không thể xóa họ này!")
                    return
        except:
            pass

        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa họ '{family['TENHO']}' (Mã: {family['MAHO']})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = get_db_connection()
                if not conn:
                    QMessageBox.warning(self, "Lỗi", "Không thể kết nối database!")
                    return

                cursor = conn.cursor()
                cursor.execute("DELETE FROM HO_THUC_VAT WHERE MAHO = ?", (family['MAHO'],))
                conn.commit()
                conn.close()

                self.load_data()
                QMessageBox.information(self, "Thành công", f"Đã xóa họ {family['TENHO']}")

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa họ: {str(e)}")

    # ==================== CÁC HÀM MỞ TRANG ====================
    def open_trang_chu(self):
        from chinhEx import MainWindow as TrangChu
        self.window = TrangChu(self.username, self.role)
        self.window.show()
        self.close()

    def open_quan_ly_cay(self):
        from quanlycayEx import QuanLyCayWindow
        self.window = QuanLyCayWindow(self.username, self.role)
        self.window.show()
        self.close()

    def open_loai_thuc_vat(self):
        from LoaithucvatEx import MainWindow as LoaiThucVat
        self.window = LoaiThucVat(self.username, self.role)
        self.window.show()
        self.close()

    def open_ho_thuc_vat(self):
        pass

    def open_khu_trung_bay(self):
        from KhutrungbayEx import MainWindow as KhuTrungBay
        self.window = KhuTrungBay(self.username, self.role)
        self.window.show()
        self.close()

    def open_nhan_vien(self):
        from NhanvienEx import MainWindow as NhanVien
        self.window = NhanVien(self.username, self.role)
        self.window.show()
        self.close()

    def open_phieu_cham_soc(self):
        from phieu_cham_socEx import PhieuChamSocEx
        self.window = PhieuChamSocEx(self.username, self.role)
        self.window.show()
        self.close()

    def open_phieu_khao_sat(self):
        from phieu_khao_satEx import PhieuKhaoSatEx
        self.window = PhieuKhaoSatEx(self.username, self.role)
        self.window.show()
        self.close()

    def open_yeu_cau_bao_tri(self):
        from yeu_cau_bao_triEx import YeuCauBaoTriEx
        self.window = YeuCauBaoTriEx(self.username, self.role)
        self.window.show()
        self.close()

    def open_bao_cao_su_co(self):
        from bao_cao_su_coEx import MainWindow as BaoCaoSuCo
        self.window = BaoCaoSuCo(self.username, self.role)
        self.window.show()
        self.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(username="Admin", role="Quản trị viên")
    window.show()
    sys.exit(app.exec())