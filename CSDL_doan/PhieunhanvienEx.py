# PhieunhanvienEx.py
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QDialog, QMessageBox
)
from PyQt6.QtCore import QDate
from PyQt6.uic import loadUi
import pyodbc
import config
from datetime import datetime


def get_db_connection():
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


class StaffInfoDialog(QDialog):
    def __init__(self, parent=None, edit_mode=False, staff_data=None, existing_ids=None):
        super().__init__(parent)

        self.edit_mode = edit_mode
        self.staff_data = staff_data
        self.existing_ids = existing_ids or []
        self.result_data = None

        # Load UI
        ui_path = os.path.join(os.path.dirname(__file__), 'Phieunhanvien.ui')
        try:
            loadUi(ui_path, self)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể load UI: {str(e)}")
            sys.exit(1)

        # Kết nối sự kiện
        self.saveButton.clicked.connect(self.save_data)
        self.cancelButton.clicked.connect(self.reject)

        # Thiết lập ngày sinh
        self.dobInput.setCalendarPopup(True)
        self.dobInput.setDisplayFormat("dd/MM/yyyy")
        self.dobInput.setMinimumDate(QDate(1940, 1, 1))
        self.dobInput.setMaximumDate(QDate.currentDate())
        self.dobInput.setDate(QDate(1990, 1, 1))

        if edit_mode and staff_data:
            self.load_data(staff_data)
        else:
            self.generate_auto_id()

    def generate_auto_id(self):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(MANV) FROM NHAN_VIEN")
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                num = int(row[0].replace('NV', '')) + 1
                new_id = f"NV{num:03d}"
            else:
                new_id = "NV001"
            self.idInput.setText(new_id)
        except:
            if not self.existing_ids:
                new_id = "NV001"
            else:
                max_num = 0
                for id_str in self.existing_ids:
                    try:
                        num = int(id_str.replace('NV', ''))
                        if num > max_num:
                            max_num = num
                    except:
                        continue
                new_id = f"NV{max_num + 1:03d}"
            self.idInput.setText(new_id)

    def load_data(self, data):
        if data:
            self.idInput.setText(data.get('MANV', ''))
            self.nameInput.setText(data.get('HOTEN', ''))

            # Load ngày sinh vào QDateEdit
            ngaysinh = data.get('NGAYSINH', '')
            if ngaysinh:
                try:
                    if isinstance(ngaysinh, str) and '/' in ngaysinh:
                        qdate = QDate.fromString(ngaysinh, "dd/MM/yyyy")
                    else:
                        qdate = QDate.fromString(str(ngaysinh), "yyyy-MM-dd")
                    if qdate.isValid():
                        self.dobInput.setDate(qdate)
                except:
                    pass

            gender = data.get('GIOITINH', 'Nam')
            index = self.genderCombo.findText(gender)
            if index >= 0:
                self.genderCombo.setCurrentIndex(index)

            self.phoneInput.setText(data.get('DIENTHOAI', ''))
            self.emailInput.setText(data.get('EMAIL', ''))

            chucvu = data.get('CHUCVU', 'Nhân viên')
            index = self.positionCombo.findText(chucvu)
            if index >= 0:
                self.positionCombo.setCurrentIndex(index)

    def validate_data(self):
        if not self.nameInput.text().strip():
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập họ và tên!")
            self.nameInput.setFocus()
            return False
        return True

    def save_data(self):
        if not self.validate_data():
            return

        self.result_data = {
            'MANV': self.idInput.text(),
            'HOTEN': self.nameInput.text().strip(),
            'NGAYSINH': self.dobInput.date().toString("yyyy-MM-dd") if self.dobInput.date().isValid() else None,
            'GIOITINH': self.genderCombo.currentText(),
            'DIENTHOAI': self.phoneInput.text().strip(),
            'EMAIL': self.emailInput.text().strip(),
            'CHUCVU': self.positionCombo.currentText()
        }
        self.accept()

    def get_data(self):
        return self.result_data


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dialog = StaffInfoDialog(edit_mode=False)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_data()
        if data:
            print("Dữ liệu nhập:")
            for key, value in data.items():
                print(f"  {key}: {value}")
    sys.exit()