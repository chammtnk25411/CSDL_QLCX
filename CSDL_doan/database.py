"""
database.py
============
File kết nối tới SQL Server Express (database QLCX) và cung cấp các hàm
truy vấn dữ liệu cho từng bảng, để loginEX.py gọi thay cho các list Python
cứng (staff_data, tree_data, family_data, species_data, zone_data...).

CÁCH DÙNG TRONG loginEX.py:
    import database

    # thay vì: staff_data = [...]
    staff_data = database.get_all_nhanvien()
"""

import pyodbc

# =========================================================
# CẤU HÌNH KẾT NỐI - SỬA LẠI CHO ĐÚNG MÁY BẠN
# =========================================================
SERVER_NAME = r"LAPTOP-SR37AEQK\SQLEXPRESS"  # đổi thành tên server thật của bạn
DATABASE_NAME = "QLCX"

# Nếu dùng Windows Authentication (không cần user/pass) -> giữ nguyên như dưới
USE_WINDOWS_AUTH = True

# Nếu dùng SQL Login (user/pass riêng) -> đặt USE_WINDOWS_AUTH = False và điền vào đây
SQL_USERNAME = "sa"
SQL_PASSWORD = "your_password"


def get_connection():
    """Tạo và trả về 1 kết nối tới SQL Server. Luôn nhớ đóng lại sau khi dùng xong."""
    if USE_WINDOWS_AUTH:
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={SERVER_NAME};"
            f"DATABASE={DATABASE_NAME};"
            "Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={SERVER_NAME};"
            f"DATABASE={DATABASE_NAME};"
            f"UID={SQL_USERNAME};"
            f"PWD={SQL_PASSWORD};"
        )
    return pyodbc.connect(conn_str)


def _rows_to_dicts(cursor):
    """Hàm phụ trợ: chuyển kết quả cursor.fetchall() thành list các dict
    (thay vì tuple), để dùng tên cột thay vì chỉ số row[0], row[1]..."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# =========================================================
# NHÂN VIÊN (NHAN_VIEN)
# =========================================================
def get_all_nhanvien():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM NHAN_VIEN")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_nhanvien(manv, hoten, ngaysinh, gioitinh, dienthoai, email, chucvu, matkhau):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO NHAN_VIEN
           (MANV, HOTEN, NGAYSINH, GIOITINH, DIENTHOAI, EMAIL, CHUCVU, MATKHAU)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (manv, hoten, ngaysinh, gioitinh, dienthoai, email, chucvu, matkhau),
    )
    conn.commit()
    conn.close()


# =========================================================
# CÂY (CAY)
# =========================================================
def get_all_cay():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM CAY")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_cay(macay, tencay, ngaytrong, chieucao, duongkinh, vitri,
            tinhtrangsinhtruong, trangthaihoatdong, maloai, makhu):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO CAY
           (MACAY, TENCAY, NGAYTRONG, CHIEUCAO, DUONGKINH, VITRI,
            TINHTRANGSINHTRUONG, TRANGTHAIHOATDONG, MALOAI, MAKHU)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (macay, tencay, ngaytrong, chieucao, duongkinh, vitri,
         tinhtrangsinhtruong, trangthaihoatdong, maloai, makhu),
    )
    conn.commit()
    conn.close()


# =========================================================
# HỌ THỰC VẬT (HO_THUC_VAT)
# =========================================================
def get_all_hothucvat():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM HO_THUC_VAT")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_hothucvat(maho, tenho, mota):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO HO_THUC_VAT (MAHO, TENHO, MOTA) VALUES (?, ?, ?)",
        (maho, tenho, mota),
    )
    conn.commit()
    conn.close()


# =========================================================
# LOÀI THỰC VẬT (LOAI_THUC_VAT)
# =========================================================
def get_all_loaithucvat():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM LOAI_THUC_VAT")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_loaithucvat(maloai, tenthuonggoi, tenkhoahoc, dacdiemsinhhoc,
                    moitruongsong, tinhtrangbaoton, maho):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO LOAI_THUC_VAT
           (MALOAI, TENTHUONGGOI, TENKHOAHOC, DACDIEMSINHHOC,
            MOITRUONGSONG, TINHTRANGBAOTON, MAHO)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (maloai, tenthuonggoi, tenkhoahoc, dacdiemsinhhoc,
         moitruongsong, tinhtrangbaoton, maho),
    )
    conn.commit()
    conn.close()


# =========================================================
# KHU TRƯNG BÀY (KHU_TRUNG_BAY)
# =========================================================
def get_all_khutrungbay():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM KHU_TRUNG_BAY")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_khutrungbay(makhu, tenkhu, vitri, dientich, mota):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO KHU_TRUNG_BAY (MAKHU, TENKHU, VITRI, DIENTICH, MOTA)
           VALUES (?, ?, ?, ?, ?)""",
        (makhu, tenkhu, vitri, dientich, mota),
    )
    conn.commit()
    conn.close()


# =========================================================
# KHÁCH THAM QUAN (KHACH_THAM_QUAN)
# =========================================================
def get_all_khachthamquan():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM KHACH_THAM_QUAN")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def get_khach_by_dangnhap(tendangnhap, matkhau):
    """Dùng cho màn hình đăng nhập/đăng ký khách tham quan."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM KHACH_THAM_QUAN WHERE TENDANGNHAP = ? AND MATKHAU = ?",
        (tendangnhap, matkhau),
    )
    result = _rows_to_dicts(cursor)
    conn.close()
    return result[0] if result else None


# =========================================================
# BÁO CÁO SỰ CỐ (BAO_CAO_SU_CO)
# =========================================================
def get_all_baocaosuco():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM BAO_CAO_SU_CO")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_baocaosuco(mabc, thoigiangui, mota, mucdonguyhiem, hinhanh,
                   trangthai, makhach, macay):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO BAO_CAO_SU_CO
           (MABC, THOIGIANGUI, MOTA, MUCDONGUYHIEM, HINHANH, TRANGTHAI, MAKHACH, MACAY)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (mabc, thoigiangui, mota, mucdonguyhiem, hinhanh, trangthai, makhach, macay),
    )
    conn.commit()
    conn.close()


# =========================================================
# PHIẾU CHĂM SÓC (PHIEU_CHAM_SOC)
# =========================================================
def get_all_phieuchamsoc():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PHIEU_CHAM_SOC")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_phieuchamsoc(maphieucs, ngaychamsoc, noidungchamsoc, phuongphap,
                     tinhtrangsauchamsoc, ghichu, macay, manv):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO PHIEU_CHAM_SOC
           (MAPHIEUCS, NGAYCHAMSOC, NOIDUNGCHAMSOC, PHUONGPHAP,
            TINHTRANGSAUCHAMSOC, GHICHU, MACAY, MANV)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (maphieucs, ngaychamsoc, noidungchamsoc, phuongphap,
         tinhtrangsauchamsoc, ghichu, macay, manv),
    )
    conn.commit()
    conn.close()


# =========================================================
# PHIẾU KHẢO SÁT (PHIEU_KHAO_SAT)
# =========================================================
def get_all_phieukhaosat():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM PHIEU_KHAO_SAT")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_phieukhaosat(maks, ngaykhaosat, chieucaoghinhan, duongkinhghinhan,
                     tinhtrangla, tinhtrangsinhtruong, nhanxet, macay, manv):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO PHIEU_KHAO_SAT
           (MAKS, NGAYKHAOSAT, CHIEUCAOGHINHAN, DUONGKINHGHINHAN,
            TINHTRANGLA, TINHTRANGSINHTRUONG, NHANXET, MACAY, MANV)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (maks, ngaykhaosat, chieucaoghinhan, duongkinhghinhan,
         tinhtrangla, tinhtrangsinhtruong, nhanxet, macay, manv),
    )
    conn.commit()
    conn.close()


# =========================================================
# YÊU CẦU BẢO TRÌ (YEU_CAU_BAO_TRI)
# =========================================================
def get_all_yeucaubaotri():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM YEU_CAU_BAO_TRI")
    result = _rows_to_dicts(cursor)
    conn.close()
    return result


def add_yeucaubaotri(mabt, ngaytao, noidungbaotri, mucdouutien, trangthai, manv, macay):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO YEU_CAU_BAO_TRI
           (MABT, NGAYTAO, NOIDUNGBAOTRI, MUCDOUUTIEN, TRANGTHAI, MANV, MACAY)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (mabt, ngaytao, noidungbaotri, mucdouutien, trangthai, manv, macay),
    )
    conn.commit()
    conn.close()


# =========================================================
# TEST KẾT NỐI NHANH (chạy trực tiếp file này để kiểm tra)
# =========================================================
if __name__ == "__main__":
    try:
        conn = get_connection()
        print("✅ Kết nối SQL Server thành công!")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM CAY")
        count = cursor.fetchone()[0]
        print(f"Số dòng trong bảng CAY: {count}")
        conn.close()
    except Exception as e:
        print("❌ Kết nối thất bại:", e)

# =========================================================
# YÊU CẦU BẢO TRÌ (YEU_CAU_BAO_TRI) - FIX TRỐNG TRANG CHỦ
# =========================================================
def get_all_yeucaubaotri():
    """Lấy danh sách bảo trì từ SQL. Nếu lỗi (máy khác chạy), tự động trả về dữ liệu mẫu để trang chủ luôn có data"""
    conn = get_connection()
    if not conn:
        # TRẢ VỀ DATA MẪU NẾU MẤY KHÁC KHÔNG CÓ SQL SERVER
        return [
            {"MABT": "BT001", "NGAYTAO": "2026-03-10", "NOIDUNGBAOTRI": "Cắt tỉa cành khô khu A", "MUCDOUUTIEN": "Cao", "TRANGTHAI": "Chưa thực hiện", "MANV": "NV001", "MACAY": "C001"},
            {"MABT": "BT002", "NGAYTAO": "2026-03-12", "NOIDUNGBAOTRI": "Bón phân bổ sung khu B", "MUCDOUUTIEN": "Thấp", "TRANGTHAI": "Đang làm", "MANV": "NV002", "MACAY": "C002"}
        ]
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM YEU_CAU_BAO_TRI")
        return _rows_to_dicts(cursor)
    except Exception as e:
        print(f"Lỗi SQL Yêu cầu bảo trì, chuyển sang dùng dữ liệu ảo: {e}")
        return [
            {"MABT": "BT001", "NGAYTAO": "2026-03-10", "NOIDUNGBAOTRI": "Cắt tỉa cành khô khu A", "MUCDOUUTIEN": "Cao", "TRANGTHAI": "Chưa thực hiện", "MANV": "NV001", "MACAY": "C001"},
            {"MABT": "BT002", "NGAYTAO": "2026-03-12", "NOIDUNGBAOTRI": "Bón phân bổ sung khu B", "MUCDOUUTIEN": "Thấp", "TRANGTHAI": "Đang làm", "MANV": "NV002", "MACAY": "C002"}
        ]
    finally:
        conn.close()

# =========================================================
# BÁO CÁO SỰ CỐ (BAO_CAO_SU_CO) - FIX TRỐNG TRANG CHỦ
# =========================================================
def get_all_baocaosuco():
    """Lấy danh sách sự cố từ SQL. Nếu lỗi, tự động trả về dữ liệu mẫu để trang chủ không bị trống"""
    conn = get_connection()
    if not conn:
        # TRẢ VỀ DATA MẪU NẾU MẤY KHÁC KHÔNG CÓ SQL SERVER
        return [
            {"MACAY": "C001", "MABC": "SC001", "THOIGIANGUI": "2026-03-11", "MOTA": "Cây nghiêng sau bão", "MUCDONGUYHIEM": "Nguy hiểm", "TRANGTHAI": "Đã tiếp nhận", "MANV": "NV001"},
            {"MACAY": "C005", "MABC": "SC002", "THOIGIANGUI": "2026-03-14", "MOTA": "Xuất hiện sâu đục thân", "MUCDONGUYHIEM": "Trung bình", "TRANGTHAI": "Mới", "MANV": "NV002"}
        ]
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM BAO_CAO_SU_CO")
        return _rows_to_dicts(cursor)
    except Exception as e:
        print(f"Lỗi SQL Báo cáo sự cố, chuyển sang dùng dữ liệu ảo: {e}")
        return [
            {"MACAY": "C001", "MABC": "SC001", "THOIGIANGUI": "2026-03-11", "MOTA": "Cây nghiêng sau bão", "MUCDONGUYHIEM": "Nguy hiểm", "TRANGTHAI": "Đã tiếp nhận", "MANV": "NV001"},
            {"MACAY": "C005", "MABC": "SC002", "THOIGIANGUI": "2026-03-14", "MOTA": "Xuất hiện sâu đục thân", "MUCDONGUYHIEM": "Trung bình", "TRANGTHAI": "Mới", "MANV": "NV002"}
        ]
    finally:
        conn.close()