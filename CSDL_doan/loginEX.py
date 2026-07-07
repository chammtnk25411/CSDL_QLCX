import sys
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QWidget,
    QTableWidgetItem,
    QDialog,
)

# Tích hợp module database
# Sửa dòng này:
# import database

# Thành dòng này:
from CSDL_doan import database

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

# Giữ nguyên dữ liệu tĩnh ban đầu từ loginEX.py để phục vụ các chức năng cũ
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
    {"id": "H002", "name": "Họ Hoa hồng (Rosaceae)", "desc": "Bao gồm nhiều loại cây ăn quả và hoa làm cảnh."}
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


# =========================================================
# LỚP NỀN ĐIỀU HƯỚNG SIDEBAR (Giữ nguyên toàn bộ thao tác chuyển giao diện)
# =========================================================
class NavigationWindow(QMainWindow):

    def setup_sidebar_connections(self):
        # 1. Nút Trang Chủ
        for attr in ["homeButton", "btn_home", "pushButton_home", "navTrangChu"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openTrangChu)

        # 2. Nút Quản Lý Cây
        for attr in ["plantManagementButton", "btn_quanlycay", "treeButton", "navQuanLyCay"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openQuanLyCay)

        # 3. Nút Họ Thực Vật
        for attr in ["familyButton", "btn_hothucvat", "navHoThucVat"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openHoThucVat)

        # 4. Nút Loài Thực Vật
        for attr in ["speciesButton", "btn_loaithucvat", "navLoaiThucVat"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openLoaiThucVat)

        # 5. Nút Khu Trưng Bày
        for attr in ["exhibitionButton", "btn_khutrungbay", "navKhuTrungBay"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openKhuTrungBay)

        # 6. Nút Nhân Viên
        for attr in ["staffButton", "btn_nhanvien", "employeeButton", "navNhanVien"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openNhanVien)

        # 7. Nút Phiếu Chăm Sóc
        for attr in ["careButton", "btn_phieuchamsoc", "navPhieuChamSoc"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openPhieuChamSoc)

        # 8. Nút Phiếu Khảo Sát
        for attr in ["navPhieuKhaoSat", "surveyButton", "btn_phieukhaosat"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openPhieuKhaoSat)

        # 9. Nút Yêu Cầu Bảo Trì
        for attr in ["maintenanceButton", "btn_yeucaubaotri", "navYeuCauBaoTri"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openYeuCauBaoTri)

        # 10. Nút Báo Cáo Sự Cố
        for attr in ["incidentButton", "reportButton", "btn_baocaosuco", "navBaoCaoSuCo", "btnBaoCaoSuCo"]:
            if hasattr(self.ui, attr):
                getattr(self.ui, attr).clicked.connect(self.openBaoCaoSuCo)

        self.setup_quanlycay_style_navigation()

    def setup_quanlycay_style_navigation(self):
        if hasattr(self.ui, "pushButton_10") and hasattr(self.ui, "pushButton_2"):
            quanlycay_mapping = [
                ("pushButton_10", self.openTrangChu),
                ("pushButton_2", self.openQuanLyCay),
                ("pushButton_3", self.openLoaiThucVat),
                ("pushButton_4", self.openHoThucVat),
                ("pushButton_5", self.openKhuTrungBay),
                ("pushButton_6", self.openNhanVien),
                ("pushButton", self.openPhieuChamSoc),
                ("pushButton_7", self.openPhieuKhaoSat),
                ("pushButton_8", self.openYeuCauBaoTri),
                ("pushButton_9", self.openBaoCaoSuCo),
            ]
            for attr, handler in quanlycay_mapping:
                if hasattr(self.ui, attr):
                    getattr(self.ui, attr).clicked.connect(handler)

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
# GIAO DIỆN CHÍNH (MainWindow)
# =========================================================
class MainWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.username = username
        self.role = role

        if hasattr(self.ui, "userInfo"):
            self.ui.userInfo.setText(f"{username}\n{role}")

        self.setup_sidebar_connections()


# =========================================================
# GIAO DIỆN QUẢN LÝ CÂY
# =========================================================
class QuanLyCayWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_QuanLyCay()
        self.ui.setupUi(self)
        self.username = username
        self.role = role

        self.loadData()

        if hasattr(self.ui, "lbl_user_profile"):
            self.ui.lbl_user_profile.setText(f"{username} ({role})")

        if hasattr(self.ui, "btn_add"):
            self.ui.btn_add.clicked.connect(self.openPhieuThongTin)

        self.setup_sidebar_connections()

    def openPhieuThongTin(self):
        self.phieu = PhieuThongTinWindow(self.username, self.role, self)
        self.phieu.exec()

    def loadData(self):
        if hasattr(self.ui, "tableWidget"):
            try:
                # Ưu tiên lấy từ Database thực tế
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
                # Fallback dữ liệu tĩnh cũ nếu db chưa tạo bảng hoặc lỗi kết nối
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
        self.username = username
        self.role = role

        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        self.loadSpeciesData()
        self.setup_sidebar_connections()

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuLoaiThucVat)

    def openPhieuLoaiThucVat(self):
        try:
            current_species = database.get_all_loaithucvat()
            next_id = f"SP{len(current_species) + 1:03d}"
        except Exception:
            next_id = f"L{len(species_data) + 1:03d}"
        self.phieu_loai = PhieuLoaiWindow(self.username, self.role, self, next_id)
        self.phieu_loai.exec()

    def loadSpeciesData(self):
        if hasattr(self.ui, "tableWidget"):
            try:
                db_species = database.get_all_loaithucvat()
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
        self.username = username
        self.role = role

        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        self.loadFamilyData()
        self.setup_sidebar_connections()

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuHoThucVat)

    def openPhieuHoThucVat(self):
        try:
            current_families = database.get_all_hothucvat()
            next_id = f"LO{len(current_families) + 1:03d}"
        except Exception:
            next_id = f"H{len(family_data) + 1:03d}"
        self.phieu_ho = PhieuHoThucVatWindow(self.username, self.role, self, next_id)
        self.phieu_ho.exec()

    def loadFamilyData(self):
        if hasattr(self.ui, "tableWidget"):
            try:
                db_families = database.get_all_hothucvat()
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
        self.username = username
        self.role = role

        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        self.loadZoneData()
        self.setup_sidebar_connections()

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuKhu)

    def openPhieuKhu(self):
        try:
            current_zones = database.get_all_khutrungbay()
            next_id = f"KHU{len(current_zones) + 1:02d}"
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
        self.username = username
        self.role = role

        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        self.loadStaffData()
        self.setup_sidebar_connections()

        if hasattr(self.ui, "addButton"):
            self.ui.addButton.clicked.connect(self.openPhieuNhanVien)
        if hasattr(self.ui, "careButton"):
            self.ui.careButton.clicked.connect(self.openPhieuChamSoc)

    def openPhieuNhanVien(self):
        try:
            current_staff = database.get_all_nhanvien()
            next_id = f"NV{len(current_staff) + 1:03d}"
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
                    self.ui.tableWidget.setItem(row, 7, QTableWidgetItem("N/A"))
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

    def __init__(self, username, role, parent):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuThongTinCay()
        self.ui.setupUi(self)
        self.ui.btnLuu.clicked.connect(self.saveTree)
        self.ui.btnHuy.clicked.connect(self.close)

    def saveTree(self):
        new_id = self.ui.txtMaCay.text().strip()
        new_name = self.ui.txtTenCay.text().strip()
        new_status = self.ui.cboTrangThaiHoatDong.currentText()
        new_species = self.ui.cboLoaiThucVat.currentText().strip()
        new_zone = self.ui.cboKhuTrungBay.currentText().strip()

        # Giữ thao tác cũ (.append vào static list)
        tree_data.append(
            {"id": new_id, "name": new_name, "species": new_species, "zone": new_zone, "status": new_status})

        # Đồng thời lưu vào database
        try:
            database.add_cay(
                macay=new_id, tencay=new_name, ngaytrong=None, chieucao=None, duongkinh=None,
                vitri=None, tinhtrangsinhtruong=None, trangthaihoatdong=new_status,
                maloai=new_species, makhu=new_zone
            )
        except Exception as e:
            print(f"Lưu vào DB lỗi nhưng vẫn lưu list tĩnh: {e}")

        self.parent.loadData()
        self.close()


class PhieuLoaiWindow(QDialog):

    def __init__(self, username, role, parent, next_id):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuLoai()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)
        self.ui.saveButton.clicked.connect(self.saveSpecies)
        self.ui.cancelButton.clicked.connect(self.close)

    def saveSpecies(self):
        if self.ui.nameInput.text().strip() == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên loài.")
            return

        sid = self.ui.idInput.text().strip()
        sname = self.ui.nameInput.text().strip()
        sciname = self.ui.scientificNameInput.text().strip()
        sfamily = self.ui.familyInput.text().strip()
        sbio = self.ui.characteristicsInput.toPlainText().strip()
        shabitat = self.ui.habitatInput.text().strip()
        sstatus = self.ui.statusCombo.currentText()

        # Giữ thao tác cũ
        species_data.append(
            {"id": sid, "name": sname, "sci_name": sciname, "family": sfamily, "bio": sbio, "habitat": shabitat,
             "status": sstatus})

        # Lưu database
        try:
            database.add_loaithucvat(
                maloai=sid, tenthuonggoi=sname, tenkhoahoc=sciname,
                dacdiemsinhhoc=sbio, moitruongsong=shabitat, tinhtrangbaoton=sstatus, maho=sfamily
            )
        except Exception as e:
            print(f"Lưu DB lỗi: {e}")

        self.parent.loadSpeciesData()
        self.close()


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
        if self.ui.nameInput.text().strip() == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên họ.")
            return

        fid = self.ui.idInput.text().strip()
        fname = self.ui.nameInput.text().strip()
        fdesc = self.ui.characteristicsInput.toPlainText().strip()

        # Giữ thao tác cũ
        family_data.append({"id": fid, "name": fname, "desc": fdesc})

        # Lưu database
        try:
            database.add_hothucvat(maho=fid, tenho=fname, mota=fdesc)
        except Exception as e:
            print(f"Lưu DB lỗi: {e}")

        self.parent.loadFamilyData()
        self.close()


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
        if self.ui.nameInput.text().strip() == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên khu.")
            return

        zid = self.ui.idInput.text().strip()
        zname = self.ui.nameInput.text().strip()
        zpos = self.ui.scientificNameInput.text().strip()
        zdesc = self.ui.characteristicsInput.toPlainText().strip()

        # Giữ thao tác cũ
        zone_data.append(
            {"id": zid, "name": zname, "pos": zpos, "area": "N/A", "desc": zdesc, "status": "Đang hoạt động"})

        # Lưu database
        try:
            database.add_khutrungbay(makhu=zid, tenkhu=zname, vitri=zpos, dientich=None, mota=zdesc)
        except Exception as e:
            print(f"Lưu DB lỗi: {e}")

        self.parent.loadZoneData()
        self.close()


class PhieuNhanVienWindow(QDialog):

    def __init__(self, username, role, parent, next_id):
        super().__init__()
        self.parent = parent
        self.ui = Ui_PhieuNhanVien()
        self.ui.setupUi(self)
        self.ui.idInput.setText(next_id)
        self.ui.saveButton.clicked.connect(self.saveStaff)
        self.ui.cancelButton.clicked.connect(self.close)

    def saveStaff(self):
        if self.ui.nameInput.text().strip() == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên nhân viên.")
            return

        nid = self.ui.idInput.text().strip()
        nname = self.ui.nameInput.text().strip()
        ndob = self.ui.dobInput.text().strip()
        ngender = self.ui.genderCombo.currentText()
        nphone = self.ui.phoneInput.text().strip()
        nemail = self.ui.emailInput.text().strip()
        npos = self.ui.positionCombo.currentText()

        # Giữ thao tác cũ
        staff_data.append({"id": nid, "name": nname, "dob": ndob, "gender": ngender, "phone": nphone, "email": nemail,
                           "position": npos, "managed_by": "N/A"})

        # Lưu database
        try:
            database.add_nhanvien(manv=nid, hoten=nname, ngaysinh=ndob, gioitinh=ngender, dienthoai=nphone,
                                  email=nemail, chucvu=npos, matkhau="123")
        except Exception as e:
            print(f"Lưu DB lỗi: {e}")

        self.parent.loadStaffData()
        self.close()


# =========================================================
# GIAO DIỆN ĐĂNG KÝ / ĐĂNG NHẬP
# =========================================================
class SignWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.ui = Ui_RegisterForm()
        self.ui.setupUi(self)
        self.ui.registerButton.clicked.connect(self.register)

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
        self.ui.btn_role_guest.setStyleSheet(
            "QPushButton{background:#fffbeb;border:1px solid #b45309;border-radius:8px;color:#b45309;font-weight:bold;}")
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

        # 1. Nếu là Khách tham quan -> Chuyển sang màn hình đăng ký/vào thẳng
        if self.role == "Khách tham quan":
            self.sign = SignWindow()
            self.sign.show()
            self.close()
            return

        # 2. KIỂM TRA TÀI KHOẢN CỨNG ĐỂ TEST NHANH (Không cần mở SQL Server)
        # Nếu chọn Quản trị viên -> Nhập tài khoản: admin / mật khẩu: 123
        if self.role == "Quản trị viên" and username == "Nguyễn Văn A" and password == "123":
            self.main_window = MainWindow("Nguyễn Văn A", self.role)
            self.main_window.show()
            self.close()
            return

        # Nếu chọn Nhân viên -> Nhập tài khoản: staff / mật khẩu: 123
        if self.role == "Nhân viên" and username == "staff" and password == "123":
            self.main_window = MainWindow("Nhân Viên (Mẫu)", self.role)
            self.main_window.show()
            self.close()
            return

        # 3. NẾU KHÔNG PHẢI TÀI KHOẢN CỨNG -> QUÉT TRONG DATABASE SQL SERVER
        try:
            import database  # Gọi file kết nối database
            all_staff = database.get_all_nhanvien()

            for staff in all_staff:
                # Kiểm tra Mã NV hoặc Email khớp với mật khẩu
                if (staff["MANV"] == username or staff["EMAIL"] == username) and staff["MATKHAU"] == password:
                    # Kiểm tra chức vụ phù hợp với Vai trò đã chọn ở giao diện
                    if (self.role == "Quản trị viên" and staff["CHUCVU"] == "Trưởng phòng") or \
                            (self.role == "Nhân viên" and staff["CHUCVU"] != "Trưởng phòng"):
                        self.main_window = MainWindow(staff["HOTEN"], self.role)
                        self.main_window.show()
                        self.close()
                        return

            QMessageBox.warning(self, "Đăng nhập thất bại", "Sai tên đăng nhập, mật khẩu hoặc vai trò.")
        except Exception as e:
            # Nếu chưa bật SQL Server hoặc kết nối lỗi thì báo tài khoản test sai
            QMessageBox.warning(self, "Đăng nhập thất bại",
                                f"Sai tài khoản/mật khẩu mẫu hoặc Lỗi kết nối SQL Server.\n(Chi tiết: {e})")
class PhieuChamSocWindow(NavigationWindow):
    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_PhieuChamSoc()
        self.ui.setupUi(self)
        self.username = username
        self.role = role

        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        self.setup_sidebar_connections()


class PhieuKhaoSatWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_PhieuKhaoSat()
        self.ui.setupUi(self)
        self.username = username
        self.role = role

        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        self.setup_sidebar_connections()


class YeuCauBaoTriWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_YeuCauBaoTri()
        self.ui.setupUi(self)
        self.username = username
        self.role = role

        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        self.setup_sidebar_connections()


class BaoCaoSuCoWindow(NavigationWindow):

    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_BaoCaoSuCo()
        self.ui.setupUi(self)
        self.username = username
        self.role = role

        if hasattr(self.ui, "sidebarUserLabel"):
            self.ui.sidebarUserLabel.setText(f"👤 {username}")
        if hasattr(self.ui, "sidebarRoleLabel"):
            self.ui.sidebarRoleLabel.setText(role)

        self.setup_sidebar_connections()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())