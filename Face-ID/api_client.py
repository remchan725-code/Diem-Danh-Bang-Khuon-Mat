import requests
 
BASE_URL = "http://localhost:8000"
 
 
def lay_danh_sach_lop() -> list:
    r = requests.get(f"{BASE_URL}/api/v1/lop-hoc", timeout=5)
    r.raise_for_status()
    return r.json()
 
 
def lay_danh_sach_ca(lop_id: int) -> list:
    r = requests.get(f"{BASE_URL}/api/v1/ca-hoc", params={"lop_id": lop_id}, timeout=5)
    r.raise_for_status()
    return r.json()
 
 
def goi_diem_danh(ca_hoc_id: int, frame_base64: str) -> dict:
    r = requests.post(
        f"{BASE_URL}/api/v1/diem-danh",
        json={"ca_hoc_id": ca_hoc_id, "frame_base64": frame_base64},
        timeout=5,
    )
    r.raise_for_status()
    return r.json()
 
 
def lay_ket_qua_diem_danh(ca_hoc_id: int) -> dict:
    r = requests.get(f"{BASE_URL}/api/v1/diem-danh/{ca_hoc_id}", timeout=5)
    r.raise_for_status()
    return r.json()
 