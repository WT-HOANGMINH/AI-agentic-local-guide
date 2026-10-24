
/* =====================================
   DA NANG GUIDE - CHAT AI
===================================== */

document.addEventListener('DOMContentLoaded', async () => {

  // KIEM TRA DANG NHAP
  // Ho tro Google OAuth va tai khoan Demo
  if (!(await protect())) {
    return;
  }

  // LAY CAC THANH PHAN GIAO DIEN
  const messages = $('#chat-messages');
  const form = $('#chat-form');
  const input = $('#chat-input');
  const send = $('#send-chat');

  if (!messages || !form || !input || !send) {
    return;
  }

  let isSending = false;

  // =====================================
  // HIEN THI TIN NHAN
  // =====================================

  function appendMessage(who, text) {

    const div = document.createElement('div');

    div.className =
      'bubble ' + (who === 'user' ? 'user' : 'bot');

    div.textContent = text;

    messages.appendChild(div);

    messages.scrollTop = messages.scrollHeight;

    return div;
  }

  // =====================================
  // LOI CHAO BAN DAU
  // =====================================

  appendMessage(
    'bot',
    'Xin chào! Mình là trợ lý du lịch DaNang Guide. ' +
    'Bạn muốn khám phá địa điểm, tìm món ăn ngon ' +
    'hay lên lịch trình du lịch Đà Nẵng?'
  );

  // =====================================
  // GUI CAU HOI DEN CHAT AI
  // =====================================

  async function ask(question) {

    const text = String(question || '').trim();

    if (!text || isSending) {
      return;
    }

    isSending = true;

    // Hien thi cau hoi nguoi dung
    appendMessage('user', text);

    input.value = '';
    input.disabled = true;
    send.disabled = true;

    // Hien thi trang thai dang tra loi
    const typing = appendMessage(
      'bot',
      'Đang tìm câu trả lời cho bạn...'
    );

    try {

      // Goi API Chat AI cua du an
      const reply = await API.chat(text);

      typing.textContent =
        reply || 'AI chưa trả về nội dung.';

    } catch (error) {

      typing.textContent =
        'Không thể kết nối Chat AI: ' +
        (error.message || 'Có lỗi xảy ra.');

    } finally {

      isSending = false;

      input.disabled = false;
      send.disabled = false;

      messages.scrollTop = messages.scrollHeight;

      input.focus();
    }
  }

  // =====================================
  // GUI TIN NHAN BANG NUT HOAC ENTER
  // =====================================

  form.addEventListener('submit', event => {

    event.preventDefault();

    ask(input.value);
  });

  // =====================================
  // XU LY CAC CAU HOI GOI Y
  // =====================================

  $$('[data-prompt]').forEach(button => {

    button.addEventListener('click', () => {

      ask(button.dataset.prompt);
    });

  });

});
