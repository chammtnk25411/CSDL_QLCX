# phieu_cham_socEx.py - Phân quyền khách hàng
import sys

import pyodbc
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QHeaderView,
                             QDialog, QVBoxLayout, QLabel, QFormLayout, QPushButton,
                             QHBoxLayout, QLineEdit, QComboBox, QDateEdit, QTableWidgetItem)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QBrush, QColor

import config
from phieu_cham_soc import Ui_MainWindow


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


class ChiTietPhieuDialog(QDialog):
    """Popup hiển thị thông tin phiếu chăm sóc"""

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi Tiết Phiếu Chăm Sóc")
        self.resize(550, 450)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel#title { 
                font-size: 18px; font-weight: bold; color: #1e5631; 
                padding-bottom: 12px; border-bottom: 2px solid #e2e5e3;
            }
            QLabel.formLabel { font-size: 13px; font-weight: bold; color: #5c6b60; }
            QLabel#valLabel { 
                font-size: 13px; font-weight: bold; color: #1c1c1c; 
                background-color: #f7f9f7; padding: 6px 10px;
                border-radius: 4px; border: 1px solid #eef1ef;
            }
            QPushButton#btnClose { 
                background-color: #1e5631; color: white; border-radius: 6px; 
                padding: 10px 24px; font-size: 12px; font-weight: bold; border: none;
            }
            QPushButton#btnClose:hover { background-color: #24693a; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        title_label = QLabel("CHI TIẾT PHIẾU CHĂM SÓC")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        labels = [
            "Mã phiếu CS:", "Cây:", "Ngày chăm sóc:", "Nội dung chăm sóc:",
            "Phương pháp:", "Tình trạng sau CS:", "Nhân viên thực hiện:", "Ghi chú:"
        ]

        for i, text in enumerate(labels):
            lbl_title = QLabel(text)
            lbl_title.setProperty("class", "formLabel")

            clean_text = data[i].replace('\n', ' ') if i < len(data) else ""
            lbl_val = QLabel(clean_text)
            lbl_val.setObjectName("valLabel")
            lbl_val.setWordWrap(True)

            form_layout.addRow(lbl_title, lbl_val)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("Đóng cửa sổ")
        btn_close.setObjectName("btnClose")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)


class ChinhSuaPhieuDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chỉnh Sửa Phiếu Chăm Sóc")
        self.resize(500, 480)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { font-size: 13px; font-weight: bold; color: #33413a; }
            QLineEdit, QComboBox, QDateEdit { 
                border: 1px solid #d8dcd9; border-radius: 6px; 
                padding: 7px 10px; font-size: 13px; background-color: #ffffff;
            }
            QLineEdit:disabled { background-color: #f4f6f5; color: #9aa39d; }
            QPushButton { font-size: 12px; font-weight: bold; border-radius: 6px; padding: 10px 22px; }
            QPushButton#btnSave { background-color: #1e5631; color: white; border: none; }
            QPushButton#btnSave:hover { background-color: #24693a; }
            QPushButton#btnCancel { background-color: #ffffff; color: #33413a; border: 1px solid #d8dcd9; }
            QPushButton#btnCancel:hover { background-color: #f4f6f5; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.cay_goc = data[1]

        self.txt_ma = QLineEdit()
        self.txt_ma.setText(data[0])
        self.txt_ma.setEnabled(False)
        form_layout.addRow("Mã phiếu CS:", self.txt_ma)

        self.txt_ngay = QDateEdit()
        self.txt_ngay.setCalendarPopup(True)
        self.txt_ngay.setDisplayFormat("dd/MM/yyyy")
        qdate = QDate.fromString(data[2], "dd/MM/yyyy")
        self.txt_ngay.setDate(qdate if qdate.isValid() else QDate.currentDate())
        form_layout.addRow("Ngày chăm sóc:", self.txt_ngay)

        self.txt_noidung = QLineEdit()
        self.txt_noidung.setText(data[3])
        form_layout.addRow("Nội dung chăm sóc:", self.txt_noidung)

        self.txt_phuongphap = QLineEdit()
        self.txt_phuongphap.setText(data[4])
        form_layout.addRow("Phương pháp:", self.txt_phuongphap)

        self.cbo_tinhtrang = QComboBox()
        self.cbo_tinhtrang.addItems(["Tốt", "Trung bình", "Kém"])
        self.cbo_tinhtrang.setCurrentText(data[5])
        form_layout.addRow("Tình trạng sau CS:", self.cbo_tinhtrang)

        self.cbo_nhanvien = QComboBox()
        self.cbo_nhanvien.addItems(["Lê Văn C", "Trần Thị B", "Phạm Minh D", "Nguyễn Văn A"])
        self.cbo_nhanvien.setCurrentText(data[6])
        form_layout.addRow("Nhân viên thực hiện:", self.cbo_nhanvien)

        self.txt_ghichu = QLineEdit()
        self.txt_ghichu.setText(data[7])
        form_layout.addRow("Ghi chú:", self.txt_ghichu)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Hủy bỏ")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Lưu thay đổi")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def get_data(self):
        return [
            self.txt_ma.text(),
            self.cay_goc,
            self.txt_ngay.date().toString("dd/MM/yyyy"),
            self.txt_noidung.text(),
            self.txt_phuongphap.text(),
            self.cbo_tinhtrang.currentText(),
            self.cbo_nhanvien.currentText(),
            self.txt_ghichu.text(),
            "..."
        ]


class ThemPhieuDialog(QDialog):
    """Thêm mới phiếu chăm sóc"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm Phiếu Chăm Sóc Mới")
        self.resize(500, 520)
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; }
            QLabel { font-size: 13px; font-weight: bold; color: #33413a; }
            QLineEdit, QComboBox, QDateEdit { 
                border: 1px solid #d8dcd9; border-radius: 6px; 
                padding: 7px 10px; font-size: 13px; background-color: #ffffff;
            }
            QPushButton { font-size: 12px; font-weight: bold; border-radius: 6px; padding: 10px 22px; }
            QPushButton#btnSave { background-color: #1e5631; color: white; border: none; }
            QPushButton#btnSave:hover { background-color: #24693a; }
            QPushButton#btnCancel { background-color: #ffffff; color: #33413a; border: 1px solid #d8dcd9; }
            QPushButton#btnCancel:hover { background-color: #f4f6f5; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)

        self.txt_ma = QLineEdit()
        self.txt_ma.setPlaceholderText("VD: CS20240601001")
        form_layout.addRow("Mã phiếu CS:", self.txt_ma)

        self.cbo_cay = QComboBox()
        self.cbo_cay.addItems(["Sao đen (C045)", "Bằng lăng (C012)", "Phượng vĩ (C033)"])
        form_layout.addRow("Cây:", self.cbo_cay)

        self.txt_ngay = QDateEdit()
        self.txt_ngay.setCalendarPopup(True)
        self.txt_ngay.setDisplayFormat("dd/MM/yyyy")
        self.txt_ngay.setDate(QDate.currentDate())
        form_layout.addRow("Ngày chăm sóc:", self.txt_ngay)

        self.txt_noidung = QLineEdit()
        self.txt_noidung.setPlaceholderText("VD: Bón phân, tưới nước...")
        form_layout.addRow("Nội dung chăm sóc:", self.txt_noidung)

        self.txt_phuongphap = QLineEdit()
        self.txt_phuongphap.setPlaceholderText("VD: Bón gốc, phun lá...")
        form_layout.addRow("Phương pháp:", self.txt_phuongphap)

        self.cbo_tinhtrang = QComboBox()
        self.cbo_tinhtrang.addItems(["Tốt", "Trung bình", "Kém"])
        form_layout.addRow("Tình trạng sau CS:", self.cbo_tinhtrang)

        self.cbo_nhanvien = QComboBox()
        self.cbo_nhanvien.addItems(["Lê Văn C", "Trần Thị B", "Phạm Minh D", "Nguyễn Văn A"])
        form_layout.addRow("Nhân viên thực hiện:", self.cbo_nhanvien)

        self.txt_ghichu = QLineEdit()
        self.txt_ghichu.setPlaceholderText("Ghi chú thêm (nếu có)")
        form_layout.addRow("Ghi chú:", self.txt_ghichu)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Hủy bỏ")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Thêm mới")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def get_data(self):
        cay_text = self.cbo_cay.currentText().replace(" (", "\n(")
        return [
            self.txt_ma.text(),
            cay_text,
            self.txt_ngay.date().toString("dd/MM/yyyy"),
            self.txt_noidung.text(),
            self.txt_phuongphap.text(),
            self.cbo_tinhtrang.currentText(),
            self.cbo_nhanvien.currentText(),
            self.txt_ghichu.text() if self.txt_ghichu.text() else "-",
            "..."
        ]


class PhieuChamSocEx(QMainWindow):
    def __init__(self, username=None, role=None):
        super().__init__()
        self.username = username
        self.role = role

        # ===== PHÂN QUYỀN =====
        self.is_guest = (role == "Khách tham quan")
        self.is_admin_or_staff = (role in ["Quản trị viên", "Nhân viên"])

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._dialog = None

        # Cập nhật thông tin người dùng
        if username:
            self.ui.userName.setText(username)
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if role:
            self.ui.userRole.setText(role)
            self.ui.sidebarRoleLabel.setText(role)

        self.setup_defaults()
        self.connect_signals()
        self.setup_permissions()

        # Load dữ liệu từ database
        self.load_data_from_db()

    def setup_defaults(self):
        self.ui.filterTuNgay.setDate(QDate.currentDate().addMonths(-1))
        self.ui.filterDenNgay.setDate(QDate.currentDate())

        header = self.ui.tableCareRecords.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

    def setup_permissions(self):
        """Phân quyền - Ẩn nút thêm nếu là khách"""
        if self.is_guest:
            # Khách hàng: Ẩn nút Thêm phiếu
            if hasattr(self.ui, "btnAddSurvey"):
                self.ui.btnAddSurvey.setVisible(False)
                self.ui.btnAddSurvey.setEnabled(False)
            # Đổi tiêu đề
            self.setWindowTitle("PHIẾU CHĂM SÓC - Chế độ xem")
        else:
            if hasattr(self.ui, "btnAddSurvey"):
                self.ui.btnAddSurvey.setVisible(True)
                self.ui.btnAddSurvey.setEnabled(True)
            self.setWindowTitle("PHIẾU CHĂM SÓC")

    def connect_signals(self):
        # Các nút chức năng
        self.ui.btnMenuToggle.clicked.connect(self.handle_toggle_menu)
        self.ui.btnAddSurvey.clicked.connect(self.handle_add_care_record)
        self.ui.searchBox.textChanged.connect(self.handle_search)
        self.ui.tableCareRecords.cellClicked.connect(self.handle_table_click)

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
        if hasattr(self.ui, "navPhieuKhaoSat"):
            self.ui.navPhieuKhaoSat.clicked.connect(self.open_phieu_khao_sat)
        if hasattr(self.ui, "navYeuCauBaoTri"):
            self.ui.navYeuCauBaoTri.clicked.connect(self.open_yeu_cau_bao_tri)
        if hasattr(self.ui, "navBaoCaoSuCo"):
            self.ui.navBaoCaoSuCo.clicked.connect(self.open_bao_cao_su_co)

    def load_data_from_db(self):
        """Load dữ liệu từ database vào bảng"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT pcs.MAPHIEUCS, c.TENCAY, pcs.NGAYCHAMSOC, 
                       pcs.NOIDUNGCHAMSOC, pcs.PHUONGPHAP, pcs.TINHTRANGSAUCHAMSOC,
                       nv.HOTEN, pcs.GHICHU
                FROM PHIEU_CHAM_SOC pcs
                LEFT JOIN CAY c ON pcs.MACAY = c.MACAY
                LEFT JOIN NHAN_VIEN nv ON pcs.MANV = nv.MANV
                ORDER BY pcs.NGAYCHAMSOC DESC
            """)
            rows = cursor.fetchall()
            conn.close()

            self.ui.tableCareRecords.setRowCount(0)

            for row_idx, row in enumerate(rows):
                self.ui.tableCareRecords.insertRow(row_idx)

                # 8 cột dữ liệu
                for col_idx in range(8):
                    value = row[col_idx] if row[col_idx] is not None else ""
                    if col_idx == 2 and row[col_idx]:  # Ngày
                        value = row[col_idx].strftime("%d/%m/%Y") if hasattr(row[col_idx], 'strftime') else str(value)

                    item = QTableWidgetItem(str(value))

                    # Định dạng cột Tình trạng (cột 5)
                    if col_idx == 5 and value:
                        if "Tốt" in str(value):
                            item.setBackground(QBrush(QColor(222, 245, 227)))
                            item.setForeground(QBrush(QColor(27, 107, 57)))
                        elif "Trung bình" in str(value):
                            item.setBackground(QBrush(QColor(252, 236, 205)))
                            item.setForeground(QBrush(QColor(158, 106, 11)))
                        else:
                            item.setBackground(QBrush(QColor(255, 205, 210)))
                            item.setForeground(QBrush(QColor(211, 47, 47)))

                    self.ui.tableCareRecords.setItem(row_idx, col_idx, item)

                # Cột Thao tác (cột 8)
                btn_item = QTableWidgetItem("👁 Chỉ xem" if self.is_guest else "✏️ 🗑")
                btn_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tableCareRecords.setItem(row_idx, 8, btn_item)

            self.update_pagination_info()

        except Exception as e:
            print(f"Lỗi load dữ liệu: {e}")

    def handle_toggle_menu(self):
        is_visible = self.ui.sidebarFrame.isVisible()
        self.ui.sidebarFrame.setVisible(not is_visible)

    def handle_add_care_record(self):
        """Thêm phiếu chăm sóc - CHỈ ADMIN/NHÂN VIÊN"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền thêm phiếu chăm sóc!")
            return

        try:
            self._dialog = ThemPhieuDialog(self)
            if self._dialog.exec() == int(QDialog.DialogCode.Accepted):
                new_data = self._dialog.get_data()

                if not new_data[0].strip():
                    QMessageBox.warning(self, "Lỗi nhập liệu", "Vui lòng nhập Mã phiếu chăm sóc!")
                    return

                # Thêm vào database
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()

                    # Lấy MACAY từ tên cây
                    cay_text = new_data[1].replace("\n(", " (").split("(")
                    macay = cay_text[-1].replace(")", "").strip() if len(cay_text) > 1 else ""

                    # Lấy MANV từ tên nhân viên
                    manv = ""
                    for nv in ["Lê Văn C", "Trần Thị B", "Phạm Minh D", "Nguyễn Văn A"]:
                        if nv in new_data[6]:
                            # Tìm MANV từ database
                            cursor.execute("SELECT MANV FROM NHAN_VIEN WHERE HOTEN = ?", (nv,))
                            row = cursor.fetchone()
                            if row:
                                manv = row[0]
                                break

                    # Chuyển đổi ngày
                    ngay = QDate.fromString(new_data[2], "dd/MM/yyyy")
                    ngay_str = ngay.toString("yyyy-MM-dd") if ngay.isValid() else QDate.currentDate().toString(
                        "yyyy-MM-dd")

                    cursor.execute("""
                        INSERT INTO PHIEU_CHAM_SOC 
                        (MAPHIEUCS, NGAYCHAMSOC, NOIDUNGCHAMSOC, PHUONGPHAP, 
                         TINHTRANGSAUCHAMSOC, GHICHU, MACAY, MANV)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        new_data[0],
                        ngay_str,
                        new_data[3],
                        new_data[4],
                        new_data[5],
                        new_data[7],
                        macay,
                        manv
                    ))
                    conn.commit()
                    conn.close()

                    QMessageBox.information(self, "Thành công", f"Đã thêm phiếu {new_data[0]} thành công!")
                    self.load_data_from_db()

                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể lưu vào database:\n{str(e)}")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi Runtime", f"Đã xảy ra lỗi:\n{str(e)}")

    def handle_search(self, text):
        pass

    def handle_table_click(self, row, column):
        """Xử lý click vào bảng"""
        if column == 8:
            row_data = []
            for col in range(8):
                item = self.ui.tableCareRecords.item(row, col)
                row_data.append(item.text() if item else "")

            ma_phieu = row_data[0]

            # Nếu là khách hàng -> chỉ xem chi tiết
            if self.is_guest:
                self.show_detail_popup(row_data)
                return

            # Nếu là admin/nhân viên -> hiển thị menu đầy đủ
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Lựa chọn thao tác")
            msg_box.setText(f"PHIẾU: {ma_phieu}")

            btn_view = msg_box.addButton("🔍 Xem chi tiết", QMessageBox.ButtonRole.ActionRole)
            btn_edit = msg_box.addButton("✏️ Chỉnh sửa", QMessageBox.ButtonRole.ActionRole)
            btn_delete = msg_box.addButton("🗑 Xóa phiếu", QMessageBox.ButtonRole.ActionRole)
            btn_cancel = msg_box.addButton("❌ Hủy bỏ", QMessageBox.ButtonRole.RejectRole)

            msg_box.exec()

            if msg_box.clickedButton() == btn_view:
                self.show_detail_popup(row_data)
            elif msg_box.clickedButton() == btn_edit:
                self.show_edit_popup(row, row_data)
            elif msg_box.clickedButton() == btn_delete:
                self.confirm_and_delete(row, ma_phieu)

    def show_detail_popup(self, row_data):
        dialog = ChiTietPhieuDialog(row_data, self)
        dialog.exec()

    def show_edit_popup(self, row, row_data):
        """Sửa phiếu - CHỈ ADMIN/NHÂN VIÊN"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền chỉnh sửa!")
            return

        dialog = ChinhSuaPhieuDialog(row_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_data()

            # Cập nhật database
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Chuyển đổi ngày
                ngay = QDate.fromString(updated_data[2], "dd/MM/yyyy")
                ngay_str = ngay.toString("yyyy-MM-dd") if ngay.isValid() else QDate.currentDate().toString("yyyy-MM-dd")

                cursor.execute("""
                    UPDATE PHIEU_CHAM_SOC 
                    SET NGAYCHAMSOC = ?, NOIDUNGCHAMSOC = ?, PHUONGPHAP = ?,
                        TINHTRANGSAUCHAMSOC = ?, GHICHU = ?
                    WHERE MAPHIEUCS = ?
                """, (
                    ngay_str,
                    updated_data[3],
                    updated_data[4],
                    updated_data[5],
                    updated_data[7],
                    updated_data[0]
                ))
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Thành công", f"Đã cập nhật phiếu {updated_data[0]} thành công!")
                self.load_data_from_db()

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật:\n{str(e)}")

    def confirm_and_delete(self, row, ma_phieu):
        """Xóa phiếu - CHỈ ADMIN/NHÂN VIÊN"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền xóa!")
            return

        reply = QMessageBox.question(
            self, "Xác nhận xóa", f"Bạn có chắc chắn muốn xóa hoàn toàn phiếu {ma_phieu}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM PHIEU_CHAM_SOC WHERE MAPHIEUCS = ?", (ma_phieu,))
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Thành công", f"Đã xóa thành công phiếu {ma_phieu}!")
                self.load_data_from_db()

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa:\n{str(e)}")

    def update_pagination_info(self):
        total_rows = self.ui.tableCareRecords.rowCount()
        if total_rows > 0:
            self.ui.paginationInfo.setText(f"Hiển thị 1 đến {total_rows} trong tổng số {total_rows} phiếu chăm sóc")
        else:
            self.ui.paginationInfo.setText("Không còn phiếu chăm sóc nào trong danh sách")

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhieuChamSocEx()
    window.show()
    sys.exit(app.exec())