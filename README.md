# 🌸 Beaudy Backend — Hướng dẫn cài đặt & sử dụng

## Tổng quan

Hệ thống backend đầy đủ cho website Beaudy, bao gồm:

- **Database**: SQLite — lưu bài viết, tài khoản admin, tin nhắn liên hệ
- **Backend**: Python Flask — xử lý đăng nhập, CRUD bài viết, nhận form liên hệ
- **Admin Panel**: Trang quản trị tại `/admin`
- **REST API**: Các endpoint JSON cho frontend
- **Website tĩnh**: Serve toàn bộ file HTML/CSS/JS gốc

---

## Cấu trúc thư mục

```
beaudy-backend/
├── app.py               ← Server chính (Flask)
├── db/
│   ├── init_db.py       ← Khởi tạo database
│   └── beaudy.db        ← SQLite database (tự tạo khi chạy)
├── public/              ← Toàn bộ file website gốc (HTML, CSS, JS, images)
│   ├── index.html
│   ├── style.css
│   ├── shared.js
│   ├── bai-viet-*.html
│   └── images/
└── uploads-img/         ← Ảnh upload từ admin (tự tạo)
```

---

## Cài đặt & Chạy

### Yêu cầu
- Python 3.8+
- Flask 3.x (`pip install flask`)

### Bước 1 — Cài Flask
```bash
pip install flask
```

### Bước 2 — Chạy server
```bash
python app.py
```

### Bước 3 — Mở trình duyệt
| URL | Mô tả |
|-----|-------|
| http://localhost:5000 | Trang chủ website |
| http://localhost:5000/admin | Admin Panel |
| http://localhost:5000/api/posts | API danh sách bài viết |

---

## 🔐 Đăng nhập Admin

- **URL**: http://localhost:5000/admin
- **Username**: `admin`
- **Password**: `admin123`

> ⚠️ Đổi mật khẩu ngay sau lần đầu đăng nhập tại **Admin > Cài đặt**

---

## 🗄️ Database Schema

### Bảng `posts` — Bài viết
| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | INTEGER | Primary key |
| slug | TEXT | URL-friendly ID (vd: `bai-viet-duong-toc`) |
| title | TEXT | Tiêu đề bài viết |
| category | TEXT | Danh mục |
| excerpt | TEXT | Tóm tắt ngắn |
| content | TEXT | Nội dung HTML đầy đủ |
| cover_image | TEXT | Đường dẫn ảnh bìa |
| author | TEXT | Tên tác giả |
| status | TEXT | `published` hoặc `draft` |
| view_count | INTEGER | Số lượt xem |
| created_at | DATETIME | Ngày tạo |
| updated_at | DATETIME | Ngày cập nhật |

### Bảng `admins` — Tài khoản quản trị
| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | INTEGER | Primary key |
| username | TEXT | Tên đăng nhập |
| password_hash | TEXT | Mật khẩu (SHA-256) |
| display_name | TEXT | Tên hiển thị |

### Bảng `contacts` — Tin nhắn liên hệ
| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | INTEGER | Primary key |
| name | TEXT | Họ tên người gửi |
| email | TEXT | Email |
| subject | TEXT | Chủ đề |
| message | TEXT | Nội dung tin nhắn |
| is_read | INTEGER | 0 = chưa đọc, 1 = đã đọc |
| created_at | DATETIME | Thời gian gửi |

### Bảng `categories` — Danh mục
| Cột | Kiểu | Mô tả |
|-----|------|-------|
| id | INTEGER | Primary key |
| slug | TEXT | URL slug |
| name | TEXT | Tên hiển thị |
| icon | TEXT | Emoji icon |
| sort_order | INTEGER | Thứ tự sắp xếp |

---

## 📡 REST API Endpoints

### Public (không cần auth)

```
GET  /api/posts              Danh sách bài viết
GET  /api/posts?q=keyword    Tìm kiếm
GET  /api/posts?category=xxx Lọc theo danh mục
GET  /api/posts?limit=10&offset=0
GET  /api/posts/<slug>       Chi tiết 1 bài (tự tăng view_count)
POST /api/contact            Gửi tin nhắn liên hệ
```

**Ví dụ request Contact:**
```json
POST /api/contact
{
  "name": "Nguyễn Thị A",
  "email": "a@gmail.com",
  "subject": "Hỏi về sản phẩm",
  "message": "Tôi muốn hỏi về..."
}
```

### Admin (cần đăng nhập session)

```
GET  /api/admin/stats        Thống kê tổng quan
```

---

## 🎛️ Admin Panel

### Dashboard
- Thống kê tổng quan (số bài, lượt xem, tin nhắn chưa đọc)
- Tin nhắn mới nhất
- Top bài viết nhiều lượt xem nhất

### Quản lý Bài viết
- Danh sách tất cả bài viết với filter/tìm kiếm
- Tạo bài viết mới (hỗ trợ HTML)
- Sửa bài viết (tiêu đề, nội dung, danh mục, ảnh bìa, trạng thái)
- Xóa bài viết
- Bật/tắt trạng thái published/draft
- Preview bài viết trực tiếp

### Quản lý Tin nhắn
- Xem danh sách tất cả tin nhắn
- Filter: tất cả / chưa đọc / đã đọc
- Xem chi tiết tin nhắn (tự đánh dấu đã đọc)
- Trả lời qua email (mở mail client)
- Xóa tin nhắn
- Đánh dấu tất cả đã đọc

### Cài đặt
- Đổi mật khẩu admin
- Thông tin hệ thống

---

## 🔧 Tùy chỉnh

### Đổi port
```python
# Trong app.py, cuối file:
app.run(port=8080)  # Thay 5000 thành port mong muốn
```

### Thêm tài khoản admin (bằng Python)
```python
import sqlite3, hashlib
conn = sqlite3.connect('db/beaudy.db')
conn.execute(
    "INSERT INTO admins (username, password_hash, display_name) VALUES (?, ?, ?)",
    ('newadmin', hashlib.sha256('password123'.encode()).hexdigest(), 'Admin 2')
)
conn.commit()
```

### Deploy lên server thực
1. Dùng **Gunicorn** thay Flask dev server:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```
2. Đặt Nginx làm reverse proxy
3. Đổi `app.secret_key` thành chuỗi ngẫu nhiên
4. Bật HTTPS

---

## 📝 Notes

- Database SQLite nằm tại `db/beaudy.db` — backup file này để giữ dữ liệu
- 50 bài viết gốc được tự động import khi khởi tạo
- Form liên hệ tại `/lien-he.html` đã được patch tự động để gọi API thay vì alert()
- Tất cả ảnh gốc trong `public/images/` được serve tự động
