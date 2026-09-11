DROP TABLE IF EXISTS LopHoc;

CREATE TABLE LopHoc (
    id SERIAL PRIMARY KEY,
    ten_lop VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

create Table SinhVien(
    id SERIAL PRIMARY KEY,
    ma_sv Text UNIQUE NOT NULL,
    ho_ten TEXT NOT NULL,
    vector_tho vector(512),
    vector_ma_hoa BYTEA,
    lop_id INTEGER NOT NULL REFERENCES LopHoc(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bang 3: CaHoc
CREATE TABLE CaHoc (
    id SERIAL PRIMARY KEY,
    lop_id INTEGER NOT NULL REFERENCES LopHoc(id),
    ngay DATE NOT NULL,
    gio_bat_dau TIME NOT NULL,
    gio_ket_thuc TIME
);

-- Bang 4: LichSuDiemDanh
CREATE TABLE LichSuDiemDanh (
    id SERIAL PRIMARY KEY,
    sinh_vien_id INTEGER NOT NULL REFERENCES SinhVien(id),
    ca_hoc_id INTEGER NOT NULL REFERENCES CaHoc(id),
    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trang_thai TEXT NOT NULL CHECK (trang_thai IN ('co_mat', 'vang', 'tre')),
    is_synced BOOLEAN DEFAULT FALSE
);

-- Index
CREATE INDEX idx_diemdanh_sinhvien ON LichSuDiemDanh(sinh_vien_id);
CREATE INDEX idx_diemdanh_cahoc ON LichSuDiemDanh(ca_hoc_id);
CREATE INDEX idx_sinhvien_masv ON SinhVien(ma_sv);

-- Index HNSW cho pgvector: khong bat buoc o quy mo 1 lop hoc, nhung huu ich
-- khi mo rong len nhieu lop hoac nhieu khoa.
CREATE INDEX idx_sinhvien_vector ON SinhVien USING hnsw (vector_tho vector_cosine_ops);
