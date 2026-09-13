import os
import sys
import random
import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QGroupBox, QCheckBox,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

import api_client
from camera_worker import CameraWorker, lay_danh_sach_camera

# ==============================================================================
# CẤU HÌNH MÔI TRƯỜNG
# ==============================================================================
# DEBUG: True -> Hiện hộp chọn camera & công cụ phát triển. False -> Sản phẩm cuối.
DEBUG: bool = os.getenv("APP_DEBUG", "True").lower() in ("true", "1", "yes")

# TEST_MODE: True -> Chạy với Mock Backend (không cần bật FastAPI server hoặc PostgreSQL).
# Có thể kích hoạt bằng biến môi trường: set APP_TEST_MODE=true
TEST_MODE: bool = os.getenv("APP_TEST_MODE", "False").lower() in ("true", "1", "yes")


class MockBackend:
    """Giả lập toàn bộ các API của Backend khi không có server thật chạy."""
    def __init__(self):
        self.sinh_vien_mau = [
            {"ma_sv": "250174802010022", "ho_ten": "Nguyễn Minh Đức"},
            {"ma_sv": "250174802010025", "ho_ten": "Nguyễn Hồng Nam"},
            {"ma_sv": "250174802010047", "ho_ten": "Phùng Thanh Độ"},
            {"ma_sv": "250174802010099", "ho_ten": "Trần Thu Hà"},
        ]
        # Lưu kết quả điểm danh theo ca_hoc_id: {ca_hoc_id: [records]}
        self.lich_su_ca = {}

    def lay_danh_sach_lop(self) -> list:
        return [
            {"id": 1, "ten_lop": "[Test Mode] CNTT01 - Công nghệ thông tin"},
            {"id": 2, "ten_lop": "[Test Mode] KTPM02 - Kỹ thuật phần mềm"},
            {"id": 3, "ten_lop": "[Test Mode] HTTT01 - Hệ thống thông tin"},
        ]

    def lay_danh_sach_ca(self, lop_id: int) -> list:
        return [
            {"id": 101, "ngay": "2026-09-14", "gio_bat_dau": "07:30", "gio_ket_thuc": "09:30"},
            {"id": 102, "ngay": "2026-09-14", "gio_bat_dau": "09:45", "gio_ket_thuc": "11:45"},
            {"id": 103, "ngay": "2026-09-15", "gio_bat_dau": "13:30", "gio_ket_thuc": "15:30"},
        ]

    def goi_diem_danh(self, ca_hoc_id: int, frame_base64: str) -> dict:
        # Giả lập: 70% cơ hội phát hiện ra sinh viên để test giao diện nhận diện
        if random.random() < 0.7:
            sv = random.choice(self.sinh_vien_mau)
            khoang_cach = round(random.uniform(0.12, 0.35), 4)

            ds = self.lich_su_ca.setdefault(ca_hoc_id, [])
            if not any(r["ma_sv"] == sv["ma_sv"] for r in ds):
                ds.append({
                    "ma_sv": sv["ma_sv"],
                    "ho_ten": sv["ho_ten"],
                    "trang_thai": "co_mat",
                    "thoi_gian": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })

            return {
                "so_mat_thay": 1,
                "ket_qua": [{
                    "nhan_dien": True,
                    "sinh_vien_id": int(sv["ma_sv"][-3:]),
                    "ho_ten": sv["ho_ten"],
                    "khoang_cach": khoang_cach,
                }]
            }
        else:
            return {
                "so_mat_thay": 1,
                "ket_qua": [{
                    "nhan_dien": False,
                    "khoang_cach": 0.58,
                }]
            }

    def lay_ket_qua_diem_danh(self, ca_hoc_id: int) -> dict:
        ds = self.lich_su_ca.get(ca_hoc_id, [])
        if not ds:
            ds = [{
                "ma_sv": self.sinh_vien_mau[0]["ma_sv"],
                "ho_ten": self.sinh_vien_mau[0]["ho_ten"],
                "trang_thai": "co_mat",
                "thoi_gian": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }]
        return {
            "ca_hoc_id": ca_hoc_id,
            "so_luong": len(ds),
            "danh_sach": ds,
        }


class ManHinhBatDauCa(QWidget):
    def __init__(self, chuyen_man_hinh, mock_backend: MockBackend, debug: bool = DEBUG, test_mode: bool = TEST_MODE):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        self.mock_backend = mock_backend
        self.debug = debug
        self.test_mode = test_mode
        layout = QVBoxLayout(self)

        # Banner trạng thái Test Mode
        self.nhan_banner_test = QLabel("⚠️ ĐANG Ở TEST MODE: Dữ liệu giả lập, không yêu cầu Backend API")
        self.nhan_banner_test.setStyleSheet("color: #b78103; font-weight: bold; padding: 4px; background-color: #fff9db; border-radius: 4px;")
        self.nhan_banner_test.setVisible(self.test_mode)
        layout.addWidget(self.nhan_banner_test)

        layout.addWidget(QLabel("Chọn lớp"))
        self.combo_lop = QComboBox()
        layout.addWidget(self.combo_lop)

        layout.addWidget(QLabel("Chọn ca học"))
        self.combo_ca = QComboBox()
        layout.addWidget(self.combo_ca)

        # Nhóm cấu hình Development & Test Mode
        self.group_dev = QGroupBox("⚙️ Cấu hình Nhà phát triển")
        layout_dev = QVBoxLayout(self.group_dev)

        self.chk_test_mode = QCheckBox("Bật Test Mode (Chạy giả lập - Không cần Backend)")
        self.chk_test_mode.setChecked(self.test_mode)
        self.chk_test_mode.toggled.connect(self.thay_doi_che_do_test)
        layout_dev.addWidget(self.chk_test_mode)

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

        nut_tai_lai = QPushButton("Tải lại danh sách (Thử kết nối lại)")
        nut_tai_lai.clicked.connect(self.tai_lai_toan_bo)
        layout.addWidget(nut_tai_lai)

        self.combo_lop.currentIndexChanged.connect(self.doi_lop)

    def thay_doi_che_do_test(self, bat: bool):
        self.test_mode = bat
        self.nhan_banner_test.setVisible(bat)
        self.tai_lai_toan_bo()

    def tai_danh_sach_camera(self):
        self.combo_camera.clear()
        try:
            danh_sach = lay_danh_sach_camera()
            for idx, ten in danh_sach:
                self.combo_camera.addItem(f"[{idx}] {ten}", idx)
        except Exception:
            self.combo_camera.addItem("Camera 0 (Mặc định)", 0)

    def tai_danh_sach_lop(self):
        if self.test_mode:
            danh_sach = self.mock_backend.lay_danh_sach_lop()
            self.combo_lop.clear()
            for lop in danh_sach:
                self.combo_lop.addItem(lop["ten_lop"], lop["id"])
            return

        try:
            danh_sach = api_client.lay_danh_sach_lop()
            self.combo_lop.clear()
            for lop in danh_sach:
                self.combo_lop.addItem(lop["ten_lop"], lop["id"])
        except Exception as e:
            tra_loi = QMessageBox.question(
                self,
                "Lỗi kết nối Backend API",
                f"Không thể kết nối đến Backend API ({api_client.BASE_URL}).\n\n"
                f"Chi tiết: {e}\n\n"
                "👉 Bạn có muốn BẬT 'Chế độ Test (Mock Backend)' để chạy thử giao diện và camera ngay bây giờ không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if tra_loi == QMessageBox.StandardButton.Yes:
                self.test_mode = True
                self.chk_test_mode.setChecked(True)
                self.nhan_banner_test.setVisible(True)
                self.tai_danh_sach_lop()

    def tai_lai_toan_bo(self):
        self.tai_danh_sach_lop()
        if self.debug:
            self.tai_danh_sach_camera()

    def doi_lop(self):
        lop_id = self.combo_lop.currentData()
        if lop_id is None:
            return

        if self.test_mode:
            danh_sach_ca = self.mock_backend.lay_danh_sach_ca(lop_id)
        else:
            try:
                danh_sach_ca = api_client.lay_danh_sach_ca(lop_id)
            except Exception as e:
                QMessageBox.warning(self, "Lỗi kết nối", f"Không thể lấy danh sách ca học: {e}")
                return

        self.combo_ca.clear()
        for ca in danh_sach_ca:
            self.combo_ca.addItem(f"{ca['ngay']} - {ca['gio_bat_dau']}", ca["id"])

    def bat_dau(self):
        ca_hoc_id = self.combo_ca.currentData()
        if ca_hoc_id is not None:
            camera_id = 0
            if self.debug and self.combo_camera.currentData() is not None:
                camera_id = self.combo_camera.currentData()
            self.chuyen_man_hinh("diem_danh_live", ca_hoc_id, camera_id, self.test_mode)


class ManHinhDiemDanhLive(QWidget):
    def __init__(self, chuyen_man_hinh, mock_backend: MockBackend):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        self.mock_backend = mock_backend
        self.worker = None
        self.ca_hoc_id = None
        self.camera_id = 0
        self.test_mode = False

        layout = QVBoxLayout(self)

        self.nhan_thong_bao_che_do = QLabel("")
        self.nhan_thong_bao_che_do.setStyleSheet("color: #b78103; font-weight: bold;")
        layout.addWidget(self.nhan_thong_bao_che_do)

        self.nhan_camera = QLabel("Đang chờ camera...")
        self.nhan_camera.setMinimumHeight(360)
        layout.addWidget(self.nhan_camera)

        self.nhan_ket_qua = QLabel("")
        layout.addWidget(self.nhan_ket_qua)

        nut_ket_thuc = QPushButton("Kết thúc ca")
        nut_ket_thuc.clicked.connect(self.ket_thuc)
        layout.addWidget(nut_ket_thuc)

    def vao_man_hinh(self, ca_hoc_id: int, camera_id: int = 0, test_mode: bool = False):
        self.ca_hoc_id = ca_hoc_id
        self.camera_id = camera_id
        self.test_mode = test_mode
        self.nhan_ket_qua.setText("")

        if self.test_mode:
            self.nhan_thong_bao_che_do.setText("⚠️ [TEST MODE] Đang dùng AI Mock (Giả lập nhận diện)")
            fn_diem_danh = self.mock_backend.goi_diem_danh
        else:
            self.nhan_thong_bao_che_do.setText("")
            fn_diem_danh = api_client.goi_diem_danh

        self.worker = CameraWorker(ca_hoc_id, fn_diem_danh, camera_id=self.camera_id)
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
            self.worker.wait()
        self.chuyen_man_hinh("tong_ket", self.ca_hoc_id, 0, self.test_mode)


class ManHinhTongKet(QWidget):
    def __init__(self, chuyen_man_hinh, mock_backend: MockBackend):
        super().__init__()
        self.chuyen_man_hinh = chuyen_man_hinh
        self.mock_backend = mock_backend
        layout = QVBoxLayout(self)

        self.nhan_tieu_de = QLabel("Tổng kết")
        layout.addWidget(self.nhan_tieu_de)

        self.bang = QTableWidget(0, 3)
        self.bang.setHorizontalHeaderLabels(["Mã SV", "Họ tên", "Trạng thái"])
        layout.addWidget(self.bang)

        nut_quay_lai = QPushButton("Về màn hình bắt đầu")
        nut_quay_lai.clicked.connect(lambda: self.chuyen_man_hinh("bat_dau_ca", None))
        layout.addWidget(nut_quay_lai)

    def vao_man_hinh(self, ca_hoc_id: int, test_mode: bool = False):
        try:
            if test_mode:
                du_lieu = self.mock_backend.lay_ket_qua_diem_danh(ca_hoc_id)
            else:
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
    def __init__(self, debug: bool = DEBUG, test_mode: bool = TEST_MODE):
        super().__init__()
        self.debug = debug
        self.test_mode = test_mode
        self.mock_backend = MockBackend()

        tieu_de = "Hệ thống điểm danh khuôn mặt"
        if self.test_mode:
            tieu_de += " [TEST MODE - Giả lập]"
        elif self.debug:
            tieu_de += " [Chế độ Development]"
        self.setWindowTitle(tieu_de)
        self.resize(800, 600)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.man_bat_dau = ManHinhBatDauCa(self.chuyen_man_hinh, self.mock_backend, debug=self.debug, test_mode=self.test_mode)
        self.man_diem_danh = ManHinhDiemDanhLive(self.chuyen_man_hinh, self.mock_backend)
        self.man_tong_ket = ManHinhTongKet(self.chuyen_man_hinh, self.mock_backend)

        self.stack.addWidget(self.man_bat_dau)
        self.stack.addWidget(self.man_diem_danh)
        self.stack.addWidget(self.man_tong_ket)

        self.man_bat_dau.tai_danh_sach_lop()

    def chuyen_man_hinh(self, ten_man_hinh: str, ca_hoc_id, camera_id: int = 0, test_mode: bool = False):
        if ten_man_hinh == "diem_danh_live":
            self.man_diem_danh.vao_man_hinh(ca_hoc_id, camera_id, test_mode)
            self.stack.setCurrentWidget(self.man_diem_danh)
        elif ten_man_hinh == "tong_ket":
            self.man_tong_ket.vao_man_hinh(ca_hoc_id, test_mode)
            self.stack.setCurrentWidget(self.man_tong_ket)
        elif ten_man_hinh == "bat_dau_ca":
            self.man_bat_dau.tai_lai_toan_bo()
            self.stack.setCurrentWidget(self.man_bat_dau)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    cua_so = CuaSoChinh()
    cua_so.show()
    sys.exit(app.exec())

 