Hướng dẫn chạy thử nghiệm
Cách 1: Test riêng Webcam (Không cần Backend / Database)
Bạn có thể mở file 

Face-ID/camera_worker.py
 và bấm Run, hoặc mở PowerShell:

powershell
.\.venv\Scripts\python.exe .\Face-ID\camera_worker.py
(Cửa sổ webcam sẽ hiện lên để bạn kiểm tra luồng camera).

Cách 2: Chạy đầy đủ hệ thống (Giao diện + Backend)
Hệ thống này được thiết kế theo kiến trúc Client - Server, bạn cần mở 2 terminal:

Terminal 1 — Khởi động Backend API:

powershell
cd Face-ID
..\.venv\Scripts\python.exe main.py
(Server sẽ khởi động tại http://127.0.0.1:8000. Bạn có thể truy cập http://127.0.0.1:8000/docs trên trình duyệt để kiểm tra API).

Terminal 2 — Khởi động Giao diện PyQt:

powershell
cd Face-ID
..\.venv\Scripts\python.exe main_window.py
NOTE

Để đăng ký sinh viên và lưu lịch sử điểm danh đầy đủ, Backend cần kết nối tới PostgreSQL (port 5433, user postgres, password 12345 theo cấu hình trong 

Face-ID/db.py
). Nếu bạn dùng thông tin tài khoản khác, hãy cập nhật lại file này hoặc đặt biến môi trường tương ứng.