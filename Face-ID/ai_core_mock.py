import random
import numpy as np

def _random_unit_vector(dim: int = 512) -> list:
    """Vector ngẫu nhiên đã chuẩn hóa độ dài 1 — giống thật, vì embedding khuôn
    mặt (ArcFace/InsightFace) luôn là vector đơn vị (L2-normalized)."""
    v = np.random.normal(size=dim)
    v = v / np.linalg.norm(v)
    return v.tolist()
 
 
def register_face(image_bytes: bytes) -> dict:
    """Mô phỏng POST /api/v1/register-face.
    Ảnh 3x4 đăng ký luôn có sẵn 1 khuôn mặt rõ, nên luôn trả về confidence cao."""
    return {
        "vector": _random_unit_vector(),
        "confidence": round(random.uniform(0.95, 0.999), 3),
        "bbox": [50, 40, 210, 230],
    }
 
 
def process_frame(base64_image: str) -> list:
    """Mô phỏng POST /api/v1/process-frame.
    Trả về MẢNG (có thể rỗng) — đúng hành vi thật khi khung hình không có mặt nào,
    hoặc có nhiều sinh viên cùng lúc trong khung hình."""
    so_mat = random.choice([0, 1, 1, 1, 2])  # phần lớn khung hình thấy đúng 1 mặt
    return [
        {
            "vector": _random_unit_vector(),
            "confidence": round(random.uniform(0.85, 0.99), 3),
            "bbox": [30 + i * 150, 40, 190 + i * 150, 230],
        }
        for i in range(so_mat)
    ]