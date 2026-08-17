from PIL import Image
import streamlit as st
import sys
from pathlib import Path

# Đảm bảo Python luôn tìm thấy file ocr_engine.py trong cùng thư mục
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import bộ não AI từ file ocr_engine.py
try:
    from ocr_engine import process_handwriting_ocr, make_tts_friendly
except Exception as e:
    raise ImportError(f"Không thể import 'ocr_engine'. Đảm bảo file ocr_engine.py nằm chung thư mục với Run.py. Lỗi gốc: {e}")

# Gán API Key trực tiếp (Không dùng st.secrets để tránh lỗi thiếu file secrets.toml)
GOOGLE_API_KEY = "AQ.Ab8RN6JS2BuAcpiVI2oZqe1shdLIKA8dnoq4l7IAckE5o30T7g"

# ==========================================
# CẤU HÌNH GIAO DIỆN (STREAMLIT UI)
# ==========================================
st.set_page_config(page_title="App Đọc Chữ Viết Tay", page_icon="✍️")
st.title("✍️ Trợ Lý Đọc Chữ Viết Tay AI")

uploaded_file = st.file_uploader("Chọn ảnh chứa chữ viết tay...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Ảnh bạn đã tải lên", use_container_width=True)

    if st.button("🤖 Bắt đầu đọc chữ"):
        with st.spinner("AI đang phân tích..."):
            try:
                raw_result = process_handwriting_ocr(image, GOOGLE_API_KEY)
                tts_result = make_tts_friendly(raw_result)

                st.success("Xử lý thành công!")
                st.markdown("### 📄 Văn bản OCR gốc")
                st.text_area(label="", value=raw_result, height=150)
                
                st.markdown("### 🔊 Câu thoại cho TTS (Đọc cho người già)")
                st.info(tts_result)
            except Exception as e:
                st.error(f"Lỗi khi xử lý: {e}")
#Cách chạy code:
#Bước 1: Mở Terminal VS Code (Shortcut: Ctrl + `)
#Bước 2:Chạy cd "d:\Chi Hung\NCKH\Intel" (đường dẫn đến thư mục chứa file Run.py)
#Bước 3: Chạy lệnh: streamlit run Run.py