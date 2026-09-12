from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",  # Thay key của bạn
)

def tao_loi_chao_diem_danh(ten_sinh_vien: str) -> str:
    """Tạo câu chào tự động độc đáo khi quét mặt thành công."""
    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-exp:free",
        messages=[
            {
                "role": "system", 
                "content": "Bạn là trợ lý điểm danh lớp học thân thiện. Hãy tạo 1 câu chúc ngắn dưới 15 từ."
            },
            {
                "role": "user", 
                "content": f"Sinh viên {ten_sinh_vien} vừa điểm danh thành công."
            }
        ],
        max_tokens=60
    )
    return response.choices[0].message.content

def tom_tat_bao_cao(du_lieu_diem_danh: str) -> str:
    """Tóm tắc danh sách điểm danh cho giảng viên."""
    response = client.chat.completions.create(
        model="google/gemini-2.0-flash-exp:free",
        messages=[
            {"role": "user", "content": f"Tóm tắt tình hình đi học từ dữ liệu này: {du_lieu_diem_danh}"}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content