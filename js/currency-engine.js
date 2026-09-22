/* CalcWorker Currency Engine — window.cwCurrency
 *
 * Powers currency-converter.html and the usd-to-*.html pages.
 * - Baseline rates are clearly labeled "Cached Baseline Rate" in the UI.
 * - fetchLiveRates() upgrades to a live feed (open.er-api.com, no key)
 *   and the UI badge flips to "Live Market Feed".
 */
(function () {
  'use strict';

  // Baseline rates vs USD (clearly labeled as cached/baseline in the UI;
  // refreshed automatically when the live feed is reachable).
  var BASELINE_RATES = {
    USD: 1, EUR: 0.86, GBP: 0.75, JPY: 151, CAD: 1.39, AUD: 1.53, CHF: 0.80,
    CNY: 7.13, INR: 88.7, MXN: 18.7, PKR: 284, KRW: 1390, SGD: 1.29,
    NZD: 1.69, SEK: 9.5, NOK: 10.1, DKK: 6.42, ZAR: 17.6, BRL: 5.4,
    AED: 3.6725, SAR: 3.75, QAR: 3.64, KWD: 0.31, BHD: 0.376, OMR: 0.3845,
    JOD: 0.709, ILS: 3.35, TRY: 41.5, RUB: 83, THB: 32.4, MYR: 4.21,
    IDR: 16400, PHP: 58.5, VND: 26400, HKD: 7.8, TWD: 30.5, PLN: 3.65,
    CZK: 21.1, HUF: 340, RON: 4.28, BGN: 1.68, ISK: 138, EGP: 48.5,
    NGN: 1530, KES: 129, GHS: 12.4, BDT: 121, LKR: 301, NPR: 140
  };

  var CURRENCIES = {
    USD: { symbol: '$', name: 'US Dollar' }, EUR: { symbol: '€', name: 'Euro' },
    GBP: { symbol: '£', name: 'British Pound' }, JPY: { symbol: '¥', name: 'Japanese Yen' },
    CAD: { symbol: 'CA$', name: 'Canadian Dollar' }, AUD: { symbol: 'A$', name: 'Australian Dollar' },
    CHF: { symbol: 'CHF', name: 'Swiss Franc' }, CNY: { symbol: '¥', name: 'Chinese Yuan' },
    INR: { symbol: '₹', name: 'Indian Rupee' }, MXN: { symbol: 'MX$', name: 'Mexican Peso' },
    PKR: { symbol: '₨', name: 'Pakistani Rupee' }, KRW: { symbol: '₩', name: 'South Korean Won' },
    SGD: { symbol: 'S$', name: 'Singapore Dollar' }, NZD: { symbol: 'NZ$', name: 'New Zealand Dollar' },
    SEK: { symbol: 'kr', name: 'Swedish Krona' }, NOK: { symbol: 'kr', name: 'Norwegian Krone' },
    DKK: { symbol: 'kr', name: 'Danish Krone' }, ZAR: { symbol: 'R', name: 'South African Rand' },
    BRL: { symbol: 'R$', name: 'Brazilian Real' }, AED: { symbol: 'د.إ', name: 'UAE Dirham' },
    SAR: { symbol: '﷼', name: 'Saudi Riyal' }, QAR: { symbol: 'QR', name: 'Qatari Riyal' },
    KWD: { symbol: 'KD', name: 'Kuwaiti Dinar' }, BHD: { symbol: 'BD', name: 'Bahraini Dinar' },
    OMR: { symbol: 'RO', name: 'Omani Rial' }, JOD: { symbol: 'JD', name: 'Jordanian Dinar' },
    ILS: { symbol: '₪', name: 'Israeli Shekel' }, TRY: { symbol: '₺', name: 'Turkish Lira' },
    RUB: { symbol: '₽', name: 'Russian Ruble' }, THB: { symbol: '฿', name: 'Thai Baht' },
    MYR: { symbol: 'RM', name: 'Malaysian Ringgit' }, IDR: { symbol: 'Rp', name: 'Indonesian Rupiah' },
    PHP: { symbol: '₱', name: 'Philippine Peso' }, VND: { symbol: '₫', name: 'Vietnamese Dong' },
    HKD: { symbol: 'HK$', name: 'Hong Kong Dollar' }, TWD: { symbol: 'NT$', name: 'Taiwan Dollar' },
    PLN: { symbol: 'zł', name: 'Polish Zloty' }, CZK: { symbol: 'Kč', name: 'Czech Koruna' },
    HUF: { symbol: 'Ft', name: 'Hungarian Forint' }, RON: { symbol: 'lei', name: 'Romanian Leu' },
    BGN: { symbol: 'лв', name: 'Bulgarian Lev' }, ISK: { symbol: 'kr', name: 'Icelandic Krona' },
    EGP: { symbol: 'E£', name: 'Egyptian Pound' }, NGN: { symbol: '₦', name: 'Nigerian Naira' },
    KES: { symbol: 'KSh', name: 'Kenyan Shilling' }, GHS: { symbol: '₵', name: 'Ghanaian Cedi' },
    BDT: { symbol: '৳', name: 'Bangladeshi Taka' }, LKR: { symbol: 'Rs', name: 'Sri Lankan Rupee' },
    NPR: { symbol: 'Rs', name: 'Nepalese Rupee' }
  };

  var rates = {};
  Object.keys(BASELINE_RATES).forEach(function (k) { rates[k] = BASELINE_RATES[k]; });
  var source = 'cached';
  var lastUpdated = null;

  function rate(from, to) {
    var rf = rates[from], rt = rates[to];
    if (!rf || !rt) return 0;
    return rt / rf;
  }

  function fmtMoney(x) {
    if (!isFinite(x)) return '—';
    var abs = Math.abs(x);
    var dec = abs >= 1000 ? 2 : abs >= 1 ? 2 : 4;
    return x.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  var cwCurrency = {
    currencies: CURRENCIES,

    convert: function (amt, from, to) {
      var r = rate(from, to);
      var toAmount = (parseFloat(amt) || 0) * r;
      var toMeta = CURRENCIES[to] || { symbol: '' };
      return {
        fromAmount: parseFloat(amt) || 0,
        toAmount: toAmount,
        rate: r,
        formattedTo: (toMeta.symbol ? toMeta.symbol + ' ' : '') + fmtMoney(toAmount),
        rateDisplay: '1 ' + from + ' = ' + this.formatRate(r) + ' ' + to,
        inverseRateDisplay: r > 0 ? '1 ' + to + ' = ' + this.formatRate(1 / r) + ' ' + from : '—',
        source: source
      };
    },

    formatRate: function (x) {
      if (!isFinite(x) || x <= 0) return '—';
      if (x >= 1000) return x.toLocaleString('en-US', { maximumFractionDigits: 2 });
      if (x >= 1) return String(Math.round(x * 10000) / 10000);
      return String(Math.round(x * 1000000) / 1000000);
    },

    getFormattedTimestamp: function () {
      if (lastUpdated) {
        try { return lastUpdated.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }); }
        catch (e) { return String(lastUpdated); }
      }
      return 'Baseline rates (Sep 2026)';
    },

    getQuickDenominations: function (from, to) {
      var amounts = [1, 5, 10, 20, 50, 100, 500, 1000];
      var r = rate(from, to), self = this;
      function row(a, rr) {
        var conv = a * rr;
        return { fromAmount: a, toAmount: conv, formattedFrom: fmtMoney(a), formattedTo: fmtMoney(conv) };
      }
      return {
        forward: amounts.map(function (a) { return row(a, r); }),
        reverse: amounts.map(function (a) { return row(a, r > 0 ? 1 / r : 0); })
      };
    },

    fetchLiveRates: function (force) {
      var self = this;
      return fetch('https://open.er-api.com/v6/latest/USD')
        .then(function (resp) {
          if (!resp.ok) throw new Error('rate feed unavailable');
          return resp.json();
        })
        .then(function (data) {
          if (data && data.result === 'success' && data.rates) {
            Object.keys(data.rates).forEach(function (k) {
              if (typeof data.rates[k] === 'number' && data.rates[k] > 0) rates[k] = data.rates[k];
            });
            if (data.time_last_update_utc) lastUpdated = new Date(data.time_last_update_utc);
            else lastUpdated = new Date();
            source = 'live';
          }
          return { source: source };
        })
        .catch(function () {
          source = 'cached';
          return { source: source };
        });
    }
  };

  window.cwCurrency = cwCurrency;
})();
