import time
import base64
import cv2
from PyQt6.QtCore import QThread, pyqtSignal
 
 
def lay_danh_sach_camera() -> list[tuple[int, str]]:
    """Trả về danh sách các camera khả dụng dạng [(index, ten_thiet_bi), ...].
    Ưu tiên lấy tên thiết bị từ QMediaDevices (PyQt6). Nếu không có, fallback về OpenCV."""
    danh_sach = []
    try:
        from PyQt6.QtMultimedia import QMediaDevices
        devices = QMediaDevices.videoInputs()
        for i, device in enumerate(devices):
            ten = device.description().strip() or f"Camera {i}"
            danh_sach.append((i, ten))
    except Exception:
        pass

    # Nếu không phát hiện qua Qt, quét index bằng OpenCV
    if not danh_sach:
        for i in range(4):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                danh_sach.append((i, f"Camera {i}"))
                cap.release()

    if not danh_sach:
        danh_sach = [(0, "Camera 0 (Mặc định)")]

    return danh_sach


class CameraWorker(QThread):
    khung_hinh_moi = pyqtSignal(bytes)      # phát khung hình JPEG mới cho main thread vẽ
    ket_qua_diem_danh = pyqtSignal(dict)    # phát kết quả trả về từ API điểm danh
    loi = pyqtSignal(str)                   # báo lỗi (mất camera, lỗi gọi API...)

    def __init__(self, ca_hoc_id: int, goi_api_diem_danh, camera_id: int = 0, khoang_cach_giay: float = 2.0):
        super().__init__()
        self.ca_hoc_id = ca_hoc_id
        self.goi_api_diem_danh = goi_api_diem_danh  # callback sang api_client.goi_diem_danh
        self.camera_id = camera_id                  # chỉ số (index) camera được chọn
        self.khoang_cach_giay = khoang_cach_giay    # không gọi API mỗi khung hình — quá tốn
        self._dang_chay = True

    def dung_lai(self):
        self._dang_chay = False

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            self.loi.emit(f"Không mở được webcam (Camera ID: {self.camera_id})")
            return

        lan_goi_api_gan_nhat = 0.0
        try:
            while self._dang_chay:
                ok, frame = cap.read()
                if not ok:
                    self.loi.emit("Mất tín hiệu webcam")
                    break

                ok_encode, buffer = cv2.imencode(".jpg", frame)
                if ok_encode:
                    self.khung_hinh_moi.emit(buffer.tobytes())

                bay_gio = time.time()
                if ok_encode and bay_gio - lan_goi_api_gan_nhat >= self.khoang_cach_giay:
                    lan_goi_api_gan_nhat = bay_gio
                    base64_anh = base64.b64encode(buffer.tobytes()).decode("utf-8")
                    try:
                        ket_qua = self.goi_api_diem_danh(self.ca_hoc_id, base64_anh)
                        self.ket_qua_diem_danh.emit(ket_qua)
                    except Exception as e:
                        self.loi.emit(f"Lỗi gọi API điểm danh: {e}")

                self.msleep(30)  # ~30fps hiển thị — KHÔNG phải tốc độ gọi API
        finally:
            cap.release()


class FaceCaptureWorker(QThread):
    """Phát hình webcam liên tục để màn hình đăng ký lấy một frame hiện tại."""

    khung_hinh_moi = pyqtSignal(bytes)
    loi = pyqtSignal(str)

    def __init__(self, camera_id: int = 0):
        super().__init__()
        self.camera_id = camera_id
        self._dang_chay = True

    def dung_lai(self):
        self._dang_chay = False

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            self.loi.emit(f"Không mở được webcam (Camera ID: {self.camera_id})")
            return
        try:
            while self._dang_chay:
                ok, frame = cap.read()
                if not ok:
                    self.loi.emit("Mất tín hiệu webcam")
                    break
                ok_encode, buffer = cv2.imencode(".jpg", frame)
                if ok_encode:
                    self.khung_hinh_moi.emit(buffer.tobytes())
                self.msleep(30)
        finally:
            cap.release()


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QComboBox
    from PyQt6.QtGui import QPixmap

    print("Đang chạy thử nghiệm CameraWorker... (Bấm đóng cửa sổ để thoát)")
    app = QApplication(sys.argv)
    
    cua_so_test = QWidget()
    cua_so_test.setWindowTitle("Test Camera Worker Feed (Hỗ trợ nhiều camera)")
    layout_test = QVBoxLayout(cua_so_test)

    cameras = lay_danh_sach_camera()
    layout_test.addWidget(QLabel("Chọn Camera để kiểm tra:"))
    combo_cam = QComboBox()
    for idx, ten in cameras:
        combo_cam.addItem(f"[{idx}] {ten}", idx)
    layout_test.addWidget(combo_cam)

    label_view = QLabel("Đang mở webcam...")
    label_view.setMinimumSize(640, 480)
    layout_test.addWidget(label_view)

    worker_hien_tai = [None]

    def khoi_dong_worker(cam_id):
        if worker_hien_tai[0]:
            worker_hien_tai[0].dung_lai()
            worker_hien_tai[0].wait()

        def mock_api(ca_hoc_id, frame_b64):
            return {"ket_qua": []}

        w = CameraWorker(ca_hoc_id=1, goi_api_diem_danh=mock_api, camera_id=cam_id)

        def on_frame(jpeg_bytes):
            pixmap = QPixmap()
            pixmap.loadFromData(jpeg_bytes)
            label_view.setPixmap(pixmap)

        w.khung_hinh_moi.connect(on_frame)
        w.loi.connect(lambda msg: print(f"Lỗi: {msg}"))
        w.start()
        worker_hien_tai[0] = w

    combo_cam.currentIndexChanged.connect(lambda: khoi_dong_worker(combo_cam.currentData()))
    khoi_dong_worker(combo_cam.currentData() if combo_cam.currentData() is not None else 0)

    cua_so_test.show()
    ret = app.exec()
    if worker_hien_tai[0]:
        worker_hien_tai[0].dung_lai()
        worker_hien_tai[0].wait()
    sys.exit(ret)