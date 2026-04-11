/**
 * PriceHunt — Category Dropdown JS (fixed)
 * Tất cả logic bọc trong DOMContentLoaded để tránh lỗi DOM chưa load.
 */

(function () {
  "use strict";

  const MOBILE_BP = 768;
  function isMobile() {
    return window.innerWidth <= MOBILE_BP;
  }

  function closeAllDropdowns() {
    document.querySelectorAll(".cat-dropdown.open").forEach(function (d) {
      d.classList.remove("open");
    });
    document.querySelectorAll(".nav-category-btn.open").forEach(function (b) {
      b.classList.remove("open");
      b.setAttribute("aria-expanded", "false");
    });
  }

  window.toggleCatDropdown = function (e) {
    e.stopPropagation();
    var btn = document.getElementById("cat-btn");
    var dropdown = document.getElementById("cat-dropdown");
    if (!btn || !dropdown) return;

    var isOpen = dropdown.classList.contains("open");
    closeAllDropdowns();

    if (!isOpen) {
      dropdown.classList.add("open");
      btn.classList.add("open");
      btn.setAttribute("aria-expanded", "true");
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    /* ── Click ngoài → đóng ────────────────────────────────── */
    document.addEventListener("click", function (e) {
      var wrap = document.getElementById("cat-wrap");
      if (wrap && !wrap.contains(e.target)) closeAllDropdowns();
    });

    /* ── Escape → đóng ─────────────────────────────────────── */
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeAllDropdowns();
    });

    /* ── Mobile: click has-sub → toggle L2 ─────────────────── */
    document.querySelectorAll(".cat-item.has-sub").forEach(function (item) {
      item.addEventListener("click", function (e) {
        if (!isMobile()) return;
        if (e.target.closest(".cat-submenu")) return;
        e.preventDefault();
        e.stopPropagation();
        var wasOpen = item.classList.contains("mob-open");
        document
          .querySelectorAll(".cat-item.has-sub.mob-open")
          .forEach(function (i) {
            i.classList.remove("mob-open");
          });
        if (!wasOpen) item.classList.add("mob-open");
      });
    });

    /* ── Cart count ─────────────────────────────────────────── */
    var cartEl = document.getElementById("cart-count");
    if (cartEl) {
      fetch("/cart/count")
        .then(function (r) {
          return r.json();
        })
        .then(function (d) {
          cartEl.textContent = d.count || 0;
        })
        .catch(function () {});
    }
  });
})();
