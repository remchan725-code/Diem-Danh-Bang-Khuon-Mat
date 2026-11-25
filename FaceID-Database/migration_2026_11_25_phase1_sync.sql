-- ==============================================================================
-- MIGRATION ĐỒNG BỘ SUPABASE (2026-11-25) — AN TOÀN, KHÔNG XÓA DỮ LIỆU CŨ
-- Chạy 1 lần trong Supabase Dashboard -> SQL Editor -> New query
--
-- Nội dung:
--   1. Đồng bộ schema điểm danh 2 lượt (DotDiemDanh, HangChoDiemDanh, 7 cột mới).
--   2. Bổ sung trường Pha 1 theo góp ý 19/11: CaHoc.phong_hoc, SinhVien.khoa,
--      SinhVien.user_id, bảng trung gian LopHoc_SinhVien (1 SV học nhiều lớp).
--   3. Mở rộng vai trò `sinh_vien` + bảng hàng chờ duyệt khuôn mặt tự nộp
--      YeuCauDangKyKhuonMat + View an toàn + RPC rpc_duyet_yeu_cau_khuon_mat.
--   4. Vá 3 lỗ hổng bảo mật phát hiện trong schema_supabase_snapshot.json:
--      - Thu hồi triệt để quyền mức bảng trên SinhVien, chỉ GRANT cột an toàn
--        (khóa chặt vector_tho và vector_khuon_mat khỏi authenticated/anon).
--      - Gỡ 2 policy UPDATE trực tiếp trên CaHoc & LichSuDiemDanh (bắt buộc qua RPC).
--      - Thu gọn quyền TRUNCATE/TRIGGER/DELETE thừa của authenticated trên mọi bảng.
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ==============================================================================
-- 1. CẬP NHẬT CÁC BẢNG HIỆN CÓ (ADDITIVE / IDEMPOTENT)
-- ==============================================================================

-- 1.1. SinhVien: thêm niên khóa và liên kết tài khoản đăng nhập (1-1 với auth.users)
ALTER TABLE SinhVien ADD COLUMN IF NOT EXISTS khoa TEXT;
ALTER TABLE SinhVien ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_sinhvien_user_id ON SinhVien(user_id) WHERE user_id IS NOT NULL;

-- 1.2. CaHoc: thêm phòng học, hình thức, loại ca, ca gốc
ALTER TABLE CaHoc ADD COLUMN IF NOT EXISTS phong_hoc TEXT;
ALTER TABLE CaHoc ADD COLUMN IF NOT EXISTS hinh_thuc TEXT NOT NULL DEFAULT 'tai_lop';
ALTER TABLE CaHoc ADD COLUMN IF NOT EXISTS loai_ca TEXT NOT NULL DEFAULT 'lich_goc';
ALTER TABLE CaHoc ADD COLUMN IF NOT EXISTS ca_goc_id INT REFERENCES CaHoc(id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_cahoc_hinh_thuc') THEN
        ALTER TABLE CaHoc ADD CONSTRAINT chk_cahoc_hinh_thuc CHECK (hinh_thuc IN ('tai_lop', 'truc_tuyen'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_cahoc_loai_ca') THEN
        ALTER TABLE CaHoc ADD CONSTRAINT chk_cahoc_loai_ca CHECK (loai_ca IN ('lich_goc', 'hoc_bu'));
    END IF;
END $$;

-- 1.3. LichSuDiemDanh: thêm 2 mốc đầu giờ / cuối giờ
ALTER TABLE LichSuDiemDanh ADD COLUMN IF NOT EXISTS dau_gio BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE LichSuDiemDanh ADD COLUMN IF NOT EXISTS dau_gio_luc TIMESTAMPTZ;
ALTER TABLE LichSuDiemDanh ADD COLUMN IF NOT EXISTS cuoi_gio BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE LichSuDiemDanh ADD COLUMN IF NOT EXISTS cuoi_gio_luc TIMESTAMPTZ;

-- 1.4. NguoiDungHeThong: mở rộng vai trò thêm 'sinh_vien'
ALTER TABLE NguoiDungHeThong DROP CONSTRAINT IF EXISTS nguoidunghethong_vai_tro_check;
ALTER TABLE NguoiDungHeThong
    ADD CONSTRAINT nguoidunghethong_vai_tro_check
    CHECK (vai_tro IN ('dev_admin', 'giang_vien', 'sinh_vien'));

-- ==============================================================================
-- 2. TẠO CÁC BẢNG MỚI (ĐIỂM DANH 2 LƯỢT, LỚP-SINH VIÊN N-N, DUYỆT KHUÔN MẶT)
-- ==============================================================================

-- 2.1. Bảng trung gian LopHoc_SinhVien (1 sinh viên học nhiều lớp học phần)
CREATE TABLE IF NOT EXISTS LopHoc_SinhVien (
    id SERIAL PRIMARY KEY,
    lop_id INT NOT NULL REFERENCES LopHoc(id) ON DELETE RESTRICT,
    sinh_vien_id INT NOT NULL REFERENCES SinhVien(id) ON DELETE CASCADE,
    ngay_dang_ky TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_lop_hoc_sinh_vien UNIQUE (lop_id, sinh_vien_id)
);

CREATE INDEX IF NOT EXISTS idx_lop_hoc_sinh_vien_lop ON LopHoc_SinhVien(lop_id);
CREATE INDEX IF NOT EXISTS idx_lop_hoc_sinh_vien_sv ON LopHoc_SinhVien(sinh_vien_id);

-- Backfill dữ liệu cũ từ SinhVien.lop_id sang bảng trung gian (không làm mất lớp cũ)
INSERT INTO LopHoc_SinhVien (lop_id, sinh_vien_id)
SELECT lop_id, id
FROM SinhVien
WHERE lop_id IS NOT NULL
ON CONFLICT (lop_id, sinh_vien_id) DO NOTHING;

-- Trigger tự động ghi lớp mặc định vào LopHoc_SinhVien khi thêm sinh viên mới
CREATE OR REPLACE FUNCTION sync_sinhvien_primary_class()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NEW.lop_id IS NOT NULL THEN
        INSERT INTO LopHoc_SinhVien (lop_id, sinh_vien_id)
        VALUES (NEW.lop_id, NEW.id)
        ON CONFLICT (lop_id, sinh_vien_id) DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_sinhvien_primary_class ON SinhVien;
CREATE TRIGGER trg_sync_sinhvien_primary_class
AFTER INSERT OR UPDATE OF lop_id ON SinhVien
FOR EACH ROW
EXECUTE FUNCTION sync_sinhvien_primary_class();

-- 2.2. Bảng DotDiemDanh (đợt điểm danh đầu giờ / cuối giờ)
CREATE TABLE IF NOT EXISTS DotDiemDanh (
    id SERIAL PRIMARY KEY,
    ca_hoc_id INT NOT NULL REFERENCES CaHoc(id),
    loai TEXT NOT NULL CHECK (loai IN ('dau_gio', 'cuoi_gio')),
    trang_thai TEXT NOT NULL DEFAULT 'dong' CHECK (trang_thai IN ('mo', 'dong')),
    mo_luc TIMESTAMPTZ,
    dong_luc TIMESTAMPTZ,
    giang_vien_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dot_diem_danh UNIQUE (ca_hoc_id, loai)
);

-- 2.3. Bảng HangChoDiemDanh (hàng chờ xác nhận giảng viên)
CREATE TABLE IF NOT EXISTS HangChoDiemDanh (
    id BIGSERIAL PRIMARY KEY,
    dot_diem_danh_id INT NOT NULL REFERENCES DotDiemDanh(id),
    sinh_vien_id INT NOT NULL REFERENCES SinhVien(id),
    request_id UUID NOT NULL UNIQUE,
    trang_thai TEXT NOT NULL DEFAULT 'cho_xac_nhan'
        CHECK (trang_thai IN ('cho_xac_nhan', 'chap_nhan', 'tu_choi')),
    queued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    quyet_dinh_luc TIMESTAMPTZ,
    CONSTRAINT uq_hang_cho_dot_sinh_vien UNIQUE (dot_diem_danh_id, sinh_vien_id)
);

CREATE INDEX IF NOT EXISTS idx_hang_cho_dot_trang_thai
    ON HangChoDiemDanh(dot_diem_danh_id, trang_thai, queued_at);

-- 2.4. Bảng YeuCauDangKyKhuonMat (sinh viên tự nộp mẫu khuôn mặt -> chờ Admin/GV duyệt)
CREATE TABLE IF NOT EXISTS YeuCauDangKyKhuonMat (
    id SERIAL PRIMARY KEY,
    sinh_vien_id INT NOT NULL REFERENCES SinhVien(id) ON DELETE CASCADE,
    vector_tho_tam VECTOR(512),
    vector_khuon_mat_tam BYTEA,
    vector_version TEXT,
    so_anh INT NOT NULL DEFAULT 0,
    confidence_trung_binh NUMERIC(5,4),
    anh_xem_truoc_base64 TEXT,
    ghi_chu_sinh_vien TEXT,
    trang_thai TEXT NOT NULL DEFAULT 'cho_duyet'
        CHECK (trang_thai IN ('cho_duyet', 'da_duyet', 'tu_choi')),
    nguoi_duyet UUID REFERENCES auth.users(id),
    ly_do_duyet TEXT,
    tao_luc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duyet_luc TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_yeu_cau_khuon_mat_sv_trang_thai
    ON YeuCauDangKyKhuonMat(sinh_vien_id, trang_thai, tao_luc DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_yeu_cau_khuon_mat_cho_duyet
    ON YeuCauDangKyKhuonMat(sinh_vien_id)
    WHERE trang_thai = 'cho_duyet';

COMMENT ON COLUMN YeuCauDangKyKhuonMat.anh_xem_truoc_base64 IS
    'Temporary preview thumbnail for identity verification during admin/lecturer review; cleared to NULL immediately upon approval or rejection.';

-- ==============================================================================
-- 3. HÀM HỖ TRỢ PHÂN QUYỀN RLS (SECURITY DEFINER, CỐ ĐỊNH search_path)
-- ==============================================================================

CREATE OR REPLACE FUNCTION current_user_role()
RETURNS TEXT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT vai_tro FROM NguoiDungHeThong WHERE user_id = auth.uid() AND is_active = TRUE;
$$;

CREATE OR REPLACE FUNCTION is_dev_admin()
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM NguoiDungHeThong
    WHERE user_id = auth.uid() AND vai_tro = 'dev_admin' AND is_active = TRUE
  );
$$;

CREATE OR REPLACE FUNCTION giang_vien_co_lop(p_lop_id INT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1 FROM PhanCongGiangVien p
    JOIN NguoiDungHeThong u ON u.user_id = p.giang_vien_id
    WHERE p.giang_vien_id = auth.uid()
      AND p.lop_id = p_lop_id
      AND u.vai_tro = 'giang_vien'
      AND u.is_active = TRUE
  );
$$;

CREATE OR REPLACE FUNCTION current_sinh_vien_id()
RETURNS INT
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT sv.id
  FROM SinhVien sv
  JOIN NguoiDungHeThong u ON u.user_id = sv.user_id
  WHERE sv.user_id = auth.uid()
    AND u.vai_tro = 'sinh_vien'
    AND u.is_active = TRUE
  LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION sinh_vien_thuoc_lop(p_lop_id INT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM LopHoc_SinhVien ls
    WHERE ls.sinh_vien_id = current_sinh_vien_id()
      AND ls.lop_id = p_lop_id
  )
  OR EXISTS (
    SELECT 1
    FROM SinhVien sv
    WHERE sv.id = current_sinh_vien_id()
      AND sv.lop_id = p_lop_id
  );
$$;

CREATE OR REPLACE FUNCTION giang_vien_phu_trach_sinh_vien(p_sinh_vien_id INT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM LopHoc_SinhVien ls
    WHERE ls.sinh_vien_id = p_sinh_vien_id
      AND giang_vien_co_lop(ls.lop_id)
  )
  OR EXISTS (
    SELECT 1
    FROM SinhVien sv
    WHERE sv.id = p_sinh_vien_id
      AND giang_vien_co_lop(sv.lop_id)
  );
$$;

CREATE OR REPLACE FUNCTION sinh_vien_co_vector(p_sinh_vien_id INT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT COALESCE(
    (
      SELECT (vector_khuon_mat IS NOT NULL OR vector_tho IS NOT NULL)
      FROM SinhVien
      WHERE id = p_sinh_vien_id
        AND (
          is_dev_admin()
          OR giang_vien_phu_trach_sinh_vien(p_sinh_vien_id)
          OR p_sinh_vien_id = current_sinh_vien_id()
        )
    ),
    FALSE
  );
$$;

CREATE OR REPLACE FUNCTION yeu_cau_co_vector(p_yeu_cau_id INT)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT COALESCE(
    (
      SELECT (vector_khuon_mat_tam IS NOT NULL OR vector_tho_tam IS NOT NULL)
      FROM YeuCauDangKyKhuonMat y
      WHERE y.id = p_yeu_cau_id
        AND (
          is_dev_admin()
          OR giang_vien_phu_trach_sinh_vien(y.sinh_vien_id)
          OR y.sinh_vien_id = current_sinh_vien_id()
        )
    ),
    FALSE
  );
$$;

GRANT EXECUTE ON FUNCTION sinh_vien_co_vector(INT) TO authenticated;
GRANT EXECUTE ON FUNCTION yeu_cau_co_vector(INT) TO authenticated;

-- ==============================================================================
-- 4. VÁ BẢO MẬT QUYỀN MỨC BẢNG & CỘT (THU HỒI TRUNCATE / VECTOR COLUMNS)
-- ==============================================================================

-- 4.1. Thu hồi sạch mọi quyền thừa (bao gồm TRUNCATE, TRIGGER, REFERENCES) từ anon/authenticated/PUBLIC
REVOKE ALL ON TABLE
    LopHoc, SinhVien, LopHoc_SinhVien, CaHoc, LichSuDiemDanh,
    DotDiemDanh, HangChoDiemDanh, YeuCauDangKyKhuonMat,
    NhatKyXacThuc, NhatKyQuanTri, PhanCongGiangVien,
    CauHinhQuyenGiangVien, NguoiDungHeThong
FROM anon, authenticated, PUBLIC;

-- 4.2. Cấp quyền tối thiểu cần thiết cho authenticated (vẫn lọc chặt bằng RLS bên dưới)
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    LopHoc, LopHoc_SinhVien, CaHoc, PhanCongGiangVien, NguoiDungHeThong
TO authenticated;

GRANT SELECT, UPDATE ON TABLE CauHinhQuyenGiangVien TO authenticated;
GRANT SELECT ON TABLE LichSuDiemDanh, DotDiemDanh, HangChoDiemDanh, NhatKyXacThuc TO authenticated;
GRANT SELECT, INSERT ON TABLE NhatKyQuanTri TO authenticated;

-- SinhVien: CHỈ cấp SELECT cho các cột an toàn (KHÔNG BAO GIỜ cấp vector_tho, vector_khuon_mat!)
GRANT SELECT (id, ma_sv, ho_ten, lop_id, khoa, user_id, vector_version, vector_updated_at, create_at)
    ON TABLE SinhVien TO authenticated;
GRANT DELETE ON TABLE SinhVien TO authenticated;

-- YeuCauDangKyKhuonMat: CHỈ cấp SELECT cho các cột an toàn (KHÔNG cấp vector_tho_tam, vector_khuon_mat_tam!)
GRANT SELECT (id, sinh_vien_id, vector_version, so_anh, confidence_trung_binh,
              anh_xem_truoc_base64, ghi_chu_sinh_vien, trang_thai,
              nguoi_duyet, ly_do_duyet, tao_luc, duyet_luc)
    ON TABLE YeuCauDangKyKhuonMat TO authenticated;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- 4.3. View an toàn cho browser client (security_invoker = true để kế thừa RLS)
DROP VIEW IF EXISTS v_sinh_vien_an_toan;
CREATE VIEW v_sinh_vien_an_toan
WITH (security_invoker = true)
AS
SELECT
    id,
    ma_sv,
    ho_ten,
    lop_id,
    khoa,
    user_id,
    vector_version,
    vector_updated_at,
    create_at,
    sinh_vien_co_vector(id) AS co_vector_khuon_mat
FROM SinhVien;

GRANT SELECT ON v_sinh_vien_an_toan TO authenticated;

DROP VIEW IF EXISTS v_yeu_cau_khuon_mat_an_toan;
CREATE VIEW v_yeu_cau_khuon_mat_an_toan
WITH (security_invoker = true)
AS
SELECT
    id,
    sinh_vien_id,
    vector_version,
    so_anh,
    confidence_trung_binh,
    anh_xem_truoc_base64,
    ghi_chu_sinh_vien,
    trang_thai,
    nguoi_duyet,
    ly_do_duyet,
    tao_luc,
    duyet_luc,
    yeu_cau_co_vector(id) AS co_vector_tam
FROM YeuCauDangKyKhuonMat;

GRANT SELECT ON v_yeu_cau_khuon_mat_an_toan TO authenticated;

-- ==============================================================================
-- 5. BẬT RLS & CẬP NHẬT POLICIES (KHÓA ĐI VÒNG RPC + THÊM ROLE sinh_vien)
-- ==============================================================================

ALTER TABLE LopHoc ENABLE ROW LEVEL SECURITY;
ALTER TABLE SinhVien ENABLE ROW LEVEL SECURITY;
ALTER TABLE LopHoc_SinhVien ENABLE ROW LEVEL SECURITY;
ALTER TABLE CaHoc ENABLE ROW LEVEL SECURITY;
ALTER TABLE LichSuDiemDanh ENABLE ROW LEVEL SECURITY;
ALTER TABLE DotDiemDanh ENABLE ROW LEVEL SECURITY;
ALTER TABLE HangChoDiemDanh ENABLE ROW LEVEL SECURITY;
ALTER TABLE YeuCauDangKyKhuonMat ENABLE ROW LEVEL SECURITY;
ALTER TABLE NhatKyXacThuc ENABLE ROW LEVEL SECURITY;
ALTER TABLE NhatKyQuanTri ENABLE ROW LEVEL SECURITY;
ALTER TABLE PhanCongGiangVien ENABLE ROW LEVEL SECURITY;
ALTER TABLE CauHinhQuyenGiangVien ENABLE ROW LEVEL SECURITY;
ALTER TABLE NguoiDungHeThong ENABLE ROW LEVEL SECURITY;

-- 5.1. Gỡ 2 policy UPDATE đi vòng RPC (bắt buộc giảng viên sửa qua rpc_doi_ca_hoc / rpc_dieu_chinh_diem_danh)
DROP POLICY IF EXISTS "giang_vien_reschedule_cahoc" ON CaHoc;
DROP POLICY IF EXISTS "giang_vien_update_diemdanh" ON LichSuDiemDanh;

-- 5.2. LopHoc
DROP POLICY IF EXISTS "sinh_vien_select_lophoc" ON LopHoc;
CREATE POLICY "sinh_vien_select_lophoc" ON LopHoc
FOR SELECT TO authenticated USING (sinh_vien_thuoc_lop(id));

-- 5.3. SinhVien (GV thấy SV thuộc lớp phụ trách kể cả qua LopHoc_SinhVien; SV chỉ thấy chính mình)
DROP POLICY IF EXISTS "giang_vien_select_sinhvien" ON SinhVien;
CREATE POLICY "giang_vien_select_sinhvien" ON SinhVien
FOR SELECT TO authenticated USING (giang_vien_phu_trach_sinh_vien(id));

DROP POLICY IF EXISTS "sinh_vien_select_self" ON SinhVien;
CREATE POLICY "sinh_vien_select_self" ON SinhVien
FOR SELECT TO authenticated USING (id = current_sinh_vien_id());

-- 5.4. LopHoc_SinhVien
DROP POLICY IF EXISTS "dev_admin_all_lophoc_sinhvien" ON LopHoc_SinhVien;
CREATE POLICY "dev_admin_all_lophoc_sinhvien" ON LopHoc_SinhVien
FOR ALL TO authenticated USING (is_dev_admin()) WITH CHECK (is_dev_admin());

DROP POLICY IF EXISTS "giang_vien_select_lophoc_sinhvien" ON LopHoc_SinhVien;
CREATE POLICY "giang_vien_select_lophoc_sinhvien" ON LopHoc_SinhVien
FOR SELECT TO authenticated USING (giang_vien_co_lop(lop_id));

DROP POLICY IF EXISTS "sinh_vien_select_own_lophoc_sinhvien" ON LopHoc_SinhVien;
CREATE POLICY "sinh_vien_select_own_lophoc_sinhvien" ON LopHoc_SinhVien
FOR SELECT TO authenticated USING (sinh_vien_id = current_sinh_vien_id());

-- 5.5. CaHoc
DROP POLICY IF EXISTS "sinh_vien_select_cahoc" ON CaHoc;
CREATE POLICY "sinh_vien_select_cahoc" ON CaHoc
FOR SELECT TO authenticated USING (sinh_vien_thuoc_lop(lop_id));

-- 5.6. LichSuDiemDanh (SV chỉ xem điểm danh của chính mình)
DROP POLICY IF EXISTS "sinh_vien_select_own_diemdanh" ON LichSuDiemDanh;
CREATE POLICY "sinh_vien_select_own_diemdanh" ON LichSuDiemDanh
FOR SELECT TO authenticated USING (sinh_vien_id = current_sinh_vien_id());

-- 5.7. DotDiemDanh
DROP POLICY IF EXISTS "dev_admin_all_dotdiemdanh" ON DotDiemDanh;
CREATE POLICY "dev_admin_all_dotdiemdanh" ON DotDiemDanh
FOR ALL TO authenticated USING (is_dev_admin()) WITH CHECK (is_dev_admin());

DROP POLICY IF EXISTS "giang_vien_select_dotdiemdanh" ON DotDiemDanh;
CREATE POLICY "giang_vien_select_dotdiemdanh" ON DotDiemDanh
FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM CaHoc c WHERE c.id = DotDiemDanh.ca_hoc_id AND giang_vien_co_lop(c.lop_id))
);

DROP POLICY IF EXISTS "sinh_vien_select_dotdiemdanh" ON DotDiemDanh;
CREATE POLICY "sinh_vien_select_dotdiemdanh" ON DotDiemDanh
FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM CaHoc c WHERE c.id = DotDiemDanh.ca_hoc_id AND sinh_vien_thuoc_lop(c.lop_id))
);

-- 5.8. HangChoDiemDanh
DROP POLICY IF EXISTS "dev_admin_all_hangcho" ON HangChoDiemDanh;
CREATE POLICY "dev_admin_all_hangcho" ON HangChoDiemDanh
FOR ALL TO authenticated USING (is_dev_admin()) WITH CHECK (is_dev_admin());

DROP POLICY IF EXISTS "giang_vien_select_hangcho" ON HangChoDiemDanh;
CREATE POLICY "giang_vien_select_hangcho" ON HangChoDiemDanh
FOR SELECT TO authenticated USING (
    EXISTS (
        SELECT 1 FROM DotDiemDanh d
        JOIN CaHoc c ON c.id = d.ca_hoc_id
        WHERE d.id = HangChoDiemDanh.dot_diem_danh_id
          AND giang_vien_co_lop(c.lop_id)
    )
);

DROP POLICY IF EXISTS "sinh_vien_select_own_hangcho" ON HangChoDiemDanh;
CREATE POLICY "sinh_vien_select_own_hangcho" ON HangChoDiemDanh
FOR SELECT TO authenticated USING (sinh_vien_id = current_sinh_vien_id());

-- 5.9. YeuCauDangKyKhuonMat (Chỉ SELECT theo phạm vi quyền; mọi phê duyệt đi qua RPC!)
DROP POLICY IF EXISTS "dev_admin_select_yeucaukhuonmat" ON YeuCauDangKyKhuonMat;
CREATE POLICY "dev_admin_select_yeucaukhuonmat" ON YeuCauDangKyKhuonMat
FOR SELECT TO authenticated USING (is_dev_admin());

DROP POLICY IF EXISTS "giang_vien_select_yeucaukhuonmat" ON YeuCauDangKyKhuonMat;
CREATE POLICY "giang_vien_select_yeucaukhuonmat" ON YeuCauDangKyKhuonMat
FOR SELECT TO authenticated USING (giang_vien_phu_trach_sinh_vien(sinh_vien_id));

DROP POLICY IF EXISTS "sinh_vien_select_own_yeucaukhuonmat" ON YeuCauDangKyKhuonMat;
CREATE POLICY "sinh_vien_select_own_yeucaukhuonmat" ON YeuCauDangKyKhuonMat
FOR SELECT TO authenticated USING (sinh_vien_id = current_sinh_vien_id());

-- ==============================================================================
-- 6. RPC PHÊ DUYỆT / TỪ CHỐI MẪU KHUÔN MẶT SINH VIÊN TỰ NỘP
-- ==============================================================================

CREATE OR REPLACE FUNCTION rpc_duyet_yeu_cau_khuon_mat(
    p_yeu_cau_id INT,
    p_quyet_dinh TEXT,
    p_ly_do TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_req YeuCauDangKyKhuonMat%ROWTYPE;
    v_ma_sv TEXT;
    v_is_admin BOOLEAN;
BEGIN
    IF p_quyet_dinh NOT IN ('da_duyet', 'tu_choi') THEN
        RAISE EXCEPTION 'Quyết định không hợp lệ: % (chỉ nhận da_duyet hoặc tu_choi).', p_quyet_dinh;
    END IF;

    IF p_quyet_dinh = 'tu_choi' AND (p_ly_do IS NULL OR length(btrim(p_ly_do)) < 5) THEN
        RAISE EXCEPTION 'Bắt buộc nhập lý do từ chối (tối thiểu 5 ký tự) để sinh viên biết cách chụp lại.';
    END IF;

    SELECT * INTO v_req
    FROM YeuCauDangKyKhuonMat
    WHERE id = p_yeu_cau_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Không tìm thấy yêu cầu đăng ký khuôn mặt ID: %', p_yeu_cau_id;
    END IF;

    IF v_req.trang_thai <> 'cho_duyet' THEN
        RAISE EXCEPTION 'Yêu cầu #% đã được xử lý trước đó (trạng thái: %).', p_yeu_cau_id, v_req.trang_thai;
    END IF;

    -- Kiểm tra quyền: chỉ dev_admin hoặc giảng viên phụ trách lớp học phần của sinh viên đó
    v_is_admin := is_dev_admin();
    IF NOT v_is_admin AND NOT giang_vien_phu_trach_sinh_vien(v_req.sinh_vien_id) THEN
        RAISE EXCEPTION 'Bạn không có quyền duyệt mẫu khuôn mặt của sinh viên này.';
    END IF;

    SELECT ma_sv INTO v_ma_sv FROM SinhVien WHERE id = v_req.sinh_vien_id;

    IF p_quyet_dinh = 'da_duyet' THEN
        IF v_req.vector_tho_tam IS NULL OR v_req.vector_khuon_mat_tam IS NULL THEN
            RAISE EXCEPTION 'Yêu cầu #% chưa có dữ liệu vector sinh trắc học hợp lệ từ AI Core.', p_yeu_cau_id;
        END IF;

        -- Chốt vector chính thức sang SinhVien
        UPDATE SinhVien
        SET vector_tho = v_req.vector_tho_tam,
            vector_khuon_mat = v_req.vector_khuon_mat_tam,
            vector_version = v_req.vector_version,
            vector_updated_at = CURRENT_TIMESTAMP
        WHERE id = v_req.sinh_vien_id;
    END IF;

    -- Xóa ngay ảnh đối chiếu tạm và vector tạm để bảo vệ dữ liệu sinh trắc học
    UPDATE YeuCauDangKyKhuonMat
    SET trang_thai = p_quyet_dinh,
        nguoi_duyet = auth.uid(),
        ly_do_duyet = CASE WHEN p_ly_do IS NOT NULL AND btrim(p_ly_do) <> '' THEN btrim(p_ly_do) ELSE NULL END,
        duyet_luc = CURRENT_TIMESTAMP,
        vector_tho_tam = NULL,
        vector_khuon_mat_tam = NULL,
        anh_xem_truoc_base64 = NULL
    WHERE id = p_yeu_cau_id;

    INSERT INTO NhatKyQuanTri (
        nguoi_thuc_hien, hanh_dong, doi_tuong, doi_tuong_id, ly_do, thong_tin_thay_doi
    ) VALUES (
        auth.uid(),
        CASE WHEN p_quyet_dinh = 'da_duyet' THEN 'DUYET_KHUON_MAT_SV' ELSE 'TU_CHOI_KHUON_MAT_SV' END,
        'YeuCauDangKyKhuonMat',
        p_yeu_cau_id::TEXT,
        COALESCE(NULLIF(btrim(p_ly_do), ''), 'Xác nhận đúng danh tính sinh viên và kích hoạt mẫu khuôn mặt'),
        jsonb_build_object(
            'sinh_vien_id', v_req.sinh_vien_id,
            'ma_sv', v_ma_sv,
            'quyet_dinh', p_quyet_dinh,
            'so_anh', v_req.so_anh,
            'confidence_trung_binh', v_req.confidence_trung_binh
        )
    );

    RETURN jsonb_build_object(
        'success', TRUE,
        'quyet_dinh', p_quyet_dinh,
        'sinh_vien_id', v_req.sinh_vien_id
    );
END;
$$;

GRANT EXECUTE ON FUNCTION rpc_duyet_yeu_cau_khuon_mat(INT, TEXT, TEXT) TO authenticated;

-- Nạp lại schema cache cho Supabase PostgREST
NOTIFY pgrst, 'reload schema';
