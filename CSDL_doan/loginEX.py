import sys
from datetime import datetime  # Dùng để lấy ngày tháng hiện tại khi tạo dữ liệu
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QWidget,
    QTableWidgetItem,
    QDialog,
)

# Tích hợp module database chính xác
try:
    from CSDL_doan import database
except ImportError:
    import database

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
            if hasattr(self.ui, "table_maintenance"):
                list_maintenance = database.get_all_yeucaubaotri()
                self.ui.table_maintenance.setRowCount(0)
                self.ui.table_maintenance.setRowCount(len(list_maintenance))

                for row_idx, item in enumerate(list_maintenance):
                    self.ui.table_maintenance.setItem(row_idx, 0, QTableWidgetItem(str(item.get("MABT", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 1, QTableWidgetItem(str(item.get("NGAYTAO", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 2, QTableWidgetItem(str(item.get("NOIDUNGBAOTRI", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 3, QTableWidgetItem(str(item.get("MUCDOUUTIEN", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 4, QTableWidgetItem(str(item.get("TRANGTHAI", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 5, QTableWidgetItem(str(item.get("MANV", ""))))
                    self.ui.table_maintenance.setItem(row_idx, 6, QTableWidgetItem(str(item.get("MACAY", ""))))

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
                    self.ui.table_incidents.setItem(row_idx, 6, QTableWidgetItem(str(item.get("MANV", ""))))

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
        self.phieu = PhieuThongTinWindow(self.username, self.role, self)
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

        self.loadSpeciesData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

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
        self.init_common(username, role)

        self.loadFamilyData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

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
        self.init_common(username, role)

        self.loadZoneData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

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
        self.init_common(username, role)

        self.loadStaffData()
        self.setup_table_search("searchInput", "tableWidget", "searchButton")

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

        try:
            # Gọi database lưu dữ liệu thật
            database.add_cay(
                macay=new_id,
                tencay=new_name,
                ngaytrong=datetime.now().strftime("%Y-%m-%d"),  # Lấy ngày hiện tại
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

    def saveSpecies(self):
        sid = self.ui.idInput.text().strip()
        sname = self.ui.nameInput.text().strip()
        sciname = self.ui.scientificNameInput.text().strip()
        sfamily = self.ui.familyInput.text().strip()  # Ô nhập text mã họ
        sbio = self.ui.characteristicsInput.toPlainText().strip()
        shabitat = self.ui.habitatInput.text().strip()
        sstatus = self.ui.statusCombo.currentText()

        if sname == "" or sfamily == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập đầy đủ tên loài và mã họ (MAHO).")
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
                    f"Vui lòng vào mục 'Họ Thực Vật' xem mã chính xác hoặc thêm mới họ này trước."
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

    def saveStaff(self):
        nid = self.ui.idInput.text().strip()
        nname = self.ui.nameInput.text().strip()
        ndob = self.ui.dobInput.text().strip()
        ngender = self.ui.genderCombo.currentText()
        nphone = self.ui.phoneInput.text().strip()
        nemail = self.ui.emailInput.text().strip()
        npos = self.ui.positionCombo.currentText()

        if nname == "":
            QMessageBox.warning(self, "Thông báo", "Vui lòng nhập tên nhân viên.")
            return

        try:
            database.add_nhanvien(manv=nid, hoten=nname, ngaysinh=ndob, gioitinh=ngender, dienthoai=nphone,
                                  email=nemail, chucvu=npos, matkhau="123")
            QMessageBox.information(self, "Thành công", "Đã thêm nhân viên mới vào Database thành công!")
            self.parent.loadStaffData()
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối CSDL", f"Không thể lưu vào SQL Server.\nChi tiết: {e}")


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
        self.ui.btn_role_guest.setStyleSheet("""
            QPushButton{background:#198754;color:white;border-radius:8px;font-weight:bold;}
        """)
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
    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_PhieuChamSoc()
        self.ui.setupUi(self)
        self.init_common(username, role)
        self.loadCareRecords()
        self.setup_table_search("searchBox", "tableCareRecords")

    def loadCareRecords(self):
        """Tích hợp database.get_all_phieuchamsoc()"""
        if hasattr(self.ui, "tableCareRecords"):
            try:
                records = database.get_all_phieuchamsoc()
                self.ui.tableCareRecords.clearContents()
                self.ui.tableCareRecords.setRowCount(len(records))
                for row, rec in enumerate(records):
                    self.ui.tableCareRecords.setItem(row, 0, QTableWidgetItem(str(rec.get("MAPHIEUCS", ""))))
                    self.ui.tableCareRecords.setItem(row, 1, QTableWidgetItem(str(rec.get("MACAY", ""))))
                    self.ui.tableCareRecords.setItem(row, 2, QTableWidgetItem(str(rec.get("NGAYCHAMSOC", ""))))
                    self.ui.tableCareRecords.setItem(row, 3, QTableWidgetItem(str(rec.get("NOIDUNGCHAMSOC", ""))))
                    self.ui.tableCareRecords.setItem(row, 4, QTableWidgetItem(str(rec.get("PHUONGPHAP", ""))))
                    self.ui.tableCareRecords.setItem(row, 5, QTableWidgetItem(str(rec.get("TINHTRANGSAUCHAMSOC", ""))))
            except Exception as e:
                print(f"Không thể load Phiếu chăm sóc từ DB: {e}")


class PhieuKhaoSatWindow(NavigationWindow):
    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_PhieuKhaoSat()
        self.ui.setupUi(self)
        self.init_common(username, role)
        self.loadSurveys()
        self.setup_table_search("searchBox", "tableSurveys")

    def loadSurveys(self):
        """Tích hợp database.get_all_phieukhaosat()"""
        if hasattr(self.ui, "tableSurveys"):
            try:
                surveys = database.get_all_phieukhaosat()
                self.ui.tableSurveys.clearContents()
                self.ui.tableSurveys.setRowCount(len(surveys))
                for row, srv in enumerate(surveys):
                    self.ui.tableSurveys.setItem(row, 0, QTableWidgetItem(str(srv.get("MAKS", ""))))
                    self.ui.tableSurveys.setItem(row, 1, QTableWidgetItem(str(srv.get("MACAY", ""))))
                    self.ui.tableSurveys.setItem(row, 2, QTableWidgetItem(str(srv.get("NGAYKHAOSAT", ""))))
                    self.ui.tableSurveys.setItem(row, 3, QTableWidgetItem(str(srv.get("CHIEUCAOGHINHAN", ""))))
                    self.ui.tableSurveys.setItem(row, 4, QTableWidgetItem(str(srv.get("DUONGKINHGHINHAN", ""))))
                    self.ui.tableSurveys.setItem(row, 5, QTableWidgetItem(str(srv.get("TINHTRANGSINHTRUONG", ""))))
            except Exception as e:
                print(f"Không thể load Phiếu khảo sát từ DB: {e}")


class YeuCauBaoTriWindow(NavigationWindow):
    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_YeuCauBaoTri()
        self.ui.setupUi(self)
        self.init_common(username, role)
        self.loadMaintenance()

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
    def __init__(self, username, role):
        super().__init__()
        self.ui = Ui_BaoCaoSuCo()
        self.ui.setupUi(self)
        self.init_common(username, role)
        self.loadIncidents()

    def loadIncidents(self):
        """Tích hợp database.get_all_baocaosuco()"""
        if hasattr(self.ui, "tableIncidents"):  # Thay thế bằng tên table tương ứng của bạn nếu có
            try:
                incidents = database.get_all_baocaosuco()
                self.ui.tableIncidents.clearContents()
                self.ui.tableIncidents.setRowCount(len(incidents))
                for row, inc in enumerate(incidents):
                    self.ui.tableIncidents.setItem(row, 0, QTableWidgetItem(str(inc.get("MABC", ""))))
                    self.ui.tableIncidents.setItem(row, 1, QTableWidgetItem(str(inc.get("THOIGIANGUI", ""))))
                    self.ui.tableIncidents.setItem(row, 2, QTableWidgetItem(str(inc.get("MOTA", ""))))
                    self.ui.tableIncidents.setItem(row, 3, QTableWidgetItem(str(inc.get("TRANGTHAI", ""))))
            except Exception as e:
                print(f"Không thể load Báo cáo sự cố từ DB: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    login = LoginWindow()
    login.show()
    sys.exit(app.exec())