import sys
import datetime
import pyodbc
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QHeaderView,
                             QDialog, QVBoxLayout, QLabel, QFormLayout, QPushButton,
                             QHBoxLayout, QLineEdit, QComboBox, QDateEdit, QTableWidgetItem)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QBrush, QColor

import config
from phieu_khao_sat import Ui_MainWindow # Đảm bảo bạn import đúng tên file UI


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
            "Nhận xét:", "Mã nhân viên/Tên nhân viên:"
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
            ["Sinh trưởng tốt", "Sinh trưởng trung bình", "Sinh trưởng kém", "Cần theo dõi", "Đang phục hồi", "Bị sâu bệnh"])
        self.cbo_sinhtruong.setCurrentText(data[6] if len(data) > 6 else "")
        form_layout.addRow("Tình trạng sinh trưởng:", self.cbo_sinhtruong)

        self.txt_nhanxet = QLineEdit()
        self.txt_nhanxet.setText(data[7] if len(data) > 7 else "")
        form_layout.addRow("Nhận xét:", self.txt_nhanxet)

        self.txt_manv = QLineEdit()
        self.txt_manv.setText(data[8] if len(data) > 8 else "")
        form_layout.addRow("Mã nhân viên:", self.txt_manv)

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
            "👁   🗑" # Chỉnh lại thành icon nếu cần
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
            ["Sinh trưởng tốt", "Sinh trưởng trung bình", "Sinh trưởng kém", "Cần theo dõi", "Đang phục hồi", "Bị sâu bệnh"])
        form_layout.addRow("Tình trạng sinh trưởng:", self.cbo_sinhtruong)

        self.txt_nhanxet = QLineEdit()
        self.txt_nhanxet.setPlaceholderText("Nhập đánh giá tổng quan...")
        form_layout.addRow("Nhận xét:", self.txt_nhanxet)

        self.txt_manv = QLineEdit()
        self.txt_manv.setPlaceholderText("VD: NV01")
        form_layout.addRow("Mã nhân viên:", self.txt_manv)

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
            "👁   🗑" # Chỉnh lại thành icon nếu cần
        ]


class PhieuKhaoSatEx(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setup_defaults()
        self.connect_signals()

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

    def load_data_from_db(self):
        """Hàm lấy dữ liệu từ DB và đổ lên QTableWidget"""
        try:
            # Thiết lập lại số cột một lần nữa cho chắc chắn
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

            # LƯU Ý QUAN TRỌNG: Câu query đã được cập nhật ĐỦ 9 CỘT DỮ LIỆU.
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
                        NV.TENNV
                    FROM PHIEUKHAOSAT P
                    LEFT JOIN NHANVIEN NV ON P.MANV = NV.MANV
                    """
            cursor.execute(query)
            rows = cursor.fetchall()

            for row_idx, row_data in enumerate(rows):
                self.ui.tableSurveys.insertRow(row_idx)

                # CẬP NHẬT QUAN TRỌNG: Lặp đúng 9 cột dữ liệu (index 0 đến 8)
                for col_idx in range(9):
                    if col_idx == 2 and row_data[col_idx]:
                        val = row_data[col_idx].strftime("%Y-%m-%d") if hasattr(row_data[col_idx], 'strftime') else str(row_data[col_idx])
                    else:
                        val = str(row_data[col_idx]) if row_data[col_idx] is not None else ""

                    item = QTableWidgetItem(val)

                    # Định dạng màu sắc dựa vào Tình trạng lá (index 5) và Tình trạng sinh trưởng (index 6)
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

                    # Gán giá trị vào cột tương ứng (từ 0 đến 8)
                    self.ui.tableSurveys.setItem(row_idx, col_idx, item)

                # Gán Nút Thao tác vào đúng Cột cuối cùng (Index 9)
                btn_item = QTableWidgetItem("👁   🗑") # Thay icon tại đây nếu muốn
                btn_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.ui.tableSurveys.setItem(row_idx, 9, btn_item)

            conn.close()
            self.update_pagination_info()

        except Exception as e:
            QMessageBox.critical(self, "Lỗi Database", f"Không thể tải dữ liệu: {str(e)}")

    def connect_signals(self):
        self.ui.btnMenuToggle.clicked.connect(self.handle_toggle_menu)
        self.ui.btnAddSurvey.clicked.connect(self.handle_add_survey)
        self.ui.searchBox.textChanged.connect(self.handle_search)
        self.ui.tableSurveys.cellClicked.connect(self.handle_table_click)

    def handle_toggle_menu(self):
        is_visible = self.ui.sidebarFrame.isVisible()
        self.ui.sidebarFrame.setVisible(not is_visible)

    def handle_add_survey(self):
        dialog = ThemKhaoSatDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_data()

            if not new_data[3] or not new_data[4]:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập chiều cao và đường kính!")
                return

            self.ui.tableSurveys.insertRow(0)

            # CẬP NHẬT QUAN TRỌNG: Cập nhật vòng lặp lấy 10 cột dữ liệu từ data thêm mới (index 0 đến 9)
            for col in range(10):
                item = QTableWidgetItem()
                item.setText(new_data[col])
                self.ui.tableSurveys.setItem(0, col, item)

                if col in [5, 6]:
                    status = new_data[col].lower()
                    if "tốt" in status or "xanh" in status:
                        item.setBackground(QBrush(QColor(222, 245, 227)))
                        item.setForeground(QBrush(QColor(27, 107, 57)))
                    elif "trung bình" in status or "vàng" in status or "cần theo dõi" in status or "phục hồi" in status:
                        item.setBackground(QBrush(QColor(252, 236, 205)))
                        item.setForeground(QBrush(QColor(158, 106, 11)))
                    else:
                        item.setBackground(QBrush(QColor(255, 205, 210)))
                        item.setForeground(QBrush(QColor(211, 47, 47)))
                elif col == 9: # Nút thao tác
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.update_pagination_info()
            QMessageBox.information(self, "Thành công", f"Đã thêm khảo sát mới: {new_data[0]}")

    def handle_search(self, text):
        print(f"Từ khóa tìm kiếm khảo sát: {text}")

    def handle_table_click(self, row, column):
        # Index của cột thao tác là 9
        if column == 9:
            row_data = []
            for col in range(9):
                item = self.ui.tableSurveys.item(row, col)
                row_data.append(item.text() if item else "")

            ma_ks = row_data[0]

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
        dialog = ChinhSuaKhaoSatDialog(row_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_data()

            for col in range(10):
                item = self.ui.tableSurveys.item(row, col)
                if not item:
                    item = QTableWidgetItem()
                    self.ui.tableSurveys.setItem(row, col, item)

                item.setText(updated_data[col])

                if col in [5, 6]:
                    status = updated_data[col].lower()
                    if "tốt" in status or "xanh" in status:
                        item.setBackground(QBrush(QColor(222, 245, 227)))
                        item.setForeground(QBrush(QColor(27, 107, 57)))
                    elif "trung bình" in status or "cần theo dõi" in status or "vàng" in status or "phục hồi" in status:
                        item.setBackground(QBrush(QColor(252, 236, 205)))
                        item.setForeground(QBrush(QColor(158, 106, 11)))
                    else:
                        item.setBackground(QBrush(QColor(255, 205, 210)))
                        item.setForeground(QBrush(QColor(211, 47, 47)))
                elif col == 9:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            QMessageBox.information(self, "Thành công", f"Đã cập nhật phiếu khảo sát {updated_data[0]} thành công!")

    def confirm_and_delete(self, row, ma_ks):
        reply = QMessageBox.question(
            self, "Xác nhận xóa", f"Bạn có chắc chắn muốn xóa hoàn toàn phiếu khảo sát {ma_ks}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ui.tableSurveys.removeRow(row)
            self.update_pagination_info()
            QMessageBox.information(self, "Thành công", f"Đã xóa thành công khảo sát {ma_ks}!")

    def update_pagination_info(self):
        total_rows = self.ui.tableSurveys.rowCount()
        if total_rows > 0:
            self.ui.paginationInfo.setText(f"Hiển thị 1 đến {total_rows} trong tổng số {total_rows} đợt khảo sát")
        else:
            self.ui.paginationInfo.setText("Không còn đợt khảo sát nào trong danh sách")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhieuKhaoSatEx()
    window.show()
    sys.exit(app.exec())