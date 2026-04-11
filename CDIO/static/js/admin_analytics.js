/**
 * static/js/admin_analytics.js
 * ─────────────────────────────
 * Dashboard Analytics cho tab "Phân tích" trong Admin.
 * Yêu cầu: Chart.js đã được load trên trang (thêm <script> vào admin.html).
 *
 * Cách dùng:
 *   <script src="/static/js/admin_analytics.js"></script>
 *   <script>AdminAnalytics.init();</script>
 */

(function (global) {
  "use strict";

  /* ── Màu theo sàn ── */
  const SITE_COLORS = {
    CellphoneS: "#3266ad",
    Clickbuy: "#BA7517",
    "Di Động 3A": "#185FA5",
    "Smart Việt": "#3B6D11",
    "Bạch Long Store": "#7F77DD",
    "Tiến Trần Mobile": "#D85A30",
  };
  const FALLBACK_COLORS = [
    "#3266ad",
    "#BA7517",
    "#3B6D11",
    "#7F77DD",
    "#D85A30",
    "#185FA5",
  ];
  function siteColor(name, idx) {
    return SITE_COLORS[name] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
  }

  /* ── Trạng thái ── */
  var _charts = {};
  var _intervals = [];
  var _startTime = Date.now();

  /* ── Fetch helper ── */
  function api(url, cb) {
    fetch(url)
      .then(function (r) {
        return r.json();
      })
      .then(cb)
      .catch(function (e) {
        console.warn("[Analytics] " + url, e);
      });
  }

  /* ══════════════════════════════════════════════════════════════
     KPI CARDS
  ══════════════════════════════════════════════════════════════ */
  function refreshSummary() {
    api("/api/analytics/summary", function (d) {
      setText("an-today", d.today_count.toLocaleString("vi-VN"));
      setText("an-total", d.total_count.toLocaleString("vi-VN"));
      setText("an-users", d.user_count.toLocaleString("vi-VN"));
      setText("an-orders", d.order_count.toLocaleString("vi-VN"));
      setText("an-last-crawl", d.last_crawl);

      var errEl = document.getElementById("an-err-rate");
      var errBdg = document.getElementById("an-err-badge");
      if (errEl) errEl.textContent = d.error_rate + "%";
      if (errBdg) {
        if (d.error_rate === 0) {
          errBdg.textContent = "Ổn định";
          errBdg.className = "an-badge an-badge-green";
        } else if (d.error_rate < 20) {
          errBdg.textContent = "Cảnh báo";
          errBdg.className = "an-badge an-badge-amber";
        } else {
          errBdg.textContent = "Có vấn đề";
          errBdg.className = "an-badge an-badge-red";
        }
      }
    });
  }

  /* ══════════════════════════════════════════════════════════════
     UPTIME CLOCK
  ══════════════════════════════════════════════════════════════ */
  function tickUptime() {
    var elapsed = Date.now() - _startTime;
    var h = Math.floor(elapsed / 3600000);
    var m = Math.floor((elapsed % 3600000) / 60000);
    var s = Math.floor((elapsed % 60000) / 1000);
    setText("an-uptime", pad(h) + ":" + pad(m) + ":" + pad(s));
  }

  /* ══════════════════════════════════════════════════════════════
     SCRAPER STATUS CARDS
  ══════════════════════════════════════════════════════════════ */
  function refreshScrapers() {
    api("/api/analytics/scraper-status", function (data) {
      var container = document.getElementById("an-scraper-grid");
      if (!container) return;
      container.innerHTML = data
        .map(function (s) {
          var dot = s.online ? "#3B6D11" : "#A32D2D";
          var label = s.online ? "Online" : "Offline";
          return (
            '<div class="an-scraper-card">' +
            '<div class="an-scraper-dot" style="background:' +
            dot +
            '"></div>' +
            '<div style="flex:1;min-width:0">' +
            '<div class="an-scraper-name">' +
            s.name +
            "</div>" +
            '<div class="an-scraper-label">' +
            label +
            "</div>" +
            "</div>" +
            '<div style="text-align:right">' +
            '<div class="an-scraper-count">' +
            s.count +
            "</div>" +
            '<div class="an-scraper-label">24h</div>' +
            "</div>" +
            "</div>"
          );
        })
        .join("");
    });
  }

  /* ══════════════════════════════════════════════════════════════
     TOP KEYWORDS  (horizontal bar)
  ══════════════════════════════════════════════════════════════ */
  function buildKeywordsChart(data) {
    var canvas = document.getElementById("an-kw-chart");
    if (!canvas || !global.Chart) return;
    if (_charts["kw"]) _charts["kw"].destroy();

    _charts["kw"] = new global.Chart(canvas, {
      type: "bar",
      data: {
        labels: data.map(function (d) {
          return d.keyword;
        }),
        datasets: [
          {
            label: "Lượt tìm kiếm",
            data: data.map(function (d) {
              return d.count;
            }),
            backgroundColor: "#185FA5",
            borderRadius: 4,
            borderWidth: 0,
          },
        ],
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return " " + ctx.raw.toLocaleString("vi-VN") + " lần";
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: "rgba(128,128,128,.12)" },
            ticks: { color: "#888", font: { size: 11 } },
          },
          y: {
            grid: { display: false },
            ticks: {
              color: "#555",
              font: { size: 11 },
              autoSkip: false,
            },
          },
        },
      },
    });
  }

  function refreshKeywords() {
    api("/api/analytics/top-keywords", buildKeywordsChart);
  }

  /* ══════════════════════════════════════════════════════════════
     SITE DISTRIBUTION  (donut)
  ══════════════════════════════════════════════════════════════ */
  function buildDonut(data) {
    var canvas = document.getElementById("an-donut-chart");
    if (!canvas || !global.Chart) return;
    if (_charts["donut"]) _charts["donut"].destroy();

    var colors = data.map(function (d, i) {
      return siteColor(d.site, i);
    });

    _charts["donut"] = new global.Chart(canvas, {
      type: "doughnut",
      data: {
        labels: data.map(function (d) {
          return d.site;
        }),
        datasets: [
          {
            data: data.map(function (d) {
              return d.percent;
            }),
            backgroundColor: colors,
            borderWidth: 0,
            hoverOffset: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "68%",
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return " " + ctx.label + ": " + ctx.raw + "%";
              },
            },
          },
        },
      },
    });

    /* Legend HTML */
    var leg = document.getElementById("an-donut-legend");
    if (!leg) return;
    leg.innerHTML = data
      .map(function (d, i) {
        return (
          '<div class="an-leg-row">' +
          '<div class="an-leg-dot" style="background:' +
          colors[i] +
          '"></div>' +
          '<span class="an-leg-name">' +
          d.site +
          "</span>" +
          '<div class="an-leg-bar-wrap"><div class="an-leg-bar" style="width:' +
          d.percent +
          "%;background:" +
          colors[i] +
          '"></div></div>' +
          '<span class="an-leg-val">' +
          d.percent +
          "%</span>" +
          "</div>"
        );
      })
      .join("");
  }

  function refreshDonut() {
    api("/api/analytics/site-distribution", buildDonut);
  }

  /* ══════════════════════════════════════════════════════════════
     CRAWL TREND  (line chart — 7 ngày)
  ══════════════════════════════════════════════════════════════ */
  function buildTrend(data) {
    var canvas = document.getElementById("an-trend-chart");
    if (!canvas || !global.Chart) return;
    if (_charts["trend"]) _charts["trend"].destroy();

    _charts["trend"] = new global.Chart(canvas, {
      type: "line",
      data: {
        labels: data.map(function (d) {
          return d.day.slice(5);
        }),
        datasets: [
          {
            label: "Sản phẩm",
            data: data.map(function (d) {
              return d.count;
            }),
            borderColor: "#185FA5",
            backgroundColor: "rgba(24,95,165,.08)",
            borderWidth: 2,
            pointRadius: 4,
            pointBackgroundColor: "#185FA5",
            tension: 0.35,
            fill: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return " " + ctx.raw.toLocaleString("vi-VN") + " sản phẩm";
              },
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#888", font: { size: 11 } },
          },
          y: {
            grid: { color: "rgba(128,128,128,.12)" },
            ticks: { color: "#888", font: { size: 11 } },
          },
        },
      },
    });
  }

  function refreshTrend() {
    api("/api/analytics/crawl-trend", buildTrend);
  }

  /* ══════════════════════════════════════════════════════════════
     BOT LOGS
  ══════════════════════════════════════════════════════════════ */
  function refreshLogs() {
    api("/api/bot-logs", function (logs) {
      var el = document.getElementById("an-log-container");
      if (!el || !logs.length) return;
      el.innerHTML = logs
        .map(function (line) {
          var cls = "log-info";
          if (line.includes("✅")) cls = "log-success";
          if (line.includes("❌")) cls = "log-error";
          var match = line.match(/^\[([^\]]+)\]/);
          var timeStr = match ? match[0] : "";
          var msg = line.replace(timeStr, "").trim();
          return (
            '<div class="log-entry ' +
            cls +
            '">' +
            '<span class="log-time">' +
            timeStr +
            "</span> " +
            msg +
            "</div>"
          );
        })
        .join("");
      el.scrollTop = 0;
      setText(
        "an-last-sync",
        "Cập nhật: " + new Date().toLocaleTimeString("vi-VN"),
      );
    });
  }

  /* ══════════════════════════════════════════════════════════════
     PUBLIC API
  ══════════════════════════════════════════════════════════════ */
  function init() {
    refreshSummary();
    refreshScrapers();
    refreshKeywords();
    refreshDonut();
    refreshTrend();
    refreshLogs();

    _intervals.push(setInterval(refreshSummary, 15000));
    _intervals.push(setInterval(refreshScrapers, 8000));
    _intervals.push(setInterval(refreshLogs, 5000));
    _intervals.push(setInterval(tickUptime, 1000));
  }

  function destroy() {
    _intervals.forEach(clearInterval);
    _intervals = [];
    Object.values(_charts).forEach(function (c) {
      c.destroy();
    });
    _charts = {};
  }

  /* ── Helpers ── */
  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }
  function pad(n) {
    return String(n).padStart(2, "0");
  }

  global.AdminAnalytics = { init: init, destroy: destroy };
})(window);
