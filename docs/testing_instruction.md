# Hướng dẫn cài đặt, chạy và kiểm thử

Tài liệu này là hướng dẫn duy nhất để chạy Frontend, Backend, AI Core và kiểm tra
luồng điểm danh. Các lệnh bên dưới dùng PowerShell trên Windows và được chạy từ
thư mục gốc của repository, trừ khi có ghi chú khác.

## 1. Chuẩn bị

- Python 3.12+ và các thư viện trong `requirements.txt`.
- PostgreSQL có cài extension pgvector.
- Webcam nếu muốn kiểm tra điểm danh trực tiếp.

Cài thư viện vào môi trường ảo của project:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### PostgreSQL local bằng Docker Compose

Khởi động PostgreSQL/pgvector:

```powershell
docker compose -f .\Face-ID-Backend\docker-compose.yml up -d
```

Compose hiện ánh xạ cổng máy `5434` tới cổng PostgreSQL `5432` trong container,
với database `attendance_db`, user `postgres`, password `postgres`. Đây là thông
tin phát triển local; không dùng các thông tin này cho môi trường thật.
Schema được tạo tự động khi khởi tạo volume mới. Nếu volume đã tồn tại, việc sửa
file schema không tự chạy lại trên volume đó.

Khi dùng PostgreSQL từ Compose, cấu hình Backend theo các giá trị trên. Nếu đã có
PostgreSQL cài trực tiếp, dùng đúng host, port, database và thông tin đăng nhập
của instance đó.

## 2. Chạy đầy đủ ứng dụng local

Mỗi dịch vụ chạy trong một cửa sổ PowerShell riêng. Biến môi trường chỉ có hiệu
lực trong cửa sổ nơi biến được đặt.

### Terminal 1 — AI Core

```powershell
$env:AI_CORE_HOST="127.0.0.1"
$env:AI_CORE_PORT="8001"
.\.venv\Scripts\python.exe .\AI-Core\insightface_run.py
```

### Terminal 2 — Backend

Ví dụ này dùng PostgreSQL Docker Compose ở trên:

```powershell
$env:BACKEND_HOST="127.0.0.1"
$env:BACKEND_PORT="8000"
$env:AI_CORE_BASE_URL="http://127.0.0.1:8001"
$env:DB_HOST="127.0.0.1"
$env:DB_PORT="5434"
$env:DB_NAME="attendance_db"
$env:DB_USER="postgres"
$env:DB_PASSWORD="postgres"
.\.venv\Scripts\python.exe .\Face-ID-Backend\main.py
```

Backend API và tài liệu OpenAPI có tại `http://127.0.0.1:8000` và
`http://127.0.0.1:8000/docs`.

### Terminal 3 — Frontend

```powershell
$env:BACKEND_API_BASE_URL="http://127.0.0.1:8000"
$env:APP_DEBUG="true"
.\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```

Ứng dụng chính gọi dịch vụ thật, không tự chuyển sang dữ liệu giả khi dịch vụ lỗi.
Nếu Backend không kết nối được, kiểm tra Backend, PostgreSQL và
`BACKEND_API_BASE_URL`.

## 3. Cấu hình dịch vụ

| Biến môi trường | Đọc bởi | Mặc định | Chức năng |
|---|---|---|---|
| `BACKEND_API_BASE_URL` | Frontend | `http://127.0.0.1:8000` | URL Backend API |
| `BACKEND_HOST` / `BACKEND_PORT` | Backend | `127.0.0.1` / `8000` | Host và cổng Backend lắng nghe |
| `AI_CORE_BASE_URL` | Backend | `http://127.0.0.1:8001` | URL AI Core API |
| `AI_CORE_HOST` / `AI_CORE_PORT` | AI Core | `0.0.0.0` / `8001` | Host và cổng AI Core lắng nghe |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Backend | Mặc định trong `Face-ID-Backend/db.py` | Kết nối PostgreSQL |
| `APP_DEBUG` | Frontend | `true` | Hiện/ẩn lựa chọn camera và công cụ phát triển |

Đặt các biến môi trường trước khi khởi động tiến trình tương ứng. Không ghi mật
khẩu database, khóa mã hóa hoặc thông tin xác thực vào mã nguồn hay Git.

## 4. Chạy các dịch vụ qua mạng LAN

Trên máy cung cấp AI Core, bind dịch vụ vào giao diện mạng:

```powershell
$env:AI_CORE_HOST="0.0.0.0"
$env:AI_CORE_PORT="8001"
.\.venv\Scripts\python.exe .\AI-Core\insightface_run.py
```

Trên máy Backend, dùng địa chỉ IP LAN của máy AI Core và cấu hình database có thể
truy cập từ Backend:

```powershell
$env:BACKEND_HOST="0.0.0.0"
$env:BACKEND_PORT="8000"
$env:AI_CORE_BASE_URL="http://<IP_AI_CORE>:8001"
$env:DB_HOST="<IP_POSTGRESQL>"
$env:DB_PORT="<PORT_POSTGRESQL>"
$env:DB_NAME="<TEN_DATABASE>"
$env:DB_USER="<DATABASE_USER>"
$env:DB_PASSWORD="<DATABASE_PASSWORD>"
.\.venv\Scripts\python.exe .\Face-ID-Backend\main.py
```

Trên máy chạy Frontend, trỏ tới IP LAN của Backend:

```powershell
$env:BACKEND_API_BASE_URL="http://<IP_BACKEND>:8000"
.\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```

`0.0.0.0` chỉ là địa chỉ bind trên máy chủ, không dùng làm URL để gọi dịch vụ.
Chỉ mở các cổng cần thiết trong firewall; không công khai AI Core hoặc PostgreSQL
trực tiếp ra Internet.

## 5. Dùng dịch vụ cloud

Đặt URL dịch vụ và thông tin database trong cấu hình môi trường/secret manager
của nơi triển khai. Frontend cần URL Backend HTTPS, Backend cần URL AI Core và
PostgreSQL có thể truy cập được.

Ví dụ URL:

- Frontend: `BACKEND_API_BASE_URL=https://<BACKEND_DOMAIN>`
- Backend: `AI_CORE_BASE_URL=https://<AI_CORE_DOMAIN>`

Chưa triển khai xác thực API, HTTPS termination hay cấu hình bảo vệ production
trong mã nguồn hiện tại. Cần hoàn thiện các biện pháp này trước khi đưa dịch vụ
lên Internet; không dùng trực tiếp cấu hình local làm cấu hình production.

## 6. Kiểm tra luồng chức năng

1. Mở `http://127.0.0.1:8000/docs` để xác nhận Backend khởi động.
2. Trong Frontend, tải danh sách lớp và ca học.
3. Đăng ký sinh viên bằng ảnh có một khuôn mặt rõ hoặc lấy ảnh từ webcam.
4. Bắt đầu ca, kiểm tra nhận diện và thông báo kết quả.
5. Kết thúc ca, kiểm tra danh sách điểm danh trong màn hình tổng kết.

Có thể kiểm tra webcam độc lập mà không gọi Backend:

```powershell
.\.venv\Scripts\python.exe .\Face-ID-Frontend\camera_worker.py
```

Các script mock/seed/E2E cũ đã được xóa. Hiện chưa có bộ kiểm thử tự động thay
thế; không chạy thử trên database có dữ liệu cần giữ. Khi bổ sung test tự động,
dùng database test riêng và pytest.

## 7. Chế độ Development

Mặc định `APP_DEBUG=true` để hiện lựa chọn camera. Ẩn công cụ này khi chạy giao diện:

```powershell
$env:APP_DEBUG="false"
.\.venv\Scripts\python.exe .\Face-ID-Frontend\main_window.py
```
