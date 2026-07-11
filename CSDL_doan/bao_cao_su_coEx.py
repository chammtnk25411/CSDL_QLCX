import sys
from datetime import datetime

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox

from bao_cao_su_co import Ui_MainWindow


MAX_MOTA_LEN = 500

# Danh sách cây mẫu (mã, tên) để test
SAMPLE_TREES = [
    ("C045", "Sao đen"),
    ("C012", "Bàng"),
    ("C078", "Phượng vĩ"),
    ("C023", "Bằng lăng"),
    ("C099", "Xà cừ"),
    ("C061", "Me tây"),
]

NAV_PAGES = [
    ("navTrangChu", "Trang chủ"),
    ("navQuanLyCay", "Quản lý cây"),
    ("navLoaiThucVat", "Loài thực vật"),
    ("navHoThucVat", "Họ thực vật"),
    ("navKhuTrungBay", "Khu trưng bày"),
    ("navNhanVien", "Nhân viên"),
    ("navPhieuKhaoSat", "Phiếu khảo sát"),
    ("navPhieuChamSoc", "Phiếu chăm sóc"),
    ("navYeuCauBaoTri", "Yêu cầu bảo trì"),
    ("navActive", "Báo cáo sự cố"),
]


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.report_count = self._get_report_count_from_database()

        self._setup_tree_combo()
        self._setup_char_counter()
        self._setup_nav_buttons()
        self._setup_form_buttons()

        self.statusBar().showMessage("Sẵn sàng.")


    def _setup_tree_combo(self):
        for ma, ten in SAMPLE_TREES[1:]:
            self.fieldCay.addItem(f"{ten} ({ma})")
        self.fieldCay.setCurrentIndex(0)


    def _setup_char_counter(self):
        self.fieldMoTa.textChanged.connect(self._on_mota_changed)
        self._on_mota_changed()

    def _on_mota_changed(self):
        text = self.fieldMoTa.toPlainText()
        if len(text) > MAX_MOTA_LEN:
            cursor = self.fieldMoTa.textCursor()
            pos = cursor.position()
            trimmed = text[:MAX_MOTA_LEN]
            self.fieldMoTa.blockSignals(True)
            self.fieldMoTa.setPlainText(trimmed)
            cursor.setPosition(min(pos, len(trimmed)))
            self.fieldMoTa.setTextCursor(cursor)
            self.fieldMoTa.blockSignals(False)
            text = trimmed

        length = len(text)
        self.charCounter2.setText(f"{length}/{MAX_MOTA_LEN}")
        if length >= MAX_MOTA_LEN:
            self.charCounter2.setStyleSheet("color: #e53935; font-size: 11px; font-weight: bold;")
        elif length >= int(MAX_MOTA_LEN * 0.9):
            self.charCounter2.setStyleSheet("color: #e08a1f; font-size: 11px;")
        else:
            self.charCounter2.setStyleSheet("color: #9aa39d; font-size: 11px;")


    def _setup_form_buttons(self):
        self.btnSave.clicked.connect(self.save_report)
        self.btnCancel.clicked.connect(self.cancel_form)

    def _reset_field_style(self, widget):
        widget.setStyleSheet("")

    def _mark_invalid(self, widget):
        widget.setStyleSheet("border: 1px solid #e53935; border-radius: 6px;")

    def validate_form(self):
        is_valid = True

        self._reset_field_style(self.fieldCay)
        self._reset_field_style(self.fieldMoTa)
        self._reset_field_style(self.fieldMucDoNguyHiem)

        if self.fieldCay.currentIndex() <= 0:
            self._mark_invalid(self.fieldCay)
            is_valid = False

        if not self.fieldMoTa.toPlainText().strip():
            self._mark_invalid(self.fieldMoTa)
            is_valid = False

        if self.fieldMucDoNguyHiem.currentIndex() <= 0:
            self._mark_invalid(self.fieldMucDoNguyHiem)
            is_valid = False

        if not is_valid:
            QMessageBox.warning(
                self, "Thiếu thông tin",
                "Vui lòng nhập đầy đủ các trường bắt buộc (đánh dấu *)."
            )
        return is_valid

    def save_report(self):
        if not self.validate_form():
            return

        ma_bc = self._generate_ma_bc()

        record = {
            "ma_bao_cao": ma_bc,
            "thoi_gian_gui": self.fieldThoiGianGui.dateTime().toString("dd/MM/yyyy HH:mm"),
            "cay": self.fieldCay.currentText(),
            "mo_ta": self.fieldMoTa.toPlainText().strip(),
            "muc_do_nguy_hiem": self.fieldMucDoNguyHiem.currentText(),
            "trang_thai": self.fieldTrangThai.currentText(),
            "ngay_tao": datetime.now().isoformat(timespec="seconds"),
        }

        ok = self._save_to_database(record)
        if not ok:
            return

        self.report_count += 1
        self.fieldMABC.setText(ma_bc)
        self.statusBar().showMessage(f"Đã lưu báo cáo {ma_bc}.", 5000)
        QMessageBox.information(self, "Thành công",
                                 f"Đã lưu báo cáo sự cố với mã: {ma_bc}")
        self.reset_form(confirm=False)

    def cancel_form(self):
        has_data = (
            self.fieldMoTa.toPlainText().strip()
            or self.fieldCay.currentIndex() > 0
            or self.fieldMucDoNguyHiem.currentIndex() > 0
        )
        self.reset_form(confirm=has_data)

    def reset_form(self, confirm=True):
        if confirm:
            reply = QMessageBox.question(
                self, "Xác nhận hủy bỏ",
                "Dữ liệu đang nhập sẽ không được lưu. Bạn có chắc muốn hủy bỏ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self.fieldMABC.clear()
        self.fieldThoiGianGui.setDateTime(QtCore.QDateTime.currentDateTime())
        self.fieldCay.setCurrentIndex(0)
        self.fieldMoTa.clear()
        self.fieldMucDoNguyHiem.setCurrentIndex(0)
        self.fieldTrangThai.setCurrentIndex(0)
        for w in (self.fieldCay, self.fieldMoTa, self.fieldMucDoNguyHiem):
            self._reset_field_style(w)
        self.statusBar().showMessage("Đã làm mới biểu mẫu.", 3000)


    def _generate_ma_bc(self):
        return f"BC-{self.report_count + 1:04d}"

    # ----------------------------------------------------------------
    # Gắn code kết nối database ở đây
    # ----------------------------------------------------------------
    def _get_report_count_from_database(self):
        return 0

    def _save_to_database(self, record: dict) -> bool:
        print("[Chưa kết nối SQL] Dữ liệu sẽ lưu:", record)
        return True

    def _setup_nav_buttons(self):
        self.nav_buttons = {}
        for name, page_title in NAV_PAGES:
            btn = getattr(self, name, None)
            if btn is None:
                continue
            self.nav_buttons[name] = (btn, page_title)
            btn.clicked.connect(lambda checked=False, n=name: self._on_nav_clicked(n))

    def _on_nav_clicked(self, clicked_name):
        for name, (btn, page_title) in self.nav_buttons.items():
            if name == clicked_name:
                btn.setObjectName("navActive")
                btn.setProperty("class", "")
            else:
                btn.setObjectName(name if name != "navActive" else "navReport")
                btn.setProperty("class", "navBtn")
            btn.style().unpolish(btn)
            btn.style().polish(btn)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()