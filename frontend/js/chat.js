/* =====================================
   DA NANG GUIDE - CHAT AI
   Hien thi tung buoc "suy nghi" that cua AI, roi hien cau tra loi tung chu.
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

    // Bong bong tra loi: phan "cac buoc suy nghi" + phan van ban
    const bubble = appendMessage('bot', '');
    const stepsEl = document.createElement('div');
    const textEl = document.createElement('span');
    const suggestionsEl = document.createElement('div');
    suggestionsEl.className = 'dg-chat-suggestions';

    const waiting = document.createElement('div');
    waiting.className = 'dg-step';
    waiting.textContent = 'Đang suy nghĩ…';
    stepsEl.appendChild(waiting);

    bubble.append(stepsEl, textEl, suggestionsEl);
    bubble.classList.add('streaming');

    try {

      if (typeof API.chatStream === 'function') {

        await API.chatStream(text, {

          onStep: step => {
            if (waiting.parentNode) waiting.remove();
            const line = document.createElement('div');
            line.className = 'dg-step';
            line.textContent = '• ' + step;
            stepsEl.appendChild(line);
            messages.scrollTop = messages.scrollHeight;
          },

          onToken: token => {
            if (waiting.parentNode) waiting.remove();
            textEl.textContent += token;
            messages.scrollTop = messages.scrollHeight;
          },

          onResult: result => {
            if (waiting.parentNode) waiting.remove();
            if (result.text && !textEl.textContent) {
              textEl.textContent = result.text;
            }
            (result.links || []).forEach(link => {
              const anchor = document.createElement('a');
              anchor.className = 'dg-chat-link';
              anchor.href = link.url;
              anchor.target = '_blank';
              anchor.rel = 'noopener noreferrer';
              anchor.textContent = `🗺️ ${link.label}`;
              bubble.insertBefore(anchor, suggestionsEl);
            });
            const multi = result.suggestion_mode === 'multi';
            const picked = new Map();
            const choices = result.suggestions || [];
            let submit;
            choices.forEach(suggestion => {
              if (!suggestion.label || !suggestion.message) return;
              const button = document.createElement('button');
              button.type = 'button';
              button.className = 'dg-chat-suggestion';
              button.textContent = suggestion.label;
              if (multi && !suggestion.exclusive) {
                button.setAttribute('role', 'checkbox');
                button.setAttribute('aria-checked', 'false');
                button.addEventListener('click', () => {
                  if (picked.has(suggestion.id)) {
                    picked.delete(suggestion.id);
                  } else {
                    picked.set(suggestion.id, suggestion.message);
                  }
                  button.setAttribute(
                    'aria-checked',
                    String(picked.has(suggestion.id))
                  );
                  submit.disabled = picked.size === 0;
                });
              } else {
                button.addEventListener('click', () => {
                  suggestionsEl.remove();
                  ask(suggestion.message);
                });
              }
              suggestionsEl.appendChild(button);
            });
            if (multi && choices.some(choice => !choice.exclusive)) {
              submit = document.createElement('button');
              submit.type = 'button';
              submit.className = 'dg-chat-suggestion';
              submit.textContent = 'Gửi lựa chọn';
              submit.disabled = true;
              submit.addEventListener('click', () => {
                const items = [...picked.values()].join(', ');
                const message = (result.multi_template || '{items}')
                  .replace('{items}', items);
                suggestionsEl.remove();
                ask(message);
              });
              suggestionsEl.appendChild(submit);
            }
            messages.scrollTop = messages.scrollHeight;
          },

          onError: message => {
            if (waiting.parentNode) waiting.remove();
            if (textEl.textContent) {
              textEl.textContent += `\n\n${message}`;
            } else {
              textEl.textContent = message;
            }
          }
        });

      } else {

        // Du phong: khong streaming
        const reply = await API.chat(text);
        if (waiting.parentNode) waiting.remove();
        textEl.textContent = reply || 'AI chưa trả về nội dung.';
      }

      if (!textEl.textContent) {
        textEl.textContent = 'AI chưa trả về nội dung.';
      }

    } catch (error) {

      if (waiting.parentNode) waiting.remove();
      textEl.textContent =
        'Không thể kết nối Chat AI: ' +
        (error.message || 'Có lỗi xảy ra.');

    } finally {

      bubble.classList.remove('streaming');

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
