/* Service Worker: Offline-Anzeige der Startseite und letzten Seiten (PRD N2.7).
   Bewusst konservativ: Inhalte kommen zuerst aus dem Netz, damit Vorstandsdaten
   nie veralten; nur die Offline-Seite und statische Dateien liegen im Cache. */

const CACHE = "schachverein-v2";
const OFFLINE_URL = "/offline/";
const VORAB_CACHE = [
  OFFLINE_URL,
  "/static/css/app.css",   /* interner Bereich */
  "/static/css/site.css",  /* öffentliche Vereinsseite */
  "/static/js/app.js",     /* interner Bereich */
  "/static/js/public.js",  /* öffentliche Vereinsseite */
  "/static/icons/icon-192.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(VORAB_CACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((namen) => Promise.all(namen.filter((name) => name !== CACHE).map((name) => caches.delete(name))))
      .then(() => self.clients.claim())
  );
});

function istStatisch(url) {
  return url.pathname.startsWith("/static/");
}

self.addEventListener("fetch", (event) => {
  const anfrage = event.request;
  if (anfrage.method !== "GET") return;
  const url = new URL(anfrage.url);
  if (url.origin !== self.location.origin) return;

  if (istStatisch(url)) {
    // Statische Dateien: erst Cache, dann Netz (und Cache aktualisieren)
    event.respondWith(
      caches.match(anfrage).then((treffer) => {
        if (treffer) return treffer;
        return fetch(anfrage).then((antwort) => {
          const kopie = antwort.clone();
          caches.open(CACHE).then((cache) => cache.put(anfrage, kopie));
          return antwort;
        });
      })
    );
    return;
  }

  // Seiten: erst Netz, bei Offline die Offline-Seite bzw. letzte Kopie
  event.respondWith(
    fetch(anfrage)
      .then((antwort) => {
        if (anfrage.mode === "navigate" && antwort.ok) {
          const kopie = antwort.clone();
          caches.open(CACHE).then((cache) => cache.put(anfrage, kopie));
        }
        return antwort;
      })
      .catch(() =>
        caches.match(anfrage).then((treffer) => treffer || caches.match(OFFLINE_URL))
      )
  );
});
