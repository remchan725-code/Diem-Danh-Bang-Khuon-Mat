# Báo cáo tiến độ dự án NCKH — Ngày 19/11/2026

Em chào Cô ạ!
Em thay mặt nhóm xin phép báo cáo tiến độ dự án NCKH đợt này (từ sau lần báo cáo ngày 14/11 đến 19/11) ạ:

## Về những thứ nhóm đã làm được trong mấy ngày qua

1. **Hoàn thiện các Endpoint chính trên Backend FastAPI và kết nối AI Core (InsightFace):**
   - Nhóm đã tách và hoàn thiện luồng xử lý giữa Backend FastAPI (cổng 8000) và dịch vụ AI Core chạy mô hình InsightFace buffalo_l (ưu tiên GPU CUDA, tự động chuyển CPU khi cần, cổng 8001).
   - **Đăng ký & quản lý hồ sơ sinh viên bằng nhiều ảnh:** Thay vì lấy 1 ảnh đơn lẻ, API đăng ký và cập nhật khuôn mặt hiện yêu cầu tải lên từ **2 đến 5 ảnh** cho mỗi sinh viên. AI Core sẽ kiểm tra chất lượng (mỗi ảnh bắt buộc chỉ chứa đúng 1 khuôn mặt, độ tin cậy phát hiện >= 0.9), sau đó lấy trung bình và chuẩn hóa các vector 512 chiều thành template duy nhất, lưu kèm bản mã hóa đối xứng Fernet và thông tin phiên bản model (vector_version). Ngoài ra đã thêm API xóa hồ sơ có điều kiện (chặn xóa vật lý nếu sinh viên đã có lịch sử điểm danh hoặc nhật ký xác thực để bảo toàn dữ liệu đối soát).
   - **Tối ưu API điểm danh:** Hỗ trợ nhận diện nhiều khuôn mặt trong cùng 1 khung hình bằng truy vấn gộp (tránh truy vấn lặp), chỉ đối chiếu sinh viên thuộc đúng lớp của ca học hiện tại và tự động ghi nhật ký xác thực.

2. **Nâng cấp Schema CSDL và bổ sung luồng điểm danh 2 lượt (Đầu giờ / Cuối giờ) có Giảng viên xác nhận:**
   - Mở rộng bảng CaHoc để hỗ trợ phân loại hình thức (tại lớp / trực tuyến) và buổi học bù (lịch gốc / học bù liên kết với ca gốc).
   - Bổ sung 2 bảng mới là DotDiemDanh và HangChoDiemDanh, đồng thời thêm 2 mốc dau_gio / cuoi_gio trong LichSuDiemDanh.
   - Thay vì AI nhận diện xong ghi thẳng kết quả chính thức, quy trình mới là: **Giảng viên mở lượt (đầu giờ hoặc cuối giờ) → Camera quét và đưa sinh viên hợp lệ vào hàng chờ (có ràng buộc chống trùng) → Giảng viên xem lại và bấm xác nhận/đóng lượt** thì hệ thống mới chốt vào LichSuDiemDanh.

3. **Hoàn thiện ứng dụng máy quét (FaceID-Client bằng PyQt6) và tách rõ vai trò:**
   - Gỡ bỏ hoàn toàn phần dữ liệu giả lập (mock) trước đây để kết nối trực tiếp với Backend API thật (hỗ trợ cấu hình chạy local, mạng LAN hoặc cloud).
   - Chuyển chức năng đăng ký sinh viên khỏi ứng dụng máy quét để máy quét tại phòng học chỉ tập trung vào nghiệp vụ điểm danh (chọn lớp/ca, chọn lượt đầu/cuối giờ, mở lượt, quét camera, xem hàng chờ, xác nhận lượt và xem tổng kết).
   - Xây dựng xong bộ khung lõi điểm danh offline cục bộ bằng SQLite + InsightFace + mã hóa Fernet (đã qua 6/6 bài unit test) làm nền tảng cho phương án dự phòng khi mất mạng sau này.

4. **Xây dựng Website quản trị (FaceID-Administration) và điều chỉnh phương án triển khai thực tế hơn:**
   - Trước đây ở báo cáo 14/11 Website quản trị mới ở mức kế hoạch và dự kiến tự host + mở port tại nhà. Trong tuần qua nhóm đã hoàn thiện bộ giao diện Web quản trị (React + TypeScript + Tailwind CSS) kết nối trực tiếp tới Supabase và gọi API sang FastAPI, gồm đầy đủ các màn hình: Tổng quan, Lớp học, Ca học, Sinh viên, Đăng ký khuôn mặt 2–5 ảnh (chụp trực tiếp qua webcam hoặc chọn file), Điểm danh, Nhật ký xác thực, Nhật ký quản trị, Phân công giảng viên và Phân quyền.
   - **Bảo mật & phân quyền (RLS trên Supabase):** Bổ sung 4 bảng quản trị (NguoiDungHeThong, PhanCongGiangVien, CauHinhQuyenGiangVien, NhatKyQuanTri) với 3 nhóm quyền (khách, giảng viên, quản trị viên). Giảng viên chỉ thấy lớp được phân công, mặc định chỉ xem và chỉ được sửa điểm danh/dời ca khi admin bật quyền (mọi thao tác sửa bắt buộc nhập lý do và ghi log). Đặc biệt, nhóm đã khóa quyền đọc các cột vector sinh trắc học từ trình duyệt (REVOKE SELECT) và chỉ cho Web đọc qua View an toàn (v_sinh_vien_an_toan).
   - **Thay đổi phương án host gọn nhẹ hơn:** Thay vì tự host web và mở port mạng nhà, Web quản trị được cấu hình sẵn để đưa lên Vercel (HTTPS, ổn định); Database nằm trên Supabase Cloud; còn riêng Backend AI Core vẫn đặt trên máy trạm có GPU ở nhà và nối ra ngoài qua Cloudflare Tunnel. Nhóm cũng làm sẵn tính năng cho phép tài khoản quản trị (dev_admin) cập nhật nhanh đường link Tunnel mới ngay trên giao diện web (không phải sửa code hay deploy lại mỗi khi tắt/bật máy trạm). Các kiểm tra build/lint và 19/19 unit test phía Web hiện đều đạt.

## Về những phần chưa làm được / Đang tiếp tục hoàn thiện

- **Chưa chạy kiểm thử tích hợp tổng thể (E2E) và đo benchmark độ trễ:** Hiện nhóm mới kiểm tra từng phần riêng lẻ bằng unit test, chưa chạy thử xuyên suốt toàn bộ quy trình (từ Web đăng ký ảnh → FastAPI + AI Core → Supabase → máy quét PyQt mở lượt/nhận diện/chốt hàng chờ) trên môi trường CSDL thật để đo độ trễ thực tế.
- **Xác thực quyền (JWT) ở phía FastAPI:** Web quản trị đã gửi kèm token đăng nhập của Supabase khi gọi sang Backend, nhưng phía FastAPI mới mở CORS và xử lý lỗi cơ bản, chưa hoàn thiện bước xác minh chữ ký JWT (JWKS) để chặn request trái phép gọi trực tiếp vào API.
- **Chống giả mạo sinh trắc học (Liveness Detection):** CSDL đã có sẵn trường lưu điểm sống (diem_song), nhưng AI Core hiện mới dừng ở nhận diện và trích xuất vector khuôn mặt, chưa tích hợp mô hình kiểm tra người thật (chống đưa ảnh/video qua điện thoại).
- **Chế độ điểm danh offline:** Lõi lưu trữ SQLite cục bộ đã viết xong nhưng chưa ghép vào giao diện máy quét và chưa làm API đồng bộ ngược lên server khi có mạng lại.

## Dự kiến kế hoạch tuần tới

1. Chạy migration cập nhật các bảng mới lên môi trường Supabase thử nghiệm và tiến hành kiểm thử tích hợp xuyên suốt toàn bộ luồng (Web đăng ký 2–5 ảnh → Client quét điểm danh đầu/cuối giờ → xác nhận lượt), đồng thời đo benchmark tốc độ nhận diện thực tế.
2. Xử lý các trường hợp biên phía Backend (bắt chuẩn trạng thái sinh viên đã có trong hàng chờ, tránh xung đột khi vừa nhận diện vừa đóng lượt) và bổ sung xác thực JWT từ Supabase cho FastAPI.
3. Nghiên cứu tích hợp bước kiểm tra người thật (Liveness / Anti-spoofing) vào AI Core.

## Vấn đề còn vướng mắc & xin ý kiến Cô

1. Với cơ chế điểm danh **2 lượt (đầu giờ và cuối giờ)**, nhóm đang phân vân về quy tắc chốt trạng thái điểm danh tổng của ca học: nếu một sinh viên chỉ có mặt 1 trong 2 lượt (ví dụ có đầu giờ nhưng vắng cuối giờ, hoặc chỉ có cuối giờ) thì nên tính là trễ, vắng hay ghi nhận riêng theo từng mốc để giảng viên tự quyết định ạ?
2. Về bài toán dữ liệu thử nghiệm như lần trước nhóm có nêu: ngoài ảnh các thành viên trong nhóm, để đánh giá ngưỡng nhận diện (cosine distance) và đo độ trễ với quy mô một lớp học (~40–60 sinh viên), Cô thấy nhóm nên dùng thêm bộ dữ liệu khuôn mặt công khai (như LFW) hay nên nhờ các bạn cùng lớp chụp mẫu thử nghiệm thực tế ạ?

Trên đây là báo cáo tiến độ đợt này của nhóm em. Rất mong nhận được góp ý và định hướng thêm của Cô ạ.
Nhân dịp ngày Nhà giáo Việt Nam 20/11 sắp tới, nhóm em xin kính chúc Cô luôn mạnh khỏe, hạnh phúc và gặt hái thật nhiều thành công trong sự nghiệp giảng dạy cũng như nghiên cứu ạ!
