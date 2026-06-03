// ── SHARED HEADER + FOOTER ──
function renderHeader(activePage = '') {
  const pages = [
    { id: 'thanh-phan', label: 'Thành phần', sub: [
      { label: 'Thành phần làm đẹp', href: 'thanh-phan.html' },
      { label: 'Tra cứu & phân tích', href: 'phan-tich.html' },
    ]},
    { id: 'my-pham', label: 'Mỹ phẩm', sub: [
      { label: 'Review mỹ phẩm', href: 'review-my-pham.html' },
      { label: 'Top mỹ phẩm', href: 'top-my-pham.html' },
    ]},
    { id: 'lam-dep-da', label: 'Làm đẹp da', sub: [
      { label: 'Chăm sóc da', href: 'lam-dep-da.html' },
      { label: 'Spa & Thẩm mỹ viện', href: 'spa.html' },
    ]},
    { id: 'toc-dep', label: 'Tóc đẹp', sub: [
      { label: 'Chăm sóc tóc', href: 'cham-soc-toc.html' },
      { label: 'Salon tóc', href: 'salon-toc.html' },
      { label: 'Tóc nữ đẹp', href: 'toc-nu.html' },
      { label: 'Tóc nam đẹp', href: 'toc-nam.html' },
    ]},
    { id: 'thoi-trang', label: 'Thời trang', href: 'thoi-trang.html', sub: [] },
    { id: 'trang-diem', label: 'Trang điểm', sub: [
      { label: 'Son môi', href: 'son-moi.html' },
      { label: 'Nail đẹp', href: 'nail-dep.html' },
    ]},
  ];

  const navItems = pages.map(p => {
    const isActive = activePage === p.id ? 'active' : '';
    const mainHref = p.href || (p.sub[0] ? p.sub[0].href : '#');
    const arrow = p.sub.length ? ' ▾' : '';
    const dropdown = p.sub.length
      ? `<div class="dropdown">${p.sub.map(s => `<a href="${s.href}">${s.label}</a>`).join('')}</div>`
      : '';
    return `<div class="nav-item ${isActive}"><a href="${mainHref}">${p.label}${arrow}</a>${dropdown}</div>`;
  }).join('');

  document.getElementById('app-header').innerHTML = `
    <div class="top-bar">🌸 Khám phá bí quyết làm đẹp chuyên sâu</div>
    <header>
      <div class="header-inner">
        <a href="index.html" class="logo">Trang chủ</a>
        <nav>${navItems}</nav>
        <div class="header-right">
          <button class="search-btn" onclick="toggleSearch()">🔍</button>
        </div>
      </div>
    </header>
    <div class="search-overlay" id="searchOverlay" onclick="closeSearchOnBg(event)">
      <div class="search-box">
        <div class="search-input-wrap">
          <input class="search-input" id="searchInput" type="text" placeholder="Tìm kiếm bài viết...">
          <button class="search-close-btn" onclick="toggleSearch()">✕</button>
        </div>
        <div class="search-tags">
          <span class="search-tag" onclick="doSearch(this)">da dầu mụn</span>
          <span class="search-tag" onclick="doSearch(this)">kem chống nắng</span>
          <span class="search-tag" onclick="doSearch(this)">kiểu tóc 2026</span>
          <span class="search-tag" onclick="doSearch(this)">son lì</span>
          <span class="search-tag" onclick="doSearch(this)">nail đẹp</span>
          <span class="search-tag" onclick="doSearch(this)">serum niacinamide</span>
        </div>
      </div>
    </div>
  `;
}

function renderFooter() {
  document.getElementById('app-footer').innerHTML = `
    <footer>
      <div class="footer-grid container">
        <div>
          <div class="footer-logo">Trang chủ</div>
          <p class="footer-desc">Trang làm đẹp chuyên sâu, phân tích thành phần mỹ phẩm, review mỹ phẩm thật, spa, thẩm mỹ viện, salon tóc, cách chăm sóc da & tóc.</p>
          <div class="footer-social">
            <div class="footer-social-btn">📘</div>
            <div class="footer-social-btn">📸</div>
            <div class="footer-social-btn">🎵</div>
            <div class="footer-social-btn">▶️</div>
          </div>
        </div>
        <div class="footer-col">
          <h4>Chủ đề</h4>
          <div class="footer-links">
            <a href="thanh-phan.html">Thành phần làm đẹp</a>
            <a href="review-my-pham.html">Review mỹ phẩm</a>
            <a href="top-my-pham.html">Top mỹ phẩm</a>
            <a href="lam-dep-da.html">Làm đẹp da</a>
            <a href="spa.html">Spa & Thẩm mỹ</a>
          </div>
        </div>
        <div class="footer-col">
          <h4>Tóc & Trang điểm</h4>
          <div class="footer-links">
            <a href="cham-soc-toc.html">Chăm sóc tóc</a>
            <a href="toc-nu.html">Tóc nữ đẹp</a>
            <a href="toc-nam.html">Tóc nam đẹp</a>
            <a href="son-moi.html">Son môi</a>
            <a href="nail-dep.html">Nail đẹp</a>
            <a href="thoi-trang.html">Thời trang</a>
          </div>
        </div>
        <div class="footer-col">
          <h4>Về chúng tôi</h4>
          <div class="footer-links">
            <a href="gioi-thieu.html">Giới thiệu</a>
            <a href="lien-he.html">Liên hệ</a>
            <a href="#">Chính sách bảo mật</a>
            <a href="#">Điều khoản sử dụng</a>
          </div>
        </div>
      </div>
      <div class="footer-bottom container">
        <span>© 2024–2026 Trang chủ – Trang làm đẹp chuyên sâu</span>
        <span>Made with 🌸 in Vietnam</span>
      </div>
    </footer>
    <button class="back-to-top" id="backToTop" onclick="scrollToTop()">↑</button>
  `;
}

// ── SHARED FUNCTIONS ──
function toggleSearch() {
  const o = document.getElementById('searchOverlay');
  o.classList.toggle('active');
  if (o.classList.contains('active')) setTimeout(() => document.getElementById('searchInput').focus(), 100);
}
function closeSearchOnBg(e) { if (e.target.id === 'searchOverlay') toggleSearch(); }
function doSearch(el) {
  const val = el.textContent;
  document.getElementById('searchInput').value = val;
  executeSearch(val);
}
function executeSearch(query) {
  if (!query || !query.trim()) return;
  window.location.href = 'search.html?q=' + encodeURIComponent(query.trim());
}
// Also add search button click handler after DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  // Add search button inside the search-input-wrap
  const wrap = document.querySelector('.search-input-wrap');
  if (wrap) {
    const btn = document.createElement('button');
    btn.className = 'search-exec-btn';
    btn.textContent = 'Tìm';
    btn.onclick = () => executeSearch(document.getElementById('searchInput').value);
    wrap.appendChild(btn);
  }
  // Enter key in search input
  const input = document.getElementById('searchInput');
  if (input) {
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') executeSearch(input.value);
    });
  }
});
function scrollToTop() { window.scrollTo({ top: 0, behavior: 'smooth' }); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') document.getElementById('searchOverlay')?.classList.remove('active'); });
window.addEventListener('scroll', () => {
  const btn = document.getElementById('backToTop');
  if (btn) btn.classList.toggle('visible', window.scrollY > 300);
});

// ── NEWSLETTER SUBSCRIBE ──
function initNewsletter() {
  document.addEventListener('DOMContentLoaded', () => {
    const btn = document.querySelector('.btn-subscribe');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      const input = document.querySelector('.subscribe-input');
      if (!input) return;
      const email = input.value.trim();
      if (!email || !email.includes('@')) {
        showToast('Vui lòng nhập email hợp lệ!', 'error'); return;
      }
      btn.disabled = true; btn.textContent = '⏳ Đang đăng ký...';
      try {
        const res = await fetch('/api/subscribe', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({email})
        });
        const data = await res.json();
        if (data.ok) {
          showToast('🌸 Đăng ký thành công! Cảm ơn bạn.', 'success');
          input.value = '';
        } else {
          showToast(data.error || 'Lỗi đăng ký', 'error');
        }
      } catch(e) {
        showToast('Lỗi kết nối. Vui lòng thử lại.', 'error');
      }
      btn.disabled = false; btn.textContent = 'Đăng ký ngay';
    });
  });
}
initNewsletter();

function showToast(msg, type='success') {
  const t = document.createElement('div');
  t.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:99999;
    background:${type==='success'?'#e8547a':'#e53e3e'};color:white;
    padding:14px 22px;border-radius:12px;font-weight:700;font-size:14px;
    box-shadow:0 6px 24px rgba(0,0,0,.2);animation:fadeInUp .3s ease`;
  t.textContent = msg;
  if (!document.querySelector('#toast-style')) {
    const s = document.createElement('style');
    s.id = 'toast-style';
    s.textContent = '@keyframes fadeInUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}';
    document.head.appendChild(s);
  }
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}
