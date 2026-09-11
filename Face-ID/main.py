import os
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
 
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
    conn = get_connection()
    try:
        cur = conn.cursor()
        for face in faces:
            vector = face["vector"]
 
            # Toán tử <=> của pgvector: tính cosine distance ngay trong SQL,
            # không cần kéo hết vector về Python rồi tính vòng lặp for.
            cur.execute(
                """
                SELECT id, ho_ten, vector_tho <=> %s AS khoang_cach
                FROM SinhVien
                ORDER BY khoang_cach ASC
                LIMIT 1
                """,
                (np.array(vector),),
            )
            row = cur.fetchone()
 
            if row is None or row[2] > NGUONG_KHOP:
                ket_qua.append({
                    "nhan_dien": False,
                    "khoang_cach": round(row[2], 4) if row else None,
                })
                continue
 
            sinh_vien_id, ho_ten, khoang_cach = row
            cur.execute(
                """
                INSERT INTO LichSuDiemDanh (sinh_vien_id, ca_hoc_id, trang_thai, is_synced)
                VALUES (%s, %s, 'co_mat', FALSE)
                """,
                (sinh_vien_id, payload.ca_hoc_id),
            )
            ket_qua.append({
                "nhan_dien": True,
                "sinh_vien_id": sinh_vien_id,
                "ho_ten": ho_ten,
                "khoang_cach": round(khoang_cach, 4),
            })
        conn.commit()
    finally:
        conn.close()
 
    return {"so_mat_thay": len(faces), "ket_qua": ket_qua}
 
