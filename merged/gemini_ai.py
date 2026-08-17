# File: gemini_ai.py
# Module này BỊ THIẾU trong bản tổng hợp — app.py có import nó nhưng file chưa tồn tại,
# nên /api/check-ddi sẽ báo lỗi "NameError: check_drug_interaction is not defined".
# Đây là bản dựng tối thiểu để chạy được; CẦN dược sĩ/bác sĩ kiểm duyệt nội dung
# trước khi dùng thật cho người dùng cao tuổi, vì đây chỉ là gợi ý từ AI, không phải
# tra cứu từ nguồn dữ liệu y khoa chính thức.

from google import genai


def check_drug_interaction(old_drugs: str, new_drugs: str, api_key: str) -> str:
    """
    Kiểm tra tương tác thuốc (DDI) giữa thuốc đang dùng và thuốc mới bằng Gemini.
    Trả về văn bản cảnh báo bằng tiếng Việt, dễ hiểu cho người già.

    LƯU Ý AN TOÀN: Đây là kiểm tra bằng AI ngôn ngữ, KHÔNG được đối chiếu với
    cơ sở dữ liệu dược lý chính thức. Không nên dùng làm căn cứ y khoa duy nhất —
    luôn khuyến khích người dùng hỏi lại dược sĩ/bác sĩ với các trường hợp
    CẦN THẬN TRỌNG hoặc NGUY HIỂM.
    """
    if not api_key:
        return "Chưa cấu hình GEMINI_API_KEY nên không thể kiểm tra tương tác thuốc."

    if not old_drugs.strip() or not new_drugs.strip():
        return "Vui lòng cung cấp đầy đủ thông tin thuốc đang dùng và thuốc mới để kiểm tra."

    client = genai.Client(api_key="AQ.Ab8RN6JS2BuAcpiVI2oZqe1shdLIKA8dnoq4l7IAckE5o30T7g")

    prompt = f"""Bạn là dược sĩ lâm sàng AI hỗ trợ người cao tuổi tại Việt Nam.

Thuốc đang dùng: {old_drugs}
Thuốc mới định dùng thêm: {new_drugs}

Trả lời ngắn gọn, dễ hiểu bằng tiếng Việt, đúng cấu trúc sau (không dùng ký tự đặc biệt như *, #):

Mức độ an toàn: [AN TOÀN / CẦN THẬN TRỌNG / NGUY HIỂM - KHÔNG NÊN DÙNG CHUNG]
Lý do: [1-2 câu ngắn gọn]
Khuyến nghị: [nên uống cách nhau bao lâu, có cần hỏi bác sĩ/dược sĩ không]

Nếu không chắc chắn về mức độ an toàn, LUÔN chọn mức CẦN THẬN TRỌNG và khuyên hỏi dược sĩ,
không được tự suy đoán là AN TOÀN khi không đủ căn cứ."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
        )
        return response.text.strip()
    except Exception as e:
        print(f"Lỗi kiểm tra DDI: {e}")
        return "Xin lỗi, hiện tại AI không thể kiểm tra tương tác thuốc. Vui lòng hỏi dược sĩ hoặc bác sĩ trực tiếp."
