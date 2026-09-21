import base64
import os

import httpx


AI_CORE_BASE_URL = os.getenv("AI_CORE_BASE_URL", "http://127.0.0.1:8001")


def register_face(image_bytes: bytes) -> dict:
    response = httpx.post(
        f"{AI_CORE_BASE_URL}/api/v1/register-face",
        files={"file": ("face.jpg", image_bytes, "image/jpeg")},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    if not data.get("faces"):
        return {"vector": [], "confidence": 0.0, "bbox": None}

    face = data["faces"][0]
    return {
        "vector": face["embedding"],
        "confidence": face["confidence"],
        "bbox": face["bbox"],
    }


def process_frame(base64_image: str) -> list:
    encoded_data = base64_image.split(",")[-1]
    response = httpx.post(
        f"{AI_CORE_BASE_URL}/api/v1/process-frame",
        json={"image_base64": encoded_data},
        timeout=15.0,
    )
    response.raise_for_status()
    data = response.json()
    return [
        {"vector": face["embedding"], "confidence": face["confidence"], "bbox": face["bbox"]}
        for face in data.get("faces", [])
    ]