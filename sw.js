/* CalcWorker — High Performance PWA Service Worker */
const CACHE_NAME = 'calcworker-v4-cache-20260924';
const PRECACHE_URLS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/css/calcworker.css',
  '/js/calcworker-common.js',
  '/js/ai-widget.js',
  '/assets/favicon.png',
  '/assets/icon-192.png',
  '/assets/icon-512.png',
  '/assets/logo.png'
];

// Install: precache app shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch((err) => {
        console.warn('[SW] Precache soft-fail:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Activate: clean up old caches, take control immediately, and force any
// stale open page to reload exactly once.
//
// Why the forced reload: a returning visitor can be stuck on HTML/JS cached
// by a previous worker version. That old page has no update listener, so the
// page-level "reload on controllerchange" trick never fires for it — the
// visitor keeps seeing the old design until they click somewhere. After
// claim(), we navigate every controlled window client once; the navigation
// goes through THIS worker (network-first), so the page comes back fresh.
// This runs only when a previous calcworker cache existed (i.e. a real
// update, not a first-time install), so first-time visitors never see a
// double load, and it can never loop: the reloaded page finds this worker
// already active, so activate never runs again for it.
self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      var keys = [];
      try { keys = await caches.keys(); } catch (e) { keys = []; }
      var hadOldVersion = keys.some(function (k) {
        return k !== CACHE_NAME && k.indexOf('calcworker-') === 0;
      });
      try {
        await Promise.all(
          keys.filter(function (k) { return k !== CACHE_NAME; }).map(function (k) { return caches.delete(k); })
        );
      } catch (e) {}
      try { await self.clients.claim(); } catch (e) {}
      if (hadOldVersion) {
        var clients = [];
        try { clients = await self.clients.matchAll({ type: 'window' }); } catch (e) { clients = []; }
        await Promise.all(clients.map(function (client) {
          try {
            var p = client.navigate(client.url);
            return p && p.catch ? p.catch(function () {}) : Promise.resolve();
          } catch (e) { return Promise.resolve(); }
        }));
      }
    })()
  );
});

// Fetch: Network-first for pages, JS and CSS (never run stale code against
// fresh HTML); Stale-While-Revalidate for images/fonts; cache fallback keeps
// offline working.
self.addEventListener('fetch', (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // Do not intercept non-GET requests
  if (req.method !== 'GET') return;

  // Do not cache or intercept third-party ads, analytics, or external APIs
  if (
    url.hostname.includes('google') ||
    url.hostname.includes('doubleclick') ||
    url.hostname.includes('googlesyndication') ||
    url.hostname.includes('clarity.ms') ||
    url.hostname.includes('x.ai') ||
    url.pathname.endsWith('.php')
  ) {
    return;
  }

  // Network-first for navigation (HTML pages), fallback to cache
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return networkResponse;
        })
        .catch(() => caches.match(req).then((cached) => cached || caches.match('/index.html')))
    );
    return;
  }

  // Network-first for local JS/CSS: guarantees the page never executes a
  // stale cached bundle against fresh HTML (the cause of dead click handlers
  // after a deploy). Cache fallback keeps the site working offline.
  if (url.origin === self.location.origin &&
      (url.pathname.endsWith('.js') || url.pathname.endsWith('.css'))) {
    event.respondWith(
      fetch(req)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return networkResponse;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // Stale-While-Revalidate for other local static assets (images, fonts)
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(req).then((cachedResponse) => {
        const fetchPromise = fetch(req).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, clone));
          }
          return networkResponse;
        }).catch(() => {/* Ignore fetch error in background */});

        return cachedResponse || fetchPromise;
      })
    );
  }
});
