# Hướng dẫn chạy thử nghiệm

## Cấu trúc thư mục

```
Diem-Danh-Bang-Khuon-Mat/
├── Face-ID-Backend/     <- FastAPI server, PostgreSQL, AI mock
│   ├── main.py
│   ├── db.py
│   ├── ai_core_mock.py
│   ├── crypto_utils.py
│   └── ...
├── Face-ID-Frontend/    <- Giao diện PyQt6 (file này đang ở đây)
│   ├── main_window.py   <- Entry point của giao diện
│   ├── camera_worker.py <- Luồng webcam (QThread)
│   └── api_client.py    <- Gọi API tới Backend
└── AI-Core/             <- InsightFace AI service (tùy chọn)
```

---

## Cách 1: Test riêng Webcam (Không cần Backend / Database)

Bạn có thể bấm Run trực tiếp file `camera_worker.py`, hoặc mở PowerShell từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe .\Face-ID-Frontend\camera_worker.py
```

Cửa sổ webcam sẽ hiện lên với dropdown chọn camera. Hoạt động hoàn toàn độc lập.

---

## Cách 2: Chạy đầy đủ hệ thống (Giao diện + Backend)

Hệ thống theo kiến trúc Client–Server, cần mở **3 terminal** khi dùng InsightFace thật:

### Terminal 0 — Khởi động AI Core thật

AI Core dùng InsightFace để đổi ảnh thành vector 512 chiều:

```powershell
cd AI-Core
..\.venv\Scripts\python.exe insightface_run.py
```

AI Core mặc định chạy tại `http://127.0.0.1:8001`. Backend dùng biến môi trường
`AI_CORE_BASE_URL` để gọi địa chỉ này.

### Terminal 1 — Khởi động Backend API

```powershell
cd Face-ID-Backend
..\..\.venv\Scripts\python.exe main.py
```

Hoặc từ thư mục gốc:
```powershell
.\.venv\Scripts\python.exe .\Face-ID-Backend\main.py
```

Server khởi động tại `http://127.0.0.1:8000`. Truy cập `http://127.0.0.1:8000/docs` để kiểm tra API.

### Terminal 2 — Khởi động Giao diện PyQt

```powershell
cd Face-ID-Frontend
..\..\.venv\Scripts\python.exe main_window.py
```

Hoặc từ thư mục gốc:
```powershell
.\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```

> **Lưu ý:** Backend cần kết nối tới PostgreSQL (port `5433`, user `postgres`, password `12345` theo cấu hình trong `Face-ID-Backend/db.py`).

### Đăng ký khuôn mặt mới

Trong giao diện, bấm **Đăng ký khuôn mặt mới**, nhập mã sinh viên, họ tên và lớp.
Bạn có thể chọn **Thêm ảnh từ máy tính** hoặc bật camera. Khi camera đang chạy,
frame hiện tại được dùng làm ảnh đăng ký khi bấm **Lưu vector và đăng ký**.
Ảnh nên chỉ có một khuôn mặt, chính diện và đủ sáng. Backend sẽ gọi AI Core,
lưu vector 512 chiều vào bảng `SinhVien`, sau đó dùng vector này để so khớp khi điểm danh.

---

## Cách 3: Chạy Giao diện ở Chế độ Test (Không cần Backend)

Dành cho khi bạn muốn chạy toàn bộ giao diện PyQt mà **chưa bật PostgreSQL hoặc FastAPI**.

### Cách 3a — Tự động chuyển khi mất kết nối

Chạy `main_window.py` bình thường. Khi app không thấy Backend, hộp thoại sẽ hỏi:
> *"Bạn có muốn BẬT 'Chế độ Test (Mock Backend)' để chạy thử giao diện và camera ngay bây giờ không?"*

Bấm **Yes** để tự động nạp dữ liệu lớp & ca học giả lập.

### Cách 3b — Bật qua ô tích trên giao diện

Trong mục **"⚙️ Cấu hình Nhà phát triển"**, tích vào ô:
> ☑️ **Bật Test Mode (Chạy giả lập - Không cần Backend)**

### Cách 3c — Bật trực tiếp từ dòng lệnh

```powershell
# Từ thư mục gốc:
$env:APP_TEST_MODE="true"; .\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```

---

## Điều chỉnh môi trường Development / Production

Mặc định khi chạy là **DEBUG = True** (hiện hộp chọn camera, công cụ phát triển).

```powershell
# Sản phẩm cuối (ẩn hộp chọn camera):
$env:APP_DEBUG="false"; .\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py

# Môi trường Development (hiện đầy đủ công cụ):
$env:APP_DEBUG="true"; .\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```
