// Guarda a casca do app (HTML, JS, CSS, ícones) para abrir sem internet. O vite.config.ts troca
// os marcadores abaixo pela lista de arquivos do build; a versão muda a cada build, e o cache
// antigo sai na ativação. A API (/api) nunca passa por aqui.
const VERSAO = "__VERSAO__";
const CASCA = __CASCA__;
const CACHE = `casca-${VERSAO}`;
// O servidor pode responder `Vary: Origin`; os arquivos da casca não mudam com isso.
const SEM_VARY = { ignoreVary: true };

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(CASCA))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (evento) => {
  const { request } = evento;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return;

  if (request.mode === "navigate") {
    // Rede primeiro, para pegar a versão nova; sem rede, a casca guardada.
    evento.respondWith(fetch(request).catch(() => caches.match("/index.html", SEM_VARY)));
    return;
  }
  evento.respondWith(caches.match(request, SEM_VARY).then((guardado) => guardado ?? fetch(request)));
});
