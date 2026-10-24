# Agentic AI Local Guide — Frontend (Ngô Xuân Hiệp)

## Chạy trong VS Code

1. Mở thư mục `frontend` trong VS Code.
2. Cài extension **Live Server** và chọn **Open with Live Server** ở `index.html`. Hoặc chạy `python -m http.server 5500` trong thư mục `frontend`, rồi mở `http://localhost:5500`.
3. Cần Internet để tải Bootstrap, Leaflet, font và bản đồ OpenStreetMap.
4. Đang dùng `USE_MOCK: true` ở `js/config.js`: vào Đăng ký, tạo tài khoản và đăng nhập để thử Chat AI, lưu yêu thích và lịch trình. Dữ liệu demo lưu ở localStorage *chỉ để kiểm thử*, không an toàn cho dữ liệu thật.

## Kết nối FastAPI

Trong `js/config.js`, đổi `USE_MOCK: false` và kiểm tra `API_BASE`. Frontend dự kiến các endpoint JSON sau (cần thống nhất với Phương):

| Method | Endpoint | Body / response mong đợi |
|---|---|---|
| POST | `/auth/register` | `{name,email,password}` → thông báo |
| POST | `/auth/login` | `{email,password}` → `{access_token,user:{id,name,email}}` |
| GET | `/places?q=&category=` | Mảng places hoặc `{places:[...]}` |
| GET | `/recommendations?category=` | Mảng places hoặc `{places:[...]}` |
| POST | `/agent/chat` | `{message}` → `{reply}` |
| GET | `/favorites` | Mảng ID địa điểm |
| POST | `/favorites/{id}` | Toggle yêu thích; body rỗng |
| GET | `/itineraries` | `{place_ids:[1,2]}` |
| POST | `/itineraries` | `{name,place_ids:[1,2]}` |

**Place object:** `{id,name,category,district,description,latitude,longitude,emoji,rating}`. `latitude`/`longitude` là tọa độ số. Nếu Backend chọn các đường dẫn hay schema khác, sửa duy nhất `js/api.js`.

Backend phải bật CORS cho origin thực tế của Live Server (ví dụ `http://127.0.0.1:5500` và `http://localhost:5500`), xử lý JWT đúng cách, và hash mật khẩu phía server. Trình duyệt không thể gọi trực tiếp FastAPI nếu CORS bị chặn.

### Bảo mật

* Mock chỉ để trình diễn: mật khẩu được lưu ở localStorage, tuyệt đối không nhập mật khẩu thật và không triển khai lên production.
* Ở API mode, token JWT lưu trong localStorage để thuận tiện tích hợp đồ án; production nên bàn với backend về cookie HttpOnly, CSP, xử lý XSS, CSRF và vòng đời token.
* Backend đã hỗ trợ đầy đủ các endpoint: `/auth/*`, `/places/*`, `/recommendations*`, `/agent/chat`, `/favorites/*`, và `/itineraries/*`.

## Các trang

- `index.html`: trang chủ, địa điểm nổi bật
- `login.html`, `register.html`: tài khoản
- `chat.html`: trợ lý AI (demo hoặc API)
- `places.html`: tìm kiếm và lọc địa điểm
- `recommendations.html`: đề xuất theo danh mục
- `map.html`: bản đồ Leaflet, marker và vị trí người dùng
- `itinerary.html`: lưu danh sách điểm dừng, chưa phải thuật toán tối ưu lịch trình

## Test nhanh

1. Thử Register/Login hợp lệ và không hợp lệ.
2. Thử tìm “biển”, lọc danh mục, không tìm thấy địa điểm.
3. Vào Chat AI và thử gửi câu hỏi.
4. Mở Map, bấm marker, thử lọc địa điểm.
5. Thêm/xóa yêu thích, thêm/xóa lịch trình.
6. Dùng DevTools chế độ điện thoại kiểm tra Responsive.
7. Chuyển `USE_MOCK:false` khi có FastAPI và kiểm tra network/status/error.

Dữ liệu địa điểm, tọa độ và đánh giá chỉ là bản minh họa, chưa xác thực đầy đủ. Không phải dữ liệu trực tiếp từ dịch vụ du lịch.


## Cập nhật dữ liệu địa điểm (19 địa điểm)

Đã thêm 11 địa điểm: Ghềnh Bàng, Bãi Bụt, Mũi Nghê, Hải đăng Tiên Sa, Nhất Lâm Thủy Trang Trà, Cầu vòm Đồn Cả, Thác Ba Đờ Phọt, Hồ Hòa Trung, Giếng Trời, Bãi Rạn Nam Ô, Rừng thông Bồ Bồ. Tổng cộng 19 địa điểm trong `js/data.js`.

- Place Search tìm theo tên, mô tả, khu vực và hoạt động. Recommendation demo có địa điểm mới.
- Chỉ Mũi Nghê có tọa độ từ nguồn bản đồ đối chiếu; đây là vị trí mũi đất, không phải vị trí lối vào. Các địa điểm khác chưa được kiểm chứng tọa độ, được dẫn tới tìm kiếm OpenStreetMap thay vì tự đặt marker sai.
- Giá vé, khoảng cách và tình trạng tiếp cận chỉ mang tính tham khảo; hãy xác minh trước khi thực địa.
- Trong API MODE, Backend đã nạp đầy đủ toàn bộ 21 địa điểm (kèm đánh giá rating xác thực, tọa độ chuẩn và danh mục) vào database để Frontend hiển thị đồng bộ.


## Dữ liệu demo cập nhật (21 địa điểm)
- Giữ 8 địa điểm ban đầu, thêm 11 điểm Sơn Trà/ngoại ô và 2 điểm khu vực Hội An, Mỹ Sơn.
- Không lặp địa điểm đã có.
- Các địa điểm chưa xác minh tọa độ để `latitude`/`longitude` là `null`; có liên kết tìm kiếm OpenStreetMap tại trang Map, không tạo ghim giả.
- Nội dung demo tham khảo; lịch diễn, giá vé, điều kiện tiếp cận và vị trí cần kiểm tra trước chuyến đi.
