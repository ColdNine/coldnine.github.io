---
layout: null
---
// Service worker for {{ site.title | default: "this site" }}.
// Bump CACHE_VERSION to force clients to drop old caches after a deploy.
const CACHE_VERSION = "v1";
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const PAGES_CACHE = `pages-${CACHE_VERSION}`;

const PRECACHE_URLS = [
  "{{ '/' | relative_url }}",
  "{{ '/offline.html' | relative_url }}",
  "{{ '/assets/css/main.css' | relative_url }}",
  "{{ '/manifest.webmanifest' | relative_url }}",
  "{{ '/assets/icons/icon-192.png' | relative_url }}",
  "{{ '/assets/icons/icon-512.png' | relative_url }}",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== PAGES_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET" || !request.url.startsWith(self.location.origin)) {
    return;
  }

  // Page navigations: network-first, falling back to cache, then the offline page.
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(PAGES_CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() =>
          caches
            .match(request)
            .then((cached) => cached || caches.match("{{ '/offline.html' | relative_url }}"))
        )
    );
    return;
  }

  // Static assets (CSS/JS/images/fonts): cache-first, updating the cache in the background.
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => cached);
      return cached || network;
    })
  );
});
