"""Mock API client tạm thời cho chế độ demo giao diện FaceID-Client (không cần Backend/DB thật).

Kích hoạt chủ động bằng cờ `--mock` hoặc biến môi trường `APP_MOCK=true`.
Xóa file này sau khi hoàn tất buổi demo hoặc khi chạy tích hợp với Backend thật.
"""

from __future__ import annotations

import base64
import threading
from datetime import date, datetime, timezone

import cv2
import numpy as np

BASE_URL = "mock://demo-client"

_LOCK = threading.Lock()

_LOP_HOC = [
    {"id": 1, "ten_lop": "D21CQCN01-N (Demo)"},
    {"id": 2, "ten_lop": "D21CQCN02-N (Demo)"},
]

_TODAY = date.today().isoformat()

_CA_HOC_THEO_LOP: dict[int, list[dict]] = {
    1: [
        {"id": 101, "lop_id": 1, "ngay": _TODAY, "gio_bat_dau": "07:30:00", "gio_ket_thuc": "09:30:00"},
        {"id": 102, "lop_id": 1, "ngay": _TODAY, "gio_bat_dau": "13:30:00", "gio_ket_thuc": "15:30:00"},
    ],
    2: [
        {"id": 201, "lop_id": 2, "ngay": _TODAY, "gio_bat_dau": "09:45:00", "gio_ket_thuc": "11:45:00"},
    ],
}

_SINH_VIEN_THEO_LOP: dict[int, list[dict]] = {
    1: [
        {"id": 1, "ma_sv": "B21DCCN001", "ho_ten": "Nguyễn Hồng Nam"},
        {"id": 2, "ma_sv": "B21DCCN002", "ho_ten": "Nguyễn Minh Đức"},
        {"id": 3, "ma_sv": "B21DCCN003", "ho_ten": "Trần Thị Mai Anh"},
        {"id": 4, "ma_sv": "B21DCCN004", "ho_ten": "Lê Hoàng Phúc"},
    ],
    2: [
        {"id": 5, "ma_sv": "B21DCCN005", "ho_ten": "Phạm Gia Huy"},
        {"id": 6, "ma_sv": "B21DCCN006", "ho_ten": "Vũ Ngọc Linh"},
        {"id": 7, "ma_sv": "B21DCCN007", "ho_ten": "Đặng Quốc Bảo"},
    ],
}

# Trạng thái trong RAM cho buổi demo
_TRANG_THAI_DOT: dict[tuple[int, str], str] = {}
_HANG_CHO: dict[tuple[int, str], list[dict]] = {}
_LICH_SU_DIEM_DANH: dict[int, dict[int, dict]] = {}
_BO_DEM_QUET: dict[tuple[int, str], int] = {}
_NEXT_HANG_CHO_ID = 1

try:
    _FACE_CASCADE = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    if _FACE_CASCADE.empty():
        _FACE_CASCADE = None
except Exception:
    _FACE_CASCADE = None


def _tim_lop_cua_ca(ca_hoc_id: int) -> int:
    for lop_id, ds_ca in _CA_HOC_THEO_LOP.items():
        if any(ca["id"] == ca_hoc_id for ca in ds_ca):
            return lop_id
    return 1


def _phat_hien_bbox_tu_frame(frame_base64: str) -> list[list[int]]:
    """Dùng Haar Cascade cục bộ để bám theo khuôn mặt thật trên webcam (nếu thấy)."""
    try:
        raw = base64.b64decode(frame_base64.split(",")[-1])
        arr = np.frombuffer(raw, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return [[180, 90, 460, 390]]

        h, w = img.shape[:2]
        if _FACE_CASCADE is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = _FACE_CASCADE.detectMultiScale(
                gray, scaleFactor=1.15, minNeighbors=5, minSize=(70, 70)
            )
            if len(faces) > 0:
                return [
                    [int(x), int(y), int(x + fw), int(y + fh)]
                    for (x, y, fw, fh) in faces
                ]
        return [[int(w * 0.30), int(h * 0.16), int(w * 0.70), int(h * 0.82)]]
    except Exception:
        return [[180, 90, 460, 390]]


def lay_danh_sach_lop() -> list:
    return list(_LOP_HOC)


def lay_danh_sach_ca(lop_id: int) -> list:
    return [
        {
            "id": ca["id"],
            "ngay": ca["ngay"],
            "gio_bat_dau": ca["gio_bat_dau"],
            "gio_ket_thuc": ca["gio_ket_thuc"],
        }
        for ca in _CA_HOC_THEO_LOP.get(lop_id, [])
    ]


def mo_dot_diem_danh(ca_hoc_id: int, loai: str, giang_vien_id: str | None = None) -> dict:
    with _LOCK:
        key = (ca_hoc_id, loai)
        if _TRANG_THAI_DOT.get(key) == "mo":
            raise RuntimeError("Đợt điểm danh đang mở.")
        _TRANG_THAI_DOT[key] = "mo"
        _HANG_CHO.setdefault(key, [])
        _BO_DEM_QUET[key] = 0
        return {
            "id": ca_hoc_id * 10 + (1 if loai == "dau_gio" else 2),
            "ca_hoc_id": ca_hoc_id,
            "loai": loai,
            "trang_thai": "mo",
        }


def goi_diem_danh(ca_hoc_id: int, frame_base64: str, loai_dot: str = "dau_gio") -> dict:
    global _NEXT_HANG_CHO_ID

    with _LOCK:
        key = (ca_hoc_id, loai_dot)
        if _TRANG_THAI_DOT.get(key) != "mo":
            ten_dot = "đầu giờ" if loai_dot == "dau_gio" else "cuối giờ"
            raise RuntimeError(
                f"Đợt điểm danh {ten_dot} chưa mở — bấm 'Mở lượt điểm danh' để bắt đầu nhận diện."
            )

        bboxes = _phat_hien_bbox_tu_frame(frame_base64)
        lop_id = _tim_lop_cua_ca(ca_hoc_id)
        ds_sv = _SINH_VIEN_THEO_LOP.get(lop_id, [])
        hang_cho = _HANG_CHO.setdefault(key, [])
        da_trong_hang_cho = {item["sinh_vien_id"] for item in hang_cho}

        step = _BO_DEM_QUET.get(key, 0)
        _BO_DEM_QUET[key] = step + 1

        ket_qua = []
        for idx, bbox in enumerate(bboxes):
            chua_vao = [sv for sv in ds_sv if sv["id"] not in da_trong_hang_cho]

            # Sau khi quét đủ sinh viên lớp, mô phỏng 1 khung hình người lạ bị từ chối (khung đỏ)
            if not chua_vao and step % 3 == 0 and idx == 0:
                ket_qua.append(
                    {
                        "nhan_dien": False,
                        "ket_qua": "khong_du_giong",
                        "khoang_cach": 0.9412,
                        "bbox": bbox,
                    }
                )
                continue

            if chua_vao:
                sv = chua_vao[0]
                da_trong_hang_cho.add(sv["id"])
                hang_cho.append(
                    {
                        "hang_cho_id": _NEXT_HANG_CHO_ID,
                        "sinh_vien_id": sv["id"],
                        "ma_sv": sv["ma_sv"],
                        "ho_ten": sv["ho_ten"],
                        "queued_at": datetime.now(timezone.utc).isoformat(),
                        "trang_thai": "cho_xac_nhan",
                    }
                )
                _NEXT_HANG_CHO_ID += 1
                trang_thai_kq = "cho_giang_vien_xac_nhan"
            else:
                sv = ds_sv[(step + idx) % len(ds_sv)]
                trang_thai_kq = "da_vao_hang_cho"

            khoang_cach = round(0.082 + (sv["id"] % 5) * 0.014, 4)
            ket_qua.append(
                {
                    "nhan_dien": True,
                    "ket_qua": trang_thai_kq,
                    "sinh_vien_id": sv["id"],
                    "ho_ten": sv["ho_ten"],
                    "khoang_cach": khoang_cach,
                    "bbox": bbox,
                }
            )

        return {"so_mat_thay": len(bboxes), "ket_qua": ket_qua}


def lay_hang_cho_diem_danh(ca_hoc_id: int, loai: str) -> list:
    with _LOCK:
        return [dict(item) for item in _HANG_CHO.get((ca_hoc_id, loai), [])]


def xac_nhan_dot_diem_danh(ca_hoc_id: int, loai: str) -> dict:
    with _LOCK:
        key = (ca_hoc_id, loai)
        if _TRANG_THAI_DOT.get(key) != "mo":
            raise RuntimeError("Đợt điểm danh chưa mở hoặc đã đóng.")

        hang_cho = _HANG_CHO.get(key, [])
        cho_xac_nhan = [item for item in hang_cho if item["trang_thai"] == "cho_xac_nhan"]
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lich_su_ca = _LICH_SU_DIEM_DANH.setdefault(ca_hoc_id, {})

        for item in cho_xac_nhan:
            item["trang_thai"] = "chap_nhan"
            sv_id = item["sinh_vien_id"]
            record = lich_su_ca.get(sv_id)
            if record is None:
                lich_su_ca[sv_id] = {
                    "ma_sv": item["ma_sv"],
                    "ho_ten": item["ho_ten"],
                    "dau_gio": loai == "dau_gio",
                    "cuoi_gio": loai == "cuoi_gio",
                    "thoi_gian": now_str,
                }
            else:
                if loai == "dau_gio":
                    record["dau_gio"] = True
                if loai == "cuoi_gio":
                    record["cuoi_gio"] = True
                record["thoi_gian"] = now_str

        _TRANG_THAI_DOT[key] = "dong"
        return {
            "ca_hoc_id": ca_hoc_id,
            "loai": loai,
            "xac_nhan": len(cho_xac_nhan),
            "trang_thai": "dong",
        }


def lay_ket_qua_diem_danh(ca_hoc_id: int) -> dict:
    with _LOCK:
        lich_su_ca = _LICH_SU_DIEM_DANH.get(ca_hoc_id, {})
        danh_sach = []
        for record in lich_su_ca.values():
            if record["dau_gio"] and record["cuoi_gio"]:
                trang_thai = "co_mat (đầu + cuối giờ)"
            elif record["dau_gio"]:
                trang_thai = "co_mat (đầu giờ)"
            elif record["cuoi_gio"]:
                trang_thai = "co_mat (cuối giờ)"
            else:
                trang_thai = "co_mat"
            danh_sach.append(
                {
                    "ma_sv": record["ma_sv"],
                    "ho_ten": record["ho_ten"],
                    "trang_thai": trang_thai,
                    "thoi_gian": record["thoi_gian"],
                }
            )
        return {
            "ca_hoc_id": ca_hoc_id,
            "so_luong": len(danh_sach),
            "danh_sach": danh_sach,
        }
