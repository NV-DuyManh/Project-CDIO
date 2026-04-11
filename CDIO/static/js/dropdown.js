/**
 * PriceHunt — Category Dropdown JS
 * Lưu tại: static/js/dropdown.js
 *
 * Hành vi:
 *   Desktop: Click nút "Danh mục" → mở/đóng L1.
 *            Hover vào item có sub-menu → L2 mở tự động qua CSS.
 *            Click ra ngoài → đóng L1.
 *   Mobile:  Click nút "Danh mục" → mở L1.
 *            Click item has-sub → toggle L2 (không dùng hover).
 */

(function () {
  "use strict";

  const MOBILE_BP = 768;

  function isMobile() {
    return window.innerWidth <= MOBILE_BP;
  }

  // ── Toggle L1 ───────────────────────────────────────────────────
  window.toggleCatDropdown = function (e) {
    e.stopPropagation();
    const btn = document.getElementById("cat-btn");
    const dropdown = document.getElementById("cat-dropdown");
    if (!btn || !dropdown) return;

    const isOpen = dropdown.classList.contains("open");

    // Đóng tất cả dropdown toàn trang trước
    closeAllDropdowns();

    if (!isOpen) {
      dropdown.classList.add("open");
      btn.classList.add("open");
      btn.setAttribute("aria-expanded", "true");
    }
  };

  function closeAllDropdowns() {
    document.querySelectorAll(".cat-dropdown.open").forEach(function (d) {
      d.classList.remove("open");
    });
    document.querySelectorAll(".nav-category-btn.open").forEach(function (b) {
      b.classList.remove("open");
      b.setAttribute("aria-expanded", "false");
    });
  }

  // ── Click ra ngoài → đóng ───────────────────────────────────────
  document.addEventListener("click", function (e) {
    const wrap = document.getElementById("cat-wrap");
    if (wrap && !wrap.contains(e.target)) {
      closeAllDropdowns();
    }
  });

  // ── Escape key ──────────────────────────────────────────────────
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeAllDropdowns();
  });

  // ── Mobile: click has-sub → toggle L2 ───────────────────────────
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".cat-item.has-sub").forEach(function (item) {
      item.addEventListener("click", function (e) {
        if (!isMobile()) return; // Desktop dùng CSS :hover

        // Nếu click vào link con (cat-sub-item) thì cho navigate
        if (e.target.closest(".cat-submenu")) return;

        e.preventDefault();
        e.stopPropagation();

        const wasOpen = item.classList.contains("mob-open");
        // Đóng tất cả L2 đang mở
        document
          .querySelectorAll(".cat-item.has-sub.mob-open")
          .forEach(function (i) {
            i.classList.remove("mob-open");
          });
        if (!wasOpen) {
          item.classList.add("mob-open");
        }
      });
    });

    // Cập nhật cart count
    if (document.getElementById("cart-count")) {
      fetch("/cart/count")
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          const el = document.getElementById("cart-count");
          if (el) el.textContent = d.count || 0;
        })
        .catch(function () {});
    }
  });
})();
