# -*- coding: utf-8 -*-


import os
import sys
import shutil
from datetime import datetime

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QApplication, QMessageBox, QFileDialog

from bao_cao_su_co import Ui_MainWindow


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads_su_co")
MAX_MOTA_LEN = 500
MAX_IMAGE_MB = 5
ALLOWED_IMAGE_EXT = (".jpg", ".jpeg", ".png")

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

        self.current_image_path = None
        self._sidebar_expanded = True

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        self.report_count = self._get_report_count_from_database()

        self._setup_tree_combo()
        self._setup_char_counter()
        self._setup_upload_dropzone()
        self._setup_nav_buttons()
        self._setup_form_buttons()
        self._setup_menu_toggle()

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


    def _setup_upload_dropzone(self):
        self.btnChooseImage.clicked.connect(self.choose_image)

        self.uploadDropzone.setAcceptDrops(True)
        self.uploadDropzone.installEventFilter(self)

        self._default_upload_icon = self.uploadIcon.text()
        self._default_upload_hint = self.uploadHint.text()

    def eventFilter(self, obj, event):
        if obj is self.uploadDropzone:
            if event.type() == QtCore.QEvent.Type.DragEnter:
                if event.mimeData().hasUrls():
                    event.acceptProposedAction()
                    return True
            elif event.type() == QtCore.QEvent.Type.Drop:
                urls = event.mimeData().urls()
                if urls:
                    self._apply_image(urls[0].toLocalFile())
                return True
        return super().eventFilter(obj, event)

    def choose_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh minh họa",
            "",
            "Hình ảnh (*.jpg *.jpeg *.png)"
        )
        if path:
            self._apply_image(path)

    def _apply_image(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in ALLOWED_IMAGE_EXT:
            QMessageBox.warning(self, "Định dạng không hợp lệ",
                                 "Chỉ chấp nhận ảnh định dạng JPG hoặc PNG.")
            return

        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > MAX_IMAGE_MB:
            QMessageBox.warning(self, "Ảnh quá lớn",
                                 f"Dung lượng ảnh tối đa là {MAX_IMAGE_MB}MB "
                                 f"(ảnh đã chọn: {size_mb:.1f}MB).")
            return

        pixmap = QtGui.QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "Lỗi", "Không thể đọc được file ảnh này.")
            return

        self.current_image_path = path
        scaled = pixmap.scaled(80, 80, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                                QtCore.Qt.TransformationMode.SmoothTransformation)
        self.uploadIcon.setPixmap(scaled)
        self.uploadHint.setText(os.path.basename(path))
        self.btnChooseImage.setText("Đổi ảnh khác")

    def _clear_image(self):
        self.current_image_path = None
        self.uploadIcon.setPixmap(QtGui.QPixmap())
        self.uploadIcon.setText(self._default_upload_icon)
        self.uploadHint.setText(self._default_upload_hint)
        self.btnChooseImage.setText("Chọn ảnh")

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
        saved_image = self._persist_image(ma_bc) if self.current_image_path else None

        record = {
            "ma_bao_cao": ma_bc,
            "thoi_gian_gui": self.fieldThoiGianGui.dateTime().toString("dd/MM/yyyy HH:mm"),
            "cay": self.fieldCay.currentText(),
            "mo_ta": self.fieldMoTa.toPlainText().strip(),
            "muc_do_nguy_hiem": self.fieldMucDoNguyHiem.currentText(),
            "trang_thai": self.fieldTrangThai.currentText(),
            "hinh_anh": saved_image,
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
            or self.current_image_path is not None
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
        self._clear_image()
        for w in (self.fieldCay, self.fieldMoTa, self.fieldMucDoNguyHiem):
            self._reset_field_style(w)
        self.statusBar().showMessage("Đã làm mới biểu mẫu.", 3000)


    def _generate_ma_bc(self):
        return f"BC-{self.report_count + 1:04d}"

    def _persist_image(self, ma_bc):
        ext = os.path.splitext(self.current_image_path)[1].lower()
        dest = os.path.join(UPLOAD_DIR, f"{ma_bc}{ext}")
        try:
            shutil.copy(self.current_image_path, dest)
            return dest
        except OSError:
            return self.current_image_path
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

    def _setup_menu_toggle(self):
        self.btnMenuToggle.clicked.connect(self._toggle_sidebar)

    def _toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        if self._sidebar_expanded:
            self.sidebarFrame.setMinimumSize(QtCore.QSize(230, 0))
            self.sidebarFrame.setMaximumSize(QtCore.QSize(230, 16777215))
            self.sidebarTitle.show()
            for name, (btn, page_title) in self.nav_buttons.items():
                icon = btn.text().split(" ")[0]
                btn.setText(f"{icon}   {page_title}")
        else:
            self.sidebarFrame.setMinimumSize(QtCore.QSize(60, 0))
            self.sidebarFrame.setMaximumSize(QtCore.QSize(60, 16777215))
            self.sidebarTitle.hide()
            for name, (btn, page_title) in self.nav_buttons.items():
                icon = btn.text().split(" ")[0]
                btn.setText(icon)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
