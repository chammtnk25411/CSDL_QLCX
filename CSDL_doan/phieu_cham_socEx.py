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

            clean_text = data[i].replace('\n', ' ')
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
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self._dialog = None

        self.setup_defaults()
        self.connect_signals()

    def setup_defaults(self):
        self.ui.filterTuNgay.setDate(QDate.currentDate().addMonths(-1))
        self.ui.filterDenNgay.setDate(QDate.currentDate())

        header = self.ui.tableCareRecords.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

    def connect_signals(self):
        self.ui.btnMenuToggle.clicked.connect(self.handle_toggle_menu)
        self.ui.btnAddSurvey.clicked.connect(self.handle_add_care_record)
        self.ui.searchBox.textChanged.connect(self.handle_search)
        self.ui.tableCareRecords.cellClicked.connect(self.handle_table_click)

    def handle_toggle_menu(self):
        is_visible = self.ui.sidebarFrame.isVisible()
        self.ui.sidebarFrame.setVisible(not is_visible)

    def handle_add_care_record(self):
        try:
            self._dialog = ThemPhieuDialog(self)
            if self._dialog.exec() == int(QDialog.DialogCode.Accepted):
                new_data = self._dialog.get_data()

                if not new_data[0].strip():
                    QMessageBox.warning(self, "Lỗi nhập liệu", "Vui lòng nhập Mã phiếu chăm sóc!")
                    return

                sorting_enabled = self.ui.tableCareRecords.isSortingEnabled()
                self.ui.tableCareRecords.setSortingEnabled(False)

                row = 0
                self.ui.tableCareRecords.insertRow(row)

                for col in range(9):
                    item = QTableWidgetItem(new_data[col])

                    if col == 0:
                        item.setForeground(QBrush(QColor(27, 110, 110)))
                    elif col == 5:
                        status = new_data[col]
                        if status == "Tốt":
                            item.setBackground(QBrush(QColor(222, 245, 227)))
                            item.setForeground(QBrush(QColor(27, 107, 57)))
                        elif status == "Trung bình":
                            item.setBackground(QBrush(QColor(252, 236, 205)))
                            item.setForeground(QBrush(QColor(158, 106, 11)))
                        else:
                            item.setBackground(QBrush(QColor(255, 205, 210)))
                            item.setForeground(QBrush(QColor(211, 47, 47)))
                    elif col == 8:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    self.ui.tableCareRecords.setItem(row, col, item)

                self.ui.tableCareRecords.setSortingEnabled(sorting_enabled)
                self.update_pagination_info()
                QMessageBox.information(self, "Thành công", f"Đã thêm phiếu {new_data[0]} thành công!")

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi Runtime", f"Đã xảy ra lỗi:\n{str(e)}")

    def handle_search(self, text):
        # Bạn có thể bổ sung logic tìm kiếm ở đây sau
        pass

    def handle_table_click(self, row, column):
        if column == 8:
            row_data = []
            for col in range(8):
                item = self.ui.tableCareRecords.item(row, col)
                row_data.append(item.text() if item else "")

            ma_phieu = row_data[0]

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
        dialog = ChinhSuaPhieuDialog(row_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_data()

            for col in range(9):
                item = self.ui.tableCareRecords.item(row, col)
                if not item:
                    item = QTableWidgetItem()
                    self.ui.tableCareRecords.setItem(row, col, item)

                item.setText(updated_data[col])

                if col == 0:
                    item.setForeground(QBrush(QColor(27, 110, 110)))
                elif col == 5:
                    status = updated_data[col]
                    if status == "Tốt":
                        item.setBackground(QBrush(QColor(222, 245, 227)))
                        item.setForeground(QBrush(QColor(27, 107, 57)))
                    elif status == "Trung bình":
                        item.setBackground(QBrush(QColor(252, 236, 205)))
                        item.setForeground(QBrush(QColor(158, 106, 11)))
                    else:
                        item.setBackground(QBrush(QColor(255, 205, 210)))
                        item.setForeground(QBrush(QColor(211, 47, 47)))
                elif col == 8:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            QMessageBox.information(self, "Thành công", f"Đã cập nhật phiếu {updated_data[0]} thành công!")

    def confirm_and_delete(self, row, ma_phieu):
        reply = QMessageBox.question(
            self, "Xác nhận xóa", f"Bạn có chắc chắn muốn xóa hoàn toàn phiếu {ma_phieu}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ui.tableCareRecords.removeRow(row)
            self.update_pagination_info()
            QMessageBox.information(self, "Thành công", f"Đã xóa thành công phiếu {ma_phieu}!")

    def update_pagination_info(self):
        total_rows = self.ui.tableCareRecords.rowCount()
        if total_rows > 0:
            self.ui.paginationInfo.setText(f"Hiển thị 1 đến {total_rows} trong tổng số {total_rows} phiếu chăm sóc")
        else:
            self.ui.paginationInfo.setText("Không còn phiếu chăm sóc nào trong danh sách")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhieuChamSocEx()
    window.show()
    sys.exit(app.exec())