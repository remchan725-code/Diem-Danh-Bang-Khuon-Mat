-- Active: 1788838410938@@127.0.0.1@5432@attendance_db

CREATE TABLE LopHoc (
    id SERIAL PRIMARY KEY,
    ten_lop VARCHAR(25) NOT NULL CHECK (btrim(ten_lop) <> ''),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

create Table SinhVien(
    id SERIAL PRIMARY KEY,
    ma_sv Text NOT NULL UNIQUE check (btrim(ma_sv) <> ''),--xoa khoang trang dau cuoi cua ma_sv tranh UNIQUE nhan nham                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
    ho_ten TEXT NOT NULL check (btrim(ho_ten) <> ''),--VD: sv001 khác với " sv001 "
    vector_khuon_mat BYTEA,
    vector_version text,
    vector_updated_at TIMESTAMPTZ,--timestamptz : theo múi giờ tự
    lop_id int not null REFERENCES LopHoc(id),
    create_at TIMESTAMPTZ not null DEFAULT CURRENT_TIMESTAMP
);

create table CaHoc(
    id SERIAL Primary KEY,
    lop_id int NOT NULL REFERENCES LopHoc(id),
    ngay DATE not NULL,
    gio_bat_dau TIME NOT null,
    gio_ket_thuc TIME
    constraint uq_ca_hoc UNIQUE (lop_id,ngay,gio_bat_dau),
    constraint check_time check (gio_ket_thuc is NULL or gio_ket_thuc > gio_bat_dau)
);

create table LichSuDiemDanh(
    id SERIAL primary KEY,
    sinh_vien_id int not null REFERENCES SinhVien(id),
    ca_hoc_id int NOT NULL REFERENCES CaHoc(id),
    thoi_gian TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
     CONSTRAINT chk_trang_thai_diem_danh
        CHECK (trang_thai IN ('co_mat', 'tre', 'vang')),
    constraint UQ_diemdanh UNIQUE (ca_hoc_id,sinh_vien_id),
    is_synced BOOLEAN DEFAULT FALSE
);

CREATE TABLE NhatKyXacThuc (
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
    request_id UUID UNIQUE,
    CONSTRAINT chk_ket_qua_xac_thuc
        CHECK (ket_qua IN ('chap_nhan', 'tu_choi', 'khong_xac_dinh')),
    CONSTRAINT chk_diem_khuon_mat
        CHECK (diem_khuon_mat IS NULL OR diem_khuon_mat BETWEEN 0 AND 1),
    CONSTRAINT chk_diem_song
        CHECK (diem_song IS NULL OR diem_song BETWEEN 0 AND 1),
    CONSTRAINT chk_ly_do_tu_choi
        CHECK (ket_qua <> 'tu_choi' OR ly_do_tu_choi IS NOT NULL)
);
CREATE INDEX idx_sinh_vien_lop ON SinhVien(lop_id);
CREATE INDEX idx_ca_hoc_lop_ngay ON CaHoc(lop_id, ngay);
CREATE INDEX idx_diem_danh_sinh_vien ON LichSuDiemDanh(sinh_vien_id);
CREATE INDEX idx_diem_danh_ca_hoc ON LichSuDiemDanh(ca_hoc_id);
CREATE INDEX idx_nhat_ky_ca_hoc_thoi_gian ON NhatKyXacThuc(ca_hoc_id, thoi_gian DESC);
CREATE INDEX idx_nhat_ky_sinh_vien_thoi_gian ON NhatKyXacThuc(sinh_vien_id, thoi_gian DESC);
COMMENT ON COLUMN SinhVien.vector_khuon_mat IS
    'Encrypted biometric template only; never persist raw face images in this column.';
COMMENT ON TABLE NhatKyXacThuc IS
    'Audit log of every AI and liveness verification attempt; retain under the approved data-retention policy.';
sinhvien_masv On SinhVien(ma_sv);
sinhvien_masv On SinhVien(ma_sv);
