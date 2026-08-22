# File: gemini_ai.py
import os
from google import genai

def check_drug_interaction(old_drugs: str, new_drugs: str, api_key: str = None) -> str:
    if not api_key:
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

    if not api_key:
        return "Chưa cấu hình API Key nên không thể kiểm tra tương tác thuốc."

    if not old_drugs.strip() or not new_drugs.strip():
        return "Vui lòng cung cấp đầy đủ thông tin thuốc đang dùng và thuốc mới để kiểm tra."

    prompt = f"""Bạn là dược sĩ lâm sàng AI hỗ trợ người cao tuổi tại Việt Nam.

Thuốc đang dùng: {old_drugs}
Thuốc mới định dùng thêm: {new_drugs}

Trả lời ngắn gọn, dễ hiểu bằng tiếng Việt, đúng cấu trúc sau (không dùng ký tự đặc biệt như *, #):

Mức độ an toàn: [AN TOÀN / CẦN THẬN TRỌNG / NGUY HIỂM - KHÔNG NÊN DÙNG CHUNG]
Lý do: [1-2 câu ngắn gọn]
Khuyến nghị: [nên uống cách nhau bao lâu, có cần hỏi bác sĩ/dược sĩ không]

Nếu không chắc chắn về mức độ an toàn, LUÔN chọn mức CẦN THẬN TRỌNG và khuyên hỏi dược sĩ."""

    try:
        client = genai.Client(api_key=str(api_key).strip())
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"Lỗi kiểm tra DDI: {e}")
        return f"Xin lỗi, hiện tại AI không thể kiểm tra tương tác thuốc. Lỗi: {e}"
