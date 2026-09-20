/* ==========================================================================
   CalcWorker — Google Analytics GA4 + Page Tracking
   File: js/analytics.js
   Replace G-1QCQNSCVQM with your real GA4 Measurement ID from:
   https://analytics.google.com → Admin → Data Streams → Web
   ========================================================================== */

const CW_GA4_ID = 'G-1QCQNSCVQM';

(function () {
  'use strict';
  var script = document.createElement('script');
  script.async = true;
  script.src = 'https://www.googletagmanager.com/gtag/js?id=' + CW_GA4_ID;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', CW_GA4_ID, {
    page_title: document.title,
    page_location: window.location.href,
    send_page_view: true
  });

  window.cwTrack = function (eventName, params) {
    if (typeof window.gtag === 'function') {
      window.gtag('event', eventName, params || {});
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.tool-card').forEach(function (card) {
      card.addEventListener('click', function () {
        var title = card.querySelector('.tool-card-title');
        window.cwTrack('tool_click', { tool_name: title ? title.textContent.trim() : 'Unknown' });
      });
    });

    var themeBtn = document.getElementById('themeToggleBtn');
    if (themeBtn) {
      themeBtn.addEventListener('click', function () {
        var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        window.cwTrack('theme_toggle', { mode: isDark ? 'light' : 'dark' });
      });
    }

    document.querySelectorAll('.mode-pill').forEach(function (pill) {
      pill.addEventListener('click', function () {
        window.cwTrack('omnicalc_mode_switch', { mode: pill.dataset.mode || pill.textContent.trim() });
      });
    });

    var aiBtn = document.getElementById('aiSolveBtn');
    if (aiBtn) {
      aiBtn.addEventListener('click', function () {
        window.cwTrack('ai_smart_compute_used', {});
      });
    }

    document.querySelectorAll('button[id*="Btn"]').forEach(function(btn){
      btn.addEventListener('click', function(){
        window.cwTrack('calculator_used', { tool: window.location.pathname, btn: btn.id });
      });
    });
  });
})();

