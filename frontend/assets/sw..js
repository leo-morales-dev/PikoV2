const CACHE_NAME = "piko-cache-v1";
const urlsToCache = ["./", "./index.html", "./manifest.json"];

// 1. Instalar: Guardamos lo básico
self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("Abriendo caché");
      return cache.addAll(urlsToCache);
    })
  );
});

// 2. Activar: Limpiamos cachés viejos
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// 3. Interceptar: Si no hay internet, sirve lo guardado
self.addEventListener("fetch", (event) => {
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});