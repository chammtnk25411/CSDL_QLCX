# LoaithucvatEx.py
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
from PhieuloaiEx import PlantInfoDialog


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
        ui_path = os.path.join(os.path.dirname(__file__), 'Loaithucvat.ui')
        try:
            loadUi(ui_path, self)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể load UI: {str(e)}")
            sys.exit(1)

        # Cập nhật thông tin người dùng
        if username:
            self.userLabel.setText(username)
            self.sidebarUserLabel.setText(f"👤 {username}")
        if role:
            self.roleLabel.setText(role)
            self.sidebarRoleLabel.setText(role)

        # Biến dữ liệu
        self.data = []
        self.filtered_data = []
        self.current_page = 0
        self.items_per_page = 6

        # Thiết lập bảng
        self.setup_table()

        # Kết nối sự kiện
        self.setup_connections()

        # Phân quyền các nút chức năng
        self.setup_permissions()

        # Load dữ liệu họ lên combobox
        self.load_families()

        # Load dữ liệu loài
        self.load_data()

    def setup_table(self):
        """Thiết lập bảng"""
        self.tableWidget.setColumnWidth(0, 80)   # Mã loài
        self.tableWidget.setColumnWidth(1, 120)  # Tên thường gọi
        self.tableWidget.setColumnWidth(2, 160)  # Tên khoa học
        self.tableWidget.setColumnWidth(3, 150)  # Họ thực vật
        self.tableWidget.setColumnWidth(4, 250)  # Đặc điểm sinh học
        self.tableWidget.setColumnWidth(5, 180)  # Môi trường sống
        self.tableWidget.setColumnWidth(6, 120)  # Tình trạng
        self.tableWidget.setColumnWidth(7, 130)  # Thao tác

        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

    def setup_connections(self):
        """Kết nối sự kiện"""
        # Các nút chức năng
        self.searchButton.clicked.connect(self.search_plants)
        self.searchInput.returnPressed.connect(self.search_plants)
        self.addButton.clicked.connect(self.add_plant)
        self.refreshButton.clicked.connect(self.refresh_data)
        self.filterButton.clicked.connect(self.apply_filter)
        self.clearFilterButton.clicked.connect(self.clear_filter)

        # Nút phân trang
        self.page1Button.clicked.connect(lambda: self.go_to_page(0))
        self.page2Button.clicked.connect(lambda: self.go_to_page(1))
        self.page3Button.clicked.connect(lambda: self.go_to_page(2))
        self.page4Button.clicked.connect(lambda: self.go_to_page(3))
        self.page5Button.clicked.connect(lambda: self.go_to_page(4))
        self.page20Button.clicked.connect(lambda: self.go_to_page(19))
        self.pageNextButton.clicked.connect(self.next_page)

        # ===== KẾT NỐI CÁC NÚT SIDEBAR =====
        if hasattr(self, "homeButton"):
            self.homeButton.clicked.connect(self.open_trang_chu)
        if hasattr(self, "plantManagementButton"):
            self.plantManagementButton.clicked.connect(self.open_quan_ly_cay)
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
        """Phân quyền: Ẩn/vô hiệu hóa nút Thêm nếu là Khách hàng"""
        if self.is_guest:
            self.addButton.setVisible(False)
            self.addButton.setEnabled(False)
            self.setWindowTitle("QUẢN LÝ LOÀI THỰC VẬT - Chế độ xem")
        else:
            self.addButton.setVisible(True)
            self.addButton.setEnabled(True)
            self.setWindowTitle("QUẢN LÝ LOÀI THỰC VẬT")

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

    def load_families(self):
        """Load danh sách họ thực vật từ database lên combobox lọc"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT TENHO FROM HO_THUC_VAT ORDER BY TENHO")
            rows = cursor.fetchall()

            self.filterFamilyCombo.clear()
            self.filterFamilyCombo.addItem("📂 Tất cả")

            for row in rows:
                if row[0]:
                    self.filterFamilyCombo.addItem(row[0])

            conn.close()

        except Exception as e:
            self.filterFamilyCombo.clear()
            self.filterFamilyCombo.addItem("📂 Tất cả")

    def load_data(self):
        """Load dữ liệu từ database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
                SELECT l.MALOAI, l.TENTHUONGGOI, l.TENKHOAHOC, 
                       h.TENHO, h.MAHO, l.DACDIEMSINHHOC, 
                       l.MOITRUONGSONG, l.TINHTRANGBAOTON
                FROM LOAI_THUC_VAT l
                LEFT JOIN HO_THUC_VAT h ON l.MAHO = h.MAHO
                ORDER BY l.MALOAI
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            self.data = []
            status_list = set()

            for row in rows:
                status = row[7] if row[7] else ''
                status_list.add(status)

                self.data.append({
                    'MALOAI': row[0],
                    'TENTHUONGGOI': row[1],
                    'TENKHOAHOC': row[2],
                    'TENHO': row[3] if row[3] else '',
                    'MAHO': row[4] if row[4] else '',
                    'DACDIEMSINHHOC': row[5] if row[5] else '',
                    'MOITRUONGSONG': row[6] if row[6] else '',
                    'TINHTRANGBAOTON': status
                })

            conn.close()

            # Cập nhật combobox tình trạng
            self.load_status_combo(status_list)

            self.filtered_data = self.data.copy()
            self.display_data()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi",
                f"Không thể kết nối database:\n{str(e)}\n\n"
                "Vui lòng kiểm tra:\n"
                "1. SQL Server đã chạy chưa?\n"
                "2. Database QLCX đã tồn tại chưa?\n"
                "3. Chạy file database_setup.sql để tạo database"
            )

    def load_status_combo(self, status_list):
        """Load danh sách tình trạng từ dữ liệu SQL lên combobox lọc"""
        self.filterStatusCombo.clear()
        self.filterStatusCombo.addItem("📊 Tất cả tình trạng")

        for status in sorted(status_list):
            if status and status != '':
                self.filterStatusCombo.addItem(status)

    def display_data(self):
        """Hiển thị dữ liệu lên bảng"""
        self.tableWidget.setRowCount(0)

        start = self.current_page * self.items_per_page
        end = min(start + self.items_per_page, len(self.filtered_data))
        current_data = self.filtered_data[start:end]

        for row, plant in enumerate(current_data):
            self.tableWidget.insertRow(row)

            self.tableWidget.setItem(row, 0, QTableWidgetItem(plant['MALOAI']))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(plant['TENTHUONGGOI']))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(plant['TENKHOAHOC']))
            self.tableWidget.setItem(row, 3, QTableWidgetItem(plant.get('TENHO', '')))
            self.tableWidget.setItem(row, 4, QTableWidgetItem(plant.get('DACDIEMSINHHOC', '')))
            self.tableWidget.setItem(row, 5, QTableWidgetItem(plant.get('MOITRUONGSONG', '')))

            # Cột Tình trạng
            status = plant.get('TINHTRANGBAOTON', '')
            status_item = QTableWidgetItem(status)
            status_item.setBackground(QColor(255, 255, 255))
            status_item.setForeground(QColor(0, 0, 0))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.setItem(row, 6, status_item)

            # Cột Thao tác
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(8)

            if self.is_admin_or_staff:
                btn_edit = QPushButton("Sửa")
                btn_edit.setFixedSize(45, 25)
                btn_edit.setToolTip("Sửa thông tin loài này")
                btn_edit.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #0078d4;
                        border: 1px solid #0078d4;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                        padding: 2px 4px;
                    }
                    QPushButton:hover {
                        background-color: #0078d4;
                        color: white;
                    }
                """)
                btn_edit.clicked.connect(lambda checked, p=plant: self.edit_plant(p))

                btn_delete = QPushButton("Xóa")
                btn_delete.setFixedSize(45, 25)
                btn_delete.setToolTip("Xóa loài này")
                btn_delete.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #d13438;
                        border: 1px solid #d13438;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                        padding: 2px 4px;
                    }
                    QPushButton:hover {
                        background-color: #d13438;
                        color: white;
                    }
                """)
                btn_delete.clicked.connect(lambda checked, p=plant: self.delete_plant(p))

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
            self.tableWidget.setCellWidget(row, 7, action_widget)

        self.update_pagination()

    def update_pagination(self):
        total = len(self.filtered_data)
        if total == 0:
            self.paginationLabel.setText("Không tìm thấy loài nào")
            return

        start = self.current_page * self.items_per_page + 1
        end = min(start + self.items_per_page - 1, total)
        self.paginationLabel.setText(f"Hiển thị {start} đến {end} trong tổng số {total} loài")

        total_pages = (total + self.items_per_page - 1) // self.items_per_page
        self.page1Button.setEnabled(total_pages >= 1)
        self.page2Button.setEnabled(total_pages >= 2)
        self.page3Button.setEnabled(total_pages >= 3)
        self.page4Button.setEnabled(total_pages >= 4)
        self.page5Button.setEnabled(total_pages >= 5)
        self.page20Button.setEnabled(total_pages >= 20)
        self.pageNextButton.setEnabled(self.current_page < total_pages - 1)

    def search_plants(self):
        keyword = self.searchInput.text().strip().lower()

        if keyword == '':
            self.filtered_data = self.data.copy()
        else:
            self.filtered_data = [
                plant for plant in self.data
                if keyword in plant['MALOAI'].lower() or
                   keyword in plant['TENTHUONGGOI'].lower() or
                   keyword in plant['TENKHOAHOC'].lower() or
                   keyword in plant.get('TENHO', '').lower() or
                   keyword in plant.get('MOITRUONGSONG', '').lower() or
                   keyword in plant.get('TINHTRANGBAOTON', '').lower()
            ]

        self.current_page = 0
        self.display_data()

    def apply_filter(self):
        family_filter = self.filterFamilyCombo.currentText()
        status_filter = self.filterStatusCombo.currentText()

        self.filtered_data = self.data.copy()

        if family_filter != "📂 Tất cả":
            self.filtered_data = [
                plant for plant in self.filtered_data
                if plant.get('TENHO', '') == family_filter
            ]

        if status_filter != "📊 Tất cả tình trạng":
            self.filtered_data = [
                plant for plant in self.filtered_data
                if plant.get('TINHTRANGBAOTON', '') == status_filter
            ]

        self.current_page = 0
        self.display_data()

    def clear_filter(self):
        self.filterFamilyCombo.setCurrentIndex(0)
        self.filterStatusCombo.setCurrentIndex(0)
        self.filtered_data = self.data.copy()
        self.current_page = 0
        self.display_data()
        QMessageBox.information(self, "Thành công", "Đã xóa bộ lọc!")

    def refresh_data(self):
        self.searchInput.clear()
        self.load_families()
        self.load_data()

    def add_plant(self):
        """Thêm loài thực vật mới"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền thêm loài thực vật!")
            return

        dialog = PlantInfoDialog(self, edit_mode=False)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO LOAI_THUC_VAT 
                        (MALOAI, TENTHUONGGOI, TENKHOAHOC, MAHO, 
                         DACDIEMSINHHOC, MOITRUONGSONG, TINHTRANGBAOTON)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data['MALOAI'],
                        data['TENTHUONGGOI'],
                        data['TENKHOAHOC'],
                        data['MAHO'],
                        data['DACDIEMSINHHOC'],
                        data['MOITRUONGSONG'],
                        data['TINHTRANGBAOTON']
                    ))

                    conn.commit()
                    conn.close()

                    self.load_data()
                    self.filtered_data = self.data.copy()
                    self.display_data()

                    QMessageBox.information(self, "Thành công", f"Đã thêm loài {data['TENTHUONGGOI']}")

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể thêm loài: {str(e)}")

    def edit_plant(self, plant):
        """Sửa thông tin loài"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền sửa thông tin loài thực vật!")
            return

        dialog = PlantInfoDialog(self, edit_mode=True, plant_data=plant)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE LOAI_THUC_VAT 
                        SET TENTHUONGGOI = ?, TENKHOAHOC = ?, MAHO = ?,
                            DACDIEMSINHHOC = ?, MOITRUONGSONG = ?, TINHTRANGBAOTON = ?
                        WHERE MALOAI = ?
                    """, (
                        data['TENTHUONGGOI'],
                        data['TENKHOAHOC'],
                        data['MAHO'],
                        data['DACDIEMSINHHOC'],
                        data['MOITRUONGSONG'],
                        data['TINHTRANGBAOTON'],
                        plant['MALOAI']
                    ))

                    conn.commit()
                    conn.close()

                    self.load_data()
                    self.filtered_data = self.data.copy()
                    self.display_data()

                    QMessageBox.information(self, "Thành công", f"Đã cập nhật loài {data['TENTHUONGGOI']}")

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật loài: {str(e)}")

    def delete_plant(self, plant):
        """Xóa loài thực vật"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền xóa loài thực vật!")
            return

        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa loài '{plant['TENTHUONGGOI']}' (Mã: {plant['MALOAI']})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM LOAI_THUC_VAT WHERE MALOAI = ?", (plant['MALOAI'],))
                conn.commit()
                conn.close()

                self.load_data()
                self.filtered_data = self.data.copy()
                self.display_data()

                QMessageBox.information(self, "Thành công", f"Đã xóa loài {plant['TENTHUONGGOI']}")

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa loài: {str(e)}")

    # ==================== CÁC HÀM CHUYỂN TRANG ====================
    def open_trang_chu(self):
        try:
            from chinhEx import MainWindow as TrangChu
            self.window = TrangChu(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở trang chủ: {str(e)}")

    def open_quan_ly_cay(self):
        try:
            from quanlycayEx import QuanLyCayWindow
            self.window = QuanLyCayWindow(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở quản lý cây: {str(e)}")

    def open_ho_thuc_vat(self):
        try:
            from HothucvatEx import MainWindow as HoThucVat
            self.window = HoThucVat(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở họ thực vật: {str(e)}")

    def open_khu_trung_bay(self):
        try:
            from KhutrungbayEx import MainWindow as KhuTrungBay
            self.window = KhuTrungBay(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở khu trưng bày: {str(e)}")

    def open_nhan_vien(self):
        try:
            from NhanvienEx import MainWindow as NhanVien
            self.window = NhanVien(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở nhân viên: {str(e)}")

    def open_phieu_cham_soc(self):
        try:
            from phieu_cham_socEx import PhieuChamSocEx
            self.window = PhieuChamSocEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở phiếu chăm sóc: {str(e)}")

    def open_phieu_khao_sat(self):
        try:
            from phieu_khao_satEx import PhieuKhaoSatEx
            self.window = PhieuKhaoSatEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở phiếu khảo sát: {str(e)}")

    def open_yeu_cau_bao_tri(self):
        try:
            from yeu_cau_bao_triEx import YeuCauBaoTriEx
            self.window = YeuCauBaoTriEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở yêu cầu bảo trì: {str(e)}")

    def open_bao_cao_su_co(self):
        try:
            from bao_cao_su_coEx import MainWindow as BaoCaoSuCo
            self.window = BaoCaoSuCo(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở báo cáo sự cố: {str(e)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(username="Admin", role="Quản trị viên")
    window.show()
    sys.exit(app.exec())