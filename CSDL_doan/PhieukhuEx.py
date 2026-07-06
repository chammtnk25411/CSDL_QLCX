# PhieukhuEx.py
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QDialog, QMessageBox, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QGroupBox, QFormLayout,
    QPushButton, QSpacerItem, QSizePolicy
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


class AreaInfoDialog(QDialog):
    """Dialog thêm/sửa thông tin khu trưng bày"""

    def __init__(self, parent=None, edit_mode=False, area_data=None, existing_ids=None):
        super().__init__(parent)

        self.edit_mode = edit_mode
        self.area_data = area_data
        self.existing_ids = existing_ids or []
        self.result_data = None

        # Tạo giao diện bằng code
        self.setWindowTitle("PHIẾU THÔNG TIN KHU TRƯNG BÀY")
        self.setFixedSize(700, 600)
        self.setStyleSheet("""
            QDialog { background-color: #f5f6fa; }
            QLabel { color: #2c3e50; font-weight: bold; font-size: 13px; }
            QLineEdit, QTextEdit {
                font-size: 13px; padding: 8px;
                border: 2px solid #bdc3c7; border-radius: 4px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #3498db;
            }
        """)

        self.setup_ui()

        if edit_mode and area_data:
            self.load_data(area_data)
        else:
            self.generate_auto_id()

    def setup_ui(self):
        """Thiết lập giao diện"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 30, 40, 30)

        # Tiêu đề
        title_label = QLabel("PHIẾU THÔNG TIN KHU TRƯNG BÀY")
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

        # Mã khu
        self.idInput = QLineEdit()
        self.idInput.setEnabled(False)
        self.idInput.setStyleSheet("""
            padding: 8px; border: 2px solid #3498db; border-radius: 4px;
            background-color: #ecf0f1; color: #2c3e50; font-weight: bold;
        """)
        form_layout.addRow("Mã khu", self.idInput)

        # Tên khu
        self.nameInput = QLineEdit()
        self.nameInput.setPlaceholderText("Nhập tên khu")
        self.nameInput.setStyleSheet("padding: 8px; border: 2px solid #e74c3c; border-radius: 4px;")
        form_layout.addRow("Tên khu *", self.nameInput)

        # Vị trí
        self.locationInput = QLineEdit()
        self.locationInput.setPlaceholderText("Nhập vị trí")
        form_layout.addRow("Vị trí", self.locationInput)

        # Diện tích
        self.areaInput = QLineEdit()
        self.areaInput.setPlaceholderText("Nhập diện tích (m²)")
        form_layout.addRow("Diện tích (m²)", self.areaInput)

        # Mô tả
        self.descriptionInput = QTextEdit()
        self.descriptionInput.setPlaceholderText("Nhập mô tả")
        self.descriptionInput.setMaximumHeight(100)
        form_layout.addRow("Mô tả", self.descriptionInput)

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

    def generate_auto_id(self):
        """Tạo mã khu tự động từ database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(MAKHU) FROM KHU_TRUNG_BAY")
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                last_id = row[0]
                num = int(last_id.replace('KHU', '')) + 1
                new_id = f"KHU{num:02d}"
            else:
                new_id = "KHU01"
            self.idInput.setText(new_id)
        except:
            if not self.existing_ids:
                new_id = "KHU01"
            else:
                max_num = 0
                for id_str in self.existing_ids:
                    try:
                        num = int(id_str.replace('KHU', ''))
                        if num > max_num:
                            max_num = num
                    except:
                        continue
                new_id = f"KHU{max_num + 1:02d}"
            self.idInput.setText(new_id)

    def load_data(self, data):
        """Load dữ liệu vào form khi sửa"""
        if data:
            self.idInput.setText(data.get('MAKHU', ''))
            self.nameInput.setText(data.get('TENKHU', ''))
            self.locationInput.setText(data.get('VITRI', ''))
            dientich = data.get('DIENTICH', 0)
            self.areaInput.setText(str(dientich) if dientich else '')
            self.descriptionInput.setText(data.get('MOTA', ''))

    def validate_data(self):
        """Kiểm tra dữ liệu"""
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên khu!")
            self.nameInput.setFocus()
            return False

        # Kiểm tra diện tích
        area_text = self.areaInput.text().strip()
        if area_text:
            try:
                float(area_text.replace(',', ''))
            except ValueError:
                QMessageBox.warning(self, "Lỗi", "Diện tích phải là số!")
                self.areaInput.setFocus()
                return False

        return True

    def save_data(self):
        """Lưu dữ liệu"""
        if not self.validate_data():
            return

        area_text = self.areaInput.text().strip().replace(',', '')
        dientich = float(area_text) if area_text else 0

        self.result_data = {
            'MAKHU': self.idInput.text(),
            'TENKHU': self.nameInput.text().strip(),
            'VITRI': self.locationInput.text().strip(),
            'DIENTICH': dientich,
            'MOTA': self.descriptionInput.toPlainText().strip()
        }
        self.accept()

    def get_data(self):
        return self.result_data


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = AreaInfoDialog(edit_mode=False)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_data()
        if data:
            print("Dữ liệu nhập:")
            for key, value in data.items():
                print(f"  {key}: {value}")
    sys.exit()