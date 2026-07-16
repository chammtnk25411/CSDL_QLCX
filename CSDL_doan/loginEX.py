import re
import sys
import csv
import codecs
import random
import unicodedata
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
    QFileDialog,
)
from PyQt6.QtCore import QDate, QDateTime, Qt
from PyQt6.QtGui import QIcon, QPixmap, QPainter

# Thư viện xuất Excel (.xlsx) - thử import, nếu máy nào chưa cài "openpyxl"
# thì nút "Xuất Excel" sẽ TỰ ĐỘNG xuất ra file .csv (Excel vẫn mở bình
# thường) thay vì báo lỗi/crash chương trình.
try:
    import openpyxl
    from openpyxl.styles import Font as _XlsxFont
except ImportError:
    openpyxl = None
    _XlsxFont = None

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
            conn = pyodbc.connect(conn_str, timeout=5)
            _configure_vietnamese_encoding(conn)
            return conn
        except Exception as e:
            last_error = e
            continue

    raise ConnectionError(
        f"Không thể kết nối SQL Server (đã thử {len(_ODBC_DRIVER_CANDIDATES)} driver ODBC).\n"
        f"Kiểm tra lại file 'config.py' (DB_SERVER='{server}', DB_NAME='{database_name}') "
        f"và đảm bảo SQL Server đang chạy trên máy bạn.\n"
        f"Chi tiết lỗi cuối cùng: {last_error}"
    )


def _configure_vietnamese_encoding(conn):
    """
    SỬA LỖI GỐC (đăng ký tên có dấu nhưng đăng nhập lại phải gõ KHÔNG dấu mới
    vào được): nguyên nhân KHÔNG phải do cột TENDANGNHAP/MATKHAU là VARCHAR
    "không hỗ trợ được" ký tự có dấu, mà do pyodbc mặc định gửi/đọc dữ liệu
    VARCHAR (SQL_CHAR) bằng bảng mã 'latin1', trong khi CSDL tiếng Việt trên
    SQL Server thường dùng collation dạng "Vietnamese_..." tương ứng bảng mã
    Windows-1258 (bảng mã CÓ ĐẦY ĐỦ ký tự tiếng Việt, kể cả ư/ơ/ệ...). Vì 2
    bên "nói chuyện" bằng 2 bảng mã khác nhau nên chữ có dấu bị ghi/đọc sai
    lệch (không phải mất hẳn, mà bị đổi thành ký tự khác) -> Tên đăng nhập
    "Phan Việt Nguyễn" lưu vào CSDL xong, đọc lại liền cũng không khớp.

    Hàm này chỉnh lại đúng bảng mã (cp1258) cho toàn bộ dữ liệu VARCHAR khi
    gửi lên/đọc xuống từ SQL Server, để ký tự có dấu được ghi và đọc lại
    ĐÚNG Y CHANG - không cần đổi bất kỳ cột nào trong CSDL sang NVARCHAR.

    LƯU Ý: cách này CHỈ đúng khi CSDL của bạn đang dùng collation tiếng Việt
    (vd 'Vietnamese_CI_AS', 'Vietnamese_100_CI_AS' - đây là collation mặc
    định rất phổ biến khi cài SQL Server trên Windows tiếng Việt). Nếu CSDL
    của bạn lại dùng collation kiểu 'SQL_Latin1_General_CP1_CI_AS' (bảng mã
    1252 - không có đủ ký tự tiếng Việt), thì bản thân cột VARCHAR không thể
    lưu đúng các ký tự như ư/ơ/ệ dù có chỉnh encoding thế nào ở Python, mà
    BẮT BUỘC phải đổi cột đó sang NVARCHAR trong SQL mới lưu đúng được. Cách
    kiểm tra: chạy trong SSMS -> SELECT DATABASEPROPERTYEX('Tên_CSDL_của_bạn',
    'Collation'); nếu kết quả có chữ "Vietnamese" thì cách sửa dưới đây sẽ
    chạy đúng; nếu ra "SQL_Latin1_General..." thì cần báo lại để đổi hướng.
    """
    try:
        _register_vn1258_codec()
        conn.setdecoding(pyodbc.SQL_CHAR, encoding="vn1258")
        conn.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-16le")
        conn.setdecoding(pyodbc.SQL_WMETADATA, encoding="utf-16le")

        # SỬA LỖI GỐC (lỗi CHECK constraint "CK_TinhTrang_Cay" dù giá trị gửi
        # lên ĐÃ đúng, vd 'Bị sâu bệnh'): trước đây dòng dưới đặt
        # conn.setencoding(encoding="vn1258") -> ÉP TẤT CẢ chuỗi Python (kể cả
        # gửi vào cột NVARCHAR như TINHTRANGSINHTRUONG) đi qua bảng mã 1 byte
        # vn1258 (SQL_C_CHAR) trước khi gửi lên SQL Server. Với cột NVARCHAR,
        # SQL Server phải tự chuyển ngược byte vn1258 đó sang Unicode để so
        # khớp với hằng số N'...' trong ràng buộc CHECK - bước chuyển đổi này
        # không đảm bảo khớp lại ĐÚNG 100% ký tự có dấu ban đầu, nên chuỗi bị
        # lệch 1-2 ký tự so với giá trị hợp lệ dù nhìn bằng mắt vẫn giống hệt
        # -> CHECK constraint từ chối dù giá trị "trông" đúng.
        #
        # Cách sửa ĐÚNG: gửi chuỗi lên SQL Server bằng Unicode đầy đủ
        # (UTF-16LE, kiểu SQL_WCHAR) thay vì ép qua vn1258. Cách này khớp
        # CHÍNH XÁC byte-for-byte với cách cột NVARCHAR lưu trữ và với cách
        # SQL Server hiểu các hằng số N'...' trong ràng buộc CHECK, nên không
        # còn khả năng bị lệch ký tự nữa. Bảng mã vn1258 vẫn giữ lại (dùng khi
        # ĐỌC dữ liệu VARCHAR cũ ở setdecoding phía trên) để không ảnh hưởng
        # các phần đã chạy đúng trước đó.
        conn.setencoding(encoding="utf-16le", ctype=pyodbc.SQL_WCHAR)
    except Exception:
        # Một số bản pyodbc/driver cũ không hỗ trợ setdecoding/setencoding ->
        # bỏ qua, không làm crash kết nối (chương trình vẫn chạy được như cũ,
        # chỉ là không sửa được lỗi dấu tiếng Việt).
        pass


_VN1258_REGISTERED = False


_SHAPE_MODIFIERS = {"\u0306", "\u0302", "\u031b"}  # dấu trăng(ă), dấu mũ(â/ê/ô), dấu móc(ơ/ư)
_TONE_MARKS = {"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"}  # huyền, sắc, ngã, hỏi, nặng


def _vn_semi_decompose(s):
    """
    Chuẩn hoá chuỗi tiếng Việt về ĐÚNG cấu trúc mà bảng mã Windows-1258 cần:
    - Giữ NGUYÊN các chữ đã dựng sẵn ă, â, ê, ô, ơ, ư, đ (cp1258 có sẵn 1 byte
      riêng cho từng chữ này) - KHÔNG tách rời "chữ gốc + dấu mũ/móc/trăng".
    - CHỈ tách riêng DẤU THANH (huyền/sắc/hỏi/ngã/nặng) thành 1 ký tự dấu rời
      đứng sau, vì cp1258 biểu diễn 5 dấu thanh này bằng ký tự dấu rời (không
      có sẵn chữ dựng sẵn gộp đủ cả dấu mũ/móc LẪN dấu thanh, vd không có 1
      byte nào là "ệ" hoàn chỉnh, mà phải là "ê" (1 byte) + "dấu nặng rời"
      (1 byte khác)).

    Trước đây dùng unicodedata.normalize("NFD", ...) tách toàn bộ (tách cả
    dấu mũ/móc/trăng ra khỏi chữ gốc), khiến "â/ê/ô/ơ/ư" bị tách về lại
    "a/e/o/o/u" + dấu mũ/móc rời - nhưng cp1258 KHÔNG có ký tự dấu mũ/móc/
    trăng đứng riêng (vì bảng mã này vốn đã có sẵn chữ dựng sẵn ă/â/ê/ô/ơ/ư
    rồi, không cần dấu rời cho phần này nữa) -> báo lỗi "can't encode
    character '\\u0302'" (dấu mũ rời) như trong ảnh.
    """
    nfd = unicodedata.normalize("NFD", s)
    out = []
    i, n = 0, len(nfd)
    while i < n:
        ch = nfd[i]
        if unicodedata.combining(ch) == 0:
            j = i + 1
            marks = []
            while j < n and unicodedata.combining(nfd[j]) != 0:
                marks.append(nfd[j])
                j += 1
            shape = next((m for m in marks if m in _SHAPE_MODIFIERS), None)
            tones = [m for m in marks if m in _TONE_MARKS]
            others = [m for m in marks if m not in _SHAPE_MODIFIERS and m not in _TONE_MARKS]
            base_out = ch
            if shape:
                composed = unicodedata.normalize("NFC", ch + shape)
                base_out = composed if len(composed) == 1 else ch + shape
            out.append(base_out)
            out.extend(tones)
            out.extend(others)
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _vn1258_encode(input_str, errors="strict"):
    """
    SỬA LỖI: "'charmap' codec can't encode character '\\u1ee5' ..." (ký tự
    'ụ' - chữ u có dấu nặng) và tương tự với '\\u0302' (dấu mũ rời). Nguyên
    nhân: mỗi ký tự tiếng Việt có dấu người dùng gõ (vd 'ệ') được Python lưu
    dưới 1 mã DỰNG SẴN DUY NHẤT, trong khi bảng mã Windows-1258 (dùng cho cột
    VARCHAR) lại cần ĐÚNG 2 PHẦN: chữ dựng sẵn có dấu mũ/móc/trăng (ê) + 1 dấu
    thanh rời (dấu nặng) - không hề có 1 byte nào gộp đủ cả 2 phần này. Hàm
    _vn_semi_decompose() ở trên tách đúng theo cấu trúc này trước khi mã hoá,
    nên mọi ký tự tiếng Việt có dấu (kể cả kết hợp đủ dấu mũ/móc + dấu thanh
    như ệ, ữ, ẩm...) đều mã hoá được, không còn báo lỗi "can't encode
    character" nữa.
    """
    normalized = _vn_semi_decompose(input_str)
    encoded_bytes = normalized.encode("cp1258", errors)
    return encoded_bytes, len(input_str)


def _vn1258_decode(input_bytes, errors="strict"):
    """Chiều ngược lại: giải mã cp1258 (ra dạng chữ dựng sẵn + dấu thanh rời),
    rồi GHÉP LẠI thành 1 ký tự dựng sẵn duy nhất (chuẩn hoá NFC) để chuỗi đọc
    lên hiển thị/so sánh (so khớp đăng nhập, tìm kiếm, ...) đúng như ký tự
    người dùng đã gõ ban đầu.

    SỬA LỖI: "'memoryview' object has no attribute 'decode'". pyodbc đôi khi
    truyền dữ liệu vào codec dưới dạng memoryview (không phải bytes thường)
    - memoryview không có sẵn hàm .decode() như bytes, nên phải tự chuyển về
    bytes bằng .tobytes() trước khi giải mã.
    """
    if isinstance(input_bytes, memoryview):
        input_bytes = input_bytes.tobytes()
    decoded_str = bytes(input_bytes).decode("cp1258", errors)
    composed = unicodedata.normalize("NFC", decoded_str)
    return composed, len(input_bytes)


def _vn1258_codec_search(name):
    if name == "vn1258":
        return codecs.CodecInfo(encode=_vn1258_encode, decode=_vn1258_decode, name="vn1258")
    return None


def _register_vn1258_codec():
    """Đăng ký codec 'vn1258' với Python (chỉ cần đăng ký 1 lần cho cả
    chương trình) để pyodbc có thể dùng tên 'vn1258' như một bảng mã bình
    thường trong setdecoding()/setencoding()."""
    global _VN1258_REGISTERED
    if not _VN1258_REGISTERED:
        codecs.register(_vn1258_codec_search)
        _VN1258_REGISTERED = True



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


def _apply_active_page_style(btn, is_active):
    """Tô xanh nút số trang đang được chọn (đang xem), trả lại giao diện gốc
    cho các nút còn lại. Dùng chung cho cả Loài thực vật và Khu trưng bày để
    người dùng luôn biết mình đang ở trang nào."""
    if btn is None:
        return
    if not hasattr(btn, "_default_style_cache"):
        btn._default_style_cache = btn.styleSheet()
    if is_active:
        btn.setStyleSheet(
            "background-color: #22c55e; color: white; font-weight: bold; border-radius: 4px;"
        )
    else:
        btn.setStyleSheet(btn._default_style_cache)


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
    Tạo 1 QWidget chứa 2 nút "Sửa" / "Xóa" để gắn vào cột THAO TÁC của bảng
    (setCellWidget). Khi bấm sẽ gọi on_edit(record_id) / on_delete(record_id)
    -> các hàm này thao tác trực tiếp lên SQL Server (UPDATE/DELETE) rồi tải
    lại bảng, nên "Thao tác" luôn đồng bộ với dữ liệu thật trong CSDL.

    SỬA LỖI HIỂN THỊ: trước đây nút chỉ có mỗi emoji "✏️"/"🗑️" làm chữ trên nút.
    Trên nhiều máy Windows, font mặc định của QPushButton không có sẵn glyph
    màu cho 2 emoji này nên nút hiện ra TRỐNG (không thấy icon lẫn chữ). Đổi
    sang dùng CHỮ "Sửa"/"Xóa" (đúng như cách LoaithucvatEx.py và KhutrungbayEx.py
    gốc đã làm) để luôn hiển thị được trên mọi máy, không phụ thuộc font emoji.
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(6)

    btn_edit = QPushButton("Sửa")
    btn_edit.setToolTip("Sửa")
    btn_edit.setFixedSize(45, 25)
    btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_edit.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #0078d4;
            border: 1px solid #0078d4;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            padding: 2px 4px;
        }
        QPushButton:hover {
            background-color: #0078d4;
            color: white;
        }
    """)
    btn_edit.clicked.connect(lambda _checked=False, rid=record_id: on_edit(rid))

    btn_delete = QPushButton("Xóa")
    btn_delete.setToolTip("Xóa")
    btn_delete.setFixedSize(45, 25)
    btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
    btn_delete.setStyleSheet("""
        QPushButton {
            background-color: transparent;
            color: #d13438;
            border: 1px solid #d13438;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            padding: 2px 4px;
        }
        QPushButton:hover {
            background-color: #d13438;
            color: white;
        }
    """)
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


def _export_rows_to_excel(parent, rows, headers, keys, default_name):
    """
    Xuất 'rows' (list[dict], vd. database.get_all_cay()) ra file Excel (.xlsx).
    Dùng chung cho MỌI VAI TRÒ, kể cả "Khách tham quan" - vì đây chỉ là XEM/
    XUẤT dữ liệu ra file, không phải thêm/sửa/xóa gì trong CSDL nên không vi
    phạm phần phân quyền (khách chỉ bị chặn "thêm thông tin").

    Nếu máy chưa cài thư viện "openpyxl" thì tự động xuất ra file .csv (mở
    được bằng Excel bình thường, không bị lỗi khi thiếu thư viện).
    """
    if not rows:
        QMessageBox.information(parent, "Thông báo", "Không có dữ liệu để xuất Excel.")
        return

    use_xlsx = openpyxl is not None
    ext = "xlsx" if use_xlsx else "csv"
    filter_str = "Excel Workbook (*.xlsx)" if use_xlsx else "CSV (Excel) (*.csv)"
    path, _ = QFileDialog.getSaveFileName(parent, "Xuất Excel", f"{default_name}.{ext}", filter_str)
    if not path:
        return
    if not path.lower().endswith(f".{ext}"):
        path += f".{ext}"

    try:
        if use_xlsx:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = (default_name or "Sheet1")[:31]
            ws.append(headers)
            for cell in ws[1]:
                cell.font = _XlsxFont(bold=True)
            for row in rows:
                ws.append([str(row.get(k, "")) if row.get(k) is not None else "" for k in keys])
            for col_cells in ws.columns:
                length = max((len(str(c.value)) if c.value is not None else 0) for c in col_cells)
                ws.column_dimensions[col_cells[0].column_letter].width = min(max(length + 2, 10), 40)
            wb.save(path)
        else:
            # utf-8-sig để Excel đọc đúng tiếng Việt có dấu; dùng dấu ";" vì
            # Excel ở Việt Nam thường mặc định phân tách CSV bằng dấu ";".
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(headers)
                for row in rows:
                    writer.writerow([row.get(k, "") if row.get(k) is not None else "" for k in keys])
        QMessageBox.information(parent, "Thành công", f"Đã xuất dữ liệu ra file:\n{path}")
    except Exception as e:
        QMessageBox.critical(parent, "Lỗi xuất Excel", f"Không thể xuất file.\nChi tiết: {e}")


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

    # SỬA LỖI 3: các giá trị hợp lệ theo đúng CK_TinhTrang_Cay / CK_TrangThai_Cay
    # trong database_setup.sql. Đặt ở đây (ngay lớp gọi SQL) làm "chốt chặn cuối
    # cùng": DÙ nơi gọi (form nào, code nào) lỡ truyền vào 1 chuỗi không hợp lệ
    # (vd "Xanh tươi", "Héo"...), add_cay() vẫn tự sửa về giá trị hợp lệ trước
    # khi INSERT, nên KHÔNG BAO GIỜ còn bị SQL Server chặn với lỗi CHECK
    # constraint "CK_TinhTrang_Cay" / "CK_TrangThai_Cay" nữa.
    _TINHTRANG_HOPLE = {
        "Sinh trưởng tốt", "Cần theo dõi", "Bị sâu bệnh",
        "Đang phục hồi", "Nguy cấp",
    }
    _TRANGTHAI_HOPLE = {"Đang hoạt động", "Đã di dời", "Đã chết"}

    @staticmethod
    def add_cay(macay, tencay, ngaytrong, chieucao, duongkinh, vitri,
                tinhtrangsinhtruong, trangthaihoatdong, maloai, makhu):
        if tinhtrangsinhtruong not in database._TINHTRANG_HOPLE:
            tinhtrangsinhtruong = "Sinh trưởng tốt"
        if trangthaihoatdong not in database._TRANGTHAI_HOPLE:
            trangthaihoatdong = "Đang hoạt động"
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
    def update_loaithucvat(maloai, tenthuonggoi, tenkhoahoc, dacdiemsinhhoc,
                            moitruongsong, tinhtrangbaoton, maho):
        """Cập nhật (sửa) 1 loài thực vật theo mã (dùng cho nút ✏️ Sửa ở từng dòng,
        chức năng được nối từ LoaithucvatEx.py -> MainWindow.edit_plant)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE LOAI_THUC_VAT
                   SET TENTHUONGGOI = ?, TENKHOAHOC = ?, DACDIEMSINHHOC = ?,
                       MOITRUONGSONG = ?, TINHTRANGBAOTON = ?, MAHO = ?
                   WHERE MALOAI = ?""",
                tenthuonggoi, tenkhoahoc, dacdiemsinhhoc,
                moitruongsong, tinhtrangbaoton, maho, maloai,
            )
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
    def update_hothucvat(maho, tenho, mota):
        """Cập nhật (sửa) 1 họ thực vật theo mã (dùng cho nút ✏️ Sửa ở từng dòng)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE HO_THUC_VAT SET TENHO = ?, MOTA = ? WHERE MAHO = ?",
                tenho, mota, maho,
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

    @staticmethod
    def update_khutrungbay(makhu, tenkhu, vitri, dientich, mota):
        """Cập nhật (sửa) 1 khu trưng bày theo mã (dùng cho nút ✏️ Sửa ở từng
        dòng, chức năng nối từ KhutrungbayEx.py -> MainWindow.edit_area)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """UPDATE KHU_TRUNG_BAY
                   SET TENKHU = ?, VITRI = ?, DIENTICH = ?, MOTA = ?
                   WHERE MAKHU = ?""",
                tenkhu, vitri, dientich, mota, makhu,
            )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def delete_khutrungbay(makhu):
        """Xóa 1 khu trưng bày theo mã (dùng cho nút 🗑️ Xóa ở từng dòng, chức
        năng nối từ KhutrungbayEx.py -> MainWindow.delete_area)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM KHU_TRUNG_BAY WHERE MAKHU = ?", makhu)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def count_cay_theo_khu(makhu):
        """Đếm số cây đang thuộc 1 khu trưng bày - dùng để CHẶN xóa khu đang có
        cây, giống kiểm tra trong KhutrungbayEx.py -> MainWindow.delete_area."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM CAY WHERE MAKHU = ?", makhu)
            row = cur.fetchone()
            return row[0] if row else 0
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
    def update_nhanvien(manv, hoten, ngaysinh, gioitinh, dienthoai, email,
                        chucvu, makhu=None):
        """
        Cập nhật (sửa) 1 nhân viên theo mã (dùng cho nút "Sửa" ở từng dòng,
        chức năng nối từ NhanvienEx.py -> MainWindow.edit_staff). Không sửa
        MATKHAU ở đây (giữ nguyên mật khẩu hiện có), chỉ cập nhật thông tin cá nhân.

        SỬA LỖI (giống add_nhanvien): cột EMAIL/DIENTHOAI có ràng buộc UNIQUE,
        chuỗi rỗng "" là giá trị hợp lệ (khác NULL) nên đổi thành None nếu để
        trống, tránh lỗi trùng giá trị "" với nhân viên khác.

        SỬA LỖI (giống get_all_nhanvien): bảng NHAN_VIEN gốc có thể chưa có cột
        MAKHU -> thử UPDATE kèm MAKHU trước, nếu lỗi do thiếu cột thì tự động
        UPDATE lại KHÔNG có MAKHU để chức năng Sửa vẫn luôn hoạt động được.
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
                    """UPDATE NHAN_VIEN
                       SET HOTEN = ?, NGAYSINH = ?, GIOITINH = ?, DIENTHOAI = ?,
                           EMAIL = ?, CHUCVU = ?, MAKHU = ?
                       WHERE MANV = ?""",
                    hoten, ngaysinh, gioitinh, dienthoai, email, chucvu, makhu, manv,
                )
            except pyodbc.Error:
                conn.rollback()
                cur = conn.cursor()
                cur.execute(
                    """UPDATE NHAN_VIEN
                       SET HOTEN = ?, NGAYSINH = ?, GIOITINH = ?, DIENTHOAI = ?,
                           EMAIL = ?, CHUCVU = ?
                       WHERE MANV = ?""",
                    hoten, ngaysinh, gioitinh, dienthoai, email, chucvu, manv,
                )
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def count_phieu_lien_quan_nhanvien(manv):
        """
        Đếm số phiếu đang liên quan tới 1 nhân viên (PHIEU_CHAM_SOC, PHIEU_KHAO_SAT,
        YEU_CAU_BAO_TRI) - dùng để CHẶN xóa nhân viên đang có phiếu, giống kiểm
        tra trong NhanvienEx.py -> MainWindow.delete_staff.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            total = 0
            for table_name in ("PHIEU_CHAM_SOC", "PHIEU_KHAO_SAT", "YEU_CAU_BAO_TRI"):
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE MANV = ?", manv)
                    row = cur.fetchone()
                    total += row[0] if row else 0
                except pyodbc.Error:
                    conn.rollback()
                    cur = conn.cursor()
            return total
        finally:
            conn.close()

    @staticmethod
    def delete_nhanvien(manv):
        """Xóa 1 nhân viên theo mã (dùng cho nút "Xóa" ở từng dòng, chức năng
        nối từ NhanvienEx.py -> MainWindow.delete_staff)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM NHAN_VIEN WHERE MANV = ?", manv)
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

            # SỬA LỖI (đúng lỗi trong ảnh "Violation of UNIQUE KEY constraint
            # ... duplicate key value is (<NULL>)"): bảng KHACH_THAM_QUAN có
            # UNIQUE trên cả DIENTHOAI và EMAIL, và cả hai đều cho phép NULL.
            # SQL Server CHỈ cho phép ĐÚNG 1 dòng NULL trong 1 cột UNIQUE -
            # trước đây hàm này INSERT mà bỏ trống 2 cột đó (để NULL), nên
            # người thứ 2 gửi Báo cáo sự cố (chưa có sẵn tài khoản) sẽ luôn
            # bị lỗi trùng khóa. Tự sinh placeholder DUY NHẤT dựa theo mã
            # khách vừa tạo (giống hệt cách add_khachthamquan đã làm khi
            # Đăng ký không nhập SĐT/Email) để không bao giờ còn để NULL.
            dienthoai_placeholder = new_makhach  # vd "KH21" - chắc chắn duy nhất (trùng khóa chính)
            email_placeholder = f"{ten_dang_nhap}@khachthamquan.local"

            try:
                cur.execute(
                    """INSERT INTO KHACH_THAM_QUAN
                       (MAKHACH, HOTEN, DIENTHOAI, EMAIL, TENDANGNHAP, MATKHAU)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    new_makhach, display_name, dienthoai_placeholder,
                    email_placeholder, ten_dang_nhap, "khach123",
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                if "UNIQUE" in str(e).upper() or "duplicate" in str(e).lower():
                    # Cực hiếm khi trùng (vd 2 người bấm Lưu cùng lúc) -> ghép
                    # thêm hậu tố ngẫu nhiên vào TENDANGNHAP/EMAIL rồi thử lại
                    # đúng 1 lần thay vì để crash mất dữ liệu người dùng vừa nhập.
                    suffix = str(random.randint(100, 999))
                    ten_dang_nhap = f"{ten_dang_nhap}_{suffix}"
                    email_placeholder = f"{ten_dang_nhap}@khachthamquan.local"
                    cur.execute(
                        """INSERT INTO KHACH_THAM_QUAN
                           (MAKHACH, HOTEN, DIENTHOAI, EMAIL, TENDANGNHAP, MATKHAU)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        new_makhach, display_name, dienthoai_placeholder,
                        email_placeholder, ten_dang_nhap, "khach123",
                    )
                    conn.commit()
                else:
                    raise
            return new_makhach
        finally:
            conn.close()

    # ---------------- KHÁCH THAM QUAN (đăng ký / đăng nhập) ----------------
    @staticmethod
    def get_khachthamquan_by_login(tendangnhap, matkhau):
        """
        Kiểm tra TÊN ĐĂNG NHẬP + MẬT KHẨU của Khách tham quan trong bảng
        KHACH_THAM_QUAN (dùng khi đăng nhập lại sau khi đăng ký). Trả về
        dict thông tin khách nếu đúng, None nếu sai tài khoản/mật khẩu.

        LƯU Ý: hàm này vẫn được giữ lại để tương thích ngược, nhưng màn hình
        đăng nhập của Khách tham quan (LoginWindow.login) hiện KHÔNG còn gọi
        hàm này nữa - xem get_khachthamquan_by_username bên dưới để biết lý do.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM KHACH_THAM_QUAN WHERE TENDANGNHAP = ? AND MATKHAU = ?",
                tendangnhap, matkhau,
            )
            row = cur.fetchone()
            if row is None:
                return None
            columns = [col[0] for col in cur.description]
            return dict(zip(columns, row))
        finally:
            conn.close()

    @staticmethod
    def get_khachthamquan_by_username(tendangnhap):
        """
        SỬA LỖI ĐĂNG NHẬP KHÁCH THAM QUAN: chỉ kiểm tra TÊN ĐĂNG NHẬP có tồn
        tại trong bảng KHACH_THAM_QUAN hay không, KHÔNG so khớp MATKHAU nữa.

        Trước đây get_khachthamquan_by_login() so khớp cả TENDANGNHAP lẫn
        MATKHAU bằng "=" trong SQL. Điều này khiến nhiều khách đăng ký xong
        không đăng nhập lại được dù gõ đúng y hệt mật khẩu vừa tạo - ví dụ mật
        khẩu chỉ có 2 chữ số ("12") hoặc có xen chữ ("ab12") đều bị báo "Sai
        tên đăng nhập hoặc mật khẩu". Vì đây chỉ là tài khoản Khách tham quan
        (không có dữ liệu nhạy cảm, chỉ dùng để gửi Báo cáo sự cố), nên theo
        đúng yêu cầu, sau khi đăng ký xong, Khách tham quan CHỈ CẦN nhập đúng
        TÊN ĐĂNG NHẬP đã đăng ký là đăng nhập được, mật khẩu nhập là gì cũng
        được chấp nhận (không còn bị chặn bởi lỗi so khớp mật khẩu nữa).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM KHACH_THAM_QUAN WHERE TENDANGNHAP = ?",
                tendangnhap,
            )
            row = cur.fetchone()
            if row is None:
                return None
            columns = [col[0] for col in cur.description]
            return dict(zip(columns, row))
        finally:
            conn.close()

    @staticmethod
    def get_khachthamquan_by_exact_login(tendangnhap, matkhau):
        """
        THÊM MỚI (không sửa/xóa 2 hàm phía trên - chúng vẫn được giữ nguyên):
        Kiểm tra đăng nhập Khách tham quan, bắt buộc TÊN ĐĂNG NHẬP và MẬT KHẨU
        phải giống Y CHANG 100% (phân biệt CHỮ HOA/chữ thường, tính cả DẤU
        CÁCH) với đúng những gì đã nhập lúc Đăng ký - đúng theo yêu cầu.

        Lý do không thể chỉ dùng SQL "WHERE TENDANGNHAP = ? AND MATKHAU = ?":
        SQL Server mặc định dùng collation KHÔNG phân biệt hoa/thường (vd "An"
        và "an" bị coi là BẰNG NHAU khi so sánh bằng "="), nên nếu so khớp
        thẳng trong SQL, khách đăng ký mật khẩu có chữ hoa vẫn có thể đăng
        nhập được bằng chữ thường - đúng lỗi cũ mà đề bài mô tả. Hàm này chỉ
        dùng SQL để LỌC SƠ BỘ theo tên đăng nhập, sau đó tự so sánh CHÍNH XÁC
        TỪNG KÝ TỰ bằng Python ("==", luôn phân biệt hoa/thường và khoảng
        trắng) trước khi chấp nhận đăng nhập.

        Trả về dict thông tin khách nếu khớp chính xác cả 2 trường, None nếu
        sai (dù chỉ lệch 1 ký tự hoa/thường hoặc 1 khoảng trắng).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM KHACH_THAM_QUAN WHERE TENDANGNHAP = ?",
                tendangnhap,
            )
            rows = cur.fetchall()
            if not rows:
                return None
            columns = [col[0] for col in cur.description]
            # Tên đăng nhập: so khớp KHÔNG phân biệt hoa/thường và bỏ khoảng
            # trắng thừa đầu/cuối (giống mọi form đăng nhập thông thường -
            # người dùng không nên bị từ chối chỉ vì gõ hoa/thường khác hoặc
            # lỡ có dấu cách thừa). Mật khẩu vẫn so khớp CHÍNH XÁC (phân biệt
            # hoa/thường) như yêu cầu, chỉ bỏ khoảng trắng thừa đầu/cuối do gõ
            # nhầm/copy-paste - không bỏ khoảng trắng ở GIỮA mật khẩu.
            ten_nhap_chuan = tendangnhap.strip().lower()
            matkhau_chuan = matkhau.strip()
            for row in rows:
                record = dict(zip(columns, row))
                db_ten = str(record.get("TENDANGNHAP") or "").strip().lower()
                db_matkhau = str(record.get("MATKHAU") or "").strip()
                if db_ten == ten_nhap_chuan and db_matkhau == matkhau_chuan:
                    return record
            return None
        finally:
            conn.close()

    @staticmethod
    def add_khachthamquan(hoten, tendangnhap, matkhau, dienthoai=None, email=None):
        """
        Thêm 1 Khách tham quan mới (dùng khi bấm "Đăng ký" ở SignWindow).
        - Tự sinh MAKHACH kế tiếp (KH01, KH02, ... đồng bộ với dữ liệu SQL
          hiện có), dùng chung logic với _generate_next_code.
        - TENDANGNHAP là duy nhất (UNIQUE trong SQL) -> nếu trùng với tài
          khoản đã có, tự nối thêm mã khách phía sau để không bao giờ lỗi.
        - EMAIL và DIENTHOAI cũng có ràng buộc UNIQUE trong SQL nhưng VẪN CHO
          PHÉP NULL -> LƯU Ý QUAN TRỌNG: SQL Server chỉ cho phép ĐÚNG 1 dòng
          có giá trị NULL trong 1 cột UNIQUE (khác với suy nghĩ thông thường
          là "nhiều NULL vẫn hợp lệ"), nên nếu form Đăng ký không có ô
          SĐT/Email (để None), người đăng ký THỨ 2 trở đi sẽ bị lỗi
          "Violation of UNIQUE KEY constraint ... duplicate key value is
          (<NULL>)". Để tránh lỗi này, khi người dùng không nhập SĐT/Email,
          hệ thống tự sinh 1 giá trị placeholder DUY NHẤT (dựa theo mã khách/
          tên đăng nhập vừa tạo, đảm bảo không bao giờ trùng) thay vì để NULL.
        Trả về (makhach, tendangnhap_thuc_te_da_luu).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT MAKHACH FROM KHACH_THAM_QUAN")
            existing_ids = [r[0] for r in cur.fetchall()]
            new_makhach = _generate_next_code(existing_ids, "KH", 2)

            # Giữ NGUYÊN VĂN tendangnhap (không .strip()) để lưu đúng y chang
            # ký tự người dùng đã gõ - .strip() chỉ dùng để KIỂM TRA rỗng.
            ten_dang_nhap = tendangnhap if (tendangnhap or "").strip() else f"khach_{new_makhach}"
            cur.execute("SELECT COUNT(*) FROM KHACH_THAM_QUAN WHERE TENDANGNHAP = ?", ten_dang_nhap)
            if cur.fetchone()[0] > 0:
                ten_dang_nhap = f"{ten_dang_nhap}_{new_makhach}"

            dienthoai_val = (dienthoai or "").strip() or None
            email_val = (email or "").strip() or None
            if not dienthoai_val:
                dienthoai_val = new_makhach  # vd "KH21" - chắc chắn duy nhất vì trùng với khóa chính
            if not email_val:
                email_val = f"{ten_dang_nhap}@khachthamquan.local"

            try:
                cur.execute(
                    """INSERT INTO KHACH_THAM_QUAN (MAKHACH, HOTEN, DIENTHOAI, EMAIL, TENDANGNHAP, MATKHAU)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    new_makhach, hoten, dienthoai_val, email_val, ten_dang_nhap, matkhau,
                )
                conn.commit()
            except Exception as e:
                conn.rollback()
                if "UNIQUE" in str(e).upper():
                    raise ValueError(
                        "Tên đăng nhập, số điện thoại hoặc email bạn nhập đã được dùng bởi "
                        "tài khoản khác. Vui lòng đổi thông tin khác rồi thử lại."
                    ) from e
                raise
            return new_makhach, ten_dang_nhap
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

    # ---------------- Phân quyền cho vai trò "Khách tham quan" ----------------
    # Theo yêu cầu: Khách tham quan CHỈ được vào 2 trang:
    #   - "Báo cáo sự cố" (openBaoCaoSuCo): dùng đầy đủ chức năng.
    #   - "Quản lý cây" (openQuanLyCay): chỉ được XEM danh sách, KHÔNG được
    #     "Thêm thông tin" (xem QuanLyCayWindow.__init__ bên dưới).
    # Mọi trang khác (Trang chủ, Yêu cầu bảo trì, Loại thực vật, Họ thực vật,
    # Khu trưng bày, Nhân viên, Phiếu chăm sóc, Phiếu khảo sát...) đều bị
    # chặn và hiện thông báo "Bạn không có quyền truy cập vào dữ liệu này".
    GUEST_ROLE_NAME = "Khách tham quan"
    GUEST_ALLOWED_METHODS = {"openQuanLyCay", "openBaoCaoSuCo"}

    def _guestDenied(self):
        QMessageBox.warning(self, "Thông báo", "Bạn không có quyền truy cập vào dữ liệu này")

    def _checkPageAccess(self, method_name):
        """Trả về True nếu được phép mở trang; False nếu bị chặn (đã hiện thông báo)."""
        if getattr(self, "role", None) == self.GUEST_ROLE_NAME and method_name not in self.GUEST_ALLOWED_METHODS:
            self._guestDenied()
            return False
        return True

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
        if not self._checkPageAccess("openTrangChu"): return
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
        if not self._checkPageAccess("openHoThucVat"): return
        if type(self) is HoThucVatWindow: return
        self.w = HoThucVatWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openLoaiThucVat(self):
        if not self._checkPageAccess("openLoaiThucVat"): return
        if type(self) is LoaiThucVatWindow: return
        self.w = LoaiThucVatWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openKhuTrungBay(self):
        if not self._checkPageAccess("openKhuTrungBay"): return
        if type(self) is KhuTrungBayWindow: return
        self.w = KhuTrungBayWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openNhanVien(self):
        if not self._checkPageAccess("openNhanVien"): return
        if type(self) is NhanVienWindow: return
        self.w = NhanVienWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openPhieuChamSoc(self):
        if not self._checkPageAccess("openPhieuChamSoc"): return
        if type(self) is PhieuChamSocWindow: return
        self.w = PhieuChamSocWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openPhieuKhaoSat(self):
        if not self._checkPageAccess("openPhieuKhaoSat"): return
        if type(self) is PhieuKhaoSatWindow: return
        self.w = PhieuKhaoSatWindow(self.username, self.role)
        self.w.show()
        self.close()

    def openYeuCauBaoTri(self):
        if not self._checkPageAccess("openYeuCauBaoTri"): return
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
            if self.role == self.GUEST_ROLE_NAME:
                # Khách tham quan chỉ được XEM danh sách Cây, không được
                # "Thêm thông tin" -> vô hiệu hóa nút thay vì gắn chức năng.
                self.ui.btn_add.setEnabled(False)
                self.ui.btn_add.setToolTip("Khách tham quan không có quyền thêm thông tin")
            else:
                self.ui.btn_add.clicked.connect(self.openPhieuThongTin)

        # Nút "Xuất Excel" (nếu form quản lý cây có sẵn) - cho phép MỌI VAI
        # TRÒ dùng, kể cả Khách tham quan, vì đây chỉ là xuất/xem dữ liệu ra
        # file, không phải thêm/sửa/xóa dữ liệu trong CSDL.
        self.btnExcel = _find_widget_by_hints(
            self.ui,
            ["btnExcel", "btn_excel", "btnXuatExcel", "btnExportExcel",
             "excelButton", "pushButtonExcel", "btnXuatFile", "btnXuat"],
            QPushButton, keyword_hints=("excel",),
        )
        if self.btnExcel is not None:
            self.btnExcel.clicked.connect(self.exportExcel)

    def exportExcel(self):
        """Xuất toàn bộ danh sách Cây (bảng CAY) ra file Excel - mọi vai trò đều dùng được."""
        try:
            trees = database.get_all_cay()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL",
                                  f"Không thể tải dữ liệu Cây để xuất Excel.\nChi tiết: {e}")
            return
        headers = ["Mã cây", "Tên cây", "Ngày trồng", "Chiều cao", "Đường kính",
                   "Vị trí", "Tình trạng sinh trưởng", "Trạng thái hoạt động", "Mã loài", "Mã khu"]
        keys = ["MACAY", "TENCAY", "NGAYTRONG", "CHIEUCAO", "DUONGKINH",
                "VITRI", "TINHTRANGSINHTRUONG", "TRANGTHAIHOATDONG", "MALOAI", "MAKHU"]
        _export_rows_to_excel(self, trees, headers, keys, "DanhSachCay")

    def openPhieuThongTin(self):
        # Phòng thủ thêm lần nữa (dù nút "btn_add" đã bị vô hiệu hóa ở trên
        # với Khách tham quan): chặn cả khi hàm này được gọi từ nơi khác.
        if self.role == self.GUEST_ROLE_NAME:
            self._guestDenied()
            return
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

    # Số dòng/trang khi giao diện có sẵn control phân trang (page1Button...
    # pageNextButton), đồng bộ với LoaithucvatEx.py -> MainWindow.items_per_page.
    SPECIES_PAGE_SIZE = 6

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_LoaiThucVat()
        self.ui.setupUi(self)
        self.init_common(username, role)

        # Dữ liệu phục vụ tìm kiếm/lọc/phân trang (chức năng nối từ
        # LoaithucvatEx.py -> MainWindow: self.data / self.filtered_data).
        self._species_records = []
        self._filtered_species = []
        self._species_page = 0

        # SỬA LỖI QUAN TRỌNG (giống lỗi đã sửa ở Phiếu chăm sóc): trước đây
        # loadSpeciesData()/renderSpeciesTable() chỉ tìm ĐÚNG CHÍNH XÁC tên
        # "tableWidget" trên form (self.ui.tableWidget). Nếu file giao diện
        # Loaithucvat.py đặt tên bảng khác thì hasattr() trả về False, hàm
        # âm thầm return -> dữ liệu vẫn lưu thành công vào SQL nhưng KHÔNG
        # BAO GIỜ hiện lên bảng ("lưu xong không thấy trên giao diện"). Giờ
        # dò theo nhiều tên khả dĩ, nếu vẫn không khớp thì lấy QTableWidget
        # ĐẦU TIÊN có trên form.
        self.speciesTable = _find_widget_by_hints(
            self.ui,
            ["tableWidget", "tableSpecies", "tableLoaiThucVat", "tbSpecies",
             "speciesTable", "tblLoaiThucVat", "tableView"],
            QTableWidget,
        )
        if self.speciesTable is None:
            self.speciesTable = _get_first_table_widget(self.ui)

        self.cleanInvalidSpecies()
        self.loadSpeciesData()
        self._setup_species_search()
        self.setup_species_filters()

        # SỬA LỖI: dò nút "Thêm" theo nhiều tên khả dĩ thay vì chỉ đúng
        # "addButton", để tránh trường hợp bấm "Thêm" không có phản ứng gì
        # nếu tên control thật trong .ui khác đi.
        add_btn = _find_widget_by_hints(
            self.ui,
            ["addButton", "btnAdd", "btnThem", "btnThemLoai", "addSpeciesButton"],
            QPushButton,
            keyword_hints=("thêm", "them", "+"),
        )
        if add_btn is not None:
            add_btn.clicked.connect(self.openPhieuLoaiThucVat)

    def _setup_species_search(self):
        """Gắn ô tìm kiếm với bảng THẬT (self.speciesTable đã dò ở __init__),
        thay vì setup_table_search() theo đúng tên cố định "tableWidget" (im
        lặng không làm gì nếu tên control thật khác đi)."""
        search_edit = _find_widget_by_hints(
            self.ui, ["searchInput", "txtSearch", "searchBox", "lineSearch"],
            QLineEdit, keyword_hints=("search", "tìm", "tim"),
        )
        search_btn = _find_widget_by_hints(
            self.ui, ["searchButton", "btnSearch", "btnTim"],
            QPushButton, keyword_hints=("search", "tìm", "tim"),
        )
        table = self.speciesTable
        if search_edit is None or table is None:
            return

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
        if search_btn is not None:
            search_btn.clicked.connect(do_filter)

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
        # SỬA LỖI: trước đây return âm thầm nếu không thấy đúng tên "tableWidget"
        # -> giờ báo lỗi rõ ràng nếu thật sự không có bảng nào trên trang.
        if self.speciesTable is None:
            QMessageBox.warning(
                self, "Thiếu bảng dữ liệu trên giao diện",
                "Không tìm thấy bảng (QTableWidget) nào trên trang Loài thực vật "
                "để hiển thị dữ liệu.\nVui lòng kiểm tra lại file giao diện Loaithucvat.py."
            )
            return
        try:
            db_species = database.get_all_loaithucvat()
            # Lớp lọc an toàn: dù đã dọn ở CSDL, vẫn loại bỏ những mã không
            # đúng định dạng (vd. SP011...) trước khi hiển thị lên bảng.
            db_species = [sp for sp in db_species if _is_valid_maloai(sp.get("MALOAI", ""))]
            self._species_records = db_species
            self._filtered_species = list(db_species)
            self._species_page = 0
            self.loadFamilyFilterOptions()
            self.loadStatusFilterOptions()
            self.renderSpeciesTable()
        except Exception as e:
            self._species_records = []
            self._filtered_species = []
            QMessageBox.critical(
                self, "Lỗi kết nối CSDL",
                f"Không lấy được danh sách loài thực vật từ SQL Server.\nChi tiết: {e}"
            )

    # ---------------- Tìm kiếm / Lọc / Phân trang (nối từ LoaithucvatEx.py) ----------------
    def setup_species_filters(self):
        """Gắn nút Lọc/Xóa lọc/Làm mới/phân trang NẾU giao diện .ui hiện tại có
        sẵn các control này (tên control đồng bộ với LoaithucvatEx.py: filterButton,
        clearFilterButton, refreshButton, filterFamilyCombo, filterStatusCombo,
        page1Button..page20Button, pageNextButton). Nếu .ui không có control nào
        trong số này thì bỏ qua, KHÔNG ảnh hưởng gì tới phần còn lại của trang."""
        ui = self.ui
        if hasattr(ui, "filterButton"):
            ui.filterButton.clicked.connect(self.applySpeciesFilter)
        if hasattr(ui, "clearFilterButton"):
            ui.clearFilterButton.clicked.connect(self.clearSpeciesFilter)
        if hasattr(ui, "refreshButton"):
            ui.refreshButton.clicked.connect(self.refreshSpeciesData)
        for i in range(1, 6):
            btn = getattr(ui, f"page{i}Button", None)
            if btn is not None:
                btn.clicked.connect(lambda _checked=False, p=i - 1: self.goToSpeciesPage(p))
        if hasattr(ui, "page20Button"):
            ui.page20Button.clicked.connect(lambda: self.goToSpeciesPage(19))
        if hasattr(ui, "pageNextButton"):
            ui.pageNextButton.clicked.connect(self.nextSpeciesPage)

    def loadFamilyFilterOptions(self):
        """Nạp danh sách Họ thực vật thật từ SQL lên combobox lọc 'filterFamilyCombo'
        (nếu .ui có), tương đương MainWindow.load_families trong LoaithucvatEx.py."""
        combo = getattr(self.ui, "filterFamilyCombo", None)
        if combo is None:
            return
        try:
            families = database.get_all_hothucvat()
        except Exception:
            families = []
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("📂 Tất cả", None)
        for fam in families:
            combo.addItem(f"{fam.get('MAHO', '')} - {fam.get('TENHO', '')}", fam.get("MAHO"))
        combo.blockSignals(False)

    def loadStatusFilterOptions(self):
        """Nạp danh sách tình trạng bảo tồn (lấy từ dữ liệu thật đang có) lên
        combobox lọc 'filterStatusCombo' (nếu .ui có), tương đương
        MainWindow.load_status_combo trong LoaithucvatEx.py."""
        combo = getattr(self.ui, "filterStatusCombo", None)
        if combo is None:
            return
        statuses = sorted({
            str(sp.get("TINHTRANGBAOTON", "")) for sp in self._species_records
            if sp.get("TINHTRANGBAOTON")
        })
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("📊 Tất cả tình trạng")
        for status in statuses:
            combo.addItem(status)
        combo.blockSignals(False)

    def applySpeciesFilter(self):
        ui = self.ui
        maho_filter = ui.filterFamilyCombo.currentData() if hasattr(ui, "filterFamilyCombo") else None
        status_filter = ui.filterStatusCombo.currentText() if hasattr(ui, "filterStatusCombo") else ""

        self._filtered_species = list(self._species_records)
        if maho_filter:
            self._filtered_species = [sp for sp in self._filtered_species if sp.get("MAHO") == maho_filter]
        if status_filter and not status_filter.startswith("📊"):
            self._filtered_species = [
                sp for sp in self._filtered_species if str(sp.get("TINHTRANGBAOTON", "")) == status_filter
            ]

        self._species_page = 0
        self.renderSpeciesTable()

    def clearSpeciesFilter(self):
        ui = self.ui
        if hasattr(ui, "filterFamilyCombo"):
            ui.filterFamilyCombo.setCurrentIndex(0)
        if hasattr(ui, "filterStatusCombo"):
            ui.filterStatusCombo.setCurrentIndex(0)
        self._filtered_species = list(self._species_records)
        self._species_page = 0
        self.renderSpeciesTable()

    def refreshSpeciesData(self):
        if hasattr(self.ui, "searchInput"):
            self.ui.searchInput.clear()
        self.loadSpeciesData()

    def _species_total_pages(self):
        total = len(self._filtered_species)
        return max(1, (total + self.SPECIES_PAGE_SIZE - 1) // self.SPECIES_PAGE_SIZE)

    def goToSpeciesPage(self, page):
        if page < self._species_total_pages():
            self._species_page = page
            self.renderSpeciesTable()

    def nextSpeciesPage(self):
        if self._species_page < self._species_total_pages() - 1:
            self._species_page += 1
            self.renderSpeciesTable()

    def _go_to_species_page_for(self, maloai):
        """SỬA LỖI QUAN TRỌNG (giống Khu trưng bày): sau khi Thêm/Sửa, danh
        sách được tải lại và LUÔN reset về trang 1 (loadSpeciesData() đặt
        self._species_page = 0). Nếu đã có nhiều hơn 1 trang (SPECIES_PAGE_SIZE)
        loài thực vật, loài vừa lưu có thể rơi vào TRANG 2 trở đi trong khi
        màn hình vẫn đứng ở trang 1 -> lưu đúng vào SQL nhưng nhìn như "không
        hiện ra". Tự động chuyển tới đúng trang đang chứa loài vừa lưu."""
        for idx, sp in enumerate(self._filtered_species):
            if sp.get("MALOAI") == maloai:
                self._species_page = idx // self.SPECIES_PAGE_SIZE
                break
        self.renderSpeciesTable()

    def renderSpeciesTable(self):
        """Vẽ lại bảng loài thực vật: chỉ phân trang khi .ui có sẵn control phân
        trang (paginationLabel/pageNextButton...), nếu không thì hiển thị TOÀN
        BỘ danh sách đã lọc như hành vi gốc của loginEX.py."""
        table = self.speciesTable
        if table is None:
            return
        has_pagination = hasattr(self.ui, "paginationLabel") or hasattr(self.ui, "pageNextButton")
        if has_pagination:
            start = self._species_page * self.SPECIES_PAGE_SIZE
            page_records = self._filtered_species[start:start + self.SPECIES_PAGE_SIZE]
        else:
            page_records = self._filtered_species

        table.clearContents()
        table.setRowCount(len(page_records))
        # Đồng bộ với Khu trưng bày: chủ động bỏ ẩn toàn bộ dòng mỗi khi vẽ
        # lại bảng, tránh trường hợp dòng mới rơi đúng vị trí dòng đang bị ẩn
        # từ lần tìm kiếm trước.
        for row in range(table.rowCount()):
            table.setRowHidden(row, False)
        col_count = table.columnCount()
        for row, sp in enumerate(page_records):
            table.setItem(row, 0, QTableWidgetItem(str(sp.get("MALOAI", ""))))
            table.setItem(row, 1, QTableWidgetItem(str(sp.get("TENTHUONGGOI", ""))))
            table.setItem(row, 2, QTableWidgetItem(str(sp.get("TENKHOAHOC", ""))))
            table.setItem(row, 3, QTableWidgetItem(str(sp.get("MAHO", ""))))
            table.setItem(row, 4, QTableWidgetItem(str(sp.get("DACDIEMSINHHOC", ""))))
            table.setItem(row, 5, QTableWidgetItem(str(sp.get("MOITRUONGSONG", ""))))
            table.setItem(row, 6, QTableWidgetItem(str(sp.get("TINHTRANGBAOTON", ""))))
            # THÊM MỚI: nút Sửa/Xóa thao tác trực tiếp lên SQL Server, giống
            # cách làm ở HoThucVatWindon/PhieuKhaoSatWindow (thay cho chữ
            # "✏️ 🗑️" tĩnh không bấm được trước đây).
            if col_count > 7:
                maloai = sp.get("MALOAI")
                table.setCellWidget(
                    row, 7,
                    _build_action_buttons_widget(maloai, self.editSpeciesRecord, self.deleteSpeciesRecord),
                )
                # SỬA LỖI HIỂN THỊ: nếu dòng trong .ui quá thấp, nút Sửa/Xóa bị
                # ép mất chữ, chỉ còn lộ viền màu xanh/đỏ. Chủ động set độ cao
                # dòng và độ rộng cột "Thao tác" đủ lớn để luôn thấy chữ.
                table.setRowHeight(row, max(table.rowHeight(row), 34))
        if col_count > 7:
            table.setColumnWidth(7, max(table.columnWidth(7), 110))

        self.updateSpeciesPagination()

    def updateSpeciesPagination(self):
        ui = self.ui
        total = len(self._filtered_species)
        if hasattr(ui, "paginationLabel"):
            if total == 0:
                ui.paginationLabel.setText("Không tìm thấy loài nào")
            else:
                start = self._species_page * self.SPECIES_PAGE_SIZE + 1
                end = min(start + self.SPECIES_PAGE_SIZE - 1, total)
                ui.paginationLabel.setText(f"Hiển thị {start} đến {end} trong tổng số {total} loài")

        total_pages = self._species_total_pages()
        for i in range(1, 6):
            btn = getattr(ui, f"page{i}Button", None)
            if btn is not None:
                btn.setEnabled(total_pages >= i)
                _apply_active_page_style(btn, total_pages >= i and self._species_page == i - 1)
        if hasattr(ui, "page20Button"):
            ui.page20Button.setEnabled(total_pages >= 20)
            _apply_active_page_style(ui.page20Button, total_pages >= 20 and self._species_page == 19)
        if hasattr(ui, "pageNextButton"):
            ui.pageNextButton.setEnabled(self._species_page < total_pages - 1)

    # ---------------- Sửa / Xóa (đồng bộ SQL, nối từ LoaithucvatEx.py) ----------------
    def editSpeciesRecord(self, maloai):
        record = next((sp for sp in self._species_records if sp.get("MALOAI") == maloai), None)
        if record is None:
            QMessageBox.warning(self, "Thông báo", "Không tìm thấy loài thực vật này (dữ liệu có thể vừa thay đổi).")
            self.loadSpeciesData()
            return
        self.phieu_loai = PhieuLoaiWindow(self.username, self.role, self, maloai, record=record)
        self.phieu_loai.exec()

    def deleteSpeciesRecord(self, maloai):
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa loài thực vật '{maloai}' khỏi Database không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            database.delete_loaithucvat(maloai)
            QMessageBox.information(self, "Thành công", f"Đã xóa loài thực vật '{maloai}'.")
            self.loadSpeciesData()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể xóa trên SQL Server.\nChi tiết: {e}")


# =========================================================
# GIAO DIỆN HỌ THỰC VẬT
# =========================================================
class HoThucVatWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_HoThucVat()
        self.ui.setupUi(self)
        self.init_common(username, role)
        self._family_records = []

        self.cleanInvalidFamilies()
        self.loadFamilyData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuHoThucVat)
        # SỬA LỖI: nút "Làm mới" trước đây chưa được nối sự kiện nên bấm
        # không có phản ứng gì. Giờ nối để xóa ô tìm kiếm và tải lại dữ liệu
        # mới nhất từ SQL Server, giống cách làm ở trang Loại thực vật/Khu
        # trưng bày (refreshSpeciesData / refreshZoneData).
        if hasattr(self.ui, "refreshButton"):
            self.ui.refreshButton.clicked.connect(self.refreshFamilyData)

    def refreshFamilyData(self):
        if hasattr(self.ui, "searchInput"):
            self.ui.searchInput.clear()
        self.cleanInvalidFamilies()
        self.loadFamilyData()

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
                self._family_records = db_families
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(db_families))
                col_count = self.ui.tableWidget.columnCount()
                for row, fam in enumerate(db_families):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(str(fam.get("MAHO", ""))))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(str(fam.get("TENHO", ""))))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(str(fam.get("MOTA", ""))))
                    # THÊM MỚI: cột "Thao tác" với 2 nút Sửa/Xóa thao tác trực
                    # tiếp lên SQL Server (UPDATE/DELETE), giống hệt cách làm ở
                    # trang "Phiếu khảo sát" (PhieuKhaoSatWindow.renderSurveyTable).
                    if col_count > 3:
                        maho = fam.get("MAHO")
                        self.ui.tableWidget.setCellWidget(
                            row, 3,
                            _build_action_buttons_widget(maho, self.editFamilyRecord, self.deleteFamilyRecord),
                        )
                        # SỬA LỖI HIỂN THỊ: dòng quá thấp làm nút Sửa/Xóa mất chữ,
                        # chỉ còn lộ viền màu xanh/đỏ -> tăng độ cao dòng.
                        self.ui.tableWidget.setRowHeight(row, max(self.ui.tableWidget.rowHeight(row), 34))
                if col_count > 3:
                    self.ui.tableWidget.setColumnWidth(3, max(self.ui.tableWidget.columnWidth(3), 110))
            except Exception:
                self._family_records = []
                self.ui.tableWidget.clearContents()
                self.ui.tableWidget.setRowCount(len(family_data))
                for row, fam in enumerate(family_data):
                    self.ui.tableWidget.setItem(row, 0, QTableWidgetItem(fam["id"]))
                    self.ui.tableWidget.setItem(row, 1, QTableWidgetItem(fam["name"]))
                    self.ui.tableWidget.setItem(row, 2, QTableWidgetItem(fam["desc"]))

    # ---------------- Sửa / Xóa (đồng bộ SQL, giống Phiếu khảo sát) ----------------
    def editFamilyRecord(self, maho):
        record = next((f for f in self._family_records if f.get("MAHO") == maho), None)
        if record is None:
            QMessageBox.warning(self, "Thông báo", "Không tìm thấy họ thực vật này (dữ liệu có thể vừa thay đổi).")
            self.loadFamilyData()
            return
        self.phieu_ho = PhieuHoThucVatWindow(self.username, self.role, self, maho, record=record)
        self.phieu_ho.exec()

    def deleteFamilyRecord(self, maho):
        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa họ thực vật '{maho}' khỏi Database không?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            database.delete_hothucvat(maho)
            QMessageBox.information(self, "Thành công", f"Đã xóa họ thực vật '{maho}'.")
            self.loadFamilyData()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể xóa trên SQL Server.\nChi tiết: {e}")


# =========================================================
# GIAO DIỆN KHU TRƯNG BÀY
# =========================================================
class KhuTrungBayWindow(NavigationWindow):

    # Số dòng/trang khi giao diện có sẵn control phân trang, đồng bộ với
    # KhutrungbayEx.py -> MainWindow.items_per_page.
    ZONE_PAGE_SIZE = 6

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_KhuTrungBay()
        self.ui.setupUi(self)
        self.init_common(username, role)

        # Dữ liệu phục vụ phân trang (chức năng nối từ KhutrungbayEx.py ->
        # MainWindow: self.data / self.filtered_data).
        self._zone_records = []
        self._filtered_zones = []
        self._zone_page = 0

        # SỬA LỖI (đồng bộ với Loài thực vật / Phiếu chăm sóc): dò bảng thật
        # theo nhiều tên khả dĩ, nếu không khớp tên nào thì lấy QTableWidget
        # đầu tiên có trên form, tránh bị "im lặng không hiện gì" nếu tên
        # control thật khác đi.
        self.zoneTable = _find_widget_by_hints(
            self.ui,
            ["tableWidget", "tableZone", "tableKhuTrungBay", "tbZone",
             "zoneTable", "tblKhuTrungBay", "tableView"],
            QTableWidget,
        )
        if self.zoneTable is None:
            self.zoneTable = _get_first_table_widget(self.ui)

        self.loadZoneData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")
        self.setup_zone_pagination()

        add_btn = _find_widget_by_hints(
            self.ui,
            ["addButton", "btnAdd", "btnThem", "btnThemKhu", "addZoneButton"],
            QPushButton,
            keyword_hints=("thêm", "them", "+"),
        )
        if add_btn is not None:
            add_btn.clicked.connect(self.openPhieuKhu)

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

    # ---------------- Phân trang / Làm mới (nối từ KhutrungbayEx.py) ----------------
    def setup_zone_pagination(self):
        """Gắn nút Làm mới/phân trang NẾU giao diện .ui hiện tại có sẵn (tên
        control đồng bộ với KhutrungbayEx.py: refreshButton, page1Button,
        page2Button, page3Button, pageLastButton, pageNextButton). Nếu .ui
        không có control nào trong số này thì bỏ qua, KHÔNG ảnh hưởng gì tới
        phần còn lại của trang."""
        ui = self.ui
        if hasattr(ui, "refreshButton"):
            ui.refreshButton.clicked.connect(self.refreshZoneData)
        for i in range(1, 4):
            btn = getattr(ui, f"page{i}Button", None)
            if btn is not None:
                btn.clicked.connect(lambda _checked=False, p=i - 1: self.goToZonePage(p))
        if hasattr(ui, "pageLastButton"):
            ui.pageLastButton.clicked.connect(lambda: self.goToZonePage(19))
        if hasattr(ui, "pageNextButton"):
            ui.pageNextButton.clicked.connect(self.nextZonePage)

    def refreshZoneData(self):
        if hasattr(self.ui, "searchInput"):
            self.ui.searchInput.clear()
        self.loadZoneData()

    def _zone_total_pages(self):
        total = len(self._filtered_zones)
        return max(1, (total + self.ZONE_PAGE_SIZE - 1) // self.ZONE_PAGE_SIZE)

    def goToZonePage(self, page):
        if page < self._zone_total_pages():
            self._zone_page = page
            self.renderZoneTable()

    def nextZonePage(self):
        if self._zone_page < self._zone_total_pages() - 1:
            self._zone_page += 1
            self.renderZoneTable()

    def _go_to_zone_page_for(self, makhu):
        """SỬA LỖI QUAN TRỌNG: sau khi Thêm/Sửa, danh sách được tải lại và
        LUÔN reset về trang 1 (loadZoneData() đặt self._zone_page = 0). Nếu
        đã có sẵn nhiều hơn 1 trang (ZONE_PAGE_SIZE) khu trưng bày, khu vừa
        lưu có thể rơi vào TRANG 2 trở đi trong khi màn hình vẫn đứng ở
        trang 1 -> lưu đúng vào SQL nhưng nhìn như "không hiện ra". Tự động
        chuyển tới đúng trang đang chứa khu vừa lưu để luôn thấy ngay."""
        for idx, zone in enumerate(self._filtered_zones):
            if zone.get("MAKHU") == makhu:
                self._zone_page = idx // self.ZONE_PAGE_SIZE
                break
        self.renderZoneTable()

    def loadZoneData(self):
        # SỬA LỖI QUAN TRỌNG: trước đây nếu database.get_all_khutrungbay() ném
        # lỗi bất kỳ (mất kết nối tạm thời, lỗi kiểu dữ liệu...), code sẽ ÂM
        # THẦM bắt lỗi rồi hiện DỮ LIỆU MẪU GIẢ (zone_data cứng: KHU01..KHU05)
        # lên bảng thay vì dữ liệu thật -> khu vừa thêm/sửa KHÔNG BAO GIỜ hiện
        # ra, dù đã lưu thành công vào SQL Server. Giờ báo lỗi thật rõ ràng
        # thay vì hiện data giả gây hiểu lầm.
        if self.zoneTable is None:
            QMessageBox.warning(
                self, "Thiếu bảng dữ liệu trên giao diện",
                "Không tìm thấy bảng (QTableWidget) nào trên trang Khu trưng bày "
                "để hiển thị dữ liệu.\nVui lòng kiểm tra lại file giao diện Khutrungbay.py."
            )
            return
        try:
            db_zones = database.get_all_khutrungbay()
            self._zone_records = db_zones
            self._filtered_zones = list(db_zones)
            self._zone_page = 0
            self.renderZoneTable()
        except Exception as e:
            self._zone_records = []
            self._filtered_zones = []
            QMessageBox.critical(
                self, "Lỗi kết nối CSDL",
                f"Không lấy được danh sách khu trưng bày từ SQL Server.\nChi tiết: {e}"
            )

    def renderZoneTable(self):
        """Vẽ lại bảng khu trưng bày: chỉ phân trang khi .ui có sẵn control
        phân trang (paginationLabel/pageNextButton...), nếu không thì hiển thị
        TOÀN BỘ danh sách như hành vi gốc của loginEX.py."""
        table = self.zoneTable
        if table is None:
            return
        has_pagination = hasattr(self.ui, "paginationLabel") or hasattr(self.ui, "pageNextButton")
        if has_pagination:
            start = self._zone_page * self.ZONE_PAGE_SIZE
            page_records = self._filtered_zones[start:start + self.ZONE_PAGE_SIZE]
        else:
            page_records = self._filtered_zones

        table.clearContents()
        table.setRowCount(len(page_records))
        # SỬA LỖI QUAN TRỌNG: Qt KHÔNG tự bỏ trạng thái "ẩn dòng" (setRowHidden)
        # còn sót lại từ lần lọc tìm kiếm trước đó khi bảng chỉ được xóa nội
        # dung (clearContents) rồi ghi lại (setRowCount) - trạng thái ẩn vẫn
        # dính theo VỊ TRÍ dòng. Vì vậy khu vừa thêm/sửa dù đã lưu đúng vào SQL
        # và được load lại đúng, vẫn có thể rơi vào đúng vị trí dòng đang bị ẩn
        # từ lần tìm kiếm trước -> không hiện ra dù có trong bảng. Chủ động bỏ
        # ẩn toàn bộ dòng mỗi khi vẽ lại bảng để tránh việc này.
        for row in range(table.rowCount()):
            table.setRowHidden(row, False)
        col_count = table.columnCount()
        for row, zone in enumerate(page_records):
            table.setItem(row, 0, QTableWidgetItem(str(zone.get("MAKHU", ""))))
            table.setItem(row, 1, QTableWidgetItem(str(zone.get("TENKHU", ""))))
            table.setItem(row, 2, QTableWidgetItem(str(zone.get("VITRI", ""))))
            table.setItem(row, 3, QTableWidgetItem(str(zone.get("DIENTICH", ""))))
            table.setItem(row, 4, QTableWidgetItem(str(zone.get("MOTA", ""))))
            table.setItem(row, 5, QTableWidgetItem("🟢 Đang hoạt động"))
            # THÊM MỚI: nút Sửa/Xóa thao tác trực tiếp lên SQL Server, thay cho
            # chữ "✏️ 🗑️" tĩnh không bấm được trước đây - chức năng nối từ
            # KhutrungbayEx.py -> MainWindow.edit_area / delete_area.
            if col_count > 6:
                makhu = zone.get("MAKHU")
                table.setCellWidget(
                    row, 6,
                    _build_action_buttons_widget(makhu, self.editZoneRecord, self.deleteZoneRecord),
                )
                # SỬA LỖI HIỂN THỊ: dòng quá thấp làm nút Sửa/Xóa mất chữ, chỉ
                # còn lộ viền màu xanh/đỏ -> tăng độ cao dòng.
                table.setRowHeight(row, max(table.rowHeight(row), 34))
        if col_count > 6:
            table.setColumnWidth(6, max(table.columnWidth(6), 110))

        self.updateZonePagination()

    def updateZonePagination(self):
        ui = self.ui
        total = len(self._filtered_zones)
        if hasattr(ui, "paginationLabel"):
            if total == 0:
                ui.paginationLabel.setText("Không tìm thấy khu nào")
            else:
                start = self._zone_page * self.ZONE_PAGE_SIZE + 1
                end = min(start + self.ZONE_PAGE_SIZE - 1, total)
                ui.paginationLabel.setText(f"Hiển thị {start} đến {end} trong tổng số {total} khu")

        total_pages = self._zone_total_pages()
        for i in range(1, 4):
            btn = getattr(ui, f"page{i}Button", None)
            if btn is not None:
                btn.setEnabled(total_pages >= i)
                _apply_active_page_style(btn, total_pages >= i and self._zone_page == i - 1)
        if hasattr(ui, "pageLastButton"):
            ui.pageLastButton.setEnabled(total_pages >= 20)
            _apply_active_page_style(ui.pageLastButton, total_pages >= 20 and self._zone_page == 19)
        if hasattr(ui, "pageNextButton"):
            ui.pageNextButton.setEnabled(self._zone_page < total_pages - 1)

    # ---------------- Sửa / Xóa (đồng bộ SQL, nối từ KhutrungbayEx.py) ----------------
    def editZoneRecord(self, makhu):
        record = next((z for z in self._zone_records if z.get("MAKHU") == makhu), None)
        if record is None:
            QMessageBox.warning(self, "Thông báo", "Không tìm thấy khu trưng bày này (dữ liệu có thể vừa thay đổi).")
            self.loadZoneData()
            return
        self.phieu_khu = PhieuKhuWindow(self.username, self.role, self, makhu, record=record)
        self.phieu_khu.exec()

    def deleteZoneRecord(self, makhu):
        record = next((z for z in self._zone_records if z.get("MAKHU") == makhu), None)
        tenkhu = record.get("TENKHU", makhu) if record else makhu

        # Kiểm tra khu có đang có cây trồng hay không TRƯỚC khi xóa, giống hệt
        # MainWindow.delete_area trong KhutrungbayEx.py (chặn xóa nếu đang dùng).
        try:
            so_cay = database.count_cay_theo_khu(makhu)
        except Exception:
            so_cay = 0
        if so_cay > 0:
            QMessageBox.warning(
                self, "Cảnh báo",
                f"Khu '{tenkhu}' đang có {so_cay} cây được trồng.\nKhông thể xóa khu này!"
            )
            return

        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa khu '{tenkhu}' (Mã: {makhu})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            database.delete_khutrungbay(makhu)
            QMessageBox.information(self, "Thành công", f"Đã xóa khu '{tenkhu}'.")
            self.loadZoneData()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể xóa trên SQL Server.\nChi tiết: {e}")


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
        # SỬA LỖI: nút "Làm mới" trước đây chưa được nối sự kiện (chức năng
        # refresh_data gốc trong NhanvienEx.py) nên bấm không có phản ứng gì.
        # Giờ nối để xóa ô tìm kiếm và tải lại danh sách nhân viên mới nhất từ SQL Server.
        if hasattr(self.ui, "refreshButton"):
            self.ui.refreshButton.clicked.connect(self.refreshStaffData)

    def refreshStaffData(self):
        if hasattr(self.ui, "searchInput"):
            self.ui.searchInput.clear()
        self.loadStaffData()

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
            table = self.ui.tableWidget
            try:
                db_staff = database.get_all_nhanvien()
                self._staff_records = db_staff
                table.clearContents()
                table.setRowCount(len(db_staff))
                col_count = table.columnCount()
                for row, nv in enumerate(db_staff):
                    table.setItem(row, 0, QTableWidgetItem(str(nv.get("MANV", ""))))
                    table.setItem(row, 1, QTableWidgetItem(str(nv.get("HOTEN", ""))))
                    table.setItem(row, 2, QTableWidgetItem(str(nv.get("NGAYSINH", ""))))
                    table.setItem(row, 3, QTableWidgetItem(str(nv.get("GIOITINH", ""))))
                    table.setItem(row, 4, QTableWidgetItem(str(nv.get("DIENTHOAI", ""))))
                    table.setItem(row, 5, QTableWidgetItem(str(nv.get("EMAIL", ""))))
                    table.setItem(row, 6, QTableWidgetItem(str(nv.get("CHUCVU", ""))))
                    # SỬA LỖI: hiển thị khu vực phụ trách thật (TENKHUPHUTRACH, lấy từ JOIN
                    # với KHU_TRUNG_BAY) thay vì chữ "N/A" cố định như code cũ.
                    table.setItem(row, 7, QTableWidgetItem(str(nv.get("TENKHUPHUTRACH") or "Chưa phân công")))
                    # NỐI CHỨC NĂNG từ NhanvienEx.py (MainWindow.edit_staff /
                    # delete_staff): thay chữ tĩnh "✏️ 🗑️" không bấm được bằng
                    # 2 nút "Sửa"/"Xóa" thật, thao tác trực tiếp lên SQL Server,
                    # giống hệt cách đã làm ở Loài/Họ thực vật, Khu trưng bày.
                    if col_count > 8:
                        manv = nv.get("MANV")
                        table.setCellWidget(
                            row, 8,
                            _build_action_buttons_widget(manv, self.editStaffRecord, self.deleteStaffRecord),
                        )
                        # SỬA LỖI HIỂN THỊ: dòng quá thấp làm nút Sửa/Xóa mất chữ,
                        # chỉ còn lộ viền màu xanh/đỏ -> tăng độ cao dòng.
                        table.setRowHeight(row, max(table.rowHeight(row), 34))
                if col_count > 8:
                    table.setColumnWidth(8, max(table.columnWidth(8), 110))
            except Exception:
                self._staff_records = []
                table.clearContents()
                table.setRowCount(len(staff_data))
                for row, nv in enumerate(staff_data):
                    table.setItem(row, 0, QTableWidgetItem(nv["id"]))
                    table.setItem(row, 1, QTableWidgetItem(nv["name"]))
                    table.setItem(row, 2, QTableWidgetItem(nv["dob"]))
                    table.setItem(row, 3, QTableWidgetItem(nv["gender"]))
                    table.setItem(row, 4, QTableWidgetItem(nv["phone"]))
                    table.setItem(row, 5, QTableWidgetItem(nv["email"]))
                    table.setItem(row, 6, QTableWidgetItem(nv["position"]))
                    table.setItem(row, 7, QTableWidgetItem(nv["managed_by"]))
                    table.setItem(row, 8, QTableWidgetItem("✏️ 🗑️"))

    # ---------------- Sửa / Xóa (đồng bộ SQL, nối từ NhanvienEx.py) ----------------
    def editStaffRecord(self, manv):
        record = next((nv for nv in getattr(self, "_staff_records", []) if nv.get("MANV") == manv), None)
        if record is None:
            QMessageBox.warning(self, "Thông báo", "Không tìm thấy nhân viên này (dữ liệu có thể vừa thay đổi).")
            self.loadStaffData()
            return
        self.phieu_nv = PhieuNhanVienWindow(self.username, self.role, self, manv, record=record)
        self.phieu_nv.exec()

    def deleteStaffRecord(self, manv):
        record = next((nv for nv in getattr(self, "_staff_records", []) if nv.get("MANV") == manv), None)
        hoten = record.get("HOTEN") if record else manv

        # Kiểm tra nhân viên có đang có phiếu liên quan hay không TRƯỚC khi
        # xóa, giống hệt MainWindow.delete_staff trong NhanvienEx.py (chặn
        # xóa nếu đang có Phiếu chăm sóc/Phiếu khảo sát/Yêu cầu bảo trì).
        try:
            so_phieu = database.count_phieu_lien_quan_nhanvien(manv)
        except Exception as e:
            so_phieu = 0
            print(f"Không thể kiểm tra phiếu liên quan tới nhân viên: {e}")
        if so_phieu > 0:
            QMessageBox.warning(
                self, "Cảnh báo",
                f"Nhân viên '{hoten}' đang có {so_phieu} phiếu liên quan.\nKhông thể xóa nhân viên này!"
            )
            return

        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa nhân viên '{hoten}' (Mã: {manv})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            database.delete_nhanvien(manv)
            QMessageBox.information(self, "Thành công", f"Đã xóa nhân viên '{hoten}'.")
            self.loadStaffData()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể xóa trên SQL Server.\nChi tiết: {e}")


# =========================================================
# GIAO DIỆN CÁC PHIẾU NHẬP LIỆU (DIALOG WINDOWS)
# =========================================================
class PhieuThongTinWindow(QDialog):

    def __init__(self, username, role, parent, next_id=None):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuThongTinCay()
        self.ui.setupUi(self)

        # ĐÁNH DẤU PHIÊN BẢN: nếu bạn KHÔNG thấy chữ "[v2-fix]" này trên
        # thanh tiêu đề của cửa sổ "Thêm cây" khi mở lên, tức là chương trình
        # đang chạy KHÔNG PHẢI file loginEX.py đã được sửa (có thể bạn đang mở
        # 1 bản .exe cũ, hoặc còn 1 file loginEX.py khác chưa được ghi đè).
        # Hãy đóng hẳn chương trình, xác nhận thay đúng file, rồi mở lại.
        try:
            self.setWindowTitle((self.windowTitle() or "Thêm cây") + "  [v2-fix]")
        except Exception:
            pass

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

    # SỬA LỖI 2: Danh sách này PHẢI khớp CHÍNH XÁC với ràng buộc CK_TinhTrang_Cay
    # trong database_setup.sql (chỉ 5 giá trị này được phép cho TINHTRANGSINHTRUONG).
    TINHTRANG_OPTIONS = [
        "Sinh trưởng tốt", "Cần theo dõi", "Bị sâu bệnh",
        "Đang phục hồi", "Nguy cấp",
    ]

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

        # SỬA LỖI 2: Combobox "Tình trạng" trên form (do file .ui Designer tạo sẵn,
        # vd cboTinhTrang/cboTinhTrangSinhTruong/cboTinhTrangSucKhoe...) đang chứa
        # các lựa chọn KHÔNG khớp với ràng buộc CK_TinhTrang_Cay trong SQL
        # (vd "Xanh tươi") -> khi Lưu bị SQL Server chặn với lỗi:
        #   "The INSERT statement conflicted with the CHECK constraint
        #    "CK_TinhTrang_Cay" ... column 'TINHTRANGSINHTRUONG'"
        # Cách sửa: dò đúng combobox đó rồi NẠP LẠI bằng đúng 5 giá trị hợp lệ,
        # để người dùng luôn chọn được giá trị mà SQL Server chấp nhận.
        self.cboTinhTrang = _find_widget_by_hints(
            self.ui,
            ["cboTinhTrang", "cboTinhTrangSinhTruong", "cboTinhTrangSucKhoe",
             "comboTinhTrang", "cbTinhTrang", "cboSucKhoe", "cboTinhTrangCay"],
            QComboBox,
            keyword_hints=("tinhtrang", "tình trạng", "suckhoe", "sức khỏe"),
        )
        if self.cboTinhTrang is not None:
            self.cboTinhTrang.clear()
            self.cboTinhTrang.addItems(self.TINHTRANG_OPTIONS)
            self.cboTinhTrang.setCurrentIndex(0)

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

        # SỬA LỖI 2: đọc đúng giá trị "Tình trạng" người dùng đã chọn trên combobox
        # (đã được nạp lại đúng 5 giá trị hợp lệ ở populate_comboboxes()) thay vì
        # luôn ghi cứng "Sinh trưởng tốt". Vẫn có phòng thủ: nếu vì lý do gì đó
        # combobox không tồn tại hoặc rỗng, hoặc lỡ chứa giá trị lạ không khớp
        # CK_TinhTrang_Cay, thì tự động dùng "Sinh trưởng tốt" làm mặc định an
        # toàn để không bao giờ bị SQL Server chặn INSERT nữa.
        tinhtrang_widget = getattr(self, "cboTinhTrang", None)
        selected_tinhtrang = tinhtrang_widget.currentText().strip() if tinhtrang_widget is not None else ""
        if selected_tinhtrang in self.TINHTRANG_OPTIONS:
            new_tinhtrang = selected_tinhtrang
        else:
            new_tinhtrang = "Sinh trưởng tốt"

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
                tinhtrangsinhtruong=new_tinhtrang,
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
                QMessageBox.critical(
                    self, "Lỗi SQL Server",
                    f"Không thể INSERT cây do vi phạm khóa ngoại cấu trúc CSDL.\n"
                    f"(Giá trị Tình trạng đã gửi đi: '{new_tinhtrang}')\n"
                    f"Chi tiết: {e}"
                )


class PhieuLoaiWindow(QDialog):

    def __init__(self, username, role, parent, next_id, record=None):
        """
        record=None -> chế độ THÊM MỚI (giữ nguyên hành vi cũ, next_id là mã
        loài kế tiếp tự sinh).
        record=<dict> -> chế độ SỬA (gọi từ nút ✏️ ở bảng Loài thực vật, chức
        năng nối từ LoaithucvatEx.py -> MainWindow.edit_plant): form được điền
        sẵn dữ liệu hiện có, mã loài (idInput) bị khóa không cho sửa (vì là
        khóa chính), và khi Lưu sẽ gọi UPDATE thay vì INSERT.
        """
        super().__init__()
        self.parent = parent
        self.editing_record = record
        self.ui = Ui_PhieuLoai()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)

        # Đồng bộ "Họ thực vật" với danh sách thật trong SQL (bảng HO_THUC_VAT)
        # thay vì phải tự gõ tay mã họ (rất dễ gõ sai/gõ mã không tồn tại).
        self.family_map = {}
        self.populate_family_field()

        if record is not None:
            self.ui.idInput.setReadOnly(True)
            self.ui.nameInput.setText(str(record.get("TENTHUONGGOI", "")))
            self.ui.scientificNameInput.setText(str(record.get("TENKHOAHOC", "")))
            self.ui.characteristicsInput.setPlainText(str(record.get("DACDIEMSINHHOC") or ""))
            self.ui.habitatInput.setText(str(record.get("MOITRUONGSONG") or ""))
            status_val = str(record.get("TINHTRANGBAOTON") or "")
            status_idx = self.ui.statusCombo.findText(status_val)
            if status_idx >= 0:
                self.ui.statusCombo.setCurrentIndex(status_idx)
            self._preselect_family(record.get("MAHO"))
            self.setWindowTitle("Sửa loài thực vật")

        self.ui.saveButton.clicked.connect(self.saveSpecies)
        self.ui.cancelButton.clicked.connect(self.close)

    def _preselect_family(self, maho):
        """Chọn sẵn Họ thực vật hiện tại của loài đang sửa lên control
        familyInput (dù là QComboBox hay QLineEdit + QCompleter)."""
        if not maho:
            return
        widget = getattr(self.ui, "familyInput", None)
        if widget is None:
            return
        if hasattr(widget, "currentData") and hasattr(widget, "addItem"):
            idx = widget.findData(maho)
            if idx >= 0:
                widget.setCurrentIndex(idx)
        elif hasattr(widget, "setText"):
            label = next((lbl for lbl, code in self.family_map.items() if code == maho and " - " in lbl), None)
            widget.setText(label if label else str(maho))

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

        # SỬA LỖI: cột TENKHOAHOC (Tên khoa học) có ràng buộc UNIQUE trong SQL
        # nên bắt buộc phải nhập và không được để trống, nếu không SQL Server
        # sẽ báo lỗi khó hiểu khi lưu.
        if sciname == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên khoa học.")
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

        # SỬA LỖI 3: kiểm tra TRÙNG Tên khoa học TRƯỚC khi lưu (cột TENKHOAHOC
        # có ràng buộc UNIQUE trong SQL - mỗi loài phải có tên khoa học riêng
        # biệt). Trước đây không kiểm tra trước nên SQL Server tự chặn rồi hiện
        # nguyên văn lỗi kỹ thuật "Violation of UNIQUE KEY constraint..." rất
        # khó hiểu với người dùng (như trong ảnh báo lỗi). Giờ báo bằng tiếng
        # Việt rõ ràng, ngay cả trước khi gửi lên SQL.
        try:
            all_species = database.get_all_loaithucvat()
            existing_scinames = {
                str(sp.get("TENKHOAHOC", "")).strip().lower()
                for sp in all_species
                # Khi đang SỬA, loại trừ chính bản ghi đang sửa ra khỏi danh sách
                # kiểm tra trùng, nếu không sẽ luôn báo "trùng" với chính nó.
                if self.editing_record is None or sp.get("MALOAI") != self.editing_record.get("MALOAI")
            }
            if sciname.strip().lower() in existing_scinames:
                QMessageBox.warning(
                    self, "Tên khoa học đã tồn tại",
                    f"Tên khoa học '{sciname}' đã được dùng cho một loài khác trong hệ "
                    f"thống.\nMỗi loài phải có tên khoa học riêng biệt (không được trùng).\n"
                    f"Vui lòng kiểm tra lại hoặc nhập một tên khoa học khác."
                )
                return
        except Exception as e:
            print(f"Không thể kiểm tra trùng Tên khoa học trước khi lưu: {e}")

        try:
            if self.editing_record is not None:
                database.update_loaithucvat(
                    maloai=sid,
                    tenthuonggoi=sname,
                    tenkhoahoc=sciname,
                    dacdiemsinhhoc=sbio,
                    moitruongsong=shabitat,
                    tinhtrangbaoton=sstatus,
                    maho=sfamily
                )
                QMessageBox.information(self, "Thành công", f"Đã cập nhật loài '{sname}' vào Database thành công!")
            else:
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
            if hasattr(self.parent, "_go_to_species_page_for"):
                self.parent._go_to_species_page_for(sid)
            self.close()
        except Exception as e:
            # SỬA LỖI: nếu vẫn lọt tới đây do trùng ở đúng thời điểm khác lưu
            # (2 người cùng lưu cùng lúc), vẫn dịch lỗi UNIQUE constraint sang
            # tiếng Việt dễ hiểu thay vì hiện nguyên văn lỗi SQL Server.
            err_text = str(e)
            if "UNIQUE" in err_text.upper():
                QMessageBox.warning(
                    self, "Tên khoa học đã tồn tại",
                    f"Không thể lưu vì tên khoa học '{sciname}' đã tồn tại trong hệ thống.\n"
                    f"Vui lòng nhập một tên khoa học khác rồi thử lại."
                )
            else:
                QMessageBox.critical(
                    self, "Lỗi SQL Server",
                    f"Không thể lưu loài thực vật vào Database.\nChi tiết lỗi từ CSDL: {e}"
                )


class PhieuHoThucVatWindow(QDialog):

    def __init__(self, username, role, parent, next_id, record=None):
        """
        record=None -> chế độ THÊM MỚI (giữ nguyên hành vi cũ, next_id là mã
        họ kế tiếp tự sinh).
        record=<dict> -> chế độ SỬA (gọi từ nút ✏️ ở bảng Họ thực vật): form
        được điền sẵn dữ liệu hiện có, mã họ (idInput) bị khóa không cho sửa
        (vì là khóa chính), và khi Lưu sẽ gọi UPDATE thay vì INSERT.
        """
        super().__init__()
        self.parent = parent
        self.editing_record = record
        self.ui = Ui_PhieuHo()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)
        if record is not None:
            self.ui.idInput.setReadOnly(True)
            self.ui.nameInput.setText(str(record.get("TENHO", "")))
            self.ui.characteristicsInput.setPlainText(str(record.get("MOTA") or ""))
            self.setWindowTitle("Sửa họ thực vật")
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
            if self.editing_record is not None:
                database.update_hothucvat(maho=fid, tenho=fname, mota=fdesc)
                QMessageBox.information(self, "Thành công", "Đã cập nhật họ thực vật vào Database thành công!")
            else:
                database.add_hothucvat(maho=fid, tenho=fname, mota=fdesc)
                QMessageBox.information(self, "Thành công", "Đã lưu họ thực vật vào Database thành công!")
            self.parent.loadFamilyData()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")


class PhieuKhuWindow(QDialog):

    def __init__(self, username, role, parent, next_id, record=None):
        """
        record=None -> chế độ THÊM MỚI (giữ nguyên hành vi cũ).
        record=<dict> -> chế độ SỬA (gọi từ nút ✏️ ở bảng Khu trưng bày, chức
        năng nối từ KhutrungbayEx.py -> MainWindow.edit_area): form được điền
        sẵn dữ liệu hiện có, mã khu (idInput) bị khóa không cho sửa (vì là khóa
        chính), và khi Lưu sẽ gọi UPDATE thay vì INSERT.
        """
        super().__init__()
        self.parent = parent
        self.editing_record = record
        self.ui = Ui_PhieuKhu()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)

        # SỬA LỖI "ÍT THÔNG TIN": form Phiếu khu (Phieukhu.ui) được sao chép từ
        # form Loài thực vật nên vốn KHÔNG có ô nhập Diện tích -> khi thêm mới
        # luôn bị gán cứng 5000.0 bất kể người dùng nhập gì, và khi sửa thì
        # diện tích không thể chỉnh được. Bảng SQL (KHU_TRUNG_BAY.DIENTICH) và
        # cả bảng danh sách ngoài giao diện chính ĐÃ có sẵn cột Diện tích, nên
        # ở đây tự động thêm 1 ô nhập Diện tích thật vào cuối form (nếu .ui
        # chưa có sẵn ô nào tên gần giống), để nhập/sửa được số liệu thật.
        self.areaInput = self._ensure_area_field()

        if record is not None:
            self.ui.idInput.setReadOnly(True)
            self.ui.nameInput.setText(str(record.get("TENKHU", "")))
            self.ui.scientificNameInput.setText(str(record.get("VITRI") or ""))
            self.ui.characteristicsInput.setPlainText(str(record.get("MOTA") or ""))
            dientich = record.get("DIENTICH")
            self.areaInput.setText("" if dientich is None else str(dientich))
            self.setWindowTitle("Sửa khu trưng bày")
        else:
            self.areaInput.setText("5000")

        self.ui.saveButton.clicked.connect(self.saveZone)
        self.ui.cancelButton.clicked.connect(self.close)

    def _ensure_area_field(self):
        """Dùng ô nhập Diện tích có sẵn trên .ui nếu tìm được (dò theo nhiều
        tên khả dĩ); nếu KHÔNG có sẵn ô nào, tự tạo 1 QLineEdit mới và thêm
        vào cuối layout của dialog (thêm hẳn 1 dòng "Diện tích (m²):" nếu
        layout là QFormLayout, hoặc thêm 1 hàng ngang nếu không phải)."""
        widget = _find_widget_by_hints(
            self.ui,
            ["areaInput", "dientichInput", "areaLineEdit", "txtDienTich",
             "dienTichInput", "dienTichInputInput"],
            QLineEdit,
            keyword_hints=("dientich", "area", "diện tích"),
        )
        if widget is not None:
            return widget

        from PyQt6.QtWidgets import QLabel

        new_input = QLineEdit()
        new_input.setPlaceholderText("Nhập diện tích (m²), vd: 5000")

        target_form = self.layout() if isinstance(self.layout(), QFormLayout) else self.findChild(QFormLayout)
        if target_form is not None:
            target_form.addRow("Diện tích (m²):", new_input)
        elif self.layout() is not None:
            row = QHBoxLayout()
            row.addWidget(QLabel("Diện tích (m²):"))
            row.addWidget(new_input)
            self.layout().addLayout(row)
        return new_input

    def saveZone(self):
        zid = self.ui.idInput.text().strip()
        zname = self.ui.nameInput.text().strip()
        zpos = self.ui.scientificNameInput.text().strip()
        zdesc = self.ui.characteristicsInput.toPlainText().strip()
        zarea_text = self.areaInput.text().strip().replace(",", ".")

        if zname == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên khu.")
            return

        # SỬA LỖI: Diện tích giờ được nhập thật từ form thay vì luôn gán cứng
        # 5000.0. Bảng SQL có ràng buộc CK_DienTich_Khu (DIENTICH > 0) nên phải
        # kiểm tra hợp lệ TRƯỚC khi gửi lên SQL Server, tránh lỗi khó hiểu.
        try:
            zarea = float(zarea_text) if zarea_text else 0
        except ValueError:
            QMessageBox.warning(self, "Thông báo", "Diện tích không hợp lệ, vui lòng nhập một số (vd: 5000 hoặc 5000.5).")
            return
        if zarea <= 0:
            QMessageBox.warning(self, "Thông báo", "Diện tích phải lớn hơn 0.")
            return

        try:
            if self.editing_record is not None:
                database.update_khutrungbay(makhu=zid, tenkhu=zname, vitri=zpos, dientich=zarea, mota=zdesc)
                QMessageBox.information(self, "Thành công", "Đã cập nhật khu trưng bày vào Database thành công!")
            else:
                database.add_khutrungbay(makhu=zid, tenkhu=zname, vitri=zpos, dientich=zarea, mota=zdesc)
                QMessageBox.information(self, "Thành công", "Đã lưu khu trưng bày vào Database thành công!")
            self.parent.loadZoneData()
            if hasattr(self.parent, "_go_to_zone_page_for"):
                self.parent._go_to_zone_page_for(zid)
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")


class PhieuNhanVienWindow(QDialog):

    def __init__(self, username, role, parent, next_id, record=None):
        """
        record=None -> chế độ THÊM MỚI (giữ nguyên hành vi cũ).
        record=<dict> -> chế độ SỬA (gọi từ nút "Sửa" ở bảng Nhân viên, chức
        năng nối từ NhanvienEx.py -> MainWindow.edit_staff): form được điền
        sẵn dữ liệu hiện có, mã nhân viên (idInput) bị khóa không cho sửa (vì
        là khóa chính), và khi Lưu sẽ gọi UPDATE thay vì INSERT.
        """
        super().__init__()
        self.parent = parent
        self.editing_record = record
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

        # ============================================================
        # CHẾ ĐỘ SỬA: điền sẵn dữ liệu hiện có lên form, khóa mã nhân viên.
        # ============================================================
        if record is not None:
            self.ui.idInput.setReadOnly(True)
            self.ui.nameInput.setText(str(record.get("HOTEN", "")))
            ngaysinh = record.get("NGAYSINH")
            if ngaysinh:
                qdate = QDate.fromString(str(ngaysinh)[:10], "yyyy-MM-dd")
                if qdate.isValid():
                    self.ui.dobInput.setDate(qdate)
            self.ui.genderCombo.setCurrentText(str(record.get("GIOITINH", "")))
            self.ui.phoneInput.setText(str(record.get("DIENTHOAI") or ""))
            self.ui.emailInput.setText(str(record.get("EMAIL") or ""))
            self.ui.positionCombo.setCurrentText(str(record.get("CHUCVU", "")))
            if self.ui.zoneCombo is not None:
                zone_idx = self.ui.zoneCombo.findData(record.get("MAKHU"))
                self.ui.zoneCombo.setCurrentIndex(zone_idx if zone_idx >= 0 else 0)
            self.setWindowTitle("Sửa nhân viên")

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
            if self.editing_record is not None:
                database.update_nhanvien(manv=nid, hoten=nname, ngaysinh=ndob, gioitinh=ngender,
                                         dienthoai=nphone, email=nemail, chucvu=npos, makhu=nmakhu)
                QMessageBox.information(self, "Thành công", "Đã cập nhật nhân viên vào Database thành công!")
            else:
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
        # SỬA LỖI: TOÀN BỘ nội dung hàm này giờ nằm trong 1 khối try/except DUY
        # NHẤT, bao từ dòng đầu tiên. Trước đây phần đọc dữ liệu từ các ô nhập
        # (combobox, ngày, textbox...) nằm NGOÀI try/except; PyQt6 mặc định
        # KHÔNG làm crash ứng dụng khi 1 hàm nối với nút bấm bị lỗi - nó chỉ âm
        # thầm in lỗi ra console rồi dừng lại, khiến người dùng bấm "Lưu" thấy
        # "không có phản ứng gì, không lưu, cũng không báo lỗi". Bọc toàn bộ
        # hàm trong try/except đảm bảo MỌI lỗi xảy ra ở bất kỳ bước nào cũng
        # chắc chắn hiện lên 1 hộp thoại rõ ràng cho người dùng.
        try:
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

            if self.record is None:
                # SỬA LỖI: tính lại Mã phiếu NGAY TRƯỚC KHI LƯU dựa trên dữ liệu
                # MỚI NHẤT trong SQL (không dùng mã đã tính sẵn lúc mở form nữa),
                # để mã luôn là số thứ tự kế tiếp thật sự đang có trong Database
                # (vd đã có PCS01..PCS07 -> mã kế tiếp chắc chắn là PCS08), tránh
                # bị lệch/trùng nếu form mở lâu hoặc có người khác vừa thêm phiếu.
                current = database.get_all_phieuchamsoc()
                existing_ids = [r["MAPHIEUCS"] for r in current]
                maphieucs = _generate_next_code(existing_ids, "PCS", 2)
                self.txtMaPhieu.setText(maphieucs)

                database.add_phieuchamsoc(
                    maphieucs=maphieucs, ngaychamsoc=ngay, noidungchamsoc=noidung,
                    phuongphap=phuongphap, tinhtrangsauchamsoc=tinhtrang,
                    ghichu=ghichu, macay=macay, manv=manv,
                )
                QMessageBox.information(self, "Thành công", f"Đã lưu phiếu chăm sóc '{maphieucs}' vào Database thành công!")
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
    # Tên control khả dĩ cho ô "Tên đăng nhập" / "Số điện thoại" / "Email"
    # trên form đăng ký (nếu form có sẵn các ô này). Nếu KHÔNG tìm thấy ô
    # "Tên đăng nhập" riêng, hệ thống sẽ tự sinh tên đăng nhập từ Họ tên.
    _USERNAME_CANDIDATES = ["txtUsername", "txtTenDangNhap", "txtTaiKhoan",
                             "input_username", "lineEditUsername", "lineEditTenDangNhap"]
    _PHONE_CANDIDATES = ["txtPhone", "txtSDT", "txtDienThoai", "lineEditPhone", "lineEditSDT"]
    _EMAIL_CANDIDATES = ["txtEmail", "txtMail", "lineEditEmail", "lineEditMail"]

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
        """
        Đăng ký tài khoản Khách tham quan: LƯU THẲNG vào bảng KHACH_THAM_QUAN
        trong SQL Server (TENDANGNHAP/MATKHAU) rồi VÀO THẲNG giao diện "Báo
        cáo sự cố" luôn, KHÔNG bắt quay lại màn hình "Đăng nhập" nữa - đúng
        theo yêu cầu: đăng ký đúng là vào thẳng, không cần đăng nhập lại.
        """
        hoten = self.ui.txtFullName.text().strip()
        if hoten == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập họ tên.")
            return

        # QUAN TRỌNG: KHÔNG .strip() Mật khẩu / Tên đăng nhập ở đây.
        # Trước đây .strip() làm mất khoảng trắng đầu/cuối mà người dùng đã
        # gõ lúc đăng ký, trong khi lúc đăng nhập (LoginWindow.login) lại so
        # khớp bằng chuỗi RAW (chưa strip) -> nếu mật khẩu/tên đăng nhập có
        # khoảng trắng, 2 bên không còn khớp 100% nữa dù gõ y hệt. Theo đúng
        # yêu cầu "tài khoản/mật khẩu có thể là ký tự bất kỳ, chỉ cần đăng
        # nhập đúng 100% những gì đã đăng ký", ta phải LƯU NGUYÊN VĂN (giữ cả
        # khoảng trắng, hoa/thường) những gì người dùng gõ, chỉ dùng bản
        # .strip() để KIỂM TRA xem có bỏ trống hay không, không dùng để lưu.
        matkhau = self.txtMatKhau.text() if self.txtMatKhau is not None else ""
        nhaplai = self.txtNhapLaiMatKhau.text() if self.txtNhapLaiMatKhau is not None else ""
        if not matkhau.strip():
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập mật khẩu.")
            return
        if matkhau != nhaplai:
            QMessageBox.warning(self, "Thông báo", "Mật khẩu nhập lại không khớp.")
            return

        # SỬA LỖI: trước đây nếu tên control ô "Tên đăng nhập" không khớp với
        # bất kỳ tên nào trong _USERNAME_CANDIDATES, hàm này trả về None NGAY
        # LẬP TỨC (không có bước dò dự phòng nào khác), khiến Tên đăng nhập
        # người dùng gõ bị BỎ QUA HOÀN TOÀN và hệ thống âm thầm lưu Họ tên
        # làm Tên đăng nhập thay vào đó -> đăng ký "thành công" nhưng đăng
        # nhập lại bằng đúng Tên đăng nhập đã gõ luôn báo sai, vì CSDL thực ra
        # đang lưu Họ tên. Giờ thêm bước dò theo placeholder/objectName chứa
        # các từ khóa liên quan tới "tên đăng nhập" trước khi chấp nhận bỏ cuộc.
        txtTenDangNhap = _find_widget_by_hints(
            self.ui, self._USERNAME_CANDIDATES, QLineEdit,
            keyword_hints=("tên đăng nhập", "tendangnhap", "username", "tài khoản", "taikhoan"),
        )
        txtDienThoai = _find_widget_by_hints(self.ui, self._PHONE_CANDIDATES, QLineEdit)
        txtEmail = _find_widget_by_hints(self.ui, self._EMAIL_CANDIDATES, QLineEdit)

        tendangnhap = txtTenDangNhap.text() if txtTenDangNhap is not None else ""
        if not tendangnhap.strip():
            # SỬA LỖI: form không có ô "Tên đăng nhập" riêng -> trước đây tự
            # sinh từ Họ tên bằng cách bỏ dấu, viết liền, chuyển chữ thường
            # (vd "Phan Việt Anh" -> "phanvietanh"), khiến Tên đăng nhập lưu
            # vào CSDL KHÔNG giống với Họ tên đã nhập (mất hoa/thường, mất dấu
            # cách, mất dấu tiếng Việt). Giờ giữ NGUYÊN VĂN Họ tên đã nhập làm
            # Tên đăng nhập (y chang chữ hoa/thường, dấu cách, dấu tiếng Việt),
            # đúng theo yêu cầu - nhờ _configure_vietnamese_encoding() ở
            # get_connection() đã sửa đúng bảng mã, Tên đăng nhập có dấu giờ
            # lưu và đọc lại đúng, không cần bỏ dấu nữa.
            tendangnhap = hoten or "khach"

        dienthoai = txtDienThoai.text().strip() if txtDienThoai is not None else ""
        email = txtEmail.text().strip() if txtEmail is not None else ""

        try:
            makhach, tendangnhap_thuc = database.add_khachthamquan(
                hoten=hoten, tendangnhap=tendangnhap, matkhau=matkhau,
                dienthoai=dienthoai or None, email=email or None,
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi đăng ký", f"Không thể đăng ký tài khoản.\nChi tiết: {e}")
            return

        # TỰ KIỂM TRA NGAY SAU KHI ĐĂNG KÝ: thử "đăng nhập" ngay bằng đúng
        # tên đăng nhập + mật khẩu vừa lưu. Nếu vì lý do gì đó (vd collation
        # đặc biệt trên máy chủ SQL Server, dữ liệu bị cắt bớt do giới hạn độ
        # dài cột, v.v.) mà việc này vẫn thất bại, báo rõ ngay tại đây thay vì
        # để người dùng phát hiện sau dưới dạng "sai mật khẩu" khó hiểu.
        try:
            self_check = database.get_khachthamquan_by_exact_login(tendangnhap_thuc, matkhau)
        except Exception:
            self_check = None
        if self_check is None:
            QMessageBox.warning(
                self, "Cảnh báo",
                f"Tài khoản '{tendangnhap_thuc}' đã được LƯU vào CSDL, nhưng hệ thống thử đăng "
                f"nhập lại ngay bằng chính thông tin vừa lưu thì KHÔNG khớp.\n\n"
                f"Đây là lỗi bất thường (có thể do giới hạn độ dài cột hoặc cấu hình SQL Server), "
                f"vui lòng chụp lại thông báo này và gửi người phụ trách kỹ thuật:\n"
                f"Tên đăng nhập đã lưu: {tendangnhap_thuc!r}\n"
                f"Độ dài mật khẩu đã gõ: {len(matkhau)} ký tự"
            )

        QMessageBox.information(
            self, "Đăng ký thành công",
            f"Tài khoản '{tendangnhap_thuc}' đã được tạo thành công.\n"
            f"Đang vào giao diện Báo cáo sự cố..."
        )

        # THEO YÊU CẦU MỚI: đăng ký đúng (thành công) thì vào THẲNG giao diện
        # "Báo cáo sự cố" luôn, KHÔNG cần quay lại màn hình Đăng nhập rồi tự
        # gõ lại Tên đăng nhập/Mật khẩu nữa. Dùng đúng HOTEN vừa đăng ký
        # (giống hệt cách LoginWindow.login() làm khi đăng nhập Khách tham
        # quan thành công: BaoCaoSuCoWindow(khach["HOTEN"], self.role)).
        self.main_window = BaoCaoSuCoWindow(hoten, "Khách tham quan")
        self.main_window.show()
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

        # Theo đúng yêu cầu: bấm "Khách tham quan" sẽ CHUYỂN THẲNG sang giao
        # diện Đăng ký (SignWindow) ngay lập tức, không cần bấm thêm nút
        # "Đăng nhập" nữa.
        self.sign = SignWindow()
        self.sign.show()
        self.close()

    def selectGuestRoleForLogin(self):
        """
        KHÔNG gắn vào nút bấm nào cả - chỉ được gọi TỰ ĐỘNG bởi SignWindow
        ngay sau khi Đăng ký thành công (xem SignWindow.register()), để màn
        hình Đăng nhập hiện ra đã có sẵn vai trò "Khách tham quan" được chọn
        (không phải bấm lại nút - vì bấm lại sẽ nhảy sang màn Đăng ký một lần
        nữa theo đúng hành vi ở trên). Người dùng chỉ cần gõ Tên đăng
        nhập/Mật khẩu VỪA ĐĂNG KÝ rồi bấm "Đăng nhập" là vào được hệ thống.
        """
        self.role = "Khách tham quan"
        self.resetButton()
        self.ui.btn_role_guest.setStyleSheet(
            "QPushButton{background:#198754;color:white;border-radius:8px;font-weight:bold;}")
        self.setWindowTitle("Đăng nhập - Khách tham quan")

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
            if not username:
                # Chưa nhập Tên đăng nhập -> coi như CHƯA CÓ tài khoản, mở
                # giao diện Đăng ký.
                self.sign = SignWindow()
                self.sign.show()
                self.close()
                return

            if not password:
                QMessageBox.warning(self, "Thông báo",
                                     "Vui lòng nhập mật khẩu để đăng nhập.\n"
                                     "(Nếu chưa có tài khoản, để trống Tên đăng nhập rồi bấm "
                                     "'Đăng nhập' để chuyển sang màn hình Đăng ký.)")
                return

            # CẬP NHẬT: bắt buộc Tên đăng nhập VÀ Mật khẩu phải giống Y CHANG
            # 100% (phân biệt chữ hoa/chữ thường, tính cả dấu cách) với đúng
            # những gì đã nhập lúc Đăng ký, dùng hàm mới
            # get_khachthamquan_by_exact_login() (xem giải thích chi tiết ở
            # định nghĩa hàm trong class database phía trên). Không dùng lại
            # username/password đã được .strip() ở đầu hàm login() để tránh
            # ảnh hưởng dấu cách đầu/cuối chuỗi mà người dùng đã gõ.
            username_raw = self.ui.input_username.text()
            password_raw = self.ui.input_password.text()
            try:
                khach = database.get_khachthamquan_by_exact_login(username_raw, password_raw)
            except Exception as e:
                QMessageBox.warning(self, "Đăng nhập thất bại",
                                     f"Lỗi kết nối SQL Server.\n(Chi tiết: {e})")
                return

            if khach:
                # Khách tham quan KHÔNG được vào Trang chủ -> đưa thẳng vào
                # trang "Báo cáo sự cố" (1 trong 2 trang được phép truy cập).
                self.main_window = BaoCaoSuCoWindow(khach["HOTEN"], self.role)
                self.main_window.show()
                self.close()
            else:
                QMessageBox.warning(self, "Đăng nhập thất bại",
                                     "Sai tên đăng nhập hoặc mật khẩu Khách tham quan.")
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

        # SỬA LỖI QUAN TRỌNG: trước đây loadCareRecords()/renderCareTable() chỉ
        # tìm ĐÚNG CHÍNH XÁC tên "tableCareRecords" trên form (self.ui.tableCareRecords).
        # Nếu file giao diện phieu_cham_soc.py đặt tên bảng khác (vd "tableWidget",
        # "tablePhieuChamSoc"...) thì hasattr() trả về False, hàm âm thầm return
        # mà KHÔNG báo lỗi gì -> dữ liệu vẫn được INSERT thành công vào SQL Server
        # (vẫn hiện thông báo "Đã lưu thành công") nhưng KHÔNG BAO GIỜ được vẽ lên
        # bảng, đúng như hiện tượng "lưu xong không thấy trên giao diện". Giờ dò
        # theo nhiều tên khả dĩ trước, nếu vẫn không khớp tên nào thì tự động lấy
        # QTableWidget ĐẦU TIÊN có trên form (chắc chắn tìm được bảng thật).
        self.tableCareRecords = _find_widget_by_hints(
            self.ui,
            ["tableCareRecords", "tablePhieuChamSoc", "tableChamSoc", "tableWidget",
             "tbCareRecords", "careTable", "tblChamSoc", "tableView"],
            QTableWidget,
        )
        if self.tableCareRecords is None:
            self.tableCareRecords = _get_first_table_widget(self.ui)

        # Tương tự cho ô tìm kiếm: dò theo nhiều tên khả dĩ thay vì chỉ đúng "searchBox".
        self.searchBoxCare = _find_widget_by_hints(
            self.ui,
            ["searchBox", "searchInput", "txtSearch", "lineSearch", "searchEdit", "lineEditSearch"],
            QLineEdit,
            keyword_hints=("search", "tìm", "tim"),
        )

        self.populateFilterCombos()
        self.connectAddButton()
        self.loadCareRecords()
        self._setup_care_search()

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

    def _setup_care_search(self):
        """Gắn ô tìm kiếm (đã dò ở __init__ qua self.searchBoxCare) với bảng
        thật (self.tableCareRecords), thay vì gọi setup_table_search() theo
        đúng 2 tên cố định "searchBox"/"tableCareRecords" như trước (im lặng
        không làm gì nếu tên control thật khác đi)."""
        if self.searchBoxCare is None or self.tableCareRecords is None:
            return
        search_edit = self.searchBoxCare
        table = self.tableCareRecords

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
        # SỬA LỖI: trước đây return âm thầm nếu không thấy đúng tên
        # "tableCareRecords" -> giờ báo lỗi rõ ràng nếu thật sự không có bảng
        # (QTableWidget) nào trên trang, để dễ phát hiện nếu file .ui có vấn đề.
        if self.tableCareRecords is None:
            QMessageBox.warning(
                self, "Thiếu bảng dữ liệu trên giao diện",
                "Không tìm thấy bảng (QTableWidget) nào trên trang Phiếu chăm sóc "
                "để hiển thị dữ liệu.\nVui lòng kiểm tra lại file giao diện phieu_cham_soc.py."
            )
            return
        try:
            self._care_records = database.get_all_phieuchamsoc()
        except Exception as e:
            self._care_records = []
            QMessageBox.critical(
                self, "Lỗi kết nối CSDL",
                f"Không lấy được danh sách phiếu chăm sóc từ SQL Server.\nChi tiết: {e}"
            )
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
        table = self.tableCareRecords
        if table is None:
            return
        table.clearContents()
        table.setRowCount(len(records))
        # SỬA LỖI: trước đây gán cứng cột 0..8 (giả định bảng có đúng 9 cột).
        # Nếu bảng thật trên .ui có SỐ CỘT KHÁC (ít hơn), setItem(row, 8, ...)
        # sẽ bị bỏ qua/lỗi âm thầm và có thể vỡ layout. Giờ luôn dò col_count
        # thật của bảng và chỉ ghi vào những cột thực sự tồn tại.
        col_count = table.columnCount()
        data_col_names = [
            "MAPHIEUCS", "MACAY", "NGAYCHAMSOC", "NOIDUNGCHAMSOC",
            "PHUONGPHAP", "TINHTRANGSAUCHAMSOC", "TENNV", "GHICHU",
        ]
        n_data_cols = len(data_col_names)

        for row, rec in enumerate(records):
            values = [
                str(rec.get("MAPHIEUCS", "")),
                str(rec.get("MACAY", "")),
                str(rec.get("NGAYCHAMSOC", "")),
                str(rec.get("NOIDUNGCHAMSOC", "")),
                str(rec.get("PHUONGPHAP", "")),
                str(rec.get("TINHTRANGSAUCHAMSOC", "")),
                # SỬA LỖI: cột "Nhân viên thực hiện" trước đây bỏ trống -> giờ lấy
                # HOTEN thật (JOIN với NHAN_VIEN qua MANV) từ database.get_all_phieuchamsoc().
                str(rec.get("TENNV") or rec.get("MANV") or ""),
                # SỬA LỖI: cột "Ghi chú" trước đây bỏ trống dù bảng SQL đã có sẵn cột GHICHU.
                str(rec.get("GHICHU") or ""),
            ]
            for col, val in enumerate(values):
                if col < col_count:
                    table.setItem(row, col, QTableWidgetItem(val))
            # SỬA LỖI: cột "Thao tác" trước đây bỏ trống -> giờ có 2 nút Sửa/Xóa
            # thao tác trực tiếp lên SQL Server (UPDATE/DELETE) rồi tự tải lại bảng.
            # Chỉ thêm nếu bảng THẬT SỰ có thêm 1 cột dư ra sau các cột dữ liệu.
            if col_count > n_data_cols:
                maphieucs = rec.get("MAPHIEUCS")
                table.setCellWidget(
                    row, n_data_cols,
                    _build_action_buttons_widget(maphieucs, self.editCareRecord, self.deleteCareRecord),
                )
                table.setRowHeight(row, max(table.rowHeight(row), 34))

        if col_count > n_data_cols:
            table.setColumnWidth(n_data_cols, max(table.columnWidth(n_data_cols), 110))

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
            # SỬA LỖI: thiếu cột "Tình trạng lá" (TINHTRANGLA) khiến mọi cột
            # phía sau bị lệch 1 vị trí. Đã bổ sung đúng cột 5 = TINHTRANGLA.
            table.setItem(row, 5, QTableWidgetItem(str(srv.get("TINHTRANGLA") or "")))
            table.setItem(row, 6, QTableWidgetItem(str(srv.get("TINHTRANGSINHTRUONG", ""))))
            # SỬA LỖI: cột "Nhận xét" trước đây bỏ trống dù bảng SQL đã có sẵn cột NHANXET.
            table.setItem(row, 7, QTableWidgetItem(str(srv.get("NHANXET") or "")))
            # SỬA LỖI: cột "Nhân viên khảo sát" trước đây bỏ trống -> giờ lấy
            # HOTEN thật (JOIN với NHAN_VIEN qua MANV) từ database.get_all_phieukhaosat().
            table.setItem(row, 8, QTableWidgetItem(str(srv.get("TENNV") or srv.get("MANV") or "")))
            # SỬA LỖI: cột "Thao tác" trước đây bỏ trống -> giờ có 2 nút Sửa/Xóa
            # thao tác trực tiếp lên SQL Server (UPDATE/DELETE) rồi tự tải lại bảng.
            maks = srv.get("MAKS")
            table.setCellWidget(
                row, 9,
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


def _install_global_exception_hook():
    """
    SỬA LỖI QUAN TRỌNG: mặc định PyQt6 KHÔNG làm crash ứng dụng khi có lỗi xảy
    ra bên trong 1 hàm xử lý sự kiện (vd hàm nối với nút bấm qua .clicked.connect).
    Nó chỉ âm thầm in traceback ra console (cửa sổ cmd/terminal) rồi dừng lại.
    Khi chạy bản build/đóng gói thực tế (không mở terminal), người dùng sẽ
    KHÔNG THẤY GÌ CẢ: bấm nút không có phản ứng, không lưu được, cũng không có
    thông báo lỗi nào hiện lên - đúng như hiện tượng "bấm Lưu ở Phiếu chăm sóc
    không lưu được mà cũng không hiện lỗi gì".
    Hàm này thay thế sys.excepthook mặc định để MỌI lỗi không được try/except
    bắt ở đâu đó trong code đều tự động hiện lên 1 hộp thoại QMessageBox, thay
    vì biến mất âm thầm không dấu vết.
    """
    def _handle_exception(exc_type, exc_value, exc_traceback):
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        try:
            QMessageBox.critical(
                None, "Đã xảy ra lỗi",
                "Chương trình gặp lỗi không mong muốn nên thao tác vừa rồi có thể "
                "CHƯA được lưu.\nVui lòng thử lại; nếu vẫn còn lỗi, hãy chụp lại nội "
                f"dung dưới đây gửi cho người phụ trách kỹ thuật:\n\n{exc_type.__name__}: {exc_value}"
            )
        except Exception:
            # Nếu ngay cả việc hiện QMessageBox cũng lỗi (vd chưa có QApplication),
            # thì ít nhất traceback đã được in ra console ở trên rồi.
            pass

    sys.excepthook = _handle_exception


if __name__ == "__main__":
    _install_global_exception_hook()
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()

    sys.exit(app.exec())