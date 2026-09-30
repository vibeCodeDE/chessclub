/* Schachvereins-Software – Interaktionen der öffentlichen Seiten
   Progressive Enhancement: alle Seiten funktionieren auch ohne JavaScript.
   Enthält nur, was der öffentliche Auftritt braucht: Hauptnavigation (mobil),
   Ladezustand beim Seitenwechsel, Toasts und die Service-Worker-Registrierung.
   Der interne Bereich lädt static/js/app.js – beide Dateien sind unabhängig. */
(function () {
  "use strict";

  const Public = (window.Public = {});
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  /* ---------------------------------------------------------------- Toasts */
  function dismiss(el) {
    el.classList.add("is-leaving");
    window.setTimeout(() => el.remove(), 220);
  }

  function toast(message, type, timeout) {
    const stack = $("[data-toast-stack]");
    if (!stack || !message) return;
    const el = document.createElement("div");
    el.className = "toast " + (type || "info");
    const text = document.createElement("div");
    text.className = "grow";
    text.textContent = message;
    const close = document.createElement("button");
    close.className = "toast-close";
    close.type = "button";
    close.setAttribute("aria-label", "Meldung schließen");
    close.textContent = "✕";
    close.addEventListener("click", () => dismiss(el));
    el.append(text, close);
    stack.append(el);
    window.setTimeout(() => dismiss(el), timeout || (type === "error" ? 8000 : 5000));
  }

  Public.toast = toast;
  Public.success = (m) => toast(m, "success");
  Public.error = (m) => toast(m, "error");

  /* ------------------------------------------------------------ Ladezustand */
  function showLoading() {
    const bar = $("[data-loading-bar]");
    if (bar) bar.classList.add("is-active");
  }
  function hideLoading() {
    const bar = $("[data-loading-bar]");
    if (bar) bar.classList.remove("is-active");
  }
  Public.loading = { show: showLoading, hide: hideLoading };

  /* ------------------------------------------------------- Hauptnavigation */
  /* Mobil: Menü auf- und zuklappen; schließt per Escape und Klick daneben. */
  function initPublicNav() {
    const nav = $("[data-public-nav]");
    const toggle = $("[data-public-nav-toggle]");
    if (!nav || !toggle) return;
    const icon = $("use", toggle);
    const open = () => {
      nav.classList.add("is-open");
      toggle.setAttribute("aria-expanded", "true");
      toggle.setAttribute("aria-label", "Menü schließen");
      if (icon) icon.setAttribute("href", "#i-x");
    };
    const close = () => {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
      toggle.setAttribute("aria-label", "Menü öffnen");
      if (icon) icon.setAttribute("href", "#i-menu");
    };
    toggle.addEventListener("click", () => {
      nav.classList.contains("is-open") ? close() : open();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
    document.addEventListener("click", (event) => {
      if (!nav.classList.contains("is-open")) return;
      if (nav.contains(event.target) || toggle.contains(event.target)) return;
      close();
    });
  }

  /* ----------------------------------------------- Ladezustand bei Navigation */
  function initNavigationFeedback() {
    window.addEventListener("beforeunload", () => showLoading());
    document.addEventListener("submit", (event) => {
      const button = event.submitter || $("button[type=submit]", event.target);
      if (button) {
        button.classList.add("is-loading");
        button.disabled = true;
      }
      showLoading();
    });
    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link) return;
      if (link.target === "_blank" || link.hasAttribute("download")) return;
      const href = link.getAttribute("href");
      if (!href || href.startsWith("#")) return;
      if (link.hasAttribute("data-no-loading")) return;  /* z. B. mailto-Links */
      if (link.host !== window.location.host) return;
      showLoading();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initPublicNav();
    initNavigationFeedback();
  });
})();


/* ---- PWA: Service Worker registrieren (PRD N2.7) ---- */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      /* Offline-Funktion ist optional – Fehler nicht in die Konsole der Vorstandschaft werfen */
    });
  });
}
