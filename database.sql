create table HO_THUC_VAT
(
	MAHO varchar(10) not null primary key,
	TENHO nvarchar(100),
	MOTA nvarchar(1000)
)
create table KHU_TRUNG_BAY
(
	MAKHU varchar(10) not null primary key,
	TENKHU nvarchar(100) not null,
	VITRI nvarchar(200),
	DIENTICH decimal(8,2),
	MOTA nvarchar(500)
)
create table NHAN_VIEN
(
	MANV varchar(10) primary key,
	HOTEN nvarchar(100) not null,
	NGAYSINH date,
	GIOITINH nvarchar(10),
	DIENTHOAI varchar(15) unique,
	EMAIL varchar(100) unique,
	CHUCVU nvarchar(50)
)
create table LOAI_THUC_VAT
(
    MALOAI varchar(10) not null primary key,
    TENTHUONGGOI nvarchar(100) not null,
    TENKHOAHOC varchar(150) not null,
    DACDIEMSINHHOC nvarchar(max),
    MOITRUONGSONG nvarchar(200),
    TINHTRANGBAOTON nvarchar(50),
    MAHO varchar(10) not null foreign key references HO_THUC_VAT(MAHO)
)
create table KHACH_THAM_QUAN
(
	MAKHACH varchar(10) not null primary key,
	HOTEN nvarchar(100) not null,
	DIENTHOAI varchar(15) unique,
    EMAIL varchar(100) unique,
	TENDANGNHAP varchar(255) unique not null,
	MATKHAU varchar(255) not null
)
create table CAY
(
    MACAY varchar(10) not null primary key,
    TENCAY nvarchar(100) not null,
    NGAYTRONG date not null,
    CHIEUCAO decimal(5,2),
    DUONGKINH decimal(5,2),
    VITRI nvarchar(200),
    TINHTRANGSINHTRUONG nvarchar(50) not null,
    TRANGTHAIHOATDONG nvarchar(30) not null,
    MALOAI varchar(10) not null foreign key references LOAI_THUC_VAT(MALOAI),
    MAKHU varchar(10) not null foreign key references KHU_TRUNG_BAY(MAKHU)
)
create table PHIEU_CHAM_SOC
(
    MAPHIEUCS varchar(10) not null primary key,
    NGAYCHAMSOC date not null,
    NOIDUNGCHAMSOC nvarchar(1000) not null,
    PHUONGPHAP nvarchar(200),
    TINHTRANGSAUCHAMSOC nvarchar(200),
    GHICHU nvarchar(500),
    MACAY varchar(10) not null foreign key references CAY(MACAY),
    MANV varchar(10) not null foreign key references NHAN_VIEN(MANV)
)
create table PHIEU_KHAO_SAT
(
    MAKS varchar(10) not null primary key,
    NGAYKHAOSAT date not null,
    CHIEUCAOGHINHAN decimal(5,2),
    DUONGKINHGHINHAN decimal(5,2),
    TINHTRANGLA nvarchar(100),
    TINHTRANGSINHTRUONG nvarchar(50),
    NHANXET nvarchar(500),
    MACAY varchar(10) not null foreign key references CAY(MACAY),
    MANV varchar(10) not null foreign key references NHAN_VIEN(MANV)
)
create table YEU_CAU_BAO_TRI
(
    MABT varchar(10) not null primary key,
    NGAYTAO date not null,
    NOIDUNGBAOTRI nvarchar(1000) not null,
    MUCDOUUTIEN nvarchar(20),
    TRANGTHAI nvarchar(50),
    MANV varchar(10) not null foreign key references NHAN_VIEN(MANV),
    MACAY varchar(10) not null foreign key references CAY(MACAY)
)
create table BAO_CAO_SU_CO
(
    MABC varchar(10) not null primary key,
    THOIGIANGUI datetime2 not null,
    MOTA nvarchar(max) not null,
    MUCDONGUYHIEM nvarchar(30),
    HINHANH varbinary(max),
    TRANGTHAI nvarchar(50),
    MAKHACH varchar(10) not null foreign key references KHACH_THAM_QUAN(MAKHACH)
)
Alter table CAY
add constraint CK_ChieuCao_Cay check (CHIEUCAO>0),
    constraint CK_DuongKinh_Cay check (DUONGKINH>0);

Alter table KHU_TRUNG_BAY
add constraint CK_DienTich_Khu check (DIENTICH>0);

Alter table PHIEU_KHAO_SAT
add constraint CK_ChieuCao_KS check (CHIEUCAOGHINHAN>0),
    constraint CK_DuongKinh_KS check (DUONGKINHGHINHAN>0);

Alter table NHAN_VIEN
add constraint CK_GioiTinh_NV check (GIOITINH In (N'Nam', N'Nữ', N'Khác'));

Alter table YEU_CAU_BAO_TRI
add constraint DF_TrangThai_YCBT default N'Chờ xử lý' for TRANGTHAI;

Alter table BAO_CAO_SU_CO
add constraint DF_TrangThai_BCSC default N'Mới tiếp nhận' for TRANGTHAI;
