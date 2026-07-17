# phieu_khao_satEx.py - Phân quyền khách hàng
import sys
import datetime
import pyodbc
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QHeaderView,
                             QDialog, QVBoxLayout, QLabel, QFormLayout, QPushButton,
                             QHBoxLayout, QLineEdit, QComboBox, QDateEdit, QTableWidgetItem)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QBrush, QColor

import config
from phieu_khao_sat import Ui_MainWindow


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


class ChiTietKhaoSatDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chi Tiết Phiếu Khảo Sát")
        self.resize(550, 520)
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

        title_label = QLabel("CHI TIẾT PHIẾU KHẢO SÁT")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        labels = [
            "Mã khảo sát:", "Mã cây:", "Ngày khảo sát:", "Chiều cao ghi nhận:",
            "Đường kính ghi nhận:", "Tình trạng lá:", "Tình trạng sinh trưởng:",
            "Nhận xét:", "Nhân viên khảo sát:"
        ]

        for i, text in enumerate(labels):
            lbl_title = QLabel(text)
            lbl_title.setProperty("class", "formLabel")

            clean_text = str(data[i]).replace('\n', ' ') if i < len(data) else ""
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


class ChinhSuaKhaoSatDialog(QDialog):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chỉnh Sửa Khảo Sát")
        self.resize(500, 560)
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

        self.txt_ma = QLineEdit()
        self.txt_ma.setText(data[0])
        self.txt_ma.setEnabled(False)
        form_layout.addRow("Mã KS:", self.txt_ma)

        self.txt_macay = QLineEdit()
        self.txt_macay.setText(data[1] if len(data) > 1 else "")
        form_layout.addRow("Mã cây:", self.txt_macay)

        self.txt_ngay = QDateEdit()
        self.txt_ngay.setCalendarPopup(True)
        self.txt_ngay.setDisplayFormat("yyyy-MM-dd")
        qdate = QDate.fromString(data[2] if len(data) > 2 else "", "yyyy-MM-dd")
        self.txt_ngay.setDate(qdate if qdate.isValid() else QDate.currentDate())
        form_layout.addRow("Ngày khảo sát:", self.txt_ngay)

        self.txt_chieucao = QLineEdit()
        self.txt_chieucao.setText(data[3] if len(data) > 3 else "")
        form_layout.addRow("Chiều cao ghi nhận:", self.txt_chieucao)

        self.txt_duongkinh = QLineEdit()
        self.txt_duongkinh.setText(data[4] if len(data) > 4 else "")
        form_layout.addRow("Đường kính ghi nhận:", self.txt_duongkinh)

        self.cbo_tinhtrangla = QComboBox()
        self.cbo_tinhtrangla.addItems(["Xanh tốt", "Xanh, vài lá sâu", "Vàng/Khô héo"])
        self.cbo_tinhtrangla.setCurrentText(data[5] if len(data) > 5 else "")
        form_layout.addRow("Tình trạng lá:", self.cbo_tinhtrangla)

        self.cbo_sinhtruong = QComboBox()
        self.cbo_sinhtruong.addItems(
            ["Sinh trưởng tốt", "Sinh trưởng trung bình", "Sinh trưởng kém", "Cần theo dõi", "Đang phục hồi",
             "Bị sâu bệnh"])
        self.cbo_sinhtruong.setCurrentText(data[6] if len(data) > 6 else "")
        form_layout.addRow("Tình trạng sinh trưởng:", self.cbo_sinhtruong)

        self.txt_nhanxet = QLineEdit()
        self.txt_nhanxet.setText(data[7] if len(data) > 7 else "")
        form_layout.addRow("Nhận xét:", self.txt_nhanxet)

        self.txt_manv = QLineEdit()
        self.txt_manv.setText(data[8] if len(data) > 8 else "")
        form_layout.addRow("Nhân viên:", self.txt_manv)

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
            self.txt_macay.text(),
            self.txt_ngay.date().toString("yyyy-MM-dd"),
            self.txt_chieucao.text(),
            self.txt_duongkinh.text(),
            self.cbo_tinhtrangla.currentText(),
            self.cbo_sinhtruong.currentText(),
            self.txt_nhanxet.text(),
            self.txt_manv.text(),
            "👁   🗑"
        ]


class ThemKhaoSatDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Thêm Đợt Khảo Sát Mới")
        self.resize(500, 560)
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

        auto_ma_ks = f"PKS{datetime.datetime.now().strftime('%y%m%d%H%M')}"
        self.txt_ma = QLineEdit()
        self.txt_ma.setText(auto_ma_ks)
        self.txt_ma.setEnabled(False)
        form_layout.addRow("Mã KS:", self.txt_ma)

        self.txt_macay = QLineEdit()
        self.txt_macay.setPlaceholderText("VD: C01")
        form_layout.addRow("Mã cây:", self.txt_macay)

        self.txt_ngay = QDateEdit()
        self.txt_ngay.setCalendarPopup(True)
        self.txt_ngay.setDisplayFormat("yyyy-MM-dd")
        self.txt_ngay.setDate(QDate.currentDate())
        form_layout.addRow("Ngày khảo sát:", self.txt_ngay)

        self.txt_chieucao = QLineEdit()
        self.txt_chieucao.setPlaceholderText("VD: 7.5")
        form_layout.addRow("Chiều cao ghi nhận:", self.txt_chieucao)

        self.txt_duongkinh = QLineEdit()
        self.txt_duongkinh.setPlaceholderText("VD: 0.32")
        form_layout.addRow("Đường kính ghi nhận:", self.txt_duongkinh)

        self.cbo_tinhtrangla = QComboBox()
        self.cbo_tinhtrangla.addItems(["Xanh tốt", "Xanh, vài lá sâu", "Vàng/Khô héo"])
        form_layout.addRow("Tình trạng lá:", self.cbo_tinhtrangla)

        self.cbo_sinhtruong = QComboBox()
        self.cbo_sinhtruong.addItems(
            ["Sinh trưởng tốt", "Sinh trưởng trung bình", "Sinh trưởng kém", "Cần theo dõi", "Đang phục hồi",
             "Bị sâu bệnh"])
        form_layout.addRow("Tình trạng sinh trưởng:", self.cbo_sinhtruong)

        self.txt_nhanxet = QLineEdit()
        self.txt_nhanxet.setPlaceholderText("Nhập đánh giá tổng quan...")
        form_layout.addRow("Nhận xét:", self.txt_nhanxet)

        self.txt_manv = QLineEdit()
        self.txt_manv.setPlaceholderText("VD: NV01")
        form_layout.addRow("Nhân viên:", self.txt_manv)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Hủy bỏ")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Lưu khảo sát")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def get_data(self):
        return [
            self.txt_ma.text(),
            self.txt_macay.text(),
            self.txt_ngay.date().toString("yyyy-MM-dd"),
            self.txt_chieucao.text(),
            self.txt_duongkinh.text(),
            self.cbo_tinhtrangla.currentText(),
            self.cbo_sinhtruong.currentText(),
            self.txt_nhanxet.text(),
            self.txt_manv.text(),
            "👁   🗑"
        ]


class PhieuKhaoSatEx(QMainWindow):
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
        self.setup_permissions()

        self.load_data_from_db()

    def setup_defaults(self):
        # Đảm bảo chắc chắn UI sẽ thiết lập 10 cột
        self.ui.tableSurveys.setColumnCount(10)
        headers = [
            "MÃ KS", "MÃ CÂY", "NGÀY KHẢO SÁT", "CHIỀU CAO GHI NHẬN",
            "ĐƯỜNG KÍNH GHI NHẬN", "TÌNH TRẠNG LÁ", "TÌNH TRẠNG SINH TRƯỞNG",
            "NHẬN XÉT", "NHÂN VIÊN KHẢO SÁT", "THAO TÁC"
        ]
        self.ui.tableSurveys.setHorizontalHeaderLabels(headers)

        header = self.ui.tableSurveys.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

    def setup_permissions(self):
        """Phân quyền - Ẩn nút thêm nếu là khách"""
        if self.is_guest:
            if hasattr(self.ui, "btnAddSurvey"):
                self.ui.btnAddSurvey.setVisible(False)
                self.ui.btnAddSurvey.setEnabled(False)
            self.setWindowTitle("PHIẾU KHẢO SÁT - Chế độ xem")
        else:
            if hasattr(self.ui, "btnAddSurvey"):
                self.ui.btnAddSurvey.setVisible(True)
                self.ui.btnAddSurvey.setEnabled(True)
            self.setWindowTitle("PHIẾU KHẢO SÁT")

    def load_data_from_db(self):
        """Hàm lấy dữ liệu từ DB và đổ lên QTableWidget"""
        try:
            self.ui.tableSurveys.setColumnCount(10)
            headers = [
                "MÃ KS", "MÃ CÂY", "NGÀY KHẢO SÁT", "CHIỀU CAO GHI NHẬN",
                "ĐƯỜNG KÍNH GHI NHẬN", "TÌNH TRẠNG LÁ", "TÌNH TRẠNG SINH TRƯỞNG",
                "NHẬN XÉT", "NHÂN VIÊN KHẢO SÁT", "THAO TÁC"
            ]
            self.ui.tableSurveys.setHorizontalHeaderLabels(headers)
            self.ui.tableSurveys.setRowCount(0)

            conn = get_db_connection()
            cursor = conn.cursor()

            query = """
                    SELECT 
                        P.MAKS, 
                        P.MACAY, 
                        P.NGAYKHAOSAT, 
                        P.CHIEUCAOGHINHAN, 
                        P.DUONGKINHGHINHAN, 
                        P.TINHTRANGLA, 
                        P.TINHTRANGSINHTRUONG, 
                        P.NHANXET, 
                        NV.HOTEN
                    FROM PHIEU_KHAO_SAT P
                    LEFT JOIN NHAN_VIEN NV ON P.MANV = NV.MANV
                    """
            cursor.execute(query)
            rows = cursor.fetchall()

            for row_idx, row_data in enumerate(rows):
                self.ui.tableSurveys.insertRow(row_idx)

                for col_idx in range(9):
                    val = str(row_data[col_idx]) if row_data[col_idx] is not None else ""
                    if col_idx == 2 and row_data[col_idx]:
                        val = row_data[col_idx].strftime("%Y-%m-%d") if hasattr(row_data[col_idx], 'strftime') else str(
                            row_data[col_idx])

                    item = QTableWidgetItem(val)

                    if col_idx in [5, 6] and val:
                        status = val.lower()
                        if "tốt" in status or "mới" in status or "xanh" in status or "bóng" in status:
                            item.setBackground(QBrush(QColor(222, 245, 227)))
                            item.setForeground(QBrush(QColor(27, 107, 57)))
                        elif "trung bình" in status or "cần theo dõi" in status or "phục hồi" in status or "vàng" in status:
                            item.setBackground(QBrush(QColor(252, 236, 205)))
                            item.setForeground(QBrush(QColor(158, 106, 11)))
                        else:
                            item.setBackground(QBrush(QColor(255, 205, 210)))
                            item.setForeground(QBrush(QColor(211, 47, 47)))

                    self.ui.tableSurveys.setItem(row_idx, col_idx, item)

                # Cột Thao tác - hiển thị theo quyền
                btn_text = "👁 Chỉ xem" if self.is_guest else "✏️ 🗑"
                btn_item = QTableWidgetItem(btn_text)
                btn_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tableSurveys.setItem(row_idx, 9, btn_item)

            conn.close()
            self.update_pagination_info()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Database", f"Không thể tải dữ liệu: {str(e)}")

    def connect_signals(self):
        # Các nút chức năng
        self.ui.btnMenuToggle.clicked.connect(self.handle_toggle_menu)
        self.ui.btnAddSurvey.clicked.connect(self.handle_add_survey)
        self.ui.searchBox.textChanged.connect(self.handle_search)
        self.ui.tableSurveys.cellClicked.connect(self.handle_table_click)

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
        if hasattr(self.ui, "navYeuCauBaoTri"):
            self.ui.navYeuCauBaoTri.clicked.connect(self.open_yeu_cau_bao_tri)
        if hasattr(self.ui, "navBaoCaoSuCo"):
            self.ui.navBaoCaoSuCo.clicked.connect(self.open_bao_cao_su_co)

    def handle_toggle_menu(self):
        is_visible = self.ui.sidebarFrame.isVisible()
        self.ui.sidebarFrame.setVisible(not is_visible)

    def handle_add_survey(self):
        """Thêm khảo sát - CHỈ ADMIN/NHÂN VIÊN"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền thêm khảo sát!")
            return

        dialog = ThemKhaoSatDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()

            if not new_data[3] or not new_data[4]:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập chiều cao và đường kính!")
                return

            # Lưu vào database
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Lấy MANV từ tên
                manv = ""
                ten_nv = new_data[8] if new_data[8] else ""
                if ten_nv:
                    cursor.execute("SELECT MANV FROM NHAN_VIEN WHERE HOTEN LIKE ?", (f"%{ten_nv}%",))
                    row = cursor.fetchone()
                    if row:
                        manv = row[0]

                cursor.execute("""
                    INSERT INTO PHIEU_KHAO_SAT 
                    (MAKS, MACAY, NGAYKHAOSAT, CHIEUCAOGHINHAN, DUONGKINHGHINHAN,
                     TINHTRANGLA, TINHTRANGSINHTRUONG, NHANXET, MANV)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    new_data[0],
                    new_data[1],
                    new_data[2],
                    float(new_data[3]) if new_data[3] else None,
                    float(new_data[4]) if new_data[4] else None,
                    new_data[5],
                    new_data[6],
                    new_data[7],
                    manv
                ))
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Thành công", f"Đã thêm khảo sát mới: {new_data[0]}")
                self.load_data_from_db()

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu vào database:\n{str(e)}")

    def handle_search(self, text):
        print(f"Từ khóa tìm kiếm khảo sát: {text}")

    def handle_table_click(self, row, column):
        """Xử lý click vào bảng"""
        if column == 9:
            row_data = []
            for col in range(9):
                item = self.ui.tableSurveys.item(row, col)
                row_data.append(item.text() if item else "")

            ma_ks = row_data[0]

            # Nếu là khách hàng -> chỉ xem chi tiết
            if self.is_guest:
                self.show_detail_popup(row_data)
                return

            # Nếu là admin/nhân viên -> hiển thị menu đầy đủ
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Lựa chọn thao tác")
            msg_box.setText(f"THAO TÁC KHẢO SÁT: {ma_ks}")

            btn_view = msg_box.addButton("🔍 Xem chi tiết", QMessageBox.ButtonRole.ActionRole)
            btn_edit = msg_box.addButton("✏️ Chỉnh sửa", QMessageBox.ButtonRole.ActionRole)
            btn_delete = msg_box.addButton("🗑 Xóa khảo sát", QMessageBox.ButtonRole.ActionRole)
            msg_box.addButton("❌ Hủy bỏ", QMessageBox.ButtonRole.RejectRole)

            msg_box.exec()

            if msg_box.clickedButton() == btn_view:
                self.show_detail_popup(row_data)
            elif msg_box.clickedButton() == btn_edit:
                self.show_edit_popup(row, row_data)
            elif msg_box.clickedButton() == btn_delete:
                self.confirm_and_delete(row, ma_ks)

    def show_detail_popup(self, row_data):
        dialog = ChiTietKhaoSatDialog(row_data, self)
        dialog.exec()

    def show_edit_popup(self, row, row_data):
        """Sửa khảo sát - CHỈ ADMIN/NHÂN VIÊN"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền chỉnh sửa khảo sát!")
            return

        dialog = ChinhSuaKhaoSatDialog(row_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_data()

            # Cập nhật database
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Lấy MANV từ tên
                manv = ""
                ten_nv = updated_data[8] if updated_data[8] else ""
                if ten_nv:
                    cursor.execute("SELECT MANV FROM NHAN_VIEN WHERE HOTEN LIKE ?", (f"%{ten_nv}%",))
                    row_nv = cursor.fetchone()
                    if row_nv:
                        manv = row_nv[0]

                cursor.execute("""
                    UPDATE PHIEU_KHAO_SAT 
                    SET MACAY = ?, NGAYKHAOSAT = ?, CHIEUCAOGHINHAN = ?, DUONGKINHGHINHAN = ?,
                        TINHTRANGLA = ?, TINHTRANGSINHTRUONG = ?, NHANXET = ?, MANV = ?
                    WHERE MAKS = ?
                """, (
                    updated_data[1],
                    updated_data[2],
                    float(updated_data[3]) if updated_data[3] else None,
                    float(updated_data[4]) if updated_data[4] else None,
                    updated_data[5],
                    updated_data[6],
                    updated_data[7],
                    manv,
                    updated_data[0]
                ))
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Thành công", f"Đã cập nhật phiếu khảo sát {updated_data[0]} thành công!")
                self.load_data_from_db()

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật:\n{str(e)}")

    def confirm_and_delete(self, row, ma_ks):
        """Xóa khảo sát - CHỈ ADMIN/NHÂN VIÊN"""
        if self.is_guest:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Bạn không có quyền xóa khảo sát!")
            return

        reply = QMessageBox.question(
            self, "Xác nhận xóa", f"Bạn có chắc chắn muốn xóa hoàn toàn phiếu khảo sát {ma_ks}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM PHIEU_KHAO_SAT WHERE MAKS = ?", (ma_ks,))
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Thành công", f"Đã xóa thành công khảo sát {ma_ks}!")
                self.load_data_from_db()

            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể xóa:\n{str(e)}")

    def update_pagination_info(self):
        total_rows = self.ui.tableSurveys.rowCount()
        if total_rows > 0:
            self.ui.paginationInfo.setText(f"Hiển thị 1 đến {total_rows} trong tổng số {total_rows} đợt khảo sát")
        else:
            self.ui.paginationInfo.setText("Không còn đợt khảo sát nào trong danh sách")

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

    def open_phieu_cham_soc(self):
        try:
            from phieu_cham_socEx import PhieuChamSocEx
            self.window = PhieuChamSocEx(self.username, self.role)
            self.window.show()
            self.close()
        except Exception as e:
            print(f"Lỗi mở phiếu chăm sóc: {e}")

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
    window = PhieuKhaoSatEx(username="Admin", role="Quản trị viên")
    window.show()
    sys.exit(app.exec())