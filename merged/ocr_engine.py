# File: ocr_engine.py
from PIL import Image
import google.genai as genai


def process_handwriting_ocr(image: Image.Image, api_key: str) -> str:
    """Chương trình nhận diện chữ viết tay qua Gemini API."""
    if not api_key:
        raise RuntimeError(
            "Thiếu GEMINI_API_KEY. Hãy đặt biến môi trường GEMINI_API_KEY trước khi chạy server."
        )

    # QUAN TRỌNG: dùng đúng api_key được truyền vào, không gắn cứng key trong file.
    client = genai.Client(api_key="AQ.Ab8RN6Lebg-Ojlqw6sgbFEZtRIbEpFKOawv_DWnChs6_NRQkcA")

    prompt = (
        "Bạn là một chuyên gia nhận dạng chữ viết tay (OCR).\n"
        "Hãy đọc chính xác văn bản trong hình ảnh này.\n"
        "Chữ viết có thể nguệch ngoạc, hãy dùng ngữ cảnh tiếng Việt để suy đoán từ chính xác.\n"
        "Chỉ trả về văn bản đã đọc được, không thêm bất kỳ diễn giải nào khác.\n"
        """Định dạng JSON yêu cầu:
        [
            {
                "name": "Tên thuốc & Hàm lượng",
                "dose": "Liều lượng (VD: 1 viên)",
                "time": "Thời gian uống (VD: 08:00 AM hoặc Sáng - Tối)",
                "note": "Hướng dẫn (VD: Uống sau bữa ăn)"
            }
        ]
        Cần đảm bảo chỉ trả về JSON hợp lệ, không kèm văn bản giải thích.
        """

    )

    # Ghi chú: kiểm tra lại tên model hiện có trong tài khoản Google AI Studio của bạn
    # (ví dụ "gemini-2.5-flash") — "gemini-3.6-flash" có thể không tồn tại / không khả dụng.
    response = client.models.generate_content(
        model="gemini-3.7-flash",
        contents=[prompt, image],
    )
    return response.text


def make_tts_friendly(raw_text: str) -> str:
    """Chuyển đổi văn bản OCR thô thành câu nói rõ ràng cho người già nghe TTS."""
    lines = raw_text.strip().split("\n")
    spoken_sentences = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if "||" in line:
            parts = [p.strip() for p in line.split("||")]
            ten_thuoc = parts[0].lstrip("0123456789- ").strip()
            lieu_luong = parts[1] if len(parts) > 1 else ""
            cach_dung = parts[2] if len(parts) > 2 else ""
            ghi_chu = parts[3] if len(parts) > 3 else ""

            sentence = f"Thuốc {ten_thuoc}. Liều dùng: {lieu_luong}. Cách dùng: {cach_dung}."
            if ghi_chu:
                sentence += f" Ghi chú: {ghi_chu}."
            spoken_sentences.append(sentence)
        else:
            clean_line = line.replace("-", "").strip()
            spoken_sentences.append(clean_line)

    return " ... ".join(spoken_sentences)
