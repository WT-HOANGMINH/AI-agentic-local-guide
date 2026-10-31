# 🌴 Agentic AI Local Guide - Khám Phá Đà Nẵng

> Hệ thống trợ lý du lịch địa phương thông minh cho thành phố Đà Nẵng, dùng mô hình phân loại ý định tự huấn luyện cho chat, tìm kiếm điểm đến (POI), dự báo thời tiết và lập lịch trình tự động. Một API Gemini riêng vẫn có thể dùng cho tích hợp cũ.

---

## 📌 Mục lục
1. [Giới thiệu & Tính năng chính](#-giới-thiệu--tính-năng-chính)
2. [Kiến trúc công nghệ](#-kiến-trúc-công-nghệ)
3. [Cấu trúc thư mục](#-cấu-trúc-thư-mục)
4. [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
5. [Hướng dẫn cài đặt & Chạy dự án (Từng bước)](#-hướng-dẫn-cài-đặt--chạy-dự-án-từng-bước)
6. [Tài khoản mẫu để kiểm thử](#-tài-khoản-mẫu-để-kiểm-thử)
7. [Tài liệu API & Kiểm thử (Swagger / Postman)](#-tài-liệu-api--kiểm-thử-swagger--postman)
8. [Các cơ chế dự phòng thông minh (Fallback Resilience)](#-các-cơ-chế-dự-phòng-thông-minh-fallback-resilience)

---

## 🌟 Giới thiệu & Tính năng chính

* **Bản đồ tương tác thời gian thực**: Sử dụng **Leaflet.js**, ghim vị trí (Pin SVG màu theo danh mục), đồng bộ 2 chiều giữa danh sách thẻ địa điểm và điểm ghim trên bản đồ, tích hợp GPS định vị và liên kết chỉ đường Google Maps.
* **Tìm kiếm & Bộ lọc linh hoạt**: Tìm kiếm theo tên/mô tả, lọc danh mục (*Điểm tham quan, Ẩm thực, Quán cà phê, Mua sắm*), mức giá (₫ - ₫₫₫₫₫).
* **Xác thực người dùng an toàn**: Đăng nhập/Đăng ký modal HTML5 native, cấp phát **JWT Bearer Token**, băm mật khẩu bảo mật cao bằng **Bcrypt**.
* **Chat AI dùng model đã huấn luyện**: `POST /agent/chat` nạp `training/models/intent_classifier.joblib`, tra cứu địa điểm trong database và tạo lịch trình bằng planner nội bộ; luồng này không gọi Gemini.
* **Dự báo thời tiết**: Planner lấy dữ liệu dự báo từ Open-Meteo để tư vấn lịch trình, giờ nghỉ và hoạt động ngoài trời.
* **Lập lịch trình chuyến đi (Trip Itinerary API)**:
  * Lập kế hoạch du lịch chi tiết theo từng ngày (sáng, trưa, chiều, tối).
  * **AI Smart Generator**: Tự động sinh lịch trình tối ưu 1 - 7 ngày dựa trên các địa điểm thực tế tại Đà Nẵng.
* **Quản trị POI dành riêng cho Admin (POI Management)**:
  * Thống kê tổng quan số lượng POI và phân bổ danh mục.
  * Thêm, sửa, xóa (soft delete / permanent) và bật/tắt nhanh hiển thị địa điểm.

---

## 🛠 Kiến trúc công nghệ

| Thành phần | Công nghệ sử dụng |
| :--- | :--- |
| **Backend** | Python 3.10+, FastAPI, Uvicorn, SQLAlchemy 2.0 |
| **AI / Agent** | Mô hình intent scikit-learn đã huấn luyện, planner nội bộ; Gemini chỉ dùng bởi API tích hợp cũ `/api/ai-guide/ask` |
| **Bảo mật** | JWT (python-jose), Bcrypt |
| **Cơ sở dữ liệu** | MySQL (Chính) / Tự động chuyển đổi sang SQLite (Dự phòng) |
| **Frontend** | Vanilla HTML5/CSS3, JavaScript ES Modules (Kiến trúc Module hóa) |
| **Bản đồ** | Leaflet.js, OpenStreetMap Tiles |

---

## 📁 Cấu trúc thư mục

```text
agentic-ai-local-guide/
├── backend/
│   ├── models/             # SQLAlchemy ORM Models (User, Place, Preference, Itinerary)
│   ├── routes/             # FastAPI Routers (auth, users, places, preferences, recommendations, itineraries)
│   ├── schemas/            # Pydantic Schemas (Validation dữ liệu đầu vào & đầu ra)
│   ├── services/           # Business logic (auth_service, etc.)
│   ├── agent.py            # LangGraph ReAct AI Agent với công cụ tra cứu địa điểm & thời tiết
│   ├── auth_utils.py       # Middleware xác thực JWT, phân quyền get_current_user & require_admin
│   ├── database.py         # Cấu hình engine kết nối DB (Tự động fallback MySQL -> SQLite)
│   └── main.py             # Entrypoint khởi tạo FastAPI, CORS, Exception Handlers & Seeder
├── frontend/
│   ├── css/                # CSS tách module (base.css, topbar.css, search.css, map.css, modal.css, toast.css)
│   ├── js/                 # JS ES Modules (config.js, utils.js, api.js, auth.js, map.js, places.js, app.js)
│   ├── index.html          # Trang giao diện chính
│   └── style.css           # File tổng hợp nạp các CSS module
├── .env.example            # Mẫu cấu hình biến môi trường
├── requirements.txt        # Danh sách thư viện Python cần cài đặt
├── postman_collection.json # File Postman Collection đầy đủ 27 API endpoints
└── README.md               # Tài liệu hướng dẫn sử dụng
```

---

## 💻 Yêu cầu hệ thống

* **Hệ điều hành**: Windows 10/11, macOS, hoặc Linux.
* **Python**: Phiên bản `3.10` trở lên (Đã kiểm thử hoạt động hoàn hảo trên Python 3.11 & Python 3.13).
* **Trình duyệt**: Chrome, Edge, Firefox, Brave phiên bản mới nhất.
* *(Tùy chọn)*: **MySQL / XAMPP** (Nếu không bật MySQL, hệ thống sẽ tự động dùng SQLite có sẵn).

---

## 🚀 Hướng dẫn cài đặt & Chạy dự án (Từng bước)

### Bước 1: Mở Terminal tại thư mục dự án
Mở **Command Prompt**, **PowerShell**, hoặc **VS Code Terminal** tại thư mục gốc của dự án:
```bash
cd C:\Users\Administrator\Downloads\agentic-ai-local-guide
```

---

### Bước 2: Tạo và kích hoạt môi trường ảo Python (Virtual Environment)

* **Trên Windows (PowerShell / Command Prompt)**:
  ```bash
  # Tạo môi trường ảo .venv
  python -m venv .venv

  # Kích hoạt môi trường ảo trên PowerShell:
  .venv\Scripts\Activate.ps1

  # Hoặc kích hoạt trên Command Prompt (cmd):
  .venv\Scripts\activate.bat
  ```

* **Trên macOS / Linux**:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

*(Khi kích hoạt thành công, bạn sẽ thấy tiền tố `(.venv)` hiển thị ở đầu dòng lệnh).*

---

### Bước 3: Cài đặt các thư viện cần thiết

Cài đặt toàn bộ các gói phụ thuộc từ `requirements.txt`:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Bước 4: Cấu hình biến môi trường (`.env`)

Sao chép file `.env.example` thành `.env`:
```bash
# Trên Windows (cmd / powershell):
copy .env.example .env

# Trên macOS / Linux:
cp .env.example .env
```

Mở file `.env` và cập nhật các thông số (nếu có):
```ini
# Google Gemini API Key (Lấy miễn phí tại: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash

# Cấu hình kết nối MySQL (Nếu MySQL không bật, Backend sẽ tự động dùng SQLite: local_guide.db)
DATABASE_URL=mysql+pymysql://root:1234@localhost:3306/agentic_local_guide

# Khóa bí mật mã hóa JWT
SECRET_KEY=agentic-ai-local-guide-secret-key-2026
```

> [!NOTE]
> Chat `/agent/chat` dùng dữ liệu địa phương và không cần **Gemini API Key**. Key chỉ cần cho API tích hợp cũ `/api/ai-guide/ask`. Nếu **MySQL chưa bật**, backend sẽ thử dùng SQLite cục bộ.

#### Đăng nhập Google / Facebook (tùy chọn)

Tạo OAuth app ở Google Cloud Console và Meta for Developers, sau đó cấu hình các biến môi trường sau trong `.env` (hoặc Environment của Render):

```ini
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
FACEBOOK_APP_ID=
FACEBOOK_APP_SECRET=
FACEBOOK_REDIRECT_URI=http://127.0.0.1:8000/auth/facebook/callback
FRONTEND_URL=http://127.0.0.1:5500
```

Đăng ký đúng từng callback URL ở trang cấu hình của nhà cung cấp. Trên môi trường deploy, thay các URL localhost bằng URL HTTPS thực tế; `FRONTEND_URL` chỉ là origin, không kèm đường dẫn. Giữ các secret trong biến môi trường, không đưa vào frontend hay commit vào Git. Nếu thiếu cấu hình, endpoint OAuth sẽ báo lỗi cấu hình rõ ràng thay vì giả lập đăng nhập.

---

### Bước 5: Khởi chạy Backend FastAPI

Chạy máy chủ Uvicorn:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Huấn luyện lại model chat

Chat sử dụng bộ dữ liệu trong `training/data/` và lưu model tại
`training/models/intent_classifier.joblib`. Sau khi cài requirements, chạy:

```bash
python training/src/train_intent_v2.py --final
```

Lệnh này huấn luyện đủ tám intent; không cần Gemini API Key để trả lời trong giao diện chat.

Khi khởi động thành công, màn hình terminal sẽ hiển thị:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
Database tables initialized successfully.
[Seeder] Da khoi tao tai khoan mau va du lieu dia diem Da Nang!
```

---

### Bước 6: Khởi chạy Giao diện Frontend

Bạn có thể mở giao diện bằng 1 trong các cách sau:

#### Cách 1: Sử dụng Python HTTP Server (Khuyên dùng)
Mở một cửa sổ Terminal mới và chạy:
```bash
python -m http.server 5500 --directory frontend
```
Sau đó mở trình duyệt và truy cập: **`http://127.0.0.1:5500/`**

#### Cách 2: Truy cập trực tiếp qua Backend static mount
Do Backend đã tích hợp sẵn thư mục frontend, bạn có thể truy cập thẳng vào:
👉 **`http://127.0.0.1:8000/app/index.html`**

#### Cách 3: Sử dụng VS Code Live Server
Mở file `frontend/index.html` trong VS Code, nhấp chuột phải chọn **"Open with Live Server"** (Port mặc định `5500`).

Khi frontend chạy ở localhost (ví dụ cổng `5500`) và backend ở cổng `8000`, cấu hình sẽ tự gửi API tới backend. Khi frontend được phục vụ từ chính ứng dụng FastAPI, API dùng cùng origin. Có thể đặt `window.LOCAL_GUIDE_API_BASE` trước `js/config.js` để chỉ định backend khác.

---

## 👤 Tài khoản mẫu để kiểm thử

Hệ thống đã tự động gieo sẵn (auto-seed) tài khoản Quản trị viên và dữ liệu địa điểm Đà Nẵng:

| Vai trò | Email đăng nhập | Mật khẩu | Quyền hạn |
| :--- | :--- | :--- | :--- |
| **Quản trị viên (Admin)** | `admin@localguide.vn` | `admin123` | Quản trị toàn quyền: Thống kê POI, Thêm, Sửa, Xóa, Ẩn/Hiện địa điểm |
| **Người dùng (User)** | Tự đăng ký trực tiếp trên modal | Tùy chọn | Tìm kiếm, xem bản đồ, lưu sở thích, tạo lịch trình cá nhân |

---

## 📖 Tài liệu API & Kiểm thử (Swagger / Postman)

### 1. Swagger UI & ReDoc
Backend cung cấp tài liệu API tương tác trực tiếp:
* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Format**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 2. Sử dụng Postman Collection
Dự án đi kèm file **`postman_collection.json`** với 27 API endpoints đã được cấu hình sẵn biến môi trường:
1. Mở ứng dụng **Postman**.
2. Nhấn nút **Import** ở góc trên bên trái.
3. Chọn file [`postman_collection.json`](postman_collection.json) trong thư mục gốc.
4. Chạy request **`1. Authentication > Đăng nhập Admin`**: Hệ thống sẽ tự động lưu JWT Token vào biến `{{token}}` cho tất cả các request phía sau.

### 3. Kiểm thử và huấn luyện AI

Từ thư mục gốc dự án, trong PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
python -m pytest -q tests
python -m compileall -q backend training tests
```

Để huấn luyện lại bộ trích thông tin trên Windows (đảm bảo console dùng UTF-8):

```powershell
python -X utf8 training\src\export_place_names.py
python -X utf8 training\src\generate_slots.py
python -X utf8 training\src\train_slots.py
```

CI và Render cũng sinh hai mô hình AI trong quá trình build. Bộ phân loại, trích thông tin, truy vấn địa điểm và lập lịch trình chạy cục bộ. Khi được cấu hình `GEMINI_API_KEY`, endpoint SSE dùng Gemini để diễn đạt câu trả lời đã được kiểm chứng và gửi từng token; các bước suy nghĩ nội bộ không được gửi ra giao diện. Không có key, hoặc khi cần hỏi làm rõ, ứng dụng trả kết quả địa phương qua sự kiện `result` và UI vẫn hiển thị các lựa chọn gợi ý.

---

## 🛡 Các cơ chế dự phòng thông minh (Fallback Resilience)

Hệ thống được thiết kế theo tiêu chuẩn công nghiệp với khả năng chịu lỗi cao:

1. **Database Fallback**:
   Nếu máy chưa cài đặt hoặc chưa khởi động dịch vụ MySQL trên cổng `3306`, [`backend/database.py`](backend/database.py) sẽ tự động kích hoạt cơ sở dữ liệu nhúng **SQLite** (`sqlite:///./local_guide.db`) để ứng dụng không bị gián đoạn.
2. **Chat AI nội bộ**:
   [`backend/routes/agent.py`](backend/routes/agent.py) dùng model đã huấn luyện và planner cục bộ; không phụ thuộc Gemini. API tích hợp cũ `/api/ai-guide/ask` là luồng riêng.
3. **Frontend Mock Fallback**:
   Nếu Backend tạm thời ngắt kết nối, [`frontend/js/places.js`](frontend/js/places.js) sẽ tự động nạp danh sách 10 địa điểm nổi tiếng Đà Nẵng từ mock data để bản đồ và giao diện vẫn hiển thị sinh động.
4. **Bảo vệ mã hóa Console Windows**:
   Mọi log lỗi hệ thống đều được lọc mã ký tự ASCII trước khi xuất console, triệt tiêu hoàn toàn lỗi `UnicodeEncodeError (charmap / CP1252)` trên hệ điều hành Windows.

---

🎉 *Chúc bạn có trải nghiệm tuyệt vời khi phát triển và sử dụng Agentic AI Local Guide!*
