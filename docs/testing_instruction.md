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

### Lõi điểm danh local (bản kỹ thuật đầu tiên)

`Face-ID-Frontend/local_attendance_core.py` có phần lõi chạy InsightFace ngay trên
client: trích embedding từ frame BGR, so khớp cosine với cache sinh viên, mã hóa
vector trong SQLite local và lưu kết quả `co_mat` chờ đồng bộ. Lõi chọn CUDA nếu
ONNX Runtime hỗ trợ, nếu không thì dùng CPU; model pack `buffalo_l` được tải khi
khởi tạo lần đầu nếu máy chưa có.

Đặt một khóa Fernet cố định cho thiết bị trước khi dùng store. Ví dụ tạo khóa một
lần rồi lưu an toàn; không tạo lại mỗi lần chạy:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
$env:LOCAL_FERNET_KEY = "<dán khóa vừa tạo vào đây>"
```

Đường dẫn SQLite mặc định nằm trong `%LOCALAPPDATA%\DiemDanhBangKhuonMat\`.
Không dùng khóa hoặc database local này làm secret dùng chung cho nhiều thiết bị.

**Giới hạn hiện tại:** lõi đã có API Python nhưng chưa được nối vào màn hình
`main_window.py`; chưa có endpoint an toàn để tải roster/vector và ca học từ
Backend, cũng chưa có luồng đồng bộ lượt pending lên server. Backend hiện chưa
ghi `vector_version` khi đăng ký sinh viên. Vì vậy chưa thể dùng lõi này để thay
luồng điểm danh chính hoặc khẳng định chế độ offline hoàn chỉnh. Chỉ đưa vector
vào cache khi lấy từ nguồn đồng bộ đã xác thực và có `vector_version` đúng
`insightface_buffalo_l_v1`. Đây là nhận diện khuôn mặt, chưa có liveness/chống giả
mạo; ngưỡng 0.4 cần được kiểm thử với dữ liệu thật trước khi dùng vận hành.

### Dùng Supabase thay cho PostgreSQL local

Supabase thay thế **dịch vụ PostgreSQL**, không thay thế FastAPI hoặc AI Core.
Trong cấu hình hướng dẫn này, Frontend, Backend và AI Core vẫn chạy trên máy
của bạn; Backend kết nối qua Internet tới PostgreSQL trên Supabase. Không cần
khởi động Docker Compose khi dùng Supabase. Giữ file Compose để phát triển local
hoặc kiểm thử khi không muốn dùng database cloud.

1. Tạo project Supabase, bật pgvector và chạy schema theo
   [hướng dẫn Supabase](SUPABASE_POSTGRESQL.md). Lấy host, port, database, user
   và password từ **Supabase Dashboard → Connect**; dùng đúng thông tin được
   dashboard cấp, không tự đoán. Nếu mạng không hỗ trợ IPv6, chọn phương thức
   pooler phù hợp theo hướng dẫn Supabase.
2. Trong cửa sổ PowerShell dùng để chạy Backend, đặt cấu hình Supabase. Thay
   các giá trị mẫu bằng thông tin từ dashboard:

   ```powershell
   $env:DB_HOST = "<host từ Supabase>"
   $env:DB_PORT = "<port từ Supabase>"
   $env:DB_NAME = "<database từ Supabase>"
   $env:DB_USER = "<user từ Supabase>"
   $env:DB_PASSWORD = "<database password>"
   $env:PGSSLMODE = "require"
   ```

   Đặt `FERNET_KEY` thành khóa Fernet cố định và lưu an toàn; không tạo khóa mới
   mỗi lần chạy vì dữ liệu đã mã hóa cần đúng khóa cũ để giải mã. Cách tạo và
   bảo quản khóa được hướng dẫn trong tài liệu Supabase.
3. Khởi động AI Core như bình thường, rồi chạy Backend trong **chính cửa sổ đã
   đặt các biến trên**:

   ```powershell
   .\.venv\Scripts\python.exe .\Face-ID-Backend\main.py
   ```

4. Kiểm tra Backend kết nối được database bằng endpoint liệt kê lớp như mục 5,
   sau đó chạy Frontend như mục 2. Nếu Backend vẫn đang trỏ tới Compose, kiểm
   tra lại `DB_*` trong cửa sổ Backend. Việc đổi cấu hình không chuyển dữ liệu
   giữa PostgreSQL local và Supabase.

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

Ví dụ này dùng PostgreSQL Docker Compose ở trên. Nếu dùng Supabase, hãy đặt
`DB_*` và `PGSSLMODE` theo mục **Dùng Supabase thay cho PostgreSQL local** thay
cho các biến `DB_*` bên dưới.

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
| `PGSSLMODE` | Backend/libpq | Tùy môi trường | Dùng `require` khi kết nối Supabase |
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
