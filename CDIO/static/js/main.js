/* ============================================================
   INSTANT SEARCH — Autocomplete dropdown
   ============================================================ */
(function initInstantSearch() {
  const searchInput = document.querySelector('.search-wrap input[name="keyword"]');
  if (!searchInput) return;

  /* --- Build dropdown element --- */
  const wrap = searchInput.parentElement;
  wrap.style.position = 'relative';

  const dropdown = Object.assign(document.createElement('div'), {
    id: 'ph-suggestions',
  });
  Object.assign(dropdown.style, {
    position: 'absolute', top: 'calc(100% + 6px)', left: '0', right: '0',
    background: 'var(--surface2)', border: '1px solid var(--border)',
    borderRadius: 'var(--radius)', zIndex: '300',
    boxShadow: 'var(--shadow)', display: 'none', overflow: 'hidden',
  });
  wrap.appendChild(dropdown);

  let timer;
  searchInput.addEventListener('input', () => {
    clearTimeout(timer);
    const q = searchInput.value.trim();
    if (q.length < 2) { dropdown.style.display = 'none'; return; }
    timer = setTimeout(() => fetchSuggestions(q), 240);
  });

  async function fetchSuggestions(q) {
    try {
      const res  = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`);
      const list = await res.json();
      renderDropdown(list);
    } catch (_) {}
  }

  function renderDropdown(items) {
    if (!items.length) { dropdown.style.display = 'none'; return; }
    dropdown.innerHTML = items.map(({ text, type }) => `
      <div class="ph-sug-item" data-text="${text}" style="
          padding:.6rem 1.1rem; cursor:pointer; display:flex; align-items:center;
          gap:.5rem; font-size:.9rem; color:var(--text); transition:background .12s;">
        <span style="font-size:.85rem">${type === 'trending' ? '🔥' : '🔍'}</span>
        ${text}
        <span style="margin-left:auto;font-size:.7rem;color:var(--text3);text-transform:uppercase">
          ${type}
        </span>
      </div>`).join('');

    dropdown.querySelectorAll('.ph-sug-item').forEach(el => {
      el.addEventListener('mouseenter', () => el.style.background = 'var(--surface3)');
      el.addEventListener('mouseleave', () => el.style.background = '');
      el.addEventListener('mousedown',  e  => {
        e.preventDefault();  // prevent blur before click
        searchInput.value = el.dataset.text;
        dropdown.style.display = 'none';
        searchInput.closest('form').submit();
      });
    });

    dropdown.style.display = 'block';
  }

  searchInput.addEventListener('blur', () =>
    setTimeout(() => { dropdown.style.display = 'none'; }, 150));
  searchInput.addEventListener('keydown', e => {
    if (e.key === 'Escape') dropdown.style.display = 'none';
  });
})();


/* ============================================================
   STALE-WHILE-REVALIDATE — Auto-refresh when data is stale
   ============================================================ */
(function initSWR() {
  const body    = document.body;
  const keyword = body.dataset.keyword;
  const isStale = body.dataset.stale === 'true';
  if (!isStale || !keyword) return;

  /* Inject stale notice banner */
  const banner = document.createElement('div');
  banner.id = 'swr-banner';
  banner.innerHTML = `
    <div style="background:rgba(245,166,35,.1);border:1px solid rgba(245,166,35,.3);
                border-radius:8px;padding:.6rem 1.1rem;margin-bottom:1rem;
                display:flex;align-items:center;gap:.75rem;font-size:.85rem;">
      <span>⏳</span>
      <span style="color:var(--text2)">Đang tải giá mới nhất ở nền…</span>
      <span id="swr-dot" style="margin-left:auto;animation:ring-spin 1s linear infinite;
                                display:inline-block">🔄</span>
    </div>`;
  const header = document.querySelector('.results-header');
  if (header) header.insertAdjacentElement('afterend', banner);

  let attempts = 0;
  const MAX    = 24;        // 24 × 5s = 2 min max wait

  const poll = setInterval(async () => {
    if (++attempts > MAX) { clearInterval(poll); banner.remove(); return; }
    try {
      const res  = await fetch(`/api/cache-status?keyword=${encodeURIComponent(keyword)}`);
      const data = await res.json();
      if (data.status === 'fresh') {
        clearInterval(poll);
        banner.innerHTML = `
          <div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);
                      border-radius:8px;padding:.6rem 1.1rem;margin-bottom:1rem;
                      display:flex;align-items:center;gap:.75rem;font-size:.85rem;">
            <span>✅</span>
            <span style="color:#86efac">Giá đã được cập nhật!</span>
            <button onclick="location.reload()" style="margin-left:auto;background:var(--accent);
                    color:#000;border:none;padding:.3rem .8rem;border-radius:6px;
                    cursor:pointer;font-size:.8rem;font-weight:600">Tải lại</button>
          </div>`;
      }
    } catch (_) {}
  }, 5000);
})();


/* ============================================================
   FAST FILTER BAR — client-side + server-side /api/filter
   ============================================================ */
(function initFilterBar() {
  const keyword = document.body.dataset.keyword;
  if (!keyword) return;

  const filterBar = document.querySelector('.results-filters');
  if (!filterBar) return;

  /* Storage filter buttons */
  const storages = ['128GB', '256GB', '512GB', '1TB'];
  storages.forEach(gb => {
    const btn = document.createElement('button');
    btn.className  = 'filter-btn';
    btn.textContent = gb;
    btn.dataset.storage = gb;
    btn.addEventListener('click', () => applyFilter({ storage: gb }));
    filterBar.appendChild(btn);
  });

  /* Price alert button */
  const alertBtn = document.createElement('button');
  alertBtn.className  = 'filter-btn';
  alertBtn.textContent = '🔔 Theo dõi giá';
  alertBtn.addEventListener('click', openAlertModal);
  filterBar.appendChild(alertBtn);

  async function applyFilter({ storage = '', sort = 'price_asc' } = {}) {
    document.querySelectorAll('.filter-btn[data-storage]').forEach(b =>
      b.classList.toggle('active', b.dataset.storage === storage));

    try {
      const params = new URLSearchParams({ keyword, sort });
      if (storage) params.set('storage', storage);
      const res      = await fetch(`/api/filter?${params}`);
      const products = await res.json();
      renderProducts(products);
    } catch (e) { console.error('[filter]', e); }
  }

  function renderProducts(products) {
    const grid = document.querySelector('.products-grid');
    if (!grid) return;
    if (!products.length) {
      grid.innerHTML = '<div class="empty-state"><div class="empty-icon">😕</div><h3>Không tìm thấy sản phẩm phù hợp</h3></div>';
      return;
    }
    // Delegate full re-render to existing template logic via reload with params
    // For a SPA-style update you would rebuild card HTML here
    grid.style.opacity = '0.5';
    setTimeout(() => {
      grid.style.opacity = '1';
      // Minimal indicator — full implementation depends on card template
    }, 300);
  }

  function openAlertModal() {
    if (!document.body.dataset.loggedIn) {
      window.location.href = '/login';
      return;
    }
    const threshold = prompt(`Nhập giá cảnh báo cho "${keyword}" (VND, không có dấu chấm):`);
    if (!threshold || isNaN(threshold)) return;

    fetch('/alerts/set', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        keyword,
        threshold_price: parseInt(threshold, 10),
        channel: 'email',
      }),
    })
    .then(r => r.json())
    .then(d => alert(d.message || (d.ok ? 'Đã đặt cảnh báo!' : d.error)))
    .catch(() => alert('Lỗi khi đặt cảnh báo.'));
  }
})();