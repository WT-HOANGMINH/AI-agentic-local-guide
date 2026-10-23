# 🌴 Agentic AI Local Guide - Khám Phá Đà Nẵng

> Hệ thống trợ lý du lịch địa phương thông minh cho thành phố Đà Nẵng, tích hợp **Agentic AI** (LangGraph & Google Gemini), tìm kiếm điểm đến (POI) trên bản đồ tương tác, lập lịch trình tự động và quản lý hồ sơ sở thích cá nhân hóa.

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
* **Xác thực người dùng an toàn**: Đăng nhập/Đăng ký modal HTML5 native, cấp phát **JWT Bearer Token**, băm mậtpython -m http.server 5500 --directory frontend khẩu bảo mật cao bằng **Bcrypt**.
* **AI Agent Gợi ý Du lịch**: Tích hợp **LangGraph ReAct Agent + Gemini Flash**, tự động phân tích câu hỏi kết hợp hồ sơ sở thích cá nhân để đưa ra câu trả lời tự nhiên kèm danh sách địa điểm phù hợp.
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
| **AI / Agent** | LangGraph, LangChain, Google Gemini API (`gemini-3.8-flash` / `gemini-1.5-flash`) |
| **Bảo mật** | JWT (python-jose), Bcrypt |
| **Cơ sở dữ liệu** | MySQL (Chính) / Tự động chuyển đổi sang SQLite (Dự phòng) |
| **Frontend** | Vanilla HTML5/CSS3, JavaScript ES Modules (Kiến trúc Module hóa) |
| **Bản đồ** | Leaflet.js, OpenStreetMap Tiles |

---

## 📁 Cấu trúc thư mục

```text
AI-agentic-local-guide-main/
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
cd C:\Users\Administrator\Downloads\AI-agentic-local-guide-main
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

# Cấu hình kết nối MySQL (Nếu MySQL không bật, Backend sẽ tự động dùng SQLite: local_guide.db)
DATABASE_URL=mysql+pymysql://root:1234@localhost:3306/agentic_local_guide

# Khóa bí mật mã hóa JWT
SECRET_KEY=agentic-ai-local-guide-secret-key-2026
```

> [!NOTE]
> Nếu bạn chưa có **Gemini API Key** hoặc **MySQL chưa bật**, ứng dụng vẫn khởi chạy bình thường nhờ cơ chế Fallback tự động.

---

### Bước 5: Khởi chạy Backend FastAPI

Chạy máy chủ Uvicorn:
```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Khi khởi động thành công, màn hình terminal sẽ hiển thị:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
Database tables initialized successfully.
[Seeder] Da khoi tao tai khoan mau va du lieu dia diem Da Nang!
```

---

### Bước 6: Khởi chạy Giao diện Frontend

Backend đã phục vụ frontend và API trên cùng một máy chủ. Sau khi chạy Backend ở Bước 5, mở:
👉 **`http://127.0.0.1:8000/app/index.html`**

Không nên dùng `python -m http.server` trên Windows cho frontend này: một số cấu hình Windows trả các file ES module `.js` với MIME type `text/plain`, khiến trình duyệt từ chối tải ứng dụng. Nếu cần dùng máy chủ frontend riêng như VS Code Live Server, hãy xác nhận các file `.js` được phục vụ với MIME type `text/javascript`.

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

---

## 🛡 Các cơ chế dự phòng thông minh (Fallback Resilience)

Hệ thống được thiết kế theo tiêu chuẩn công nghiệp với khả năng chịu lỗi cao:

1. **Database Fallback**:
   Nếu máy chưa cài đặt hoặc chưa khởi động dịch vụ MySQL trên cổng `3306`, [`backend/database.py`](backend/database.py) sẽ tự động kích hoạt cơ sở dữ liệu nhúng **SQLite** (`sqlite:///./local_guide.db`) để ứng dụng không bị gián đoạn.
2. **AI Agent Fallback**:
   Nếu `GEMINI_API_KEY` chưa được điền hoặc gặp sự cố mất kết nối mạng ngoài, [`backend/routes/recommendations.py`](backend/routes/recommendations.py) sẽ kích hoạt **Smart Recommendation Engine** để phân tích câu hỏi của du khách và lọc địa điểm phù hợp trong database, luôn trả về HTTP `200 OK` thay vì crash 500.
3. **Frontend Mock Fallback**:
   Nếu Backend tạm thời ngắt kết nối, [`frontend/js/places.js`](frontend/js/places.js) sẽ tự động nạp danh sách 10 địa điểm nổi tiếng Đà Nẵng từ mock data để bản đồ và giao diện vẫn hiển thị sinh động.
4. **Bảo vệ mã hóa Console Windows**:
   Mọi log lỗi hệ thống đều được lọc mã ký tự ASCII trước khi xuất console, triệt tiêu hoàn toàn lỗi `UnicodeEncodeError (charmap / CP1252)` trên hệ điều hành Windows.

---

🎉 *Chúc bạn có trải nghiệm tuyệt vời khi phát triển và sử dụng Agentic AI Local Guide!*
