import sys

import pyodbc

import config
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QDate
from yeu_cau_bao_tri import Ui_MainWindow

def ket_noi_co_so_du_lieu():
    try:
        chuoi_ket_noi = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={config.DB_SERVER};"
            f"DATABASE={config.DB_NAME};"
            f"Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(chuoi_ket_noi)
        return conn
    except pyodbc.Error as e:
        print(f"Lỗi kết nối SQL Server: {e}")
        return None


class YeuCauBaoTriEx(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.setup_defaults()

        self.connect_signals()

    def setup_defaults(self):
        # Đặt ngày tạo mặc định là ngày hôm nay
        self.ui.fieldNgayTao.setDate(QDate.currentDate())

    def connect_signals(self):
        self.ui.btnCancel.clicked.connect(self.handle_cancel)
        self.ui.btnSave.clicked.connect(self.handle_save)
        self.ui.btnMenuToggle.clicked.connect(self.handle_toggle_menu)

        self.ui.fieldNoiDungBaoTri.textChanged.connect(self.handle_char_counter)

    def handle_char_counter(self):
        """Hàm đếm và giới hạn số ký tự trong ô nội dung bảo trì"""
        text = self.ui.fieldNoiDungBaoTri.toPlainText()
        max_length = 500
        current_length = len(text)

        if current_length > max_length:
            text = text[:max_length]
            self.ui.fieldNoiDungBaoTri.setPlainText(text)

            cursor = self.ui.fieldNoiDungBaoTri.textCursor()
            cursor.setPosition(max_length)
            self.ui.fieldNoiDungBaoTri.setTextCursor(cursor)
            current_length = max_length

        self.ui.charCounter1.setText(f"{current_length}/{max_length}")

    def handle_toggle_menu(self):
        """Hàm ẩn/hiện Sidebar khi nhấn nút Toggle"""
        is_visible = self.ui.sidebarFrame.isVisible()
        self.ui.sidebarFrame.setVisible(not is_visible)

    def handle_cancel(self):
        """Hàm xử lý khi nhấn nút Hủy bỏ"""
        reply = QMessageBox.question(
            self,
            'Xác nhận',
            'Bạn có chắc chắn muốn hủy bỏ? Các thay đổi chưa lưu sẽ bị mất.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()

    def handle_save(self):
        """Hàm xử lý khi nhấn nút Lưu"""
        ngay_tao = self.ui.fieldNgayTao.date().toString("dd/MM/yyyy")
        cay = self.ui.fieldCay.currentText()
        noi_dung = self.ui.fieldNoiDungBaoTri.toPlainText().strip()
        muc_do = self.ui.fieldMucDoUuTien.currentText()
        trang_thai = self.ui.fieldTrangThai.currentText()
        nhan_vien = self.ui.fieldNhanVienPhuTrach.currentText()

        # Kiểm tra tính hợp lệ của nhập liệu
        if cay == "Chọn cây" or not noi_dung or muc_do == "Chọn mức độ ưu tiên" or nhan_vien == "Chọn nhân viên":
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập đầy đủ các thông tin bắt buộc (*)")
            return

        # ----------------------------------------------------------------
        # Gắn code kết nối database ở đây
        # ----------------------------------------------------------------

        # Hiển thị thông báo thành công
        msg = f"Đã lưu yêu cầu bảo trì thành công!\n\nChi tiết:\n- Cây: {cay}\n- Mức độ: {muc_do}\n- Nhân viên: {nhan_vien}\n- Trạng thái: {trang_thai}"
        QMessageBox.information(self, "Thành công", msg)



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YeuCauBaoTriEx()
    window.show()
    sys.exit(app.exec())