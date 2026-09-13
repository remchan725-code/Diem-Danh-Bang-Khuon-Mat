import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
 
import api_client
from camera_worker import CameraWorker
 
 
class ManHinhBatDauCa(QWidget):
    def __init__(self, chuyen_man_hinh):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        layout = QVBoxLayout(self)
 
        layout.addWidget(QLabel("Chọn lớp"))
        self.combo_lop = QComboBox()
        layout.addWidget(self.combo_lop)
 
        layout.addWidget(QLabel("Chọn ca học"))
        self.combo_ca = QComboBox()
        layout.addWidget(self.combo_ca)
 
        nut_bat_dau = QPushButton("Bắt đầu điểm danh")
        nut_bat_dau.clicked.connect(self.bat_dau)
        layout.addWidget(nut_bat_dau)
 
        nut_tai_lai = QPushButton("Tải lại danh sách (Thử kết nối lại)")
        nut_tai_lai.clicked.connect(self.tai_danh_sach_lop)
        layout.addWidget(nut_tai_lai)
 
        self.combo_lop.currentIndexChanged.connect(self.doi_lop)
 
    def tai_danh_sach_lop(self):
        try:
            danh_sach = api_client.lay_danh_sach_lop()
            self.combo_lop.clear()
            for lop in danh_sach:
                self.combo_lop.addItem(lop["ten_lop"], lop["id"])
        except Exception as e:
            QMessageBox.warning(
                self,
                "Lỗi kết nối Backend API",
                f"Không thể kết nối đến Backend API ({api_client.BASE_URL}).\n\n"
                f"Chi tiết lỗi: {e}\n\n"
                "Vui lòng đảm bảo Backend API đã được khởi động trước (uvicorn main:app --reload) rồi bấm 'Tải lại danh sách'.",
            )
 
    def doi_lop(self):
        lop_id = self.combo_lop.currentData()
        if lop_id is None:
            return
        try:
            danh_sach_ca = api_client.lay_danh_sach_ca(lop_id)
            self.combo_ca.clear()
            for ca in danh_sach_ca:
                self.combo_ca.addItem(f"{ca['ngay']} - {ca['gio_bat_dau']}", ca["id"])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi kết nối", f"Không thể lấy danh sách ca học: {e}")
 
    def bat_dau(self):
        ca_hoc_id = self.combo_ca.currentData()
        if ca_hoc_id is not None:
            self.chuyen_man_hinh("diem_danh_live", ca_hoc_id)
 
 
class ManHinhDiemDanhLive(QWidget):
    def __init__(self, chuyen_man_hinh):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        self.worker = None
        self.ca_hoc_id = None
 
        layout = QVBoxLayout(self)
        self.nhan_camera = QLabel("Đang chờ camera...")
        self.nhan_camera.setMinimumHeight(360)
        layout.addWidget(self.nhan_camera)
 
        self.nhan_ket_qua = QLabel("")
        layout.addWidget(self.nhan_ket_qua)
 
        nut_ket_thuc = QPushButton("Kết thúc ca")
        nut_ket_thuc.clicked.connect(self.ket_thuc)
        layout.addWidget(nut_ket_thuc)
 
    def vao_man_hinh(self, ca_hoc_id: int):
        self.ca_hoc_id = ca_hoc_id
        self.nhan_ket_qua.setText("")
        # QUAN TRỌNG: camera chạy trên QThread riêng — main thread chỉ nhận
        # kết quả qua signal, không bao giờ tự đọc webcam trực tiếp ở đây.
        self.worker = CameraWorker(ca_hoc_id, api_client.goi_diem_danh)
        self.worker.khung_hinh_moi.connect(self.cap_nhat_khung_hinh)
        self.worker.ket_qua_diem_danh.connect(self.cap_nhat_ket_qua)
        self.worker.loi.connect(lambda msg: self.nhan_ket_qua.setText(f"Lỗi: {msg}"))
        self.worker.start()
 
    def cap_nhat_khung_hinh(self, jpeg_bytes: bytes):
        pixmap = QPixmap()
        pixmap.loadFromData(jpeg_bytes)
        self.nhan_camera.setPixmap(
            pixmap.scaled(640, 360, Qt.AspectRatioMode.KeepAspectRatio)
        )
 
    def cap_nhat_ket_qua(self, ket_qua: dict):
        dong = [f"{r['ho_ten']} ({r.get('khoang_cach')})"
                for r in ket_qua["ket_qua"] if r["nhan_dien"]]
        if dong:
            self.nhan_ket_qua.setText("Vừa nhận diện: " + ", ".join(dong))
 
    def ket_thuc(self):
        if self.worker:
            self.worker.dung_lai()
            self.worker.wait()  # đợi thread thoát hẳn trước khi chuyển màn hình
        self.chuyen_man_hinh("tong_ket", self.ca_hoc_id)
 
 
class ManHinhTongKet(QWidget):
    def __init__(self, chuyen_man_hinh):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        layout = QVBoxLayout(self)
 
        self.nhan_tieu_de = QLabel("Tổng kết")
        layout.addWidget(self.nhan_tieu_de)
 
        self.bang = QTableWidget(0, 3)
        self.bang.setHorizontalHeaderLabels(["Mã SV", "Họ tên", "Trạng thái"])
        layout.addWidget(self.bang)
 
        nut_quay_lai = QPushButton("Về màn hình bắt đầu")
        nut_quay_lai.clicked.connect(lambda: self.chuyen_man_hinh("bat_dau_ca", None))
        layout.addWidget(nut_quay_lai)
 
    def vao_man_hinh(self, ca_hoc_id: int):
        try:
            du_lieu = api_client.lay_ket_qua_diem_danh(ca_hoc_id)
            self.nhan_tieu_de.setText(
                f"Ca học #{ca_hoc_id} — {du_lieu['so_luong']} sinh viên đã điểm danh"
            )
            self.bang.setRowCount(len(du_lieu["danh_sach"]))
            for hang, sv in enumerate(du_lieu["danh_sach"]):
                self.bang.setItem(hang, 0, QTableWidgetItem(sv["ma_sv"]))
                self.bang.setItem(hang, 1, QTableWidgetItem(sv["ho_ten"]))
                self.bang.setItem(hang, 2, QTableWidgetItem(sv["trang_thai"]))
        except Exception as e:
            QMessageBox.warning(self, "Lỗi API", f"Không thể tải kết quả điểm danh: {e}")

 
 
class CuaSoChinh(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hệ thống điểm danh khuôn mặt")
        self.resize(800, 600)
 
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
 
        self.man_bat_dau = ManHinhBatDauCa(self.chuyen_man_hinh)
        self.man_diem_danh = ManHinhDiemDanhLive(self.chuyen_man_hinh)
        self.man_tong_ket = ManHinhTongKet(self.chuyen_man_hinh)
 
        self.stack.addWidget(self.man_bat_dau)
        self.stack.addWidget(self.man_diem_danh)
        self.stack.addWidget(self.man_tong_ket)
 
        self.man_bat_dau.tai_danh_sach_lop()
 
    def chuyen_man_hinh(self, ten_man_hinh: str, ca_hoc_id):
        if ten_man_hinh == "diem_danh_live":
            self.man_diem_danh.vao_man_hinh(ca_hoc_id)
            self.stack.setCurrentWidget(self.man_diem_danh)
        elif ten_man_hinh == "tong_ket":
            self.man_tong_ket.vao_man_hinh(ca_hoc_id)
            self.stack.setCurrentWidget(self.man_tong_ket)
        elif ten_man_hinh == "bat_dau_ca":
            self.man_bat_dau.tai_danh_sach_lop()
            self.stack.setCurrentWidget(self.man_bat_dau)
 
 
if __name__ == "__main__":
    app = QApplication(sys.argv)
    cua_so = CuaSoChinh()
    cua_so.show()
    sys.exit(app.exec())
 