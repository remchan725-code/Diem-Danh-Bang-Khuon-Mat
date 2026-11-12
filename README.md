# Diem-Danh-Bang-Khuon-Mat
Hệ thống điểm danh bằng khuôn mặt tránh gian lận sinh trắc học

Dự án NCKH Khoa CNTT&TT HVQLGD
- Nguyễn Hồng Nam
- Nguyễn Minh Đức

## Cấu trúc dự án

```text
FaceID-Client/       Ứng dụng PyQt trên máy điểm danh
FaceID-Backend/      FastAPI và AI service InsightFace
FaceID-Database/     Schema PostgreSQL và Docker Compose
docs/                Hướng dẫn chạy, Supabase và kiểm thử
```

AI service được đặt trong `FaceID-Backend/ai_service/`, nhưng vẫn chạy process
riêng ở cổng 8001 để giữ nguyên giao tiếp hiện tại với FastAPI ở cổng 8000.

## Chạy client trên Linux

PyQt6 cần thư viện XCB của hệ thống để mở cửa sổ:

```bash
sudo apt install libxcb-cursor0
```

Sau đó cài dependency Python và chạy Client:

```bash
python -m pip install -r requirements.txt
python FaceID-Client/main_window.py
```

## Python 3.12+

Xem [hướng dẫn cài đặt, chạy và kiểm thử](docs/testing_instruction.md) để cấu hình
PostgreSQL, AI service, Backend API và Client trên local/LAN/cloud.
