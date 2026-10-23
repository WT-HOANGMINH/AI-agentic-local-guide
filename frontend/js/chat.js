
/* =====================================
   DA NANG GUIDE - CHAT AI
===================================== */

document.addEventListener('DOMContentLoaded', () => {

  // Kiem tra dang nhap
  if (!protect()) return;

  const messages = $('#chat-messages');
  const form = $('#chat-form');
  const input = $('#chat-input');
  const send = $('#send-chat');

  if (!messages || !form || !input || !send) return;

  let isSending = false;

  // Hien thi tin nhan
  function appendMessage(who, text) {

    const div = document.createElement('div');

    div.className =
      'bubble ' + (who === 'user' ? 'user' : 'bot');

    div.textContent = text;

    messages.appendChild(div);

    messages.scrollTop = messages.scrollHeight;

    return div;
  }

  // Loi chao
  appendMessage(
    'bot',
    'Xin chào! Mình là trợ lý du lịch DaNang Guide. ' +
    'Bạn muốn khám phá địa điểm, tìm món ăn ngon ' +
    'hay lên lịch trình du lịch Đà Nẵng?'
  );

  // Gui cau hoi den AI
  async function ask(question) {

    const text = String(question || '').trim();

    if (!text || isSending) return;

    isSending = true;

    appendMessage('user', text);

    input.value = '';
    input.disabled = true;
    send.disabled = true;

    const typing = appendMessage(
      'bot',
      'Đang tìm câu trả lời cho bạn...'
    );

    try {

      // Goi API Chat AI
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

  // Gui cau hoi bang nut Gui hoac Enter
  form.addEventListener('submit', event => {

    event.preventDefault();

    ask(input.value);
  });

  // Xu ly cac cau hoi goi y
  $$('[data-prompt]').forEach(button => {

    button.addEventListener('click', () => {

      ask(button.dataset.prompt);
    });

  });

});
