# Kế hoạch sau buổi báo cáo tiến độ ngày 19/11/2026

## 1. Gợi ý / Yêu cầu / Hướng dẫn của giảng viên hướng dẫn

- **Tách dự án thành 2 phần/pha độc lập: hệ thống điểm danh trước, nhận dạng khuôn mặt nối vào sau `[28:44 - 31:51]`:**
  > `[Transcript thô từ audio ghi âm cuộc họp]` "...bạn phải chú ý là chúng ta sẽ có ờ có thể tách thành hai cái phần. Một là cái phần hệ thống điểm danh. Cái hệ thống điểm danh này thì có thể là không phụ thuộc tới ờ phần nhận dạng khuôn mặt đâu. Mà các cái phần này thì các bạn cũng cần làm gì là các bạn cần phải phải ờ cô lấy giả sử nhá là cái app của các bạn. Đấy mình mình hiện nay mình đang có hai cái sản phẩm nhưng mà nhớ là cái phần nhận dạng khuôn mặt thì cái đấy nó sẽ giống như là một cái phần tích hợp thêm. Ờ và các em sẽ sử dụng những cái mã nguồn mở hoặc là những cái model đã được huấn luyện. Và bây giờ mình sẽ huấn luyện thêm với dữ liệu ở sinh viên ở học viện mình. Thì cái đấy nó sẽ là một cái pha sau. Các bạn sẽ làm sau. Còn bây giờ ấy các bạn cần giúp cô cái việc là gì ạ? Các bạn phải xây dựng một cái hệ thống điểm danh. Ờ hệ thống điểm danh từ việc là gì ạ? lên lịch này, lên lịch rồi sắp xếp lên lịch để học sinh viên học lớp gì, ở đâu, giáo viên là cái gì và có những thông tin quản lý sinh viên. Ờ cái thứ hai là khi điểm danh ấy thì vẫn là cái phần mềm, cái ứng dụng cái app mà bạn đang làm để cho điểm danh. Nhưng thay vì bây giờ mình chưa tạm thời mình chưa chưa chưa điểm danh bằng khuôn mặt vội mà bây giờ là gì ạ? Các bạn sẽ gắn với mỗi một sinh viên là một cái mã đúng không? Bây giờ chúng ta cứ coi đấy là mã mã sinh viên đấy. Thì mỗi một bạn nó sẽ là một một mã riêng và chúng ta sẽ sử dụng luôn ờ cái ờ cái mã đấy để làm cái mã điểm danh. Đấy. Thì ví dụ như em có cái mã này sinh viên này có họ tên có thì các bạn chỉ cần nhập mã điểm danh ờ sau đó thì hệ thống nó sẽ làm sao nhỉ? nó sẽ vào cái hệ thống điểm danh của các em. Đấy thì cái theo cô là mình sẽ là cần làm theo hai cái pha như vậy. Như vậy là cái pha đầu tiên ấy là mình sẽ phát triển cái ứng dụng điểm danh bằng có thể đơn giản là chúng ta chỉ nhập gì ạ? Nhập thông tin mã sinh viên ờ hoặc là thông qua một cái cách thức nào đó nhá bạn. Các bạn có thể nh là có mã này. Đấy thì cô nghĩ là cái là cái dễ nhất bằng con số bằng hoặc bằng tên nhưng tốt nhất là nên dùng mã để sau này mình đồng bộ với cái khuôn mặt và với ờ cái thông tin sau này của sinh viên. Đấy và em sẽ thử với điểm danh cho vài lớp để mình chạy chạy cái hệ thống này nó ngon lành đi. Còn khi nào mà mình xong được cái phần ờ xong được cái cái phần mà ừ điểm danh bằng khuôn mặt ấy thì mình sẽ làm gì? Mình sẽ tích hợp để thay vì là sinh viên nhập mã sinh viên của mình thì khi đó các bạn ấy sử dụng gì ạ? Khuôn mặt đúng không ạ? Ừ cái này đã được mình training cái mod đấy rồi nên là các bạn ấy sử dụng khuôn mặt thì cái từ khuôn mặt đấy nó sẽ ra mã sinh viên..."

- **Xác nhận của giảng viên trước khi chốt kết quả `[31:47 - 31:58]`:** Cô đồng ý với cơ chế cần có bước giảng viên xác nhận trước khi kết quả điểm danh được chốt chính thức vào hệ thống.

- **Quản lý thời khóa biểu, nhiều lớp, nhiều ca học & quy mô demo `[32:21 - 33:12, 34:12 - 35:07]`:**
  - Cần thiết kế đầy đủ thời khóa biểu/lịch học cho từng lớp, từng ca học để sinh viên điểm danh vào đúng ca; phải giải quyết tốt bài toán **nhiều lớp, nhiều ca học** trong CSDL.
  - Mô hình ưu việt nhất là ưu tiên điểm danh **tại từng phòng, từng ca học**; tuy nhiên trong phạm vi đề tài chỉ cần dùng **1 thiết bị để demo**.
  - Trước mỗi ca học, ca học và danh sách sinh viên phải có sẵn trong CSDL; đầu giờ giảng viên chọn và mở ca học đó, sau đó sinh viên lần lượt đứng trước camera (hoặc nhập mã SV ở Pha 1) để điểm danh.

- **Các chức năng ưu tiên của Hệ thống điểm danh cốt lõi (Pha 1) `[35:22 - 37:16]`:**
  1. **Tài khoản và phân quyền:** Gồm 3 nhóm người dùng: `Admin` (quản trị hệ thống), `Giảng viên`, và *(tùy chọn/option)* `Sinh viên` để sinh viên có thể đăng nhập tự kiểm tra xem mình đã điểm danh thành công hay chưa.
  2. **Quản lý lớp học:** Tạo lớp học, quản lý danh sách sinh viên học lớp đó, và phân công giảng viên giảng dạy lớp đó.
  3. **Quản lý ca học:** Phải có đầy đủ **ngày, giờ (thời gian học), địa điểm (phòng học)** và **thời gian mở/đóng điểm danh**.
  4. **Ghi nhận, xem và điều chỉnh kết quả điểm danh:** Lưu lượt điểm danh; xem danh sách kết quả và cho phép giảng viên chỉnh sửa kết quả **kèm lý do** và lưu vào **nhật ký thay đổi**.
  5. **Thống kê & xuất báo cáo:** Thống kê kết quả điểm danh **theo buổi, theo sinh viên, theo lớp** và hỗ trợ **xuất file CSV hoặc Excel**.

- **Yêu cầu đối với phần Nhận dạng khuôn mặt (Pha 2) `[33:18 - 34:12, 37:22 - 38:52]`:**
  - **Ưu tiên độ chính xác trước độ trễ:** Quan trọng nhất đầu tiên là **nhận diện đúng người** (đúng mã sinh viên của từng bạn). Với người lạ/không có trong CSDL phải **báo lỗi / từ chối** để tránh nhận nhầm và phục vụ chống giả mạo.
  - **Thu thập và gắn nhãn dữ liệu sinh viên Học viện:** Tận dụng model có sẵn và đưa dữ liệu sinh viên của Học viện vào (có thể thu thập bằng **ảnh thẻ 3×4, 4×6** tải lên hệ thống — Cô lưu ý nhiều hệ thống dùng ảnh thẻ nhận diện khá tốt — hoặc **đến lớp chụp trực tiếp mỗi bạn vài kiểu ảnh**). Khi thu thập phải **gắn nhãn chuẩn** kèm bảng thông tin đầy đủ: **Họ tên, Mã sinh viên, Lớp, Khóa**.
  - **Phản hồi rõ ràng trên ứng dụng máy quét:** Bổ sung đầy đủ thông báo trạng thái cho người dùng khi quét, ví dụ: *Điểm danh thành công*, *Không xác nhận được (người lạ)*, hoặc *Ảnh bị lỗi / mờ / chưa rõ*.

---

## 2. Đối chiếu yêu cầu của Cô với hiện trạng dự án (tính đến 25/11/2026)

1. **Tách Pha 1 điểm danh bằng mã sinh viên trước khi nối AI khuôn mặt:**
   - *Hiện trạng:* Chưa có luồng nhập `ma_sv` để điểm danh; Client PyQt và Backend FastAPI hiện mới thiết kế theo luồng gửi frame ảnh qua AI Core.
   - *Cần bổ sung / điều chỉnh:* Thêm luồng và API điểm danh bằng `ma_sv`, tái sử dụng chung quy trình *mở ca → hàng chờ → giảng viên xác nhận → chốt kết quả* để sau này nối khuôn mặt vào chỉ cần thay mỗi bước đầu vào.

2. **Xác nhận của giảng viên trước khi chốt điểm danh:**
   - *Hiện trạng:* Đã có thiết kế bảng `DotDiemDanh`, `HangChoDiemDanh` và các API mở lượt / xem hàng chờ / xác nhận trên Backend + Client (chưa test thật).
   - *Cần bổ sung / điều chỉnh:* Đồng bộ các bảng mới lên Supabase, cập nhật giao diện xác nhận trên Web quản trị nếu cần, và chạy kiểm thử thực tế toàn luồng.

3. **Quản lý lớp học, phân công giảng viên, danh sách sinh viên, nhiều lớp – nhiều ca:**
   - *Hiện trạng:* Web quản trị (`FaceID-Administration`) đã có quản lý `LopHoc`, `SinhVien`, `PhanCongGiangVien`, `CaHoc`.
   - *Cần bổ sung / điều chỉnh:* Rà soát quan hệ Sinh viên – Lớp học. Hiện bảng `SinhVien` chỉ có 1 cột `lop_id` (mỗi SV thuộc 1 lớp hành chính); cần chốt rõ xem đề tài chỉ quản lý theo lớp hành chính hay cần thêm bảng trung gian (`LopHoc_SinhVien`) để 1 SV học được nhiều lớp học phần khác nhau.

4. **Quản lý ca học (ngày, giờ, phòng học, thời gian mở/đóng điểm danh):**
   - *Hiện trạng:* `CaHoc` hiện mới có `ngay`, `gio_bat_dau`, `gio_ket_thuc`, `hinh_thuc`, `loai_ca` — **chưa có cột phòng học/địa điểm**. Bảng `DotDiemDanh` có `mo_luc`, `dong_luc` nhưng chưa đồng bộ hiển thị lên Web quản trị (`SessionsView`).
   - *Cần bổ sung / điều chỉnh:* Bổ sung cột địa điểm/phòng học (`phong_hoc`) vào `CaHoc`; đồng bộ đầy đủ các trường mới của `CaHoc` và thời gian mở/đóng lượt điểm danh lên giao diện Web quản trị.

5. **Tài khoản & phân quyền (Admin, Giảng viên và option Sinh viên):**
   - *Hiện trạng:* Đã có 3 nhóm `dev_admin`, `giang_vien`, `guest` kèm phân quyền RLS trên Supabase.
   - *Cần bổ sung / điều chỉnh:* Cân nhắc bổ sung vai trò `sinh_vien` (liên kết tài khoản với `SinhVien`, thiết lập RLS chỉ cho phép đọc lịch sử điểm danh của chính mình để SV tự kiểm tra đã điểm danh thành công hay chưa).

6. **Xem và điều chỉnh kết quả điểm danh có lý do + nhật ký thay đổi:**
   - *Hiện trạng:* Đã có sẵn trên Web quản trị (`AttendanceView`, RPC `rpc_dieu_chinh_diem_danh`, lưu vết tự động vào `NhatKyQuanTri`).
   - *Cần bổ sung / điều chỉnh:* Chạy kiểm thử thực tế với dữ liệu nhiều lớp/nhiều ca ở Pha 1 để chắc chắn vận hành trơn tru.

7. **Thốndg kê kết quả (theo buổi, theo sinh viên, theo lớp) và xuất file CSV / Excel:**
   - *Hiện trạng:* **Chưa có** (Web quản trị hiện mới có lọc cơ bản trên màn hình `AttendanceView`, chưa có tổng hợp thống kê và chưa có nút xuất file).
   - *Cần bổ sung / điều chỉnh:* Bổ sung phần thống kê chuyên cần theo đủ 3 góc nhìn (theo buổi/ca học, theo từng sinh viên, theo từng lớp) và chức năng xuất báo cáo ra file **CSV (UTF-8 BOM)** / **Excel (.xlsx)**.

8. **Dữ liệu khuôn mặt sinh viên Học viện có gắn nhãn + hỗ trợ ảnh thẻ hoặc chụp nhiều ảnh:**
   - *Hiện trạng:* Bảng `SinhVien` chưa có cột `khoa` (niên khóa); Backend đăng ký khuôn mặt hiện đang bắt buộc tải lên từ 2–5 ảnh/lần.
   - *Cần bổ sung / điều chỉnh:* Bổ sung cột `khoa` cho `SinhVien` để bảng thông tin gắn nhãn đủ 4 trường (`họ tên`, `mã SV`, `lớp`, `khóa`); điều chỉnh API đăng ký linh hoạt để nhận được cả **1 ảnh thẻ 3×4 / 4×6 đạt chuẩn** lẫn **2–5 ảnh chụp nhiều góc**; lên kế hoạch thu thập ảnh thực tế từ sinh viên trong Học viện.

9. **Độ chính xác nhận diện, từ chối người lạ và phản hồi ảnh mờ/lỗi trên máy quét:**
   - *Hiện trạng:* Backend FastAPI và AI Core mới dừng ở mã nguồn (chưa chạy test thật); giao diện máy quét hiện mới chỉ hiện tên khi khớp hoặc chữ `"Không xác định"`.
   - *Cần bổ sung / điều chỉnh:* Ở Pha 2 ưu tiên kiểm thử độ chính xác nhận diện đúng người và bắt chặt người lạ trước khi tối ưu độ trễ; bổ sung kiểm tra chất lượng ảnh đầu vào (mờ, lỗi, không rõ mặt) và hiển thị các thông báo phản hồi cụ thể trên màn hình máy quét (*Điểm danh thành công*, *Không xác nhận được*, *Ảnh bị lỗi / mờ / chưa rõ*).

---

## 3. Kế hoạch triển khai chi tiết sau buổi báo cáo

### Pha 1: Hoàn thiện và chạy thông suốt Hệ thống điểm danh cốt lõi (không phụ thuộc nhận dạng khuôn mặt)

> **Mục tiêu đầu ra Pha 1:** Toàn bộ hệ thống điểm danh (CSDL Supabase + Web quản trị + Backend/App điểm danh bằng **mã sinh viên**) chạy thông suốt, test thực tế hoàn chỉnh trên **2–3 lớp học và nhiều ca học** với 1 thiết bị demo, có đủ thống kê và xuất CSV/Excel.

1. **Bước 1.1 — Chuẩn hóa lại CSDL (Supabase / PostgreSQL):**
   - Bổ sung các trường còn thiếu theo góp ý của Cô:
     - Bảng `CaHoc`: thêm `phong_hoc` (địa điểm phòng học).
     - Bảng `SinhVien`: thêm `khoa` (niên khóa/khóa học) để sẵn sàng cho việc quản lý và gắn nhãn dữ liệu ở Pha 2.
   - Đồng bộ migration lên Supabase cho đầy đủ cả nhánh bảng điểm danh (`DotDiemDanh`, `HangChoDiemDanh`, các cột `hinh_thuc`, `loai_ca`, `dau_gio`, `cuoi_gio`) và nhánh bảng quản trị/RLS của Web Admin.
   - Chốt thiết kế cho bài toán **nhiều lớp, nhiều ca học**: đảm bảo lịch học (thời khóa biểu) của nhiều lớp không chồng chéo sai lệch; xác định rõ sinh viên gắn theo lớp hành chính (`SinhVien.lop_id`) hay cần thêm bảng trung gian đăng ký lớp học phần (`DangKyLopHoc`).

2. **Bước 1.2 — Hoàn thiện đầy đủ các chức năng cốt lõi trên Web quản trị (`FaceID-Administration`):**
   - **Quản lý lớp học & thời khóa biểu ca học:** Cập nhật `SessionsView` và `types` để tạo/sửa/hiển thị đầy đủ `ngày`, `giờ bắt đầu/kết thúc`, `phòng học`, `hình thức`, và quản lý mở/đóng lượt điểm danh kèm thời gian mở/đóng.
   - **Thống kê & Xuất báo cáo (BẮT BUỘC bổ sung):**
     - Xây dựng góc nhìn thống kê theo 3 tiêu chí: **theo buổi/ca học**, **theo sinh viên** (tổng số buổi có mặt/trễ/vắng, tỷ lệ chuyên cần), và **theo lớp học**.
     - Thêm chức năng xuất file **CSV (UTF-8 BOM để mở Excel không lỗi tiếng Việt)** và/hoặc **Excel (.xlsx)**.
   - **Xem & điều chỉnh điểm danh có nhật ký:** Rà soát và chạy test thật luồng giảng viên xem danh sách, chỉnh sửa kết quả kèm lý do và kiểm tra log trong `NhatKyQuanTri`.
   - **Phân quyền tài khoản (Option Sinh viên):** Giữ vững 2 vai trò `dev_admin` và `giang_vien`; bổ sung thêm vai trò `sinh_vien` (kèm RLS chỉ cho xem lịch sử điểm danh của chính mình) để đáp ứng trọn vẹn gợi ý của Cô.

3. **Bước 1.3 — Xây dựng luồng điểm danh bằng Mã sinh viên (thay tạm bước quét mặt):**
   - Thiết kế API điểm danh tách riêng tầng định danh (`ma_sv`) khỏi tầng nghiệp vụ điểm danh:
     - **Pha 1:** Ứng dụng điểm danh (`FaceID-Client` hoặc màn hình điểm danh chuyên dụng) cho phép giảng viên chọn lớp → chọn ca → mở lượt điểm danh → sinh viên nhập `ma_sv` để gửi lên hệ thống → kiểm tra sinh viên có thuộc lớp của ca học đó không → đưa vào `HangChoDiemDanh` → giảng viên xem danh sách hàng chờ và bấm **Xác nhận & đóng lượt** để chốt vào `LichSuDiemDanh`.
     - Khi chuyển sang **Pha 2**, chỉ cần thay bước "nhập `ma_sv`" bằng "AI Core nhận diện khuôn mặt → trả về `ma_sv` + `ho_ten`" mà **không phải sửa lại luồng nghiệp vụ điểm danh**.
   - Sửa các lỗi biên đã ghi nhận trước đó ở Backend FastAPI (`ON CONFLICT DO NOTHING` khi trùng hàng chờ, xử lý xung đột khi vừa điểm danh vừa đóng lượt, bổ sung xác thực JWT Supabase cho API).

4. **Bước 1.4 — Chạy thử nghiệm thực tế Pha 1 trên vài lớp mẫu:**
   - Tạo dữ liệu giả lập đầy đủ cho **2–3 lớp học**, mỗi lớp có thời khóa biểu **nhiều ca học**, phân công giảng viên và danh sách sinh viên rõ ràng.
   - Chạy thử trọn vẹn quy trình trên 1 máy demo: tạo lớp/ca → mở ca điểm danh → nhập mã sinh viên điểm danh (thử cả trường hợp nhập đúng, nhập trùng, nhập mã không thuộc lớp, nhập khi ca chưa mở) → giảng viên xác nhận → điều chỉnh có lý do → xem thống kê → xuất file CSV/Excel → (nếu làm option SV) đăng nhập tài khoản sinh viên để tự tra cứu.

---

### Pha 2: Thu thập dữ liệu, Tích hợp & Kiểm chứng Module Nhận dạng khuôn mặt

> **Mục tiêu đầu ra Pha 2:** Tích hợp trơn tru AI nhận diện khuôn mặt vào đúng chỗ nhập mã sinh viên của Pha 1; chứng minh được độ chính xác **đúng người**, **bắt/từ chối người lạ**, và **phản hồi lỗi ảnh rõ ràng** trên dữ liệu thực tế của sinh viên Học viện.

1. **Bước 2.1 — Thu thập & chuẩn hóa dữ liệu sinh viên Học viện:**
   - Lập bảng dữ liệu gắn nhãn đầy đủ: `ma_sv`, `ho_ten`, `lop`, `khoa`.
   - Thu thập ảnh khuôn mặt sinh viên (kết hợp **ảnh thẻ 3×4 / 4×6** có sẵn hoặc **đến lớp chụp trực tiếp mỗi bạn 2–5 ảnh** ở điều kiện ánh sáng, góc mặt tự nhiên).
   - Điều chỉnh API đăng ký khuôn mặt sao cho linh hoạt: hỗ trợ tốt cả trường hợp tải **1 ảnh thẻ rõ nét** lẫn **2–5 ảnh chụp nhiều góc** (trung bình chuẩn hóa vector 512-D).

2. **Bước 2.2 — Dựng chạy thực tế & ghép nối AI Core (`InsightFace buffalo_l`) vào hệ thống Pha 1:**
   - Chạy thật 2 service `FaceID-Backend` (cổng 8000) và `ai_service` (cổng 8001) kết nối tới Supabase.
   - Kiểm thử luồng đăng ký khuôn mặt từ Web quản trị (lưu vector 512-D + bản mã hóa Fernet, đảm bảo trình duyệt không bao giờ đọc được vector thô).
   - Nối camera trên `FaceID-Client` để thay bước nhập `ma_sv`: khuôn mặt → trích xuất vector → so khớp trong đúng danh sách sinh viên của lớp → trả về `ma_sv` + `ho_ten` → đẩy vào đúng hàng chờ xác nhận của Pha 1.

3. **Bước 2.3 — Kiểm thử độ chính xác nhận diện & Chống giả mạo (Ưu tiên đúng người trước độ trễ):**
   - Thực nghiệm kiểm tra 3 nhóm tình huống bắt buộc:
     1. **Đúng người (True Positive):** Mỗi sinh viên đứng trước camera phải nhận đúng `ma_sv` và `ho_ten` của mình.
     2. **Người lạ / Sinh viên lớp khác (Reject Unknown):** Phải báo lỗi / từ chối, tuyệt đối không nhận nhầm sang người khác trong lớp.
     3. **Ảnh kém chất lượng:** Đánh giá độ mờ (độ nét ảnh), độ tin cậy phát hiện mặt (`det_score`), ngược sáng hoặc nhiều mặt lỗi.
   - Tinh chỉnh ngưỡng `NGUONG_KHOP` (hiện đang để tạm `0.4`) dựa trên kết quả thực nghiệm, đo độ trễ trung bình, sau đó nghiên cứu tích hợp thêm mô hình kiểm tra thực thể sống (**Liveness Detection / Anti-spoofing**) để điền cột `diem_song` trong `NhatKyXacThuc`.

4. **Bước 2.4 — Hoàn thiện phản hồi trực quan trên ứng dụng máy quét (`FaceID-Client`):**
   - Hiển thị rõ ràng từng trạng thái phản hồi theo đúng góp ý của Cô:
     - **Điểm danh thành công** (kèm họ tên, mã SV, trạng thái đã vào hàng chờ / đã điểm danh trước đó).
     - **Không xác nhận được** (người lạ không có trong CSDL hoặc không thuộc lớp hiện tại).
     - **Ảnh bị lỗi / mờ / chưa rõ** (hướng dẫn sinh viên đứng thẳng, đủ sáng, giữ yên mặt).

5. **Bước 2.5 — Demo tổng thể cuối cùng:**
   - Chạy diễn tập toàn bộ quy trình trên 1 thiết bị demo với nhiều lớp, nhiều ca học, dữ liệu khuôn mặt sinh viên thật, xác nhận giảng viên, xem nhật ký xác thực/quản trị và xuất file báo cáo CSV/Excel.

---

## 4. Một số điểm nhóm cần thống nhất nhanh trước khi bắt tay làm Pha 1

1. **Cấu trúc Lớp – Sinh viên:** Trong phạm vi đề tài, mỗi sinh viên chỉ thuộc 1 lớp cố định (`SinhVien.lop_id`) hay cần hỗ trợ 1 sinh viên tham gia nhiều lớp học phần khác nhau (thêm bảng trung gian `LopHoc_SinhVien`)?
2. **Mức độ ưu tiên của vai trò `Sinh viên`:** Làm luôn trong Pha 1 (một màn hình đơn giản để SV đăng nhập xem lịch sử điểm danh của mình) hay chốt xong toàn bộ luồng Admin + Giảng viên + Xuất CSV/Excel rồi mới bổ sung?
3. **Kênh nhập mã sinh viên ở Pha 1:** Cho nhập mã SV trực tiếp trên ứng dụng desktop `FaceID-Client` (để sau này bật camera đè lên cùng 1 app) hay hỗ trợ nhập cả trên Web quản trị?
