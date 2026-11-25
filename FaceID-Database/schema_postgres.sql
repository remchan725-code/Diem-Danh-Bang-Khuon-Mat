-- Active: 1788838410938@@127.0.0.1@5433@postgres
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS LopHoc (
    id SERIAL PRIMARY KEY,
    ten_lop VARCHAR(25) NOT NULL CHECK (btrim(ten_lop) <> ''),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS SinhVien (
    id SERIAL PRIMARY KEY,
    ma_sv TEXT NOT NULL UNIQUE CHECK (btrim(ma_sv) <> ''),
    ho_ten TEXT NOT NULL CHECK (btrim(ho_ten) <> ''),
    vector_tho VECTOR(512),
    vector_khuon_mat BYTEA,
    vector_version TEXT,
    vector_updated_at TIMESTAMPTZ,
    lop_id INT NOT NULL REFERENCES LopHoc(id), -- Lớp hành chính mặc định
    khoa TEXT,                                 -- Niên khóa / khóa học (Pha 1 - 19/11)
    user_id UUID UNIQUE,                       -- Liên kết tài khoản đăng nhập (Supabase auth.users)
    create_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Bảng trung gian n-n: 1 sinh viên có thể học nhiều lớp học phần
CREATE TABLE IF NOT EXISTS LopHoc_SinhVien (
    id SERIAL PRIMARY KEY,
    lop_id INT NOT NULL REFERENCES LopHoc(id) ON DELETE RESTRICT,
    sinh_vien_id INT NOT NULL REFERENCES SinhVien(id) ON DELETE CASCADE,
    ngay_dang_ky TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_lop_hoc_sinh_vien UNIQUE (lop_id, sinh_vien_id)
);

CREATE TABLE IF NOT EXISTS CaHoc (
    id SERIAL PRIMARY KEY,
    lop_id INT NOT NULL REFERENCES LopHoc(id),
    ngay DATE NOT NULL,
    gio_bat_dau TIME NOT NULL,
    gio_ket_thuc TIME,
    phong_hoc TEXT,
    hinh_thuc TEXT NOT NULL DEFAULT 'tai_lop' CHECK (hinh_thuc IN ('tai_lop', 'truc_tuyen')),
    loai_ca TEXT NOT NULL DEFAULT 'lich_goc' CHECK (loai_ca IN ('lich_goc', 'hoc_bu')),
    ca_goc_id INT REFERENCES CaHoc(id),
    CONSTRAINT uq_ca_hoc UNIQUE (lop_id, ngay, gio_bat_dau),
    CONSTRAINT check_time CHECK (gio_ket_thuc IS NULL OR gio_ket_thuc > gio_bat_dau)
);

CREATE TABLE IF NOT EXISTS LichSuDiemDanh (
    id SERIAL PRIMARY KEY,
    sinh_vien_id INT NOT NULL REFERENCES SinhVien(id),
    ca_hoc_id INT NOT NULL REFERENCES CaHoc(id),
    thoi_gian TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    trang_thai TEXT NOT NULL CHECK (trang_thai IN ('co_mat', 'tre', 'vang')),
    dau_gio BOOLEAN NOT NULL DEFAULT FALSE,
    dau_gio_luc TIMESTAMPTZ,
    cuoi_gio BOOLEAN NOT NULL DEFAULT FALSE,
    cuoi_gio_luc TIMESTAMPTZ,
    CONSTRAINT UQ_diemdanh UNIQUE (ca_hoc_id, sinh_vien_id),
    is_synced BOOLEAN DEFAULT FALSE
);

-- Additive migration for databases created from earlier versions of this schema.
ALTER TABLE SinhVien ADD COLUMN IF NOT EXISTS khoa TEXT;
ALTER TABLE SinhVien ADD COLUMN IF NOT EXISTS user_id UUID;
CREATE UNIQUE INDEX IF NOT EXISTS uq_sinhvien_user_id ON SinhVien(user_id) WHERE user_id IS NOT NULL;
ALTER TABLE CaHoc ADD COLUMN IF NOT EXISTS phong_hoc TEXT;
ALTER TABLE CaHoc ADD COLUMN IF NOT EXISTS hinh_thuc TEXT NOT NULL DEFAULT 'tai_lop';
ALTER TABLE CaHoc ADD COLUMN IF NOT EXISTS loai_ca TEXT NOT NULL DEFAULT 'lich_goc';
ALTER TABLE CaHoc ADD COLUMN IF NOT EXISTS ca_goc_id INT REFERENCES CaHoc(id);
ALTER TABLE LichSuDiemDanh ADD COLUMN IF NOT EXISTS dau_gio BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE LichSuDiemDanh ADD COLUMN IF NOT EXISTS dau_gio_luc TIMESTAMPTZ;
ALTER TABLE LichSuDiemDanh ADD COLUMN IF NOT EXISTS cuoi_gio BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE LichSuDiemDanh ADD COLUMN IF NOT EXISTS cuoi_gio_luc TIMESTAMPTZ;

INSERT INTO LopHoc_SinhVien (lop_id, sinh_vien_id)
SELECT lop_id, id FROM SinhVien WHERE lop_id IS NOT NULL
ON CONFLICT (lop_id, sinh_vien_id) DO NOTHING;

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

-- Hàng chờ duyệt mẫu khuôn mặt do sinh viên tự nộp (chống gian lận danh tính đầu vào)
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
    nguoi_duyet UUID,
    ly_do_duyet TEXT,
    tao_luc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duyet_luc TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS NhatKyXacThuc (
    id SERIAL PRIMARY KEY,
    ca_hoc_id INT NOT NULL REFERENCES CaHoc(id),
    sinh_vien_id INT REFERENCES SinhVien(id),
    thoi_gian TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ket_qua TEXT NOT NULL,
    ly_do_tu_choi TEXT,
    diem_khuon_mat NUMERIC(5,4),
    diem_song NUMERIC(5,4),
    model_version TEXT NOT NULL,
    device_id TEXT,
    request_id UUID NOT NULL UNIQUE,
    CONSTRAINT chk_ket_qua_xac_thuc CHECK (ket_qua IN ('chap_nhan', 'tu_choi', 'khong_xac_dinh')),

    CONSTRAINT chk_diem_khuon_mat CHECK (diem_khuon_mat IS NULL OR diem_khuon_mat BETWEEN 0 AND 1),

    CONSTRAINT chk_diem_song CHECK (diem_song IS NULL OR diem_song BETWEEN 0 AND 1),

    CONSTRAINT chk_chap_nhan_can_sinh_vien CHECK (ket_qua <> 'chap_nhan' OR sinh_vien_id IS NOT NULL),

    CONSTRAINT chk_ly_do_tu_choi CHECK (ket_qua <> 'tu_choi' OR ly_do_tu_choi IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_sinh_vien_lop ON SinhVien(lop_id);
CREATE INDEX IF NOT EXISTS idx_lop_hoc_sinh_vien_lop ON LopHoc_SinhVien(lop_id);
CREATE INDEX IF NOT EXISTS idx_lop_hoc_sinh_vien_sv ON LopHoc_SinhVien(sinh_vien_id);
CREATE INDEX IF NOT EXISTS idx_ca_hoc_lop_ngay ON CaHoc(lop_id, ngay);
CREATE INDEX IF NOT EXISTS idx_diem_danh_sinh_vien ON LichSuDiemDanh(sinh_vien_id);
CREATE INDEX IF NOT EXISTS idx_diem_danh_ca_hoc ON LichSuDiemDanh(ca_hoc_id);
CREATE INDEX IF NOT EXISTS idx_nhat_ky_ca_hoc_thoi_gian ON NhatKyXacThuc(ca_hoc_id, thoi_gian DESC);
CREATE INDEX IF NOT EXISTS idx_nhat_ky_sinh_vien_thoi_gian ON NhatKyXacThuc(sinh_vien_id, thoi_gian DESC);
CREATE INDEX IF NOT EXISTS idx_hang_cho_dot_trang_thai ON HangChoDiemDanh(dot_diem_danh_id, trang_thai, queued_at);
CREATE INDEX IF NOT EXISTS idx_yeu_cau_khuon_mat_sv_trang_thai ON YeuCauDangKyKhuonMat(sinh_vien_id, trang_thai, tao_luc DESC);
CREATE UNIQUE INDEX IF NOT EXISTS uq_yeu_cau_khuon_mat_cho_duyet ON YeuCauDangKyKhuonMat(sinh_vien_id) WHERE trang_thai = 'cho_duyet';

COMMENT ON COLUMN SinhVien.vector_khuon_mat IS
    'Encrypted biometric template only; never persist raw face images in this column.';
COMMENT ON TABLE NhatKyXacThuc IS
    'Audit log of every AI and liveness verification attempt; retain under the approved data-retention policy.';
CREATE INDEX IF NOT EXISTS idx_sinhvien_masv ON SinhVien(ma_sv);
