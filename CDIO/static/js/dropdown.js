/**
 * PriceHunt — Dropdown JS (fixed)
 * - Không đặt script trước <body>
 * - Tất cả logic trong DOMContentLoaded
 * - Toggle L1 bằng click, L2 bằng CSS hover (desktop) / JS click (mobile)
 */
(function () {
  "use strict";

  var MOBILE_BP = 768;
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

  /* Toggle L1 — gọi từ onclick="toggleCatDropdown(event)" */
  window.toggleCatDropdown = function (e) {
    e.stopPropagation();
    var btn = document.getElementById("cat-btn");
    var dd = document.getElementById("cat-dropdown");
    if (!btn || !dd) return;
    var isOpen = dd.classList.contains("open");
    closeAllDropdowns();
    if (!isOpen) {
      dd.classList.add("open");
      btn.classList.add("open");
      btn.setAttribute("aria-expanded", "true");
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    /* Click ngoài → đóng */
    document.addEventListener("click", function (e) {
      var wrap = document.getElementById("cat-wrap");
      if (wrap && !wrap.contains(e.target)) closeAllDropdowns();
    });

    /* Escape → đóng */
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeAllDropdowns();
    });

    /* Mobile: click has-sub → toggle L2 */
    document.querySelectorAll(".cat-item.has-sub").forEach(function (item) {
      item.addEventListener("click", function (e) {
        if (!isMobile()) return;
        if (e.target.closest(".cat-submenu a"))
          return; /* cho phép click link con */
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

    /* Cart count */
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

    /* ── Navbar search (mini) ── */
    var navInput = document.getElementById("nav-search-input");
    var navList = document.getElementById("nav-suggestions");
    if (navInput && navList) {
      var debounceTimer;
      navInput.addEventListener("input", function () {
        clearTimeout(debounceTimer);
        var q = navInput.value.trim();
        if (q.length < 2) {
          navList.classList.remove("show");
          return;
        }
        debounceTimer = setTimeout(function () {
          fetch("/api/suggestions?q=" + encodeURIComponent(q))
            .then(function (r) {
              return r.json();
            })
            .then(function (data) {
              if (!data.length) {
                navList.classList.remove("show");
                return;
              }
              navList.innerHTML = data
                .slice(0, 8)
                .map(function (s) {
                  var hi = s.replace(
                    new RegExp(
                      "(" + q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")",
                      "gi",
                    ),
                    "<mark>$1</mark>",
                  );
                  return (
                    '<li class="nav-sug-item" data-val="' +
                    s.replace(/"/g, "&quot;") +
                    '">' +
                    hi +
                    "</li>"
                  );
                })
                .join("");
              navList.classList.add("show");
              navList.querySelectorAll(".nav-sug-item").forEach(function (li) {
                li.addEventListener("mousedown", function (e) {
                  e.preventDefault();
                  navInput.value = li.dataset.val;
                  navList.classList.remove("show");
                  /* submit form hoặc redirect */
                  var form = document.getElementById("nav-search-form");
                  if (form) form.submit();
                  else
                    window.location.href =
                      "/?keyword=" + encodeURIComponent(li.dataset.val);
                });
              });
            })
            .catch(function () {
              navList.classList.remove("show");
            });
        }, 220);
      });

      document.addEventListener("click", function (e) {
        if (!navInput.contains(e.target) && !navList.contains(e.target))
          navList.classList.remove("show");
      });

      /* Enter submit */
      navInput.addEventListener("keydown", function (e) {
        if (e.key === "Enter") {
          navList.classList.remove("show");
          var form = document.getElementById("nav-search-form");
          if (form) form.submit();
          else
            window.location.href =
              "/?keyword=" + encodeURIComponent(navInput.value.trim());
        }
      });
    }
  });
})();
