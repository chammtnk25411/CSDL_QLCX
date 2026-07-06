# PhieuloaiEx.py
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QDialog, QMessageBox, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QComboBox, QGroupBox,
    QFormLayout, QPushButton, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi
import pyodbc
import config


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


class PlantInfoDialog(QDialog):
    """Dialog thêm/sửa thông tin loài thực vật"""

    def __init__(self, parent=None, edit_mode=False, plant_data=None):
        super().__init__(parent)

        self.edit_mode = edit_mode
        self.plant_data = plant_data
        self.result_data = None

        # Tạo giao diện bằng code thay vì load UI
        self.setWindowTitle("PHIẾU THÔNG TIN LOÀI THỰC VẬT")
        self.setFixedSize(700, 700)
        self.setStyleSheet("""
            QDialog { background-color: #f5f6fa; }
            QLabel { color: #2c3e50; font-weight: bold; font-size: 13px; }
            QLineEdit, QTextEdit, QComboBox {
                font-size: 13px; padding: 8px;
                border: 2px solid #bdc3c7; border-radius: 4px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border-color: #3498db;
            }
        """)

        self.setup_ui()
        self.load_families()

        if edit_mode and plant_data:
            self.load_data(plant_data)
        else:
            self.generate_auto_id()

    def setup_ui(self):
        """Thiết lập giao diện"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 30, 40, 30)

        # Tiêu đề
        title_label = QLabel("PHIẾU THÔNG TIN LOÀI THỰC VẬT")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 22px; font-weight: bold; padding: 12px;
            background-color: #3498db; color: white; border-radius: 8px;
        """)
        main_layout.addWidget(title_label)

        # Group thông tin
        group_box = QGroupBox("THÔNG TIN CHI TIẾT")
        group_box.setStyleSheet("""
            QGroupBox {
                font-weight: bold; font-size: 14px; color: #2c3e50;
                border: 2px solid #bdc3c7; border-radius: 8px;
                margin-top: 15px; padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin; left: 20px;
                padding: 0 10px; background-color: white;
            }
        """)

        form_layout = QFormLayout(group_box)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(15)

        # Mã loài
        self.idInput = QLineEdit()
        self.idInput.setEnabled(False)
        self.idInput.setStyleSheet("""
            padding: 8px; border: 2px solid #3498db; border-radius: 4px;
            background-color: #ecf0f1; color: #2c3e50; font-weight: bold;
        """)
        form_layout.addRow("Mã loài", self.idInput)

        # Tên thường gọi
        self.nameInput = QLineEdit()
        self.nameInput.setPlaceholderText("Nhập tên thường gọi")
        self.nameInput.setStyleSheet("padding: 8px; border: 2px solid #e74c3c; border-radius: 4px;")
        form_layout.addRow("Tên thường gọi *", self.nameInput)

        # Tên khoa học
        self.scientificNameInput = QLineEdit()
        self.scientificNameInput.setPlaceholderText("Nhập tên khoa học")
        self.scientificNameInput.setStyleSheet("padding: 8px; border: 2px solid #e74c3c; border-radius: 4px;")
        form_layout.addRow("Tên khoa học *", self.scientificNameInput)

        # Họ thực vật - QComboBox
        self.familyInput = QComboBox()
        self.familyInput.setStyleSheet("padding: 8px; border: 2px solid #bdc3c7; border-radius: 4px;")
        self.familyInput.addItem("Chọn họ...")
        form_layout.addRow("Họ thực vật", self.familyInput)

        # Đặc điểm sinh học
        self.characteristicsInput = QTextEdit()
        self.characteristicsInput.setPlaceholderText("Nhập đặc điểm sinh học")
        self.characteristicsInput.setMaximumHeight(80)
        form_layout.addRow("Đặc điểm sinh học", self.characteristicsInput)

        # Môi trường sống
        self.habitatInput = QLineEdit()
        self.habitatInput.setPlaceholderText("Nhập môi trường sống")
        form_layout.addRow("Môi trường sống", self.habitatInput)

        # Tình trạng bảo tồn
        self.statusCombo = QComboBox()
        self.statusCombo.setStyleSheet("padding: 8px; border: 2px solid #bdc3c7; border-radius: 4px;")
        self.statusCombo.addItems([
            'Ít lo ngại (LC)', 'Gần nguy cấp (NT)',
            'Sẽ nguy cấp (VU)', 'Nguy cấp (EN)',
            'Cực kỳ nguy cấp (CR)'
        ])
        form_layout.addRow("Tình trạng bảo tồn", self.statusCombo)

        main_layout.addWidget(group_box)

        # Spacer
        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Nút bấm
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancelButton = QPushButton("Hủy")
        self.cancelButton.setMinimumSize(120, 45)
        self.cancelButton.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6; color: white; border: none;
                border-radius: 6px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #7f8c8d; }
        """)
        self.cancelButton.clicked.connect(self.reject)

        self.saveButton = QPushButton("Lưu thông tin")
        self.saveButton.setMinimumSize(120, 45)
        self.saveButton.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; color: white; border: none;
                border-radius: 6px; font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #219a52; }
        """)
        self.saveButton.clicked.connect(self.save_data)

        button_layout.addWidget(self.cancelButton)
        button_layout.addWidget(self.saveButton)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)

    def load_families(self):
        """Load danh sách họ thực vật từ database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAHO, TENHO FROM HO_THUC_VAT ORDER BY TENHO")
            rows = cursor.fetchall()

            self.familyInput.clear()
            self.familyInput.addItem("Chọn họ...")

            for row in rows:
                self.familyInput.addItem(row[1], row[0])

            conn.close()

        except Exception as e:
            QMessageBox.warning(self, "Cảnh báo", f"Không thể load danh sách họ: {str(e)}\nSử dụng dữ liệu mẫu!")
            self.familyInput.clear()
            self.familyInput.addItem("Chọn họ...")
            self.familyInput.addItem("Họ Phong lan", "HO01")
            self.familyInput.addItem("Họ Đậu", "HO02")
            self.familyInput.addItem("Họ Ráy", "HO03")
            self.familyInput.addItem("Họ Cau", "HO04")
            self.familyInput.addItem("Họ Trúc đào", "HO05")
            self.familyInput.addItem("Họ Bách", "HO06")

    def generate_auto_id(self):
        """Tạo mã loài tự động từ database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(MALOAI) FROM LOAI_THUC_VAT")
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                last_id = row[0]
                num = int(last_id.replace('LOAI', '')) + 1
                new_id = f"LOAI{num:02d}"
            else:
                new_id = "LOAI01"
            self.idInput.setText(new_id)
        except:
            self.idInput.setText("LOAI01")

    def load_data(self, data):
        """Load dữ liệu vào form khi sửa"""
        if data:
            self.idInput.setText(data.get('MALOAI', ''))
            self.nameInput.setText(data.get('TENTHUONGGOI', ''))
            self.scientificNameInput.setText(data.get('TENKHOAHOC', ''))
            self.characteristicsInput.setText(data.get('DACDIEMSINHHOC', ''))
            self.habitatInput.setText(data.get('MOITRUONGSONG', ''))

            # Set họ
            mah = data.get('MAHO', '')
            index = self.familyInput.findData(mah)
            if index >= 0:
                self.familyInput.setCurrentIndex(index)

            # Set tình trạng
            status = data.get('TINHTRANGBAOTON', '')
            index = self.statusCombo.findText(status)
            if index >= 0:
                self.statusCombo.setCurrentIndex(index)

    def validate_data(self):
        """Kiểm tra dữ liệu"""
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên thường gọi!")
            self.nameInput.setFocus()
            return False
        if not self.scientificNameInput.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên khoa học!")
            self.scientificNameInput.setFocus()
            return False
        if self.familyInput.currentIndex() == 0:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn họ thực vật!")
            self.familyInput.setFocus()
            return False
        return True

    def save_data(self):
        """Lưu dữ liệu"""
        if not self.validate_data():
            return

        self.result_data = {
            'MALOAI': self.idInput.text(),
            'TENTHUONGGOI': self.nameInput.text().strip(),
            'TENKHOAHOC': self.scientificNameInput.text().strip(),
            'MAHO': self.familyInput.currentData(),
            'DACDIEMSINHHOC': self.characteristicsInput.toPlainText().strip(),
            'MOITRUONGSONG': self.habitatInput.text().strip(),
            'TINHTRANGBAOTON': self.statusCombo.currentText()
        }
        self.accept()

    def get_data(self):
        return self.result_data


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = PlantInfoDialog(edit_mode=False)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_data()
        if data:
            print("Dữ liệu nhập:")
            for key, value in data.items():
                print(f"  {key}: {value}")
    sys.exit()