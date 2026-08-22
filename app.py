import os
import sys
import json
import base64
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io

# 1. Thiết lập đường dẫn thư mục hiện tại
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# 2. Import các module xử lý AI (OCR, kiểm tra DDI, giọng nói)
from ocr_engine import process_handwriting_ocr, make_tts_friendly, parse_ocr_json
from gemini_ai import check_drug_interaction
from worker import speech_to_text, text_to_speech, openai_process_message, generate_health_memo

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# QUAN TRỌNG: Tự động lấy Google/Gemini API Key từ biến môi trường của Render/System
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""

if not GOOGLE_API_KEY:
    print("⚠️  Chưa đặt biến môi trường GOOGLE_API_KEY / GEMINI_API_KEY trên Render!")


# ==========================================
# Route 1: Trang chủ giao diện Web chính
# ==========================================
@app.route("/")
def index():
    return render_template("index.html")


# ==========================================
# Route 2: API Xử lý OCR hình ảnh đơn thuốc
# ==========================================
@app.route('/api/ocr', methods=['POST'])
def handle_ocr():
    try:
        file = request.files.get('file') or request.files.get('image')
        
        if not file:
            print(f"❌ [DEBUG] Files received in request: {list(request.files.keys())}")
            return jsonify({'success': False, 'error': 'No file found under key "file" or "image"'}), 400
            
        from PIL import Image
        image = Image.open(io.BytesIO(file.read()))

        # Lấy key từ biến môi trường đã khai báo ở trên
        api_key = GOOGLE_API_KEY

        raw_text = process_handwriting_ocr(image, api_key)
        parsed_drugs = parse_ocr_json(raw_text)
        tts_text = make_tts_friendly(raw_text)

        return jsonify({
            'success': True,
            'raw_text': raw_text,
            'drugs': parsed_drugs,
            'tts_text': tts_text
        })

    except Exception as e:
        print(f"❌ Server Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==========================================
# Route 3: API Kiểm tra kỵ thuốc (DDI)
# ==========================================
@app.route("/api/check-ddi", methods=["POST"])
def handle_ddi():
    try:
        data = request.json or {}
        old_drugs = data.get("old_drugs", "")
        new_drugs = data.get("new_drugs", "")

        result = check_drug_interaction(old_drugs, new_drugs, GOOGLE_API_KEY)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        print(f"❌ Lỗi kiểm tra DDI: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# Route 4: Speech-to-Text (ghi âm người dùng -> văn bản)
# ==========================================
@app.route('/speech-to-text', methods=['POST'])
def speech_to_text_route():
    print("Processing speech-to-text...")
    audio_binary = request.data
    text = speech_to_text(audio_binary)

    return app.response_class(
        response=json.dumps({'text': text}),
        status=200,
        mimetype='application/json'
    )


# ==========================================
# Route 5: Xử lý hội thoại (GPT) + trả lời bằng giọng nói (TTS)
# ==========================================
@app.route('/process-message', methods=['POST'])
def process_message_route():
    data = request.get_json() or {}
    user_message = data.get('userMessage', '')
    voice = data.get('voice', 'vi-VN-HoaiMyNeural')

    print('User message:', user_message)

    openai_response_text = openai_process_message(user_message)
    openai_response_text = os.linesep.join([s for s in openai_response_text.splitlines() if s])

    openai_response_speech = text_to_speech(openai_response_text, voice)
    openai_response_speech = base64.b64encode(openai_response_speech).decode('utf-8')

    return app.response_class(
        response=json.dumps({
            "openaiResponseText": openai_response_text,
            "openaiResponseSpeech": openai_response_speech,
        }),
        status=200,
        mimetype='application/json'
    )

@app.route("/api/generate-memo", methods=["POST"])
def handle_generate_memo():
    try:
        data = request.json or {}
        conversation = data.get("conversation", "")

        if not conversation:
            return jsonify({"success": False, "error": "Chưa có nội dung hội thoại!"}), 400

        memo_data = generate_health_memo(conversation)

        if memo_data:
            return jsonify({"success": True, "memo": memo_data})
        else:
            return jsonify({"success": False, "error": "Không thể trích xuất Memo từ AI."}), 500

    except Exception as e:
        print(f"❌ Lỗi API Memo: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 Đang khởi động Server PillGuard AI (OCR + DDI + Giọng nói) "
          "tại http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000, host='0.0.0.0')