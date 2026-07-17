# KhutrungbayEx.py - Thêm kết nối sidebar
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
from PhieukhuEx import AreaInfoDialog


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
        ui_path = os.path.join(os.path.dirname(__file__), 'Khutrungbay.ui')
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

        # Load dữ liệu
        self.load_data()

    def setup_table(self):
        """Thiết lập bảng - GIỮ NGUYÊN CỘT THAO TÁC"""
        self.tableWidget.setColumnWidth(0, 80)  # Mã khu
        self.tableWidget.setColumnWidth(1, 150)  # Tên khu
        self.tableWidget.setColumnWidth(2, 120)  # Vị trí
        self.tableWidget.setColumnWidth(3, 100)  # Diện tích
        self.tableWidget.setColumnWidth(4, 250)  # Mô tả
        self.tableWidget.setColumnWidth(5, 120)  # Trạng thái
        self.tableWidget.setColumnWidth(6, 130)  # Thao tác

        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Xóa dữ liệu mẫu trong UI
        self.tableWidget.setRowCount(0)

    def setup_connections(self):
        """Kết nối sự kiện"""
        # Các nút chức năng
        self.searchButton.clicked.connect(self.search_areas)
        self.searchInput.returnPressed.connect(self.search_areas)
        self.addButton.clicked.connect(self.add_area)
        self.refreshButton.clicked.connect(self.refresh_data)

        # Nút phân trang
        self.page1Button.clicked.connect(lambda: self.go_to_page(0))
        self.page2Button.clicked.connect(lambda: self.go_to_page(1))
        self.page3Button.clicked.connect(lambda: self.go_to_page(2))
        self.pageLastButton.clicked.connect(lambda: self.go_to_page(19))
        self.pageNextButton.clicked.connect(self.next_page)

        # ===== KẾT NỐI CÁC NÚT SIDEBAR =====
        # Trang chủ
        if hasattr(self, "homeButton"):
            self.homeButton.clicked.connect(self.open_trang_chu)

        # Quản lý cây
        if hasattr(self, "plantManagementButton"):
            self.plantManagementButton.clicked.connect(self.open_quan_ly_cay)

        # Loài thực vật
        if hasattr(self, "speciesButton"):
            self.speciesButton.clicked.connect(self.open_loai_thuc_vat)

        # Họ thực vật
        if hasattr(self, "familyButton"):
            self.familyButton.clicked.connect(self.open_ho_thuc_vat)

        # Khu trưng bày (đang ở trang này)
        if hasattr(self, "exhibitionButton"):
            self.exhibitionButton.clicked.connect(self.open_khu_trung_bay)

        # Nhân viên
        if hasattr(self, "staffButton"):
            self.staffButton.clicked.connect(self.open_nhan_vien)

        # Phiếu chăm sóc
        if hasattr(self, "careButton"):
            self.careButton.clicked.connect(self.open_phieu_cham_soc)

        # Phiếu khảo sát
        if hasattr(self, "surveyButton"):
            self.surveyButton.clicked.connect(self.open_phieu_khao_sat)

        # Yêu cầu bảo trì
        if hasattr(self, "maintenanceButton"):
            self.maintenanceButton.clicked.connect(self.open_yeu_cau_bao_tri)

        # Báo cáo sự cố
        if hasattr(self, "reportButton"):
            self.reportButton.clicked.connect(self.open_bao_cao_su_co)

    def setup_permissions(self):
        """Phân quyền: Ẩn/vô hiệu hóa nút Thêm nếu là Khách hàng"""
        if self.is_guest:
            self.addButton.setVisible(False)
            self.addButton.setEnabled(False)
            self.setWindowTitle("QUẢN LÝ KHU TRƯNG BÀY - Chế độ xem")
        else:
            self.addButton.setVisible(True)
            self.addButton.setEnabled(True)
            self.setWindowTitle("QUẢN LÝ KHU TRƯNG BÀY")

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
            cursor = conn.cursor()

            query = """
                SELECT MAKHU, TENKHU, VITRI, DIENTICH, MOTA
                FROM KHU_TRUNG_BAY
                ORDER BY MAKHU
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            self.data = []
            for row in rows:
                self.data.append({
                    'MAKHU': row[0],
                    'TENKHU': row[1],
                    'VITRI': row[2] if row[2] else '',
                    'DIENTICH': row[3] if row[3] else 0,
                    'MOTA': row[4] if row[4] else ''
                })

            conn.close()

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
            self.load_sample_data()

    def load_sample_data(self):
        """Dữ liệu mẫu khi không kết nối được database"""
        self.data = [
            {'MAKHU': 'K001', 'TENKHU': 'Khu A - Cây gỗ lớn', 'VITRI': 'Phía Bắc công viên', 'DIENTICH': 5000,
             'MOTA': 'Nơi trồng các loại cây thân gỗ lâu năm'},
            {'MAKHU': 'K002', 'TENKHU': 'Khu B - Hoa cảnh', 'VITRI': 'Phía Nam công viên', 'DIENTICH': 3000,
             'MOTA': 'Khu vực trưng bày hoa và cây bụi nhỏ'},
            {'MAKHU': 'K003', 'TENKHU': 'Khu C - Cây ăn quả', 'VITRI': 'Phía Đông công viên', 'DIENTICH': 2000,
             'MOTA': 'Vườn cây ăn trái các loại'},
            {'MAKHU': 'K004', 'TENKHU': 'Khu D - Cây cảnh', 'VITRI': 'Phía Tây công viên', 'DIENTICH': 1500,
             'MOTA': 'Trưng bày cây cảnh nghệ thuật'}
        ]
        self.filtered_data = self.data.copy()
        self.display_data()

    def display_data(self):
        """Hiển thị dữ liệu lên bảng - GIỮ NGUYÊN CỘT THAO TÁC"""
        self.tableWidget.setRowCount(0)

        start = self.current_page * self.items_per_page
        end = min(start + self.items_per_page, len(self.filtered_data))
        current_data = self.filtered_data[start:end]

        for row, area in enumerate(current_data):
            self.tableWidget.insertRow(row)

            self.tableWidget.setItem(row, 0, QTableWidgetItem(area['MAKHU']))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(area['TENKHU']))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(area.get('VITRI', '')))

            dientich = area.get('DIENTICH', 0)
            if isinstance(dientich, (int, float)):
                dientich_str = f"{dientich:,.0f}" if dientich >= 1000 else str(dientich)
            else:
                dientich_str = str(dientich)
            self.tableWidget.setItem(row, 3, QTableWidgetItem(dientich_str))

            self.tableWidget.setItem(row, 4, QTableWidgetItem(area.get('MOTA', '')))

            status_item = QTableWidgetItem("🟢 Đang hoạt động")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tableWidget.setItem(row, 5, status_item)

            # Cột Thao tác
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(8)

            if self.is_admin_or_staff:
                btn_edit = QPushButton("Sửa")
                btn_edit.setFixedSize(45, 25)
                btn_edit.setToolTip("Sửa thông tin khu này")
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
                btn_edit.clicked.connect(lambda checked, a=area: self.edit_area(a))

                btn_delete = QPushButton("Xóa")
                btn_delete.setFixedSize(45, 25)
                btn_delete.setToolTip("Xóa khu này")
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
                btn_delete.clicked.connect(lambda checked, a=area: self.delete_area(a))

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
            self.tableWidget.setCellWidget(row, 6, action_widget)

        self.update_pagination()

    def update_pagination(self):
        total = len(self.filtered_data)
        if total == 0:
            self.paginationLabel.setText("Không tìm thấy khu nào")
            return

        start = self.current_page * self.items_per_page + 1
        end = min(start + self.items_per_page - 1, total)
        self.paginationLabel.setText(f"Hiển thị {start} đến {end} trong tổng số {total} khu")

        total_pages = (total + self.items_per_page - 1) // self.items_per_page
        self.page1Button.setEnabled(total_pages >= 1)
        self.page2Button.setEnabled(total_pages >= 2)
        self.page3Button.setEnabled(total_pages >= 3)
        self.pageLastButton.setEnabled(total_pages >= 20)
        self.pageNextButton.setEnabled(self.current_page < total_pages - 1)

    def search_areas(self):
        keyword = self.searchInput.text().strip().lower()

        if keyword == '':
            self.filtered_data = self.data.copy()
        else:
            self.filtered_data = [
                area for area in self.data
                if keyword in area['MAKHU'].lower() or
                   keyword in area['TENKHU'].lower() or
                   keyword in area.get('VITRI', '').lower() or
                   keyword in area.get('MOTA', '').lower()
            ]

        self.current_page = 0
        self.display_data()

    def refresh_data(self):
        self.searchInput.clear()
        self.load_data()

    def add_area(self):
        """Thêm khu trưng bày mới"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền thêm khu trưng bày!")
            return

        existing_ids = [a['MAKHU'] for a in self.data]
        dialog = AreaInfoDialog(self, edit_mode=False, existing_ids=existing_ids)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO KHU_TRUNG_BAY (MAKHU, TENKHU, VITRI, DIENTICH, MOTA)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        data['MAKHU'],
                        data['TENKHU'],
                        data['VITRI'],
                        data['DIENTICH'],
                        data['MOTA']
                    ))

                    conn.commit()
                    conn.close()

                    self.load_data()
                    QMessageBox.information(self, "Thành công", f"Đã thêm khu {data['TENKHU']}")

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể thêm khu: {str(e)}")

    def edit_area(self, area):
        """Sửa thông tin khu"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền sửa thông tin khu trưng bày!")
            return

        dialog = AreaInfoDialog(self, edit_mode=True, area_data=area)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE KHU_TRUNG_BAY 
                        SET TENKHU = ?, VITRI = ?, DIENTICH = ?, MOTA = ?
                        WHERE MAKHU = ?
                    """, (
                        data['TENKHU'],
                        data['VITRI'],
                        data['DIENTICH'],
                        data['MOTA'],
                        area['MAKHU']
                    ))

                    conn.commit()
                    conn.close()

                    self.load_data()
                    QMessageBox.information(self, "Thành công", f"Đã cập nhật khu {data['TENKHU']}")

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật khu: {str(e)}")

    def delete_area(self, area):
        """Xóa khu trưng bày"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền xóa khu trưng bày!")
            return

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM CAY WHERE MAKHU = ?", (area['MAKHU'],))
            count = cursor.fetchone()[0]
            conn.close()

            if count > 0:
                QMessageBox.warning(self, "Cảnh báo",
                                    f"Khu '{area['TENKHU']}' đang có {count} cây được trồng.\n"
                                    "Không thể xóa khu này!")
                return
        except:
            pass

        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa khu '{area['TENKHU']}' (Mã: {area['MAKHU']})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM KHU_TRUNG_BAY WHERE MAKHU = ?", (area['MAKHU'],))
                conn.commit()
                conn.close()

                self.load_data()
                QMessageBox.information(self, "Thành công", f"Đã xóa khu {area['TENKHU']}")

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa khu: {str(e)}")

    # ==================== CÁC HÀM CHUYỂN TRANG ====================
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
        """Đang ở trang khu trưng bày"""
        pass

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
        try:
            from bao_cao_su_coEx import MainWindow as BaoCaoSuCo
            self.window = BaoCaoSuCo(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở báo cáo sự cố: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow(username="Admin", role="Quản trị viên")
    window.show()
    sys.exit(app.exec())