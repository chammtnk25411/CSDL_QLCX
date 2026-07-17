# NhanvienEx.py - Thêm kết nối sidebar
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
from PhieunhanvienEx import StaffInfoDialog


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

        # Kiểm tra quyền - MẶC ĐỊNH LÀ ADMIN NẾU KHÔNG CÓ ROLE
        if role is None:
            self.is_admin_or_staff = True
            self.is_guest = False
        else:
            self.is_admin_or_staff = self.role in ["Quản trị viên", "Nhân viên"]
            self.is_guest = self.role == "Khách tham quan"

        # Load UI
        ui_path = os.path.join(os.path.dirname(__file__), 'Nhanvien.ui')
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
        # UI có 8 cột: 0-Mã NV, 1-Họ tên, 2-Ngày sinh, 3-Giới tính, 4-SĐT, 5-Email, 6-Chức vụ, 7-Thao tác
        self.tableWidget.setColumnWidth(0, 100)  # Mã nhân viên
        self.tableWidget.setColumnWidth(1, 150)  # Họ và tên
        self.tableWidget.setColumnWidth(2, 100)  # Ngày sinh
        self.tableWidget.setColumnWidth(3, 80)   # Giới tính
        self.tableWidget.setColumnWidth(4, 110)  # SĐT
        self.tableWidget.setColumnWidth(5, 200)  # Email
        self.tableWidget.setColumnWidth(6, 120)  # Chức vụ
        self.tableWidget.setColumnWidth(7, 130)  # Thao tác - GIỮ NGUYÊN

        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Xóa dữ liệu mẫu trong UI
        self.tableWidget.setRowCount(0)

    def setup_connections(self):
        """Kết nối sự kiện"""
        # Các nút chức năng
        self.searchButton.clicked.connect(self.search_staff)
        self.searchInput.returnPressed.connect(self.search_staff)
        self.addButton.clicked.connect(self.add_staff)
        self.refreshButton.clicked.connect(self.refresh_data)

        # Nút phân trang
        self.page1Button.clicked.connect(lambda: self.go_to_page(0))
        self.page2Button.clicked.connect(lambda: self.go_to_page(1))
        self.page3Button.clicked.connect(lambda: self.go_to_page(2))
        self.pageLastButton.clicked.connect(lambda: self.go_to_page(19))
        self.pageNextButton.clicked.connect(self.next_page)

        # ===== KẾT NỐI CÁC NÚT SIDEBAR =====
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
            # Khách hàng: Ẩn nút Thêm
            self.addButton.setVisible(False)
            self.addButton.setEnabled(False)

            # Đổi tiêu đề để biết là chỉ xem
            self.setWindowTitle("QUẢN LÝ NHÂN VIÊN - Chế độ xem")
        else:
            # Nhân viên/Quản trị viên: Đầy đủ quyền
            self.addButton.setVisible(True)
            self.addButton.setEnabled(True)
            self.setWindowTitle("QUẢN LÝ NHÂN VIÊN")

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
                SELECT MANV, HOTEN, NGAYSINH, GIOITINH, DIENTHOAI, EMAIL, CHUCVU
                FROM NHAN_VIEN
                ORDER BY MANV
            """
            cursor.execute(query)
            rows = cursor.fetchall()

            self.data = []
            for row in rows:
                ngaysinh = row[2].strftime('%d/%m/%Y') if row[2] else ''
                self.data.append({
                    'MANV': row[0],
                    'HOTEN': row[1],
                    'NGAYSINH': ngaysinh,
                    'GIOITINH': row[3] if row[3] else '',
                    'DIENTHOAI': row[4] if row[4] else '',
                    'EMAIL': row[5] if row[5] else '',
                    'CHUCVU': row[6] if row[6] else ''
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

    def display_data(self):
        """Hiển thị dữ liệu lên bảng - GIỮ NGUYÊN CỘT THAO TÁC"""
        self.tableWidget.setRowCount(0)

        start = self.current_page * self.items_per_page
        end = min(start + self.items_per_page, len(self.filtered_data))
        current_data = self.filtered_data[start:end]

        for row, staff in enumerate(current_data):
            self.tableWidget.insertRow(row)

            self.tableWidget.setItem(row, 0, QTableWidgetItem(staff['MANV']))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(staff['HOTEN']))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(staff['NGAYSINH']))
            self.tableWidget.setItem(row, 3, QTableWidgetItem(staff['GIOITINH']))
            self.tableWidget.setItem(row, 4, QTableWidgetItem(staff['DIENTHOAI']))
            self.tableWidget.setItem(row, 5, QTableWidgetItem(staff['EMAIL']))
            self.tableWidget.setItem(row, 6, QTableWidgetItem(staff['CHUCVU']))

            # ===== CỘT THAO TÁC (CỘT 7) - LUÔN HIỂN THỊ =====
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(8)

            if self.is_admin_or_staff:
                # Nhân viên/Quản trị viên: Hiển thị nút Sửa và Xóa
                btn_edit = QPushButton("Sửa")
                btn_edit.setFixedSize(45, 25)
                btn_edit.setToolTip("Sửa thông tin nhân viên này")
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
                btn_edit.clicked.connect(lambda checked, s=staff: self.edit_staff(s))

                btn_delete = QPushButton("Xóa")
                btn_delete.setFixedSize(45, 25)
                btn_delete.setToolTip("Xóa nhân viên này")
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
                btn_delete.clicked.connect(lambda checked, s=staff: self.delete_staff(s))

                action_layout.addWidget(btn_edit)
                action_layout.addWidget(btn_delete)

            else:
                # Khách hàng: Hiển thị text "Chỉ xem"
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
            self.paginationLabel.setText("Không tìm thấy nhân viên nào")
            return

        start = self.current_page * self.items_per_page + 1
        end = min(start + self.items_per_page - 1, total)
        self.paginationLabel.setText(f"Hiển thị {start} đến {end} trong tổng số {total} nhân viên")

        total_pages = (total + self.items_per_page - 1) // self.items_per_page
        self.page1Button.setEnabled(total_pages >= 1)
        self.page2Button.setEnabled(total_pages >= 2)
        self.page3Button.setEnabled(total_pages >= 3)
        self.pageLastButton.setEnabled(total_pages >= 20)
        self.pageNextButton.setEnabled(self.current_page < total_pages - 1)

    def search_staff(self):
        keyword = self.searchInput.text().strip().lower()

        if keyword == '':
            self.filtered_data = self.data.copy()
        else:
            self.filtered_data = [
                staff for staff in self.data
                if keyword in staff['MANV'].lower() or
                   keyword in staff['HOTEN'].lower() or
                   keyword in staff['CHUCVU'].lower() or
                   keyword in staff['EMAIL'].lower() or
                   keyword in staff['DIENTHOAI'].lower()
            ]

        self.current_page = 0
        self.display_data()

    def refresh_data(self):
        self.searchInput.clear()
        self.load_data()

    def add_staff(self):
        """Thêm nhân viên mới - Chỉ Nhân viên/Quản trị viên"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền thêm nhân viên!")
            return

        existing_ids = [s['MANV'] for s in self.data]
        dialog = StaffInfoDialog(self, edit_mode=False, existing_ids=existing_ids)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        INSERT INTO NHAN_VIEN 
                        (MANV, HOTEN, NGAYSINH, GIOITINH, DIENTHOAI, EMAIL, CHUCVU, MATKHAU)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        data['MANV'],
                        data['HOTEN'],
                        data['NGAYSINH'],
                        data['GIOITINH'],
                        data['DIENTHOAI'],
                        data['EMAIL'],
                        data['CHUCVU'],
                        '123456'  # Mật khẩu mặc định
                    ))

                    conn.commit()
                    conn.close()

                    self.load_data()
                    QMessageBox.information(self, "Thành công", f"Đã thêm nhân viên {data['HOTEN']}")

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể thêm nhân viên: {str(e)}")

    def edit_staff(self, staff):
        """Sửa thông tin nhân viên - Chỉ Nhân viên/Quản trị viên"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền sửa thông tin nhân viên!")
            return

        dialog = StaffInfoDialog(self, edit_mode=True, staff_data=staff)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE NHAN_VIEN 
                        SET HOTEN = ?, NGAYSINH = ?, GIOITINH = ?, 
                            DIENTHOAI = ?, EMAIL = ?, CHUCVU = ?
                        WHERE MANV = ?
                    """, (
                        data['HOTEN'],
                        data['NGAYSINH'],
                        data['GIOITINH'],
                        data['DIENTHOAI'],
                        data['EMAIL'],
                        data['CHUCVU'],
                        staff['MANV']
                    ))

                    conn.commit()
                    conn.close()

                    self.load_data()
                    QMessageBox.information(self, "Thành công", f"Đã cập nhật nhân viên {data['HOTEN']}")

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật nhân viên: {str(e)}")

    def delete_staff(self, staff):
        """Xóa nhân viên - Chỉ Nhân viên/Quản trị viên"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "Bạn không có quyền xóa nhân viên!")
            return

        # Kiểm tra xem nhân viên có đang được sử dụng không
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Kiểm tra trong bảng PHIEU_CHAM_SOC
            cursor.execute("SELECT COUNT(*) FROM PHIEU_CHAM_SOC WHERE MANV = ?", (staff['MANV'],))
            count1 = cursor.fetchone()[0]

            # Kiểm tra trong bảng PHIEU_KHAO_SAT
            cursor.execute("SELECT COUNT(*) FROM PHIEU_KHAO_SAT WHERE MANV = ?", (staff['MANV'],))
            count2 = cursor.fetchone()[0]

            # Kiểm tra trong bảng YEU_CAU_BAO_TRI
            cursor.execute("SELECT COUNT(*) FROM YEU_CAU_BAO_TRI WHERE MANV = ?", (staff['MANV'],))
            count3 = cursor.fetchone()[0]

            conn.close()

            total = count1 + count2 + count3
            if total > 0:
                QMessageBox.warning(self, "Cảnh báo",
                                    f"Nhân viên '{staff['HOTEN']}' đang có {total} phiếu liên quan.\n"
                                    "Không thể xóa nhân viên này!")
                return
        except:
            pass

        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa nhân viên '{staff['HOTEN']}' (Mã: {staff['MANV']})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM NHAN_VIEN WHERE MANV = ?", (staff['MANV'],))
                conn.commit()
                conn.close()

                self.load_data()
                QMessageBox.information(self, "Thành công", f"Đã xóa nhân viên {staff['HOTEN']}")

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa nhân viên: {str(e)}")

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

    def open_loai_thuc_vat(self):
        try:
            from LoaithucvatEx import MainWindow as LoaiThucVat
            self.window = LoaiThucVat(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể mở loài thực vật: {str(e)}")

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
    # Khi chạy riêng, mặc định là Quản trị viên (có đầy đủ quyền)
    window = MainWindow(username="Admin", role="Quản trị viên")
    window.show()
    sys.exit(app.exec())