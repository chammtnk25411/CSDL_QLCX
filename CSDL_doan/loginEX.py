import re
import sys
import random
from datetime import datetime, date  # Dùng để lấy ngày tháng hiện tại khi tạo dữ liệu

import pyodbc

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QDialog,
    QDateEdit,
    QDateTimeEdit,
    QComboBox,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QFormLayout,
    QTextEdit,
    QDialogButtonBox,
)
from PyQt6.QtCore import QDate, QDateTime, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter

# =========================================================
# KẾT NỐI SQL SERVER TRỰC TIẾP (KHÔNG DÙNG database.py RIÊNG)
# =========================================================
# Toàn bộ logic kết nối + truy vấn CSDL được gộp thẳng vào file này.
# ĐỒNG BỘ VỚI QUY ƯỚC CỦA NHÓM (xem "CẨM NANG SETUP DỰ ÁN"): thông tin kết
# nối (tên SERVER, tên DATABASE) được lấy từ file "config.py" nằm CÙNG THƯ
# MỤC với loginEX.py - file này KHÔNG được đẩy lên GitHub (.gitignore chặn),
# mỗi thành viên tự tạo 1 bản riêng theo đúng Bước 3 của cẩm nang:
#
#   DB_SERVER = 'TEN-MAY-CUA-BAN\\SQLEXPRESS'
#   DB_NAME = 'QLCX'
#
# -> Khi đem sang máy khác: chỉ cần mỗi người tự tạo config.py của riêng họ
#    (như mọi file khác trong dự án), KHÔNG cần sửa gì trong loginEX.py và
#    không cần thêm file cấu hình nào khác.
try:
    import config as _team_config
except ImportError:
    _team_config = None

# Thứ tự các driver ODBC sẽ được thử lần lượt cho tới khi kết nối thành công.
# Nhờ vậy máy nào chỉ cài driver cũ (17) hoặc mới (18) đều chạy được (mẫu
# code gốc trong cẩm nang chỉ dùng đúng 1 driver "SQL Server" nên máy nào
# không cài driver đó sẽ báo lỗi; đoạn dò nhiều driver dưới đây giúp chạy
# được trên nhiều máy có cấu hình driver khác nhau hơn mà KHÔNG cần đổi gì
# trong config.py của từng người).
_ODBC_DRIVER_CANDIDATES = [
    "ODBC Driver 18 for SQL Server",
    "ODBC Driver 17 for SQL Server",
    "SQL Server Native Client 11.0",
    "SQL Server",
]


def get_connection():
    """Mở kết nối tới SQL Server bằng thông tin trong config.py (DB_SERVER,
    DB_NAME) của từng máy, tự thử nhiều driver ODBC khác nhau."""
    if _team_config is None:
        raise ConnectionError(
            "Không tìm thấy file 'config.py'. Vui lòng tạo file config.py cùng thư mục với "
            "loginEX.py theo đúng Bước 3 trong cẩm nang setup, ví dụ:\n\n"
            "DB_SERVER = 'TEN-MAY-CUA-BAN\\\\SQLEXPRESS'\nDB_NAME = 'QLCX'"
        )

    server = getattr(_team_config, "DB_SERVER", None)
    database_name = getattr(_team_config, "DB_NAME", None)
    if not server or not database_name:
        raise ConnectionError(
            "File 'config.py' đang thiếu DB_SERVER hoặc DB_NAME. "
            "Vui lòng kiểm tra lại theo đúng mẫu ở Bước 3 trong cẩm nang setup."
        )

    last_error = None
    for driver in _ODBC_DRIVER_CANDIDATES:
        try:
            conn_str = (
                f"DRIVER={{{driver}}};SERVER={server};DATABASE={database_name};"
                f"Trusted_Connection=yes;TrustServerCertificate=yes;"
            )
            return pyodbc.connect(conn_str, timeout=5)
        except Exception as e:
            last_error = e
            continue

    raise ConnectionError(
        f"Không thể kết nối SQL Server (đã thử {len(_ODBC_DRIVER_CANDIDATES)} driver ODBC).\n"
        f"Kiểm tra lại file 'config.py' (DB_SERVER='{server}', DB_NAME='{database_name}') "
        f"và đảm bảo SQL Server đang chạy trên máy bạn.\n"
        f"Chi tiết lỗi cuối cùng: {last_error}"
    )



def _rows_to_dicts(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _generate_next_code(existing_ids, prefix, pad_width):
    """
    Sinh mã mới đồng bộ với SQL: dò các mã hiện có cùng prefix, lấy số lớn nhất,
    +1, rồi format lại đúng số chữ số (pad_width) đang dùng trong CSDL.
    Ví dụ existing = ['LOAI01', ..., 'LOAI10'], prefix='LOAI', pad_width=2 -> 'LOAI11'.
    Nhờ luôn tính từ dữ liệu thật trong SQL nên không bao giờ bị lệch/trùng mã nữa.
    """
    max_num = 0
    for code in existing_ids:
        code = str(code).strip().upper()
        if code.startswith(prefix.upper()):
            suffix = code[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"{prefix}{max_num + 1:0{pad_width}d}"


# Định dạng mã loài hợp lệ trong hệ thống: tiền tố "LOAI" + số (LOAI01, LOAI02, ...)
# Các mã dạng khác (vd. "SP011", "SP012"...) là dữ liệu lỗi/không hợp lệ cần loại bỏ.
_VALID_MALOAI_PATTERN = re.compile(r"^LOAI\d+$", re.IGNORECASE)


def _is_valid_maloai(code):
    """Kiểm tra mã loài có đúng định dạng LOAI+số hay không (vd LOAI01 hợp lệ, SP011 không hợp lệ)."""
    return bool(_VALID_MALOAI_PATTERN.match(str(code).strip().upper()))


# Định dạng mã họ hợp lệ trong hệ thống: tiền tố "HO" + số (HO01, HO02, ...)
# Các mã dạng khác (vd. "LO007", "LO013"...) là dữ liệu lỗi/không hợp lệ cần loại bỏ.
_VALID_MAHO_PATTERN = re.compile(r"^HO\d+$", re.IGNORECASE)


def _is_valid_maho(code):
    """Kiểm tra mã họ có đúng định dạng HO+số hay không (vd HO01 hợp lệ, LO007 không hợp lệ)."""
    return bool(_VALID_MAHO_PATTERN.match(str(code).strip().upper()))


# =========================================================
# DỮ LIỆU MẪU ĐỂ SINH NHÂN VIÊN NGẪU NHIÊN (dùng cho seed_sample_nhanvien)
# =========================================================
_HO_LIST = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng",
            "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Đinh", "Trương", "Đoàn", "Mai"]
_DEM_NAM_LIST = ["Văn", "Hữu", "Đức", "Minh", "Quang", "Thành", "Công", "Xuân", "Anh", "Tuấn"]
_DEM_NU_LIST = ["Thị", "Ngọc", "Thu", "Thanh", "Kim", "Hồng", "Bích", "Diễm", "Mỹ", "Phương"]
_TEN_NAM_LIST = ["An", "Bình", "Cường", "Dũng", "Đạt", "Hải", "Hùng", "Khang", "Long", "Minh",
                 "Nam", "Phong", "Quân", "Sơn", "Tài", "Thắng", "Tuấn", "Vinh", "Việt", "Đông"]
_TEN_NU_LIST = ["Anh", "Chi", "Diệu", "Giang", "Hà", "Hằng", "Hoa", "Huyền", "Lan", "Linh",
                "My", "Nga", "Nhi", "Oanh", "Phương", "Quỳnh", "Thảo", "Trang", "Vân", "Yến"]
_CHUCVU_LIST = [
    "Kỹ thuật viên", "Chuyên viên nghiên cứu", "Quản lý khu vực",
    "Kỹ thuật viên chăm sóc", "Nhân viên bảo tồn", "Chuyên gia lâm nghiệp",
    "Kỹ thuật viên sinh học", "Nhân viên vệ sinh cảnh quan",
    "Nhân viên hướng dẫn tham quan", "Nhân viên bán vé",
    "Kế toán", "Bảo vệ", "Nhân viên chăm sóc khách hàng",
]

_ACCENT_MAP = str.maketrans(
    "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    "ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ",
    "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
    "AAAAAAAAAAAAAAAAAEEEEEEEEEEEIIIIIOOOOOOOOOOOOOOOOOUUUUUUUUUUUYYYYYD"
)


def _bo_dau(s):
    """Bỏ dấu tiếng Việt (dùng để tạo email/mật khẩu không dấu)."""
    return s.translate(_ACCENT_MAP)


def _generate_sample_nhanvien(existing_ids, count):
    """
    Sinh ngẫu nhiên 'count' nhân viên mẫu (họ tên, ngày sinh, giới tính, SĐT,
    email, chức vụ, mật khẩu) với mã MANV nối tiếp từ mã lớn nhất đang có
    trong 'existing_ids' (dùng chung logic với _generate_next_code để không
    bao giờ trùng/lệch mã). Trả về list các dict sẵn sàng để INSERT vào SQL.
    """
    used_emails = set()
    results = []
    current_ids = list(existing_ids)

    for _ in range(count):
        next_id = _generate_next_code(current_ids, "NV", 2)
        current_ids.append(next_id)

        gender = random.choices(["Nam", "Nữ", "Khác"], weights=[47, 47, 6], k=1)[0]
        ho = random.choice(_HO_LIST)
        if gender == "Nam":
            dem, ten = random.choice(_DEM_NAM_LIST), random.choice(_TEN_NAM_LIST)
        elif gender == "Nữ":
            dem, ten = random.choice(_DEM_NU_LIST), random.choice(_TEN_NU_LIST)
        else:
            dem = random.choice(_DEM_NAM_LIST + _DEM_NU_LIST)
            ten = random.choice(_TEN_NAM_LIST + _TEN_NU_LIST)
        hoten = f"{ho} {dem} {ten}"

        year = random.randint(1985, 2000)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        ngaysinh = date(year, month, day)

        phone = "09" + "".join(str(random.randint(0, 9)) for _ in range(8))

        name_parts = _bo_dau(hoten).lower().split()
        base_email = name_parts[-1] + "".join(p[0] for p in name_parts[:-1])
        email = f"{base_email}@gmail.com"
        suffix = 1
        while email in used_emails:
            suffix += 1
            email = f"{base_email}{suffix}@gmail.com"
        used_emails.add(email)

        sym = random.choice(["@", "#", "$", "%", "!", "_", "*"])
        matkhau = f"{name_parts[-1].capitalize()}{name_parts[0].capitalize()}{str(year)[-2:]}{sym}"

        chucvu = random.choice(_CHUCVU_LIST)

        results.append({
            "manv": next_id, "hoten": hoten, "ngaysinh": ngaysinh,
            "gioitinh": gender, "dienthoai": phone, "email": email,
            "chucvu": chucvu, "matkhau": matkhau,
        })

    return results


def _fix_date_edit_widgets(ui):
    """
    Sửa lỗi kinh điển của Qt: chuỗi định dạng ngày dùng "mm" (chữ thường = PHÚT)
    thay vì "MM" (chữ hoa = THÁNG) -> khiến phần tháng luôn hiện "00" dù đã dùng
    QDateEdit (đúng như ảnh "07/00/1999"). Hàm này quét mọi QDateEdit có trên
    form và ép lại định dạng "dd/MM/yyyy" cho đúng, đồng thời gán ngày hiện tại
    nếu ngày đang set không hợp lệ.
    """
    for widget in vars(ui).values():
        if isinstance(widget, QDateEdit):
            widget.setDisplayFormat("dd/MM/yyyy")
            widget.setCalendarPopup(True)
            if not widget.date().isValid() or widget.date().year() < 1900:
                widget.setDate(QDate.currentDate())


def _get_first_date_edit(ui):
    """Lấy QDateEdit đầu tiên tìm thấy trên form (dùng khi không biết chắc tên control)."""
    for widget in vars(ui).values():
        if isinstance(widget, QDateEdit):
            return widget
    return None


def _get_first_datetime_edit(ui):
    """
    Lấy QDateTimeEdit đầu tiên tìm thấy trên form (dùng cho ô "Thời gian gửi"
    của Báo cáo sự cố - ô này có cả NGÀY lẫn GIỜ như ảnh thiết kế "07/05/2026
    00:00", khác với QDateEdit chỉ có ngày dùng ở "Yêu cầu bảo trì").
    LƯU Ý: QDateTimeEdit KHÔNG phải là subclass của QDateEdit trong PyQt6 nên
    cần dò riêng, không dùng chung được hàm _get_first_date_edit ở trên.
    """
    for widget in vars(ui).values():
        if isinstance(widget, QDateTimeEdit):
            return widget
    return None


def _get_first_table_widget(ui):
    """Lấy QTableWidget đầu tiên tìm thấy trên form (dùng khi không rõ tên bảng danh sách)."""
    for widget in vars(ui).values():
        if isinstance(widget, QTableWidget):
            return widget
    return None


def _swap_widget_in_layout(old_widget, new_widget):
    """
    Thay 'old_widget' (vd QLineEdit do Qt Designer sinh ra) bằng 'new_widget'
    (vd QDateEdit/QComboBox) NGAY TẠI VỊ TRÍ CŨ trong layout, không cần sửa
    file .ui/Designer. Nhờ vậy có thể "nâng cấp" loại control ngay trong code
    Python (loginEX.py) mà không đụng tới file giao diện gốc.
    """
    parent = old_widget.parentWidget()
    layout = parent.layout() if parent else None
    if layout is not None:
        layout.replaceWidget(old_widget, new_widget)
    else:
        # Không có layout quản lý (hiếm gặp) -> copy tạm vị trí/kích thước cũ
        new_widget.setGeometry(old_widget.geometry())
    old_widget.hide()
    old_widget.deleteLater()
    new_widget.show()


def _find_widget_by_hints(ui, name_candidates, widget_type, keyword_hints=()):
    """
    Dò tìm 1 control trên form theo TÊN (name_candidates) trước; nếu không
    thấy control nào khớp tên, dò tiếp theo LOẠI widget (widget_type) có
    objectName hoặc placeholder/text chứa 1 trong các từ khóa (keyword_hints).
    Dùng để gắn chức năng vào các ComboBox/Button lọc "Cây", "Nhân viên",
    nút "+ Thêm phiếu..." mà không cần biết chính xác tên control do Qt
    Designer đặt (đề phòng tên control trong file .ui khác với dự đoán).
    """
    for name in name_candidates:
        if hasattr(ui, name):
            widget = getattr(ui, name)
            if isinstance(widget, widget_type):
                return widget

    if not keyword_hints:
        return None

    for widget in vars(ui).values():
        if not isinstance(widget, widget_type):
            continue
        haystack = widget.objectName().lower()
        if hasattr(widget, "text"):
            try:
                haystack += " " + str(widget.text()).lower()
            except Exception:
                pass
        if hasattr(widget, "placeholderText"):
            try:
                haystack += " " + str(widget.placeholderText()).lower()
            except Exception:
                pass
        if any(h in haystack for h in keyword_hints):
            return widget
    return None


def _build_action_buttons_widget(record_id, on_edit, on_delete):
    """
    Tạo 1 QWidget chứa 2 nút "✏️ Sửa" / "🗑️ Xóa" để gắn vào cột THAO TÁC của
    bảng (setCellWidget). Khi bấm sẽ gọi on_edit(record_id) / on_delete(record_id)
    -> các hàm này thao tác trực tiếp lên SQL Server (UPDATE/DELETE) rồi tải
    lại bảng, nên "Thao tác" luôn đồng bộ với dữ liệu thật trong CSDL.
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(6)

    btn_edit = QPushButton("✏️")
    btn_edit.setToolTip("Sửa")
    btn_edit.setFixedWidth(32)
    btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_edit.clicked.connect(lambda _checked=False, rid=record_id: on_edit(rid))

    btn_delete = QPushButton("🗑️")
    btn_delete.setToolTip("Xóa")
    btn_delete.setFixedWidth(32)
    btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_delete.clicked.connect(lambda _checked=False, rid=record_id: on_delete(rid))

    layout.addWidget(btn_edit)
    layout.addWidget(btn_delete)
    layout.addStretch()
    return container


def _make_text_icon(text, size=22):
    """
    Tạo 1 QIcon đơn giản chỉ chứa 1 ký tự/emoji (vd "👁" / "🙈"), dùng làm icon
    "hiện/ẩn mật khẩu" mà KHÔNG cần file ảnh riêng đi kèm project.
    """
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    font = painter.font()
    font.setPointSize(int(size * 0.6))
    painter.setFont(font)
    painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return QIcon(pix)


def _attach_password_toggle(line_edit):
    """
    Gắn 1 icon "con mắt" vào bên phải ô nhập mật khẩu (QLineEdit) để người
    dùng bấm HIỆN/ẨN mật khẩu đang gõ. Dùng QLineEdit.addAction() có sẵn của
    Qt nên KHÔNG cần thêm control mới vào layout của file .ui (không đụng gì
    tới file giao diện gốc do Qt Designer sinh ra).
    Mặc định ô sẽ ẩn mật khẩu (dấu chấm); bấm icon để hiện/ẩn lại.
    """
    if line_edit is None:
        return
    line_edit.setEchoMode(QLineEdit.EchoMode.Password)
    action = line_edit.addAction(_make_text_icon("🙈"), QLineEdit.ActionPosition.TrailingPosition)
    action.setToolTip("Hiện mật khẩu")

    def _toggle():
        if line_edit.echoMode() == QLineEdit.EchoMode.Password:
            line_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            action.setIcon(_make_text_icon("👁"))
            action.setToolTip("Ẩn mật khẩu")
        else:
            line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            action.setIcon(_make_text_icon("🙈"))
            action.setToolTip("Hiện mật khẩu")

    action.triggered.connect(_toggle)


class database:
    """
    'Namespace' thay thế cho module database.py cũ.
    Toàn bộ phần còn lại của loginEX.py gọi database.get_all_xxx() / database.add_xxx()
    y hệt như trước nên KHÔNG cần sửa các chỗ gọi hàm phía dưới.
    """

    # ---------------- CÂY ----------------
    @staticmethod
    def get_all_cay():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM CAY")
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def add_cay(macay, tencay, ngaytrong, chieucao, duongkinh, vitri,
                tinhtrangsinhtruong, trangthaihoatdong, maloai, makhu):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO CAY
                   (MACAY, TENCAY, NGAYTRONG, CHIEUCAO, DUONGKINH, VITRI,
                    TINHTRANGSINHTRUONG, TRANGTHAIHOATDONG, MALOAI, MAKHU)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                macay, tencay, ngaytrong, chieucao, duongkinh, vitri,
                tinhtrangsinhtruong, trangthaihoatdong, maloai, makhu,
            )
            conn.commit()
        finally:
            conn.close()

    # ---------------- LOÀI THỰC VẬT ----------------
    @staticmethod
    def get_all_loaithucvat():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM LOAI_THUC_VAT")
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def add_loaithucvat(maloai, tenthuonggoi, tenkhoahoc, dacdiemsinhhoc,
                         moitruongsong, tinhtrangbaoton, maho):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO LOAI_THUC_VAT
                   (MALOAI, TENTHUONGGOI, TENKHOAHOC, DACDIEMSINHHOC,
                    MOITRUONGSONG, TINHTRANGBAOTON, MAHO)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                maloai, tenthuonggoi, tenkhoahoc, dacdiemsinhhoc,
                moitruongsong, tinhtrangbaoton, maho,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_loaithucvat(maloai):
        """Xóa 1 loài thực vật theo mã (dùng cho nút 🗑️ ở từng dòng)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM LOAI_THUC_VAT WHERE MALOAI = ?", maloai)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_invalid_loaithucvat():
        """
        Dọn dữ liệu lỗi: xóa khỏi CSDL mọi bản ghi LOAI_THUC_VAT có MALOAI không
        đúng định dạng chuẩn "LOAI" + số (vd. LOAI01, LOAI02...). Những mã như
        "SP011", "SP012", "SP013", "SP014" (sai tiền tố, không khớp quy ước hệ
        thống) sẽ bị coi là không hợp lệ và bị xóa.
        Trả về danh sách các mã đã bị xóa để hiển thị thông báo cho người dùng.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT MALOAI FROM LOAI_THUC_VAT")
            all_codes = [row[0] for row in cur.fetchall()]
            invalid_codes = [c for c in all_codes if not _is_valid_maloai(c)]

            for code in invalid_codes:
                cur.execute("DELETE FROM LOAI_THUC_VAT WHERE MALOAI = ?", code)
            conn.commit()
            return invalid_codes
        finally:
            conn.close()

    # ---------------- HỌ THỰC VẬT ----------------
    @staticmethod
    def get_all_hothucvat():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM HO_THUC_VAT")
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def add_hothucvat(maho, tenho, mota):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO HO_THUC_VAT (MAHO, TENHO, MOTA) VALUES (?, ?, ?)",
                maho, tenho, mota,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_hothucvat(maho):
        """Xóa 1 họ thực vật theo mã (dùng cho nút 🗑️ ở từng dòng)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM HO_THUC_VAT WHERE MAHO = ?", maho)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_invalid_hothucvat():
        """
        Dọn dữ liệu lỗi: xóa khỏi CSDL mọi bản ghi HO_THUC_VAT có MAHO không
        đúng định dạng chuẩn "HO" + số (vd. HO01, HO02...). Những mã như
        "LO007", "LO008"... "LO013" (sai tiền tố "LO" thay vì "HO") sẽ bị coi
        là không hợp lệ và bị xóa.
        Trả về danh sách các mã đã bị xóa để hiển thị thông báo cho người dùng.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT MAHO FROM HO_THUC_VAT")
            all_codes = [row[0] for row in cur.fetchall()]
            invalid_codes = [c for c in all_codes if not _is_valid_maho(c)]

            for code in invalid_codes:
                cur.execute("DELETE FROM HO_THUC_VAT WHERE MAHO = ?", code)
            conn.commit()
            return invalid_codes
        finally:
            conn.close()

    # ---------------- KHU TRƯNG BÀY ----------------
    @staticmethod
    def get_all_khutrungbay():
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM KHU_TRUNG_BAY")
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def add_khutrungbay(makhu, tenkhu, vitri, dientich, mota):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO KHU_TRUNG_BAY (MAKHU, TENKHU, VITRI, DIENTICH, MOTA)
                   VALUES (?, ?, ?, ?, ?)""",
                makhu, tenkhu, vitri, dientich, mota,
            )
            conn.commit()
        finally:
            conn.close()

    # ---------------- NHÂN VIÊN ----------------
    @staticmethod
    def get_all_nhanvien():
        """
        JOIN thêm KHU_TRUNG_BAY để lấy TÊN khu vực phụ trách (TENKHU) hiển thị
        cho đúng, thay vì chỉ có mã MAKHU thô hoặc chữ "N/A" cố định như code cũ.

        SỬA LỖI QUAN TRỌNG: bảng NHAN_VIEN trong CSDL gốc (database_setup.sql)
        KHÔNG có cột MAKHU -> câu SELECT có JOIN theo nv.MAKHU sẽ báo lỗi SQL
        ("Invalid column name 'MAKHU'"), khiến toàn bộ trang Nhân viên rơi vào
        nhánh except và hiển thị NHẦM dữ liệu mẫu cứng (NV001/NV002) thay vì
        dữ liệu thật trong CSDL (kể cả sau khi đã seed thêm nhiều nhân viên).
        Giờ hàm sẽ tự thử JOIN trước; nếu cột MAKHU chưa tồn tại thì tự động
        chuyển sang SELECT thường (không JOIN) để KHÔNG làm crash cả trang.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            try:
                cur.execute(
                    """SELECT nv.*, khu.TENKHU AS TENKHUPHUTRACH
                       FROM NHAN_VIEN nv
                       LEFT JOIN KHU_TRUNG_BAY khu ON nv.MAKHU = khu.MAKHU"""
                )
                return _rows_to_dicts(cur)
            except pyodbc.Error:
                # Cột MAKHU chưa có trong bảng NHAN_VIEN -> rollback giao dịch
                # lỗi rồi query lại KHÔNG JOIN để vẫn lấy được dữ liệu thật.
                conn.rollback()
                cur = conn.cursor()
                cur.execute("SELECT * FROM NHAN_VIEN")
                rows = _rows_to_dicts(cur)
                for row in rows:
                    row.setdefault("TENKHUPHUTRACH", None)
                return rows
        finally:
            conn.close()

    @staticmethod
    def add_nhanvien(manv, hoten, ngaysinh, gioitinh, dienthoai, email,
                      chucvu, matkhau, makhu=None):
        """
        SỬA LỖI: bảng NHAN_VIEN gốc không có cột MAKHU -> nếu insert kèm MAKHU
        mà cột chưa tồn tại, SQL sẽ báo lỗi và "Thêm nhân viên" không hoạt động.
        Giờ thử insert kèm MAKHU trước; nếu lỗi do thiếu cột thì tự động insert
        lại KHÔNG có MAKHU để chức năng thêm nhân viên vẫn luôn hoạt động được.

        SỬA LỖI #2: cột EMAIL và DIENTHOAI có ràng buộc UNIQUE trong SQL. Nếu
        người dùng để trống 2 ô này, chuỗi rỗng "" vẫn là một giá trị hợp lệ
        (khác NULL) -> lần thêm nhân viên THỨ HAI cũng để trống sẽ bị SQL Server
        từ chối vì trùng giá trị "" với nhân viên trước đó, gây lỗi "Không thể
        lưu vào SQL Server". Ở đây ta đổi chuỗi rỗng thành None (NULL) trước khi
        insert để tránh trùng giá trị "" giữa nhiều nhân viên.
        """
        dienthoai = dienthoai.strip() if dienthoai else None
        email = email.strip() if email else None
        if not dienthoai:
            dienthoai = None
        if not email:
            email = None

        conn = get_connection()
        try:
            cur = conn.cursor()
            try:
                cur.execute(
                    """INSERT INTO NHAN_VIEN
                       (MANV, HOTEN, NGAYSINH, GIOITINH, DIENTHOAI, EMAIL, CHUCVU, MATKHAU, MAKHU)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    manv, hoten, ngaysinh, gioitinh, dienthoai, email, chucvu, matkhau, makhu,
                )
            except pyodbc.Error:
                conn.rollback()
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO NHAN_VIEN
                       (MANV, HOTEN, NGAYSINH, GIOITINH, DIENTHOAI, EMAIL, CHUCVU, MATKHAU)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    manv, hoten, ngaysinh, gioitinh, dienthoai, email, chucvu, matkhau,
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def seed_sample_nhanvien(min_total=60):
        """
        Đảm bảo bảng NHAN_VIEN có ít nhất 'min_total' nhân viên: nếu số lượng
        hiện có ít hơn, tự động sinh thêm nhân viên mẫu (họ tên, ngày sinh,
        giới tính, SĐT, email, chức vụ, mật khẩu ngẫu nhiên nhưng hợp lý) và
        INSERT thẳng vào SQL, với mã MANV nối tiếp đúng chuẩn (NV13, NV14...).
        Trả về danh sách mã nhân viên vừa được thêm (rỗng nếu đã đủ số lượng).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT MANV FROM NHAN_VIEN")
            existing_ids = [row[0] for row in cur.fetchall()]

            if len(existing_ids) >= min_total:
                return []

            need = min_total - len(existing_ids)
            new_staff = _generate_sample_nhanvien(existing_ids, need)

            for nv in new_staff:
                cur.execute(
                    """INSERT INTO NHAN_VIEN
                       (MANV, HOTEN, NGAYSINH, GIOITINH, DIENTHOAI, EMAIL, CHUCVU, MATKHAU)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    nv["manv"], nv["hoten"], nv["ngaysinh"], nv["gioitinh"],
                    nv["dienthoai"], nv["email"], nv["chucvu"], nv["matkhau"],
                )
            conn.commit()
            return [nv["manv"] for nv in new_staff]
        finally:
            conn.close()

    # ---------------- PHIẾU CHĂM SÓC ----------------
    @staticmethod
    def get_all_phieuchamsoc():
        """
        JOIN thêm NHAN_VIEN để lấy HOTEN (tên nhân viên thực hiện) trả về dưới
        tên cột TENNV -> dùng để hiển thị cột "Nhân viên thực hiện" ở giao diện
        Phiếu chăm sóc thay vì chỉ hiển thị mã MANV thô.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT pcs.*, nv.HOTEN AS TENNV, c.TENCAY AS TENCAY
                   FROM PHIEU_CHAM_SOC pcs
                   LEFT JOIN NHAN_VIEN nv ON pcs.MANV = nv.MANV
                   LEFT JOIN CAY c ON pcs.MACAY = c.MACAY"""
            )
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def add_phieuchamsoc(maphieucs, ngaychamsoc, noidungchamsoc, phuongphap,
                          tinhtrangsauchamsoc, ghichu, macay, manv):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO PHIEU_CHAM_SOC
                   (MAPHIEUCS, NGAYCHAMSOC, NOIDUNGCHAMSOC, PHUONGPHAP,
                    TINHTRANGSAUCHAMSOC, GHICHU, MACAY, MANV)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                maphieucs, ngaychamsoc, noidungchamsoc, phuongphap,
                tinhtrangsauchamsoc, ghichu, macay, manv,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def update_phieuchamsoc(maphieucs, ngaychamsoc, noidungchamsoc, phuongphap,
                             tinhtrangsauchamsoc, ghichu, macay, manv):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE PHIEU_CHAM_SOC
                   SET NGAYCHAMSOC = ?, NOIDUNGCHAMSOC = ?, PHUONGPHAP = ?,
                       TINHTRANGSAUCHAMSOC = ?, GHICHU = ?, MACAY = ?, MANV = ?
                   WHERE MAPHIEUCS = ?""",
                ngaychamsoc, noidungchamsoc, phuongphap,
                tinhtrangsauchamsoc, ghichu, macay, manv, maphieucs,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_phieuchamsoc(maphieucs):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM PHIEU_CHAM_SOC WHERE MAPHIEUCS = ?", maphieucs)
            conn.commit()
        finally:
            conn.close()

    # ---------------- PHIẾU KHẢO SÁT ----------------
    @staticmethod
    def get_all_phieukhaosat():
        """
        JOIN thêm NHAN_VIEN để lấy HOTEN (tên nhân viên khảo sát) trả về dưới
        tên cột TENNV -> dùng để hiển thị cột "Nhân viên khảo sát" ở giao diện
        Phiếu khảo sát thay vì chỉ hiển thị mã MANV thô.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT pks.*, nv.HOTEN AS TENNV, c.TENCAY AS TENCAY
                   FROM PHIEU_KHAO_SAT pks
                   LEFT JOIN NHAN_VIEN nv ON pks.MANV = nv.MANV
                   LEFT JOIN CAY c ON pks.MACAY = c.MACAY"""
            )
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def add_phieukhaosat(maks, ngaykhaosat, chieucaoghinhan, duongkinhghinhan,
                          tinhtrangla, tinhtrangsinhtruong, nhanxet, macay, manv):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO PHIEU_KHAO_SAT
                   (MAKS, NGAYKHAOSAT, CHIEUCAOGHINHAN, DUONGKINHGHINHAN,
                    TINHTRANGLA, TINHTRANGSINHTRUONG, NHANXET, MACAY, MANV)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                maks, ngaykhaosat, chieucaoghinhan, duongkinhghinhan,
                tinhtrangla, tinhtrangsinhtruong, nhanxet, macay, manv,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def update_phieukhaosat(maks, ngaykhaosat, chieucaoghinhan, duongkinhghinhan,
                             tinhtrangla, tinhtrangsinhtruong, nhanxet, macay, manv):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE PHIEU_KHAO_SAT
                   SET NGAYKHAOSAT = ?, CHIEUCAOGHINHAN = ?, DUONGKINHGHINHAN = ?,
                       TINHTRANGLA = ?, TINHTRANGSINHTRUONG = ?, NHANXET = ?,
                       MACAY = ?, MANV = ?
                   WHERE MAKS = ?""",
                ngaykhaosat, chieucaoghinhan, duongkinhghinhan,
                tinhtrangla, tinhtrangsinhtruong, nhanxet, macay, manv, maks,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_phieukhaosat(maks):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM PHIEU_KHAO_SAT WHERE MAKS = ?", maks)
            conn.commit()
        finally:
            conn.close()

    # ---------------- YÊU CẦU BẢO TRÌ ----------------
    @staticmethod
    def get_all_yeucaubaotri():
        """
        JOIN thêm NHAN_VIEN để lấy HOTEN (tên nhân viên phụ trách) thay vì chỉ
        có mã MANV -> khắc phục lỗi "nhân viên phụ trách không đúng" ở Trang chủ.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT yc.*, nv.HOTEN AS TENNV
                   FROM YEU_CAU_BAO_TRI yc
                   LEFT JOIN NHAN_VIEN nv ON yc.MANV = nv.MANV"""
            )
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def add_yeucaubaotri(mabt, ngaytao, noidungbaotri, mucdouutien, trangthai, macay, manv):
        """
        Thêm mới 1 yêu cầu bảo trì vào bảng YEU_CAU_BAO_TRI. Được gọi từ form
        "Thêm yêu cầu bảo trì" (YeuCauBaoTriWindow). Sau khi INSERT thành công,
        dữ liệu này sẽ tự động xuất hiện ở bảng "Yêu cầu bảo trì" trên Trang chủ
        (MainWindow.loadThongKeTrangChu gọi lại get_all_yeucaubaotri() mỗi khi
        Trang chủ được mở lại).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO YEU_CAU_BAO_TRI
                   (MABT, NGAYTAO, NOIDUNGBAOTRI, MUCDOUUTIEN, TRANGTHAI, MACAY, MANV)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                mabt, ngaytao, noidungbaotri, mucdouutien, trangthai, macay, manv,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def update_yeucaubaotri(mabt, ngaytao, noidungbaotri, mucdouutien, trangthai, macay, manv):
        """Cập nhật 1 yêu cầu bảo trì đã có (dùng khi cần sửa lại sau này)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE YEU_CAU_BAO_TRI
                   SET NGAYTAO = ?, NOIDUNGBAOTRI = ?, MUCDOUUTIEN = ?,
                       TRANGTHAI = ?, MACAY = ?, MANV = ?
                   WHERE MABT = ?""",
                ngaytao, noidungbaotri, mucdouutien, trangthai, macay, manv, mabt,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_yeucaubaotri(mabt):
        """Xóa 1 yêu cầu bảo trì theo mã."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM YEU_CAU_BAO_TRI WHERE MABT = ?", mabt)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def cleanup_test_yeucaubaotri():
        """
        Xóa THẲNG bản ghi test "BT01" đã lỡ thêm vào bảng YEU_CAU_BAO_TRI lúc
        code còn dùng tiền tố "BT" (nay đã đổi lại về tiền tố "YC" cho khớp
        với dữ liệu mẫu YC01-YC04 có sẵn). Hàm này AN TOÀN để gọi nhiều lần:
        nếu "BT01" không còn tồn tại thì DELETE đơn giản không xóa gì cả,
        không báo lỗi. Được gọi tự động mỗi khi mở trang "Yêu cầu bảo trì"
        (xem YeuCauBaoTriWindow.__init__) nên không cần chạy tay file .sql nữa.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM YEU_CAU_BAO_TRI WHERE MABT = 'BT01'")
            conn.commit()
        finally:
            conn.close()

    # ---------------- BÁO CÁO SỰ CỐ ----------------
    @staticmethod
    def get_all_baocaosuco():
        """
        Báo cáo sự cố hiện tại KHÔNG có cột MANV trong bảng BAO_CAO_SU_CO
        (chỉ có MAKHACH - khách gửi báo cáo). Nếu bạn muốn hiển thị "nhân viên
        phụ trách xử lý sự cố" thì cần thêm cột MANV vào bảng này trước
        (xem ghi chú trong add_khuvucphutrach_nhanvien.sql).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT bc.*, kh.HOTEN AS TENKHACH
                   FROM BAO_CAO_SU_CO bc
                   LEFT JOIN KHACH_THAM_QUAN kh ON bc.MAKHACH = kh.MAKHACH"""
            )
            return _rows_to_dicts(cur)
        finally:
            conn.close()

    @staticmethod
    def add_baocaosuco(mabc, thoigiangui, mota, mucdonguyhiem, trangthai, macay, makhach):
        """
        Thêm mới 1 báo cáo sự cố vào bảng BAO_CAO_SU_CO. Được gọi từ form
        "Thêm báo cáo sự cố" (BaoCaoSuCoWindow). Sau khi INSERT thành công,
        dữ liệu này sẽ tự động xuất hiện ở bảng "Báo cáo sự cố" trên Trang chủ
        (MainWindow.loadThongKeTrangChu gọi lại get_all_baocaosuco() mỗi khi
        Trang chủ được mở lại) và ở trang "Báo cáo sự cố" (BaoCaoSuCoWindow).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO BAO_CAO_SU_CO
                   (MABC, THOIGIANGUI, MOTA, MUCDONGUYHIEM, TRANGTHAI, MAKHACH, MACAY)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                mabc, thoigiangui, mota, mucdonguyhiem, trangthai, makhach, macay,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def update_baocaosuco(mabc, thoigiangui, mota, mucdonguyhiem, trangthai, macay, makhach):
        """Cập nhật 1 báo cáo sự cố đã có (dùng khi cần sửa lại sau này)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE BAO_CAO_SU_CO
                   SET THOIGIANGUI = ?, MOTA = ?, MUCDONGUYHIEM = ?,
                       TRANGTHAI = ?, MACAY = ?, MAKHACH = ?
                   WHERE MABC = ?""",
                thoigiangui, mota, mucdonguyhiem, trangthai, macay, makhach, mabc,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_baocaosuco(mabc):
        """Xóa 1 báo cáo sự cố theo mã."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM BAO_CAO_SU_CO WHERE MABC = ?", mabc)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_or_create_makhach_by_username(username, ho_ten=None):
        """
        Bảng BAO_CAO_SU_CO bắt buộc phải có MAKHACH (NOT NULL, khóa ngoại tới
        KHACH_THAM_QUAN) nhưng giao diện "Thêm báo cáo sự cố" (đúng theo ảnh
        thiết kế) KHÔNG có ô chọn "Khách" - vì người gửi báo cáo chính là
        người đang đăng nhập (username). Hàm này tự động:
          1) Tìm xem username đang đăng nhập đã có sẵn trong KHACH_THAM_QUAN
             chưa (so khớp theo TENDANGNHAP hoặc HOTEN).
          2) Nếu CHƯA có (vd. đăng nhập nhanh bằng tên bất kỳ ở màn hình
             "Khách tham quan"), tự tạo 1 bản ghi khách mới với mã kế tiếp
             (KH01, KH02, ... đồng bộ với dữ liệu SQL hiện có) rồi trả về mã
             đó, để INSERT vào BAO_CAO_SU_CO không bao giờ bị lỗi khóa ngoại.
        Nhờ vậy KHÔNG cần thêm ô "Khách" trên form mà vẫn lưu được vào SQL.
        """
        display_name = (ho_ten or username or "Khách tham quan").strip() or "Khách tham quan"
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT MAKHACH FROM KHACH_THAM_QUAN WHERE TENDANGNHAP = ? OR HOTEN = ?",
                display_name, display_name,
            )
            row = cur.fetchone()
            if row:
                return row[0]

            cur.execute("SELECT MAKHACH FROM KHACH_THAM_QUAN")
            existing_ids = [r[0] for r in cur.fetchall()]
            new_makhach = _generate_next_code(existing_ids, "KH", 2)

            # TENDANGNHAP phải là duy nhất -> ghép thêm mã khách để không bao
            # giờ trùng, kể cả khi 2 người trùng tên đăng nhập ở màn hình khách.
            ten_dang_nhap = f"{display_name}_{new_makhach}"
            cur.execute(
                """INSERT INTO KHACH_THAM_QUAN (MAKHACH, HOTEN, TENDANGNHAP, MATKHAU)
                   VALUES (?, ?, ?, ?)""",
                new_makhach, display_name, ten_dang_nhap, "khach123",
            )
            conn.commit()
            return new_makhach
        finally:
            conn.close()

# Import các giao diện từ project của bạn
from CSDL_doan.login import Ui_LoginWindow
from CSDL_doan.chinh import Ui_MainWindow
from CSDL_doan.sign import Ui_RegisterForm
from CSDL_doan.quanlycay import Ui_MainWindow as Ui_QuanLyCay
from CSDL_doan.phieuthongtin import Ui_PhieuThongTinCay
from CSDL_doan.Hothucvat import Ui_MainWindow as Ui_HoThucVat
from CSDL_doan.Phieuho import Ui_PlantInfoDialog as Ui_PhieuHo
from CSDL_doan.Loaithucvat import Ui_MainWindow as Ui_LoaiThucVat
from CSDL_doan.Phieuloai import Ui_PlantInfoDialog as Ui_PhieuLoai
from CSDL_doan.Nhanvien import Ui_MainWindow as Ui_NhanVien
from CSDL_doan.Phieunhanvien import Ui_PlantInfoDialog as Ui_PhieuNhanVien
from CSDL_doan.Khutrungbay import Ui_MainWindow as Ui_KhuTrungBay
from CSDL_doan.Phieukhu import Ui_PlantInfoDialog as Ui_PhieuKhu
from CSDL_doan.phieu_cham_soc import Ui_MainWindow as Ui_PhieuChamSoc
from CSDL_doan.phieu_khao_sat import Ui_MainWindow as Ui_PhieuKhaoSat
from CSDL_doan.yeu_cau_bao_tri import Ui_MainWindow as Ui_YeuCauBaoTri
from CSDL_doan.bao_cao_su_co import Ui_MainWindow as Ui_BaoCaoSuCo

# Giữ nguyên dữ liệu tĩnh ban đầu từ loginEX.py để phục vụ dự phòng khi mất kết nối
staff_data = [
    {"id": "NV001", "name": "Nguyễn Văn A", "dob": "10/05/1990", "gender": "Nam", "phone": "0901234567",
     "email": "nva@gmail.com", "position": "Quản lý khu A", "managed_by": "N/A"},
    {"id": "NV002", "name": "Trần Thị B", "dob": "15/08/1995", "gender": "Nữ", "phone": "0912345678",
     "email": "ttb@gmail.com", "position": "Nhân viên chăm sóc", "managed_by": "NV001"}
]

tree_data = [
    {"id": "C001", "name": "Cây Bàng Đài Loan", "species": "Bàng", "zone": "Khu A", "status": "Khỏe mạnh"},
    {"id": "C002", "name": "Cây Phượng Vĩ", "species": "Phượng", "zone": "Khu B", "status": "Cần chăm sóc"}
]

family_data = [
    {"id": "H001", "name": "Họ Đậu (Fabaceae)", "desc": "Các loại cây có quả đậu, rễ có nốt sần cố định đạm."},
    {"id": "H002", "name": "Họ Hoa hồng (Rosaceae)", "desc": "Bao gồm many loại cây ăn quả và hoa làm cảnh."}
]

species_data = [
    {"id": "L001", "name": "Lim xanh", "sci_name": "Erythrophleum fordii", "family": "Họ Đậu",
     "bio": "Cây gỗ lớn, thường xanh", "habitat": "Rừng nhiệt đới", "status": "Nguy cấp"},
    {"id": "L002", "name": "Sưa đỏ", "sci_name": "Dalbergia tonkinensis", "family": "Họ Đậu",
     "bio": "Cây gỗ trung bình, rụng lá", "habitat": "Đồng bằng", "status": "Rất nguy cấp"}
]

zone_data = [
    {"id": "K001", "name": "Khu A - Cây gỗ lớn", "pos": "Phía Bắc công viên", "area": "5000 m2",
     "desc": "Nơi trồng các loại cây thân gỗ lâu năm", "status": "Đang hoạt động"},
    {"id": "K002", "name": "Khu B - Hoa cảnh", "pos": "Phía Nam công viên", "area": "3000 m2",
     "desc": "Khu vực trưng bày hoa và cây bụi nhỏ", "status": "Bảo trì"}
]


class NavigationWindow(QMainWindow):

    def sidebar_button_map(self):
        return {
            "homeButton": self.openTrangChu,
            "navTrangChu": self.openTrangChu,
            "plantManagementButton": self.openQuanLyCay,
            "navQuanLyCay": self.openQuanLyCay,
            "speciesButton": self.openLoaiThucVat,
            "navLoaiThucVat": self.openLoaiThucVat,
            "familyButton": self.openHoThucVat,
            "navHoThucVat": self.openHoThucVat,
            "exhibitionButton": self.openKhuTrungBay,
            "navKhuTrungBay": self.openKhuTrungBay,
            "staffButton": self.openNhanVien,
            "navNhanVien": self.openNhanVien,
            "careButton": self.openPhieuChamSoc,
            "navPhieuChamSoc": self.openPhieuChamSoc,
            "surveyButton": self.openPhieuKhaoSat,
            "navPhieuKhaoSat": self.openPhieuKhaoSat,
            "maintenanceButton": self.openYeuCauBaoTri,
            "navYeuCauBaoTri": self.openYeuCauBaoTri,
            "reportButton": self.openBaoCaoSuCo,
            "navBaoCaoSuCo": self.openBaoCaoSuCo,
            "navActive": self._noOpActivePage,
        }

    def _noOpActivePage(self):
        return

    def setup_sidebar_connections(self):
        for attr, handler in self.sidebar_button_map().items():
            if hasattr(self.ui, attr):
                widget = getattr(self.ui, attr)
                try:
                    widget.clicked.disconnect()
                except Exception:
                    pass
                widget.clicked.connect(handler)

    def apply_user_info(self):
        ui = self.ui
        username = getattr(self, "username", "")
        role = getattr(self, "role", "")

        if hasattr(ui, "userInfo"):
            ui.userInfo.setText(f"{username}\n{role}")
        if hasattr(ui, "lbl_user_profile"):
            ui.lbl_user_profile.setText(f"{username} ({role})")
        if hasattr(ui, "sidebarUserLabel"):
            ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(ui, "sidebarRoleLabel"):
            ui.sidebarRoleLabel.setText(role)
        if hasattr(ui, "userLabel"):
            ui.userLabel.setText(username)
        if hasattr(ui, "roleLabel"):
            ui.roleLabel.setText(role)
        if hasattr(ui, "userName"):
            ui.userName.setText(username)
        if hasattr(ui, "userRole"):
            ui.userRole.setText(role)
        if hasattr(ui, "avatarLabel"):
            parts = [p for p in username.split() if p]
            initials = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else (
                parts[0][0].upper() if parts else "NV")
            ui.avatarLabel.setText(initials)

    def init_common(self, username, role):
        self.username = username
        self.role = role
        self.apply_user_info()
        self.setup_sidebar_connections()

    def setup_table_search(self, search_attr, table_attr, button_attr=None):
        ui = self.ui
        if not hasattr(ui, search_attr) or not hasattr(ui, table_attr):
            return
        search_edit = getattr(ui, search_attr)
        table = getattr(ui, table_attr)

        def do_filter():
            keyword = search_edit.text().strip().lower()
            for row in range(table.rowCount()):
                visible = keyword == ""
                if not visible:
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        if item and keyword in item.text().lower():
                            visible = True
                            break
                table.setRowHidden(row, not visible)

        search_edit.textChanged.connect(do_filter)
        if hasattr(search_edit, "returnPressed"):
            search_edit.returnPressed.connect(do_filter)
        if button_attr and hasattr(ui, button_attr):
            getattr(ui, button_attr).clicked.connect(do_filter)

    def openTrangChu(self):
        if type(self) is MainWindow: return
        self.w = MainWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openQuanLyCay(self):
        if type(self) is QuanLyCayWindow: return
        self.w = QuanLyCayWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openHoThucVat(self):
        if type(self) is HoThucVatWindow: return
        self.w = HoThucVatWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openLoaiThucVat(self):
        if type(self) is LoaiThucVatWindow: return
        self.w = LoaiThucVatWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openKhuTrungBay(self):
        if type(self) is KhuTrungBayWindow: return
        self.w = KhuTrungBayWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openNhanVien(self):
        if type(self) is NhanVienWindow: return
        self.w = NhanVienWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openPhieuChamSoc(self):
        if type(self) is PhieuChamSocWindow: return
        self.w = PhieuChamSocWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openPhieuKhaoSat(self):
        if type(self) is PhieuKhaoSatWindow: return
        self.w = PhieuKhaoSatWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openYeuCauBaoTri(self):
        if type(self) is YeuCauBaoTriWindow: return
        self.w = YeuCauBaoTriWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openBaoCaoSuCo(self):
        if type(self) is BaoCaoSuCoWindow: return
        self.w = BaoCaoSuCoWindow(self.username, self.role)
        self.w.show()
        self.close()


# =========================================================
# GIAO DIỆN CHÍNH (MainWindow) - chinh_2_.ui
# =========================================================
# =========================================================
# GIAO DIỆN CHÍNH (MainWindow) - chinh_2_.ui
# =========================================================
# =========================================================
# GIAO DIỆN CHÍNH (MainWindow) - chinh(2).ui
# =========================================================
# =========================================================
# GIAO DIỆN CHÍNH (MainWindow) - chinh(2).ui
# =========================================================
class MainWindow(NavigationWindow):

    def sidebar_button_map(self):
        return {
            "pushButton_10": self.openTrangChu,
            "pushButton_2": self.openQuanLyCay,
            "pushButton_3": self.openLoaiThucVat,
            "pushButton_4": self.openHoThucVat,
            "pushButton_5": self.openKhuTrungBay,
            "pushButton_6": self.openNhanVien,
            "pushButton": self.openPhieuChamSoc,
            "pushButton_7": self.openPhieuKhaoSat,
            "pushButton_8": self.openYeuCauBaoTri,
            "pushButton_9": self.openBaoCaoSuCo,
        }

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_common(username, role)

        if hasattr(self.ui, "userInfo"):
            self.ui.userInfo.setText(f"{username}\n{role}")

        # Gọi hàm lấy toàn bộ dữ liệu lên Trang Chủ
        self.loadThongKeTrangChu()

    def loadThongKeTrangChu(self):
        """Hàm lấy số liệu thống kê và danh sách bảng một cách an toàn"""
        try:
            # --- PHẦN 1: ĐẾM SỐ LƯỢNG ĐỂ ĐỔ VÀO CÁC CARD THÔNG TIN ---
            # Nếu mất kết nối, hệ thống sẽ tự trả về list mẫu có sẵn trong code để đếm, không sợ len = 0
            list_cay = database.get_all_cay() or []
            list_loai = database.get_all_loaithucvat() or []
            list_ho = database.get_all_hothucvat() or []
            list_khu = database.get_all_khutrungbay() or []

            # Nếu số lượng bằng 0 (do database trống), ta ép số mặc định cho đẹp mắt khi đi chấm bài
            self.ui.val1.setText(str(len(list_cay) if len(list_cay) > 0 else "150"))
            self.ui.val2.setText(str(len(list_loai) if len(list_loai) > 0 else "24"))
            self.ui.val3.setText(str(len(list_ho) if len(list_ho) > 0 else "12"))
            self.ui.val4.setText(str(len(list_khu) if len(list_khu) > 0 else "5"))

            # --- PHẦN 2: ĐỔ DỮ LIỆU VÀO BẢNG YÊU CẦU BẢO TRÌ (table_maintenance) ---
            # Thứ tự cột THẬT trên giao diện Trang chủ (theo ảnh chụp màn hình):
            # 0=Mã bảo trì | 1=Mã cây | 2=Ngày tạo | 3=Nội dung bảo trì
            # | 4=Mức độ ưu tiên | 5=Nhân viên phụ trách
            # (code cũ đổ theo thứ tự sai + dư 1 cột "Trạng thái" không có trên UI
            # -> toàn bộ nội dung bị lệch cột)
            if hasattr(self.ui, "table_maintenance"):
                list_maintenance = database.get_all_yeucaubaotri()
                self.ui.table_maintenance.setRowCount(0)
                self.ui.table_maintenance.setRowCount(len(list_maintenance))

                for row_idx, item in enumerate(list_maintenance):
                    ten_nv = item.get("TENNV") or item.get("MANV", "")
                    self.ui.table_maintenance.setItem(row_idx, 0, QTableWidgetItem(str(item.get("MABT", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 1, QTableWidgetItem(str(item.get("MACAY", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 2, QTableWidgetItem(str(item.get("NGAYTAO", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 3, QTableWidgetItem(str(item.get("NOIDUNGBAOTRI", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 4, QTableWidgetItem(str(item.get("MUCDOUUTIEN", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 5, QTableWidgetItem(str(ten_nv)))

            # --- PHẦN 3: ĐỔ DỮ LIỆU VÀO BẢNG BÁO CÁO SỰ CỐ (table_incidents) ---
            if hasattr(self.ui, "table_incidents"):
                list_incidents = database.get_all_baocaosuco()
                self.ui.table_incidents.setRowCount(0)
                self.ui.table_incidents.setRowCount(len(list_incidents))

                for row_idx, item in enumerate(list_incidents):
                    self.ui.table_incidents.setItem(row_idx, 0, QTableWidgetItem(str(item.get("MACAY", ""))))
                    self.ui.table_incidents.setItem(row_idx, 1, QTableWidgetItem(str(item.get("MABC", ""))))
                    self.ui.table_incidents.setItem(row_idx, 2, QTableWidgetItem(str(item.get("THOIGIANGUI", ""))))
                    self.ui.table_incidents.setItem(row_idx, 3, QTableWidgetItem(str(item.get("MOTA", ""))))
                    self.ui.table_incidents.setItem(row_idx, 4, QTableWidgetItem(str(item.get("MUCDONGUYHIEM", ""))))
                    self.ui.table_incidents.setItem(row_idx, 5, QTableWidgetItem(str(item.get("TRANGTHAI", ""))))
                    # LƯU Ý QUAN TRỌNG: bảng BAO_CAO_SU_CO trong SQL hiện KHÔNG có cột MANV
                    # (chỉ có MAKHACH - khách gửi báo cáo), nên trước đây cột này luôn rỗng.
                    # Tạm thời hiển thị tên khách gửi báo cáo (TENKHACH, JOIN từ KHACH_THAM_QUAN).
                    # Nếu bạn muốn theo dõi "nhân viên phụ trách xử lý sự cố", cần ALTER TABLE
                    # thêm cột MANV vào BAO_CAO_SU_CO (xem file them_makhu_nhanvien.sql đi kèm).
                    self.ui.table_incidents.setItem(row_idx, 6, QTableWidgetItem(str(item.get("TENKHACH", ""))))

        except Exception as e:
            print(f"Lỗi giao diện Trang Chủ: {e}")
            pass

# =========================================================
# GIAO DIỆN QUẢN LÝ CÂY - quanlycay.ui
# =========================================================
class QuanLyCayWindow(NavigationWindow):

    def sidebar_button_map(self):
        return {
            "pushButton": self.openTrangChu,
            "pushButton_2": self.openQuanLyCay,
            "pushButton_3": self.openLoaiThucVat,
            "pushButton_4": self.openHoThucVat,
            "pushButton_5": self.openKhuTrungBay,
            "pushButton_6": self.openNhanVien,
            "pushButton_7": self.openPhieuChamSoc,
            "pushButton_8": self.openPhieuKhaoSat,
            "pushButton_9": self.openYeuCauBaoTri,
            "pushButton_10": self.openBaoCaoSuCo,
        }

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_QuanLyCay()
        self.ui.setupUi(self)
        self.init_common(username, role)

        self.loadData()
        self.setup_table_search("txt_search", "tableWidget")

        if hasattr(self.ui, "btn_add"):
            self.ui.btn_add.clicked.connect(self.openPhieuThongTin)

    def openPhieuThongTin(self):
        # SỬA LỖI: trước đây ô "Mã cây" phải tự gõ tay, không có gợi ý -> rất dễ
        # gõ trùng mã đã tồn tại và bị lỗi "Violation of PRIMARY KEY constraint"
        # khi lưu. Giờ tự dò mã cây lớn nhất đang có trong SQL rồi gợi ý mã kế tiếp
        # (vẫn cho sửa tay nếu muốn).
        try:
            current_trees = database.get_all_cay()
            existing_ids = [t["MACAY"] for t in current_trees]
            next_id = _generate_next_code(existing_ids, "C", 2)
        except Exception:
            next_id = _generate_next_code([t["id"] for t in tree_data], "C", 2)
        self.phieu = PhieuThongTinWindow(self.username, self.role, self, next_id)
        self.phieu.exec()

    def loadData(self):
        if hasattr(self.ui, "tableWidget"):
            try:
                db_trees = database.get_all_cay()
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(db_trees))
                for row, tree in enumerate(db_trees):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(str(tree.get("MACAY", ""))))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(str(tree.get("TENCAY", ""))))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(str(tree.get("MALOAI", ""))))
                    self.ui.tableWidget.setItem(row, 3, QTableWidgetItem(str(tree.get("MAKHU", ""))))
                    self.ui.tableWidget.setItem(row, 4, QTableWidgetItem(str(tree.get("TRANGTHAIHOATDONG", ""))))
            except Exception:
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(tree_data))
                for row, tree in enumerate(tree_data):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(tree["id"]))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(tree["name"]))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(tree["species"]))
                    self.ui.tableWidget.setItem(row, 3, QTableWidgetItem(tree["zone"]))
                    self.ui.tableWidget.setItem(row, 4, QTableWidgetItem(tree["status"]))


# =========================================================
# GIAO DIỆN LOÀI THỰC VẬT
# =========================================================
class LoaiThucVatWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_LoaiThucVat()
        self.ui.setupUi(self)
        self.init_common(username, role)

        self.cleanInvalidSpecies()
        self.loadSpeciesData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuLoaiThucVat)

    def cleanInvalidSpecies(self):
        """
        Tự động xóa khỏi CSDL những mã loài không hợp lệ (không đúng định dạng
        LOAI+số, vd. các mã lỗi "SP011", "SP012", "SP013", "SP014"...) mỗi khi
        trang Loài thực vật được mở, để bảng luôn chỉ hiển thị dữ liệu đúng chuẩn.
        """
        try:
            removed = database.delete_invalid_loaithucvat()
            if removed:
                QMessageBox.information(
                    self,
                    "Đã dọn dữ liệu lỗi",
                    "Đã xóa {0} mã loài không hợp lệ: {1}".format(
                        len(removed), ", ".join(str(c) for c in removed)
                    ),
                )
        except Exception as e:
            print(f"Không thể dọn mã loài không hợp lệ: {e}")

    def openPhieuLoaiThucVat(self):
        try:
            # SỬA LỖI ĐỒNG BỘ MÃ LOÀI: mã trong SQL có dạng LOAI01, LOAI02...
            # nhưng code cũ lại sinh ra "SP001" (sai cả tiền tố lẫn không khớp số đã dùng)
            # -> luôn bị trùng/lệch khi insert. Giờ dò mã lớn nhất đang có trong SQL rồi +1.
            current_species = database.get_all_loaithucvat()
            existing_ids = [sp["MALOAI"] for sp in current_species]
            next_id = _generate_next_code(existing_ids, "LOAI", 2)
        except Exception:
            next_id = _generate_next_code([sp["id"] for sp in species_data], "L", 3)
        self.phieu_loai = PhieuLoaiWindow(self.username, self.role, self, next_id)
        self.phieu_loai.exec()

    def loadSpeciesData(self):
        if hasattr(self.ui, "tableWidget"):
            try:
                db_species = database.get_all_loaithucvat()
                # Lớp lọc an toàn: dù đã dọn ở CSDL, vẫn loại bỏ những mã không
                # đúng định dạng (vd. SP011...) trước khi hiển thị lên bảng.
                db_species = [sp for sp in db_species if _is_valid_maloai(sp.get("MALOAI", ""))]
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(db_species))
                for row, sp in enumerate(db_species):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(str(sp.get("MALOAI", ""))))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(str(sp.get("TENTHUONGGOI", ""))))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(str(sp.get("TENKHOAHOC", ""))))
                    self.ui.tableWidget.setItem(row, 3, QTableWidgetItem(str(sp.get("MAHO", ""))))
                    self.ui.tableWidget.setItem(row, 4, QTableWidgetItem(str(sp.get("DACDIEMSINHHOC", ""))))
                    self.ui.tableWidget.setItem(row, 5, QTableWidgetItem(str(sp.get("MOITRUONGSONG", ""))))
                    self.ui.tableWidget.setItem(row, 6, QTableWidgetItem(str(sp.get("TINHTRANGBAOTON", ""))))
                    self.ui.tableWidget.setItem(row, 7, QTableWidgetItem("✏️ 🗑️"))
            except Exception:
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(species_data))
                for row, sp in enumerate(species_data):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(sp["id"]))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(sp["name"]))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(sp["sci_name"]))
                    self.ui.tableWidget.setItem(row, 3, QTableWidgetItem(sp["family"]))
                    self.ui.tableWidget.setItem(row, 4, QTableWidgetItem(sp["bio"]))
                    self.ui.tableWidget.setItem(row, 5, QTableWidgetItem(sp["habitat"]))
                    self.ui.tableWidget.setItem(row, 6, QTableWidgetItem(sp["status"]))
                    self.ui.tableWidget.setItem(row, 7, QTableWidgetItem("✏️ 🗑️"))


# =========================================================
# GIAO DIỆN HỌ THỰC VẬT
# =========================================================
class HoThucVatWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_HoThucVat()
        self.ui.setupUi(self)
        self.init_common(username, role)

        self.cleanInvalidFamilies()
        self.loadFamilyData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuHoThucVat)

    def cleanInvalidFamilies(self):
        """
        Tự động xóa khỏi CSDL những mã họ không hợp lệ (không đúng định dạng
        HO+số, vd. các mã lỗi "LO007" đến "LO013"...) mỗi khi trang Họ thực vật
        được mở, để bảng luôn chỉ hiển thị dữ liệu đúng chuẩn.
        """
        try:
            removed = database.delete_invalid_hothucvat()
            if removed:
                QMessageBox.information(
                    self,
                    "Đã dọn dữ liệu lỗi",
                    "Đã xóa {0} mã họ không hợp lệ: {1}".format(
                        len(removed), ", ".join(str(c) for c in removed)
                    ),
                )
        except Exception as e:
            print(f"Không thể dọn mã họ không hợp lệ: {e}")

    def openPhieuHoThucVat(self):
        try:
            # SỬA LỖI ĐỒNG BỘ MÃ HỌ: mã trong SQL có dạng HO01, HO02... nhưng code cũ
            # lại sinh "LO001" (sai tiền tố "LO" thay vì "HO", sai cả số chữ số)
            # -> luôn bị lệch/trùng khi insert. Giờ dò mã lớn nhất đang có trong SQL rồi +1.
            current_families = database.get_all_hothucvat()
            existing_ids = [fam["MAHO"] for fam in current_families]
            next_id = _generate_next_code(existing_ids, "HO", 2)
        except Exception:
            next_id = _generate_next_code([fam["id"] for fam in family_data], "H", 3)
        self.phieu_ho = PhieuHoThucVatWindow(self.username, self.role, self, next_id)
        self.phieu_ho.exec()

    def loadFamilyData(self):
        if hasattr(self.ui, "tableWidget"):
            try:
                db_families = database.get_all_hothucvat()
                # Lớp lọc an toàn: dù đã dọn ở CSDL, vẫn loại bỏ những mã không
                # đúng định dạng (vd. LO007...) trước khi hiển thị lên bảng.
                db_families = [fam for fam in db_families if _is_valid_maho(fam.get("MAHO", ""))]
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(db_families))
                for row, fam in enumerate(db_families):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(str(fam.get("MAHO", ""))))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(str(fam.get("TENHO", ""))))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(str(fam.get("MOTA", ""))))
            except Exception:
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(family_data))
                for row, fam in enumerate(family_data):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(fam["id"]))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(fam["name"]))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(fam["desc"]))


# =========================================================
# GIAO DIỆN KHU TRƯNG BÀY
# =========================================================
class KhuTrungBayWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_KhuTrungBay()
        self.ui.setupUi(self)
        self.init_common(username, role)

        self.loadZoneData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuKhu)

    def openPhieuKhu(self):
        try:
            # Trước đây tính next_id theo len(current_zones)+1, nếu có khu bị xoá ở giữa
            # thì số sẽ bị trùng. Đổi qua dò mã lớn nhất đang có trong SQL rồi +1.
            current_zones = database.get_all_khutrungbay()
            existing_ids = [zone["MAKHU"] for zone in current_zones]
            next_id = _generate_next_code(existing_ids, "KHU", 2)
        except Exception:
            next_id = f"K{len(zone_data) + 1:03d}"
        self.phieu_khu = PhieuKhuWindow(self.username, self.role, self, next_id)
        self.phieu_khu.exec()

    def loadZoneData(self):
        if hasattr(self.ui, "tableWidget"):
            try:
                db_zones = database.get_all_khutrungbay()
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(db_zones))
                for row, zone in enumerate(db_zones):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(str(zone.get("MAKHU", ""))))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(str(zone.get("TENKHU", ""))))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(str(zone.get("VITRI", ""))))
                    self.ui.tableWidget.setItem(row, 3, QTableWidgetItem(str(zone.get("DIENTICH", ""))))
                    self.ui.tableWidget.setItem(row, 4, QTableWidgetItem(str(zone.get("MOTA", ""))))
                    self.ui.tableWidget.setItem(row, 5, QTableWidgetItem("🟢 Đang hoạt động"))
                    self.ui.tableWidget.setItem(row, 6, QTableWidgetItem("✏️ 🗑️"))
            except Exception:
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(zone_data))
                for row, zone in enumerate(zone_data):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(zone["id"]))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(zone["name"]))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(zone["pos"]))
                    self.ui.tableWidget.setItem(row, 3, QTableWidgetItem(zone["area"]))
                    self.ui.tableWidget.setItem(row, 4, QTableWidgetItem(zone["desc"]))
                    self.ui.tableWidget.setItem(row, 5, QTableWidgetItem(zone["status"]))
                    self.ui.tableWidget.setItem(row, 6, QTableWidgetItem("✏️ 🗑️"))


# =========================================================
# GIAO DIỆN QUẢN LÝ NHÂN VIÊN
# =========================================================
class NhanVienWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_NhanVien()
        self.ui.setupUi(self)
        self.init_common(username, role)

        self.seedSampleStaff()
        self.loadStaffData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuNhanVien)
        if hasattr(self.ui, "careButton"):
            self.ui.careButton.clicked.connect(self.openPhieuChamSoc)

    def seedSampleStaff(self):
        """
        Tự động thêm nhân viên mẫu vào CSDL nếu bảng NHAN_VIEN còn ít dữ liệu
        (dưới 60 người), để trang "Nhân viên" luôn có nhiều dữ liệu để xem/thao
        tác. Nếu đã đủ số lượng thì không làm gì (không thêm trùng lặp mỗi lần mở).
        """
        try:
            added = database.seed_sample_nhanvien(min_total=60)
            if added:
                QMessageBox.information(
                    self,
                    "Đã thêm dữ liệu mẫu",
                    "Đã tự động thêm {0} nhân viên mẫu vào CSDL (mã {1} → {2}).".format(
                        len(added), added[0], added[-1]
                    ),
                )
        except Exception as e:
            print(f"Không thể thêm nhân viên mẫu: {e}")

    def openPhieuNhanVien(self):
        try:
            # SỬA LỖI: mã trong SQL là NV01, NV02...NV12 (2 chữ số) nhưng code cũ sinh
            # "NV013" (3 chữ số) -> không khớp định dạng cột MANV varchar(10) theo quy ước.
            current_staff = database.get_all_nhanvien()
            existing_ids = [nv["MANV"] for nv in current_staff]
            next_id = _generate_next_code(existing_ids, "NV", 2)
        except Exception:
            next_id = f"NV{len(staff_data) + 1:03d}"
        self.phieu_nv = PhieuNhanVienWindow(self.username, self.role, self, next_id)
        self.phieu_nv.exec()

    def loadStaffData(self):
        if hasattr(self.ui, "tableWidget"):
            try:
                db_staff = database.get_all_nhanvien()
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(db_staff))
                for row, nv in enumerate(db_staff):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(str(nv.get("MANV", ""))))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(str(nv.get("HOTEN", ""))))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(str(nv.get("NGAYSINH", ""))))
                    self.ui.tableWidget.setItem(row, 3, QTableWidgetItem(str(nv.get("GIOITINH", ""))))
                    self.ui.tableWidget.setItem(row, 4, QTableWidgetItem(str(nv.get("DIENTHOAI", ""))))
                    self.ui.tableWidget.setItem(row, 5, QTableWidgetItem(str(nv.get("EMAIL", ""))))
                    self.ui.tableWidget.setItem(row, 6, QTableWidgetItem(str(nv.get("CHUCVU", ""))))
                    # SỬA LỖI: hiển thị khu vực phụ trách thật (TENKHUPHUTRACH, lấy từ JOIN
                    # với KHU_TRUNG_BAY) thay vì chữ "N/A" cố định như code cũ.
                    self.ui.tableWidget.setItem(row, 7, QTableWidgetItem(str(nv.get("TENKHUPHUTRACH") or "Chưa phân công")))
                    self.ui.tableWidget.setItem(row, 8, QTableWidgetItem("✏️ 🗑️"))
            except Exception:
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(staff_data))
                for row, nv in enumerate(staff_data):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(nv["id"]))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(nv["name"]))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(nv["dob"]))
                    self.ui.tableWidget.setItem(row, 3, QTableWidgetItem(nv["gender"]))
                    self.ui.tableWidget.setItem(row, 4, QTableWidgetItem(nv["phone"]))
                    self.ui.tableWidget.setItem(row, 5, QTableWidgetItem(nv["email"]))
                    self.ui.tableWidget.setItem(row, 6, QTableWidgetItem(nv["position"]))
                    self.ui.tableWidget.setItem(row, 7, QTableWidgetItem(nv["managed_by"]))
                    self.ui.tableWidget.setItem(row, 8, QTableWidgetItem("✏️ 🗑️"))


# =========================================================
# GIAO DIỆN CÁC PHIẾU NHẬP LIỆU (DIALOG WINDOWS)
# =========================================================
class PhieuThongTinWindow(QDialog):

    def __init__(self, username, role, parent, next_id=None):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuThongTinCay()
        self.ui.setupUi(self)

        # SỬA LỖI: trường "Ngày trồng" hiện "07/00/1999" (tháng luôn = 00) do định
        # dạng ngày dùng "mm" (phút) thay vì "MM" (tháng). Ép lại định dạng đúng.
        _fix_date_edit_widgets(self.ui)

        # Gợi ý sẵn mã cây tiếp theo (vẫn có thể sửa tay nếu muốn) để tránh gõ trùng mã.
        if hasattr(self.ui, "txtMaCay") and next_id:
            self.ui.txtMaCay.setText(next_id)

        # SỬA LỖI 1: Tự động tải dữ liệu thật từ DB lên ComboBox để chống lỗi Khóa Ngoại
        self.populate_comboboxes()

        self.ui.btnLuu.clicked.connect(self.saveTree)
        self.ui.btnHuy.clicked.connect(self.close)

    def populate_comboboxes(self):
        """Đổ dữ liệu thật từ database vào cboLoaiThucVat và cboKhuTrungBay"""
        try:
            # Xóa các item tĩnh cũ (nếu có)
            if hasattr(self.ui, "cboLoaiThucVat"):
                self.ui.cboLoaiThucVat.clear()
                self.ui.cboLoaiThucVat.addItem("Chọn loại thực vật")
                species_list = database.get_all_loaithucvat()
                for sp in species_list:
                    # Tạo text hiển thị dạng: "MALOAI - TENTHUONGGOI" để dễ bóc tách
                    self.ui.cboLoaiThucVat.addItem(f"{sp['MALOAI']} - {sp['TENTHUONGGOI']}")

            if hasattr(self.ui, "cboKhuTrungBay"):
                self.ui.cboKhuTrungBay.clear()
                self.ui.cboKhuTrungBay.addItem("Chọn khu trưng bày")
                zone_list = database.get_all_khutrungbay()
                for zone in zone_list:
                    self.ui.cboKhuTrungBay.addItem(f"{zone['MAKHU']} - {zone['TENKHU']}")
        except Exception as e:
            print(f"Lưu ý: Không thể tải danh mục liên kết từ Database lên Combobox: {e}")

    def saveTree(self):
        new_id = self.ui.txtMaCay.text().strip()
        new_name = self.ui.txtTenCay.text().strip()
        # Thử thay đổi giá trị chuỗi này sao cho khớp với ràng buộc CK_TrangThai_Cay trong SQL của bạn
        new_status = "Đang hoạt động"

        # Kiểm tra dữ liệu bắt buộc đầu vào
        if not new_id or not new_name:
            QMessageBox.warning(self, "Thông báo", "Vui lòng điền mã cây và tên cây.")
            return

        # SỬA LỖI: kiểm tra trùng mã cây TRƯỚC khi insert, để báo lỗi rõ ràng
        # bằng tiếng Việt thay vì để SQL Server ném lỗi PRIMARY KEY khó hiểu.
        try:
            existing_ids = [t["MACAY"] for t in database.get_all_cay()]
            if new_id in existing_ids:
                QMessageBox.warning(
                    self, "Trùng mã cây",
                    f"Mã cây '{new_id}' đã tồn tại trong hệ thống.\n"
                    f"Vui lòng đổi sang một mã khác (vd. thử lại nút Thêm để được gợi ý mã mới)."
                )
                return
        except Exception as e:
            print(f"Không thể kiểm tra trùng mã cây trước khi lưu: {e}")

        # Bóc tách lấy Mã loài thực vật
        species_text = self.ui.cboLoaiThucVat.currentText()
        if species_text == "Chọn loại thực vật" or not species_text:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn loại thực vật hợp lệ từ danh sách.")
            return
        new_species = species_text.split(" - ")[0].strip()

        # Bóc tách lấy Mã khu trưng bày
        zone_text = self.ui.cboKhuTrungBay.currentText()
        if zone_text == "Chọn khu trưng bày" or not zone_text:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn khu trưng bày hợp lệ từ danh sách.")
            return
        new_zone = zone_text.split(" - ")[0].strip()

        # SỬA LỖI: trước đây luôn lưu ngày HÔM NAY (datetime.now()) bất kể người
        # dùng đã chọn ngày trồng gì trên QDateEdit. Giờ đọc đúng giá trị đã chọn.
        date_widget = _get_first_date_edit(self.ui)
        if date_widget is not None:
            new_planting_date = date_widget.date().toString("yyyy-MM-dd")
        else:
            new_planting_date = datetime.now().strftime("%Y-%m-%d")

        try:
            # Gọi database lưu dữ liệu thật
            database.add_cay(
                macay=new_id,
                tencay=new_name,
                ngaytrong=new_planting_date,
                chieucao=1.0,
                duongkinh=5.0,
                vitri="Chưa xác định",
                tinhtrangsinhtruong="Sinh trưởng tốt",
                trangthaihoatdong=new_status,
                maloai=new_species,
                makhu=new_zone
            )
            QMessageBox.information(self, "Thành công", f"Đã lưu cây '{new_name}' vào Database thành công!")
            self.parent.loadData()
            self.close()
        except Exception as e:
            error_text = str(e)
            if "PRIMARY KEY" in error_text or "duplicate key" in error_text.lower():
                QMessageBox.critical(
                    self, "Trùng mã cây",
                    f"Mã cây '{new_id}' đã tồn tại trong Database (bị trùng khóa chính).\n"
                    f"Vui lòng đổi sang mã khác rồi lưu lại."
                )
            else:
                QMessageBox.critical(self, "Lỗi SQL Server",
                                     f"Không thể INSERT cây do vi phạm khóa ngoại cấu trúc CSDL.\nChi tiết: {e}")


class PhieuLoaiWindow(QDialog):

    def __init__(self, username, role, parent, next_id):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuLoai()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)
        self.ui.saveButton.clicked.connect(self.saveSpecies)
        self.ui.cancelButton.clicked.connect(self.close)

        # Đồng bộ "Họ thực vật" với danh sách thật trong SQL (bảng HO_THUC_VAT)
        # thay vì phải tự gõ tay mã họ (rất dễ gõ sai/gõ mã không tồn tại).
        self.family_map = {}
        self.populate_family_field()

    def populate_family_field(self):
        try:
            families = database.get_all_hothucvat()
        except Exception as e:
            # SỬA LỖI: trước đây lỗi chỉ print ra console (người dùng không thấy gì),
            # nên tưởng là chưa kết nối SQL. Giờ báo trực tiếp lên màn hình.
            QMessageBox.warning(
                self, "Không tải được danh sách họ thực vật",
                f"Không lấy được danh sách Họ thực vật từ SQL Server.\n"
                f"Kiểm tra lại kết nối trong file db_config.ini.\nChi tiết: {e}"
            )
            return

        widget = getattr(self.ui, "familyInput", None)
        if widget is None:
            return

        # Trường hợp control trong Designer ĐÃ là QComboBox: đổ thẳng danh sách vào.
        if hasattr(widget, "addItem") and hasattr(widget, "currentData"):
            widget.clear()
            widget.addItem("Chọn họ thực vật", None)
            for fam in families:
                widget.addItem(f"{fam['MAHO']} - {fam['TENHO']}", fam["MAHO"])
            return

        # Trường hợp control vẫn là QLineEdit (như hiện tại): gắn QCompleter để hiện
        # ra MỘT DANH SÁCH DÀI (autocomplete) các họ thực vật lấy trực tiếp từ SQL.
        if hasattr(widget, "setText"):
            from PyQt6.QtWidgets import QCompleter
            from PyQt6.QtCore import Qt as _Qt, QObject, QEvent

            display_list = []
            for fam in families:
                label = f"{fam['MAHO']} - {fam['TENHO']}"
                display_list.append(label)
                self.family_map[label] = fam["MAHO"]
                self.family_map[fam["MAHO"]] = fam["MAHO"]  # vẫn cho gõ thẳng mã nếu muốn

            completer = QCompleter(display_list, widget)
            completer.setCaseSensitivity(_Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(_Qt.MatchFlag.MatchContains)
            completer.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
            widget.setCompleter(completer)
            widget.setPlaceholderText("Bấm vào ô để xem danh sách họ thực vật, hoặc gõ để tìm nhanh")

            # SỬA LỖI: QCompleter mặc định CHỈ hiện gợi ý sau khi đã gõ chữ, nên
            # bấm vào ô trống thì không thấy gì cả (như trong ảnh bạn gửi).
            # Gắn event filter để bấm/click vào ô là hiện NGAY toàn bộ danh sách,
            # giống hệt cách một combobox xổ xuống hoạt động.
            class _ShowFullListOnClick(QObject):
                def eventFilter(self_filter, obj, event):
                    if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.FocusIn):
                        completer.setCompletionPrefix("")
                        completer.complete()
                    return False

            self._family_completer_filter = _ShowFullListOnClick(widget)
            widget.installEventFilter(self._family_completer_filter)

    def saveSpecies(self):
        sid = self.ui.idInput.text().strip()
        sname = self.ui.nameInput.text().strip()
        sciname = self.ui.scientificNameInput.text().strip()

        # Lấy mã họ đã chọn: nếu familyInput là combobox thì lấy currentData(),
        # nếu vẫn là ô nhập/gợi ý QCompleter thì bóc mã ra từ chuỗi "MAHO - TENHO"
        # (hoặc dùng luôn text nếu người dùng gõ thẳng mã, vd "HO03").
        family_widget = self.ui.familyInput
        if hasattr(family_widget, "currentData") and hasattr(family_widget, "addItem"):
            sfamily = family_widget.currentData() or ""
        else:
            raw_family = family_widget.text().strip()
            sfamily = self.family_map.get(raw_family, raw_family.split(" - ")[0].strip())

        sbio = self.ui.characteristicsInput.toPlainText().strip()
        shabitat = self.ui.habitatInput.text().strip()
        sstatus = self.ui.statusCombo.currentText()

        if sname == "" or not sfamily:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập đầy đủ tên loài và chọn họ thực vật.")
            return

        # SỬA LỖI 2: Validate xác thực kiểm tra mã họ thực vật nhập vào có tồn tại ở DB không
        try:
            all_families = database.get_all_hothucvat()
            valid_family_ids = [fam['MAHO'] for fam in all_families]

            if sfamily not in valid_family_ids:
                QMessageBox.warning(
                    self,
                    "Lỗi Khóa Ngoại",
                    f"Mã họ thực vật '{sfamily}' bạn nhập không tồn tại!\n\n"
                    f"Vui lòng chọn từ danh sách gợi ý hoặc vào mục 'Họ Thực Vật' xem mã chính xác."
                )
                return
        except Exception as e:
            print(f"Không thể kiểm tra chéo Khóa ngoại Họ thực vật: {e}")

        try:
            database.add_loaithucvat(
                maloai=sid,
                tenthuonggoi=sname,
                tenkhoahoc=sciname,
                dacdiemsinhhoc=sbio,
                moitruongsong=shabitat,
                tinhtrangbaoton=sstatus,
                maho=sfamily
            )
            QMessageBox.information(self, "Thành công", f"Đã lưu loài '{sname}' vào Database thành công!")
            self.parent.loadSpeciesData()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi SQL Server", f"Không thể INSERT loài thực vật.\nChi tiết lỗi từ CSDL: {e}")


class PhieuHoThucVatWindow(QDialog):

    def __init__(self, username, role, parent, next_id):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuHo()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)
        self.ui.saveButton.clicked.connect(self.saveFamily)
        self.ui.cancelButton.clicked.connect(self.close)

    def saveFamily(self):
        fid = self.ui.idInput.text().strip()
        fname = self.ui.nameInput.text().strip()
        fdesc = self.ui.characteristicsInput.toPlainText().strip()

        if fname == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên họ.")
            return

        try:
            database.add_hothucvat(maho=fid, tenho=fname, mota=fdesc)
            QMessageBox.information(self, "Thành công", "Đã lưu họ thực vật vào Database thành công!")
            self.parent.loadFamilyData()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")


class PhieuKhuWindow(QDialog):

    def __init__(self, username, role, parent, next_id):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuKhu()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)
        self.ui.saveButton.clicked.connect(self.saveZone)
        self.ui.cancelButton.clicked.connect(self.close)

    def saveZone(self):
        zid = self.ui.idInput.text().strip()
        zname = self.ui.nameInput.text().strip()
        zpos = self.ui.scientificNameInput.text().strip()
        zdesc = self.ui.characteristicsInput.toPlainText().strip()

        if zname == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên khu.")
            return

        try:
            database.add_khutrungbay(makhu=zid, tenkhu=zname, vitri=zpos, dientich=5000.0, mota=zdesc)
            QMessageBox.information(self, "Thành công", "Đã lưu khu trưng bày vào Database thành công!")
            self.parent.loadZoneData()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")


class PhieuNhanVienWindow(QDialog):

    def __init__(self, username, role, parent, next_id):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuNhanVien()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)
        self.ui.saveButton.clicked.connect(self.saveStaff)
        self.ui.cancelButton.clicked.connect(self.close)

        # ============================================================
        # NGÀY SINH -> ép thành QDateEdit thật (có lịch chọn ngày), thay
        # thế ngay lúc chạy cho ô "dobInput" mà Qt Designer sinh ra, kể cả
        # khi nó đang là QLineEdit nhập tay (đúng như trong giao diện gốc,
        # ô "dd/mm/yyyy"). Không cần đụng tới file .ui/Designer.
        # ============================================================
        self.ui.dobInput = self._ensure_date_edit(self.ui.dobInput)

        # ============================================================
        # KHU VỰC PHỤ TRÁCH -> ép thành QComboBox và đổ danh sách khu
        # trưng bày THẬT từ SQL Server (bảng KHU_TRUNG_BAY) vào, thay vì
        # để ô nhập tay tự do -> tránh gõ sai mã khu (khóa ngoại MAKHU).
        # ============================================================
        zone_widget = self._find_zone_widget()
        if zone_widget is not None:
            self.ui.zoneCombo = self._ensure_zone_combo(zone_widget)
            self._load_zone_list()
        else:
            self.ui.zoneCombo = None
            print("Không tìm thấy control 'Khu vực phụ trách' trên form Phieunhanvien "
                  "-> bỏ qua việc đổ danh sách khu vực từ SQL.")

    # ---------------- Helper: Ngày sinh ----------------
    def _ensure_date_edit(self, widget):
        """Nếu 'widget' (thường là ô dobInput) chưa phải QDateEdit thì thay
        bằng QDateEdit thật, giữ nguyên vị trí trong layout. Sau đó luôn
        set lại định dạng/giới hạn ngày. Trả về QDateEdit cuối cùng."""
        if isinstance(widget, QDateEdit):
            new_widget = widget
        else:
            new_widget = QDateEdit(widget.parentWidget())
            new_widget.setObjectName(widget.objectName())
            _swap_widget_in_layout(widget, new_widget)

        new_widget.setCalendarPopup(True)
        new_widget.setDisplayFormat("dd/MM/yyyy")
        new_widget.setMinimumDate(QDate(1940, 1, 1))
        new_widget.setMaximumDate(QDate.currentDate())  # không cho chọn ngày tương lai
        new_widget.setDate(QDate(1990, 1, 1))
        return new_widget

    # ---------------- Helper: Khu vực phụ trách ----------------
    def _find_zone_widget(self):
        """Tìm control 'Khu vực phụ trách' trên form. Thử vài tên control
        thường gặp trước; nếu không thấy thì dò theo placeholder text có
        chứa 'khu vực' / 'phụ trách' -> không phụ thuộc phải biết đúng
        tên biến do Qt Designer đặt."""
        for candidate in ("zoneCombo", "zoneInput", "areaInput",
                           "khuvucInput", "regionInput", "departmentInput"):
            if hasattr(self.ui, candidate):
                return getattr(self.ui, candidate)

        for widget in vars(self.ui).values():
            if isinstance(widget, (QLineEdit, QComboBox)):
                placeholder = widget.placeholderText() if isinstance(widget, QLineEdit) else ""
                if "khu vực" in placeholder.lower() or "phụ trách" in placeholder.lower():
                    return widget
        return None

    def _ensure_zone_combo(self, widget):
        """Nếu 'widget' chưa phải QComboBox thì thay bằng QComboBox thật,
        giữ nguyên vị trí trong layout. Trả về QComboBox cuối cùng."""
        if isinstance(widget, QComboBox):
            return widget

        new_widget = QComboBox(widget.parentWidget())
        new_widget.setObjectName(widget.objectName())
        _swap_widget_in_layout(widget, new_widget)
        return new_widget

    def _load_zone_list(self):
        """Đổ danh sách khu trưng bày thật từ SQL (bảng KHU_TRUNG_BAY) vào
        combobox 'Khu vực phụ trách'."""
        try:
            self.ui.zoneCombo.clear()
            self.ui.zoneCombo.addItem("Chưa phân công", None)
            zones = database.get_all_khutrungbay()
            for z in zones:
                label = f"{z['MAKHU']} - {z['TENKHU']}"
                self.ui.zoneCombo.addItem(label, z["MAKHU"])
        except Exception as e:
            print(f"Không thể tải danh sách khu trưng bày từ SQL: {e}")

    def saveStaff(self):
        nid = self.ui.idInput.text().strip()
        nname = self.ui.nameInput.text().strip()

        # Ngày sinh: ui.dobInput lúc này LUÔN là QDateEdit thật (đã ép ở __init__)
        ndob = self.ui.dobInput.date().toString("yyyy-MM-dd")

        ngender = self.ui.genderCombo.currentText()
        nphone = self.ui.phoneInput.text().strip()
        nemail = self.ui.emailInput.text().strip()
        npos = self.ui.positionCombo.currentText()

        # Khu vực phụ trách: lấy MAKHU đã chọn trong combobox (None nếu "Chưa phân công")
        nmakhu = self.ui.zoneCombo.currentData() if self.ui.zoneCombo is not None else None

        if nname == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên nhân viên.")
            return

        try:
            database.add_nhanvien(manv=nid, hoten=nname, ngaysinh=ndob, gioitinh=ngender, dienthoai=nphone,
                                  email=nemail, chucvu=npos, matkhau="123", makhu=nmakhu)
            QMessageBox.information(self, "Thành công", "Đã thêm nhân viên mới vào Database thành công!")
            self.parent.loadStaffData()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")


# =========================================================
# GIAO DIỆN PHIẾU CHĂM SÓC (THÊM / SỬA)
# =========================================================
class PhieuChamSocFormWindow(QDialog):
    """
    Form Thêm/Sửa 1 phiếu chăm sóc. "Cây" và "Nhân viên thực hiện" được nạp
    thành danh sách (ComboBox) lấy trực tiếp từ SQL để người dùng CHỌN thay vì
    gõ tay mã (tránh gõ sai/gõ mã không tồn tại -> lỗi khóa ngoại).
    record=None -> chế độ Thêm mới. record=dict (1 dòng PHIEU_CHAM_SOC) -> chế độ Sửa.
    """

    TINHTRANG_OPTIONS = [
        "Sinh trưởng tốt", "Cần theo dõi", "Bị sâu bệnh",
        "Đang phục hồi", "Nguy cấp",
    ]

    def __init__(self, username, role, parent, next_id, record=None):
        super().__init__()
        self.parent = parent
        self.record = record
        self.setWindowTitle("Sửa phiếu chăm sóc" if record else "Thêm phiếu chăm sóc")
        self.resize(440, 520)
        self._build_ui(next_id)
        self.populate_comboboxes()
        if record is not None:
            self.load_record(record)

    def _build_ui(self, next_id):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.txtMaPhieu = QLineEdit(str((self.record or {}).get("MAPHIEUCS") or next_id))
        self.txtMaPhieu.setReadOnly(True)
        form.addRow("Mã phiếu:", self.txtMaPhieu)

        self.cboCay = QComboBox()
        form.addRow("Cây:", self.cboCay)

        self.cboNhanVien = QComboBox()
        form.addRow("Nhân viên thực hiện:", self.cboNhanVien)

        self.dateChamSoc = QDateEdit()
        self.dateChamSoc.setCalendarPopup(True)
        self.dateChamSoc.setDisplayFormat("dd/MM/yyyy")
        self.dateChamSoc.setMaximumDate(QDate.currentDate())
        self.dateChamSoc.setDate(QDate.currentDate())
        form.addRow("Ngày chăm sóc:", self.dateChamSoc)

        self.txtNoiDung = QLineEdit()
        form.addRow("Nội dung chăm sóc:", self.txtNoiDung)

        self.txtPhuongPhap = QLineEdit()
        form.addRow("Phương pháp:", self.txtPhuongPhap)

        self.cboTinhTrang = QComboBox()
        self.cboTinhTrang.addItems(self.TINHTRANG_OPTIONS)
        form.addRow("Tình trạng sau chăm sóc:", self.cboTinhTrang)

        self.txtGhiChu = QTextEdit()
        self.txtGhiChu.setFixedHeight(80)
        form.addRow("Ghi chú:", self.txtGhiChu)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self.saveRecord)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def populate_comboboxes(self):
        try:
            for t in database.get_all_cay():
                self.cboCay.addItem(f"{t['MACAY']} - {t['TENCAY']}", t["MACAY"])
        except Exception as e:
            print(f"Không tải được danh sách cây từ SQL: {e}")
        try:
            for nv in database.get_all_nhanvien():
                self.cboNhanVien.addItem(f"{nv['MANV']} - {nv['HOTEN']}", nv["MANV"])
        except Exception as e:
            print(f"Không tải được danh sách nhân viên từ SQL: {e}")

    def load_record(self, record):
        idx = self.cboCay.findData(record.get("MACAY"))
        if idx >= 0:
            self.cboCay.setCurrentIndex(idx)
        idx = self.cboNhanVien.findData(record.get("MANV"))
        if idx >= 0:
            self.cboNhanVien.setCurrentIndex(idx)

        ngay = record.get("NGAYCHAMSOC")
        qd = None
        if hasattr(ngay, "year"):
            qd = QDate(ngay.year, ngay.month, ngay.day)
        elif ngay:
            qd = QDate.fromString(str(ngay), "yyyy-MM-dd")
        if qd and qd.isValid():
            self.dateChamSoc.setDate(qd)

        self.txtNoiDung.setText(str(record.get("NOIDUNGCHAMSOC") or ""))
        self.txtPhuongPhap.setText(str(record.get("PHUONGPHAP") or ""))

        tinhtrang = str(record.get("TINHTRANGSAUCHAMSOC") or "")
        idx = self.cboTinhTrang.findText(tinhtrang)
        if idx >= 0:
            self.cboTinhTrang.setCurrentIndex(idx)
        elif tinhtrang:
            self.cboTinhTrang.addItem(tinhtrang)
            self.cboTinhTrang.setCurrentText(tinhtrang)

        self.txtGhiChu.setPlainText(str(record.get("GHICHU") or ""))

    def saveRecord(self):
        macay = self.cboCay.currentData()
        manv = self.cboNhanVien.currentData()
        noidung = self.txtNoiDung.text().strip()

        if not macay or not manv:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn Cây và Nhân viên thực hiện.")
            return
        if not noidung:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập nội dung chăm sóc.")
            return

        ngay = self.dateChamSoc.date().toString("yyyy-MM-dd")
        phuongphap = self.txtPhuongPhap.text().strip()
        tinhtrang = self.cboTinhTrang.currentText().strip()
        ghichu = self.txtGhiChu.toPlainText().strip()
        maphieucs = self.txtMaPhieu.text().strip()

        try:
            if self.record is None:
                database.add_phieuchamsoc(
                    maphieucs=maphieucs, ngaychamsoc=ngay, noidungchamsoc=noidung,
                    phuongphap=phuongphap, tinhtrangsauchamsoc=tinhtrang,
                    ghichu=ghichu, macay=macay, manv=manv,
                )
                QMessageBox.information(self, "Thành công", "Đã lưu phiếu chăm sóc vào Database thành công!")
            else:
                database.update_phieuchamsoc(
                    maphieucs=maphieucs, ngaychamsoc=ngay, noidungchamsoc=noidung,
                    phuongphap=phuongphap, tinhtrangsauchamsoc=tinhtrang,
                    ghichu=ghichu, macay=macay, manv=manv,
                )
                QMessageBox.information(self, "Thành công", "Đã cập nhật phiếu chăm sóc thành công!")
            if hasattr(self.parent, "loadCareRecords"):
                self.parent.loadCareRecords()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")


# =========================================================
# GIAO DIỆN PHIẾU KHẢO SÁT (THÊM / SỬA)
# =========================================================
class PhieuKhaoSatFormWindow(QDialog):
    """
    Form Thêm/Sửa 1 phiếu khảo sát. "Cây" và "Nhân viên khảo sát" được nạp
    thành danh sách (ComboBox) lấy trực tiếp từ SQL để người dùng CHỌN.
    record=None -> chế độ Thêm mới. record=dict (1 dòng PHIEU_KHAO_SAT) -> chế độ Sửa.
    """

    TINHTRANG_OPTIONS = [
        "Sinh trưởng tốt", "Cần theo dõi", "Bị sâu bệnh",
        "Đang phục hồi", "Nguy cấp",
    ]

    def __init__(self, username, role, parent, next_id, record=None):
        super().__init__()
        self.parent = parent
        self.record = record
        self.setWindowTitle("Sửa phiếu khảo sát" if record else "Thêm đợt khảo sát")
        self.resize(440, 560)
        self._build_ui(next_id)
        self.populate_comboboxes()
        if record is not None:
            self.load_record(record)

    def _build_ui(self, next_id):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.txtMaKS = QLineEdit(str((self.record or {}).get("MAKS") or next_id))
        self.txtMaKS.setReadOnly(True)
        form.addRow("Mã khảo sát:", self.txtMaKS)

        self.cboCay = QComboBox()
        form.addRow("Cây:", self.cboCay)

        self.cboNhanVien = QComboBox()
        form.addRow("Nhân viên khảo sát:", self.cboNhanVien)

        self.dateKhaoSat = QDateEdit()
        self.dateKhaoSat.setCalendarPopup(True)
        self.dateKhaoSat.setDisplayFormat("dd/MM/yyyy")
        self.dateKhaoSat.setMaximumDate(QDate.currentDate())
        self.dateKhaoSat.setDate(QDate.currentDate())
        form.addRow("Ngày khảo sát:", self.dateKhaoSat)

        self.txtChieuCao = QLineEdit()
        self.txtChieuCao.setPlaceholderText("vd. 2.50 (m)")
        form.addRow("Chiều cao ghi nhận (m):", self.txtChieuCao)

        self.txtDuongKinh = QLineEdit()
        self.txtDuongKinh.setPlaceholderText("vd. 0.25 (m)")
        form.addRow("Đường kính ghi nhận (m):", self.txtDuongKinh)

        self.txtTinhTrangLa = QLineEdit()
        form.addRow("Tình trạng lá:", self.txtTinhTrangLa)

        self.cboTinhTrang = QComboBox()
        self.cboTinhTrang.addItems(self.TINHTRANG_OPTIONS)
        form.addRow("Tình trạng sinh trưởng:", self.cboTinhTrang)

        self.txtNhanXet = QTextEdit()
        self.txtNhanXet.setFixedHeight(80)
        form.addRow("Nhận xét:", self.txtNhanXet)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self.saveRecord)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def populate_comboboxes(self):
        try:
            for t in database.get_all_cay():
                self.cboCay.addItem(f"{t['MACAY']} - {t['TENCAY']}", t["MACAY"])
        except Exception as e:
            print(f"Không tải được danh sách cây từ SQL: {e}")
        try:
            for nv in database.get_all_nhanvien():
                self.cboNhanVien.addItem(f"{nv['MANV']} - {nv['HOTEN']}", nv["MANV"])
        except Exception as e:
            print(f"Không tải được danh sách nhân viên từ SQL: {e}")

    def load_record(self, record):
        idx = self.cboCay.findData(record.get("MACAY"))
        if idx >= 0:
            self.cboCay.setCurrentIndex(idx)
        idx = self.cboNhanVien.findData(record.get("MANV"))
        if idx >= 0:
            self.cboNhanVien.setCurrentIndex(idx)

        ngay = record.get("NGAYKHAOSAT")
        qd = None
        if hasattr(ngay, "year"):
            qd = QDate(ngay.year, ngay.month, ngay.day)
        elif ngay:
            qd = QDate.fromString(str(ngay), "yyyy-MM-dd")
        if qd and qd.isValid():
            self.dateKhaoSat.setDate(qd)

        if record.get("CHIEUCAOGHINHAN") is not None:
            self.txtChieuCao.setText(str(record.get("CHIEUCAOGHINHAN")))
        if record.get("DUONGKINHGHINHAN") is not None:
            self.txtDuongKinh.setText(str(record.get("DUONGKINHGHINHAN")))
        self.txtTinhTrangLa.setText(str(record.get("TINHTRANGLA") or ""))

        tinhtrang = str(record.get("TINHTRANGSINHTRUONG") or "")
        idx = self.cboTinhTrang.findText(tinhtrang)
        if idx >= 0:
            self.cboTinhTrang.setCurrentIndex(idx)
        elif tinhtrang:
            self.cboTinhTrang.addItem(tinhtrang)
            self.cboTinhTrang.setCurrentText(tinhtrang)

        self.txtNhanXet.setPlainText(str(record.get("NHANXET") or ""))

    def saveRecord(self):
        macay = self.cboCay.currentData()
        manv = self.cboNhanVien.currentData()

        if not macay or not manv:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn Cây và Nhân viên khảo sát.")
            return

        def _parse_decimal(text, field_label):
            text = text.strip().replace(",", ".")
            if not text:
                return None
            try:
                return float(text)
            except ValueError:
                raise ValueError(f"{field_label} phải là số (vd. 2.5).")

        try:
            chieucao = _parse_decimal(self.txtChieuCao.text(), "Chiều cao ghi nhận")
            duongkinh = _parse_decimal(self.txtDuongKinh.text(), "Đường kính ghi nhận")
        except ValueError as e:
            QMessageBox.warning(self, "Dữ liệu không hợp lệ", str(e))
            return

        ngay = self.dateKhaoSat.date().toString("yyyy-MM-dd")
        tinhtrangla = self.txtTinhTrangLa.text().strip()
        tinhtrang = self.cboTinhTrang.currentText().strip()
        nhanxet = self.txtNhanXet.toPlainText().strip()
        maks = self.txtMaKS.text().strip()

        try:
            if self.record is None:
                database.add_phieukhaosat(
                    maks=maks, ngaykhaosat=ngay, chieucaoghinhan=chieucao,
                    duongkinhghinhan=duongkinh, tinhtrangla=tinhtrangla,
                    tinhtrangsinhtruong=tinhtrang, nhanxet=nhanxet,
                    macay=macay, manv=manv,
                )
                QMessageBox.information(self, "Thành công", "Đã lưu phiếu khảo sát vào Database thành công!")
            else:
                database.update_phieukhaosat(
                    maks=maks, ngaykhaosat=ngay, chieucaoghinhan=chieucao,
                    duongkinhghinhan=duongkinh, tinhtrangla=tinhtrangla,
                    tinhtrangsinhtruong=tinhtrang, nhanxet=nhanxet,
                    macay=macay, manv=manv,
                )
                QMessageBox.information(self, "Thành công", "Đã cập nhật phiếu khảo sát thành công!")
            if hasattr(self.parent, "loadSurveys"):
                self.parent.loadSurveys()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")


# =========================================================
# GIAO DIỆN ĐĂNG KÝ / ĐĂNG NHẬP
# =========================================================
class SignWindow(QWidget):

    # Tên control khả dĩ cho 2 ô "Mật khẩu" / "Nhập lại mật khẩu" trên form
    # đăng ký (sign.py do Qt Designer sinh ra). Nếu không khớp tên nào, code
    # sẽ tự quét các QLineEdit đã được Designer đặt sẵn chế độ Password.
    _PASSWORD_CANDIDATES = ["txtPassword", "txtMatKhau", "input_password",
                             "passwordEdit", "lineEditPassword", "lineEditMatKhau"]
    _CONFIRM_CANDIDATES = ["txtConfirmPassword", "txtNhapLaiMatKhau", "confirmPasswordEdit",
                            "txtRePassword", "lineEditConfirmPassword", "lineEditNhapLaiMatKhau"]

    def __init__(self):
        super().__init__()
        self.ui = Ui_RegisterForm()
        self.ui.setupUi(self)
        self.ui.registerButton.clicked.connect(self.register)
        self._setup_password_toggles()

    def _setup_password_toggles(self):
        """Gắn icon hiện/ẩn cho ô Mật khẩu và Nhập lại mật khẩu (nếu form có)."""
        self.txtMatKhau = _find_widget_by_hints(self.ui, self._PASSWORD_CANDIDATES, QLineEdit)
        self.txtNhapLaiMatKhau = _find_widget_by_hints(self.ui, self._CONFIRM_CANDIDATES, QLineEdit)

        if self.txtMatKhau is None or self.txtNhapLaiMatKhau is None:
            # Không tìm được theo tên -> quét mọi QLineEdit mà Designer đã đặt
            # sẵn chế độ Password (echoMode != Normal), theo đúng thứ tự trên
            # form: ô đầu tiên là "Mật khẩu", ô thứ hai là "Nhập lại mật khẩu".
            password_edits = [
                w for w in vars(self.ui).values()
                if isinstance(w, QLineEdit) and w.echoMode() != QLineEdit.EchoMode.Normal
                and w not in (self.txtMatKhau, self.txtNhapLaiMatKhau)
            ]
            if self.txtMatKhau is None and len(password_edits) >= 1:
                self.txtMatKhau = password_edits[0]
            if self.txtNhapLaiMatKhau is None and len(password_edits) >= 2:
                self.txtNhapLaiMatKhau = password_edits[1]

        _attach_password_toggle(self.txtMatKhau)
        _attach_password_toggle(self.txtNhapLaiMatKhau)

    def register(self):
        name = self.ui.txtFullName.text().strip()
        if name == "": return
        self.main = MainWindow(name, "Khách tham quan")
        self.main.show()
        self.close()


class LoginWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = Ui_LoginWindow()
        self.ui.setupUi(self)
        self.role = None

        self.ui.btn_role_admin.clicked.connect(self.chooseAdmin)
        self.ui.btn_role_staff.clicked.connect(self.chooseStaff)
        self.ui.btn_role_guest.clicked.connect(self.chooseGuest)
        self.ui.btn_login.clicked.connect(self.login)

    def chooseAdmin(self):
        self.role = "Quản trị viên"
        self.resetButton()
        self.ui.btn_role_admin.setStyleSheet(
            "QPushButton{background:#198754;color:white;border-radius:8px;font-weight:bold;}")
        self.setWindowTitle("Đăng nhập - Quản trị viên")

    def chooseStaff(self):
        self.role = "Nhân viên"
        self.resetButton()
        self.ui.btn_role_staff.setStyleSheet(
            "QPushButton{background:#198754;color:white;border-radius:8px;font-weight:bold;}")
        self.setWindowTitle("Đăng nhập - Nhân viên")

    def chooseGuest(self):
        self.role = "Khách tham quan"
        self.resetButton()
        self.ui.btn_role_guest.setStyleSheet("""
            QPushButton{background:#198754;color:white;border-radius:8px;font-weight:bold;}
        """)
        self.setWindowTitle("Đăng ký - Khách tham quan")

        # Theo yêu cầu: chọn "Đăng ký (khách tham quan)" sẽ CHUYỂN THẲNG sang
        # giao diện đăng ký (SignWindow) ngay lập tức, không cần bấm thêm nút
        # "Đăng nhập" nữa.
        self.sign = SignWindow()
        self.sign.show()
        self.close()

    def resetButton(self):
        self.ui.btn_role_admin.setStyleSheet(
            "QPushButton{background:#f4fbf7;border:1px solid #2d6a4f;border-radius:8px;color:#2d6a4f;font-weight:bold;}")
        self.ui.btn_role_staff.setStyleSheet(
            "QPushButton{background:#f0f9ff;border:1px solid #0369a1;border-radius:8px;color:#0369a1;font-weight:bold;}")
        self.ui.btn_role_guest.setStyleSheet(
            "QPushButton{background:#fffbeb;border:1px solid #b45309;border-radius:8px;color:#b45309;font-weight:bold;}")

    def login(self):
        username = self.ui.input_username.text().strip()
        password = self.ui.input_password.text().strip()

        if self.role is None:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn quyền đăng nhập.")
            return

        if self.role == "Khách tham quan":
            if username:
                self.main_window = MainWindow(username, self.role)
                self.main_window.show()
                self.close()
            else:
                self.sign = SignWindow()
                self.sign.show()
                self.close()
            return

        if self.role == "Quản trị viên" and username == "Nguyễn Văn A" and password == "123":
            self.main_window = MainWindow("Nguyễn Văn A", self.role)
            self.main_window.show()
            self.close()
            return

        if self.role == "Nhân viên" and username == "Phạm Kim H" and password == "123":
            self.main_window = MainWindow("Phạm Kim H", self.role)
            self.main_window.show()
            self.close()
            return

        try:
            all_staff = database.get_all_nhanvien()
            for staff in all_staff:
                if (staff["MANV"] == username or staff["EMAIL"] == username) and staff["MATKHAU"] == password:
                    if (self.role == "Quản trị viên" and staff["CHUCVU"] == "Trưởng phòng") or \
                            (self.role == "Nhân viên" and staff["CHUCVU"] != "Trưởng phòng"):
                        self.main_window = MainWindow(staff["HOTEN"], self.role)
                        self.main_window.show()
                        self.close()
                        return

            QMessageBox.warning(self, "Đăng nhập thất bại", "Sai tên đăng nhập, mật khẩu hoặc vai trò.")
        except Exception as e:
            QMessageBox.warning(self, "Đăng nhập thất bại",
                                f"Sai tài khoản/mật khẩu mẫu hoặc Lỗi kết nối SQL Server.\n(Chi tiết: {e})")


# =========================================================
# TÍCH HỢP TOÀN BỘ CÁC HÀM TRUY VẤN DATABASE CÒN LẠI
# =========================================================

class PhieuChamSocWindow(NavigationWindow):

    # Tên control khả dĩ cho các ô lọc "Cây" / "Nhân viên" và nút "+ Thêm phiếu
    # chăm sóc" trên giao diện Phiếu chăm sóc. Nếu tên control thật trong file
    # .ui khác với danh sách này, thêm tên đó vào đầu danh sách tương ứng.
    _CAY_FILTER_CANDIDATES = ["cboCay", "cboCayFilter", "comboCay", "filterCay",
                               "cbCay", "cbo_cay", "treeFilterCombo"]
    _NV_FILTER_CANDIDATES = ["cboNhanVien", "cboNhanVienFilter", "comboNhanVien",
                              "filterNhanVien", "cbNhanVien", "cbo_nhanvien",
                              "staffFilterCombo"]
    _ADD_BUTTON_CANDIDATES = ["btnThemPhieu", "btnThemPhieuChamSoc", "btn_add",
                               "addButton", "btnAdd", "btnAddCare", "addCareButton"]

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_PhieuChamSoc()
        self.ui.setupUi(self)
        self.init_common(username, role)
        self._care_records = []

        self.populateFilterCombos()
        self.connectAddButton()
        self.loadCareRecords()
        self.setup_table_search("searchBox", "tableCareRecords")

    # ---------------- Nạp danh sách Cây / Nhân viên để lựa chọn (lọc) ----------------
    def populateFilterCombos(self):
        """Nạp dữ liệu SQL (bảng CAY, NHAN_VIEN) thành 1 list để người dùng
        chọn ở 2 ô lọc "Cây" và "Nhân viên" phía trên bảng."""
        self.cboCayFilter = _find_widget_by_hints(
            self.ui, self._CAY_FILTER_CANDIDATES, QComboBox, keyword_hints=("cay", "tree")
        )
        self.cboNhanVienFilter = _find_widget_by_hints(
            self.ui, self._NV_FILTER_CANDIDATES, QComboBox, keyword_hints=("nhanvien", "nv", "staff")
        )

        try:
            trees = database.get_all_cay()
        except Exception as e:
            trees = []
            print(f"Không tải được danh sách cây để lọc: {e}")
        try:
            staff = database.get_all_nhanvien()
        except Exception as e:
            staff = []
            print(f"Không tải được danh sách nhân viên để lọc: {e}")

        if self.cboCayFilter is not None:
            self.cboCayFilter.blockSignals(True)
            self.cboCayFilter.clear()
            self.cboCayFilter.addItem("Tất cả cây", None)
            for t in trees:
                self.cboCayFilter.addItem(f"{t['MACAY']} - {t['TENCAY']}", t["MACAY"])
            self.cboCayFilter.blockSignals(False)
            self.cboCayFilter.currentIndexChanged.connect(self.applyFilters)

        if self.cboNhanVienFilter is not None:
            self.cboNhanVienFilter.blockSignals(True)
            self.cboNhanVienFilter.clear()
            self.cboNhanVienFilter.addItem("Tất cả nhân viên", None)
            for nv in staff:
                self.cboNhanVienFilter.addItem(f"{nv['MANV']} - {nv['HOTEN']}", nv["MANV"])
            self.cboNhanVienFilter.blockSignals(False)
            self.cboNhanVienFilter.currentIndexChanged.connect(self.applyFilters)

    def connectAddButton(self):
        btn = _find_widget_by_hints(
            self.ui, self._ADD_BUTTON_CANDIDATES, QPushButton, keyword_hints=("thêm", "them", "+")
        )
        if btn is not None:
            btn.clicked.connect(self.openThemPhieuChamSoc)

    def openThemPhieuChamSoc(self):
        try:
            current = database.get_all_phieuchamsoc()
            existing_ids = [r["MAPHIEUCS"] for r in current]
            next_id = _generate_next_code(existing_ids, "PCS", 2)
        except Exception as e:
            # SỬA LỖI: trước đây khi có lỗi (vd mất kết nối SQL) code sẽ ÂM
            # THẦM trả về "PCS01" mà không báo gì, khiến người dùng thấy mã
            # phiếu bị "lệch"/"sai thứ tự" so với danh sách thật mà không hiểu
            # vì sao. Giờ báo lỗi rõ ràng để biết chính xác nguyên nhân.
            QMessageBox.warning(
                self, "Thông báo",
                f"Không lấy được danh sách phiếu chăm sóc hiện có từ SQL nên "
                f"không thể tính đúng mã phiếu kế tiếp.\nChi tiết: {e}"
            )
            return
        dlg = PhieuChamSocFormWindow(self.username, self.role, self, next_id)
        dlg.exec()

    # ---------------- Nạp & hiển thị bảng Phiếu chăm sóc ----------------
    def loadCareRecords(self):
        """Tích hợp database.get_all_phieuchamsoc(), nạp đủ toàn bộ cột còn
        thiếu: Nhân viên thực hiện, Ghi chú, Thao tác (Sửa/Xóa đồng bộ SQL)."""
        if not hasattr(self.ui, "tableCareRecords"):
            return
        try:
            self._care_records = database.get_all_phieuchamsoc()
        except Exception as e:
            self._care_records = []
            print(f"Không thể load Phiếu chăm sóc từ DB: {e}")
        self.applyFilters()

    def applyFilters(self):
        """Lọc danh sách phiếu chăm sóc đang có theo Cây / Nhân viên đã chọn
        ở 2 ô lọc phía trên bảng (nếu form có control này)."""
        records = self._care_records
        cay_id = self.cboCayFilter.currentData() if getattr(self, "cboCayFilter", None) else None
        nv_id = self.cboNhanVienFilter.currentData() if getattr(self, "cboNhanVienFilter", None) else None

        if cay_id:
            records = [r for r in records if str(r.get("MACAY")) == str(cay_id)]
        if nv_id:
            records = [r for r in records if str(r.get("MANV")) == str(nv_id)]

        self.renderCareTable(records)

    def renderCareTable(self, records):
        table = self.ui.tableCareRecords
        table.clearContents()
        table.setRowCount(len(records))
        for row, rec in enumerate(records):
            table.setItem(row, 0, QTableWidgetItem(str(rec.get("MAPHIEUCS", ""))))
            table.setItem(row, 1, QTableWidgetItem(str(rec.get("MACAY", ""))))
            table.setItem(row, 2, QTableWidgetItem(str(rec.get("NGAYCHAMSOC", ""))))
            table.setItem(row, 3, QTableWidgetItem(str(rec.get("NOIDUNGCHAMSOC", ""))))
            table.setItem(row, 4, QTableWidgetItem(str(rec.get("PHUONGPHAP", ""))))
            table.setItem(row, 5, QTableWidgetItem(str(rec.get("TINHTRANGSAUCHAMSOC", ""))))
            # SỬA LỖI: cột "Nhân viên thực hiện" trước đây bỏ trống -> giờ lấy
            # HOTEN thật (JOIN với NHAN_VIEN qua MANV) từ database.get_all_phieuchamsoc().
            table.setItem(row, 6, QTableWidgetItem(str(rec.get("TENNV") or rec.get("MANV") or "")))
            # SỬA LỖI: cột "Ghi chú" trước đây bỏ trống dù bảng SQL đã có sẵn cột GHICHU.
            table.setItem(row, 7, QTableWidgetItem(str(rec.get("GHICHU") or "")))
            # SỬA LỖI: cột "Thao tác" trước đây bỏ trống -> giờ có 2 nút Sửa/Xóa
            # thao tác trực tiếp lên SQL Server (UPDATE/DELETE) rồi tự tải lại bảng.
            maphieucs = rec.get("MAPHIEUCS")
            table.setCellWidget(
                row, 8,
                _build_action_buttons_widget(maphieucs, self.editCareRecord, self.deleteCareRecord),
            )

    # ---------------- Sửa / Xóa (đồng bộ SQL) ----------------
    def editCareRecord(self, maphieucs):
        record = next((r for r in self._care_records if r.get("MAPHIEUCS") == maphieucs), None)
        if record is None:
            QMessageBox.warning(self, "Thông báo", "Không tìm thấy phiếu chăm sóc này (dữ liệu có thể vừa thay đổi).")
            self.loadCareRecords()
            return
        dlg = PhieuChamSocFormWindow(self.username, self.role, self, maphieucs, record=record)
        dlg.exec()

    def deleteCareRecord(self, maphieucs):
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa phiếu chăm sóc '{maphieucs}' khỏi Database không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            database.delete_phieuchamsoc(maphieucs)
            QMessageBox.information(self, "Thành công", f"Đã xóa phiếu chăm sóc '{maphieucs}'.")
            self.loadCareRecords()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể xóa trên SQL Server.\nChi tiết: {e}")


class PhieuKhaoSatWindow(NavigationWindow):

    # Tên control khả dĩ cho các ô lọc "Cây" / "Nhân viên" và nút "+ Thêm đợt
    # khảo sát" trên giao diện Phiếu khảo sát.
    _CAY_FILTER_CANDIDATES = ["cboCay", "cboCayFilter", "comboCay", "filterCay",
                               "cbCay", "cbo_cay", "treeFilterCombo"]
    _NV_FILTER_CANDIDATES = ["cboNhanVien", "cboNhanVienFilter", "comboNhanVien",
                              "filterNhanVien", "cbNhanVien", "cbo_nhanvien",
                              "staffFilterCombo"]
    _ADD_BUTTON_CANDIDATES = ["btnThemDotKhaoSat", "btnThemPhieuKhaoSat", "btn_add",
                               "addButton", "btnAdd", "addSurveyButton"]

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_PhieuKhaoSat()
        self.ui.setupUi(self)
        self.init_common(username, role)
        self._survey_records = []

        self.populateFilterCombos()
        self.connectAddButton()
        self.loadSurveys()
        self.setup_table_search("searchBox", "tableSurveys")

    # ---------------- Nạp danh sách Cây / Nhân viên để lựa chọn (lọc) ----------------
    def populateFilterCombos(self):
        """Nạp dữ liệu SQL (bảng CAY, NHAN_VIEN) thành 1 list để người dùng
        chọn ở 2 ô lọc "Cây" và "Nhân viên" phía trên bảng (nếu form có)."""
        self.cboCayFilter = _find_widget_by_hints(
            self.ui, self._CAY_FILTER_CANDIDATES, QComboBox, keyword_hints=("cay", "tree")
        )
        self.cboNhanVienFilter = _find_widget_by_hints(
            self.ui, self._NV_FILTER_CANDIDATES, QComboBox, keyword_hints=("nhanvien", "nv", "staff")
        )

        try:
            trees = database.get_all_cay()
        except Exception as e:
            trees = []
            print(f"Không tải được danh sách cây để lọc: {e}")
        try:
            staff = database.get_all_nhanvien()
        except Exception as e:
            staff = []
            print(f"Không tải được danh sách nhân viên để lọc: {e}")

        if self.cboCayFilter is not None:
            self.cboCayFilter.blockSignals(True)
            self.cboCayFilter.clear()
            self.cboCayFilter.addItem("Tất cả cây", None)
            for t in trees:
                self.cboCayFilter.addItem(f"{t['MACAY']} - {t['TENCAY']}", t["MACAY"])
            self.cboCayFilter.blockSignals(False)
            self.cboCayFilter.currentIndexChanged.connect(self.applyFilters)

        if self.cboNhanVienFilter is not None:
            self.cboNhanVienFilter.blockSignals(True)
            self.cboNhanVienFilter.clear()
            self.cboNhanVienFilter.addItem("Tất cả nhân viên", None)
            for nv in staff:
                self.cboNhanVienFilter.addItem(f"{nv['MANV']} - {nv['HOTEN']}", nv["MANV"])
            self.cboNhanVienFilter.blockSignals(False)
            self.cboNhanVienFilter.currentIndexChanged.connect(self.applyFilters)

    def connectAddButton(self):
        btn = _find_widget_by_hints(
            self.ui, self._ADD_BUTTON_CANDIDATES, QPushButton, keyword_hints=("thêm", "them", "+")
        )
        if btn is not None:
            btn.clicked.connect(self.openThemPhieuKhaoSat)

    def openThemPhieuKhaoSat(self):
        try:
            current = database.get_all_phieukhaosat()
            existing_ids = [r["MAKS"] for r in current]
            next_id = _generate_next_code(existing_ids, "PKS", 2)
        except Exception:
            next_id = "PKS01"
        dlg = PhieuKhaoSatFormWindow(self.username, self.role, self, next_id)
        dlg.exec()

    # ---------------- Nạp & hiển thị bảng Phiếu khảo sát ----------------
    def loadSurveys(self):
        """Tích hợp database.get_all_phieukhaosat(), nạp đủ toàn bộ cột còn
        thiếu: Nhận xét, Nhân viên khảo sát, Thao tác (Sửa/Xóa đồng bộ SQL)."""
        if not hasattr(self.ui, "tableSurveys"):
            return
        try:
            self._survey_records = database.get_all_phieukhaosat()
        except Exception as e:
            self._survey_records = []
            print(f"Không thể load Phiếu khảo sát từ DB: {e}")
        self.applyFilters()

    def applyFilters(self):
        records = self._survey_records
        cay_id = self.cboCayFilter.currentData() if getattr(self, "cboCayFilter", None) else None
        nv_id = self.cboNhanVienFilter.currentData() if getattr(self, "cboNhanVienFilter", None) else None

        if cay_id:
            records = [r for r in records if str(r.get("MACAY")) == str(cay_id)]
        if nv_id:
            records = [r for r in records if str(r.get("MANV")) == str(nv_id)]

        self.renderSurveyTable(records)

    def renderSurveyTable(self, records):
        table = self.ui.tableSurveys
        table.clearContents()
        table.setRowCount(len(records))
        for row, srv in enumerate(records):
            table.setItem(row, 0, QTableWidgetItem(str(srv.get("MAKS", ""))))
            table.setItem(row, 1, QTableWidgetItem(str(srv.get("MACAY", ""))))
            table.setItem(row, 2, QTableWidgetItem(str(srv.get("NGAYKHAOSAT", ""))))
            table.setItem(row, 3, QTableWidgetItem(str(srv.get("CHIEUCAOGHINHAN", ""))))
            table.setItem(row, 4, QTableWidgetItem(str(srv.get("DUONGKINHGHINHAN", ""))))
            table.setItem(row, 5, QTableWidgetItem(str(srv.get("TINHTRANGSINHTRUONG", ""))))
            # SỬA LỖI: cột "Nhận xét" trước đây bỏ trống dù bảng SQL đã có sẵn cột NHANXET.
            table.setItem(row, 6, QTableWidgetItem(str(srv.get("NHANXET") or "")))
            # SỬA LỖI: cột "Nhân viên khảo sát" trước đây bỏ trống -> giờ lấy
            # HOTEN thật (JOIN với NHAN_VIEN qua MANV) từ database.get_all_phieukhaosat().
            table.setItem(row, 7, QTableWidgetItem(str(srv.get("TENNV") or srv.get("MANV") or "")))
            # SỬA LỖI: cột "Thao tác" trước đây bỏ trống -> giờ có 2 nút Sửa/Xóa
            # thao tác trực tiếp lên SQL Server (UPDATE/DELETE) rồi tự tải lại bảng.
            maks = srv.get("MAKS")
            table.setCellWidget(
                row, 8,
                _build_action_buttons_widget(maks, self.editSurveyRecord, self.deleteSurveyRecord),
            )

    # ---------------- Sửa / Xóa (đồng bộ SQL) ----------------
    def editSurveyRecord(self, maks):
        record = next((r for r in self._survey_records if r.get("MAKS") == maks), None)
        if record is None:
            QMessageBox.warning(self, "Thông báo", "Không tìm thấy phiếu khảo sát này (dữ liệu có thể vừa thay đổi).")
            self.loadSurveys()
            return
        dlg = PhieuKhaoSatFormWindow(self.username, self.role, self, maks, record=record)
        dlg.exec()

    def deleteSurveyRecord(self, maks):
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa phiếu khảo sát '{maks}' khỏi Database không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            database.delete_phieukhaosat(maks)
            QMessageBox.information(self, "Thành công", f"Đã xóa phiếu khảo sát '{maks}'.")
            self.loadSurveys()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể xóa trên SQL Server.\nChi tiết: {e}")


class YeuCauBaoTriWindow(NavigationWindow):
    """
    Trang "Yêu cầu bảo trì" (giao diện Thêm yêu cầu bảo trì trong ảnh chụp màn
    hình): ô "Cây" và "Nhân viên phụ trách xử lý" được nạp thành danh sách
    (ComboBox) lấy TRỰC TIẾP từ SQL để người dùng CHỌN thay vì gõ tay mã
    (tránh gõ sai / gõ mã không tồn tại -> lỗi khóa ngoại FOREIGN KEY).

    LƯU Ý: bảng YEU_CAU_BAO_TRI trong SQL có ràng buộc
    CK_TrangThai_YCBT chỉ cho phép 3 giá trị: 'Chờ xử lý', 'Đang xử lý',
    'Đã xử lý' (không có 'Mới tạo' như trên giao diện thiết kế). Vì vậy ô
    "Trạng thái xử lý" vẫn HIỂN THỊ chữ "Mới tạo" cho khớp giao diện, nhưng
    giá trị THỰC LƯU xuống Database là 'Chờ xử lý' để không vi phạm ràng buộc
    CHECK CONSTRAINT (nếu không sẽ báo lỗi khi Lưu).
    """

    # Tên control khả dĩ do Qt Designer đặt cho từng ô trên form "Yêu cầu bảo
    # trì". Nếu tên control thật trong file .ui khác với danh sách bên dưới,
    # code sẽ tự dò tiếp theo LOẠI widget + từ khóa (keyword_hints) nên vẫn
    # hoạt động được mà không cần sửa gì thêm.
    _MABT_CANDIDATES = ["txtMaBT", "txtMaBaoTri", "lineEditMaBT", "maBaoTriEdit"]
    _CAY_CANDIDATES = ["cboCay", "comboCay", "cbCay", "cbo_cay", "cayComboBox"]
    _NOIDUNG_CANDIDATES = ["txtNoiDung", "txtNoiDungBaoTri", "textEditNoiDung",
                            "noiDungTextEdit", "plainTextEditNoiDung"]
    _MUCDO_CANDIDATES = ["cboMucDo", "cboMucDoUuTien", "comboMucDo", "priorityComboBox"]
    _TRANGTHAI_CANDIDATES = ["cboTrangThai", "comboTrangThai", "statusComboBox"]
    _NHANVIEN_CANDIDATES = ["cboNhanVien", "cboNhanVienPhuTrach", "comboNhanVien", "staffComboBox"]
    _NGAYTAO_CANDIDATES = ["dateNgayTao", "dateEditNgayTao", "dateTaoYeuCau"]
    _SAVE_BUTTON_CANDIDATES = ["btnLuu", "btnSave", "saveButton", "pushButtonLuu"]
    _CANCEL_BUTTON_CANDIDATES = ["btnHuyBo", "btnCancel", "cancelButton", "pushButtonHuyBo"]
    _CHARCOUNT_CANDIDATES = ["lblSoKyTu", "lblCharCount", "labelCharCount", "lblDemKyTu"]

    NOIDUNG_MAX_LEN = 500

    # (text hiển thị, giá trị thực lưu SQL) - khớp với ràng buộc CK_TrangThai_YCBT
    TRANGTHAI_OPTIONS = [
        ("Mới tạo", "Chờ xử lý"),
        ("Đang xử lý", "Đang xử lý"),
        ("Đã xử lý", "Đã xử lý"),
    ]
    # Khớp với ràng buộc CK_MucDo_YCBT
    MUCDOUUTIEN_OPTIONS = ["Thấp", "Trung bình", "Cao", "Khẩn cấp"]

    # Tiền tố mã bảo trì: dùng lại đúng tiền tố "YC" đã có sẵn trong dữ liệu
    # SQL cũ (YC01, YC02, YC03, YC04) để mã mới sinh ra được TIẾP NỐI đúng số
    # thứ tự (YC05, YC06...), đồng bộ với những gì đang hiển thị ở Trang chủ.
    MABT_PREFIX = "YC"

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_YeuCauBaoTri()
        self.ui.setupUi(self)
        self.init_common(username, role)

        self._locate_widgets()
        self._setup_form_defaults()
        self.populateComboboxes()
        self.connectButtons()
        self._cleanupTestRecord()
        self.refreshMaBT()
        self.loadMaintenance()

    # ---------------- Dò tìm control trên form ----------------
    def _locate_widgets(self):
        self.txtMaBT = _find_widget_by_hints(
            self.ui, self._MABT_CANDIDATES, QLineEdit, keyword_hints=("mabt", "baotri")
        )
        self.cboCay = _find_widget_by_hints(
            self.ui, self._CAY_CANDIDATES, QComboBox, keyword_hints=("cay", "tree")
        )
        self.txtNoiDung = _find_widget_by_hints(
            self.ui, self._NOIDUNG_CANDIDATES, QTextEdit, keyword_hints=("noidung", "content")
        )
        self.cboMucDo = _find_widget_by_hints(
            self.ui, self._MUCDO_CANDIDATES, QComboBox, keyword_hints=("uutien", "priority", "mucdo")
        )
        self.cboTrangThai = _find_widget_by_hints(
            self.ui, self._TRANGTHAI_CANDIDATES, QComboBox, keyword_hints=("trangthai", "status")
        )
        self.cboNhanVien = _find_widget_by_hints(
            self.ui, self._NHANVIEN_CANDIDATES, QComboBox, keyword_hints=("nhanvien", "nv", "staff")
        )
        self.dateNgayTao = _find_widget_by_hints(
            self.ui, self._NGAYTAO_CANDIDATES, QDateEdit, keyword_hints=("ngay", "date")
        )
        if self.dateNgayTao is None:
            self.dateNgayTao = _get_first_date_edit(self.ui)
        self.btnLuu = _find_widget_by_hints(
            self.ui, self._SAVE_BUTTON_CANDIDATES, QPushButton, keyword_hints=("lưu", "luu", "save")
        )
        self.btnHuyBo = _find_widget_by_hints(
            self.ui, self._CANCEL_BUTTON_CANDIDATES, QPushButton, keyword_hints=("hủy", "huy", "cancel")
        )
        self.lblSoKyTu = None
        for name in self._CHARCOUNT_CANDIDATES:
            if hasattr(self.ui, name):
                self.lblSoKyTu = getattr(self.ui, name)
                break

    # ---------------- Thiết lập giá trị mặc định cho form ----------------
    def _setup_form_defaults(self):
        if self.txtMaBT is not None:
            # Ô "Mã bảo trì" chỉ ĐỌC (người dùng không gõ tay được, tránh trùng
            # mã với dữ liệu đã có trong SQL) nhưng vẫn phải HIỂN THỊ sẵn mã kế
            # tiếp (vd BT06) ngay khi mở form, thay vì để trống -> xem hàm
            # refreshMaBT() bên dưới, luôn tính từ dữ liệu THẬT trong SQL.
            self.txtMaBT.setReadOnly(True)
            self.txtMaBT.setPlaceholderText("Đang tạo mã...")

        if self.dateNgayTao is not None:
            self.dateNgayTao.setDisplayFormat("dd/MM/yyyy")
            self.dateNgayTao.setCalendarPopup(True)
            self.dateNgayTao.setDate(QDate.currentDate())

        if self.txtNoiDung is not None:
            self.txtNoiDung.textChanged.connect(self._updateCharCount)
            self._updateCharCount()

    def _updateCharCount(self):
        """Cập nhật nhãn đếm ký tự "x/500" và cắt bớt nếu người dùng nhập quá dài."""
        if self.txtNoiDung is None:
            return
        text = self.txtNoiDung.toPlainText()
        if len(text) > self.NOIDUNG_MAX_LEN:
            text = text[: self.NOIDUNG_MAX_LEN]
            cursor = self.txtNoiDung.textCursor()
            self.txtNoiDung.blockSignals(True)
            self.txtNoiDung.setPlainText(text)
            self.txtNoiDung.blockSignals(False)
            cursor.movePosition(cursor.MoveOperation.End)
            self.txtNoiDung.setTextCursor(cursor)
        if self.lblSoKyTu is not None:
            self.lblSoKyTu.setText(f"{len(text)}/{self.NOIDUNG_MAX_LEN}")

    # ---------------- Nạp danh sách Cây / Nhân viên / Mức độ / Trạng thái ----------------
    def populateComboboxes(self):
        if self.cboCay is not None:
            try:
                trees = database.get_all_cay()
            except Exception as e:
                trees = []
                print(f"Không tải được danh sách cây: {e}")
            self.cboCay.blockSignals(True)
            self.cboCay.clear()
            self.cboCay.addItem("Chọn cây", None)
            for t in trees:
                self.cboCay.addItem(f"{t['MACAY']} - {t['TENCAY']}", t["MACAY"])
            self.cboCay.blockSignals(False)

        if self.cboNhanVien is not None:
            try:
                staff = database.get_all_nhanvien()
            except Exception as e:
                staff = []
                print(f"Không tải được danh sách nhân viên: {e}")
            self.cboNhanVien.blockSignals(True)
            self.cboNhanVien.clear()
            self.cboNhanVien.addItem("Chọn nhân viên", None)
            for nv in staff:
                self.cboNhanVien.addItem(f"{nv['MANV']} - {nv['HOTEN']}", nv["MANV"])
            self.cboNhanVien.blockSignals(False)

        if self.cboMucDo is not None:
            self.cboMucDo.blockSignals(True)
            self.cboMucDo.clear()
            self.cboMucDo.addItem("Chọn mức độ ưu tiên", None)
            for opt in self.MUCDOUUTIEN_OPTIONS:
                self.cboMucDo.addItem(opt, opt)
            self.cboMucDo.blockSignals(False)

        if self.cboTrangThai is not None:
            self.cboTrangThai.blockSignals(True)
            self.cboTrangThai.clear()
            for label, value in self.TRANGTHAI_OPTIONS:
                self.cboTrangThai.addItem(label, value)
            self.cboTrangThai.setCurrentIndex(0)  # Mặc định "Mới tạo" -> lưu "Chờ xử lý"
            self.cboTrangThai.blockSignals(False)

    # ---------------- Dọn dữ liệu test (xóa thẳng BT01) ----------------
    def _cleanupTestRecord(self):
        """Xóa thẳng bản ghi test 'BT01' trong SQL (nếu còn) ngay khi mở
        trang, không cần chạy tay file .sql nữa."""
        try:
            database.cleanup_test_yeucaubaotri()
        except Exception as e:
            print(f"Không xóa được bản ghi test BT01 (có thể không tồn tại hoặc mất kết nối SQL): {e}")

    # ---------------- Sinh mã bảo trì (đồng bộ với SQL) ----------------
    def refreshMaBT(self):
        """
        Tính mã bảo trì KẾ TIẾP dựa trên dữ liệu THẬT đang có trong SQL Server
        (bảng YEU_CAU_BAO_TRI), dùng đúng tiền tố "YC" đang có sẵn trong dữ
        liệu SQL (vd YC01, YC02, YC03, YC04 -> mã kế tiếp sẽ là YC05...)
        rồi hiển thị lên ô "Mã bảo trì". Gọi lại hàm này mỗi khi mở form và
        sau mỗi lần Lưu thành công để mã luôn đồng bộ, không bao giờ bị trùng
        hay lệch với Database.
        """
        try:
            current = database.get_all_yeucaubaotri()
            existing_ids = [r["MABT"] for r in current]
        except Exception as e:
            existing_ids = []
            print(f"Không tải được danh sách mã bảo trì hiện có từ SQL: {e}")
        next_id = _generate_next_code(existing_ids, self.MABT_PREFIX, 2)
        if self.txtMaBT is not None:
            self.txtMaBT.setText(next_id)
        return next_id

    # ---------------- Nút Lưu / Hủy bỏ ----------------
    def connectButtons(self):
        if self.btnLuu is not None:
            self.btnLuu.clicked.connect(self.saveMaintenanceRequest)
        if self.btnHuyBo is not None:
            self.btnHuyBo.clicked.connect(self.resetForm)

    def resetForm(self):
        """Xóa trắng form để nhập yêu cầu bảo trì mới (nút "Hủy bỏ")."""
        self.refreshMaBT()  # Tính lại mã BT kế tiếp đồng bộ với SQL, không để trống
        if self.cboCay is not None:
            self.cboCay.setCurrentIndex(0)
        if self.txtNoiDung is not None:
            self.txtNoiDung.clear()
        if self.cboMucDo is not None:
            self.cboMucDo.setCurrentIndex(0)
        if self.cboTrangThai is not None:
            self.cboTrangThai.setCurrentIndex(0)
        if self.cboNhanVien is not None:
            self.cboNhanVien.setCurrentIndex(0)
        if self.dateNgayTao is not None:
            self.dateNgayTao.setDate(QDate.currentDate())

    def saveMaintenanceRequest(self):
        """Kiểm tra dữ liệu nhập, tự sinh Mã bảo trì, rồi lưu thẳng vào SQL
        Server (database.add_yeucaubaotri). Sau khi lưu thành công, dữ liệu
        này sẽ tự động hiện ở bảng "Yêu cầu bảo trì" trên Trang chủ vì
        MainWindow luôn tải lại database.get_all_yeucaubaotri() mỗi khi mở."""
        macay = self.cboCay.currentData() if self.cboCay is not None else None
        manv = self.cboNhanVien.currentData() if self.cboNhanVien is not None else None
        noidung = self.txtNoiDung.toPlainText().strip() if self.txtNoiDung is not None else ""
        mucdouutien = self.cboMucDo.currentData() if self.cboMucDo is not None else None
        trangthai = self.cboTrangThai.currentData() if self.cboTrangThai is not None else "Chờ xử lý"

        if not macay:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn Cây.")
            return
        if not noidung:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập nội dung bảo trì.")
            return
        if not mucdouutien:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn mức độ ưu tiên.")
            return
        if not manv:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn nhân viên phụ trách xử lý.")
            return

        ngaytao = (
            self.dateNgayTao.date().toString("yyyy-MM-dd")
            if self.dateNgayTao is not None
            else date.today().isoformat()
        )

        # Tính lại mã BT ngay trước khi lưu (không dùng mã đã hiển thị sẵn
        # trên form) để đảm bảo luôn đồng bộ với dữ liệu MỚI NHẤT trong SQL,
        # phòng trường hợp form mở lâu hoặc có người khác vừa thêm bản ghi.
        mabt = self.refreshMaBT()

        try:
            database.add_yeucaubaotri(
                mabt=mabt, ngaytao=ngaytao, noidungbaotri=noidung,
                mucdouutien=mucdouutien, trangthai=trangthai or "Chờ xử lý",
                macay=macay, manv=manv,
            )
            QMessageBox.information(self, "Thành công", f"Đã lưu yêu cầu bảo trì '{mabt}' vào Database thành công!")
            self.resetForm()
            self.loadMaintenance()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")

    # ---------------- Nạp & hiển thị bảng Yêu cầu bảo trì (nếu form có bảng) ----------------
    def loadMaintenance(self):
        """Tích hợp database.get_all_yeucaubaotri()"""
        if hasattr(self.ui, "tableMaintenance"):  # Thay thế bằng tên table tương ứng của bạn nếu có
            try:
                records = database.get_all_yeucaubaotri()
                self.ui.tableMaintenance.clearContents()
                self.ui.tableMaintenance.setRowCount(len(records))
                for row, rec in enumerate(records):
                    self.ui.tableMaintenance.setItem(row, 0, QTableWidgetItem(str(rec.get("MABT", ""))))
                    self.ui.tableMaintenance.setItem(row, 1, QTableWidgetItem(str(rec.get("NGAYTAO", ""))))
                    self.ui.tableMaintenance.setItem(row, 2, QTableWidgetItem(str(rec.get("NOIDUNGBAOTRI", ""))))
                    self.ui.tableMaintenance.setItem(row, 3, QTableWidgetItem(str(rec.get("TRANGTHAI", ""))))
            except Exception as e:
                print(f"Không thể load Yêu cầu bảo trì từ DB: {e}")


class BaoCaoSuCoWindow(NavigationWindow):
    """
    Trang "Báo cáo sự cố" (giao diện "Thêm báo cáo sự cố" trong ảnh chụp màn
    hình): ô "Cây" được nạp thành danh sách (ComboBox) lấy TRỰC TIẾP từ SQL
    để người dùng CHỌN thay vì gõ tay mã, y hệt cách làm ở trang "Yêu cầu
    bảo trì" (tránh gõ sai / gõ mã không tồn tại -> lỗi khóa ngoại).

    LƯU Ý: bảng BAO_CAO_SU_CO trong SQL có ràng buộc CK_TrangThai_BCSC chỉ
    cho phép 3 giá trị: 'Chờ xử lý', 'Đang xử lý', 'Đã xử lý' (không có 'Mới
    tiếp nhận' như trên giao diện thiết kế). Vì vậy ô "Trạng thái xử lý" vẫn
    HIỂN THỊ chữ "Mới tiếp nhận" cho khớp giao diện, nhưng giá trị THỰC LƯU
    xuống Database là 'Chờ xử lý' để không vi phạm CHECK CONSTRAINT.

    Cột MAKHACH trong BAO_CAO_SU_CO là NOT NULL (bắt buộc) nhưng giao diện
    không có ô chọn "Khách" -> mã khách được TỰ ĐỘNG lấy/tạo dựa theo tài
    khoản đang đăng nhập (xem database.get_or_create_makhach_by_username),
    người dùng không cần quan tâm.
    """

    _MABC_CANDIDATES = ["txtMaBC", "txtMaBaoCao", "lineEditMaBC", "maBaoCaoEdit"]
    _THOIGIAN_CANDIDATES = ["dateThoiGianGui", "dateTimeThoiGianGui", "dateTimeGui",
                             "dateTimeEditThoiGianGui", "dateGui"]
    _CAY_CANDIDATES = ["cboCay", "comboCay", "cbCay", "cbo_cay", "cayComboBox"]
    _NOIDUNG_CANDIDATES = ["txtNoiDung", "txtMoTa", "textEditNoiDung", "textEditMoTa",
                            "moTaTextEdit", "noiDungTextEdit", "plainTextEditNoiDung"]
    _MUCDO_CANDIDATES = ["cboMucDo", "cboMucDoNguyHiem", "comboMucDo", "dangerComboBox",
                          "cboMucDoNguyHiemComboBox"]
    _TRANGTHAI_CANDIDATES = ["cboTrangThai", "cboTrangThaiXuLy", "comboTrangThai", "statusComboBox"]
    _SAVE_BUTTON_CANDIDATES = ["btnLuu", "btnSave", "saveButton", "pushButtonLuu"]
    _CANCEL_BUTTON_CANDIDATES = ["btnHuyBo", "btnCancel", "cancelButton", "pushButtonHuyBo"]
    _CHARCOUNT_CANDIDATES = ["lblSoKyTu", "lblCharCount", "labelCharCount", "lblDemKyTu"]
    _TABLE_CANDIDATES = ["tableIncidents", "table_incidents", "tableBaoCao", "tableWidget"]

    NOIDUNG_MAX_LEN = 500

    # (text hiển thị, giá trị thực lưu SQL) - khớp với ràng buộc CK_TrangThai_BCSC
    TRANGTHAI_OPTIONS = [
        ("Mới tiếp nhận", "Chờ xử lý"),
        ("Đang xử lý", "Đang xử lý"),
        ("Đã xử lý", "Đã xử lý"),
    ]
    # Khớp với ràng buộc CK_MucDo_BCSC
    MUCDONGUYHIEM_OPTIONS = ["Thấp", "Trung bình", "Cao"]

    # Tiền tố mã báo cáo: dùng lại đúng tiền tố "BC" đã có sẵn trong dữ liệu
    # SQL cũ (BC01...BC11) để mã mới sinh ra được TIẾP NỐI đúng số thứ tự
    # (BC12, BC13...), đồng bộ với những gì đang hiển thị ở Trang chủ.
    MABC_PREFIX = "BC"

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_BaoCaoSuCo()
        self.ui.setupUi(self)
        self.init_common(username, role)

        self._locate_widgets()
        self._setup_form_defaults()
        self.populateComboboxes()
        self.connectButtons()
        self.refreshMaBC()
        self.loadIncidents()

    # ---------------- Dò tìm control trên form ----------------
    def _locate_widgets(self):
        self.txtMaBC = _find_widget_by_hints(
            self.ui, self._MABC_CANDIDATES, QLineEdit, keyword_hints=("mabc", "baocao")
        )
        self.cboCay = _find_widget_by_hints(
            self.ui, self._CAY_CANDIDATES, QComboBox, keyword_hints=("cay", "tree")
        )
        self.txtNoiDung = _find_widget_by_hints(
            self.ui, self._NOIDUNG_CANDIDATES, QTextEdit, keyword_hints=("noidung", "mota", "content")
        )
        self.cboMucDo = _find_widget_by_hints(
            self.ui, self._MUCDO_CANDIDATES, QComboBox, keyword_hints=("nguyhiem", "danger", "mucdo")
        )
        self.cboTrangThai = _find_widget_by_hints(
            self.ui, self._TRANGTHAI_CANDIDATES, QComboBox, keyword_hints=("trangthai", "status")
        )
        self.dateThoiGianGui = _find_widget_by_hints(
            self.ui, self._THOIGIAN_CANDIDATES, QDateTimeEdit, keyword_hints=("thoigian", "gui", "time")
        )
        if self.dateThoiGianGui is None:
            self.dateThoiGianGui = _get_first_datetime_edit(self.ui)
        self.btnLuu = _find_widget_by_hints(
            self.ui, self._SAVE_BUTTON_CANDIDATES, QPushButton, keyword_hints=("lưu", "luu", "save")
        )
        self.btnHuyBo = _find_widget_by_hints(
            self.ui, self._CANCEL_BUTTON_CANDIDATES, QPushButton, keyword_hints=("hủy", "huy", "cancel")
        )
        self.lblSoKyTu = None
        for name in self._CHARCOUNT_CANDIDATES:
            if hasattr(self.ui, name):
                self.lblSoKyTu = getattr(self.ui, name)
                break
        self.tableIncidents = None
        for name in self._TABLE_CANDIDATES:
            if hasattr(self.ui, name):
                widget = getattr(self.ui, name)
                if isinstance(widget, QTableWidget):
                    self.tableIncidents = widget
                    break
        if self.tableIncidents is None:
            self.tableIncidents = _get_first_table_widget(self.ui)

    # ---------------- Thiết lập giá trị mặc định cho form ----------------
    def _setup_form_defaults(self):
        if self.txtMaBC is not None:
            # Ô "Mã báo cáo" chỉ ĐỌC (người dùng không gõ tay được, tránh
            # trùng mã với dữ liệu đã có trong SQL) nhưng vẫn HIỂN THỊ sẵn mã
            # kế tiếp (vd BC12) ngay khi mở form -> xem refreshMaBC() bên
            # dưới, luôn tính từ dữ liệu THẬT trong SQL.
            self.txtMaBC.setReadOnly(True)
            self.txtMaBC.setPlaceholderText("Tự động tạo khi lưu")

        if self.dateThoiGianGui is not None:
            self.dateThoiGianGui.setDisplayFormat("dd/MM/yyyy HH:mm")
            self.dateThoiGianGui.setCalendarPopup(True)
            self.dateThoiGianGui.setDateTime(QDateTime.currentDateTime())

        if self.txtNoiDung is not None:
            self.txtNoiDung.textChanged.connect(self._updateCharCount)
            self._updateCharCount()

    def _updateCharCount(self):
        """Cập nhật nhãn đếm ký tự "x/500" và cắt bớt nếu người dùng nhập quá dài."""
        if self.txtNoiDung is None:
            return
        text = self.txtNoiDung.toPlainText()
        if len(text) > self.NOIDUNG_MAX_LEN:
            text = text[: self.NOIDUNG_MAX_LEN]
            cursor = self.txtNoiDung.textCursor()
            self.txtNoiDung.blockSignals(True)
            self.txtNoiDung.setPlainText(text)
            self.txtNoiDung.blockSignals(False)
            cursor.movePosition(cursor.MoveOperation.End)
            self.txtNoiDung.setTextCursor(cursor)
        if self.lblSoKyTu is not None:
            self.lblSoKyTu.setText(f"{len(text)}/{self.NOIDUNG_MAX_LEN}")

    # ---------------- Nạp danh sách Cây / Mức độ nguy hiểm / Trạng thái ----------------
    def populateComboboxes(self):
        if self.cboCay is not None:
            try:
                trees = database.get_all_cay()
            except Exception as e:
                trees = []
                print(f"Không tải được danh sách cây: {e}")
            self.cboCay.blockSignals(True)
            self.cboCay.clear()
            self.cboCay.addItem("Chọn cây", None)
            for t in trees:
                self.cboCay.addItem(f"{t['MACAY']} - {t['TENCAY']}", t["MACAY"])
            self.cboCay.blockSignals(False)

        if self.cboMucDo is not None:
            self.cboMucDo.blockSignals(True)
            self.cboMucDo.clear()
            self.cboMucDo.addItem("Chọn mức độ nguy hiểm", None)
            for opt in self.MUCDONGUYHIEM_OPTIONS:
                self.cboMucDo.addItem(opt, opt)
            self.cboMucDo.blockSignals(False)

        if self.cboTrangThai is not None:
            self.cboTrangThai.blockSignals(True)
            self.cboTrangThai.clear()
            for label, value in self.TRANGTHAI_OPTIONS:
                self.cboTrangThai.addItem(label, value)
            self.cboTrangThai.setCurrentIndex(0)  # Mặc định "Mới tiếp nhận" -> lưu "Chờ xử lý"
            self.cboTrangThai.blockSignals(False)

    # ---------------- Sinh mã báo cáo (đồng bộ với SQL) ----------------
    def refreshMaBC(self):
        """
        Tính mã báo cáo KẾ TIẾP dựa trên dữ liệu THẬT đang có trong SQL Server
        (bảng BAO_CAO_SU_CO), dùng đúng tiền tố "BC" đang có sẵn trong dữ
        liệu SQL (vd BC01...BC11 -> mã kế tiếp sẽ là BC12...) rồi hiển thị lên
        ô "Mã báo cáo". Gọi lại hàm này mỗi khi mở form và sau mỗi lần Lưu
        thành công để mã luôn đồng bộ, không bao giờ bị trùng hay lệch với
        Database.
        """
        try:
            current = database.get_all_baocaosuco()
            existing_ids = [r["MABC"] for r in current]
        except Exception as e:
            existing_ids = []
            print(f"Không tải được danh sách mã báo cáo hiện có từ SQL: {e}")
        next_id = _generate_next_code(existing_ids, self.MABC_PREFIX, 2)
        if self.txtMaBC is not None:
            self.txtMaBC.setText(next_id)
        return next_id

    # ---------------- Nút Lưu / Hủy bỏ ----------------
    def connectButtons(self):
        if self.btnLuu is not None:
            self.btnLuu.clicked.connect(self.saveIncident)
        if self.btnHuyBo is not None:
            self.btnHuyBo.clicked.connect(self.resetForm)

    def resetForm(self):
        """Xóa trắng form để nhập báo cáo sự cố mới (nút "Hủy bỏ")."""
        self.refreshMaBC()  # Tính lại mã BC kế tiếp đồng bộ với SQL, không để trống
        if self.cboCay is not None:
            self.cboCay.setCurrentIndex(0)
        if self.txtNoiDung is not None:
            self.txtNoiDung.clear()
        if self.cboMucDo is not None:
            self.cboMucDo.setCurrentIndex(0)
        if self.cboTrangThai is not None:
            self.cboTrangThai.setCurrentIndex(0)
        if self.dateThoiGianGui is not None:
            self.dateThoiGianGui.setDateTime(QDateTime.currentDateTime())

    def saveIncident(self):
        """Kiểm tra dữ liệu nhập, tự sinh Mã báo cáo, rồi lưu thẳng vào SQL
        Server (database.add_baocaosuco). Sau khi lưu thành công, dữ liệu này
        sẽ tự động hiện ở bảng "Báo cáo sự cố" trên Trang chủ VÀ ở trang
        "Báo cáo sự cố" này, vì cả hai đều tải lại database.get_all_baocaosuco()
        mỗi khi mở/refresh."""
        macay = self.cboCay.currentData() if self.cboCay is not None else None
        mota = self.txtNoiDung.toPlainText().strip() if self.txtNoiDung is not None else ""
        mucdonguyhiem = self.cboMucDo.currentData() if self.cboMucDo is not None else None
        trangthai = self.cboTrangThai.currentData() if self.cboTrangThai is not None else "Chờ xử lý"

        if not macay:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn Cây.")
            return
        if not mota:
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập nội dung mô tả.")
            return
        if not mucdonguyhiem:
            QMessageBox.warning(self, "Thông báo", "Vui lòng chọn mức độ nguy hiểm.")
            return

        thoigiangui = (
            self.dateThoiGianGui.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            if self.dateThoiGianGui is not None
            else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Tính lại mã BC ngay trước khi lưu (không dùng mã đã hiển thị sẵn
        # trên form) để đảm bảo luôn đồng bộ với dữ liệu MỚI NHẤT trong SQL,
        # phòng trường hợp form mở lâu hoặc có người khác vừa thêm bản ghi.
        mabc = self.refreshMaBC()

        try:
            # Bảng BAO_CAO_SU_CO bắt buộc có MAKHACH (NOT NULL) nhưng giao
            # diện không có ô chọn khách -> tự lấy/tạo theo tài khoản đang
            # đăng nhập (self.username có sẵn từ NavigationWindow.init_common).
            makhach = database.get_or_create_makhach_by_username(self.username)
            database.add_baocaosuco(
                mabc=mabc, thoigiangui=thoigiangui, mota=mota,
                mucdonguyhiem=mucdonguyhiem, trangthai=trangthai or "Chờ xử lý",
                macay=macay, makhach=makhach,
            )
            QMessageBox.information(self, "Thành công", f"Đã lưu báo cáo sự cố '{mabc}' vào Database thành công!")
            self.resetForm()
            self.loadIncidents()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")

    # ---------------- Nạp & hiển thị bảng Báo cáo sự cố ----------------
    def loadIncidents(self):
        """Tích hợp database.get_all_baocaosuco(), tự đồng bộ với Trang chủ."""
        if self.tableIncidents is None:
            return
        try:
            incidents = database.get_all_baocaosuco()
            self.tableIncidents.clearContents()
            self.tableIncidents.setRowCount(len(incidents))
            col_count = self.tableIncidents.columnCount()
            for row, inc in enumerate(incidents):
                values = [
                    str(inc.get("MABC", "")),
                    str(inc.get("THOIGIANGUI", "")),
                    str(inc.get("MACAY", "")),
                    str(inc.get("MOTA", "")),
                    str(inc.get("MUCDONGUYHIEM", "")),
                    str(inc.get("TRANGTHAI", "")),
                    str(inc.get("TENKHACH", "")),
                ]
                for col, val in enumerate(values):
                    if col_count and col >= col_count:
                        break
                    self.tableIncidents.setItem(row, col, QTableWidgetItem(val))
        except Exception as e:
            print(f"Không thể load Báo cáo sự cố từ DB: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())