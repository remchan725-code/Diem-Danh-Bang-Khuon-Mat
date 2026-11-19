import os
import uuid
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
import psycopg2
from psycopg2 import errors as pg_errors
#Cần import thư viện psycopg2 và module errors để phân loại lỗi PostgreSQL cụ thể
 
import ai_core_client
import crypto_utils
from db import get_connection
 
app = FastAPI(title="He thong diem danh - Backend API")

_default_origins = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173"
_raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", _default_origins)
if os.getenv("FRONTEND_ORIGIN"):
    _raw_origins = f"{_raw_origins},{os.getenv('FRONTEND_ORIGIN')}"
ALLOWED_ORIGINS = list(dict.fromkeys(
    origin.strip().rstrip("/") for origin in _raw_origins.split(",") if origin.strip()
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=os.getenv("CORS_ALLOW_ORIGIN_REGEX") or None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
 
# Key thật PHẢI nạp từ biến môi trường (xem SETUP.md). Fallback ở đây chỉ để
# server chạy được ngay lúc demo/test, không dùng khi triển khai thật.
FERNET_KEY = os.getenv("FERNET_KEY", crypto_utils.generate_key())
 
# Cosine distance càng nhỏ càng giống (0 = giống hệt, 2 = đối lập hoàn toàn).
# Ngưỡng 0.4 là điểm khởi đầu hợp lý cho embedding ArcFace — CẦN tinh chỉnh lại
# bằng thực nghiệm ở Giai đoạn 5 (kiểm thử) với dữ liệu khuôn mặt thật.
NGUONG_KHOP = 0.4
MODEL_VERSION = "insightface_buffalo_l_v1"

ANH_XA_KET_QUA = {
    "thanh_cong": "chap_nhan",
    "da_diem_danh_roi": "chap_nhan",         # vẫn là nhận diện đúng, chỉ là ghi trùng
    "khong_du_giong": "tu_choi",
    "khong_tim_thay_ung_vien": "khong_xac_dinh",
    "loi_tham_chieu_db": "khong_xac_dinh",   # lỗi hệ thống, không tính là 1 quyết định nhận diện thật
    "cho_xac_nhan": "khong_xac_dinh",
}
class DiemDanhRequest(BaseModel):
    ca_hoc_id: int
    frame_base64: str
    device_id : str | None = None
    loai_dot: Literal["dau_gio", "cuoi_gio"] = "dau_gio"
 
@app.post("/api/v1/dang-ky-sinh-vien")
async def dang_ky_sinh_vien(
    ma_sv: str = Form(...),
    ho_ten: str = Form(...),
    lop_id: int = Form(...),
    anh: list[UploadFile] = File(...),
):
    vector, vector_khuon_mat_ma_hoa, confidence = await tao_template_tu_anh(anh)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO SinhVien
                (ma_sv, ho_ten, lop_id, vector_tho, vector_khuon_mat,
                 vector_version, vector_updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            RETURNING id
            """,
            (ma_sv.strip(), ho_ten.strip(), lop_id, vector, vector_khuon_mat_ma_hoa, MODEL_VERSION),
        )
        sinh_vien_id = cur.fetchone()[0]
        conn.commit()
    except pg_errors.UniqueViolation:
        conn.rollback()
        raise HTTPException(409, f"Mã sinh viên '{ma_sv.strip()}' đã tồn tại trong hệ thống")
    except pg_errors.ForeignKeyViolation:
        conn.rollback()
        raise HTTPException(404, f"Không tìm thấy lớp học id={lop_id}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
 
    return {"id": sinh_vien_id, "ma_sv": ma_sv, "so_anh": len(anh), "confidence_trung_binh": confidence}


async def tao_template_tu_anh(anh: list[UploadFile]) -> tuple[np.ndarray, bytes, float]:
    if len(anh) < 1 or len(anh) > 3:
        raise HTTPException(400, "Cần tải lên từ 2 đến 5 ảnh khuôn mặt")
    vectors, confidences = [], []
    for image in anh:
        raw = await image.read()
        if not raw:
            raise HTTPException(400, f"Ảnh {image.filename or ''} bị rỗng")
        result = ai_core_client.register_face(raw)
        if result["face_count"] != 1 or not result["vector"]:
            raise HTTPException(400, f"Ảnh {image.filename or ''} phải có đúng một khuôn mặt")
        if result["confidence"] < 0.9:
            raise HTTPException(400, f"Ảnh {image.filename or ''} không đủ rõ, vui lòng chụp lại")
        vectors.append(np.asarray(result["vector"], dtype=np.float32))
        confidences.append(float(result["confidence"]))
    vector = np.mean(vectors, axis=0)
    norm = np.linalg.norm(vector)
    if not np.isfinite(norm) or norm == 0:
        raise HTTPException(400, "Không thể tạo template khuôn mặt từ các ảnh đã gửi")
    vector = (vector / norm).astype(np.float32)
    encrypted = crypto_utils.encrypt_vector(vector.tolist(), FERNET_KEY)
    return vector, encrypted, float(np.mean(confidences))


@app.put("/api/v1/sinh-vien/{sinh_vien_id}/khuon-mat")
async def cap_nhat_khuon_mat(sinh_vien_id: int, anh: list[UploadFile] = File(...)):
    vector, encrypted, confidence = await tao_template_tu_anh(anh)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE SinhVien
               SET vector_tho = %s, vector_khuon_mat = %s,
                   vector_version = %s, vector_updated_at = CURRENT_TIMESTAMP
               WHERE id = %s RETURNING id""",
            (vector, encrypted, MODEL_VERSION, sinh_vien_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(404, "Không tìm thấy sinh viên")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return {"id": sinh_vien_id, "so_anh": len(anh), "confidence_trung_binh": confidence}

                                                                                                    
@app.delete("/api/v1/sinh-vien/{sinh_vien_id}", status_code=204)
def xoa_sinh_vien(sinh_vien_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM SinhVien WHERE id = %s", (sinh_vien_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, "Không tìm thấy sinh viên")
        cur.execute(
            """SELECT EXISTS (
                   SELECT 1 FROM LichSuDiemDanh WHERE sinh_vien_id = %s
                   UNION ALL
                   SELECT 1 FROM NhatKyXacThuc WHERE sinh_vien_id = %s
               )""",
            (sinh_vien_id, sinh_vien_id),
        )
        if cur.fetchone()[0]:
            raise HTTPException(409, "Sinh viên đã có lịch sử điểm danh/xác thực; không thể xóa vật lý để giữ nguyên dữ liệu kiểm toán")
        cur.execute("DELETE FROM SinhVien WHERE id = %s", (sinh_vien_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
 
def ghi_audit_log(cur, ca_hoc_id, sinh_vien_id, ket_qua_goc, khoang_cach, ly_do=None):
    ket_qua_chuan = ANH_XA_KET_QUA[ket_qua_goc]
    diem = round(1 - khoang_cach / 2, 4) if khoang_cach is not None else None
    cur.execute(
        """
        INSERT INTO NhatKyXacThuc
            (ca_hoc_id, sinh_vien_id, ket_qua, ly_do_tu_choi,
             diem_khuon_mat, model_version, request_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (ca_hoc_id, sinh_vien_id, ket_qua_chuan, ly_do,
         diem, MODEL_VERSION, str(uuid.uuid4())),
    )
@app.post("/api/v1/diem-danh")
def diem_danh(payload: DiemDanhRequest):
    ket_qua = []
    try:
        faces = ai_core_client.process_frame(payload.frame_base64)
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

        cur.execute(
            "SELECT id FROM DotDiemDanh WHERE ca_hoc_id = %s AND loai = %s AND trang_thai = 'mo'",
            (payload.ca_hoc_id, payload.loai_dot),
        )
        dot_row = cur.fetchone()
        if dot_row is None:
            raise HTTPException(409, f"Đợt điểm danh {payload.loai_dot} chưa được giảng viên mở")
        dot_diem_danh_id = dot_row[0]

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
                WHERE lop_id = (SELECT lop_id FROM CaHoc WHERE id = %s)
                ORDER BY vector_tho <=> fv.vec
                LIMIT 1
            ) sv
            ORDER BY fv.face_idx
            """,
            (all_vectors, payload.ca_hoc_id),
        )
        #Trả về sớm, tránh query DB vô ích khi không có khuôn mặt nàos
        rows = cur.fetchall()
        # rows: [(face_idx, sinh_vien_id, ho_ten, khoang_cach), ...]

        # Map kết quả theo thứ tự face
        match_map = {r[0]: (r[1], r[2], r[3]) for r in rows}

        # ---------- Bước 3: Xử lý từng khuôn mặt ----------
        for idx, face in enumerate(faces):
            match = match_map.get(idx + 1)  # WITH ORDINALITY bắt đầu từ 1

            if match is None:
                # Không tìm thấy ứng viên nào (DB rỗng hoặc lỗi)
                ghi_audit_log(cur, payload.ca_hoc_id, None, "khong_tim_thay_ung_vien", None)
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
                ghi_audit_log(cur, payload.ca_hoc_id, sinh_vien_id, "khong_du_giong", khoang_cach)
                ket_qua.append({
                    "nhan_dien": False,
                    "ket_qua": "khong_du_giong",
                    "khoang_cach": round(float(khoang_cach), 4),
                    "bbox": face["bbox"],
                })
                continue

            # Recognition only queues a candidate; the instructor confirms the round.
            cur.execute("SAVEPOINT sp_diem_danh") 
            try:
                cur.execute(
                    """
                    INSERT INTO HangChoDiemDanh (dot_diem_danh_id, sinh_vien_id, request_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (dot_diem_danh_id, sinh_vien_id) DO NOTHING
                    """,
                    (dot_diem_danh_id, sinh_vien_id, str(uuid.uuid4())),
                )
            except pg_errors.ForeignKeyViolation:
                cur.execute("ROLLBACK TO SAVEPOINT sp_diem_danh")   # chỉ hủy việc insert vừa lỗi
                ghi_audit_log(cur, payload.ca_hoc_id, None, "loi_tham_chieu_db", None)
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
                # Student already has a queue entry for this round.
                cur.execute("ROLLBACK TO SAVEPOINT sp_diem_danh")
                ghi_audit_log(cur, payload.ca_hoc_id, sinh_vien_id, "da_diem_danh_roi", None)
                ket_qua.append({
                    "nhan_dien": True,
                    "ket_qua": "da_vao_hang_cho",
                    "sinh_vien_id": sinh_vien_id,
                    "ho_ten": ho_ten,
                    "khoang_cach": round(float(khoang_cach), 4),
                    "bbox": face["bbox"],
                })
                continue
            ghi_audit_log(cur, payload.ca_hoc_id, sinh_vien_id, "cho_xac_nhan", khoang_cach)
            ket_qua.append({
                "nhan_dien": True,
                "ket_qua": "cho_giang_vien_xac_nhan",
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


@app.post("/api/v1/ca-hoc/{ca_hoc_id}/dot-diem-danh/{loai}/mo")
def mo_dot_diem_danh(ca_hoc_id: int, loai: Literal["dau_gio", "cuoi_gio"], giang_vien_id: str | None = None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM CaHoc WHERE id = %s", (ca_hoc_id,))
        if cur.fetchone() is None:
            raise HTTPException(404, "Không tìm thấy ca học")
        cur.execute(
            """INSERT INTO DotDiemDanh (ca_hoc_id, loai, trang_thai, mo_luc, giang_vien_id)
               VALUES (%s, %s, 'mo', CURRENT_TIMESTAMP, %s)
               ON CONFLICT (ca_hoc_id, loai) DO UPDATE
               SET trang_thai = 'mo', mo_luc = CURRENT_TIMESTAMP, dong_luc = NULL,
                   giang_vien_id = EXCLUDED.giang_vien_id
               WHERE DotDiemDanh.trang_thai = 'dong'
               RETURNING id""",
            (ca_hoc_id, loai, giang_vien_id),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(409, "Đợt điểm danh đang mở")
        conn.commit()
        return {"id": row[0], "ca_hoc_id": ca_hoc_id, "loai": loai, "trang_thai": "mo"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@app.get("/api/v1/ca-hoc/{ca_hoc_id}/dot-diem-danh/{loai}/hang-cho")
def lay_hang_cho(ca_hoc_id: int, loai: Literal["dau_gio", "cuoi_gio"]):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT h.id, s.id, s.ma_sv, s.ho_ten, h.queued_at, h.trang_thai
               FROM HangChoDiemDanh h
               JOIN DotDiemDanh d ON d.id = h.dot_diem_danh_id
               JOIN SinhVien s ON s.id = h.sinh_vien_id
               WHERE d.ca_hoc_id = %s AND d.loai = %s
               ORDER BY h.queued_at""",
            (ca_hoc_id, loai),
        )
        return [{"hang_cho_id": r[0], "sinh_vien_id": r[1], "ma_sv": r[2], "ho_ten": r[3],
                 "queued_at": r[4].isoformat(), "trang_thai": r[5]} for r in cur.fetchall()]
    finally:
        conn.close()


@app.post("/api/v1/ca-hoc/{ca_hoc_id}/dot-diem-danh/{loai}/xac-nhan")
def xac_nhan_dot_diem_danh(ca_hoc_id: int, loai: Literal["dau_gio", "cuoi_gio"]):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM DotDiemDanh WHERE ca_hoc_id = %s AND loai = %s AND trang_thai = 'mo' FOR UPDATE",
            (ca_hoc_id, loai),
        )
        dot = cur.fetchone()
        if dot is None:
            raise HTTPException(409, "Đợt điểm danh chưa mở hoặc đã đóng")
        dot_id = dot[0]
        cur.execute(
            """UPDATE HangChoDiemDanh SET trang_thai = 'chap_nhan', quyet_dinh_luc = CURRENT_TIMESTAMP
               WHERE dot_diem_danh_id = %s AND trang_thai = 'cho_xac_nhan'
               RETURNING sinh_vien_id""",
            (dot_id,),
        )
        sinh_vien_ids = [r[0] for r in cur.fetchall()]
        for sinh_vien_id in sinh_vien_ids:
            cur.execute(
                """INSERT INTO LichSuDiemDanh (ca_hoc_id, sinh_vien_id, trang_thai, dau_gio, dau_gio_luc,
                       cuoi_gio, cuoi_gio_luc)
                   VALUES (%s, %s, 'co_mat', %s, CASE WHEN %s = 'dau_gio' THEN CURRENT_TIMESTAMP END,
                       %s, CASE WHEN %s = 'cuoi_gio' THEN CURRENT_TIMESTAMP END)
                   ON CONFLICT (ca_hoc_id, sinh_vien_id) DO UPDATE SET
                       dau_gio = LichSuDiemDanh.dau_gio OR EXCLUDED.dau_gio,
                       dau_gio_luc = COALESCE(LichSuDiemDanh.dau_gio_luc, EXCLUDED.dau_gio_luc),
                       cuoi_gio = LichSuDiemDanh.cuoi_gio OR EXCLUDED.cuoi_gio,
                       cuoi_gio_luc = COALESCE(LichSuDiemDanh.cuoi_gio_luc, EXCLUDED.cuoi_gio_luc)""",
                (ca_hoc_id, sinh_vien_id, loai == "dau_gio", loai, loai == "cuoi_gio", loai),
            )
        cur.execute("UPDATE DotDiemDanh SET trang_thai = 'dong', dong_luc = CURRENT_TIMESTAMP WHERE id = %s", (dot_id,))
        conn.commit()
        return {"ca_hoc_id": ca_hoc_id, "loai": loai, "xac_nhan": len(sinh_vien_ids), "trang_thai": "dong"}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
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
    # được dù terminal đang ở thư mục gốc hay cd vào FaceID-Backend
    uvicorn.run(
        "main:app",
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=True,
        app_dir=str(pathlib.Path(__file__).parent),
    )
