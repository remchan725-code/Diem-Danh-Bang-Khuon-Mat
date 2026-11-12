import os
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QFileDialog, QLineEdit, QFormLayout,
    QHBoxLayout,
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt

import api_client
from camera_worker import CameraWorker, FaceCaptureWorker, lay_danh_sach_camera

# ==============================================================================
# CẤU HÌNH MÔI TRƯỜNG
# ==============================================================================
# DEBUG: True -> Hiện hộp chọn camera & công cụ phát triển. False -> Sản phẩm cuối.
DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() in ("true", "1", "yes")

class ManHinhBatDauCa(QWidget):
    def __init__(self, chuyen_man_hinh, debug: bool = DEBUG):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        self.debug = debug
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Chọn lớp"))
        self.combo_lop = QComboBox()
        layout.addWidget(self.combo_lop)

        layout.addWidget(QLabel("Chọn ca học"))
        self.combo_ca = QComboBox()
        layout.addWidget(self.combo_ca)

        # Nhóm cấu hình Development
        self.group_dev = QGroupBox("⚙️ Cấu hình Nhà phát triển")
        layout_dev = QVBoxLayout(self.group_dev)

        layout_dev.addWidget(QLabel("Chọn thiết bị Camera:"))
        self.combo_camera = QComboBox()
        layout_dev.addWidget(self.combo_camera)
        layout.addWidget(self.group_dev)

        self.group_dev.setVisible(self.debug)
        if self.debug:
            self.tai_danh_sach_camera()

        nut_bat_dau = QPushButton("Bắt đầu điểm danh")
        nut_bat_dau.clicked.connect(self.bat_dau)
        layout.addWidget(nut_bat_dau)

        nut_dang_ky = QPushButton("Đăng ký khuôn mặt mới")
        nut_dang_ky.clicked.connect(lambda: self.chuyen_man_hinh("dang_ky", None))
        layout.addWidget(nut_dang_ky)

        nut_tai_lai = QPushButton("Tải lại danh sách (Thử kết nối lại)")
        nut_tai_lai.clicked.connect(self.tai_lai_toan_bo)
        layout.addWidget(nut_tai_lai)

        self.combo_lop.currentIndexChanged.connect(self.doi_lop)

    def tai_danh_sach_camera(self):
        self.combo_camera.clear()
        try:
            danh_sach = lay_danh_sach_camera()
            for idx, ten in danh_sach:
                self.combo_camera.addItem(f"[{idx}] {ten}", idx)
        except Exception:
            self.combo_camera.addItem("Camera 0 (Mặc định)", 0)

    def tai_danh_sach_lop(self):
        try:
            danh_sach = api_client.lay_danh_sach_lop()
            self.combo_lop.clear()
            for lop in danh_sach:
                self.combo_lop.addItem(lop["ten_lop"], lop["id"])
        except Exception as e:
            self.combo_lop.clear()
            self.combo_ca.clear()
            QMessageBox.warning(
                self,
                "Lỗi kết nối Backend API",
                f"Không thể kết nối đến Backend API ({api_client.BASE_URL}).\n\n"
                f"Chi tiết: {e}\n\nKiểm tra dịch vụ và cấu hình BACKEND_API_BASE_URL.",
            )

    def tai_lai_toan_bo(self):
        self.tai_danh_sach_lop()
        if self.debug:
            self.tai_danh_sach_camera()

    def doi_lop(self):
        lop_id = self.combo_lop.currentData()
        if lop_id is None:
            return

        self.combo_ca.clear()
        try:
            danh_sach_ca = api_client.lay_danh_sach_ca(lop_id)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi kết nối", f"Không thể lấy danh sách ca học: {e}")
            return

        for ca in danh_sach_ca:
            self.combo_ca.addItem(f"{ca['ngay']} - {ca['gio_bat_dau']}", ca["id"])

    def bat_dau(self):
        ca_hoc_id = self.combo_ca.currentData()
        if ca_hoc_id is not None:
            camera_id = 0
            if self.debug and self.combo_camera.currentData() is not None:
                camera_id = self.combo_camera.currentData()
            self.chuyen_man_hinh("diem_danh_live", ca_hoc_id, camera_id)


class ManHinhDangKy(QWidget):
    def __init__(self, chuyen_man_hinh):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        self.worker = None
        self.anh_hien_tai = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.o_ma_sv = QLineEdit()
        self.o_ho_ten = QLineEdit()
        self.combo_lop = QComboBox()
        form.addRow("Mã sinh viên", self.o_ma_sv)
        form.addRow("Họ tên", self.o_ho_ten)
        form.addRow("Lớp", self.combo_lop)
        layout.addLayout(form)

        hang_camera = QHBoxLayout()
        self.combo_camera = QComboBox()
        for camera_id, ten in lay_danh_sach_camera():
            self.combo_camera.addItem(f"[{camera_id}] {ten}", camera_id)
        hang_camera.addWidget(QLabel("Camera"))
        hang_camera.addWidget(self.combo_camera)
        layout.addLayout(hang_camera)

        self.nhan_anh = QLabel("Chưa có ảnh")
        self.nhan_anh.setMinimumSize(640, 360)
        self.nhan_anh.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.nhan_anh)

        nut_anh = QPushButton("Thêm ảnh từ máy tính")
        nut_anh.clicked.connect(self.chon_anh)
        self.nut_camera = QPushButton("Bật quét camera")
        self.nut_camera.clicked.connect(self.bat_tat_camera)
        self.nut_luu = QPushButton("Lưu vector và đăng ký")
        self.nut_luu.clicked.connect(self.luu_dang_ky)
        self.nut_luu.setEnabled(False)
        hang_nut = QHBoxLayout()
        hang_nut.addWidget(nut_anh)
        hang_nut.addWidget(self.nut_camera)
        hang_nut.addWidget(self.nut_luu)
        layout.addLayout(hang_nut)

        self.nhan_trang_thai = QLabel("")
        layout.addWidget(self.nhan_trang_thai)
        nut_quay_lai = QPushButton("Quay lại")
        nut_quay_lai.clicked.connect(lambda: self.chuyen_man_hinh("bat_dau_ca", None))
        layout.addWidget(nut_quay_lai)

    def vao_man_hinh(self):
        self.tai_danh_sach_lop()
        self.nhan_trang_thai.setText("Chọn ảnh tải lên hoặc bật camera để lấy ảnh trực tiếp.")

    def tai_danh_sach_lop(self):
        try:
            danh_sach = api_client.lay_danh_sach_lop()
            self.combo_lop.clear()
            for lop in danh_sach:
                self.combo_lop.addItem(lop["ten_lop"], lop["id"])
        except Exception as e:
            self.nhan_trang_thai.setText(f"Không tải được danh sách lớp: {e}")

    def bat_camera(self):
        if self.worker:
            return
        camera_id = self.combo_camera.currentData()
        self.worker = FaceCaptureWorker(camera_id if camera_id is not None else 0)
        self.worker.khung_hinh_moi.connect(self.cap_nhat_frame)
        self.worker.loi.connect(self.bao_loi_camera)
        self.worker.finished.connect(self.camera_da_dung)
        self.worker.start()
        self.nut_camera.setText("Tắt camera")

    def bat_tat_camera(self):
        if self.worker:
            self.dung_camera()
        else:
            self.bat_camera()

    def dung_camera(self):
        if self.worker:
            self.worker.dung_lai()
            self.worker.wait()
            self.worker = None
        self.nut_camera.setText("Bật quét camera")

    def camera_da_dung(self):
        self.worker = None
        self.nut_camera.setText("Bật quét camera")

    def bao_loi_camera(self, thong_bao):
        self.nhan_trang_thai.setText(thong_bao)

    def cap_nhat_frame(self, image_bytes):
        self.anh_hien_tai = image_bytes
        pixmap = QPixmap()
        pixmap.loadFromData(image_bytes)
        self.nhan_anh.setPixmap(pixmap.scaled(640, 360, Qt.AspectRatioMode.KeepAspectRatio))
        self.nut_luu.setEnabled(True)

    def chon_anh(self):
        duong_dan, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh khuôn mặt", "", "Ảnh (*.jpg *.jpeg *.png *.bmp)"
        )
        if not duong_dan:
            return
        try:
            with open(duong_dan, "rb") as tep:
                image_bytes = tep.read()
            self.dung_camera()
            self.cap_nhat_frame(image_bytes)
            self.nhan_trang_thai.setText("Đã tải ảnh. Kiểm tra ảnh trước khi lưu đăng ký.")
        except OSError as e:
            self.nhan_trang_thai.setText(f"Không đọc được ảnh: {e}")

    def luu_dang_ky(self):
        ma_sv = self.o_ma_sv.text().strip()
        ho_ten = self.o_ho_ten.text().strip()
        lop_id = self.combo_lop.currentData()
        if not ma_sv or not ho_ten or lop_id is None or not self.anh_hien_tai:
            QMessageBox.warning(self, "Thiếu dữ liệu", "Cần nhập mã, họ tên, lớp và có ảnh khuôn mặt.")
            return
        self.nut_luu.setEnabled(False)
        try:
            ket_qua = api_client.dang_ky_sinh_vien(ma_sv, ho_ten, lop_id, self.anh_hien_tai)
            QMessageBox.information(
                self,
                "Đăng ký thành công",
                f"Đã lưu vector 512 chiều cho {ho_ten}.\nConfidence: {ket_qua['confidence']}",
            )
            self.o_ma_sv.clear()
            self.o_ho_ten.clear()
            self.anh_hien_tai = None
            self.nhan_anh.setText("Chưa có ảnh")
        except Exception as e:
            QMessageBox.critical(self, "Đăng ký thất bại", f"Không thể tạo hoặc lưu vector: {e}")
        finally:
            self.nut_luu.setEnabled(bool(self.anh_hien_tai))

    def dong(self):
        self.dung_camera()


class ManHinhDiemDanhLive(QWidget):
    def __init__(self, chuyen_man_hinh):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        self.worker = None
        self.ca_hoc_id = None
        self.camera_id = 0
        self.cac_khuon_mat_hien_tai = []

        layout = QVBoxLayout(self)

        self.nhan_camera = QLabel("Đang chờ camera...")
        self.nhan_camera.setMinimumHeight(360)
        layout.addWidget(self.nhan_camera)

        self.nhan_ket_qua = QLabel("")
        layout.addWidget(self.nhan_ket_qua)

        nut_ket_thuc = QPushButton("Kết thúc ca")
        nut_ket_thuc.clicked.connect(self.ket_thuc)
        layout.addWidget(nut_ket_thuc)

    def vao_man_hinh(self, ca_hoc_id: int, camera_id: int = 0):
        self.ca_hoc_id = ca_hoc_id
        self.camera_id = camera_id
        self.nhan_ket_qua.setText("")
        self.worker = CameraWorker(
            ca_hoc_id, api_client.goi_diem_danh, camera_id=self.camera_id
        )
        self.worker.khung_hinh_moi.connect(self.cap_nhat_khung_hinh)
        self.worker.ket_qua_diem_danh.connect(self.cap_nhat_ket_qua)
        self.worker.loi.connect(lambda msg: self.nhan_ket_qua.setText(f"Lỗi: {msg}"))
        self.worker.start()

    def cap_nhat_khung_hinh(self, jpeg_bytes: bytes):
        image = QImage()
        image.loadFromData(jpeg_bytes)

        painter = QPainter(image)
        but_xanh = QPen(QColor("#2f9e44"), 3)   # nhận diện thành công (chap_nhan)
        but_do = QPen(QColor("#e03131"), 3)     # từ chối hoặc không xác định
        phong_chu = QFont()
        phong_chu.setPointSize(14)
        painter.setFont(phong_chu)

        for mat in self.cac_khuon_mat_hien_tai:
            bbox = mat.get("bbox")
            if not bbox:
                continue
            x1, y1, x2, y2 = bbox
            dat_yeu_cau = mat.get("nhan_dien", False)
            painter.setPen(but_xanh if dat_yeu_cau else but_do)
            painter.drawRect(x1, y1, x2 - x1, y2 - y1)
            nhan = mat["ho_ten"] if dat_yeu_cau else "Không xác định"
            painter.drawText(x1, max(y1 - 8, 14), nhan)

        painter.end()

        pixmap = QPixmap.fromImage(image)
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
            self.worker.wait()
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
    def __init__(self, debug: bool = DEBUG):
        super().__init__()
        self.debug = debug

        tieu_de = "Hệ thống điểm danh khuôn mặt"
        if self.debug:
            tieu_de += " [Chế độ Development]"
        self.setWindowTitle(tieu_de)
        self.resize(800, 600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.man_bat_dau = ManHinhBatDauCa(self.chuyen_man_hinh, debug=self.debug)
        self.man_dang_ky = ManHinhDangKy(self.chuyen_man_hinh)
        self.man_diem_danh = ManHinhDiemDanhLive(self.chuyen_man_hinh)
        self.man_tong_ket = ManHinhTongKet(self.chuyen_man_hinh)

        self.stack.addWidget(self.man_bat_dau)
        self.stack.addWidget(self.man_dang_ky)
        self.stack.addWidget(self.man_diem_danh)
        self.stack.addWidget(self.man_tong_ket)

        self.man_bat_dau.tai_danh_sach_lop()

    def chuyen_man_hinh(self, ten_man_hinh: str, ca_hoc_id, camera_id: int = 0):
        if ten_man_hinh == "dang_ky":
            self.man_dang_ky.vao_man_hinh()
            self.stack.setCurrentWidget(self.man_dang_ky)
        elif ten_man_hinh == "diem_danh_live":
            self.man_diem_danh.vao_man_hinh(ca_hoc_id, camera_id)
            self.stack.setCurrentWidget(self.man_diem_danh)
        elif ten_man_hinh == "tong_ket":
            self.man_tong_ket.vao_man_hinh(ca_hoc_id)
            self.stack.setCurrentWidget(self.man_tong_ket)
        elif ten_man_hinh == "bat_dau_ca":
            self.man_dang_ky.dong()
            self.man_bat_dau.tai_lai_toan_bo()
            self.stack.setCurrentWidget(self.man_bat_dau)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    cua_so = CuaSoChinh()
    cua_so.show()
    sys.exit(app.exec())

 