# Gói cập nhật: DaNang Guide AI tự huấn luyện (không dùng Gemini/LLM bên ngoài)

Giải nén gói này vào **thư mục gốc dự án** (nơi có `backend/`, `frontend/`, `training/`).
Các file mới sẽ vào đúng vị trí; các file có sẵn bên dưới sẽ bị **ghi đè** (hãy `git commit` trước).

## Bảng file

| File trong gói | Việc cần làm |
|---|---|
| backend/services/slot_service.py | MỚI |
| backend/services/place_repo.py | MỚI |
| backend/services/place_enrichment.py | MỚI |
| backend/services/planner.py | MỚI |
| backend/services/ranker.py | MỚI |
| backend/services/nlg.py | MỚI |
| backend/services/dialogue.py | MỚI |
| backend/enrich_places.py | MỚI |
| backend/cli_chat.py | MỚI |
| training/src/export_place_names.py | MỚI |
| training/src/add_dialogue_data.py | MỚI |
| training/src/generate_slots.py | MỚI |
| training/src/train_slots.py | MỚI |
| tests/ (6 file) | MỚI |
| backend/models/place.py | GHI ĐÈ (thêm 5 cột) |
| backend/services/intent_service.py | GHI ĐÈ (thêm 4 nhãn ý định) |
| backend/routes/ai_guide.py | GHI ĐÈ (bỏ Gemini, thêm /chat, /chat-stream) |
| frontend/js/ai-chat.js | GHI ĐÈ |
| frontend/js/chat.js | GHI ĐÈ |
| frontend/chat.html | GHI ĐÈ (chỉ thêm CSS) |
| requirements.txt | GHI ĐÈ (bỏ thư viện Gemini, thêm pytest) |

**Xóa** (không còn dùng): `backend/services/llm_service.py` và file `agent.py` của bạn (mục 4).
Không đụng tới: `main.py`, `database.py`, `place_tool.py`, `train_intent_v2.py`.

## Các bước (làm đúng thứ tự)

### Bước 0 - Chuẩn bị
1. `git checkout -b self-trained-ai` và `git commit` mọi thứ đang có.
2. Sao lưu `training/models/` ra nơi khác.
3. Kiểm tra mã hóa tiếng Việt trong MySQL:
   ```sql
   SELECT COUNT(*) FROM places WHERE name LIKE '%?%' OR address LIKE '%?%';
   SHOW CREATE TABLE places;
   ```
   Kết quả 0 là ổn (chỉ do console hiển thị). Gần 300 hoặc `CHARSET=latin1` là dữ liệu đã hỏng: dừng lại, sửa/nạp lại bảng ở `utf8mb4` rồi mới làm tiếp.

### Bước 1 - Cài thư viện, gỡ Gemini
```
pip install -r requirements.txt
pip uninstall -y langchain-google-genai google-genai
```
Giữ nguyên `google-auth` (dùng cho đăng nhập Google).

### Bước 2 - Chép file CHƯA ảnh hưởng hệ thống đang chạy
Chép: `slot_service.py`, `place_enrichment.py`, `place_repo.py`, `enrich_places.py` (vào đúng thư mục ở bảng trên).

### Bước 3 - Làm giàu dữ liệu (CHẠY TRƯỚC khi thay place.py)
Bật MySQL, rồi từ thư mục gốc:
```
python -m backend.enrich_places --merge-bana
```
Script tự sao lưu bảng (`places_backup_before_enrich_...`), thêm 5 cột, điền giờ mở/đóng, khu vực (zone), thời lượng, khung giờ đẹp, và gộp 3 dòng Bà Nà (id 828, 842, 843) thành 1 dòng cả ngày.
Sau đó:
- Xem danh sách dòng "chưa suy ra zone" và sửa tay.
- Xem lại thời lượng (`duration_min`) của ~20 địa điểm nổi tiếng: đó là ước lượng mặc định.
- Đối chiếu bảng thời gian giữa khu vực (`_Z` trong `planner.py`) với Google Maps cho vài cặp quan trọng.

### Bước 4 - Chép phần còn lại
1. Chép các file MỚI và GHI ĐÈ trong bảng (đè `place.py` SAU bước 3).
2. Xóa `backend/services/llm_service.py` và `agent.py`.
3. Mở `ai_guide.py` mới: file đã tự bỏ `ask_llm` và `search_places`, không cần sửa thêm.

### Bước 5 - Huấn luyện lại bộ nhận diện ý định
```
python training/src/add_dialogue_data.py
```
Tự gõ thêm 20-30 câu THẬT cho mỗi nhãn mới (`modify_itinerary`, `clarify_reply`, `greeting`, `ask_detail`) vào `training/data/intents.csv` (câu ngắn, có/không dấu, Việt/Anh). Rồi:
```
python training/src/train_intent_v2.py          # đọc HUMAN TEST và confusion matrix
python training/src/train_intent_v2.py --final
```
Mục tiêu gợi ý: HUMAN TEST accuracy >= 85%, F1 các nhãn mới >= 0.75.

### Bước 6 - Huấn luyện bộ trích thông tin
```
python training/src/export_place_names.py
python training/src/generate_slots.py
python training/src/train_slots.py
```
Điểm trên tập sinh tự động luôn cao; hãy nhìn phần "câu VIẾT TAY" và thêm câu của bạn vào `HAND_TESTS` trong `train_slots.py`. Câu nào bắt sai thì thêm khuôn mẫu vào `TEMPLATES` của `generate_slots.py`, sinh lại và huấn luyện lại.

### Bước 7 - Thử trong terminal, rồi chạy kiểm thử
```
python -m backend.cli_chat
pytest tests/
```
Thử lần lượt:
1. `lịch trình` -> AI hỏi số ngày và sở thích.
2. `2 ngày, thích biển` -> lịch trình kèm giải thích.
3. `mình muốn đi Bà Nà từ sớm` -> Bà Nà chiếm một ngày, bắt đầu đúng giờ mở cửa.
4. `thêm bữa sáng ngày 1` -> thêm quán mở cửa sớm gần điểm đầu tiên.
5. `ăn sáng gần Mỹ Khê` -> chỉ quán mở cửa sớm.
6. `ăn gì` -> AI hỏi bữa nào, khu vực nào.

### Bước 8 - Chạy web
```
uvicorn backend.main:app --reload
```
Mở `chat.html`. Nếu không nhận được dữ liệu, mở DevTools -> Network, kiểm tra request `chat-stream`. Nếu `API_BASE` trong `config.js` đã có `/api` thì không sao (ai-chat.js tự xử lý).

## Lưu ý trung thực khi bảo vệ
- Hai model tự huấn luyện: nhận diện ý định (`intent_classifier.joblib`) và trích thông tin (`slot_tagger.joblib`). Xếp hạng địa điểm dùng TF-IDF học từ dữ liệu của bạn.
- Nội dung (hỏi gì, chọn gì, xếp thế nào, tiết kiệm bao nhiêu phút) do thuật toán tính; kho câu trong `nlg.py` chỉ lo cách diễn đạt.
- Các dòng "Phân tích câu hỏi..., Trích thông tin..." là kết quả thật của từng bước; hiệu ứng hiện từng chữ là hiệu ứng hiển thị.
- Thời gian di chuyển khi thiếu tọa độ là ước lượng theo bảng khu vực (khoảng 90% địa điểm của bạn chưa có tọa độ).
- Session hội thoại lưu trong RAM: khởi động lại server là mất lịch trình đang sửa.
- Chưa có dữ liệu khách sạn nên intent `accommodation` chưa trả được kết quả; chưa có dữ liệu thời tiết.
