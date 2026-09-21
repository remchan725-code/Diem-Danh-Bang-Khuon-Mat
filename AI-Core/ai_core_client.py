import httpx
 
AI_CORE_BASE_URL = "http://localhost:8001"  # đổi theo địa chỉ thật khi A deploy
 
 
def register_face(image_bytes: bytes) -> dict:
    """Gọi POST /api/v1/register-face của A.
    Trả về dict PHẲNG {"vector", "confidence", "bbox"} — đúng format ai_core_mock.py."""
    response = httpx.post(
        f"{AI_CORE_BASE_URL}/api/v1/register-face",
        files={"file": ("anh.jpg", image_bytes, "image/jpeg")},
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
 
    if not data["faces"]:
        # main.py hiện kiểm tra confidence < 0.9 để từ chối ảnh không rõ mặt —
        # trả confidence=0.0 để đi đúng nhánh xử lý đó, không cần sửa main.py.
        return {"vector": [], "confidence": 0.0, "bbox": None}
 
    face = data["faces"][0]
    return {
        "vector": face["embedding"],
        "confidence": face["confidence"],
        "bbox": face["bbox"],
    }
 
 
def process_frame(base64_image: str) -> list:
    """Gọi POST /api/v1/process-frame của A.
    Trả về MẢNG TRẦN [{"vector", "confidence", "bbox"}, ...] — đúng format ai_core_mock.py."""
    response = httpx.post(
        f"{AI_CORE_BASE_URL}/api/v1/process-frame",
        json={"image_base64": base64_image},
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()
 
    return [
        {"vector": f["embedding"], "confidence": f["confidence"], "bbox": f["bbox"]}
        for f in data["faces"]
    ]
 