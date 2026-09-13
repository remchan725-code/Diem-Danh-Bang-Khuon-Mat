import time
import base64
import cv2
from PyQt6.QtCore import QThread, pyqtSignal
 
 
class CameraWorker(QThread):
    khung_hinh_moi = pyqtSignal(bytes)      # phát khung hình JPEG mới cho main thread vẽ
    ket_qua_diem_danh = pyqtSignal(dict)    # phát kết quả trả về từ API điểm danh
    loi = pyqtSignal(str)                   # báo lỗi (mất camera, lỗi gọi API...)
 
    def __init__(self, ca_hoc_id: int, goi_api_diem_danh, khoang_cach_giay: float = 2.0):
        super().__init__()
        self.ca_hoc_id = ca_hoc_id
        self.goi_api_diem_danh = goi_api_diem_danh  # callback sang api_client.goi_diem_danh
        self.khoang_cach_giay = khoang_cach_giay    # không gọi API mỗi khung hình — quá tốn
        self._dang_chay = True
 
    def dung_lai(self):
        self._dang_chay = False
 
    def run(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self.loi.emit("Không mở được webcam")
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


if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QLabel
    from PyQt6.QtGui import QPixmap

    print("Đang chạy thử nghiệm CameraWorker... (Bấm đóng cửa sổ để thoát)")
    app = QApplication(sys.argv)
    label = QLabel("Đang mở webcam...")
    label.setWindowTitle("Test Camera Worker Feed")
    label.resize(640, 480)
    label.show()

    def mock_api(ca_hoc_id, frame_b64):
        return {"ket_qua": []}

    worker = CameraWorker(ca_hoc_id=1, goi_api_diem_danh=mock_api)

    def on_frame(jpeg_bytes):
        pixmap = QPixmap()
        pixmap.loadFromData(jpeg_bytes)
        label.setPixmap(pixmap)

    worker.khung_hinh_moi.connect(on_frame)
    worker.loi.connect(lambda msg: print(f"Lỗi: {msg}"))
    worker.start()

    ret = app.exec()
    worker.dung_lai()
    worker.wait()
    sys.exit(ret)