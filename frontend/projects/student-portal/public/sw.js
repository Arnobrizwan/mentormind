/* MentorMind student portal — lightweight offline shell.
 * Caches static assets on first load and mirrors GET /api/v1/courses/ +
 * /api/v1/enrollments/ for offline catalog (pairs with localStorage cache). */

const SHELL = 'mm-shell-v1';
const API = 'mm-api-v1';

const API_PREFIXES = ['/api/v1/courses/', '/api/v1/enrollments/'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL).then((cache) => cache.add('/index.html').catch(() => undefined)),
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== SHELL && k !== API).map((k) => caches.delete(k))),
    ),
  );
  self.clients.claim();
});

function isApiCacheable(url) {
  return API_PREFIXES.some((p) => url.pathname.startsWith(p));
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Static assets — cache-first (populated as users browse).
  if (url.origin === self.location.origin && /\.(js|css|woff2?|png|svg|ico)$/i.test(url.pathname)) {
    event.respondWith(
      caches.open(SHELL).then(async (cache) => {
        const cached = await cache.match(request);
        if (cached) return cached;
        const fresh = await fetch(request);
        if (fresh.ok) cache.put(request, fresh.clone());
        return fresh;
      }),
    );
    return;
  }

  // Course catalog + enrollments — network-first, cache fallback.
  if (isApiCacheable(url)) {
    event.respondWith(
      caches.open(API).then(async (cache) => {
        try {
          const fresh = await fetch(request);
          if (fresh.ok) cache.put(request, fresh.clone());
          return fresh;
        } catch {
          const cached = await cache.match(request);
          if (cached) return cached;
          throw new Error('offline');
        }
      }),
    );
    return;
  }

  // SPA navigation — network-first, index.html fallback.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() => caches.open(SHELL).then((c) => c.match('/index.html'))),
    );
  }
});

/* --- Web Push: study reminders ------------------------------------------ */

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { title: 'MentorMind', body: event.data ? event.data.text() : '' };
  }
  const title = data.title || 'MentorMind';
  event.waitUntil(
    self.registration.showNotification(title, {
      body: data.body || '',
      icon: '/favicon.ico',
      badge: '/favicon.ico',
      tag: data.tag || 'mentormind',
      data: { url: data.url || '/' },
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      // Focus an existing tab and route it, else open a new one.
      for (const client of clients) {
        if ('focus' in client) {
          client.focus();
          if ('navigate' in client) client.navigate(target).catch(() => undefined);
          return undefined;
        }
      }
      return self.clients.openWindow(target);
    }),
  );
});
