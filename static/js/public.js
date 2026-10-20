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
    window.addEventListener("pageshow", () => {
      hideLoading();
      $$("button.is-loading").forEach((btn) => {
        btn.classList.remove("is-loading");
        btn.disabled = false;
      });
      $$("form[data-submitting]").forEach((f) => {
        delete f.dataset.submitting;
      });
    });
    document.addEventListener("submit", (event) => {
      const form = event.target;
      if (form.dataset.submitting === "true") {
        event.preventDefault();
        return;
      }
      form.dataset.submitting = "true";
      const button = event.submitter || $("button[type=submit]", form);
      if (button) {
        button.classList.add("is-loading");
        button.disabled = true;
      }
      showLoading();
      window.setTimeout(() => {
        delete form.dataset.submitting;
        if (button) {
          button.classList.remove("is-loading");
          button.disabled = false;
        }
        hideLoading();
      }, 6000);
    });
    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link) return;
      if (link.target === "_blank" || link.hasAttribute("download")) return;
      const href = link.getAttribute("href");
      if (!href || href.startsWith("#")) return;
      if (link.hasAttribute("data-no-loading")) return;  /* z. B. mailto-Links */
      if (link.host !== window.location.host) return;
      if (link.pathname === window.location.pathname && link.search === window.location.search) return;
      showLoading();
    });
  }

  /* ------------------------------------------------ Formular-Barrierefreiheit */
  function initFormA11y() {
    $$(".form-field").forEach((field) => {
      const input = $("input, select, textarea", field);
      if (!input) return;
      const error = $("[role=alert]", field);
      const help = $(".help", field);
      const describedBy = [];
      if (error && error.id) {
        input.setAttribute("aria-invalid", "true");
        describedBy.push(error.id);
      }
      if (help && help.id) {
        describedBy.push(help.id);
      }
      if (describedBy.length > 0) {
        const existing = input.getAttribute("aria-describedby") || "";
        const combined = [existing, ...describedBy].filter(Boolean).join(" ");
        input.setAttribute("aria-describedby", combined);
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initPublicNav();
    initNavigationFeedback();
    initFormA11y();
  });
})();


/* ---- PWA: Service Worker Steuerung (PRD N2.7) ---- */
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    const pwaAktiv = document.documentElement.getAttribute("data-pwa-aktiv") === "1";
    if (pwaAktiv) {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
        /* Offline-Funktion ist optional – Fehler nicht in die Konsole der Vorstandschaft werfen */
      });
    } else {
      /* PWA temporär deaktiviert: Service Worker deregistrieren und Caches leeren */
      navigator.serviceWorker.getRegistrations().then((registrations) => {
        for (const registration of registrations) {
          registration.unregister();
        }
      });
      if ("caches" in window) {
        caches.keys().then((names) => {
          names.forEach((name) => caches.delete(name));
        });
      }
    }
  });
}
