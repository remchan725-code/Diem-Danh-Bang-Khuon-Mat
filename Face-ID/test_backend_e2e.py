import sys
import os
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
 
sys.path.insert(0, "backend")
from fastapi.testclient import TestClient
 
import main
import ai_core_mock
from db import get_connection
 
 
def don_dep_va_tao_lop_ca():
    """Xóa dữ liệu cũ, tạo sẵn 1 lớp + 1 ca học để gắn dữ liệu test vào."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM LichSuDiemDanh")
    cur.execute("DELETE FROM SinhVien")
    cur.execute("DELETE FROM CaHoc")
    cur.execute("DELETE FROM LopHoc")
    cur.execute("INSERT INTO LopHoc (ten_lop) VALUES ('CNTT01') RETURNING id")
    lop_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO CaHoc (lop_id, ngay, gio_bat_dau) VALUES (%s, '2026-09-08', '07:30') RETURNING id",
        (lop_id,),
    )
    ca_hoc_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return lop_id, ca_hoc_id
 
 
def vector_don_vi(vec: np.ndarray) -> list:
    return (vec / np.linalg.norm(vec)).tolist()
 
 
def chay_test():
    lop_id, ca_hoc_id = don_dep_va_tao_lop_ca()
    client = TestClient(main.app)
 
    # --- Bước 1: đăng ký 1 sinh viên, cố định vector để test kiểm soát được ---
    vector_that = vector_don_vi(np.random.normal(size=512))
    ai_core_mock.register_face = lambda image_bytes: {
        "vector": vector_that, "confidence": 0.99, "bbox": [0, 0, 100, 100]
    }
 
    resp = client.post(
        "/api/v1/dang-ky-sinh-vien",
        data={"ma_sv": "SV001", "ho_ten": "Độ Mixi", "lop_id": lop_id},
        files={"anh": ("anh.jpg", b"noi-dung-anh-gia-lap", "image/jpeg")},
    )
    print("1) Đăng ký sinh viên:", resp.status_code, resp.json())
    assert resp.status_code == 200
 
    # --- Bước 2: điểm danh với khuôn mặt CÙNG người (vector gần giống, nhiễu nhỏ) ---
    vector_giong = vector_don_vi(np.array(vector_that) + np.random.normal(scale=0.02, size=512))
    ai_core_mock.process_frame = lambda b64: [
        {"vector": vector_giong, "confidence": 0.95, "bbox": [10, 10, 110, 110]}
    ]
 
    resp = client.post("/api/v1/diem-danh", json={"ca_hoc_id": ca_hoc_id, "frame_base64": "xxx"})
    du_lieu = resp.json()
    print("2) Điểm danh (đúng người):", resp.status_code, du_lieu)
    assert du_lieu["ket_qua"][0]["nhan_dien"] is True, "Phải nhận diện đúng người vừa đăng ký!"
 
    # --- Bước 3: điểm danh với khuôn mặt LẠ (vector hoàn toàn khác, không liên quan) ---
    vector_la = vector_don_vi(np.random.normal(size=512))
    ai_core_mock.process_frame = lambda b64: [
        {"vector": vector_la, "confidence": 0.9, "bbox": [10, 10, 110, 110]}
    ]
 
    resp = client.post("/api/v1/diem-danh", json={"ca_hoc_id": ca_hoc_id, "frame_base64": "yyy"})
    du_lieu = resp.json()
    print("3) Điểm danh (người lạ):", resp.status_code, du_lieu)
    assert du_lieu["ket_qua"][0]["nhan_dien"] is False, "Không được nhận nhầm người lạ!"
 
    print("\nTẤT CẢ TEST PASS — luồng đăng ký + so khớp pgvector hoạt động đúng.")
 
 
if __name__ == "__main__":
    chay_test()
