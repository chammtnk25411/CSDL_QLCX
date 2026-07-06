# PhieuhoEx.py
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


class FamilyInfoDialog(QDialog):
    """Dialog thêm/sửa thông tin họ thực vật"""

    def __init__(self, parent=None, edit_mode=False, family_data=None, existing_ids=None):
        super().__init__(parent)

        self.edit_mode = edit_mode
        self.family_data = family_data
        self.existing_ids = existing_ids or []
        self.result_data = None

        # Tạo giao diện bằng code
        self.setWindowTitle("PHIẾU THÔNG TIN HỌ THỰC VẬT")
        self.setFixedSize(700, 500)
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

        if edit_mode and family_data:
            self.load_data(family_data)
        else:
            self.generate_auto_id()

    def setup_ui(self):
        """Thiết lập giao diện"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(40, 30, 40, 30)

        # Tiêu đề
        title_label = QLabel("PHIẾU THÔNG TIN HỌ THỰC VẬT")
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

        # Mã họ
        self.idInput = QLineEdit()
        self.idInput.setEnabled(False)
        self.idInput.setStyleSheet("""
            padding: 8px; border: 2px solid #3498db; border-radius: 4px;
            background-color: #ecf0f1; color: #2c3e50; font-weight: bold;
        """)
        form_layout.addRow("Mã họ", self.idInput)

        # Tên họ
        self.nameInput = QLineEdit()
        self.nameInput.setPlaceholderText("Nhập tên họ")
        self.nameInput.setStyleSheet("padding: 8px; border: 2px solid #e74c3c; border-radius: 4px;")
        form_layout.addRow("Tên họ *", self.nameInput)

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
        """Tạo mã họ tự động từ database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(MAHO) FROM HO_THUC_VAT")
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                last_id = row[0]
                num = int(last_id.replace('HF', '')) + 1
                new_id = f"HF{num:03d}"
            else:
                new_id = "HF001"
            self.idInput.setText(new_id)
        except:
            if not self.existing_ids:
                new_id = "HF001"
            else:
                max_num = 0
                for id_str in self.existing_ids:
                    try:
                        num = int(id_str.replace('HF', ''))
                        if num > max_num:
                            max_num = num
                    except:
                        continue
                new_id = f"HF{max_num + 1:03d}"
            self.idInput.setText(new_id)

    def load_data(self, data):
        """Load dữ liệu vào form khi sửa"""
        if data:
            self.idInput.setText(data.get('MAHO', ''))
            self.nameInput.setText(data.get('TENHO', ''))
            self.descriptionInput.setText(data.get('MOTA', ''))

    def validate_data(self):
        """Kiểm tra dữ liệu"""
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập tên họ!")
            self.nameInput.setFocus()
            return False
        return True

    def save_data(self):
        """Lưu dữ liệu"""
        if not self.validate_data():
            return

        self.result_data = {
            'MAHO': self.idInput.text(),
            'TENHO': self.nameInput.text().strip(),
            'MOTA': self.descriptionInput.toPlainText().strip()
        }
        self.accept()

    def get_data(self):
        return self.result_data


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = FamilyInfoDialog(edit_mode=False)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_data()
        if data:
            print("Dữ liệu nhập:")
            for key, value in data.items():
                print(f"  {key}: {value}")
    sys.exit()