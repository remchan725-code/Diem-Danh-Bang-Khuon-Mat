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
    vector_khuon_mat BYTEA,
    lop_id int not null REFERENCES LopHoc(id),
    create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

create table CaHoc(
    id SERIAL Primary KEY,
    lop_id int NOT NULL REFERENCES LopHoc(id),
    ngay DATE not NULL,
    gio_bat_dau TIME NOT null,
    gio_ket_thuc TIME
);

create table LichSuDiemDanh(
    id SERIAL primary KEY,
    sinh_vien_id int not null REFERENCES SinhVien(id),
    ca_hoc_id int NOT NULL REFERENCES CaHoc(id),
    thoi_gian TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trang_thai TEXT not null check(trang_thai IN ('co_mat','tre','vang')),
    is_synced BOOLEAN DEFAULT FALSE
);

create INDEX idx_diemdanh_sinhvien On LichSuDiemDanh(sinh_vien_id)
create INDEX idx_diemdanh_cahic On LichSuDiemDanh(ca_hoc_id)
create index idx_sinhvien_masv On SinhVien(ma_sv)