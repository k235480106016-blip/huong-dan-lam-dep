"""
Khởi tạo database SQLite cho Beaudy
"""
import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'beaudy.db')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Bảng tài khoản admin
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Bảng bài viết
    c.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            excerpt TEXT,
            content TEXT,
            cover_image TEXT,
            author TEXT DEFAULT 'Admin',
            status TEXT DEFAULT 'published',
            view_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Bảng tin nhắn liên hệ
    c.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            replied_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Bảng danh mục
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            icon TEXT DEFAULT '📝',
            sort_order INTEGER DEFAULT 0
        )
    ''')

    # Bảng đăng ký nhận tin
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tạo admin mặc định nếu chưa có
    c.execute("SELECT COUNT(*) FROM admins")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO admins (username, password_hash, display_name) VALUES (?, ?, ?)",
            ('admin', hash_password('admin123'), 'Quản trị viên')
        )
        print("✅ Tạo admin mặc định: admin / admin123")

    # Tạo danh mục mặc định
    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        cats = [
            ('lam-dep-da', 'Làm đẹp da', '✨', 1),
            ('cham-soc-toc', 'Chăm sóc tóc', '💇', 2),
            ('my-pham', 'Mỹ phẩm', '💄', 3),
            ('trang-diem', 'Trang điểm', '💅', 4),
            ('thoi-trang', 'Thời trang', '👗', 5),
            ('spa', 'Spa & Thẩm mỹ', '🌸', 6),
        ]
        c.executemany(
            "INSERT INTO categories (slug, name, icon, sort_order) VALUES (?, ?, ?, ?)",
            cats
        )
        print("✅ Tạo danh mục mặc định")

    # Import bài viết mẫu từ HTML files
    import_sample_posts(c)

    conn.commit()
    conn.close()
    print(f"✅ Database khởi tạo tại: {DB_PATH}")

def import_sample_posts(c):
    """Import metadata bài viết từ các file HTML"""
    import re, glob, os

    public_dir = os.path.join(os.path.dirname(__file__), '..', 'public')
    pattern = os.path.join(public_dir, 'bai-viet-*.html')
    files = glob.glob(pattern)

    c.execute("SELECT COUNT(*) FROM posts")
    if c.fetchone()[0] > 0:
        return

    cat_map = {
        'toc': 'cham-soc-toc',
        'nail': 'trang-diem',
        'son': 'trang-diem',
        'da': 'lam-dep-da',
        'spa': 'spa',
        'salon': 'spa',
        'sneaker': 'thoi-trang',
        'phoi-do': 'thoi-trang',
        'vay': 'thoi-trang',
        'review': 'my-pham',
        'cushion': 'my-pham',
        'serum': 'my-pham',
        'peptides': 'lam-dep-da',
        'mat-na': 'lam-dep-da',
        'chay-nang': 'lam-dep-da',
        'facial': 'lam-dep-da',
        'tham-my': 'spa',
    }

    for filepath in sorted(files):
        filename = os.path.basename(filepath)
        slug = filename.replace('.html', '')

        # Xác định category
        category = 'lam-dep-da'
        for key, cat in cat_map.items():
            if key in slug:
                category = cat
                break

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                html = f.read()

            # Extract title
            title_m = re.search(r'<title>(.*?)</title>', html)
            title = title_m.group(1) if title_m else slug

            # Extract h1
            h1_m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
            if h1_m:
                title = re.sub(r'<[^>]+>', '', h1_m.group(1)).strip()

            # Extract excerpt
            excerpt_m = re.search(r'<p class="card-excerpt">(.*?)</p>', html)
            if not excerpt_m:
                excerpt_m = re.search(r'<div class="article-body">\s*<p>(.*?)</p>', html, re.DOTALL)
            excerpt = re.sub(r'<[^>]+>', '', excerpt_m.group(1)).strip()[:200] if excerpt_m else ''

            # Extract cover image
            img_m = re.search(r'class="article-cover".*?src="(images/[^"]+)"', html, re.DOTALL)
            if not img_m:
                img_m = re.search(r'src="(images/[^"]+)"', html)
            cover_image = img_m.group(1) if img_m else ''

            # Extract category label
            cat_m = re.search(r'<span class="card-category">(.*?)</span>', html)
            cat_label = cat_m.group(1) if cat_m else category

            c.execute('''
                INSERT OR IGNORE INTO posts 
                (slug, title, category, excerpt, cover_image, author, status, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (slug, title, cat_label, excerpt, cover_image, 'hoangdinhdiep', 'published', html))

        except Exception as e:
            print(f"  ⚠ Skip {filename}: {e}")

    c.execute("SELECT COUNT(*) FROM posts")
    count = c.fetchone()[0]
    print(f"✅ Import {count} bài viết")

if __name__ == '__main__':
    init_db()
