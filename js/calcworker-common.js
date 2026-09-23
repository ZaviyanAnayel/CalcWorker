
  // ========================================================
  // Universal Pure Aligned Copy Engine for CalcWorker
  // ========================================================
  function extractAndFormatCalcData() {
    var title = (document.querySelector('.topbar-title') || document.querySelector('h1'))?.innerText.trim() || document.title.split('—')[0].trim();
    title = title.replace(/^[^\w\s]+/, '').trim();
    
    var primaryResultEl = document.querySelector('.mort-result-big, .auto-result-big, .result-value, .big-result, .result-amount, #resPITI, #resMonthlyPayment, #omniTotal');
    var primaryResult = primaryResultEl ? primaryResultEl.innerText.trim() : '';
    
    var primaryLabelEl = primaryResultEl ? (primaryResultEl.previousElementSibling || primaryResultEl.parentElement.querySelector('div:first-child')) : null;
    var primaryLabel = primaryLabelEl ? primaryLabelEl.innerText.trim() : 'Estimated Result';

    var subTextEl = document.querySelector('#resLoanLabel, #resTermSummary, .result-subtitle, .result-desc');
    var subText = subTextEl ? subTextEl.innerText.trim() : '';

    var rows = document.querySelectorAll('.mort-row, .auto-row, .result-row, .calc-row, .summary-row, .data-row, .breakdown-row');
    var pairs = [];
    var maxLabelLen = 0;

    rows.forEach(function(r) {
      var lblEl = r.querySelector('.lbl, .label, .item-name, td:first-child, div:first-child');
      var valEl = r.querySelector('.val, .value, .item-val, td:last-child, div:last-child');
      if (lblEl && valEl && lblEl !== valEl) {
        var lbl = lblEl.innerText.replace(/^[^\w\s$#@%&]+/, '').trim();
        var val = valEl.innerText.trim();
        if (lbl && val) {
          pairs.push({ label: lbl, value: val });
          if (lbl.length > maxLabelLen && lbl.length < 32) maxLabelLen = lbl.length;
        }
      }
    });

    if (pairs.length === 0) {
      var inputs = document.querySelectorAll('.form-group, .input-group');
      inputs.forEach(function(ig) {
        var lbl = ig.querySelector('label')?.innerText.trim();
        var inp = ig.querySelector('input, select')?.value;
        if (lbl && inp) {
          pairs.push({ label: lbl, value: inp });
          if (lbl.length > maxLabelLen && lbl.length < 32) maxLabelLen = lbl.length;
        }
      });
    }

    var padLen = Math.max(maxLabelLen + 2, 24);
    var divider = '────────────────────────────────────────────';

    var lines = [];
    lines.push('📊 CALCWORKER — ' + title.toUpperCase());
    lines.push(divider);
    if (primaryResult) {
      lines.push('⭐ ' + primaryLabel + ': ' + primaryResult);
      if (subText) lines.push('   (' + subText + ')');
      lines.push(divider);
    }
    if (pairs.length > 0) {
      lines.push('📋 CALCULATION BREAKDOWN:');
      pairs.forEach(function(p) {
        var paddedLabel = (p.label + ':').padEnd(padLen, ' ');
        lines.push('• ' + paddedLabel + ' ' + p.value);
      });
      lines.push(divider);
    }
    lines.push('🔗 Free Calculator: ' + window.location.href);

    return lines.join('\n');
  }

  function fallbackClipboardCopy(text, cb) {
    try {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    } catch (err) {}
    if (cb) cb();
  }

  function interceptAndEnforcePureCopy() {
    var btns = document.querySelectorAll('#shareBtn, #omniShareBtn, .share-calc-btn');
    btns.forEach(function(oldBtn) {
      var newBtn = oldBtn.cloneNode(true);
      newBtn.id = 'shareBtn';
      newBtn.className = 'cw-calc-copy-btn';
      newBtn.type = 'button';
      newBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
      newBtn.style.color = '#ffffff';
      newBtn.style.boxShadow = '0 3px 12px rgba(16, 185, 129, 0.35)';
      newBtn.innerHTML = '<span>📋</span> <span id="shareBtnText">Copy Calculation Summary</span>';

      newBtn.onclick = function(e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();

        var formattedData = extractAndFormatCalcData();
        
        var onDone = function() {
          var textSpan = newBtn.querySelector('#shareBtnText') || newBtn;
          textSpan.textContent = '✓ Copied to Clipboard!';
          newBtn.style.background = '#047857';
          setTimeout(function() {
            textSpan.textContent = 'Copy Calculation Summary';
            newBtn.style.background = 'linear-gradient(135deg, #10b981, #059669)';
          }, 2500);
        };

        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(formattedData).then(onDone).catch(function() {
            fallbackClipboardCopy(formattedData, onDone);
          });
        } else {
          fallbackClipboardCopy(formattedData, onDone);
        }
      };

      oldBtn.parentNode.replaceChild(newBtn, oldBtn);
    });
  }

  // CalcWorker Universal Multi-Platform Share Modal
  function openCalcWorkerShareModal() {
    var existing = document.querySelector('.cw-share-overlay');
    if (existing) existing.remove();

    var calcTitle = (document.querySelector('.topbar-title') || document.querySelector('h1'))?.innerText.trim() || document.title.split('—')[0].trim();
    var pageUrl = window.location.href;
    var shareText = 'Calculate ' + calcTitle + ' instantly for free on CalcWorker:';

    var overlay = document.createElement('div');
    overlay.className = 'cw-share-overlay';

    overlay.innerHTML = `
      <div class="cw-share-modal" role="dialog">
        <div class="cw-share-header">
          <h3><span>🔗</span> Share Calculator</h3>
          <button class="cw-share-close" id="cwShareClose" aria-label="Close">✕</button>
        </div>
        <p style="font-size:0.82rem;color:var(--text-muted);margin:0 0 16px 0;">Share <strong>${calcTitle}</strong> instantly across your favorite platforms:</p>
        <div class="cw-share-platforms">
          <a class="cw-platform-btn" href="https://api.whatsapp.com/send?text=${encodeURIComponent(shareText + ' ' + pageUrl)}" target="_blank" rel="noopener">
            <span class="cw-platform-icon" style="color:#25D366;">💬</span>
            <span>WhatsApp</span>
          </a>
          <a class="cw-platform-btn" href="https://t.me/share/url?url=${encodeURIComponent(pageUrl)}&text=${encodeURIComponent(shareText)}" target="_blank" rel="noopener">
            <span class="cw-platform-icon" style="color:#0088cc;">✈️</span>
            <span>Telegram</span>
          </a>
          <a class="cw-platform-btn" href="https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(pageUrl)}" target="_blank" rel="noopener">
            <span class="cw-platform-icon" style="color:#1DA1F2;">𝕏</span>
            <span>Twitter / X</span>
          </a>
          <a class="cw-platform-btn" href="https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(pageUrl)}" target="_blank" rel="noopener">
            <span class="cw-platform-icon" style="color:#1877F2;">📘</span>
            <span>Facebook</span>
          </a>
          <a class="cw-platform-btn" href="https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(pageUrl)}" target="_blank" rel="noopener">
            <span class="cw-platform-icon" style="color:#0A66C2;">💼</span>
            <span>LinkedIn</span>
          </a>
          <a class="cw-platform-btn" href="https://reddit.com/submit?url=${encodeURIComponent(pageUrl)}&title=${encodeURIComponent(shareText)}" target="_blank" rel="noopener">
            <span class="cw-platform-icon" style="color:#FF4500;">🤖</span>
            <span>Reddit</span>
          </a>
        </div>
        <div class="cw-share-copy-box">
          <input type="text" id="cwShareUrlInput" value="${pageUrl}" readonly>
          <button class="cw-share-copy-btn" id="cwShareCopyBtn">Copy Link</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) overlay.remove();
    });

    document.getElementById('cwShareClose').onclick = function() {
      overlay.remove();
    };

    var copyBtn = document.getElementById('cwShareCopyBtn');
    copyBtn.onclick = function() {
      var input = document.getElementById('cwShareUrlInput');
      input.select();
      navigator.clipboard.writeText(pageUrl).then(function() {
        copyBtn.classList.add('copied');
        copyBtn.textContent = '✓ Copied!';
        setTimeout(function() {
          copyBtn.classList.remove('copied');
          copyBtn.textContent = 'Copy Link';
        }, 2000);
      });
    };
  }

  // Auto-run interceptor on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      interceptAndEnforcePureCopy();
      setTimeout(interceptAndEnforcePureCopy, 500);
    });
  } else {
    interceptAndEnforcePureCopy();
    setTimeout(interceptAndEnforcePureCopy, 500);
  }

/**
 * CalcWorker — Common Shared Utilities
 * Handles Theme Management, Mobile Drawer, Audio, and Universal Sidebar Synchronization.
 */

class CalcWorkerApp {
  constructor() {
    // Dark-only forever: theme toggle removed, always dark.
    this.theme = 'dark';
    try { localStorage.setItem('calcworker_theme', 'dark'); } catch(e) {}
    this.audioEnabled = localStorage.getItem('calcworker_sound') !== 'false';
    this.audioCtx = null;
    this.init();
  }

  init() {
    document.documentElement.setAttribute('data-theme', this.theme);
    this.updateThemeButton();
    this.syncSidebarAcrossPages();

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.bindEvents());
    } else {
      this.bindEvents();
    }
  }

  syncSidebarAcrossPages() {
    if (typeof renderGlobalSidebar === 'function') {
      renderGlobalSidebar();
    }
  }

  bindEvents() {
    const themeBtn = document.getElementById('themeToggleBtn');
    if (themeBtn) {
      themeBtn.style.display = 'none';
      themeBtn.setAttribute('aria-hidden', 'true');
    }

    const hamburger = document.getElementById('hamburgerBtn');
    const sidebar = document.getElementById('sidebar');
    const backdrop = document.getElementById('sidebarBackdrop');

    if (hamburger && sidebar && backdrop) {
      hamburger.addEventListener('click', () => {
        this.playClick();
        sidebar.classList.toggle('open');
        backdrop.classList.toggle('open');
      });

      backdrop.addEventListener('click', () => {
        sidebar.classList.remove('open');
        backdrop.classList.remove('open');
      });
    }

    const searchInput = document.getElementById('searchToolsInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const cards = document.querySelectorAll('.tool-card');
        cards.forEach(card => {
          const text = (card.innerText || '').toLowerCase();
          card.style.display = text.includes(query) ? 'flex' : 'none';
        });
      });
    }
  }

  toggleTheme() {
    // Theme toggle removed: dark-only forever.
    document.documentElement.setAttribute('data-theme', 'dark');
    try { localStorage.setItem('calcworker_theme', 'dark'); } catch(e) {}
  }

    updateThemeButton() {
    const btn = document.getElementById("themeToggleBtn");
    if (btn) { btn.style.display = "none"; btn.setAttribute("aria-hidden", "true"); }
    }
  playClick() {
    if (!this.audioEnabled) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!this.audioCtx && AudioContext) this.audioCtx = new AudioContext();
      if (this.audioCtx && this.audioCtx.state === 'suspended') this.audioCtx.resume();
      if (!this.audioCtx) return;

      const now = this.audioCtx.currentTime;
      const osc = this.audioCtx.createOscillator();
      const gain = this.audioCtx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(540, now);
      osc.frequency.exponentialRampToValueAtTime(220, now + 0.035);

      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);

      osc.connect(gain);
      gain.connect(this.audioCtx.destination);
      osc.start(now);
      osc.stop(now + 0.035);
    } catch (e) {}
  }

  showToast(msg) {
    let toast = document.getElementById('cwToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'cwToast';
      toast.className = 'toast-notice';
      document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2200);
  }

  static fmtUSD(amount, decimals = 0) {
    if (isNaN(amount) || amount === null || !isFinite(amount)) return '$0';
    return '$' + Number(amount).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  static fmtPercent(rate, decimals = 1) {
    if (isNaN(rate) || rate === null || !isFinite(rate)) return '0%';
    return Number(rate).toFixed(decimals) + '%';
  }

  static fmtNumber(val, decimals = 0) {
    if (isNaN(val) || val === null || !isFinite(val)) return '0';
    return Number(val).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }
}

window.cwApp = new CalcWorkerApp();
/* ==========================================================
   GLOBAL SIDEBAR NAVIGATION (Auto-loads on all 16+ tools)
   ========================================================== */
(function () {
  "use strict";

    const sidebarGroups = window.cwSidebarGroups || [
  {
    "title": "Overview",
    "items": [
      {
        "icon": "\u26a1",
        "label": "Dashboard",
        "href": "/"
      }
    ]
  },
  {
    "title": "Flagship Suite",
    "items": [
      {
        "icon": "\ud83e\uddee",
        "label": "OmniCalc Ultra (6-in-1)",
        "href": "/tools/omnicalc.html",
      }
    ]
  },
  {
    "title": "Real Estate & Loans",
    "items": [
      {
        "icon": "\ud83c\udfe0",
        "label": "Mortgage & Amortization",
        "href": "/tools/mortgage-calculator.html",
      },
      {
        "icon": "\ud83d\ude98",
        "label": "Auto Loan Calculator",
        "href": "/tools/auto-loan.html",
      },
      {
        "icon": "\ud83d\ude97",
        "label": "Car Lease Payment",
        "href": "/tools/car-lease-calculator.html"
      },
      {
        "icon": "\ud83c\udfe0",
        "label": "Rent vs Buy Decision",
        "href": "/tools/rent-vs-buy.html"
      },
      {
        "icon": "\ud83c\udfe0",
        "label": "HELOC & Credit Line",
        "href": "/tools/heloc-calculator.html"
      },
      {
        "icon": "\ud83c\udf93",
        "label": "Student Loan Repayment",
        "href": "/tools/student-loan.html"
      },
      {
        "icon": "\ud83d\udcb3",
        "label": "Debt Snowball & Avalanche",
        "href": "/tools/debt-payoff.html"
      },
      {
        "icon": "\ud83d\udcb3",
        "label": "Credit Card Payoff",
        "href": "/tools/credit-card-payoff.html"
      }
    ]
  },
  {
    "title": "Taxes, Income & Career",
    "items": [
      {
        "icon": "\ud83d\udcb5",
        "label": "Paycheck Net Take-Home (2026)",
        "href": "/tools/paycheck-calculator.html",
      },
      {
        "icon": "\ud83d\udcbc",
        "label": "Freelance 1099 Tax Estimator",
        "href": "/tools/freelance-tax-calculator.html",
      },
      {
        "icon": "\ud83c\udfdb\ufe0f",
        "label": "Tax Withholding (2026)",
        "href": "/tools/tax-withholding.html"
      },
      {
        "icon": "\ud83d\udcbc",
        "label": "Freelancer Hourly Rate",
        "href": "/tools/hourly-rate.html"
      },
      {
        "icon": "\ud83d\ude97",
        "label": "Gig Worker Net Profit",
        "href": "/tools/gig-profit.html"
      },
      {
        "icon": "\u23f1\ufe0f",
        "label": "Overtime & 1.5x Pay",
        "href": "/tools/overtime-calculator.html"
      },
      {
        "icon": "\ud83c\udfdb\ufe0f",
        "label": "US State Sales Tax",
        "href": "/tools/sales-tax-calculator.html"
      }
    ]
  },
  {
    "title": "Creators & Social Media",
    "items": [
      {
        "icon": "\ud83d\udecd\ufe0f",
        "label": "TikTok Shop Affiliate",
        "href": "/tools/tiktok-shop-affiliate-calculator.html",
      },
      {
        "icon": "\ud83c\udfb5",
        "label": "TikTok Money Calc",
        "href": "/tools/tiktok-money-calculator.html",
      },
      {
        "icon": "\ud83e\ude99",
        "label": "TikTok Coins & Gifts",
        "href": "/tools/tiktok-coins-calculator.html",
      },
      {
        "icon": "\u25b6\ufe0f",
        "label": "YouTube Money & CPM",
        "href": "/tools/youtube-money-calculator.html",
      },
      {
        "icon": "\ud83d\udcf8",
        "label": "Instagram Sponsored Rate",
        "href": "/tools/instagram-money-calculator.html",
      },
      {
        "icon": "\ud83c\udf99\ufe0f",
        "label": "Podcast Ad Sponsorship",
        "href": "/tools/podcast-sponsorship-calculator.html"
      },
      {
        "icon": "\ud83d\ude80",
        "label": "Channel Milestone Tracker",
        "href": "/tools/channel-growth-calculator.html"
      }
    ]
  },
  {
    "title": "E-Commerce & Small Business",
    "items": [
      {
        "icon": "\u2696\ufe0f",
        "label": "Multi-Platform Profit",
        "href": "/tools/ecommerce-profit-comparator.html",
      },
      {
        "icon": "\ud83d\udce6",
        "label": "Amazon FBA Calculator",
        "href": "/tools/amazon-fba-calculator.html",
      },
      {
        "icon": "\ud83d\udecd\ufe0f",
        "label": "Shopify Fee & Margin",
        "href": "/tools/shopify-fee-calculator.html",
      },
      {
        "icon": "\ud83d\udce6",
        "label": "eBay Seller Fee & Profit",
        "href": "/tools/ebay-fee-calculator.html"
      },
      {
        "icon": "\ud83d\udecd\ufe0f",
        "label": "Etsy Seller Fee & Profit",
        "href": "/tools/etsy-profit.html"
      },
      {
        "icon": "\ud83d\udcca",
        "label": "Business Break-Even Point",
        "href": "/tools/break-even.html"
      }
    ]
  },
  {
    "title": "Investments & Wealth Planning",
    "items": [
      {
        "icon": "\ud83d\udcc8",
        "label": "Compound Interest & Savings",
        "href": "/tools/compound-interest.html"
      },
      {
        "icon": "\ud83c\udfd6\ufe0f",
        "label": "401(k) & Retirement Savings",
        "href": "/tools/retirement-401k.html"
      },
      {
        "icon": "\ud83d\udcc8",
        "label": "Roth IRA Tax-Free Growth",
        "href": "/tools/roth-ira-calculator.html"
      },
      {
        "icon": "\ud83e\ude99",
        "label": "Crypto Profit & ROI",
        "href": "/tools/crypto-profit-calculator.html"
      },
      {
        "icon": "\ud83d\udcb5",
        "label": "US Inflation & Purchasing Power",
        "href": "/tools/inflation-calculator.html"
      },
      {
        "icon": "\u2600\ufe0f",
        "label": "Solar Panel ROI Estimator",
        "href": "/tools/solar-roi.html"
      }
    ]
  },
  {
    "title": "Currency & Global Exchange",
    "items": [
      {
        "icon": "\ud83d\udcb5",
        "label": "Currency Converter (Live Rates)",
        "href": "/tools/currency-converter.html",
      }
    ]
  },
  {
    "title": "Health, Fitness & Everyday Math",
    "items": [
      {
        "icon": "\ud83d\udd22",
        "label": "Percentage Calculator",
        "href": "/tools/percentage-calculator.html",
      },
      {
        "icon": "\ud83c\udf82",
        "label": "Exact Age & Date Calculator",
        "href": "/tools/age-calculator.html",
      },
      {
        "icon": "\u2696\ufe0f",
        "label": "BMI & Body Composition",
        "href": "/tools/bmi-calculator.html"
      },
      {
        "icon": "\ud83d\udd25",
        "label": "Calorie & TDEE Deficit",
        "href": "/tools/calorie-calculator.html"
      },
      {
        "icon": "\ud83d\udca7",
        "label": "Daily Water Intake",
        "href": "/tools/water-intake-calculator.html"
      },
      {
        "icon": "\ud83c\udf7d\ufe0f",
        "label": "Tip Calculator & Bill Splitter",
        "href": "/tools/tip-calculator.html",
      },
      {
        "icon": "\u26fd",
        "label": "Fuel Cost & Gas Mileage",
        "href": "/tools/fuel-cost-calculator.html"
      }
    ]
  }
];

  function renderGlobalSidebar() {
    const sidebarNav = document.querySelector("#sidebar .sidebar-nav") || document.querySelector(".sidebar-nav");
    if (!sidebarNav) return;

    const currentPath = normalizePath(window.location.pathname);

    sidebarNav.innerHTML = sidebarGroups
      .map(function (group) {
        return `
          <div>
            <div class="nav-group-title">${escapeHtml(group.title)}</div>
            <ul class="nav-links">
              ${group.items
                .map(function (item) {
                  const itemPath = normalizePath(item.href);
                  const activeClass = itemPath === currentPath ? " active" : "";
                  const badgeHtml = item.badge
                    ? `<span class="nav-link-badge" style="background:${item.badgeType === "hot" ? "#f59e0b" : "#2563eb"};color:#fff;font-size:0.58rem;font-weight:800;padding:2px 6px;border-radius:6px;margin-left:auto;flex-shrink:0;">${escapeHtml(item.badge)}</span>`
                    : "";
                  return `
                    <li>
                      <a href="${escapeHtml(item.href)}" class="nav-link${activeClass}" title="${escapeHtml(item.label)}">
                        <span class="nav-link-icon">${escapeHtml(item.icon)}</span>
                        <span class="nav-link-text">${escapeHtml(item.label)}</span>
                        ${badgeHtml}
                      </a>
                    </li>
                  `;
                })
                .join("")}
            </ul>
          </div>
        `;
      })
      .join("");

// Bulletproof Sidebar Scroll Restoration
    const sidebarEl = document.getElementById("sidebar") || document.querySelector(".sidebar");
    if (sidebarEl) {
      const restorePos = function () {
        const activeLink = sidebarNav.querySelector(".nav-link.active");
        const savedScroll = sessionStorage.getItem("cw_sidebar_scroll");

        if (currentPath === "/") {
          sidebarEl.scrollTop = 0;
          sessionStorage.setItem("cw_sidebar_scroll", "0");
        } else if (savedScroll !== null && !isNaN(parseInt(savedScroll, 10)) && parseInt(savedScroll, 10) > 0) {
          sidebarEl.scrollTop = parseInt(savedScroll, 10);
        } else if (activeLink) {
          const targetPos = activeLink.offsetTop - (sidebarEl.clientHeight / 2) + (activeLink.clientHeight / 2);
          sidebarEl.scrollTop = Math.max(0, targetPos);
          sessionStorage.setItem("cw_sidebar_scroll", sidebarEl.scrollTop);
        }
      };

      restorePos();
      requestAnimationFrame(restorePos);
      setTimeout(restorePos, 60);

      sidebarEl.addEventListener("scroll", function () {
        sessionStorage.setItem("cw_sidebar_scroll", sidebarEl.scrollTop);
      }, { passive: true });

      sidebarNav.addEventListener("click", function (e) {
        const link = e.target.closest("a");
        if (link) {
          if (link.getAttribute("href") === "/") {
            sessionStorage.setItem("cw_sidebar_scroll", "0");
          } else {
            sessionStorage.setItem("cw_sidebar_scroll", sidebarEl.scrollTop);
          }
        }
      });
    }
    }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", renderGlobalSidebar);
  } else {
    renderGlobalSidebar();
  }
})();
/* ==========================================================
   GLOBAL LOGO AUTO-FIX (Loads logo.png on every single tool)
   ========================================================== */
(function() {
  function updateGlobalLogo() {
    var logos = document.querySelectorAll('.sidebar-brand img, .sidebar-logo');
    logos.forEach(function(img) {
      img.src = '/assets/logo.png';
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateGlobalLogo);
  } else {
    updateGlobalLogo();
  }
})();
/* ==========================================================
   GLOBAL FAVICON AUTO-SET (Loads CW Favicon on all pages)
   ========================================================== */
(function() {
  var fav = document.querySelector("link[rel*='icon']");
  if (!fav) {
    fav = document.createElement('link');
    fav.rel = 'icon';
    document.head.appendChild(fav);
  }
  fav.type = 'image/png';
  fav.href = '/assets/favicon.png';
})();
/* ==========================================================
   ENHANCED LOGO DISPLAY & 5-SECOND FLASH SHIMMER WAVE
   ========================================================== */
(function() {
  function applyLogoEnhancements() {
    if (document.getElementById('cw-logo-enhancement-styles')) return;
    var style = document.createElement('style');
    style.id = 'cw-logo-enhancement-styles';
    style.textContent = [
        '.cw-offline-strip { font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif !important; font-size: 0.82rem !important; padding: 7px 20px !important; position: sticky !important; top: 0px !important; z-index: 50 !important; overflow: hidden !important; width: 100% !important; transition: all 0.3s ease !important; }',
        '[data-theme="dark"] .cw-offline-strip { background: linear-gradient(90deg, #070a12 0%, #0d1528 50%, #070a12 100%) !important; border-bottom: 1px solid rgba(56, 189, 248, 0.25) !important; color: #f8fafc !important; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important; }',
        '[data-theme="dark"] .cw-offline-strip { background: linear-gradient(90deg, #1c2330 0%, #2b3549 50%, #1c2330 100%) !important; border-bottom: 1px solid rgba(56, 189, 248, 0.25) !important; color: #e6ecf5 !important; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35) !important; }',
        '.cw-offline-strip-inner { max-width: 1400px !important; margin: 0 auto !important; display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 12px !important; }',
        '.cw-offline-left { display: inline-flex !important; align-items: center !important; gap: 10px !important; flex-wrap: wrap !important; }',
        '.cw-offline-badge { display: inline-flex !important; align-items: center !important; gap: 6px !important; padding: 3px 10px !important; border-radius: 9999px !important; font-weight: 700 !important; font-size: 0.72rem !important; letter-spacing: 0.03em !important; white-space: nowrap !important; transition: all 0.3s ease !important; }',
        '[data-theme="dark"] .cw-offline-badge { background: rgba(16, 185, 129, 0.16) !important; border: 1px solid rgba(16, 185, 129, 0.45) !important; color: #34d399 !important; }',
        '[data-theme="dark"] .cw-offline-badge { background: rgba(16, 185, 129, 0.16) !important; border: 1px solid rgba(16, 185, 129, 0.45) !important; color: #34d399 !important; }',
        '.cw-offline-dot { width: 7px !important; height: 7px !important; border-radius: 50% !important; background-color: #10b981 !important; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7) !important; animation: cw-pulse-green 2s infinite cubic-bezier(0.4, 0, 0.6, 1) !important; }',
        '@keyframes cw-pulse-green { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }',
        '.cw-offline-headline { line-height: 1.35 !important; font-size: 0.84rem !important; }',
        '[data-theme="dark"] .cw-offline-headline { color: #e2e8f0 !important; }',
        '[data-theme="dark"] .cw-offline-headline strong { color: #38bdf8 !important; font-weight: 700 !important; }',
        '[data-theme="dark"] .cw-offline-headline { color: #c7d0e0 !important; font-weight: 600 !important; }',
        '[data-theme="dark"] .cw-offline-headline strong { color: #7dd3fc !important; font-weight: 800 !important; }',
        '.cw-offline-right { display: inline-flex !important; align-items: center !important; gap: 8px !important; flex-shrink: 0 !important; }',
        '.cw-pwa-install-btn { padding: 4px 14px !important; border-radius: 6px !important; font-size: 0.74rem !important; font-weight: 700 !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 6px !important; transition: all 0.2s ease !important; white-space: nowrap !important; border: none !important; }',
        '[data-theme="dark"] .cw-pwa-install-btn { background: linear-gradient(135deg, #0284c7, #2563eb) !important; color: #ffffff !important; box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4) !important; }',
        '[data-theme="dark"] .cw-pwa-install-btn { background: linear-gradient(135deg, #0284c7, #2563eb) !important; color: #ffffff !important; box-shadow: 0 2px 8px rgba(37, 99, 235, 0.4) !important; }',
        '.cw-pwa-install-btn:hover { filter: brightness(1.1) !important; transform: translateY(-1px) !important; }',
        '.cw-offline-dismiss { background: transparent !important; border: none !important; color: var(--text-muted) !important; font-size: 0.9rem !important; padding: 2px 7px !important; cursor: pointer !important; border-radius: 4px !important; line-height: 1 !important; transition: all 0.2s ease !important; }',
        '.cw-offline-dismiss:hover { color: var(--text-main) !important; background: rgba(0, 0, 0, 0.08) !important; }',
        '@media (max-width: 768px) { .cw-offline-strip { padding: 6px 12px !important; } .cw-offline-headline { font-size: 0.74rem !important; max-width: 55vw !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; } }'
      ].join('\n');
    document.head.appendChild(style);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', applyLogoEnhancements);
  } else {
    applyLogoEnhancements();
  }
})();


/* ==========================================================
   OFFLINE ENGINE & UNIVERSAL TOP NOTIFICATION STRIP (PWA)
   Renders prominent offline-ready banner on Dashboard & all 137 tools
   ========================================================== */
(function() {
  function isPwaInstalled() {
    try {
      if (window.matchMedia && window.matchMedia('(display-mode: standalone)').matches) return true;
      if (window.matchMedia && window.matchMedia('(display-mode: window-controls-overlay)').matches) return true;
      if (window.navigator && window.navigator.standalone === true) return true;
      if (document.referrer && document.referrer.includes('android-app://')) return true;
      if (localStorage.getItem('cw_pwa_installed') === 'true') return true;
      if (localStorage.getItem('cw_app_install_clicked') === 'true') return true;
    } catch(e) {}
    return false;
  }

  function isPwaDismissed() {
    try {
      var d = localStorage.getItem('cw_pwa_strip_dismissed');
      if (d === 'true') return true;
      if (d && (Date.now() - parseInt(d, 10) < 30 * 24 * 3600 * 1000)) return true;
    } catch(e) {}
    return false;
  }

  function hideAllInstallButtons() {
    document.querySelectorAll('#cwPwaInstallBtn, .cw-pwa-install-btn, .cw-install-btn, #cwInstallBtn, .install-app-btn').forEach(function(b) {
      b.style.display = 'none';
      b.setAttribute('aria-hidden', 'true');
    });
    var strip = document.getElementById('cw-offline-strip');
    if (strip && navigator.onLine) {
      strip.style.display = 'none';
    }
  }

  function applyPWAOfflineSuite() {
    // 1. Inject Styles if not present
    if (!document.getElementById('cw-pwa-offline-styles')) {
      var style = document.createElement('style');
      style.id = 'cw-pwa-offline-styles';
      style.textContent = [
        '.cw-offline-strip { background: linear-gradient(90deg, #091224 0%, #0f2347 50%, #091224 100%) !important; border-bottom: 1px solid rgba(59, 130, 246, 0.28) !important; color: #e2e8f0 !important; font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif !important; font-size: 0.78rem !important; padding: 7px 20px !important; position: sticky !important; top: 0px !important; z-index: 50 !important; overflow: hidden !important; width: 100% !important; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.25) !important; transition: all 0.3s ease !important; }',
        '.cw-offline-strip::after { content: "" !important; position: absolute !important; top: -60% !important; left: -120% !important; width: 60% !important; height: 220% !important; background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.03) 20%, rgba(255, 255, 255, 0.6) 50%, rgba(56, 189, 248, 0.25) 75%, transparent 100%) !important; transform: rotate(25deg) !important; pointer-events: none !important; animation: cw-offline-strip-flash 10s infinite cubic-bezier(0.4, 0, 0.2, 1) !important; z-index: 10 !important; }',
        '@keyframes cw-offline-strip-flash { 0% { left: -120%; opacity: 0; } 1% { opacity: 1; } 14% { left: 140%; opacity: 1; } 15% { opacity: 0; } 100% { left: 140%; opacity: 0; } }',
        '.cw-offline-strip-inner { max-width: 1400px !important; margin: 0 auto !important; display: flex !important; align-items: center !important; justify-content: space-between !important; gap: 12px !important; }',
        '.cw-offline-left { display: inline-flex !important; align-items: center !important; gap: 10px !important; flex-wrap: wrap !important; }',
        '.cw-offline-badge { display: inline-flex !important; align-items: center !important; gap: 6px !important; background: rgba(16, 185, 129, 0.14) !important; border: 1px solid rgba(16, 185, 129, 0.4) !important; color: #34d399 !important; padding: 2px 9px !important; border-radius: 9999px !important; font-weight: 700 !important; font-size: 0.7rem !important; letter-spacing: 0.03em !important; white-space: nowrap !important; transition: all 0.3s ease !important; }',
        '.cw-offline-badge.offline-mode { background: rgba(245, 158, 11, 0.16) !important; border-color: rgba(245, 158, 11, 0.5) !important; color: #fbbf24 !important; }',
        '.cw-offline-dot { width: 7px !important; height: 7px !important; border-radius: 50% !important; background-color: #10b981 !important; box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7) !important; animation: cw-pulse-green 2s infinite cubic-bezier(0.4, 0, 0.6, 1) !important; }',
        '.cw-offline-badge.offline-mode .cw-offline-dot { background-color: #f59e0b !important; box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7) !important; animation: cw-pulse-amber 2s infinite cubic-bezier(0.4, 0, 0.6, 1) !important; }',
        '@keyframes cw-pulse-green { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }',
        '@keyframes cw-pulse-amber { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(245, 158, 11, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); } }',
        '.cw-offline-headline { color: #cbd5e1 !important; line-height: 1.35 !important; }',
        '.cw-offline-headline strong { color: #38bdf8 !important; font-weight: 600 !important; }',
        '.cw-offline-right { display: inline-flex !important; align-items: center !important; gap: 8px !important; flex-shrink: 0 !important; }',
        '.cw-pwa-install-btn { background: linear-gradient(135deg, #1d4ed8, #2563eb) !important; border: 1px solid rgba(255, 255, 255, 0.3) !important; color: #ffffff !important; padding: 4px 12px !important; border-radius: 6px !important; font-size: 0.72rem !important; font-weight: 700 !important; cursor: pointer !important; display: inline-flex !important; align-items: center !important; gap: 5px !important; transition: all 0.2s ease !important; box-shadow: 0 2px 6px rgba(29, 78, 216, 0.3) !important; white-space: nowrap !important; }',
        '.cw-pwa-install-btn:hover { background: linear-gradient(135deg, #2563eb, #3b82f6) !important; transform: translateY(-1px) !important; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.45) !important; }',
        '.cw-offline-dismiss { background: transparent !important; border: none !important; color: #94a3b8 !important; font-size: 0.85rem !important; padding: 2px 7px !important; cursor: pointer !important; border-radius: 4px !important; line-height: 1 !important; transition: all 0.2s ease !important; }',
        '.cw-offline-dismiss:hover { color: #ffffff !important; background: rgba(255, 255, 255, 0.12) !important; }',
        '@media (max-width: 768px) { .cw-offline-strip { padding: 6px 12px !important; } .cw-offline-headline { font-size: 0.72rem !important; } }'
      ].join('\n');
      document.head.appendChild(style);
    }

    // 2. Head Meta & Manifest Auto-Link
    if (!document.querySelector('link[rel="manifest"]')) {
      var manLink = document.createElement('link');
      manLink.rel = 'manifest';
      manLink.href = '/manifest.json';
      document.head.appendChild(manLink);
    }
    if (!document.querySelector('meta[name="theme-color"]')) {
      var metaTheme = document.createElement('meta');
      metaTheme.name = 'theme-color';
      metaTheme.content = '#1d4ed8';
      document.head.appendChild(metaTheme);
    }
    if (!document.querySelector('link[rel="apple-touch-icon"]')) {
      var appleIcon = document.createElement('link');
      appleIcon.rel = 'apple-touch-icon';
      appleIcon.href = '/assets/favicon.png';
      document.head.appendChild(appleIcon);
    }
    if (!document.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
      var appleMeta = document.createElement('meta');
      appleMeta.name = 'apple-mobile-web-app-capable';
      appleMeta.content = 'yes';
      document.head.appendChild(appleMeta);
    }

    // 3. Register Service Worker
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function() {
        navigator.serviceWorker.register('/sw.js', { updateViaCache: 'none' }).then(function(reg){ reg.update(); return reg; })
          .then(function(reg) {
            console.log('[CalcWorker] Offline PWA ServiceWorker active:', reg.scope);
          })
          .catch(function(err) {
            console.warn('[CalcWorker] ServiceWorker registration warning:', err);
          });
      });
    }

    // 4. Hook Up Network Status & PWA Install Engine
    var installed = isPwaInstalled();
    var dismissed = isPwaDismissed();

    if (installed) {
      hideAllInstallButtons();
    }

    var strip = document.getElementById('cw-offline-strip');
    var mainViewport = document.querySelector('.main-viewport') || document.querySelector('.app-shell') || document.body;
    var topbar = mainViewport ? mainViewport.querySelector('.topbar') : null;

    if (!strip && mainViewport && (!installed || !navigator.onLine) && (!dismissed || !navigator.onLine)) {
      strip = document.createElement('div');
      strip.id = 'cw-offline-strip';
      strip.className = 'cw-offline-strip';
      strip.innerHTML = '<div class="cw-offline-strip-inner">' +
        '<div class="cw-offline-left">' +
          '<span class="cw-offline-badge" id="cwOfflineBadge">' +
            '<span class="cw-offline-dot"></span>' +
            '<span id="cwOfflineBadgeText">⚡ 100% Offline App</span>' +
          '</span>' +
          '<span class="cw-offline-headline" id="cwOfflineHeadline">' +
            '📲 <strong>Get the CalcWorker App:</strong> all 137 precision calculators in your pocket — free forever, works 100% offline.' +
          '</span>' +
        '</div>' +
        '<div class="cw-offline-right">' +
          (!installed ? '<button class="cw-pwa-install-btn" id="cwPwaInstallBtn" type="button" title="Get CalcWorker on Google Play">' +
            '<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M4 3.5v17c0 .4.43.64.76.43l8.9-5.32 2.3-1.38c.34-.2.34-.66 0-.86l-2.3-1.38-8.9-5.32c-.33-.21-.76 0-.76.43z" opacity=".95"/><path d="M16.66 10.5l2.3 1.38c.8.48.8 1.76 0 2.24l-2.3 1.38 2.9 1.74c1.1-.62 1.84-1.8 1.84-3.24s-.74-2.62-1.84-3.24l-2.9 1.74z" opacity=".55"/></svg>' +
            '<span>Get the App</span>' +
          '</button>' : '') +
          '<button class="cw-offline-dismiss" id="cwOfflineDismissBtn" type="button" title="Dismiss notification" aria-label="Dismiss">✕</button>' +
        '</div>' +
      '</div>';
      if (topbar) {
        mainViewport.insertBefore(strip, topbar);
      } else {
        mainViewport.insertBefore(strip, mainViewport.firstChild);
      }

      var dismissBtn = document.getElementById('cwOfflineDismissBtn');
      if (dismissBtn) {
        dismissBtn.addEventListener('click', function() {
          try {
            localStorage.setItem('cw_pwa_strip_dismissed', String(Date.now()));
          } catch(e) {}
          if (strip) strip.style.display = 'none';
        });
      }
    }

    // Network Status Indicators
    function refreshNetworkUI() {
      var badge = document.getElementById('cwOfflineBadge');
      var badgeText = document.getElementById('cwOfflineBadgeText');
      var headline = document.getElementById('cwOfflineHeadline');
      var stripEl = document.getElementById('cw-offline-strip');

      if (navigator.onLine) {
        if ((isPwaInstalled() || isPwaDismissed()) && stripEl) {
          stripEl.style.display = 'none';
        }
        if (badge) badge.classList.remove('offline-mode');
        if (badgeText) badgeText.textContent = '⚡ 100% Offline App';
        if (headline) headline.innerHTML = '📲 <strong>Get the CalcWorker App:</strong> all 137 precision calculators in your pocket — free forever, works 100% offline.';
      } else {
        if (stripEl) stripEl.style.display = 'block';
        if (badge) badge.classList.add('offline-mode');
        if (badgeText) badgeText.textContent = '📶 Offline Mode Active';
        if (headline) headline.innerHTML = '📶 <strong>You are currently Offline:</strong> All 102+ calculators, formulas and tools are running 100% locally from your device cache.';
      }
    }

    window.addEventListener('online', refreshNetworkUI);
    window.addEventListener('offline', refreshNetworkUI);
    refreshNetworkUI();

    // Listen for install events
    window.addEventListener('appinstalled', function() {
      try {
        localStorage.setItem('cw_pwa_installed', 'true');
      } catch(e) {}
      hideAllInstallButtons();
      showToast('🎉 CalcWorker installed successfully! Ready for 100% offline use.');
    });

    // 5. PWA Install Prompt Handler & Modal
    var deferredPrompt = null;
    window.addEventListener('beforeinstallprompt', function(e) {
      e.preventDefault();
      deferredPrompt = e;
      if (!isPwaInstalled()) {
        document.querySelectorAll('#cwPwaInstallBtn, .cw-pwa-install-btn, .cw-install-btn, #cwInstallBtn').forEach(function(b) {
          b.style.display = 'inline-flex';
        });
      }
    });

    function openInstallModal() {
      // Install now redirects to the Google Play Store listing (no web/PWA install).
      try { localStorage.setItem('cw_app_install_clicked', 'true'); } catch(e) {}
      hideAllInstallButtons();
      showToast('Opening Google Play Store…');
      window.open('https://play.google.com/store/apps/details?id=com.zaviyanllc.calcworker', '_blank', 'noopener');
      return;
    }


    document.addEventListener('click', function(e) {
      var btn = e.target.closest('#cwPwaInstallBtn, .cw-pwa-install-btn, .cw-install-btn, #cwInstallBtn, .install-app-btn');
      if (btn) {
        e.preventDefault();
        openInstallModal();
      }
    });
  }

  // Toast Notification System
  function showToast(message, duration) {
    duration = duration || 3200;
    var existingToast = document.querySelector('.cw-toast');
    if (existingToast && existingToast.parentNode) existingToast.parentNode.removeChild(existingToast);

    var toast = document.createElement('div');
    toast.className = 'cw-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(function() {
      toast.classList.remove('show');
    }, 10);

    setTimeout(function() {
      toast.classList.remove('show');
      setTimeout(function() { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 300);
    }, duration);
  }
  window.cwToast = showToast;

    function initSpotlightCards() {
    if (!window.matchMedia || !window.matchMedia('(pointer: fine)').matches) return;
    document.addEventListener('mousemove', function(e) {
      var target = e.target.closest('.tool-card, .kpi-card, .trust-card, .trending-card, .tool-form-card, .tool-results-card');
      if (target) {
        var rect = target.getBoundingClientRect();
        var x = e.clientX - rect.left;
        var y = e.clientY - rect.top;
        target.style.setProperty('--mouse-x', x + 'px');
        target.style.setProperty('--mouse-y', y + 'px');
      }
    }, { passive: true });
  }

  function initToolSearchAndFilters() {
    var searchInput = document.getElementById('toolSearchInput') || document.getElementById('searchToolsInput');
    var filterBtns = document.querySelectorAll('.cat-filter-btn');
    var toolsGrid = document.getElementById('toolsGrid');
    var cards = document.querySelectorAll('#toolsGrid .tool-card');
    var countEl = document.getElementById('toolResultsCount');
    var dropdown = document.getElementById('heroSearchDropdown');

    if (!cards.length && !searchInput) return;

    // Built-in Synonyms Thesaurus for Natural Language and Multi-Token Matching
    var SYNONYMS = {
      'car': ['auto', 'vehicle', 'automotive', 'lease', 'loan', 'fuel', 'gas', 'electric', 'ev', 'tire', 'commute'],
      'auto': ['car', 'vehicle', 'automotive', 'lease', 'loan'],
      'vehicle': ['car', 'auto', 'lease', 'loan'],
      'house': ['home', 'mortgage', 'realty', 'real estate', 'property', 'refinance', 'refi', 'heloc', 'equity', 'rent'],
      'home': ['house', 'mortgage', 'realty', 'real estate', 'property', 'refinance', 'refi', 'heloc', 'equity'],
      'mortgage': ['home', 'house', 'loan', 'refinance', 'refi', 'closing costs', 'fha', 'conventional', 'equity', 'heloc', 'pmi'],
      'refi': ['refinance', 'mortgage refinance', 'rate', 'closing costs', 'break even'],
      'refinance': ['refi', 'mortgage', 'loan', 'rate', 'interest', 'closing costs', 'break even'],
      'pslf': ['student loan', 'forgiveness', 'public service', 'save plan', 'idr', 'income driven'],
      'fha': ['mortgage', 'conventional', 'down payment', 'pmi', 'mip', 'home loan'],
      'salary': ['paycheck', 'wage', 'wages', 'hourly', 'rate', 'take home', 'income', 'overtime', 'job offer'],
      'pay': ['paycheck', 'salary', 'wage', 'hourly', 'take home', 'income', 'compensation'],
      'paycheck': ['salary', 'wage', 'wages', 'hourly', 'take home', 'withholding', 'taxes', 'net pay', 'gross pay'],
      'tax': ['taxes', 'irs', 'withholding', 'w2', '1099', 'freelance', 'state tax', 'property tax', 'capital gains', 'sales tax', 'child tax credit', 'estate tax'],
      'taxes': ['tax', 'irs', 'withholding', 'w2', '1099', 'freelance', 'state tax'],
      'irs': ['tax', 'taxes', 'withholding', '1099', 'w2', '401k', 'rmd', 'ira', 'roth', 'standard deduction'],
      'loan': ['debt', 'mortgage', 'auto loan', 'personal loan', 'student loan', 'payday loan', 'heloc', 'interest', 'payment'],
      'debt': ['loan', 'credit card', 'payoff', 'avalanche', 'snowball', 'personal loan', 'interest'],
      'card': ['credit card', 'debt', 'payoff', 'balance', 'apr', 'interest'],
      'credit': ['credit card', 'score', 'debt', 'payoff', 'apr', 'loan'],
      'crypto': ['cryptocurrency', 'bitcoin', 'btc', 'eth', 'ethereum', 'solana', 'profit', 'trading', 'token'],
      'invest': ['investment', 'stock', 'compound interest', '401k', 'roth ira', 'cd ladder', 'yield', 'returns', 'portfolio'],
      'retirement': ['401k', 'ira', 'roth ira', 'social security', 'pension', 'nest egg', 'rmd', 'inflation', 'retire'],
      'retire': ['retirement', '401k', 'roth ira', 'social security', 'rmd'],
      'social security': ['ssa', 'benefits', 'retirement age', 'fra', 'pia', 'spousal'],
      'business': ['llc', 'scorp', 's-corp', 'ecommerce', 'fba', 'shopify', 'etsy', 'ebay', 'profit', 'margin', 'markup', 'break even', 'invoice factoring', 'cac', 'ltv', 'nnn'],
      'creator': ['youtube', 'tiktok', 'instagram', 'podcast', 'substack', 'influencer', 'diamonds', 'monetization', 'sponsorship'],
      'youtube': ['creator', 'video', 'cpm', 'rpm', 'views', 'ad revenue', 'earnings'],
      'tiktok': ['creator', 'coins', 'diamonds', 'shop', 'affiliate', 'creator fund', 'gifts'],
      'instagram': ['creator', 'reels', 'sponsored post', 'brand deal', 'influencer'],
      'gym': ['bench press', '1rm', 'one rep max', 'lifting', 'fitness', 'strength', 'workout'],
      'health': ['bmi', 'calorie', 'calories', 'steps', 'miles', 'water', 'hydration', 'age', 'fitness', 'weight'],
      'calories': ['calorie', 'tdee', 'bmr', 'macro', 'macros', 'weight loss', 'deficit', 'diet'],
      'calorie': ['calories', 'tdee', 'bmr', 'macro', 'weight loss', 'nutrition'],
      'prompt': ['ai', 'tokens', 'gpt-4o', 'claude', 'gemini', 'deepseek', 'llm', 'api cost', 'prompt engineering'],
      'token': ['tokens', 'ai', 'prompt', 'llm', 'gpt', 'claude', 'cost', 'bpe'],
      'ai': ['prompt', 'token', 'tokens', 'cost', 'llm', 'gpt', 'claude', 'gemini', 'deepseek']
    };

    // Expand query with synonyms
    function expandSynonyms(tokens) {
      var expanded = [].concat(tokens);
      tokens.forEach(function(token) {
        if (SYNONYMS[token]) {
          expanded = expanded.concat(SYNONYMS[token]);
        }
      });
      return expanded;
    }

    // Collect all tools metadata for high-speed client-side autocomplete & search
    var toolCatalog = [];
    cards.forEach(function(card) {
      var href = card.getAttribute('href') || '';
      var titleEl = card.querySelector('.tool-card-title');
      var descEl = card.querySelector('.tool-card-desc');
      var badgeEl = card.querySelector('.tool-category-badge');
      var iconEl = card.querySelector('.tool-card-icon');
      
      var title = titleEl ? titleEl.textContent.trim() : '';
      var desc = descEl ? descEl.textContent.trim() : '';
      var badge = badgeEl ? badgeEl.textContent.trim() : '';
      var icon = iconEl ? iconEl.textContent.trim() : '⚡';
      var cat = (card.getAttribute('data-category') || '').toLowerCase();
      var keywords = (card.getAttribute('data-keywords') || '').toLowerCase();

      if (title && href) {
        var fullSearchText = (title + ' ' + desc + ' ' + badge + ' ' + keywords + ' ' + href + ' ' + cat).toLowerCase();
        toolCatalog.push({
          href: href,
          title: title,
          desc: desc,
          badge: badge,
          icon: icon,
          cat: cat,
          keywords: keywords,
          card: card,
          searchIndex: fullSearchText
        });
      }
    });

    var activeCategory = 'all';
    var searchQuery = '';
    if (searchInput) {
      searchInput.value = '';
    }

    function escapeHtml(str) {
      return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function renderDropdown(matches) {
      if (!dropdown) return;
      if (!searchQuery.trim()) {
        dropdown.style.display = 'none';
        dropdown.innerHTML = '';
        return;
      }
      dropdown.style.display = 'block';
      if (!matches.length) {
        dropdown.innerHTML = '<div class="search-dropdown-empty" style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 0.88rem;">No calculators found matching "<strong>' + escapeHtml(searchQuery) + '</strong>". Try searching "mortgage", "tax", "car", "salary", or "creator".</div>';
        return;
      }

      var html = '<div class="search-dropdown-header" style="display:flex; justify-content:space-between; align-items:center; padding:8px 14px; background:rgba(255,255,255,0.03); border-bottom:1px solid var(--border); font-size:0.75rem; color:var(--text-muted); font-weight:600;">' +
        '<span>Found ' + matches.length + ' Instant Calculator' + (matches.length === 1 ? '' : 's') + '</span>' +
        '<span>Press Enter ↵ to open</span>' +
        '</div>';

      matches.slice(0, 8).forEach(function(item, idx) {
        html += '<a href="' + item.href + '" class="search-dropdown-item' + (idx === 0 ? ' selected' : '') + '" style="display:flex; align-items:center; gap:12px; padding:10px 14px; text-decoration:none; color:inherit; border-bottom:1px solid rgba(255,255,255,0.04); transition:background 0.15s ease;">';
        html += '  <div class="search-dropdown-icon" style="font-size:1.3rem; width:36px; height:36px; border-radius:8px; background:rgba(37,99,235,0.12); border:1px solid rgba(37,99,235,0.25); display:flex; align-items:center; justify-content:center; flex-shrink:0;">' + item.icon + '</div>';
        html += '  <div class="search-dropdown-info" style="flex:1; min-width:0;">';
        html += '    <div class="search-dropdown-title" style="font-weight:700; font-size:0.88rem; color:var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">' + escapeHtml(item.title) + '</div>';
        html += '    <div class="search-dropdown-cat" style="font-size:0.74rem; color:var(--brand-secondary, #38bdf8); margin-top:2px;">' + escapeHtml(item.badge || item.cat) + '</div>';
        html += '  </div>';
        html += '  <div class="search-dropdown-arrow" style="color:var(--text-muted); font-size:0.85rem;">→</div>';
        html += '</a>';
      });

      if (matches.length > 8) {
        html += '<div style="padding:8px 14px; text-align:center; font-size:0.75rem; color:var(--brand-secondary, #38bdf8); background:rgba(56,189,248,0.05); font-weight:600;">+ ' + (matches.length - 8) + ' more calculators below on dashboard</div>';
      }

      dropdown.innerHTML = html;
    }

    // Match scoring with multi-token AND synonym expansion
    function scoreTool(item, queryTokens, expandedSyns) {
      var sIndex = item.searchIndex;
      var titleLower = item.title.toLowerCase();
      var score = 0;

      // Check if ALL original query tokens match (tokenized AND match)
      var allDirectMatch = true;
      for (var i = 0; i < queryTokens.length; i++) {
        var t = queryTokens[i];
        if (sIndex.indexOf(t) === -1) {
          allDirectMatch = false;
          break;
        }
      }

      if (allDirectMatch) {
        score += 50;
        // Exact title match bonus
        for (var i = 0; i < queryTokens.length; i++) {
          if (titleLower.indexOf(queryTokens[i]) !== -1) score += 20;
        }
      } else {
        // Try synonym-expanded matching
        var matchedTokensCount = 0;
        for (var i = 0; i < queryTokens.length; i++) {
          var t = queryTokens[i];
          if (sIndex.indexOf(t) !== -1) {
            matchedTokensCount++;
          } else {
            // Check synonyms
            var syns = SYNONYMS[t] || [];
            var anySynMatch = false;
            for (var s = 0; s < syns.length; s++) {
              if (sIndex.indexOf(syns[s]) !== -1) {
                anySynMatch = true;
                break;
              }
            }
            if (anySynMatch) matchedTokensCount++;
          }
        }
        if (matchedTokensCount === queryTokens.length) {
          score += 35; // All tokens matched via synonyms
        } else if (matchedTokensCount > 0 && queryTokens.length > 1) {
          score += (matchedTokensCount / queryTokens.length) * 20;
        }
      }

      return score;
    }

    function updateFilter() {
      var rawQuery = (searchQuery || '').trim().toLowerCase();
      var queryTokens = rawQuery ? rawQuery.split(/\s+/).filter(Boolean) : [];
      var expandedSyns = rawQuery ? expandSynonyms(queryTokens) : [];
      var visibleCount = 0;
      var matches = [];

      toolCatalog.forEach(function(item) {
        var card = item.card;
        var cardCat = item.cat;

        // Category filter
        var matchesCat = (rawQuery.length > 0) ? true : (
          (activeCategory === 'all') || 
          cardCat.indexOf(activeCategory) !== -1 || 
          (activeCategory === 'health' && (cardCat.indexOf('health') !== -1 || cardCat.indexOf('everyday') !== -1)) || 
          (activeCategory === 'currency' && (cardCat.indexOf('currency') !== -1 || cardCat.indexOf('forex') !== -1))
        );

        var matchScore = 0;
        if (!rawQuery) {
          matchScore = 1;
        } else {
          matchScore = scoreTool(item, queryTokens, expandedSyns);
        }

        var isVisible = matchesCat && (matchScore > 0);
        if (isVisible) {
          card.style.display = '';
          visibleCount++;
          if (rawQuery) {
            matches.push({ item: item, score: matchScore });
          }
        } else {
          card.style.display = 'none';
        }
      });

      if (rawQuery) {
        matches.sort(function(a, b) { return b.score - a.score; });
        var sortedItems = matches.map(function(m) { return m.item; });
        renderDropdown(sortedItems);
      } else {
        renderDropdown([]);
      }

      if (countEl) {
        if (visibleCount < cards.length) {
          countEl.innerHTML = 'Showing ' + visibleCount + ' of ' + cards.length + ' tools <button id="cwResetFilterBtn" type="button" style="margin-left:8px;background:var(--brand-primary);color:#ffffff;border:none;padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:4px;box-shadow:0 2px 6px rgba(37,99,235,0.3);">Show All ' + cards.length + ' Tools ↺</button>';
          var rBtn = document.getElementById('cwResetFilterBtn');
          if (rBtn) {
            rBtn.onclick = function(e) {
              e.preventDefault();
              if (searchInput) searchInput.value = '';
              searchQuery = '';
              activeCategory = 'all';
              filterBtns.forEach(function(b) {
                if ((b.getAttribute('data-category') || '').toLowerCase() === 'all') {
                  b.classList.add('active');
                } else {
                  b.classList.remove('active');
                }
              });
              updateFilter();
            };
          }
        } else {
          countEl.textContent = 'Showing all ' + cards.length + ' precision calculators';
        }
      }

      var noResults = document.getElementById('noSearchResultsMsg');
      if (visibleCount === 0) {
        if (!noResults && toolsGrid) {
          noResults = document.createElement('div');
          noResults.id = 'noSearchResultsMsg';
          noResults.style.cssText = 'grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: var(--bg-card); border: 1px dashed var(--border); border-radius: 16px; margin: 24px 0;';
          noResults.innerHTML = '<div style="font-size: 2rem; margin-bottom: 8px;">🔍</div><div style="font-weight: 700; font-size: 1.1rem; color: var(--text-main); margin-bottom: 6px;">No calculators found</div><div style="font-size: 0.88rem; color: var(--text-muted); max-width: 440px; margin: 0 auto 16px;">Try adjusting your search terms, check the spelling, or browse all ' + cards.length + ' tools by category above.</div><button id="cwClearSearchFilterBtn" type="button" style="background: var(--brand-primary); color: #ffffff; border: none; padding: 8px 18px; border-radius: 8px; font-weight: 600; font-size: 0.88rem; cursor: pointer;">Clear Search & Show All Tools</button>';
          toolsGrid.appendChild(noResults);
          document.getElementById('cwClearSearchFilterBtn').onclick = function() {
            if (searchInput) searchInput.value = '';
            searchQuery = '';
            activeCategory = 'all';
            filterBtns.forEach(function(b) {
              if ((b.getAttribute('data-category') || '').toLowerCase() === 'all') b.classList.add('active');
              else b.classList.remove('active');
            });
            updateFilter();
          };
        } else if (noResults) {
          noResults.style.display = 'block';
        }
      } else if (noResults) {
        noResults.style.display = 'none';
      }
    }

    if (searchInput) {
      searchInput.addEventListener('input', function(e) {
        searchQuery = e.target.value;
        updateFilter();
      });

      searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          var items = dropdown ? dropdown.querySelectorAll('.search-dropdown-item') : [];
          if (!items.length) return;
          var curIdx = -1;
          items.forEach(function(el, i) {
            if (el.classList.contains('selected')) curIdx = i;
            el.classList.remove('selected');
          });
          var nextIdx = (curIdx + 1) % items.length;
          items[nextIdx].classList.add('selected');
          items[nextIdx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'ArrowUp') {
          e.preventDefault();
          var items = dropdown ? dropdown.querySelectorAll('.search-dropdown-item') : [];
          if (!items.length) return;
          var curIdx = 0;
          items.forEach(function(el, i) {
            if (el.classList.contains('selected')) curIdx = i;
            el.classList.remove('selected');
          });
          var prevIdx = (curIdx - 1 + items.length) % items.length;
          items[prevIdx].classList.add('selected');
          items[prevIdx].scrollIntoView({ block: 'nearest' });
        } else if (e.key === 'Enter') {
          var sel = dropdown ? dropdown.querySelector('.search-dropdown-item.selected') : null;
          var firstLink = sel || (dropdown ? dropdown.querySelector('.search-dropdown-item') : null);
          if (firstLink) {
            e.preventDefault();
            firstLink.click();
          }
        }
      });

      document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && (!dropdown || !dropdown.contains(e.target))) {
          if (dropdown) dropdown.style.display = 'none';
        }
      });

      searchInput.addEventListener('focus', function() {
        if (searchQuery) updateFilter();
      });
    }

    filterBtns.forEach(function(btn) {
      btn.addEventListener('click', function() {
        filterBtns.forEach(function(b) { b.classList.remove('active'); });
        btn.classList.add('active');
        activeCategory = (btn.getAttribute('data-category') || 'all').toLowerCase();
        updateFilter();
      });
    });

    document.addEventListener('keydown', function(e) {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        if (searchInput) {
          e.preventDefault();
          searchInput.focus();
          searchInput.select();
        }
      } else if (e.key === 'Escape' && document.activeElement === searchInput) {
        searchInput.value = '';
        searchQuery = '';
        updateFilter();
        if (dropdown) dropdown.style.display = 'none';
        searchInput.blur();
      }
    });

    function updateCategoryPillCounts() {
      filterBtns.forEach(function(btn) {
        var cat = (btn.getAttribute('data-category') || 'all').toLowerCase();
        var countBadge = btn.querySelector('.cat-filter-count');
        if (!countBadge) return;
        if (cat === 'all') {
          countBadge.textContent = cards.length;
        } else {
          var count = 0;
          cards.forEach(function(card) {
            var ccat = (card.getAttribute('data-category') || '').toLowerCase();
            if (ccat.indexOf(cat) !== -1 || 
                (cat === 'health' && (ccat.indexOf('health') !== -1 || ccat.indexOf('everyday') !== -1)) || 
                (cat === 'currency' && (ccat.indexOf('currency') !== -1 || ccat.indexOf('forex') !== -1))) {
              count++;
            }
          });
          countBadge.textContent = count;
        }
      });
    }

    updateCategoryPillCounts();
    // Guarantee all cards are visible on initial load
    updateFilter();
  }



  // ========================================================
  // Universal GDPR / AdSense Cookie & Privacy Consent Banner
  // ========================================================
  function initCookieConsent() {
    try {
      if (localStorage.getItem('calcworker_cookie_consent')) return;
      if (document.getElementById('calcworker-cookie-banner')) return;

      var banner = document.createElement('div');
      banner.id = 'calcworker-cookie-banner';
      banner.innerHTML = [
        '<div style="position:fixed;bottom:20px;right:20px;max-width:440px;background:#0f172a;border:1px solid rgba(59,130,246,0.35);border-radius:14px;padding:20px;box-shadow:0 16px 40px rgba(0,0,0,0.7);z-index:999999;font-family:system-ui,-apple-system,sans-serif;color:#e2e8f0;font-size:13.5px;line-height:1.55;animation:cwFadeUp 0.3s ease-out;">',
          '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">',
            '<div style="font-weight:700;font-size:15px;color:#f8fafc;display:flex;align-items:center;gap:8px;">',
              '<span>🍪</span> Cookie &amp; Privacy Preferences',
            '</div>',
            '<button id="cw-cookie-close" aria-label="Close" style="background:none;border:none;color:#94a3b8;font-size:18px;cursor:pointer;line-height:1;padding:2px 6px;border-radius:4px;">✕</button>',
          '</div>',
          '<p style="margin:0 0 16px 0;color:#cbd5e1;font-size:13px;">',
            'CalcWorker executes all 100+ financial calculators directly inside your browser memory with <strong>zero server-side telemetry</strong>. We use local storage and standard third-party advertising/analytics cookies (such as Google AdSense &amp; Google Analytics) to fund free financial infrastructure, adhering strictly to GDPR, CCPA, and Google AdSense publisher policies. Learn more in our <a href="/privacy.html" style="color:#60a5fa;text-decoration:underline;">Privacy Policy</a>.',
          '</p>',
          '<div style="display:flex;gap:10px;justify-content:flex-end;">',
            '<button id="cw-cookie-essential" style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);color:#cbd5e1;padding:8px 14px;border-radius:8px;font-size:12.5px;font-weight:600;cursor:pointer;transition:all 0.2s;">Essential Only</button>',
            '<button id="cw-cookie-accept" style="background:linear-gradient(135deg,#2563eb,#1d4ed8);border:none;color:#ffffff;padding:8px 16px;border-radius:8px;font-size:12.5px;font-weight:700;cursor:pointer;box-shadow:0 4px 12px rgba(37,99,235,0.35);transition:all 0.2s;">Accept All Cookies</button>',
          '</div>',
        '</div>'
      ].join('');

      document.body.appendChild(banner);

      function closeBanner(type) {
        try {
          localStorage.setItem('calcworker_cookie_consent', type);
        } catch(e) {}
        if (banner && banner.parentNode) {
          banner.parentNode.removeChild(banner);
        }
      }

      document.getElementById('cw-cookie-accept').onclick = function() { closeBanner('accepted'); };
      document.getElementById('cw-cookie-essential').onclick = function() { closeBanner('essential'); };
      document.getElementById('cw-cookie-close').onclick = function() { closeBanner('dismissed'); };
    } catch(e) {}
  }

    // Hook into initialization
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      applyPWAOfflineSuite();
      initSpotlightCards();
      initToolSearchAndFilters();
      initCookieConsent();
    });
  } else {
    applyPWAOfflineSuite();
    initSpotlightCards();
    initToolSearchAndFilters();
    initCookieConsent();
  }

})();
