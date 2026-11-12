/* =====================================
   DA NANG GUIDE - CHAT AI
   Hien thi trang thai xu ly tu backend va hien cau tra loi tung chu.
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

  const WELCOME =
    'Xin chào! Mình là trợ lý du lịch DaNang Guide. ' +
    'Bạn muốn khám phá địa điểm, tìm món ăn ngon ' +
    'hay lên lịch trình du lịch Đà Nẵng?';

  function renderBotText(element, text) {
    element.replaceChildren();

    const lines = String(text).split('\n');
    lines.forEach((line, index) => {
      const header = line.match(/^=+\s*(.+?)\s*=+$/);
      const timed = line.match(/^(\d{2}:\d{2}\s*[–-]\s*\d{2}:\d{2})(\s+)(.*)$/);

      if (header) {
        const strong = document.createElement('strong');
        strong.textContent = header[1];
        element.appendChild(strong);
      } else if (timed) {
        const strong = document.createElement('strong');
        strong.textContent = timed[1];
        element.append(strong, document.createTextNode(timed[2] + timed[3]));
      } else {
        element.appendChild(document.createTextNode(line));
      }

      if (index < lines.length - 1) {
        element.appendChild(document.createTextNode('\n'));
      }
    });
  }

  async function revealBotText(element, text, append = false) {
    if (!append) element.textContent = '';
    await API.revealText(text, character => {
      element.append(character);
      messages.scrollTop = messages.scrollHeight;
    });
    renderBotText(element, text);
  }

  // =====================================
  // HIEN THI TIN NHAN
  // =====================================

  function appendMessage(who, text) {

    const div = document.createElement('div');

    div.className =
      'bubble ' + (who === 'user' ? 'user' : 'bot');

    if (who === 'user') {
      div.textContent = text;
    } else {
      renderBotText(div, text);
    }

    messages.appendChild(div);

    messages.scrollTop = messages.scrollHeight;

    return div;
  }

  // =====================================
  // LOI CHAO BAN DAU
  // =====================================

  appendMessage('bot', WELCOME);

  function resetChat() {
    if (isSending) return;
    messages.replaceChildren();
    try {
      sessionStorage.removeItem('dg_sid');
    } catch (error) {
      console.warn('Không thể đặt lại phiên chat trong trình duyệt.', error);
    }
    appendMessage('bot', WELCOME);
  }

  const topbar = document.querySelector('.dg-chat-topbar');
  if (topbar) {
    const clearButton = document.createElement('button');
    clearButton.type = 'button';
    clearButton.textContent = 'Xóa hội thoại';
    clearButton.className = 'btn btn-sm btn-outline-secondary';
    clearButton.style.marginLeft = 'auto';
    clearButton.addEventListener('click', resetChat);
    topbar.appendChild(clearButton);
  }

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
    const replyText = document.createTextNode('');
    textEl.appendChild(replyText);
    const suggestionsEl = document.createElement('div');
    suggestionsEl.className = 'dg-chat-suggestions';

    const waiting = document.createElement('div');
    waiting.className = 'dg-chat-progress active';
    waiting.textContent = 'Đang gửi yêu cầu…';
    stepsEl.appendChild(waiting);

    bubble.append(stepsEl, textEl, suggestionsEl);
    bubble.classList.add('streaming');

    try {

      if (typeof API.chatStream === 'function') {

        await API.chatStream(text, {
          onStatus: status => {
            waiting.textContent = status.text;
            messages.scrollTop = messages.scrollHeight;
          },

          onStep: step => {
            const line = document.createElement('div');
            line.className = 'dg-step done';
            line.textContent = step;
            stepsEl.appendChild(line);
            messages.scrollTop = messages.scrollHeight;
          },

          onToken: token => {
            waiting.textContent = 'Đang nhận câu trả lời từ AI…';
            textEl.classList.add('dg-streaming-text');
            replyText.appendData(token);
            messages.scrollTop = messages.scrollHeight;
          },

          onResult: async result => {
            const finalText = String(result.text || '');
            const visibleText = textEl.textContent;
            if (finalText && finalText !== visibleText) {
              waiting.textContent = 'Đang hiển thị câu trả lời…';
              textEl.classList.add('dg-streaming-text');
              const suffix = finalText.startsWith(visibleText)
                ? finalText.slice(visibleText.length)
                : finalText;
              if (suffix === finalText && visibleText) textEl.textContent = '';
              await revealBotText(textEl, suffix, true);
              renderBotText(textEl, finalText);
            }
            textEl.classList.remove('dg-streaming-text');
            if (textEl.textContent) {
              renderBotText(textEl, finalText || textEl.textContent);
            }
            if (waiting.parentNode) waiting.remove();
            (result.links || []).forEach(link => {
              const anchor = document.createElement('a');
              anchor.className = 'dg-chat-link';
              anchor.href = link.url;
              anchor.target = '_blank';
              anchor.rel = 'noopener noreferrer';
              anchor.textContent = `🗺️ ${link.label}`;
              bubble.insertBefore(anchor, suggestionsEl);
            });
            if (result.itinerary && Array.isArray(result.itinerary.days)) {
              const saveWrap = document.createElement('div');
              saveWrap.className = 'dg-chat-itinerary-action';
              const saveButton = document.createElement('button');
              saveButton.type = 'button';
              saveButton.className = 'dg-chat-suggestion';
              saveButton.textContent = 'Lưu lịch trình này';
              const saveStatus = document.createElement('span');
              saveStatus.className = 'muted';
              saveButton.addEventListener('click', async () => {
                saveButton.disabled = true;
                saveStatus.textContent = 'Đang lưu…';
                try {
                  const saved = await API.saveChatItinerary(result.itinerary);
                  saveStatus.textContent = 'Đã lưu lịch trình.';
                  const savedLink = document.createElement('a');
                  savedLink.href = `itinerary.html?id=${encodeURIComponent(saved.id)}`;
                  savedLink.textContent = 'Mở lịch trình đã lưu';
                  savedLink.className = 'dg-chat-link';
                  saveWrap.appendChild(savedLink);
                } catch (error) {
                  saveStatus.textContent = error.message || 'Không thể lưu lịch trình.';
                  saveButton.disabled = false;
                }
              });
              saveWrap.append(saveButton, saveStatus);
              bubble.insertBefore(saveWrap, suggestionsEl);
            }
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
            textEl.classList.remove('dg-streaming-text');
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
        waiting.textContent = 'Đang hiển thị câu trả lời…';
        textEl.classList.add('dg-streaming-text');
        await revealBotText(textEl, reply || 'AI chưa trả về nội dung.');
        textEl.classList.remove('dg-streaming-text');
        if (waiting.parentNode) waiting.remove();
      }

      if (!textEl.textContent) {
        textEl.textContent = 'AI chưa trả về nội dung.';
      }

    } catch (error) {

      if (waiting.parentNode) waiting.remove();
      textEl.classList.remove('dg-streaming-text');
      textEl.textContent =
        'Không thể kết nối Chat AI: ' +
        (error.message || 'Có lỗi xảy ra.');

    } finally {

      if (waiting.parentNode) waiting.remove();
      textEl.classList.remove('dg-streaming-text');
      if (textEl.textContent) {
        renderBotText(textEl, textEl.textContent);
      }

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
