---1. Bảng HO_THUC_VAT
create table HO_THUC_VAT(
	MAHO varchar(10) not null primary key,
	TENHO nvarchar(100) not null, -- Theo thiết kế file Word [cite: 8]
	MOTA nvarchar(1000)
)

---2. Bảng KHU_TRUNG_BAY
create table KHU_TRUNG_BAY(
	MAKHU varchar(10) not null primary key,
	TENKHU nvarchar(100) not null,
	VITRI nvarchar(200),
	DIENTICH decimal(8,2) constraint CK_DIENTICH_KHU check (DIENTICH > 0), -- Gộp ràng buộc diện tích > 0 [cite: 10]
	MOTA nvarchar(500)
)

---3. Bảng NHAN_VIEN
create table NHAN_VIEN(
	MANV varchar(10) primary key,
	HOTEN nvarchar(100) not null,
	NGAYSINH date,
	GIOITINH nvarchar(10),
	DIENTHOAI varchar(15) unique,
	EMAIL varchar(100) unique,
	CHUCVU nvarchar(50) -- Đổi sang nvarchar để gõ tiếng Việt chuẩn báo cáo
)

---4. Bảng KHACH_THAM_QUAN
create table KHACH_THAM_QUAN(
	MAKHACH varchar(10) not null primary key,
	HOTEN nvarchar(100) not null,
	DIENTHOAI varchar(15) unique,
    EMAIL varchar(100) unique
)

---5. Bảng LOAI_THUC_VAT
create table LOAI_THUC_VAT(
    MALOAI varchar(10) not null primary key,
    TENTHUONGGOI nvarchar(100) not null,
    TENKHOAHOC varchar(150) not null,
    DACDIEMSINHHOC nvarchar(max),
    MOITRUONGSONG nvarchar(200),
    TINHTRANGBAOTON nvarchar(50),
	MAHO varchar(10) not null foreign key references HO_THUC_VAT(MAHO)
)

---6. Bảng CAY
create table CAY(
    MACAY varchar(10) not null primary key,
    TENCAY nvarchar(100) not null,
    NGAYTRONG date not null,
    CHIEUCAO decimal(5,2) constraint CK_CHIEUCAO_CAY check (CHIEUCAO > 0), -- Gộp kiểm tra chiều cao > 0 [cite: 3]
    DUONGKINH decimal(5,2) constraint CK_DUONGKINH_CAY check (DUONGKINH > 0), -- Gộp kiểm tra đường kính > 0 [cite: 3]
    VITRI nvarchar(200),
    TINHTRANGSINHTRUONG nvarchar(50) not null,
    TRANGTHAIHOATDONG nvarchar(30) not null,
    MALOAI varchar(10) not null foreign key references LOAI_THUC_VAT(MALOAI),
    MAKHU varchar(10) not null foreign key references KHU_TRUNG_BAY(MAKHU)
)

---7. Bảng PHIEU_CHAM_SOC
create table PHIEU_CHAM_SOC(
    MAPHIEUCS varchar(10) not null primary key,
    NGAYCHAMSOC date not null,
    NOIDUNGCHAMSOC nvarchar(1000) not null,
    PHUONGPHAP nvarchar(200),
    TINHTRANGSAUCHAMSOC nvarchar(200),
    GHICHU nvarchar(500),
    MACAY varchar(10) not null foreign key references CAY(MACAY),
    MANV varchar(10) not null foreign key references NHAN_VIEN(MANV)
)

---8. Bảng PHIEU_KHAO_SAT
create table PHIEU_KHAO_SAT(
    MAKS varchar(10) not null primary key,
    NGAYKHAOSAT date not null,
    CHIEUCAOGHINHAN decimal(5,2) constraint CK_CHIEUCAO_KS check (CHIEUCAOGHINHAN > 0), -- Gộp kiểm tra chiều cao ks > 0 [cite: 16]
    DUONGKINHGHINHAN decimal(5,2) constraint CK_DUONGKINH_KS check (DUONGKINHGHINHAN > 0), -- Gộp kiểm tra đường kính ks > 0 [cite: 16]
    TINHTRANGLA nvarchar(100),
    TINHTRANGSINHTRUONG nvarchar(50),
    NHANXET nvarchar(500),
    MACAY varchar(10) not null foreign key references CAY(MACAY),
    MANV varchar(10) not null foreign key references NHAN_VIEN(MANV)
)

---9. Bảng YEU_CAU_BAO_TRI
create table YEU_CAU_BAO_TRI(
    MABT varchar(10) not null primary key,
    NGAYTAO date not null,
    NOIDUNGBAOTRI nvarchar(1000) not null,
    MUCDOUUTIEN nvarchar(20),
    TRANGTHAI nvarchar(50),
    MANV varchar(10) not null foreign key references NHAN_VIEN(MANV)
)

---10. Bảng BAO_CAO_SU_CO
create table BAO_CAO_SU_CO(
    MABC varchar(10) not null primary key,
    THOIGIANGUI datetime2 not null,
    MOTA nvarchar(max) not null,
    MUCDONGUYHIEM nvarchar(30),
    HINHANH varbinary(max),
    TRANGTHAI nvarchar(50),
    MAKHACH varchar(10) not null foreign key references KHACH_THAM_QUAN(MAKHACH)
)
