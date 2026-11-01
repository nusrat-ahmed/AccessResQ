/* Offline shell only; NEVER cache personal data, documents, SOS or any /api response. */
const CACHE = 'accessresq-shell-v1.1.0';
const SHELL = ['/', '/static/styles.css','/static/rescue.css','/static/app.js','/static/rescue.js','/static/icon.svg','/static/manifest.webmanifest'];
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(SHELL)).then(()=>self.skipWaiting())));
self.addEventListener('activate', event => event.waitUntil(Promise.all([caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k)))),self.clients.claim()])));
self.addEventListener('fetch', event => {
  const req = event.request, url = new URL(req.url);
  if(req.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/uploads/')) return;
  if(req.mode === 'navigate') {
    event.respondWith(fetch(req).catch(()=>caches.match('/')));return;
  }
  if(SHELL.includes(url.pathname)) event.respondWith(caches.match(req).then(cached=>cached||fetch(req)));
});
