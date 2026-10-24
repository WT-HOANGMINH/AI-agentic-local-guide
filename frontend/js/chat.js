/* =====================================
   DA NANG GUIDE - CHAT AI
   - Nut "Xoa hoi thoai" (tu tao, khong can sua chat.html)
   - Tieu de ngay va gio trong lich trinh duoc in dam
===================================== */

document.addEventListener('DOMContentLoaded', () => {

  // Kiem tra dang nhap (xoa dong nay neu muon khach chat khong can tai khoan)
  if (!protect()) return;

  const messages = $('#chat-messages');
  const form = $('#chat-form');
  const input = $('#chat-input');
  const send = $('#send-chat');

  if (!messages || !form || !input || !send) return;

  let isSending = false;

  const WELCOME =
    'Xin chào! Mình là trợ lý du lịch DaNang Guide. ' +
    'Bạn muốn khám phá địa điểm, tìm món ăn ngon ' +
    'hay lên lịch trình du lịch Đà Nẵng?';

  // ---------- Hien thi noi dung bot: in dam ngay va gio ----------
  // Dung DOM + textContent (khong dung innerHTML) nen an toan voi du lieu tu server.
  function renderBotText(el, text) {
    el.textContent = '';

    const lines = String(text).split('\n');

    lines.forEach((line, index) => {

      // "=== Ngay 1 (24/10) ===" -> tieu de dam
      const header = line.match(/^=+\s*(.+?)\s*=+$/);

      // "07:00–08:00  An sang: ..." -> gio dam
      const timed = line.match(/^(\d{2}:\d{2}\s*[–-]\s*\d{2}:\d{2})(\s+)(.*)$/);

      if (header) {
        const strong = document.createElement('strong');
        strong.textContent = header[1];
        strong.style.fontSize = '15px';
        el.appendChild(strong);

      } else if (timed) {
        const strong = document.createElement('strong');
        strong.textContent = timed[1];
        el.appendChild(strong);
        el.appendChild(document.createTextNode(timed[2] + timed[3]));

      } else {
        el.appendChild(document.createTextNode(line));
      }

      if (index < lines.length - 1) {
        el.appendChild(document.createTextNode('\n'));
      }
    });
  }

  // ---------- Hien thi tin nhan ----------
  function appendMessage(who, text) {

    const div = document.createElement('div');

    div.className = 'bubble ' + (who === 'user' ? 'user' : 'bot');

    if (who === 'user') {
      div.textContent = text;
    } else {
      renderBotText(div, text);
    }

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;

    return div;
  }

  // ---------- Nut xoa hoi thoai ----------
  function resetChat() {
    if (isSending) return;
    messages.innerHTML = '';
    appendMessage('bot', WELCOME);
  }

  const topbar = document.querySelector('.dg-chat-topbar');

  if (topbar) {
    const clearBtn = document.createElement('button');
    clearBtn.type = 'button';
    clearBtn.textContent = 'Xóa hội thoại';
    clearBtn.className = 'btn btn-sm btn-outline-secondary';
    clearBtn.style.marginLeft = 'auto';
    clearBtn.addEventListener('click', resetChat);
    topbar.appendChild(clearBtn);
  }

  // Loi chao
  appendMessage('bot', WELCOME);

  // ---------- Gui cau hoi den AI ----------
  async function ask(question) {

    const text = String(question || '').trim();

    if (!text || isSending) return;

    isSending = true;

    appendMessage('user', text);

    input.value = '';
    input.disabled = true;
    send.disabled = true;

    const typing = appendMessage('bot', 'Đang tìm câu trả lời cho bạn...');

    try {

      const reply = await API.chat(text);

      renderBotText(typing, reply || 'AI chưa trả về nội dung.');

    } catch (error) {

      renderBotText(
        typing,
        'Không thể kết nối Chat AI: ' + (error.message || 'Có lỗi xảy ra.')
      );

    } finally {

      isSending = false;

      input.disabled = false;
      send.disabled = false;

      messages.scrollTop = messages.scrollHeight;

      input.focus();
    }
  }

  // Gui bang nut Gui hoac Enter
  form.addEventListener('submit', event => {
    event.preventDefault();
    ask(input.value);
  });

  // Cac cau hoi goi y
  $$('[data-prompt]').forEach(button => {
    button.addEventListener('click', () => {
      ask(button.dataset.prompt);
    });
  });

});