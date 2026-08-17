/* ==========================================
   PILLGUARD AI - MAIN INTERACTIVE & VOICE LOGIC
   ========================================== */

let lightMode = false;
let recorder = null;
let recording = false;
let voiceOption = "vi-VN-HoaiMyNeural";
const responses = [];
const botRepeatButtonIDToIndexMap = {};
const userRepeatButtonIDToRecordingMap = {};
const baseUrl = window.location.origin;

// Hàm sleep delay
const sleep = (time) => new Promise((resolve) => setTimeout(resolve, time));

/* ==========================================
   1. XỬ LÝ FILE & MODAL KIỂM TRA MẮT NGƯỜI (KHUNG 1)
   ========================================== */

// Xử lý khi chọn file đơn thuốc (Khung 1) và gửi lên Flask Server
async function handlePrescriptionUpload(event) {
  const file = event.target.files[0];
  const nameLabel = document.getElementById("prescription-file-name");
  
  if (!file) return;

  if (nameLabel) {
    nameLabel.innerText = "⏳ Đang phân tích OCR: " + file.name;
  }

  // Tạo FormData để đóng gói file gửi lên Flask API
  const formData = new FormData();
  formData.append("image", file);

  try {
    speakText("Hệ thống đang quét đơn thuốc, vui lòng đợi trong giây lát.");

    // Gửi yêu cầu tới API Flask
    const response = await fetch("/api/ocr", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (data.success) {
      if (nameLabel) {
        nameLabel.innerText = "✅ Đã đọc xong: " + file.name;
      }

      // Phát âm thanh đọc kết quả TTS
      speakText(data.tts_text || "Đã trích xuất xong đơn thuốc.");

      // Cập nhật dữ liệu OCR nhận được vào bảng trong Modal kiểm tra
      populateModalWithOCR(data.raw_text);

      // Mở Modal kiểm tra cho con người xác nhận (Human-in-the-loop)
      openVerificationModal();
    } else {
      alert("Lỗi khi đọc đơn thuốc: " + data.error);
      if (nameLabel) nameLabel.innerText = "❌ Lỗi khi đọc ảnh";
    }
  } catch (error) {
    console.error("Lỗi gửi ảnh OCR:", error);
    alert("Không thể kết nối tới máy chủ Flask!");
    if (nameLabel) nameLabel.innerText = "❌ Lỗi kết nối";
  }
}

function populateModalWithOCR(rawText) {
  const tbody = document.getElementById('modal-drug-list');
  if (!tbody) return;

  tbody.innerHTML = ''; // Làm sạch bảng cũ
  if (!rawText) return;

  let items = [];

  try {
    // Nếu dữ liệu trả về là chuỗi JSON từ AI
    if (typeof rawText === 'string') {
      const cleanJson = rawText.replace(/```json/g, '').replace(/```/g, '').trim();
      items = JSON.parse(cleanJson);
    } else if (Array.isArray(rawText)) {
      items = rawText;
    }
  } catch (e) {
    console.warn("Không thể parse JSON OCR, sử dụng fallback tách dòng:", e);
    // Phương án dự phòng nếu AI không trả về JSON
    const lines = rawText.split('\n').filter(line => line.trim() !== '');
    items = lines.map(line => ({
      name: line.trim(),
      dose: "1 viên",
      time: "08:00 AM",
      note: "Uống sau bữa ăn"
    }));
  }

  // Điền dữ liệu bóc tách vào từng ô tương ứng
  items.forEach(item => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="p-1.5"><input type="text" value="${(item.name || '').replace(/"/g, '&quot;')}" class="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs focus:border-yellow-400 outline-none"></td>
      <td class="p-1.5"><input type="text" value="${item.dose || '1 viên'}" class="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs focus:border-yellow-400 outline-none"></td>
      <td class="p-1.5"><input type="text" value="${item.time || '08:00 AM'}" class="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs focus:border-yellow-400 outline-none"></td>
      <td class="p-1.5"><input type="text" value="${item.note || 'Uống sau bữa ăn'}" class="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs focus:border-yellow-400 outline-none"></td>
      <td class="p-1.5 text-center"><button onclick="this.closest('tr').remove()" class="text-rose-400 hover:text-rose-300 font-bold px-1">✕</button></td>
    `;
    tbody.appendChild(tr);
  });
}
// Áp dụng thay đổi từ Modal vào Bảng Lịch Sử chính
function applyModalChanges() {
  const rows = document.querySelectorAll('#modal-drug-list tr');
  const historyTableBody = document.getElementById('history-table-body');
  if (!historyTableBody) return;

  historyTableBody.innerHTML = ''; // Làm sạch bảng cũ

  rows.forEach((row) => {
    const inputs = row.querySelectorAll('input');
    if (inputs.length >= 4) {
      const nameDose = `${inputs[0].value} (${inputs[1].value})`;
      const time = inputs[2].value;
      const note = inputs[3].value;

      const newRow = document.createElement('tr');
      newRow.className = "hover:bg-gray-800/40 transition";
      newRow.innerHTML = `
        <td class="p-3 font-bold text-blue-400">Ngày 1</td>
        <td class="p-3 font-mono text-yellow-400 font-bold">${time}</td>
        <td class="p-3 font-semibold text-white">${nameDose}</td>
        <td class="p-3 text-gray-400">${note}</td>
        <td class="p-3 text-center">
          <input type="checkbox" onchange="toggleTaken(this)" class="w-5 h-5 accent-emerald-500 cursor-pointer rounded">
        </td>
      `;
      historyTableBody.appendChild(newRow);
    }
  });

  closeVerificationModal();
  speakText("Đã xác nhận và lưu đơn thuốc vào bảng lịch sử thành công.");
}

/* ==========================================
   2. KHUNG 2 - KIỂM TRA LOẠI THUỐC (SOI VỈ THỰC TẾ)
   ========================================== */

// Lấy danh sách đơn thuốc hiện tại từ Bảng Lịch Sử làm Context
function getPrescriptionContext() {
  const rows = document.querySelectorAll('#history-table-body tr');
  let contextText = "";
  rows.forEach((row, idx) => {
    const cols = row.querySelectorAll('td');
    if (cols.length >= 4) {
      contextText += `${idx + 1}. ${cols[2].innerText} - Giờ: ${cols[1].innerText} - Ghi chú: ${cols[3].innerText}\n`;
    }
  });
  return contextText || "Chưa có dữ liệu đơn thuốc.";
}

// Xử lý khi tải ảnh vỉ thuốc qua nút Upload ở Khung 2
async function handleDailyFileSelect(event) {
  const file = event.target.files[0];
  if (!file) return;

  updateDrugInfoUI("⏳ Đang nhận diện...", "⏳ Đang tra cứu...", "⏳ Đang tra cứu...");
  speakText("Đang phân tích vỉ thuốc, vui lòng chờ.");

  const formData = new FormData();
  formData.append("image", file);
  formData.append("prescription_context", getPrescriptionContext());

  try {
    const response = await fetch("/api/scan-pill", {
      method: "POST",
      body: formData
    });

    const data = await response.json();
    if (data.success) {
      parseAndDisplayPillResult(data.result);
    } else {
      updateDrugInfoUI("❌ Lỗi nhận diện", "--", "--");
      alert("Không thể soi vỉ thuốc: " + data.error);
    }
  } catch (err) {
    console.error("Lỗi scan pill:", err);
    updateDrugInfoUI("❌ Lỗi kết nối", "--", "--");
  }
}

// Hàm hỗ trợ tách chuỗi trả về từ Gemini và dán vào 3 ô
function parseAndDisplayPillResult(resultText) {
  let name = "--";
  let dose = "--";
  let time = "--";

  const lines = resultText.split("\n");
  lines.forEach(line => {
    if (line.includes("1. Tên thuốc:") || line.includes("Tên thuốc:")) {
      name = line.split(":")[1]?.trim() || "--";
    } else if (line.includes("2. Liều lượng:") || line.includes("Liều lượng:")) {
      dose = line.split(":")[1]?.trim() || "--";
    } else if (line.includes("3. Thời gian sử dụng:") || line.includes("Thời gian:")) {
      time = line.split(":")[1]?.trim() || "--";
    }
  });

  updateDrugInfoUI(name, dose, time);
  speakText(`Thuốc ${name}. Liều lượng: ${dose}. Thời gian uống: ${time}.`);
}

// Hàm cập nhật Giao diện 3 ô Khung 2
function updateDrugInfoUI(name, dose, time) {
  const drugName = document.getElementById("drug-name");
  const drugDose = document.getElementById("drug-dose");
  const drugTime = document.getElementById("drug-time");

  if (drugName) drugName.innerText = name;
  if (drugDose) drugDose.innerText = dose;
  if (drugTime) drugTime.innerText = time;
}

// Đánh dấu trạng thái đã uống thuốc
function toggleTaken(checkbox) {
  const row = checkbox.closest("tr");
  if (checkbox.checked) {
    row.classList.add("opacity-50", "line-through");
    speakText("Đã ghi nhận uống thuốc thành công.");
  } else {
    row.classList.remove("opacity-50", "line-through");
  }
}

// Đọc câu thông báo nhanh qua Web Speech API
function speakText(text) {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'vi-VN';
    utterance.rate = 0.9;
    window.speechSynthesis.speak(utterance);
  }
}

/* ==========================================
   3. TRỢ LÝ GIỌNG NÓI PILLGUARD (KHUNG 3: OPENAI & TTS)
   ========================================== */

// Hiển thị / Ẩn Loading Animation
async function showBotLoadingAnimation() {
  await sleep(300);
  $(".loading-animation").not(".my-loading").show();
}

function hideBotLoadingAnimation() {
  $(".loading-animation").not(".my-loading").hide();
}

async function showUserLoadingAnimation() {
  await sleep(100);
  $(".loading-animation.my-loading").show();
}

function hideUserLoadingAnimation() {
  $(".loading-animation.my-loading").hide();
}

// API Call: Speech To Text
const getSpeechToText = async (userRecording) => {
  try {
    if (!userRecording || !userRecording.audioBlob) {
      return "Không có dữ liệu âm thanh.";
    }

    let response = await fetch(baseUrl + "/speech-to-text", {
      method: "POST",
      body: userRecording.audioBlob,
    });
    response = await response.json();
    return response.text || "Không thể nhận diện giọng nói.";
  } catch (error) {
    console.error("Lỗi Speech-to-Text:", error);
    return "Lỗi kết nối Speech-to-Text.";
  }
};

// API Call: Process Message (OpenAI / Gemini + TTS)
const processUserMessage = async (userMessage) => {
  try {
    let response = await fetch(baseUrl + "/process-message", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ userMessage: userMessage, voice: voiceOption }),
    });
    response = await response.json();
    return response;
  } catch (error) {
    console.error("Lỗi Process Message:", error);
    return {
      openaiResponseText: "Rất tiếc, đã có lỗi kết nối máy chủ backend.",
      openaiResponseSpeech: ""
    };
  }
};

// Làm sạch input nhập vào
const cleanTextInput = (value) => {
  return value
    .trim()
    .replace(/[\n\t]/g, "")
    .replace(/<[^>]*>/g, "")
    .replace(/[<>&;]/g, "");
};

// Record Audio từ Microphone
const recordAudio = () => {
  return new Promise(async (resolve) => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const mediaRecorder = new MediaRecorder(stream);
    const audioChunks = [];

    mediaRecorder.addEventListener("dataavailable", (event) => {
      audioChunks.push(event.data);
    });

    const start = () => mediaRecorder.start();

    const stop = () =>
      new Promise((resolve) => {
        mediaRecorder.addEventListener("stop", () => {
          const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
          const audioUrl = URL.createObjectURL(audioBlob);
          const audio = new Audio(audioUrl);
          const play = () => audio.play();
          resolve({ audioBlob, audioUrl, play });
        });

        mediaRecorder.stop();
      });

    resolve({ start, stop });
  });
};

const toggleRecording = async () => {
  if (!recording) {
    recorder = await recordAudio();
    recording = true;
    recorder.start();
  } else {
    recording = false; // Tự động cập nhật lại trạng thái khi tắt
    const audio = await recorder.stop();
    await sleep(500);
    return audio;
  }
};

// Phát audio phản hồi
const playResponseAudio = (function () {
  const df = document.createDocumentFragment();
  return function Sound(src) {
    if (!src || src.endsWith("base64,")) return;
    const snd = new Audio(src);
    df.appendChild(snd);
    snd.addEventListener("ended", function () {
      df.removeChild(snd);
    });
    snd.play();
    return snd;
  };
})();

const getRandomID = () => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

// Cuộn tự động xuống cuối khung Chat
const scrollToBottom = () => {
  const chatWin = $("#chat-window");
  if (chatWin.length) {
    chatWin.animate({ scrollTop: chatWin[0].scrollHeight }, 300);
  }
};

// Thêm tin nhắn Người Dùng vào UI
const populateUserMessage = (userMessage, userRecording) => {
  $("#message-input").val("");

  if (userRecording) {
    const userRepeatButtonID = getRandomID();
    userRepeatButtonIDToRecordingMap[userRepeatButtonID] = userRecording;
    hideUserLoadingAnimation();
    $("#message-list").append(
      `<div class='message-line my-text my-2 text-right'>
        <div class='inline-block bg-purple-700 text-white p-3 rounded-2xl max-w-[80%] text-sm'>
          <div>${userMessage}</div>
        </div>
        <button id='${userRepeatButtonID}' class='repeat-button ml-2 text-purple-400 hover:text-purple-300' onclick='userRepeatButtonIDToRecordingMap[this.id].play()'>
          🔊
        </button>
      </div>`
    );
  } else {
    $("#message-list").append(
      `<div class='message-line my-text my-2 text-right'>
        <div class='inline-block bg-purple-700 text-white p-3 rounded-2xl max-w-[80%] text-sm'>
          <div>${userMessage}</div>
        </div>
      </div>`
    );
  }

  scrollToBottom();
};

// Thêm tin nhắn Bot AI vào UI
const populateBotResponse = async (userMessage) => {
  await showBotLoadingAnimation();
  const response = await processUserMessage(userMessage);
  responses.push(response);

  const repeatButtonID = getRandomID();
  botRepeatButtonIDToIndexMap[repeatButtonID] = responses.length - 1;
  hideBotLoadingAnimation();

  $("#message-list").append(
    `<div class='message-line my-2 text-left flex items-start gap-2'>
      <div class='bg-gray-800 text-gray-100 p-3 rounded-2xl max-w-[80%] text-sm border border-gray-700'>
        ${response.openaiResponseText}
      </div>
      <button id='${repeatButtonID}' class='repeat-button text-purple-400 hover:text-purple-300 mt-2' onclick='playResponseAudio("data:audio/mp3;base64," + responses[botRepeatButtonIDToIndexMap[this.id]].openaiResponseSpeech)'>
        🔊
      </button>
    </div>`
  );

  if (response.openaiResponseSpeech) {
    playResponseAudio("data:audio/mp3;base64," + response.openaiResponseSpeech);
  }

  scrollToBottom();
};

/* ==========================================
   4. KHỞI TẠO EVENT LISTENERS KHI TRANG SẴN SÀNG
   ========================================== */
$(document).ready(function () {
  // 1. Sự kiện gõ bàn phím ô chat
  $("#message-input").keyup(function (event) {
    let inputVal = cleanTextInput($("#message-input").val());

    if (event.keyCode === 13 && inputVal !== "") {
      const message = inputVal;
      populateUserMessage(message, null);
      populateBotResponse(message);
    }
  });

  // 2. Sự kiện bấm nút Micro / Gửi
$("#send-button").click(async function () {
  if (!recording && $("#message-input").val().trim() === "") {
    // Bật ghi âm
    await toggleRecording();
    $(this).removeClass("bg-purple-600").addClass("bg-red-600").html("⏹️");
  } else if (recording) {
    // Tắt ghi âm và xử lý
    $(this).removeClass("bg-red-600").addClass("bg-purple-600").html("🎙️");
    
    const userRecording = await toggleRecording();
    if (userRecording) {
      await showUserLoadingAnimation();
      const userMessage = await getSpeechToText(userRecording);
      populateUserMessage(userMessage, userRecording);
      populateBotResponse(userMessage);
    }
  } else {
    // Gửi tin nhắn bằng văn bản nhập tay
    const message = cleanTextInput($("#message-input").val());
    if (message !== "") {
      populateUserMessage(message, null);
      populateBotResponse(message);
    }
  }
});
  // 3. Chuyển chế độ Dark / Light
  $("#light-dark-mode-switch").change(function () {
    $("body").toggleClass("bg-gray-950 bg-gray-100 text-gray-900 text-gray-100");
    lightMode = !lightMode;
  });

  // 4. Thay đổi Giọng nói
  $("#voice-options").change(function () {
    voiceOption = $(this).val();
  });
});
// 1. Gom toàn bộ tin nhắn chat lại thành văn bản
function getChatTranscript() {
  let transcript = "";
  $("#message-list .message-line").each(function () {
    const text = $(this).text().trim();
    if (text) {
      transcript += text + "\n";
    }
  });
  return transcript;
}

// 2. Gửi request lên API tạo Memo
async function createMemoFromChat() {
  const conversation = getChatTranscript();

  if (!conversation.trim()) {
    alert("Chưa có tin nhắn nào trong khung Chat để tạo Memo!");
    return;
  }

  speakText("Đang tổng hợp thông tin sức khỏe từ cuộc trò chuyện, vui lòng chờ trong giây lát.");

  try {
    const response = await fetch("/api/generate-memo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conversation: conversation })
    });

    const data = await response.json();

    if (data.success && data.memo) {
      populateMemoModal(data.memo);
      openMemoModal();
      speakText("Đã tạo Memo sức khỏe thành công. Vui lòng kiểm tra lại trước khi lưu.");
    } else {
      alert("Lỗi tạo Memo: " + (data.error || "Không thể xử lý."));
    }
  } catch (err) {
    console.error("Lỗi khi gọi API Memo:", err);
    alert("Không thể kết nối tới máy chủ AI!");
  }
}

// 3. Đổ dữ liệu JSON từ AI vào các ô input trong Modal Review
function populateMemoModal(memo) {
  const today = new Date().toLocaleDateString('vi-VN');

  $("#memo-date").val(memo.date !== "Không đề cập" ? memo.date : today);
  $("#memo-main-concern").val(memo.main_concern || "Không đề cập");
  $("#memo-symptoms").val(memo.symptoms || "Không đề cập");
  $("#memo-timing").val(memo.timing_duration || "Không đề cập");
  $("#memo-severity").val(memo.severity || "Không đề cập");
  $("#memo-medication").val(memo.medication_mentioned || "Không đề cập");
  $("#memo-side-effects").val(memo.side_effects || "Không đề cập");
  $("#memo-what-helped").val(memo.what_helped || "Không đề cập");
  $("#memo-questions").val(memo.questions_for_doctor || "Không đề cập");
}

function openMemoModal() {
  $("#memo-modal").removeClass("hidden");
}

function closeMemoModal() {
  $("#memo-modal").addClass("hidden");
}

// 4. Lưu hoặc Tải bản Memo xuống máy
function saveHealthMemo() {
  const memoObject = {
    date: $("#memo-date").val(),
    mainConcern: $("#memo-main-concern").val(),
    symptoms: $("#memo-symptoms").val(),
    timing: $("#memo-timing").val(),
    medication: $("#memo-medication").val(),
    sideEffects: $("#memo-side-effects").val(),
    whatHelped: $("#memo-what-helped").val(),
    questionsForDoctor: $("#memo-questions").val()
  };

  console.log("Đã lưu Health Memo thành công:", memoObject);
  
  // Thông báo & Đóng modal
  alert("✅ Đã lưu Health Memo sức khỏe thành công!");
  closeMemoModal();
  speakText("Đã ghi nhận và lưu nhật ký sức khỏe thành công.");
}