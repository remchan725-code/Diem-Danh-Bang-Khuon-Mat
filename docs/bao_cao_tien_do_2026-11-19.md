# Báo cáo tiến độ dự án NCKH — Ngày 19/11/2026

Em chào Cô ạ!
Em thay mặt nhóm xin phép báo cáo tiến độ dự án NCKH đợt này (từ sau lần báo cáo ngày 14/11 đến 19/11) ạ:

## 1. Những phần nhóm chắc chắn đã hoàn thành

1. **Hoàn thiện phần móng CSDL trên Supabase và chốt logic điểm danh mới (2 lượt có Giảng viên xác nhận):**
   - Nâng cấp cấu trúc CSDL so với đợt báo cáo trước: mở rộng bảng CaHoc để hỗ trợ phân loại hình thức (tại lớp / trực tuyến) và buổi học bù (lịch gốc / học bù liên kết với ca gốc); bổ sung 2 bảng mới là DotDiemDanh và HangChoDiemDanh, đồng thời thêm 2 mốc dau_gio / cuoi_gio trong LichSuDiemDanh.
   - Chốt lại quy trình nghiệp vụ điểm danh chặt chẽ hơn: thay vì AI nhận diện xong ghi thẳng kết quả chính thức, hệ thống sẽ chạy theo luồng **Giảng viên mở lượt (đầu giờ hoặc cuối giờ) → Camera quét và đẩy sinh viên hợp lệ vào hàng chờ (có ràng buộc chống trùng) → Giảng viên kiểm tra và bấm xác nhận/đóng lượt** thì hệ thống mới chốt chính thức vào LichSuDiemDanh.
   - **Bảo mật & phân quyền (RLS trên Supabase):** Bổ sung 4 bảng quản trị (NguoiDungHeThong, PhanCongGiangVien, CauHinhQuyenGiangVien, NhatKyQuanTri) với 3 nhóm quyền (khách, giảng viên, quản trị viên). Giảng viên chỉ xem được lớp được phân công, mặc định chỉ xem và chỉ được sửa điểm danh/dời ca khi quản trị viên bật quyền (mọi thao tác sửa bắt buộc nhập lý do và ghi log vào NhatKyQuanTri). Đặc biệt, nhóm đã khóa quyền đọc các cột vector sinh trắc học từ phía trình duyệt (REVOKE SELECT) và chỉ cho Web đọc qua View an toàn (v_sinh_vien_an_toan).

2. **Xây dựng Website quản trị (FaceID-Administration) và điều chỉnh phương án triển khai gọn nhẹ hơn:**
   - Trước đây ở báo cáo 14/11 Website quản trị mới ở mức kế hoạch và dự kiến tự host + mở port tại nhà. Trong mấy ngày qua nhóm đã hoàn thiện bộ giao diện Web quản trị (React + TypeScript + Tailwind CSS) kết nối trực tiếp tới Supabase, gồm đầy đủ các màn hình: Tổng quan, Lớp học, Ca học, Sinh viên, khung Đăng ký khuôn mặt 2–5 ảnh (chụp webcam hoặc chọn file, đã nối sẵn cấu trúc gọi sang FastAPI), Điểm danh, Nhật ký xác thực, Nhật ký quản trị, Phân công giảng viên và Phân quyền.
   - **Điều chỉnh phương án triển khai thực tế hơn:** Thay vì tự host web và mở port mạng nhà, Web quản trị được cấu hình sẵn để đưa lên Vercel (HTTPS, ổn định); Database đặt trên Supabase Cloud; còn riêng Backend AI Core vẫn đặt tại máy trạm có GPU ở nhà và nối ra ngoài qua Cloudflare Tunnel. Nhóm cũng làm sẵn tính năng cho phép tài khoản quản trị (dev_admin) cập nhật nhanh đường link Tunnel mới ngay trên giao diện web (không phải sửa code hay deploy lại mỗi khi tắt/bật máy trạm). Các kiểm tra build, lint và 19/19 unit test phía Web hiện đều đã đạt.

## 2. Những phần đã viết xong mã nguồn theo thiết kế nhưng CHƯA chạy kiểm thử thực tế

Do chưa dựng chạy kiểm thử đồng bộ được phần Backend và AI Core, nhóm xin báo cáo rõ các hạng mục dưới đây mới hoàn thành ở mức viết mã nguồn và giao diện, chưa thể khẳng định là đã vận hành ổn định:

1. **Backend FastAPI và các Endpoint AI Core (InsightFace):**
   - Nhóm đã viết xong mã nguồn cho các endpoint chính giữa FastAPI (cổng 8000) và dịch vụ AI Core dùng InsightFace buffalo_l (cổng 8001), bao gồm:
     - Đăng ký và cập nhật hồ sơ khuôn mặt bằng 2–5 ảnh (kiểm tra mỗi ảnh chỉ có đúng 1 khuôn mặt, độ tin cậy >= 0.9, lấy trung bình và chuẩn hóa vector 512 chiều thành template duy nhất, mã hóa đối xứng Fernet và lưu vector_version).
     - Xóa hồ sơ sinh viên có điều kiện (chặn xóa vật lý nếu sinh viên đã có lịch sử điểm danh hoặc nhật ký xác thực để giữ dữ liệu đối soát).
     - API điểm danh hỗ trợ nhiều khuôn mặt trong cùng 1 khung hình (truy vấn gộp theo đúng lớp của ca học, đưa kết quả vào hàng chờ và ghi nhật ký xác thực), cùng các API mở lượt, xem hàng chờ, xác nhận/đóng lượt và cấu hình CORS kết nối với Web quản trị.
   - **Tình trạng hiện tại:** Toàn bộ các endpoint này mới dừng ở mức hoàn thiện code, nhóm chưa chạy test thực tế với AI Core và Supabase nên chưa kiểm chứng được lỗi phát sinh lúc chạy thật và chưa đo được độ trễ.

2. **Ứng dụng máy quét (FaceID-Client bằng PyQt6):**
   - Nhóm đã gỡ bỏ phần dữ liệu giả lập (mock) cũ, tách bỏ chức năng đăng ký sinh viên khỏi máy quét (đẩy hẳn việc đăng ký sang Web quản trị) và cập nhật lại giao diện máy quét cho khớp với luồng điểm danh 2 lượt mới (chọn lớp/ca, chọn lượt đầu/cuối giờ, mở lượt, xem hàng chờ, xác nhận lượt, tổng kết).
   - Ngoài ra nhóm có viết trước bộ khung lõi điểm danh offline cục bộ bằng SQLite + InsightFace + mã hóa Fernet (đã qua 6/6 unit test mô phỏng).
   - **Tình trạng hiện tại:** Vì Backend FastAPI chưa chạy kiểm thử thật nên ứng dụng máy quét cũng mới dừng ở mức hoàn thiện mã nguồn/giao diện, chưa chạy thử xuyên suốt qua camera thật.

## 3. Những phần chưa triển khai / Đang còn thiếu

- **Xác thực quyền (JWT) ở phía FastAPI:** Web quản trị đã chuẩn bị bước gửi kèm token đăng nhập Supabase, nhưng phía FastAPI chưa viết bước kiểm tra chữ ký JWT (JWKS) để chặn request trái phép gọi trực tiếp vào API.
- **Chống giả mạo sinh trắc học (Liveness Detection):** CSDL đã có sẵn trường lưu điểm sống (diem_song), nhưng AI Core hiện mới có phần phát hiện và trích xuất vector khuôn mặt, chưa tích hợp mô hình kiểm tra người thật (chống ảnh/video giả).
- **Ghép nối chế độ điểm danh offline:** Khung lõi SQLite cục bộ mới dừng ở module độc lập, chưa ghép vào giao diện máy quét và chưa viết luồng đồng bộ ngược lên server khi có mạng lại.

## 4. Dự kiến kế hoạch tuần tới

1. **Ưu tiên trọng tâm:** Dựng chạy thực tế và kiểm thử toàn bộ các endpoint của Backend FastAPI và AI Core với CSDL Supabase thử nghiệm, sửa các lỗi phát sinh khi chạy thật và đo benchmark độ trễ nhận diện.
2. Kiểm thử xuyên suốt từ Web quản trị (đăng ký 2–5 ảnh) sang máy quét PyQt (mở lượt đầu/cuối giờ → quét khuôn mặt → hàng chờ → giảng viên xác nhận), đồng thời xử lý các trường hợp biên phía Backend (trùng sinh viên trong hàng chờ, xung đột khi vừa nhận diện vừa đóng lượt).
3. Bổ sung xác thực JWT từ Supabase cho FastAPI và bắt đầu nghiên cứu ghép bước kiểm tra người thật (Liveness / Anti-spoofing) vào AI Core.

## 5. Vấn đề còn vướng mắc & xin ý kiến Cô

1. Chuẩn bị bước vào giai đoạn chạy test thực tế Backend FastAPI + AI Core tuần tới, nhóm vẫn còn băn khoăn về dữ liệu đầu vào: ngoài ảnh các thành viên trong nhóm, để đánh giá ngưỡng nhận diện (cosine distance) và đo độ trễ với quy mô một lớp học (~40–60 sinh viên), Cô thấy nhóm nên dùng thêm bộ dữ liệu khuôn mặt công khai (như LFW) hay nên nhờ các bạn cùng lớp chụp mẫu thử nghiệm thực tế ạ?


Trên đây là báo cáo tiến độ thực tế đợt này của nhóm em. Rất mong nhận được góp ý và định hướng thêm của Cô ạ.
Nhân dịp ngày Nhà giáo Việt Nam 20/11 sắp tới, nhóm em xin kính chúc Cô luôn mạnh khỏe, hạnh phúc và gặt hái thật nhiều thành công trong sự nghiệp giảng dạy cũng như nghiên cứu ạ!
