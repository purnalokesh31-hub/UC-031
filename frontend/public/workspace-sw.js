/* Offline shell for previously visited screens; never cache API or scan responses. */
const CACHE = "cropguard-shell-v1";
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(["/", "/index.html"])));
  self.skipWaiting();
});
self.addEventListener("activate", event => event.waitUntil(
  caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith("cropguard-shell-") && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())
));
self.addEventListener("message", event => {
  if (event.data?.type !== "CACHE_VISITED_ASSETS" || !Array.isArray(event.data.urls)) return;
  event.waitUntil(caches.open(CACHE).then(cache => Promise.allSettled(event.data.urls.slice(0, 200).filter(name => {
    try { const url = new URL(name); return url.origin === self.location.origin && /^\/(src\/|assets\/|node_modules\/\.vite\/|@vite\/|@react-refresh)/.test(url.pathname); }
    catch { return false; }
  }).map(url => cache.add(url)))));
});
self.addEventListener("fetch", event => {
  const req = event.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api") || !["document", "script", "style", "font"].includes(req.destination)) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(req);
      if (response.ok) await cache.put(req, response.clone());
      return response;
    } catch {
      const cached = await cache.match(req);
      if (cached) return cached;
      if (req.mode === "navigate") return (await cache.match("/index.html")) || Response.error();
      return Response.error();
    }
  })());
});
