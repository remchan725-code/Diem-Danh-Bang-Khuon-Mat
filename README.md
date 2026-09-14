# Diem-Danh-Bang-Khuon-Mat
Hệ thống điểm danh bằng khuôn mặt tránh gian lận sinh trắc học,

## Chạy frontend trên Linux

PyQt6 cần thư viện XCB của hệ thống để mở cửa sổ trên máy Linux:

```bash
sudo apt install libxcb-cursor0
```

Sau đó cài dependency Python và chạy frontend:

```bash
python -m pip install -r requirements.txt
python Face-ID-Frontend/main_window.py
```

## Python 3.12+
