# Hướng dẫn chạy thử nghiệm — Backend

## Khởi động Backend API

Chạy từ **thư mục gốc** của project:
```powershell
.\.venv\Scripts\python.exe .\Face-ID-Backend\main.py
```

Hoặc `cd` vào thư mục Backend:
```powershell
cd Face-ID-Backend
..\..\.venv\Scripts\python.exe main.py
```

Server sẽ khởi động tại `http://127.0.0.1:8000`. Truy cập `http://127.0.0.1:8000/docs` để kiểm tra API.

> **Lưu ý:** Backend cần kết nối tới PostgreSQL (port `5433`, user `postgres`, password `12345` theo cấu hình trong `Face-ID-Backend/db.py`). Nếu bạn dùng thông tin khác, hãy cập nhật file `db.py` hoặc đặt biến môi trường tương ứng.

---

## Chạy E2E test Backend

```powershell
.\.venv\Scripts\python.exe .\Face-ID-Backend\test_backend_e2e.py
```

---

## Giao diện (Frontend)

Giao diện PyQt nằm riêng ở `Face-ID-Frontend/`. Xem hướng dẫn tại `Face-ID-Frontend/testing_instruction.md`.