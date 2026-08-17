# File: ocr_engine.py
from PIL import Image
from google import genai

def process_handwriting_ocr(image: Image.Image, api_key: str) -> str:
    """Chương trình nhận diện chữ viết tay qua Gemini API."""
    client = genai.Client(api_key=api_key)

    prompt = (
        "Bạn là một chuyên gia nhận dạng chữ viết tay (OCR).\n"
        "Hãy đọc chính xác văn bản trong hình ảnh này.\n"
        "Chữ viết có thể nguệch ngoạc, hãy dùng ngữ cảnh tiếng Việt để suy đoán từ chính xác.\n"
        "Chỉ trả về văn bản đã đọc được, không thêm bất kỳ diễn giải nào khác.\n"
        "Hãy viết theo định dạng sau:\n"
        "[Tên người viết (nếu có)], [Tên bệnh nhân (nếu có)], [Ngày tháng (nếu có)], [Nội dung chữ viết].\n"
        "(Nếu không có tên hay ngày tháng, chỉ cần trả về nội dung chữ viết.)\n"
        "[Số thứ tự] - [Tên thuốc] || [Liều lượng] || [Cách dùng] || [Ghi chú (nếu có)]\n"
        "*Lưu ý: Không thêm bất kỳ ký tự đặc biệt nào khác ngoài các ký tự trong nội dung chữ viết (Chẳng hạn như dấu '*' để tô đậm). Ngoài ra cứ hết 1 dòng chữ viết tay thì xuống 2 dòng mới, giữa các dòng phải có 1 dòng trống."
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[prompt, image]
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