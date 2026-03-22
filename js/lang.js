/**
 * Crypto3D Language System
 * Single source of truth for language toggle across all pages.
 * Works alongside theme.js — button sits next to theme toggle in header.
 */
(function() {
  var STORAGE_KEY = 'lang';
  var currentLang = localStorage.getItem(STORAGE_KEY) || 'zh';

  function applyLang(lang) {
    currentLang = lang;
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    localStorage.setItem(STORAGE_KEY, lang);

    // Update global toggle button text
    var btn = document.getElementById('lang-toggle');
    if (btn) btn.textContent = lang === 'zh' ? 'EN' : '中';

    // Update data-zh/data-en elements
    document.querySelectorAll('[data-zh]').forEach(function(el) {
      var val = el.getAttribute('data-' + lang);
      if (val) el.textContent = val;
    });

    // Update LangUtils.currentLang for compat
    if (window.LangUtils) window.LangUtils.currentLang = lang;

    // Dispatch event for page-specific i18n handlers
    window.dispatchEvent(new CustomEvent('langchange', { detail: { lang: lang } }));
  }

  function toggleLang() {
    applyLang(currentLang === 'zh' ? 'en' : 'zh');
  }

  function getLang() {
    return currentLang;
  }

  // Remove any page-level lang switchers
  function removeLocalSwitchers() {
    document.querySelectorAll('.lang-switch, .lang-switch-tev').forEach(function(el) {
      el.style.display = 'none';
    });
  }

  // Inject global toggle button into header
  function injectButton() {
    // Find the slot: next to theme toggle
    var themeBtn = document.querySelector('.theme-toggle-btn, #tt, [data-theme-toggle]');
    if (!themeBtn) return;

    var btn = document.createElement('button');
    btn.id = 'lang-toggle';
    btn.className = 'lang-toggle-btn';
    btn.textContent = currentLang === 'zh' ? 'EN' : '中';
    btn.setAttribute('aria-label', 'Toggle language');
    btn.addEventListener('click', toggleLang);

    // Insert before theme button
    themeBtn.parentNode.insertBefore(btn, themeBtn);
  }

  // Expose globally for page scripts that need current lang
  window.CryptoLang = {
    get: getLang,
    set: applyLang,
    toggle: toggleLang
  };

  // Also keep LangUtils compatible for indicator pages (data-zh / data-en pattern)
  function updateDataAttrs() {
    document.querySelectorAll('[data-zh]').forEach(function(el) {
      var val = el.getAttribute('data-' + currentLang);
      if (val) el.textContent = val;
    });
  }

  window.LangUtils = {
    currentLang: currentLang,
    get: getLang,
    init: function() {
      removeLocalSwitchers();
      updateDataAttrs();
    },
    toggle: function() {
      toggleLang();
      updateDataAttrs();
    },
    update: function() {
      updateDataAttrs();
    }
  };

  // Init on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      removeLocalSwitchers();
      injectButton();
      applyLang(currentLang);
    });
  } else {
    removeLocalSwitchers();
    injectButton();
    applyLang(currentLang);
  }
})();
