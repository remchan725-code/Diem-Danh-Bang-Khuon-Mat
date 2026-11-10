# Hướng dẫn kết nối app với PostgreSQL trên Supabase

Tài liệu này hướng dẫn theo code hiện tại của dự án, ưu tiên phương án dễ thử và ít thay đổi:

> **FastAPI vẫn chạy trên máy của bạn; chỉ database PostgreSQL chuyển lên Supabase.**

Frontend PyQt tiếp tục gọi FastAPI. Frontend **không** kết nối trực tiếp với Supabase/PostgreSQL.

```text
PyQt frontend ──HTTP──> FastAPI backend trên máy bạn ──PostgreSQL──> Supabase
                                  │
                                  └──> AI Core (nếu đang dùng service AI thật)
```

Sau khi thử nghiệm ổn, có thể deploy FastAPI lên một máy chủ riêng. Đó là bước độc lập; Supabase cung cấp PostgreSQL, không tự host ứng dụng FastAPI hoặc AI Core.

---

## 1. Trước khi bắt đầu

Bạn cần:

- Tài khoản Supabase và một project Supabase.
- Python và các thư viện trong `requirements.txt` đã cài.
- Backend hiện chạy được với PostgreSQL local hoặc ít nhất có thể khởi động.
- Thông tin kết nối database lấy từ **Supabase Dashboard → Connect**.

Các file liên quan trong dự án:

- `Face-ID-Backend/db.py`: tạo kết nối PostgreSQL bằng `psycopg2`, đọc các biến `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`; đăng ký kiểu dữ liệu pgvector.
- `Face-ID-Backend/schema_postgres.sql`: tạo extension `vector`, các bảng và index.
- `Face-ID-Backend/main.py`: FastAPI dùng kết nối từ `db.py`.
- `Face-ID-Frontend/api_client.py`: frontend đang gọi `http://localhost:8000`.
- `Face-ID-Backend/docker-compose.yml`: PostgreSQL local để phát triển; không cần chạy database này khi backend đã trỏ tới Supabase.

### Kiểm tra cấu hình hiện tại

Giá trị mặc định trong `db.py` không khớp hoàn toàn với `docker-compose.yml`:

| Cấu hình | `db.py` mặc định | Docker Compose |
|---|---:|---:|
| Database | `postgres` | `attendance_db` |
| Password | `12345` | `postgres` |
| Port máy host | `5433` | `5434` |

Khi cấu hình Supabase, hãy đặt đầy đủ biến môi trường bên dưới để không vô tình kết nối nhầm database local.

---

## 2. Tạo project Supabase

1. Tạo project mới trong Supabase Dashboard.
2. Chọn region phù hợp với nơi đặt backend và người dùng. Nếu backend hiện ở máy cá nhân tại Việt Nam, chọn region gần Việt Nam nếu có.
3. Tạo database password mạnh và lưu trong password manager. Đây là mật khẩu database, không phải mật khẩu tài khoản Supabase.
4. Chờ trạng thái project sẵn sàng.
5. Mở **Connect** trong dashboard và ghi nhận thông tin host, port, database, user và loại kết nối.

### Chọn kiểu kết nối

Trong project, bấm **Connect** ở đầu trang để xem thông tin kết nối. Chọn theo mạng nơi chạy FastAPI:

- **Direct connection**: dùng khi mạng của máy backend hỗ trợ IPv6, hoặc project có IPv4 add-on. Username thường là `postgres`, port thường là `5432`.
- **Session pooler**: dùng nếu máy backend chỉ có IPv4. Đây là lựa chọn phù hợp để thử trên nhiều mạng gia đình/trường học. Sao chép host, port và username chính xác từ dashboard; username thường có dạng `postgres.<project-ref>` và port thường là `5432`.
- Không chọn **Transaction pooler** cho hướng dẫn này; hãy dùng Direct hoặc Session pooler và sao chép thông tin từ dashboard, không tự đoán host/user/port.

Không đưa mật khẩu database, connection string, `FERNET_KEY` hoặc service-role key vào Git, ảnh chụp màn hình, tài liệu công khai hay mã nguồn.

---

## 3. Bật pgvector và tạo schema

Ứng dụng cần pgvector vì `SinhVien.vector_tho` có kiểu `VECTOR(512)` và truy vấn nhận diện dùng toán tử cosine distance `<=>`.

1. Trong thanh điều hướng project, mở **Database → Extensions**, tìm `vector` và bật extension.
2. Mở **SQL Editor → New query**.
3. Mở file `Face-ID-Backend/schema_postgres.sql` trong VS Code, sao chép toàn bộ nội dung vào query và bấm **Run**.
4. Nếu dashboard hiện cảnh báo hỏi có bật RLS cùng lúc không, chọn **Run without RLS**. Nút bật tự động đã gây lỗi `relation "LopHoc" does not exist` với schema này vì tên bảng được PostgreSQL chuyển thành chữ thường.
5. Bật RLS thủ công bằng tên bảng chữ thường trong **SQL Editor → New query**:

```sql
ALTER TABLE public.lophoc ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sinhvien ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cahoc ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lichsudiemdanh ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nhatkyxacthuc ENABLE ROW LEVEL SECURITY;
```

Các bảng không có policy sẽ không truy cập được qua API với vai trò `anon`/`authenticated`. Backend hiện dùng kết nối PostgreSQL trực tiếp bằng tài khoản đặc quyền; không mở quyền Data API công khai để xử lý lỗi RLS.
6. Chạy các câu lệnh kiểm tra:

```sql
SELECT extname
FROM pg_extension
WHERE extname = 'vector';
```

Kết quả cần có một dòng `vector`. Tiếp theo, kiểm tra các bảng:

```sql
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'lophoc',
    'sinhvien',
    'cahoc',
    'lichsudiemdanh',
    'nhatkyxacthuc'
  )
ORDER BY table_name;
```

PostgreSQL chuyển tên bảng không đặt trong dấu ngoặc kép thành chữ thường. Vì vậy, ví dụ `CREATE TABLE LopHoc` tạo bảng tên `lophoc`; code Python cũng tham chiếu `LopHoc` không đặt ngoặc kép nên vẫn hoạt động.

> Nếu câu kiểm tra bảng không liệt kê đủ bảng, xem tab **Results** của lần chạy schema để tìm lỗi đầu tiên. Không tiếp tục chạy app cho tới khi schema tạo thành công.

### Schema tạo những dữ liệu nào?

File schema tạo cấu trúc bảng và index, nhưng không tự tạo lớp học, ca học hay sinh viên. Backend hiện có API liệt kê lớp/ca và đăng ký sinh viên, nhưng chưa có API quản trị để tạo lớp hoặc ca.

Có thể tạo dữ liệu demo trong SQL Editor:

```sql
INSERT INTO LopHoc (ten_lop)
VALUES ('NCKH Demo')
RETURNING id;
```

Ghi lại `id` trả về rồi tạo ca học (thay `1` bằng ID thật):

```sql
INSERT INTO CaHoc (lop_id, ngay, gio_bat_dau, gio_ket_thuc)
VALUES (1, CURRENT_DATE, TIME '08:00', TIME '09:00')
RETURNING id;
```

Các câu lệnh trên chỉ tạo dữ liệu demo. Tránh chèn một sinh viên giả nếu muốn thử nhận diện thật, vì luồng đăng ký cần embedding tương thích được tạo bởi AI Core.

---

## 4. Cấu hình backend trên Windows

Mở **PowerShell mới** tại thư mục gốc của repository. Thay các giá trị trong dấu ngoặc nhọn bằng thông tin từ **Supabase → Connect**:

```powershell
$env:DB_HOST = "<host từ Supabase>"
$env:DB_NAME = "<database từ Supabase>"
$env:DB_USER = "<user từ Supabase>"
$env:DB_PASSWORD = "<database password>"
$env:DB_PORT = "<port từ Supabase>"
```

Đặt SSL bắt buộc bằng biến môi trường libpq `PGSSLMODE`; `psycopg2` nhận biến này mà không cần sửa `db.py`:

```powershell
$env:PGSSLMODE = "require"
```

`require` mã hóa kết nối nhưng không xác minh danh tính máy chủ. Với triển khai production, nên cấu hình xác minh chứng chỉ theo hướng dẫn SSL của Supabase.

Backend hiện đọc `FERNET_KEY` để mã hóa vector sinh trắc học. Đặt một khóa cố định cho môi trường này trước khi chạy:

```powershell
$env:FERNET_KEY = "<Fernet key cố định, lưu an toàn>"
```

Có thể tạo khóa Fernet bằng Python sau khi dependencies đã cài:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Lưu khóa vào password manager hoặc secret manager, không lưu vào repository. **Không tạo khóa mới mỗi lần khởi động**: dữ liệu đã mã hóa bằng khóa cũ sẽ không giải mã được bằng khóa mới.

Khởi động backend trong chính cửa sổ PowerShell đã đặt biến:

```powershell
.\.venv\Scripts\python.exe .\Face-ID-Backend\main.py
```

Nếu môi trường ảo của bạn nằm ở vị trí khác, dùng đường dẫn Python thực tế của môi trường đó. Biến `$env:...` chỉ có hiệu lực trong cửa sổ PowerShell hiện tại; mở cửa sổ mới thì phải đặt lại.

---

## 5. Kiểm tra kết nối từng lớp

### Bước 1: kiểm tra backend khởi động

Mở:

```text
http://127.0.0.1:8000/docs
```

Nếu trang docs mở được, FastAPI đã chạy. Điều này **chưa chứng minh** database kết nối thành công vì kết nối được mở khi endpoint cần truy vấn database.

### Bước 2: gọi endpoint đọc database

Thử endpoint liệt kê lớp:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/lop-hoc
```

Kết quả kỳ vọng là danh sách lớp (có thể rỗng nếu chưa tạo lớp). Thử tiếp:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/ca-hoc?lop_id=1"
```

Thay `1` bằng ID lớp thật. Nếu endpoint trả về JSON thay vì lỗi database, kết nối FastAPI → Supabase hoạt động.

### Bước 3: thử giao diện

Khi FastAPI chạy tại `localhost:8000`, mở ứng dụng PyQt như bình thường. Frontend hiện gọi backend ở `http://localhost:8000`, nên **chưa cần sửa frontend** nếu backend vẫn chạy trên cùng máy.

### Bước 4: thử đăng ký/điểm danh

Các bước này còn phụ thuộc vào AI Core:

- Đăng ký sinh viên cần AI Core trả embedding.
- Điểm danh cần AI Core xử lý frame và database có sinh viên đã đăng ký.
- E2E test có thể ghi dữ liệu vào database đang cấu hình. Chỉ chạy trên project Supabase thử nghiệm hoặc sau khi đã hiểu dữ liệu mà test tạo ra.

---

## 6. Chuyển dữ liệu từ PostgreSQL local

Tạo schema mới trên Supabase **không tự chuyển dữ liệu** đang có từ PostgreSQL local.

### Trước khi chuyển

1. Xác định đúng database nguồn và port đang dùng. Cấu hình local có thể khác giữa `db.py` và Docker Compose.
2. Tạo project Supabase thử nghiệm hoặc backup trước khi thao tác.
3. Không chạy restore vào database có dữ liệu cần giữ nếu chưa kiểm tra nội dung backup.

### Chuyển bằng `pg_dump` / `pg_restore`

Cần cài PostgreSQL command-line tools tương thích, gồm `pg_dump` và `pg_restore`. Các lệnh dưới đây dùng placeholder; thay bằng thông tin thật. Chạy lệnh sẽ hỏi password, không ghi mật khẩu trực tiếp vào lệnh:

```powershell
pg_dump -h <host-nguon> -p <port-nguon> -U <user-nguon> -d <database-nguon> -Fc -f .\attendance-backup.dump
```

Kiểm tra file backup được tạo, sau đó restore vào **project Supabase đích còn trống**:

```powershell
pg_restore -h <host-supabase> -p <port-supabase> -U <user-supabase> -d <database-supabase> --no-owner --no-acl .\attendance-backup.dump
```

- Với nguồn Supabase dùng pooler, điền chính xác host, port và user của pooler.
- Backup toàn bộ có thể chứa extension, owner hoặc đối tượng không được phép restore bằng user Supabase. Nếu restore báo lỗi, dừng lại và đọc lỗi cụ thể; không xóa dữ liệu đích để thử lại một cách mù quáng.
- Nếu chọn restore toàn bộ backup, đừng chạy trước một bản schema trùng lặp lên project đích.
- Nếu chỉ muốn chuyển cấu trúc rồi tạo dữ liệu demo, tạo schema theo mục 3 là đủ; không cần dump/restore.

Sau restore, chạy truy vấn kiểm tra extension, bảng và số dòng, rồi mới trỏ backend vào database đích. Giữ database cũ làm bản rollback cho tới khi xác nhận dữ liệu và app hoạt động.

---

## 7. Khi nào cần deploy FastAPI?

### Chỉ thử Supabase từ máy phát triển

Không cần deploy thêm gì. Luồng là:

```text
PyQt trên máy bạn → FastAPI trên máy bạn → Supabase
```

Frontend và backend cùng máy nên `localhost:8000` vẫn đúng.

### Muốn người khác hoặc máy khác dùng app qua Internet

Khi đó cần deploy FastAPI lên máy chủ/dịch vụ hosting riêng:

1. Cấu hình biến database và `FERNET_KEY` bằng secrets của nền tảng deploy.
2. Cập nhật backend để bind ra interface phù hợp (hiện `main.py` chạy với host `127.0.0.1`).
3. Cấu hình HTTPS, firewall/network access và giới hạn nguồn truy cập database nếu nền tảng hỗ trợ.
4. Đặt URL backend thành cấu hình có thể thay đổi. Hiện `Face-ID-Frontend/api_client.py` hard-code `BASE_URL = "http://localhost:8000"`; máy client khác sẽ gọi chính máy của người dùng, không phải server.
5. Nếu AI Core chạy riêng, bảo đảm backend production truy cập được AI Core qua URL cấu hình phù hợp.
6. Chỉ mở các API cần thiết; thêm xác thực/phân quyền và giới hạn truy cập trước khi đưa dữ liệu thật lên Internet.

Đây là một giai đoạn triển khai riêng. Chỉ có database Supabase thì các máy client khác vẫn chưa thể gọi được FastAPI trên máy bạn.

---

## 8. Bảo mật và dữ liệu sinh trắc học

- Không đặt database password, connection URI, `FERNET_KEY` hoặc Supabase service-role key trong frontend, repository, file commit lên Git, hay log.
- PyQt chỉ gọi FastAPI; không nhúng thông tin đăng nhập database vào ứng dụng client.
- Các bảng được bật RLS nhưng chưa có policy sẽ bị từ chối khi truy cập qua Data API với vai trò `anon`/`authenticated`. Backend hiện dùng kết nối PostgreSQL trực tiếp bằng tài khoản đặc quyền; không mở Data API công khai để xử lý lỗi kết nối. Nếu sau này dùng Data API, cần tạo policy giới hạn quyền trước khi cấp quyền truy cập.
- Schema hiện có `vector_tho VECTOR(512)` để truy vấn pgvector và `vector_khuon_mat BYTEA` để lưu vector mã hóa. Vector thô vẫn tồn tại để so khớp; mã hóa cột kia không đồng nghĩa toàn bộ dữ liệu vector được bảo vệ khỏi tài khoản database có quyền đọc.
- `main.py` hiện tự tạo Fernet key ngẫu nhiên nếu `FERNET_KEY` không được đặt. Cần đặt khóa cố định, bảo vệ backup khóa và có kế hoạch xoay/khôi phục khóa.
- Đây là dữ liệu sinh trắc học và thông tin sinh viên. Chỉ đưa dữ liệu thật lên dịch vụ cloud khi nhóm đã xem xét quyền truy cập, backup, thời hạn lưu, đồng ý sử dụng và quy định áp dụng.
- Supabase không tự cung cấp chế độ điểm danh offline cho app hiện tại. Nếu mất mạng, backend vẫn cần kết nối database. SQLite cache và đồng bộ offline là một tính năng/kiến trúc riêng, chưa được hướng dẫn như thể đã có sẵn.

---

## 9. Lỗi thường gặp

| Hiện tượng | Nguyên nhân thường gặp | Kiểm tra |
|---|---|---|
| `password authentication failed` | Sai password hoặc user | Sao chép lại user/password từ **Connect**; kiểm tra có thừa khoảng trắng không |
| `could not translate host name` | Sai host hoặc placeholder chưa thay | Dùng host đúng từ dashboard, kiểm tra DNS/mạng |
| Timeout / không kết nối được | Sai port, firewall, IPv4/IPv6 hoặc loại kết nối không phù hợp | Thử connection method được dashboard khuyến nghị, thường là Session pooler khi direct không truy cập được |
| `connection refused` | Backend còn trỏ tới PostgreSQL local hoặc sai host/port | In/kiểm tra các biến DB trong cùng PowerShell đang chạy backend; xác nhận host và port |
| `type "vector" does not exist` | Extension pgvector chưa được bật/tạo | Bật `vector`, chạy lại phần schema phù hợp và xác nhận trong `pg_extension` |
| `relation "LopHoc" does not exist` khi chạy schema kèm RLS | Tác vụ tự bật RLS của dashboard tham chiếu tên viết hoa, trong khi PostgreSQL đã lưu tên không ngoặc kép thành chữ thường | Chọn **Run without RLS**, chạy schema, sau đó bật RLS bằng các lệnh `ALTER TABLE public.lophoc ...` ở mục 3 |
| `relation "lophoc" does not exist` | Schema chưa chạy thành công, chạy sai project/database hoặc restore chưa hoàn tất | Kiểm tra project, database và các bảng trong schema `public` |
| App chạy nhưng danh sách lớp trống | Database đúng nhưng chưa có dữ liệu lớp | Thêm lớp demo hoặc nhập dữ liệu cần thiết |
| Đăng ký sinh viên lỗi khi gọi AI | AI Core chưa chạy/URL sai; không nhất thiết là lỗi Supabase | Kiểm tra riêng AI Core và cấu hình URL AI Core |
| Frontend trên máy khác không kết nối được | `localhost` trỏ tới máy client, không phải máy backend | Deploy backend và cấu hình frontend dùng URL backend có thể truy cập |
| Vector đã mã hóa không giải mã được | `FERNET_KEY` bị thiếu hoặc thay đổi sau khi mã hóa dữ liệu | Khôi phục đúng khóa đã dùng; không tạo khóa thay thế nếu chưa có kế hoạch chuyển đổi dữ liệu |

Không gửi password hoặc connection string nguyên văn khi nhờ người khác xem lỗi. Hãy che giá trị bí mật và chỉ chia sẻ thông báo lỗi đã loại bỏ thông tin nhạy cảm.

---

## 10. Quay lại PostgreSQL local

1. Dừng backend.
2. Trong cùng PowerShell, đặt lại `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT` theo PostgreSQL local; xóa `PGSSLMODE` nếu local không dùng SSL:

  ```powershell
  Remove-Item Env:PGSSLMODE -ErrorAction SilentlyContinue
  ```

3. Khởi động backend lại.

Thay đổi biến môi trường không di chuyển dữ liệu giữa hai database. Dữ liệu ghi trên Supabase vẫn ở Supabase, dữ liệu local vẫn ở local, trừ khi đã chạy quy trình dump/restore.

---

## 11. Những việc chưa được thực hiện trong tài liệu này

- Không sửa code ứng dụng hay tạo migration tự động.
- Không deploy FastAPI hoặc AI Core.
- Không triển khai đồng bộ offline SQLite ↔ Supabase.
- Không thiết kế authentication/authorization hoàn chỉnh cho API.
- Không tự chuyển dữ liệu local lên cloud.

Nên làm từng bước: trước tiên kết nối backend local với một Supabase project thử nghiệm; sau khi kiểm thử ổn mới quyết định có chuyển dữ liệu thật và deploy backend hay không.

---

## 12. Ngữ cảnh có thể gửi lại cho AI khi muốn code tiếp

Sao chép đoạn dưới đây vào phiên làm việc mới. Không điền password, connection string hay secret thật vào đoạn ngữ cảnh:

```text
Ngữ cảnh dự án:
- Đây là app điểm danh khuôn mặt NCKH, backend Python/FastAPI, database PostgreSQL,
  frontend PyQt6. Hệ điều hành phát triển là Windows.
- PostgreSQL đang được chuyển dần sang Supabase. Ưu tiên hiện tại là chỉ đổi nơi lưu
  database; FastAPI và AI Core vẫn chạy local. Không mặc định rằng app đã được deploy
  lên cloud hay có hỗ trợ offline.
- Face-ID-Backend/db.py dùng psycopg2 + pgvector.psycopg2.register_vector và đọc
  DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT. Đặt `PGSSLMODE=require` trong
  môi trường để bắt buộc SSL mà không cần sửa `db.py`.
- Face-ID-Backend/schema_postgres.sql tạo extension vector và các bảng
  LopHoc, SinhVien, CaHoc, LichSuDiemDanh, NhatKyXacThuc.
- SinhVien.vector_tho VECTOR(512) và SinhVien.vector_khuon_mat BYTEA được giữ riêng
  có chủ đích: vector_tho dùng truy vấn pgvector, BYTEA chứa vector mã hóa.
- Không đổi hợp đồng AI Core hoặc tên trường của AI Core nếu chưa xác nhận với chủ
  dự án. Logic chuyển đổi định dạng AI nằm trong ai_core_client.py.
- Frontend hiện gọi BASE_URL = http://localhost:8000 trong
  Face-ID-Frontend/api_client.py. Nếu deploy backend, cần làm BASE_URL có thể cấu hình.
- Không đưa secret vào code/Git/frontend. FERNET_KEY phải ổn định và được lưu an toàn;
  main.py hiện tự sinh key nếu biến này thiếu nên cần xử lý trước production.
- Schema không tự có dữ liệu lớp/ca/sinh viên. Backend hiện liệt kê lớp/ca, đăng ký
  sinh viên và điểm danh; việc tạo lớp/ca có thể cần SQL hoặc API quản trị riêng.
- Supabase PostgreSQL không tự cung cấp offline attendance. Offline SQLite cache và
  đồng bộ là công việc riêng.
- Khi chạy schema trong SQL Editor, nếu dashboard hỏi bật RLS thì chọn **Run without
  RLS**, sau đó bật bằng các tên bảng chữ thường (`lophoc`, `sinhvien`, `cahoc`,
  `lichsudiemdanh`, `nhatkyxacthuc`) như mục 3; không dùng tác vụ tự động đang gây lỗi
  `relation "LopHoc" does not exist`.

Khi sửa code:
1. Đọc file hiện tại trước khi sửa và giữ nguyên các thay đổi chưa commit của người dùng.
2. Ưu tiên thay đổi nhỏ, tương thích Windows; không sửa các phần không liên quan.
3. Không dùng secret thật trong ví dụ/log.
4. Nêu rõ file đã sửa, lý do, cách kiểm tra và giới hạn còn lại.
5. Kiểm tra yêu cầu cụ thể bằng lệnh/test nhỏ phù hợp; không khẳng định đã chạy PostgreSQL
   thật nếu chưa kiểm chứng với một instance thật.

Việc cần làm tiếp: [mô tả chính xác thay đổi muốn thực hiện ở đây].
```
