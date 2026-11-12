# Hướng dẫn chạy thử nghiệm

## Cấu trúc thư mục

```
Diem-Danh-Bang-Khuon-Mat/
├── Face-ID-Backend/     <- FastAPI server, PostgreSQL, AI Core client
│   ├── main.py
│   ├── db.py
│   ├── ai_core_client.py
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

## Cấu hình gọi Backend và AI Core

Ứng dụng chính chỉ sử dụng dịch vụ thật. Khi không kết nối được, giao diện báo lỗi
thay vì tự chuyển sang dữ liệu giả lập. URL được cấu hình qua biến môi trường:

| Biến | Đọc bởi | Mặc định | Mục đích |
|---|---|---|---|
| `BACKEND_API_BASE_URL` | Frontend | `http://127.0.0.1:8000` | Địa chỉ Backend API |
| `BACKEND_HOST`, `BACKEND_PORT` | Backend | `127.0.0.1`, `8000` | Giao diện mạng và cổng Backend lắng nghe |
| `AI_CORE_BASE_URL` | Backend | `http://127.0.0.1:8001` | Địa chỉ AI Core API |
| `AI_CORE_HOST`, `AI_CORE_PORT` | AI Core | `0.0.0.0`, `8001` | Giao diện mạng và cổng AI Core lắng nghe |
| `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` | Backend | Cấu hình trong `Face-ID-Backend/db.py` | Thông tin kết nối PostgreSQL local/LAN/cloud |

Ví dụ PowerShell từ thư mục gốc (mỗi dịch vụ chạy trong terminal riêng):

```powershell
# Terminal Backend — chạy local trên cùng máy
$env:BACKEND_HOST="127.0.0.1"
$env:BACKEND_PORT="8000"
$env:AI_CORE_BASE_URL="http://127.0.0.1:8001"
$env:DB_HOST="127.0.0.1"
# Chạy Backend:
.\.venv\Scripts\python.exe .\Face-ID-Backend\main.py

# Terminal Frontend — trỏ tới Backend local
$env:BACKEND_API_BASE_URL="http://127.0.0.1:8000"
.\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```

Với LAN, đặt các giá trị trên máy chủ tương ứng và dùng IP LAN có thể truy cập:

```powershell
# Terminal AI Core trên máy 192.168.1.21
$env:AI_CORE_HOST="0.0.0.0"
$env:AI_CORE_PORT="8001"
.\.venv\Scripts\python.exe .\AI-Core\insightface_run.py

# Terminal Backend trên máy chủ Backend
$env:BACKEND_HOST="0.0.0.0"
$env:BACKEND_PORT="8000"
$env:AI_CORE_BASE_URL="http://192.168.1.21:8001"
.\.venv\Scripts\python.exe .\Face-ID-Backend\main.py

# Terminal Frontend trên máy trạm
$env:BACKEND_API_BASE_URL="http://192.168.1.20:8000"
.\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```

Với cloud, đặt các biến môi trường tương ứng trong môi trường triển khai; URL
client dùng domain HTTPS do nhóm triển khai cung cấp, ví dụ
`BACKEND_API_BASE_URL=https://backend.example.com` và
`AI_CORE_BASE_URL=https://ai.example.com`.

Backend cần truy cập được AI Core và PostgreSQL. `AI_CORE_BASE_URL` phải được đặt
trong môi trường chạy Backend; `BACKEND_API_BASE_URL` phải được đặt trong môi
trường chạy Frontend. Các biến `DB_*` được cấu hình trong môi trường Backend để
kết nối PostgreSQL. Không đưa thông tin xác thực hoặc khóa bí mật vào mã nguồn.
`0.0.0.0` chỉ dùng làm địa chỉ bind trên máy chủ, không dùng làm URL từ Frontend.
Khi triển khai Internet/cloud cần HTTPS, xác thực API và giới hạn firewall; các
cơ chế này chưa được triển khai trong bước hiện tại. Mock chỉ còn là công cụ
phát triển/kiểm thử, không tham gia luồng chạy của ứng dụng chính.

---

## Điều chỉnh môi trường Development / Production

Mặc định khi chạy là **DEBUG = True** (hiện hộp chọn camera, công cụ phát triển).

```powershell
# Sản phẩm cuối (ẩn hộp chọn camera):
$env:APP_DEBUG="false"; .\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py

# Môi trường Development (hiện đầy đủ công cụ):
$env:APP_DEBUG="true"; .\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```
