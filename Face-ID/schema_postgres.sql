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
    lop_id INT NOT NULL REFERENCES LopHoc(id),
    create_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS CaHoc (
    id SERIAL PRIMARY KEY,
    lop_id INT NOT NULL REFERENCES LopHoc(id),
    ngay DATE NOT NULL,
    gio_bat_dau TIME NOT NULL,
    gio_ket_thuc TIME,
    CONSTRAINT uq_ca_hoc UNIQUE (lop_id, ngay, gio_bat_dau),
    CONSTRAINT check_time CHECK (gio_ket_thuc IS NULL OR gio_ket_thuc > gio_bat_dau)
);

CREATE TABLE IF NOT EXISTS LichSuDiemDanh (
    id SERIAL PRIMARY KEY,
    sinh_vien_id INT NOT NULL REFERENCES SinhVien(id),
    ca_hoc_id INT NOT NULL REFERENCES CaHoc(id),
    thoi_gian TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    trang_thai TEXT NOT NULL CHECK (trang_thai IN ('co_mat', 'tre', 'vang')),
    CONSTRAINT UQ_diemdanh UNIQUE (ca_hoc_id, sinh_vien_id),
    is_synced BOOLEAN DEFAULT FALSE
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
CREATE INDEX IF NOT EXISTS idx_ca_hoc_lop_ngay ON CaHoc(lop_id, ngay);
CREATE INDEX IF NOT EXISTS idx_diem_danh_sinh_vien ON LichSuDiemDanh(sinh_vien_id);
CREATE INDEX IF NOT EXISTS idx_diem_danh_ca_hoc ON LichSuDiemDanh(ca_hoc_id);
CREATE INDEX IF NOT EXISTS idx_nhat_ky_ca_hoc_thoi_gian ON NhatKyXacThuc(ca_hoc_id, thoi_gian DESC);
CREATE INDEX IF NOT EXISTS idx_nhat_ky_sinh_vien_thoi_gian ON NhatKyXacThuc(sinh_vien_id, thoi_gian DESC);

COMMENT ON COLUMN SinhVien.vector_khuon_mat IS
    'Encrypted biometric template only; never persist raw face images in this column.';
COMMENT ON TABLE NhatKyXacThuc IS
    'Audit log of every AI and liveness verification attempt; retain under the approved data-retention policy.';
CREATE INDEX IF NOT EXISTS idx_sinhvien_masv ON SinhVien(ma_sv);
