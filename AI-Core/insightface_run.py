import base64
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import List
from insightface.app import FaceAnalysis

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Smart Attendance AI Core Service",
    description="Microservice trích xuất Vector khuôn mặt phục vụ điểm danh thông minh",
    version="1.0.0"
)

# Biến toàn cục chứa Model AI (Singleton pattern để tránh load lại model mỗi request)
app_ai = None

@app.on_event("startup")
def load_ai_model():
    global app_ai
    # Ưu tiên chạy GPU CUDA cho RTX 2060 Super, tự động fallback về CPU nếu thiếu driver
    app_ai = FaceAnalysis(
        name="buffalo_l",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
    )
    # Kích thước det_size=(640, 640) cân bằng hoàn hảo giữa nhận diện xa và tốc độ
    app_ai.prepare(ctx_id=0, det_size=(640, 640))
    print("[AI Core] Đã tải thành công mô hình InsightFace (ArcFace + SCRFD)!")

# Schema định dạng dữ liệu Base64 gửi lên từ Client
class FrameRequest(BaseModel):
    image_base64: str

def format_face_object(face) -> dict:
    """Hàm bổ trợ chuẩn hóa dữ liệu Face của InsightFace sang kiểu Native Python (JSON Serializable)"""
    return {
        "bbox": face.bbox.astype(int).tolist(),  # Tọa độ khung [x1, y1, x2, y2]
        "confidence": float(face.det_score),     # Độ tin cậy phát hiện mặt (0.0 - 1.0)
        "embedding": face.embedding.tolist()    # Vector đặc trưng 512 chiều kiểu float
    }

@app.post("/api/v1/register-face", summary="Trích xuất Vector từ ảnh thẻ 3x4")
async def register_face(file: UploadFile = File(...)):
    """
    Endpoint nhận file ảnh nhị phân (UploadFile) từ form đăng ký sinh viên.
    Tự động cắt mặt, căn chỉnh và trả về 1 Vector 512 chiều tốt nhất.
    """
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(status_code=400, detail="File ảnh tải lên không đúng định dạng hoặc bị lỗi")

    # Tiến hành phát hiện và trích xuất
    faces = app_ai.get(img)

    if len(faces) == 0:
        return {
            "success": False,
            "message": "Không tìm thấy khuôn mặt nào trong ảnh",
            "face_count": 0,
            "faces": []
        }

    # Trường hợp ảnh thẻ có nhiễu nhiều mặt, chọn mặt có score cao nhất
    best_face = max(faces, key=lambda x: x.det_score)

    return {
        "success": True,
        "message": "Trích xuất vector ảnh gốc thành công",
        "face_count": 1,
        "faces": [format_face_object(best_face)]
    }

@app.post("/api/v1/process-frame", summary="Xử lý frame hình webcam thời gian thực")
async def process_frame(payload: FrameRequest):
    """
    Endpoint nhận chuỗi ảnh Base64 từ luồng Webcam của Frontend.
    Trả về danh sách tất cả các mặt xuất hiện trong khung hình kèm BBox và Vector 512-D.
    """
    try:
        # Cắt bỏ tiền tố Data URL (ví dụ: 'data:image/jpeg;base64,') nếu client gửi thừa
        encoded_data = payload.image_base64.split(",")[-1]
        image_bytes = base64.b64decode(encoded_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise HTTPException(status_code=400, detail="Không thể giải mã chuỗi Base64 thành hình ảnh")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Lỗi định dạng Base64: {str(e)}")

    # Trích xuất toàn bộ khuôn mặt trong frame
    faces = app_ai.get(img)
    processed_faces = [format_face_object(f) for f in faces]

    return {
        "success": True,
        "face_count": len(processed_faces),
        "faces": processed_faces
    }

if __name__ == "__main__":
    import os
    import uvicorn
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run(
        "insightface_run:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        app_dir=current_dir
    )
