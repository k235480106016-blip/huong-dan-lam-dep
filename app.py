"""
Beaudy Backend — Flask + SQLite
Chạy: python app.py
"""
import os, sys, json, hashlib, re
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, jsonify, session, redirect,
    url_for, send_from_directory, abort, make_response
)

# ── Paths ────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_DIR     = os.path.join(BASE_DIR, 'db')
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads-img')
ADMIN_DIR  = os.path.join(BASE_DIR, 'admin')
DB_PATH    = os.path.join(DB_DIR, 'beaudy.db')

# Khởi tạo DB nếu chưa có
if not os.path.exists(DB_PATH):
    sys.path.insert(0, DB_DIR)
    from init_db import init_db
    init_db()

import sqlite3

app = Flask(__name__, static_folder=None)
app.secret_key = 'beaudy-secret-key-2026-change-in-production'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# Vietnamese search helper
# ─────────────────────────────────────────────
def viet_normalize(s):
    """Convert Vietnamese with diacritics to ASCII for slug-style matching"""
    import unicodedata
    s = s.lower().replace('đ', 'd').replace('Đ', 'd')
    # NFD decompose then strip combining diacritical marks
    nfkd = unicodedata.normalize('NFD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

def build_search_conditions(search, base_conditions=None):
    """Build SQL conditions for Vietnamese-aware search"""
    conditions = list(base_conditions or [])
    params = []
    if search:
        norm = viet_normalize(search)
        # Search both original (accented) and normalized slug
        conditions.append(
            "(title LIKE ? OR excerpt LIKE ? OR slug LIKE ? OR "
            "title LIKE ? OR excerpt LIKE ? OR content LIKE ?)"
        )
        params.extend([
            f'%{search}%', f'%{search}%', f'%{norm}%',
            f'%{norm}%',  f'%{norm}%',  f'%{search}%'
        ])
    return conditions, params

# ─────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ─────────────────────────────────────────────
# Auth decorator
# ─────────────────────────────────────────────
def require_login(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get('admin_id'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Chưa đăng nhập'}), 401
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return wrapper

# ─────────────────────────────────────────────
# Serve public website files
# ─────────────────────────────────────────────
@app.route('/')
@app.route('/index.html')
def home():
    return send_from_directory(PUBLIC_DIR, 'index.html')

@app.route('/<path:filename>')
def public_files(filename):
    # Cho phép serve HTML, CSS, JS, images
    filepath = os.path.join(PUBLIC_DIR, filename)
    if os.path.isfile(filepath):
        return send_from_directory(PUBLIC_DIR, filename)
    abort(404)

# ─────────────────────────────────────────────
# API — Contact Form
# ─────────────────────────────────────────────
@app.route('/api/contact', methods=['POST'])
def api_contact():
    data = request.get_json() or {}
    name    = data.get('name', '').strip()
    email   = data.get('email', '').strip()
    subject = data.get('subject', '').strip()
    message = data.get('message', '').strip()

    if not name or not email or not message:
        return jsonify({'ok': False, 'error': 'Vui lòng điền đầy đủ họ tên, email và nội dung'}), 400

    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'ok': False, 'error': 'Email không hợp lệ'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)',
        (name, email, subject, message)
    )
    db.commit()
    db.close()
    return jsonify({'ok': True, 'message': 'Tin nhắn đã được gửi thành công! Chúng tôi sẽ phản hồi trong 24-48h. 🌸'})

# ─────────────────────────────────────────────
# API — Newsletter Subscribe
# ─────────────────────────────────────────────
@app.route('/api/subscribe', methods=['POST'])
def api_subscribe():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
        return jsonify({'ok': False, 'error': 'Email không hợp lệ'}), 400

    db = get_db()
    try:
        db.execute('INSERT INTO subscribers (email) VALUES (?)', (email,))
        db.commit()
        db.close()
        return jsonify({'ok': True, 'message': 'Đăng ký thành công!'})
    except Exception:
        db.close()
        return jsonify({'ok': False, 'error': 'Email này đã đăng ký trước đó!'})



# ─────────────────────────────────────────────
# API — Posts (public)
# ─────────────────────────────────────────────
@app.route('/api/posts')
def api_posts():
    category = request.args.get('category', '')
    limit    = min(int(request.args.get('limit', 20)), 100)
    offset   = int(request.args.get('offset', 0))
    search   = request.args.get('q', '')

    db = get_db()
    conditions = ["status = 'published'"]
    params = []

    if category:
        conditions.append("category LIKE ?")
        params.append(f'%{category}%')
    if search:
        norm = viet_normalize(search)
        conditions.append(
            "(title LIKE ? OR title_norm LIKE ? OR "
            "excerpt LIKE ? OR excerpt_norm LIKE ? OR "
            "slug LIKE ? OR content LIKE ?)"
        )
        params.extend([
            f'%{search}%', f'%{norm}%',
            f'%{search}%', f'%{norm}%',
            f'%{norm}%',   f'%{search}%'
        ])

    where = ' AND '.join(conditions)
    rows = db.execute(
        f'SELECT id, slug, title, category, excerpt, cover_image, author, view_count, created_at '
        f'FROM posts WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?',
        params + [limit, offset]
    ).fetchall()

    total = db.execute(f'SELECT COUNT(*) FROM posts WHERE {where}', params).fetchone()[0]
    db.close()

    return jsonify({
        'posts': [dict(r) for r in rows],
        'total': total
    })

@app.route('/api/posts/<slug>')
def api_post_detail(slug):
    db = get_db()
    row = db.execute(
        "SELECT * FROM posts WHERE slug = ? AND status = 'published'", (slug,)
    ).fetchone()

    if not row:
        db.close()
        return jsonify({'error': 'Không tìm thấy bài viết'}), 404

    # Tăng view count
    db.execute('UPDATE posts SET view_count = view_count + 1 WHERE slug = ?', (slug,))
    db.commit()
    db.close()
    return jsonify(dict(row))

# ─────────────────────────────────────────────
# Admin — Login/Logout
# ─────────────────────────────────────────────
@app.route('/admin')
@app.route('/admin/')
def admin_index():
    if session.get('admin_id'):
        return redirect('/admin/dashboard')
    return redirect('/admin/login')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')

        db = get_db()
        admin = db.execute(
            'SELECT * FROM admins WHERE username = ? AND password_hash = ?',
            (username, hash_password(password))
        ).fetchone()
        db.close()

        if admin:
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['display_name'] or admin['username']
            return redirect('/admin/dashboard')
        error = 'Tên đăng nhập hoặc mật khẩu không đúng'

    return render_login(error)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect('/admin/login')

# ─────────────────────────────────────────────
# Admin — Dashboard
# ─────────────────────────────────────────────
@app.route('/admin/dashboard')
@require_login
def admin_dashboard():
    db = get_db()
    stats = {
        'posts':       db.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
        'contacts':    db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
        'unread':      db.execute("SELECT COUNT(*) FROM contacts WHERE is_read=0").fetchone()[0],
        'views':       db.execute("SELECT COALESCE(SUM(view_count),0) FROM posts").fetchone()[0],
        'subscribers': db.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0],
    }
    recent_contacts = db.execute(
        "SELECT * FROM contacts ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    top_posts = db.execute(
        "SELECT slug, title, view_count, category FROM posts ORDER BY view_count DESC LIMIT 5"
    ).fetchall()
    db.close()

    return render_admin_page('dashboard', stats=stats,
        recent_contacts=[dict(r) for r in recent_contacts],
        top_posts=[dict(r) for r in top_posts])

# ─────────────────────────────────────────────
# Admin — Posts CRUD
# ─────────────────────────────────────────────
@app.route('/admin/posts')
@require_login
def admin_posts():
    search   = request.args.get('q', '')
    category = request.args.get('category', '')
    page     = max(int(request.args.get('page', 1)), 1)
    per_page = 20

    db = get_db()
    conditions = ['1=1']
    params = []
    if search:
        norm = viet_normalize(search)
        conditions.append("(title LIKE ? OR title_norm LIKE ? OR excerpt LIKE ? OR excerpt_norm LIKE ?)")
        params.extend([f'%{search}%', f'%{norm}%', f'%{search}%', f'%{norm}%'])
    if category:
        conditions.append("category LIKE ?")
        params.append(f'%{category}%')

    where = ' AND '.join(conditions)
    total = db.execute(f'SELECT COUNT(*) FROM posts WHERE {where}', params).fetchone()[0]
    posts = db.execute(
        f'SELECT id, slug, title, category, status, view_count, created_at, cover_image '
        f'FROM posts WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?',
        params + [per_page, (page-1)*per_page]
    ).fetchall()
    cats = db.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()
    db.close()

    return render_admin_page('posts', posts=[dict(r) for r in posts],
        total=total, page=page, per_page=per_page,
        categories=[dict(c) for c in cats], search=search, category=category)

@app.route('/admin/posts/new', methods=['GET', 'POST'])
@require_login
def admin_post_new():
    db = get_db()
    if request.method == 'POST':
        slug    = request.form.get('slug', '').strip().lower()
        title   = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        excerpt = request.form.get('excerpt', '').strip()
        content = request.form.get('content', '').strip()
        cover   = request.form.get('cover_image', '').strip()
        status  = request.form.get('status', 'published')
        author  = session.get('admin_name', 'Admin')

        if not slug or not title:
            cats = db.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()
            db.close()
            return render_admin_page('post_edit', post=None, error='Slug và tiêu đề là bắt buộc',
                categories=[dict(c) for c in cats])

        # Tạo slug nếu trống
        slug = re.sub(r'[^a-z0-9-]', '', slug.replace(' ', '-'))

        try:
            title_norm  = viet_normalize(title)
            excerpt_norm = viet_normalize(excerpt)
            db.execute('''
                INSERT INTO posts (slug, title, title_norm, category, excerpt, excerpt_norm, content, cover_image, author, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (slug, title, title_norm, category, excerpt, excerpt_norm, content, cover, author, status))
            db.commit()
            db.close()
            return redirect('/admin/posts?success=created')
        except sqlite3.IntegrityError:
            cats = db.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()
            db.close()
            return render_admin_page('post_edit', post=None, error='Slug đã tồn tại',
                categories=[dict(c) for c in cats])

    cats = db.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()
    db.close()
    return render_admin_page('post_edit', post=None, categories=[dict(c) for c in cats])

@app.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@require_login
def admin_post_edit(post_id):
    db = get_db()
    post = db.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if not post:
        db.close()
        abort(404)

    if request.method == 'POST':
        title    = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        excerpt  = request.form.get('excerpt', '').strip()
        content  = request.form.get('content', '').strip()
        cover    = request.form.get('cover_image', '').strip()
        status   = request.form.get('status', 'published')

        title_norm_u  = viet_normalize(title)
        excerpt_norm_u = viet_normalize(excerpt)
        db.execute('''
            UPDATE posts SET title=?, title_norm=?, category=?, excerpt=?, excerpt_norm=?,
            content=?, cover_image=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?
        ''', (title, title_norm_u, category, excerpt, excerpt_norm_u, content, cover, status, post_id))
        db.commit()
        db.close()
        return redirect(f'/admin/posts?success=updated')

    cats = db.execute('SELECT * FROM categories ORDER BY sort_order').fetchall()
    db.close()
    return render_admin_page('post_edit', post=dict(post),
        categories=[dict(c) for c in cats])

@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@require_login
def admin_post_delete(post_id):
    db = get_db()
    db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    db.commit()
    db.close()
    return redirect('/admin/posts?success=deleted')

@app.route('/admin/posts/<int:post_id>/toggle', methods=['POST'])
@require_login
def admin_post_toggle(post_id):
    db = get_db()
    post = db.execute('SELECT status FROM posts WHERE id=?', (post_id,)).fetchone()
    if post:
        new_status = 'draft' if post['status'] == 'published' else 'published'
        db.execute('UPDATE posts SET status=? WHERE id=?', (new_status, post_id))
        db.commit()
    db.close()
    return redirect('/admin/posts')

# ─────────────────────────────────────────────
# Admin — Contacts
# ─────────────────────────────────────────────
@app.route('/admin/contacts')
@require_login
def admin_contacts():
    filter_read = request.args.get('filter', '')
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 20

    db = get_db()
    conditions = ['1=1']
    params = []
    if filter_read == 'unread':
        conditions.append('is_read = 0')
    elif filter_read == 'read':
        conditions.append('is_read = 1')

    where = ' AND '.join(conditions)
    total = db.execute(f'SELECT COUNT(*) FROM contacts WHERE {where}', params).fetchone()[0]
    contacts = db.execute(
        f'SELECT * FROM contacts WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?',
        params + [per_page, (page-1)*per_page]
    ).fetchall()
    unread_count = db.execute('SELECT COUNT(*) FROM contacts WHERE is_read=0').fetchone()[0]
    db.close()

    return render_admin_page('contacts', contacts=[dict(c) for c in contacts],
        total=total, page=page, per_page=per_page,
        filter_read=filter_read, unread_count=unread_count)

@app.route('/admin/contacts/<int:contact_id>')
@require_login
def admin_contact_detail(contact_id):
    db = get_db()
    contact = db.execute('SELECT * FROM contacts WHERE id=?', (contact_id,)).fetchone()
    if not contact:
        db.close()
        abort(404)
    # Đánh dấu đã đọc
    db.execute('UPDATE contacts SET is_read=1 WHERE id=?', (contact_id,))
    db.commit()
    db.close()
    return render_admin_page('contact_detail', contact=dict(contact))

@app.route('/admin/contacts/<int:contact_id>/delete', methods=['POST'])
@require_login
def admin_contact_delete(contact_id):
    db = get_db()
    db.execute('DELETE FROM contacts WHERE id=?', (contact_id,))
    db.commit()
    db.close()
    return redirect('/admin/contacts')

@app.route('/admin/contacts/mark-all-read', methods=['POST'])
@require_login
def admin_mark_all_read():
    db = get_db()
    db.execute('UPDATE contacts SET is_read=1')
    db.commit()
    db.close()
    return redirect('/admin/contacts')

# ─────────────────────────────────────────────
# Admin — Settings (đổi mật khẩu)
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# Admin — Subscribers
# ─────────────────────────────────────────────
@app.route('/admin/subscribers')
@require_login
def admin_subscribers():
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 30
    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM subscribers').fetchone()[0]
    subs  = db.execute(
        'SELECT * FROM subscribers ORDER BY created_at DESC LIMIT ? OFFSET ?',
        (per_page, (page-1)*per_page)
    ).fetchall()
    db.close()
    return render_admin_page('subscribers', subs=[dict(s) for s in subs],
        total=total, page=page, per_page=per_page)

@app.route('/admin/subscribers/<int:sub_id>/delete', methods=['POST'])
@require_login
def admin_subscriber_delete(sub_id):
    db = get_db()
    db.execute('DELETE FROM subscribers WHERE id=?', (sub_id,))
    db.commit()
    db.close()
    return redirect('/admin/subscribers')

@app.route('/admin/settings', methods=['GET', 'POST'])
@require_login
def admin_settings():
    msg = ''
    error = ''
    if request.method == 'POST':
        old_pw  = request.form.get('old_password', '')
        new_pw  = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        db = get_db()
        admin = db.execute(
            'SELECT * FROM admins WHERE id=? AND password_hash=?',
            (session['admin_id'], hash_password(old_pw))
        ).fetchone()

        if not admin:
            error = 'Mật khẩu hiện tại không đúng'
        elif len(new_pw) < 6:
            error = 'Mật khẩu mới phải ít nhất 6 ký tự'
        elif new_pw != confirm:
            error = 'Xác nhận mật khẩu không khớp'
        else:
            db.execute('UPDATE admins SET password_hash=? WHERE id=?',
                (hash_password(new_pw), session['admin_id']))
            db.commit()
            msg = 'Đổi mật khẩu thành công!'
        db.close()

    return render_admin_page('settings', msg=msg, error=error)

# ─────────────────────────────────────────────
# API — Admin endpoints (JSON)
# ─────────────────────────────────────────────
@app.route('/api/admin/stats')
@require_login
def api_admin_stats():
    db = get_db()
    data = {
        'posts':    db.execute("SELECT COUNT(*) FROM posts").fetchone()[0],
        'published': db.execute("SELECT COUNT(*) FROM posts WHERE status='published'").fetchone()[0],
        'contacts': db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
        'unread':   db.execute("SELECT COUNT(*) FROM contacts WHERE is_read=0").fetchone()[0],
        'total_views': db.execute("SELECT COALESCE(SUM(view_count),0) FROM posts").fetchone()[0],
    }
    db.close()
    return jsonify(data)

# ─────────────────────────────────────────────
# HTML Rendering helpers
# ─────────────────────────────────────────────
def render_login(error=''):
    return f'''<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admin Login – Hướng dẫn làm đẹp</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Nunito',sans-serif;background:linear-gradient(135deg,#fff0f3,#ffe4ec,#fff8e1);min-height:100vh;display:flex;align-items:center;justify-content:center}}
.card{{background:white;border-radius:20px;padding:48px 40px;width:100%;max-width:400px;box-shadow:0 20px 60px rgba(232,84,122,.15)}}
.logo{{text-align:center;margin-bottom:32px}}
.logo h1{{font-size:32px;color:#e8547a;font-weight:700}}
.logo p{{color:#6b6b7b;font-size:14px;margin-top:6px}}
.form-group{{margin-bottom:20px}}
label{{display:block;font-size:13px;font-weight:600;color:#1a1a2e;margin-bottom:8px}}
input{{width:100%;padding:12px 16px;border:1.5px solid #e8e8f0;border-radius:10px;font-family:inherit;font-size:14px;transition:all .2s}}
input:focus{{outline:none;border-color:#e8547a;box-shadow:0 0 0 3px rgba(232,84,122,.1)}}
.btn{{width:100%;padding:14px;background:linear-gradient(135deg,#e8547a,#c62a54);color:white;border:none;border-radius:10px;font-family:inherit;font-size:15px;font-weight:700;cursor:pointer;transition:all .2s}}
.btn:hover{{transform:translateY(-1px);box-shadow:0 6px 20px rgba(232,84,122,.35)}}
.error{{background:#fff0f0;color:#e53e3e;padding:12px 16px;border-radius:8px;font-size:13px;margin-bottom:20px;border:1px solid #fed7d7}}
.hint{{text-align:center;margin-top:20px;font-size:12px;color:#aaa}}
</style>
</head>
<body>
<div class="card">
  <div class="logo">
    <h1>🌸 Hướng dẫn làm đẹp</h1>
    <p>Trang quản trị nội dung</p>
  </div>
  {'<div class="error">⚠ '+error+'</div>' if error else ''}
  <form method="POST">
    <div class="form-group">
      <label>Tên đăng nhập</label>
      <input type="text" name="username" placeholder="admin" required autofocus>
    </div>
    <div class="form-group">
      <label>Mật khẩu</label>
      <input type="password" name="password" placeholder="••••••••" required>
    </div>
    <button class="btn" type="submit">🔐 Đăng nhập</button>
  </form>
  <p class="hint">Mặc định: admin / admin123</p>
</div>
</body>
</html>'''

def render_admin_page(page_name, **ctx):
    admin_name = session.get('admin_name', 'Admin')

    # Lấy unread count cho badge
    db = get_db()
    unread = db.execute("SELECT COUNT(*) FROM contacts WHERE is_read=0").fetchone()[0]
    db.close()

    nav_items = [
        ('dashboard', '📊', 'Dashboard', '/admin/dashboard'),
        ('posts', '📝', 'Bài viết', '/admin/posts'),
        ('contacts', '📬', f'Tin nhắn {"<span class=badge>"+str(unread)+"</span>" if unread else ""}', '/admin/contacts'),
        ('subscribers', '📧', 'Đăng ký nhận tin', '/admin/subscribers'),
        ('settings', '⚙️', 'Cài đặt', '/admin/settings'),
    ]

    nav_html = ''
    for key, icon, label, href in nav_items:
        active = 'active' if page_name == key else ''
        nav_html += f'<a href="{href}" class="nav-item {active}">{icon} {label}</a>'

    content = render_page_content(page_name, **ctx)

    return f'''<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Admin – Hướng dẫn làm đẹp</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
{get_admin_css()}
</style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="sidebar-logo">🌸 Hướng dẫn làm đẹp</div>
    <nav class="sidebar-nav">
      {nav_html}
    </nav>
    <div class="sidebar-footer">
      <div class="admin-info">👤 {admin_name}</div>
      <a href="/admin/logout" class="logout-btn">🚪 Đăng xuất</a>
    </div>
  </aside>
  <main class="main-content">
    {content}
  </main>
</div>
<script>{get_admin_js()}</script>
</body>
</html>'''

def render_page_content(page_name, **ctx):
    if page_name == 'dashboard':
        return render_dashboard(**ctx)
    elif page_name == 'posts':
        return render_posts_list(**ctx)
    elif page_name == 'post_edit':
        return render_post_edit(**ctx)
    elif page_name == 'contacts':
        return render_contacts_list(**ctx)
    elif page_name == 'contact_detail':
        return render_contact_detail(**ctx)
    elif page_name == 'settings':
        return render_settings(**ctx)
    elif page_name == 'subscribers':
        return render_subscribers(**ctx)
    return '<p>Page not found</p>'

def render_dashboard(stats, recent_contacts, top_posts, **kw):
    rc_rows = ''
    for c in recent_contacts:
        badge = '<span class="badge-unread">Mới</span>' if not c['is_read'] else ''
        rc_rows += f'''
        <tr>
          <td><strong>{c["name"]}</strong> {badge}</td>
          <td>{c["email"]}</td>
          <td>{c["subject"] or "—"}</td>
          <td>{c["created_at"][:16]}</td>
          <td><a href="/admin/contacts/{c["id"]}" class="btn-sm">Xem</a></td>
        </tr>'''

    tp_rows = ''
    for p in top_posts:
        tp_rows += f'''
        <tr>
          <td><a href="/{p["slug"]}.html" target="_blank">{p["title"][:50]}...</a></td>
          <td><span class="tag">{p["category"]}</span></td>
          <td>👁 {p["view_count"]}</td>
        </tr>'''

    return f'''
<div class="page-header">
  <h1>📊 Dashboard</h1>
</div>
<div class="stats-grid">
  <div class="stat-card pink">
    <div class="stat-icon">📝</div>
    <div class="stat-val">{stats["posts"]}</div>
    <div class="stat-label">Tổng bài viết</div>
  </div>
  <div class="stat-card gold">
    <div class="stat-icon">👁</div>
    <div class="stat-val">{stats["views"]:,}</div>
    <div class="stat-label">Lượt xem</div>
  </div>
  <div class="stat-card blue">
    <div class="stat-icon">📬</div>
    <div class="stat-val">{stats["contacts"]}</div>
    <div class="stat-label">Tin nhắn</div>
  </div>
  <div class="stat-card red">
    <div class="stat-icon">🔔</div>
    <div class="stat-val">{stats["unread"]}</div>
    <div class="stat-label">Chưa đọc</div>
  </div>
  <div class="stat-card green">
    <div class="stat-icon">📧</div>
    <div class="stat-val">{stats["subscribers"]}</div>
    <div class="stat-label">Người đăng ký</div>
  </div>
</div>
<div class="two-col-grid">
  <div class="card">
    <div class="card-header">📬 Tin nhắn gần đây</div>
    <table class="table">
      <thead><tr><th>Tên</th><th>Email</th><th>Chủ đề</th><th>Thời gian</th><th></th></tr></thead>
      <tbody>{rc_rows or "<tr><td colspan=5 class=empty>Chưa có tin nhắn nào</td></tr>"}</tbody>
    </table>
    <a href="/admin/contacts" class="view-all-link">Xem tất cả →</a>
  </div>
  <div class="card">
    <div class="card-header">🔥 Bài viết nhiều lượt xem</div>
    <table class="table">
      <thead><tr><th>Tiêu đề</th><th>Danh mục</th><th>Lượt xem</th></tr></thead>
      <tbody>{tp_rows or "<tr><td colspan=3 class=empty>Chưa có dữ liệu</td></tr>"}</tbody>
    </table>
    <a href="/admin/posts" class="view-all-link">Xem tất cả →</a>
  </div>
</div>'''

def render_posts_list(posts, total, page, per_page, categories, search, category, **kw):
    success = request.args.get('success', '')
    success_msg = {'created': '✅ Tạo bài viết thành công!', 'updated': '✅ Cập nhật thành công!', 'deleted': '✅ Đã xóa bài viết!'}.get(success, '')

    cat_opts = '<option value="">Tất cả danh mục</option>'
    for c in categories:
        sel = 'selected' if c['slug'] == category or c['name'] == category else ''
        cat_opts += f'<option value="{c["slug"]}" {sel}>{c["icon"]} {c["name"]}</option>'

    rows = ''
    for p in posts:
        status_badge = '<span class="badge-pub">Đã đăng</span>' if p['status'] == 'published' else '<span class="badge-draft">Nháp</span>'
        img = f'<img src="/{p["cover_image"]}" style="width:50px;height:36px;object-fit:cover;border-radius:4px">' if p.get('cover_image') else '🖼'
        rows += f'''
        <tr>
          <td>{img}</td>
          <td><a href="/admin/posts/{p["id"]}/edit" class="post-title">{p["title"][:60]}</a></td>
          <td><span class="tag">{p["category"]}</span></td>
          <td>{status_badge}</td>
          <td>👁 {p["view_count"]}</td>
          <td>{p["created_at"][:10]}</td>
          <td class="actions">
            <a href="/admin/posts/{p["id"]}/edit" class="btn-sm">✏️</a>
            <a href="/{p["slug"]}.html" target="_blank" class="btn-sm">👁</a>
            <form method="POST" action="/admin/posts/{p["id"]}/toggle" style="display:inline">
              <button class="btn-sm {'btn-draft' if p['status']=='published' else 'btn-pub'}">
                {'📤' if p['status']=='published' else '✅'}
              </button>
            </form>
            <form method="POST" action="/admin/posts/{p["id"]}/delete" style="display:inline"
              onsubmit="return confirm('Xóa bài viết này?')">
              <button class="btn-sm btn-danger">🗑</button>
            </form>
          </td>
        </tr>'''

    total_pages = (total + per_page - 1) // per_page
    pagination = ''
    for i in range(1, total_pages + 1):
        active = 'active' if i == page else ''
        pagination += f'<a href="?page={i}&q={search}&category={category}" class="page-btn {active}">{i}</a>'

    return f'''
<div class="page-header">
  <h1>📝 Bài viết</h1>
  <a href="/admin/posts/new" class="btn-primary">+ Thêm bài mới</a>
</div>
{f'<div class="alert-success">{success_msg}</div>' if success_msg else ''}
<div class="card">
  <div class="filters">
    <form method="GET" style="display:flex;gap:12px;flex-wrap:wrap">
      <input name="q" value="{search}" placeholder="🔍 Tìm bài viết..." class="filter-input">
      <select name="category" class="filter-select">{cat_opts}</select>
      <button type="submit" class="btn-primary">Lọc</button>
      <a href="/admin/posts" class="btn-outline">Reset</a>
    </form>
  </div>
  <div class="table-info">Hiển thị {len(posts)}/{total} bài viết</div>
  <table class="table">
    <thead><tr><th>Ảnh</th><th>Tiêu đề</th><th>Danh mục</th><th>Trạng thái</th><th>Lượt xem</th><th>Ngày tạo</th><th>Thao tác</th></tr></thead>
    <tbody>{rows or "<tr><td colspan=7 class=empty>Không có bài viết nào</td></tr>"}</tbody>
  </table>
  <div class="pagination">{pagination}</div>
</div>'''

def render_post_edit(post, categories, error='', **kw):
    title_val  = post['title']    if post else ''
    slug_val   = post['slug']     if post else ''
    cat_val    = post['category'] if post else ''
    excerpt_val = post['excerpt'] if post else ''
    content_val = post['content'] if post else ''
    cover_val  = post['cover_image'] if post else ''
    status_val = post['status']   if post else 'published'
    post_id    = post['id']       if post else None
    page_title = '✏️ Sửa bài viết' if post else '+ Tạo bài viết mới'
    action_url = f'/admin/posts/{post_id}/edit' if post else '/admin/posts/new'

    cat_opts = ''
    for c in categories:
        sel = 'selected' if c['name'] == cat_val or c['slug'] == cat_val else ''
        cat_opts += f'<option value="{c["name"]}" {sel}>{c["icon"]} {c["name"]}</option>'

    pub_sel  = 'selected' if status_val == 'published' else ''
    draft_sel = 'selected' if status_val == 'draft' else ''

    preview_img = f'<img src="/{cover_val}" style="max-width:200px;border-radius:8px;margin-top:8px" id="cover-preview">' if cover_val else '<div id="cover-preview"></div>'

    return f'''
<div class="page-header">
  <h1>{page_title}</h1>
  <a href="/admin/posts" class="btn-outline">← Quay lại</a>
</div>
{f'<div class="alert-error">{error}</div>' if error else ''}
<form method="POST" action="{action_url}">
<div class="edit-grid">
  <div class="edit-main">
    <div class="card">
      <div class="form-group">
        <label>Tiêu đề bài viết *</label>
        <input type="text" name="title" value="{html_escape(title_val)}" 
          placeholder="Nhập tiêu đề hấp dẫn..." required class="form-input"
          oninput="autoSlug(this.value)">
      </div>
      <div class="form-group">
        <label>Slug (URL) *</label>
        <div style="display:flex;gap:8px">
          <span style="padding:10px 14px;background:#f5f5f8;border-radius:8px;font-size:13px;color:#888">bai-viet-</span>
          <input type="text" name="slug" id="slug-input" value="{html_escape(slug_val)}" 
            placeholder="ten-bai-viet" required class="form-input" style="flex:1">
        </div>
      </div>
      <div class="form-group">
        <label>Tóm tắt</label>
        <textarea name="excerpt" rows="3" placeholder="Mô tả ngắn về bài viết..." 
          class="form-input">{html_escape(excerpt_val)}</textarea>
      </div>
      <div class="form-group">
        <label>Nội dung (HTML)</label>
        <textarea name="content" rows="20" placeholder="Nhập nội dung HTML..." 
          class="form-input code-input">{html_escape(content_val)}</textarea>
        <p class="field-hint">💡 Hỗ trợ HTML đầy đủ. Có thể paste nội dung từ bài viết sẵn có.</p>
      </div>
    </div>
  </div>
  <div class="edit-sidebar">
    <div class="card">
      <div class="card-header">Xuất bản</div>
      <div class="form-group">
        <label>Trạng thái</label>
        <select name="status" class="form-input">
          <option value="published" {pub_sel}>✅ Đã đăng</option>
          <option value="draft" {draft_sel}>📋 Nháp</option>
        </select>
      </div>
      <button type="submit" class="btn-primary full-width">
        💾 {'Cập nhật' if post else 'Tạo bài viết'}
      </button>
    </div>
    <div class="card">
      <div class="card-header">Phân loại</div>
      <div class="form-group">
        <label>Danh mục</label>
        <select name="category" class="form-input">{cat_opts}</select>
      </div>
    </div>
    <div class="card">
      <div class="card-header">Ảnh bìa</div>
      <div class="form-group">
        <input type="text" name="cover_image" value="{html_escape(cover_val)}"
          placeholder="images/ten-anh.webp" class="form-input"
          oninput="previewCover(this.value)">
        {preview_img}
        <p class="field-hint">Đường dẫn ảnh trong thư mục images/</p>
      </div>
    </div>
  </div>
</div>
</form>'''

def render_contacts_list(contacts, total, page, per_page, filter_read, unread_count, **kw):
    rows = ''
    for c in contacts:
        badge = '<span class="badge-unread">Mới</span>' if not c['is_read'] else ''
        rows += f'''
        <tr class="{'row-unread' if not c['is_read'] else ''}">
          <td><strong>{c["name"]}</strong> {badge}</td>
          <td>{c["email"]}</td>
          <td>{c["subject"] or "—"}</td>
          <td>{c["message"][:60]}...</td>
          <td>{c["created_at"][:16]}</td>
          <td class="actions">
            <a href="/admin/contacts/{c["id"]}" class="btn-sm">👁 Xem</a>
            <form method="POST" action="/admin/contacts/{c["id"]}/delete" style="display:inline"
              onsubmit="return confirm('Xóa tin nhắn này?')">
              <button class="btn-sm btn-danger">🗑</button>
            </form>
          </td>
        </tr>'''

    total_pages = (total + per_page - 1) // per_page
    pagination = ''
    for i in range(1, total_pages + 1):
        active = 'active' if i == page else ''
        pagination += f'<a href="?page={i}&filter={filter_read}" class="page-btn {active}">{i}</a>'

    unread_active = 'active' if filter_read == 'unread' else ''
    all_active    = 'active' if not filter_read else ''
    read_active   = 'active' if filter_read == 'read' else ''

    return f'''
<div class="page-header">
  <h1>📬 Tin nhắn liên hệ</h1>
  <form method="POST" action="/admin/contacts/mark-all-read">
    <button class="btn-outline" type="submit">✅ Đánh dấu tất cả đã đọc</button>
  </form>
</div>
<div class="filter-tabs">
  <a href="?filter=" class="tab {all_active}">Tất cả ({total})</a>
  <a href="?filter=unread" class="tab {unread_active}">🔴 Chưa đọc ({unread_count})</a>
  <a href="?filter=read" class="tab {read_active}">✅ Đã đọc</a>
</div>
<div class="card">
  <table class="table">
    <thead><tr><th>Người gửi</th><th>Email</th><th>Chủ đề</th><th>Nội dung</th><th>Thời gian</th><th>Thao tác</th></tr></thead>
    <tbody>{rows or "<tr><td colspan=6 class=empty>Không có tin nhắn nào</td></tr>"}</tbody>
  </table>
  <div class="pagination">{pagination}</div>
</div>'''

def render_contact_detail(contact, **kw):
    read_status = '✅ Đã đọc' if contact['is_read'] else '🔴 Chưa đọc'
    return f'''
<div class="page-header">
  <h1>📬 Chi tiết tin nhắn</h1>
  <a href="/admin/contacts" class="btn-outline">← Quay lại</a>
</div>
<div class="card" style="max-width:700px">
  <div class="contact-detail">
    <div class="detail-row">
      <span class="detail-label">👤 Người gửi</span>
      <span class="detail-val"><strong>{contact["name"]}</strong></span>
    </div>
    <div class="detail-row">
      <span class="detail-label">📧 Email</span>
      <span class="detail-val"><a href="mailto:{contact["email"]}">{contact["email"]}</a></span>
    </div>
    <div class="detail-row">
      <span class="detail-label">📌 Chủ đề</span>
      <span class="detail-val">{contact["subject"] or "—"}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">📅 Thời gian</span>
      <span class="detail-val">{contact["created_at"]}</span>
    </div>
    <div class="detail-row">
      <span class="detail-label">📊 Trạng thái</span>
      <span class="detail-val">{read_status}</span>
    </div>
    <div class="detail-message">
      <div class="detail-label" style="margin-bottom:12px">💬 Nội dung tin nhắn:</div>
      <div class="message-box">{contact["message"]}</div>
    </div>
    <div style="display:flex;gap:12px;margin-top:24px">
      <a href="mailto:{contact["email"]}?subject=Re: {contact["subject"] or 'Liên hệ từ Hướng dẫn làm đẹp'}" 
        class="btn-primary">📤 Trả lời qua Email</a>
      <form method="POST" action="/admin/contacts/{contact["id"]}/delete"
        onsubmit="return confirm('Xóa tin nhắn này?')">
        <button class="btn-danger-outline">🗑 Xóa</button>
      </form>
    </div>
  </div>
</div>'''

def render_subscribers(subs, total, page, per_page, **kw):
    total_pages = (total + per_page - 1) // per_page
    rows = ''
    for s in subs:
        rows += f"""
        <tr>
          <td>{s["email"]}</td>
          <td>{s["created_at"][:16]}</td>
          <td>
            <form method="POST" action="/admin/subscribers/{s["id"]}/delete" style="display:inline"
              onsubmit="return confirm('Xóa subscriber này?')">
              <button class="btn-sm btn-danger">🗑 Xóa</button>
            </form>
          </td>
        </tr>"""
    pagination = ''.join(
        f'<a href="?page={i}" class="page-btn {"active" if i==page else ""}">{i}</a>'
        for i in range(1, total_pages+1)
    )
    return f"""
<div class="page-header">
  <h1>📧 Danh sách đăng ký nhận tin</h1>
</div>
<div class="card">
  <div class="table-info">Tổng cộng {total} người đăng ký</div>
  <table class="table">
    <thead><tr><th>Email</th><th>Thời gian đăng ký</th><th>Thao tác</th></tr></thead>
    <tbody>{rows or "<tr><td colspan=3 class=empty>Chưa có ai đăng ký</td></tr>"}</tbody>
  </table>
  <div class="pagination">{pagination}</div>
</div>"""


def render_settings(msg='', error='', **kw):
    return f'''
<div class="page-header">
  <h1>⚙️ Cài đặt</h1>
</div>
{f'<div class="alert-success">{msg}</div>' if msg else ''}
{f'<div class="alert-error">{error}</div>' if error else ''}
<div class="card" style="max-width:500px">
  <div class="card-header">🔐 Đổi mật khẩu Admin</div>
  <form method="POST">
    <div class="form-group">
      <label>Mật khẩu hiện tại</label>
      <input type="password" name="old_password" class="form-input" required>
    </div>
    <div class="form-group">
      <label>Mật khẩu mới</label>
      <input type="password" name="new_password" class="form-input" minlength="6" required>
    </div>
    <div class="form-group">
      <label>Xác nhận mật khẩu mới</label>
      <input type="password" name="confirm_password" class="form-input" required>
    </div>
    <button type="submit" class="btn-primary">💾 Đổi mật khẩu</button>
  </form>
</div>
<div class="card" style="max-width:500px;margin-top:20px">
  <div class="card-header">ℹ️ Thông tin hệ thống</div>
  <div class="info-list">
    <div class="info-row"><span>Phiên bản</span><span>Hướng dẫn làm đẹp v8 + Backend</span></div>
    <div class="info-row"><span>Database</span><span>SQLite</span></div>
    <div class="info-row"><span>Backend</span><span>Python Flask</span></div>
    <div class="info-row"><span>Website</span><span><a href="/" target="_blank">Xem trang chủ →</a></span></div>
  </div>
</div>'''

def html_escape(s):
    if not s:
        return ''
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def get_admin_css():
    return '''
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Nunito',sans-serif;background:#f8f9fc;color:#1a1a2e;font-size:14px}
a{color:inherit;text-decoration:none}
.layout{display:flex;min-height:100vh}
/* Sidebar */
.sidebar{width:240px;background:linear-gradient(180deg,#1a1a2e 0%,#16213e 100%);color:white;display:flex;flex-direction:column;position:fixed;height:100vh;z-index:100}
.sidebar-logo{padding:24px 20px;font-size:18px;font-weight:700;border-bottom:1px solid rgba(255,255,255,.1);letter-spacing:-.3px}
.sidebar-nav{flex:1;padding:16px 12px;display:flex;flex-direction:column;gap:4px}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:10px;color:rgba(255,255,255,.7);font-weight:600;font-size:13.5px;transition:all .2s}
.nav-item:hover{background:rgba(255,255,255,.1);color:white}
.nav-item.active{background:linear-gradient(135deg,#e8547a,#c62a54);color:white;box-shadow:0 4px 15px rgba(232,84,122,.4)}
.badge{background:#e8547a;color:white;font-size:11px;padding:2px 7px;border-radius:20px;margin-left:4px}
.sidebar-footer{padding:16px 12px;border-top:1px solid rgba(255,255,255,.1)}
.admin-info{font-size:12px;color:rgba(255,255,255,.5);padding:6px 14px;margin-bottom:8px}
.logout-btn{display:block;padding:10px 14px;border-radius:10px;color:rgba(255,255,255,.7);font-size:13px;font-weight:600;transition:all .2s}
.logout-btn:hover{background:rgba(232,84,122,.2);color:#e8547a}
/* Main */
.main-content{margin-left:240px;flex:1;padding:28px 32px;max-width:calc(100vw - 240px)}
.page-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:28px}
.page-header h1{font-size:24px;font-weight:700}
/* Stats */
.stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:28px}
.stat-card{background:white;border-radius:16px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.06);position:relative;overflow:hidden}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px}
.stat-card.pink::before{background:linear-gradient(90deg,#e8547a,#ff8fa3)}
.stat-card.gold::before{background:linear-gradient(90deg,#d4a853,#f0c97a)}
.stat-card.blue::before{background:linear-gradient(90deg,#4a90d9,#74b4f0)}
.stat-card.red::before{background:linear-gradient(90deg,#e53e3e,#fc8181)}
.stat-card.green::before{background:linear-gradient(90deg,#38a169,#68d391)}
.stat-icon{font-size:28px;margin-bottom:8px}
.stat-val{font-size:32px;font-weight:700;line-height:1}
.stat-label{color:#888;font-size:13px;margin-top:6px}
/* Cards */
.card{background:white;border-radius:16px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.06);margin-bottom:20px}
.card-header{font-weight:700;font-size:15px;margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid #f5f5f8}
/* Tables */
.table{width:100%;border-collapse:collapse}
.table th{text-align:left;padding:10px 12px;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#888;border-bottom:2px solid #f5f5f8}
.table td{padding:12px;border-bottom:1px solid #f9f9f9;vertical-align:middle}
.table tr:hover td{background:#fafafa}
.empty{text-align:center;color:#aaa;padding:32px!important}
.row-unread td{background:#fff8f9}
/* Buttons */
.btn-primary{background:linear-gradient(135deg,#e8547a,#c62a54);color:white;border:none;padding:10px 20px;border-radius:10px;font-family:inherit;font-size:13.5px;font-weight:700;cursor:pointer;display:inline-block;transition:all .2s}
.btn-primary:hover{transform:translateY(-1px);box-shadow:0 4px 15px rgba(232,84,122,.35)}
.btn-primary.full-width{width:100%;text-align:center}
.btn-outline{border:1.5px solid #e8e8f0;color:#6b6b7b;padding:10px 20px;border-radius:10px;font-size:13.5px;font-weight:600;cursor:pointer;display:inline-block;transition:all .2s;background:white}
.btn-outline:hover{border-color:#e8547a;color:#e8547a}
.btn-sm{background:#f5f5f8;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:13px;display:inline-flex;align-items:center;gap:4px;transition:all .2s}
.btn-sm:hover{background:#e8547a;color:white}
.btn-danger{background:#fff0f0;border:1px solid #fed7d7;color:#e53e3e;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:13px}
.btn-danger:hover{background:#e53e3e;color:white}
.btn-danger-outline{border:1.5px solid #fed7d7;color:#e53e3e;padding:10px 20px;border-radius:10px;font-size:13.5px;font-weight:600;cursor:pointer;background:white}
.btn-pub{background:#e6ffed;color:#276749}
.btn-draft{background:#fffacd;color:#b7791f}
/* Badges */
.badge-unread{background:#e8547a;color:white;font-size:11px;padding:2px 8px;border-radius:20px;font-weight:700}
.badge-pub{background:#e6ffed;color:#276749;font-size:12px;padding:3px 10px;border-radius:20px;font-weight:600}
.badge-draft{background:#fffacd;color:#b7791f;font-size:12px;padding:3px 10px;border-radius:20px;font-weight:600}
.tag{background:#f5f5f8;color:#6b6b7b;font-size:12px;padding:3px 10px;border-radius:20px}
/* Forms */
.form-group{margin-bottom:18px}
.form-group label{display:block;font-size:13px;font-weight:600;margin-bottom:7px;color:#1a1a2e}
.form-input{width:100%;padding:10px 14px;border:1.5px solid #e8e8f0;border-radius:10px;font-family:inherit;font-size:14px;transition:all .2s;background:white}
.form-input:focus{outline:none;border-color:#e8547a;box-shadow:0 0 0 3px rgba(232,84,122,.08)}
.code-input{font-family:monospace;font-size:13px;line-height:1.6}
.field-hint{font-size:12px;color:#aaa;margin-top:6px}
/* Edit layout */
.edit-grid{display:grid;grid-template-columns:1fr 300px;gap:20px;align-items:start}
.edit-main{}
.edit-sidebar{}
/* Filters */
.filters{margin-bottom:16px}
.filter-input{padding:9px 14px;border:1.5px solid #e8e8f0;border-radius:10px;font-family:inherit;font-size:14px;min-width:200px}
.filter-select{padding:9px 14px;border:1.5px solid #e8e8f0;border-radius:10px;font-family:inherit;font-size:14px}
.filter-tabs{display:flex;gap:4px;margin-bottom:16px}
.tab{padding:8px 18px;border-radius:10px;font-weight:600;font-size:13px;color:#6b6b7b;transition:all .2s}
.tab.active{background:#e8547a;color:white}
.tab:hover:not(.active){background:#f5f5f8}
/* Table info */
.table-info{font-size:13px;color:#888;margin-bottom:12px}
/* Pagination */
.pagination{display:flex;gap:6px;margin-top:16px;flex-wrap:wrap}
.page-btn{padding:6px 12px;border-radius:8px;font-size:13px;font-weight:600;color:#6b6b7b;background:#f5f5f8;transition:all .2s}
.page-btn.active{background:#e8547a;color:white}
.page-btn:hover:not(.active){background:#e8e8f0}
/* Two col */
.two-col-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
/* Contact detail */
.detail-row{display:flex;gap:16px;padding:12px 0;border-bottom:1px solid #f5f5f8}
.detail-label{font-weight:600;color:#888;min-width:130px;font-size:13px}
.detail-val a{color:#e8547a}
.detail-message{margin-top:16px}
.message-box{background:#f8f9fc;border-radius:10px;padding:18px;line-height:1.8;white-space:pre-wrap}
/* Alerts */
.alert-success{background:#e6ffed;color:#276749;padding:12px 18px;border-radius:10px;margin-bottom:20px;font-weight:600}
.alert-error{background:#fff0f0;color:#e53e3e;padding:12px 18px;border-radius:10px;margin-bottom:20px;font-weight:600}
/* Info list */
.info-list{}
.info-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f5f5f8;font-size:13px}
.info-row a{color:#e8547a}
/* Post title */
.post-title{color:#1a1a2e;font-weight:600}
.post-title:hover{color:#e8547a}
/* View all */
.view-all-link{display:block;text-align:right;color:#e8547a;font-size:13px;font-weight:600;margin-top:12px}
/* Actions */
.actions{white-space:nowrap}
'''

def get_admin_js():
    return '''
function autoSlug(title) {
  const slugInput = document.getElementById('slug-input');
  if (slugInput && !slugInput.dataset.edited) {
    // Convert Vietnamese to ASCII roughly
    let s = title.toLowerCase()
      .replace(/[àáạảãâầấậẩẫăằắặẳẵ]/g, 'a')
      .replace(/[èéẹẻẽêềếệểễ]/g, 'e')
      .replace(/[ìíịỉĩ]/g, 'i')
      .replace(/[òóọỏõôồốộổỗơờớợởỡ]/g, 'o')
      .replace(/[ùúụủũưừứựửữ]/g, 'u')
      .replace(/[ỳýỵỷỹ]/g, 'y')
      .replace(/[đ]/g, 'd')
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .slice(0, 60);
    slugInput.value = s;
  }
}
document.addEventListener('DOMContentLoaded', function() {
  const slugInput = document.getElementById('slug-input');
  if (slugInput && slugInput.value) slugInput.dataset.edited = '1';
  if (slugInput) slugInput.addEventListener('input', () => slugInput.dataset.edited = '1');
});
function previewCover(val) {
  const el = document.getElementById('cover-preview');
  if (!el) return;
  if (val) {
    el.outerHTML = '<img src="/'+val+'" style="max-width:200px;border-radius:8px;margin-top:8px" id="cover-preview" onerror="this.style.display=\'none\'">';
  }
}
'''

# ─────────────────────────────────────────────
# Patch lien-he.html — inject API form
# ─────────────────────────────────────────────
@app.route('/lien-he.html')
def contact_page():
    with open(os.path.join(PUBLIC_DIR, 'lien-he.html'), 'r', encoding='utf-8') as f:
        html = f.read()

    # Inject JS để form gọi API thay vì alert
    inject = '''
<script>
(function() {
  document.addEventListener('DOMContentLoaded', function() {
    const btn = document.querySelector('button[onclick]');
    if (!btn) return;
    btn.removeAttribute('onclick');
    btn.addEventListener('click', async function() {
      const inputs = document.querySelectorAll('input, textarea, select');
      const data = {
        name: inputs[0]?.value || '',
        email: inputs[1]?.value || '',
        subject: inputs[2]?.value || '',
        message: inputs[3]?.value || ''
      };
      if (!data.name || !data.email || !data.message) {
        alert('Vui lòng điền đầy đủ thông tin!'); return;
      }
      btn.disabled = true; btn.textContent = '⏳ Đang gửi...';
      try {
        const res = await fetch('/api/contact', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(data)
        });
        const result = await res.json();
        if (result.ok) {
          alert(result.message);
          inputs.forEach(i => i.value = '');
        } else {
          alert('❌ ' + result.error);
        }
      } catch(e) {
        alert('Lỗi kết nối. Vui lòng thử lại.');
      }
      btn.disabled = false; btn.textContent = '📨 Gửi tin nhắn';
    });
  });
})();
</script>
'''
    html = html.replace('</body>', inject + '</body>')
    return html

# ─────────────────────────────────────────────
if __name__ == '__main__':
    # Khởi tạo DB
    sys.path.insert(0, DB_DIR)
    from init_db import init_db
    init_db()

    print("\n" + "="*50)
    print("🌸  BEAUDY BACKEND  🌸")
    print("="*50)
    print("🌐 Website:    http://localhost:5000")
    print("🔧 Admin:      http://localhost:5000/admin")
    print("🔑 Login:      admin / admin123")
    print("📡 API:        http://localhost:5000/api/posts")
    print("="*50 + "\n")

    app.run(debug=True, port=5000, host='0.0.0.0')
