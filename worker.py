import os
import asyncio
import tempfile
from openai import OpenAI
import edge_tts

# Khởi tạo OpenAI Client

openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    print("⚠️  Chưa đặt biến môi trường OPENAI_API_KEY!")

# Khởi tạo OpenAI Client chuẩn
client = OpenAI(api_key=openai_api_key)

def speech_to_text(audio_binary):
    """
    Dùng OpenAI Whisper API để chuyển âm thanh nhận được từ micro thành văn bản.
    Không cần chạy Docker Watson STT nữa.
    """
    if not audio_binary:
        return ""
    
    try:
        # Lưu file audio tạm thời để truyền vào OpenAI Whisper
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_audio:
            temp_audio.write(audio_binary)
            temp_audio_path = temp_audio.name

        # Gọi Whisper API
        with open(temp_audio_path, "rb") as audio_file:
            transcript_response = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="vi"  # Hoặc "en" tùy theo ngôn ngữ sử dụng
            )
        
        # Xóa file tạm
        os.remove(temp_audio_path)
        return transcript_response.text

    except Exception as e:
        print(f"Lỗi khi chuyển Speech-to-Text: {e}")
        return ""


def openai_process_message(user_message):
    """
    Gửi câu hỏi tới GPT-4o-mini để xử lý thông tin y tế / tư vấn thuốc.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Bạn là PillGuard AI, trợ lý y tế thông minh tư vấn về thuốc. Trả lời ngắn gọn, chính xác và dễ hiểu bằng tiếng Việt."
                },
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Lỗi OpenAI GPT: {e}")
        return "Xin lỗi, hiện tại hệ thống AI đang bận. Bạn vui lòng thử lại sau."


def text_to_speech(text, voice="vi-VN-HoaiMyNeural"):
    """
    Dùng Microsoft Edge TTS để tạo âm thanh giọng đọc tiếng Việt cực mượt.
    Trả về dữ liệu âm thanh dạng binary MP3 cho server.
    """
    try:
        async def _generate_audio():
            communicate = edge_tts.Communicate(text, voice)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3:
                temp_mp3_path = temp_mp3.name
            
            await communicate.save(temp_mp3_path)
            
            with open(temp_mp3_path, "rb") as f:
                data = f.read()
                
            os.remove(temp_mp3_path)
            return data

        # Chạy hàm bất đồng bộ edge-tts
        audio_data = asyncio.run(_generate_audio())
        return audio_data

    except Exception as e:
        print(f"Lỗi Text-to-Speech (Edge-TTS): {e}")
        return b""

def openai_process_message(user_message):
    # Set the prompt for OpenAI Api
    prompt = "Act like a personal assistant. You can respond to questions, translate sentences, summarize news, and give recommendations. Keep responses concise - 2 to 3 sentences maximum."
    # Call the OpenAI Api to process our prompt
    openai_response = client.chat.completions.create(
        model="gpt-5-nano", 
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message}
        ],
        max_completion_tokens=2500
    )
    print("openai response:", openai_response)
    # Parse the response to get the response message for our prompt
    response_text = openai_response.choices[0].message.content
    return response_text

def openai_process_message(user_message):
    # Set the prompt for OpenAI Api
    prompt = "Act like a personal assistant. You can respond to questions, translate sentences, summarize news, and give recommendations. Keep responses concise - 2 to 3 sentences maximum."
    # Call the OpenAI Api to process our prompt
    openai_response = client.chat.completions.create(
        model="gpt-5-nano", 
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message}
        ],
        max_completion_tokens=2500
    )
    print("openai response:", openai_response)
    # Parse the response to get the response message for our prompt
    response_text = openai_response.choices[0].message.content
    return response_text
import json

def generate_health_memo(conversation_text):
    """
    Trích xuất nhật ký sức khỏe (Health Memo) từ đoạn hội thoại chat.
    """
    # Sửa .trim() thành .strip()
    if not conversation_text or not conversation_text.strip():
        return None

    prompt = f"""
Bạn là trợ lý y tế chuyên trích xuất thông tin sức khỏe thành Memo ngắn gọn.
Hãy trích xuất thông tin từ đoạn hội thoại dưới đây thành định dạng JSON với các khóa (keys) tiếng Việt:

JSON Output Format:
{{
  "date": "Ngày xảy ra (Ví dụ: 16/08/2026 hoặc 'Không đề cập')",
  "main_concern": "Vấn đề chính / Bận tâm lớn nhất",
  "symptoms": "Các triệu chứng xuất hiện",
  "timing_duration": "Thời điểm bị & Thời gian kéo dài",
  "severity": "Mức độ nghiêm trọng",
  "medication_mentioned": "Thuốc được đề cập / Đã uống",
  "side_effects": "Tác dụng phụ có thể có",
  "what_helped": "Cách xử lý / Việc đã làm giúp dịu bớt",
  "questions_for_doctor": "Câu hỏi cần hỏi Bác sĩ hoặc Người chăm sóc",
  "follow_up": "Theo dõi tiếp theo"
}}

NGUYÊN TẮC AN TOÀN BẮT BUỘC (CRITICAL SAFETY RULES):
1. KHÔNG TỰ CHẨN ĐOÁN BỆNH.
2. KHÔNG TỰ Ý ĐỀ XUẤT ĐỔI LIỀU HOẶC NGỪNG THUỐC.
3. KHÔNG TỰ NGHĨ RA THÔNG TIN KHÔNG CÓ TRONG HỘI THOẠI.
4. Nếu thông tin nào không xuất hiện trong chat, điền chính xác từ: "Không đề cập".
5. Ngôn ngữ sử dụng: Tiếng Việt ngắn gọn, khách quan.

Đoạn hội thoại:
\"\"\"
{conversation_text}
\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "Bạn là AI trích xuất dữ liệu Health Memo an toàn và chính xác."},
                {"role": "user", "content": prompt}
            ]
        )
        memo_json = json.loads(response.choices[0].message.content)
        return memo_json
    except Exception as e:
        print(f"Lỗi trích xuất Health Memo: {e}")
        return None
