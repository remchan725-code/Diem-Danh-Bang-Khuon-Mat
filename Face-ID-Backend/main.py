import os
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2 import errors as pg_errors
#Cần import thư viện psycopg2 và module errors để phân loại lỗi PostgreSQL cụ thể
 
import ai_core_mock
import crypto_utils
from db import get_connection
 
app = FastAPI(title="He thong diem danh - Backend API")
 
# Key thật PHẢI nạp từ biến môi trường (xem SETUP.md). Fallback ở đây chỉ để
# server chạy được ngay lúc demo/test, không dùng khi triển khai thật.
FERNET_KEY = os.getenv("FERNET_KEY", crypto_utils.generate_key())
 
# Cosine distance càng nhỏ càng giống (0 = giống hệt, 2 = đối lập hoàn toàn).
# Ngưỡng 0.4 là điểm khởi đầu hợp lý cho embedding ArcFace — CẦN tinh chỉnh lại
# bằng thực nghiệm ở Giai đoạn 5 (kiểm thử) với dữ liệu khuôn mặt thật.
NGUONG_KHOP = 0.4
 
 
class DiemDanhRequest(BaseModel):
    ca_hoc_id: int
    frame_base64: str
 
@app.post("/api/v1/dang-ky-sinh-vien")
async def dang_ky_sinh_vien(
    ma_sv: str = Form(...),
    ho_ten: str = Form(...),
    lop_id: int = Form(...),
    anh: UploadFile = File(...),
):
    image_bytes = await anh.read()
 
    # Gọi AI Core: input ảnh raw (đúng contract — không crop trước ở đây)
    ket_qua = ai_core_mock.register_face(image_bytes)
    vector = ket_qua["vector"]
 
    if ket_qua["confidence"] < 0.9:
        raise HTTPException(400, "Ảnh không đủ rõ để đăng ký, vui lòng chụp lại")
 
    vector_khuon_mat_ma_hoa = crypto_utils.encrypt_vector(vector, FERNET_KEY)
 
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO SinhVien (ma_sv, ho_ten, lop_id, vector_tho, vector_khuon_mat)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (ma_sv, ho_ten, lop_id, np.array(vector), vector_khuon_mat_ma_hoa),
        )
        sinh_vien_id = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()
 
    return {"id": sinh_vien_id, "ma_sv": ma_sv, "confidence": ket_qua["confidence"]}
 
 
@app.post("/api/v1/diem-danh")
def diem_danh(payload: DiemDanhRequest):
    faces = ai_core_mock.process_frame(payload.frame_base64)
    ket_qua = []
    try:
        faces = ai_core_mock.process_frame(payload.frame_base64)
    except ValueError as e:
        # AI trả về lỗi dữ liệu ảnh (base64 hỏng, format sai)
        raise HTTPException(status_code=400, detail=f"Ảnh không hợp lệ: {e}")
    except RuntimeError as e:
        # AI model chưa load, GPU lỗi, timeout...
        raise HTTPException(status_code=503, detail=f"AI service lỗi: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi không xác định từ AI: {e}")
    if not faces:
        return {"so_mat_thay": 0, "ket_qua": []}
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Thu thập tất cả vector của các khuôn mặt
        all_vectors = [np.array(face["vector"], dtype=np.float32) for face in faces]

        # --- Batch query: tìm top-1 match cho TẤT CẢ faces trong 1 lệnh SQL ---
        # Sử dụng UNNEST + LATERAL để tránh N+1 query
        cur.execute(
            """
            WITH face_vecs AS (
                SELECT
                    idx AS face_idx,
                    vec
                FROM unnest(%s::vector[]) WITH ORDINALITY AS t(vec, idx)
            )
            SELECT
                fv.face_idx,
                sv.id,
                sv.ho_ten,
                fv.vec <=> sv.vector_tho AS khoang_cach
            FROM face_vecs fv
            CROSS JOIN LATERAL (
                SELECT id, ho_ten, vector_tho
                FROM SinhVien
                ORDER BY vector_tho <=> fv.vec
                LIMIT 1
            ) sv
            ORDER BY fv.face_idx
            """,
            (all_vectors,),
        )
        Trả về sớm, tránh query DB vô ích khi không có khuôn mặt nàos = cur.fetchall()
        # rows: [(face_idx, sinh_vien_id, ho_ten, khoang_cach), ...]

        # Map kết quả theo thứ tự face
        match_map = {r[0]: (r[1], r[2], r[3]) for r in rows}

        # ---------- Bước 3: Xử lý từng khuôn mặt ----------
        for idx, face in enumerate(faces):
            match = match_map.get(idx + 1)  # WITH ORDINALITY bắt đầu từ 1

            if match is None:
                # Không tìm thấy ứng viên nào (DB rỗng hoặc lỗi)
                ket_qua.append({
                    "nhan_dien": False,
                    "ket_qua": "khong_tim_thay_ung_vien",
                    "khoang_cach": None,
                    "bbox": face["bbox"],
                })
                continue

            sinh_vien_id, ho_ten, khoang_cach = match

            if khoang_cach > NGUONG_KHOP:
                # Có ứng viên nhưng không đủ giống
                ket_qua.append({
                    "nhan_dien": False,
                    "ket_qua": "khong_du_giong",
                    "khoang_cach": round(float(khoang_cach), 4),
                    "bbox": face["bbox"],
                })
                continue

            # --- Nhận diện thành công → ghi vào LichSuDiemDanh ---
            try:
                cur.execute(
                    """
                    INSERT INTO LichSuDiemDanh
                        (sinh_vien_id, ca_hoc_id, trang_thai, is_synced)
                    VALUES (%s, %s, 'co_mat', FALSE)
                    """,
                    (sinh_vien_id, payload.ca_hoc_id),
                )
            except pg_errors.ForeignKeyViolation:
                # sinh_vien_id hoặc ca_hoc_id không tồn tại
                ket_qua.append({
                    "nhan_dien": False,
                    "ket_qua": "loi_tham_chieu_db",
                    "khoang_cach": round(float(khoang_cach), 4),
                    "bbox": face["bbox"],
                    "loi": f"sinh_vien_id={sinh_vien_id} hoac ca_hoc_id={payload.ca_hoc_id} khong hop le",
                })
                continue
            except pg_errors.UniqueViolation:
                # Đã điểm danh rồi (nếu có unique constraint)
                ket_qua.append({
                    "nhan_dien": True,
                    "ket_qua": "da_diem_danh_roi",
                    "sinh_vien_id": sinh_vien_id,
                    "ho_ten": ho_ten,
                    "khoang_cach": round(float(khoang_cach), 4),
                    "bbox": face["bbox"],
                })
                continue

            ket_qua.append({
                "nhan_dien": True,
                "ket_qua": "thanh_cong",
                "sinh_vien_id": sinh_vien_id,
                "ho_ten": ho_ten,
                "khoang_cach": round(float(khoang_cach), 4),
                "bbox": face["bbox"],
            })

        conn.commit()

    except pg_errors.OperationalError as e:
        # Mất kết nối DB, timeout, server down
        conn.rollback()
        raise HTTPException(status_code=503, detail=f"Database khong san sang: {e}")
    except pg_errors.IntegrityError as e:
        # Mất kết nối DB, timeout, server down
        conn.rollback()
        raise HTTPException(status_code=503, detail=f"Database khong san sang: {e}")
    except pg_errors.IntegrityError as e:
        # Vi phạm constraint (NOT NULL, CHECK, ...)
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Loi du lieu: {e}")
    except psycopg2.Error as e:
        # Lỗi PostgreSQL chung
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Loi database: {e}")
    finally:
        conn.close()

    return {"so_mat_thay": len(faces), "ket_qua": ket_qua}
@app.get("/api/v1/lop-hoc")
def danh_sach_lop_hoc():
    """Cho UI đổ vào dropdown chọn lớp ở màn hình 'Bắt đầu ca'."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, ten_lop FROM LopHoc ORDER BY ten_lop")
        return [{"id": r[0], "ten_lop": r[1]} for r in cur.fetchall()]
    finally:
        conn.close()
@app.get("/api/v1/ca-hoc")
def danh_sach_ca_hoc(lop_id: int):
    """Cho UI đổ vào dropdown chọn ca học, sau khi đã chọn lớp ở trên."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, ngay, gio_bat_dau, gio_ket_thuc
            FROM CaHoc WHERE lop_id = %s
            ORDER BY ngay DESC, gio_bat_dau DESC
            """,
            (lop_id,),
        )
        return [
            {"id": r[0], "ngay": str(r[1]), "gio_bat_dau": str(r[2]),
             "gio_ket_thuc": str(r[3]) if r[3] else None}
            for r in cur.fetchall()
        ]
    finally:
        conn.close()
@app.get("/api/v1/diem-danh/{ca_hoc_id}")
def ket_qua_diem_danh(ca_hoc_id: int):
    """Cho màn hình 'Tổng kết' — danh sách đã điểm danh trong 1 ca cụ thể."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT SinhVien.ma_sv, SinhVien.ho_ten, LichSuDiemDanh.trang_thai,
                   LichSuDiemDanh.thoi_gian
            FROM LichSuDiemDanh
            JOIN SinhVien ON LichSuDiemDanh.sinh_vien_id = SinhVien.id
            WHERE LichSuDiemDanh.ca_hoc_id = %s
            ORDER BY LichSuDiemDanh.thoi_gian
            """,
            (ca_hoc_id,),
        )
        danh_sach = [
            {"ma_sv": r[0], "ho_ten": r[1], "trang_thai": r[2], "thoi_gian": str(r[3])}
            for r in cur.fetchall()
        ]
        return {"ca_hoc_id": ca_hoc_id, "so_luong": len(danh_sach), "danh_sach": danh_sach}
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    import pathlib
    # reload=True cần biết thư mục chứa file để watch — dùng app_dir để chạy
    # được dù terminal đang ở thư mục gốc hay cd vào Face-ID-Backend
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        app_dir=str(pathlib.Path(__file__).parent),
    )