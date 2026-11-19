import requests
import os
 
BASE_URL = os.getenv("BACKEND_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def lay_danh_sach_lop() -> list:
    r = requests.get(f"{BASE_URL}/api/v1/lop-hoc", timeout=5)
    r.raise_for_status()
    return r.json()
 
 
def lay_danh_sach_ca(lop_id: int) -> list:
    r = requests.get(f"{BASE_URL}/api/v1/ca-hoc", params={"lop_id": lop_id}, timeout=5)
    r.raise_for_status()
    return r.json()
 
 
def goi_diem_danh(ca_hoc_id: int, frame_base64: str, loai_dot: str = "dau_gio") -> dict:
    r = requests.post(
        f"{BASE_URL}/api/v1/diem-danh",
        json={"ca_hoc_id": ca_hoc_id, "frame_base64": frame_base64, "loai_dot": loai_dot},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def mo_dot_diem_danh(ca_hoc_id: int, loai: str, giang_vien_id: str | None = None) -> dict:
    r = requests.post(
        f"{BASE_URL}/api/v1/ca-hoc/{ca_hoc_id}/dot-diem-danh/{loai}/mo",
        params={"giang_vien_id": giang_vien_id} if giang_vien_id else None,
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def lay_hang_cho_diem_danh(ca_hoc_id: int, loai: str) -> list:
    r = requests.get(
        f"{BASE_URL}/api/v1/ca-hoc/{ca_hoc_id}/dot-diem-danh/{loai}/hang-cho",
        timeout=5,
    )
    r.raise_for_status()
    return r.json()


def xac_nhan_dot_diem_danh(ca_hoc_id: int, loai: str) -> dict:
    r = requests.post(
        f"{BASE_URL}/api/v1/ca-hoc/{ca_hoc_id}/dot-diem-danh/{loai}/xac-nhan",
        timeout=5,
    )
    r.raise_for_status()
    return r.json()
 
 
def lay_ket_qua_diem_danh(ca_hoc_id: int) -> dict:
    r = requests.get(f"{BASE_URL}/api/v1/diem-danh/{ca_hoc_id}", timeout=5)
    r.raise_for_status()
    return r.json()
 
