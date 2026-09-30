/* Schachvereins-Software – Interaktionen des internen Bereichs (Dashboard/Verwaltung)
   Progressive Enhancement: ohne JavaScript funktionieren alle Formulare normal.
   Enthält: Sidebar/Drawer, Dropdowns, Toasts, optimistische Updates,
   Autosave, Bestätigungsdialog, Ladezustände.
   Die öffentlichen Seiten laden static/js/public.js – beide Dateien sind unabhängig. */
(function () {
  "use strict";

  const App = (window.App = {});

  /* ------------------------------------------------------------- Utilities */
  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

  function csrfToken() {
    const input = $("input[name=csrfmiddlewaretoken]");
    if (input) return input.value;
    const match = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[2]) : "";
  }

  async function post(url, data, options) {
    const opts = options || {};
    const body = data instanceof FormData ? data : new FormData();
    if (!(data instanceof FormData) && data) {
      Object.entries(data).forEach(([key, value]) => body.append(key, value));
    }
    if (!body.has("csrfmiddlewaretoken")) body.append("csrfmiddlewaretoken", csrfToken());
    const response = await fetch(url, {
      method: "POST",
      body: body,
      headers: {
        "X-Requested-With": "fetch",
        Accept: "application/json",
        "X-CSRFToken": csrfToken(),
      },
      credentials: "same-origin",
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = { ok: false, message: "Unerwartete Antwort des Servers." };
    }
    if (!response.ok && payload && payload.ok === undefined) payload.ok = false;
    return { ok: response.ok, payload: payload, response: response };
  }
  App.post = post;

  /* ---------------------------------------------------------------- Toasts */
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
  function dismiss(el) {
    el.classList.add("is-leaving");
    window.setTimeout(() => el.remove(), 220);
  }
  App.toast = toast;
  App.success = (m) => toast(m, "success");
  App.error = (m) => toast(m, "error");

  /* --------------------------------------------------- Server-Meldungen → UI */
  function adoptFlashMessages() {
    const block = $("[data-flash-messages]");
    if (!block) return;
    $$(".alert", block).forEach((alert) => {
      let type = "info";
      if (alert.classList.contains("alert-success")) type = "success";
      else if (alert.classList.contains("alert-error") || alert.classList.contains("alert-danger")) type = "error";
      else if (alert.classList.contains("alert-warning")) type = "warning";
      toast(alert.textContent.trim(), type);
    });
    block.remove();
  }

  /* ------------------------------------------------------------ Ladezustand */
  function showLoading() {
    const bar = $("[data-loading-bar]");
    if (bar) bar.classList.add("is-active");
  }
  function hideLoading() {
    const bar = $("[data-loading-bar]");
    if (bar) bar.classList.remove("is-active");
  }
  App.loading = { show: showLoading, hide: hideLoading };

  function withButtonLoading(button, on) {
    if (!button) return;
    if (on) {
      button.classList.add("is-loading");
      button.dataset.wasDisabled = button.disabled ? "1" : "";
      button.disabled = true;
    } else {
      button.classList.remove("is-loading");
      button.disabled = false;
    }
  }

  /* --------------------------------------------------------------- Sidebar */
  function initSidebar() {
    const sidebar = $("#sidebar");
    if (!sidebar) return;
    const backdrop = $("[data-sidebar-close]");
    const open = () => {
      sidebar.classList.add("is-open");
      if (backdrop) backdrop.hidden = false;
      if (backdrop) backdrop.classList.add("is-open");
    };
    const close = () => {
      sidebar.classList.remove("is-open");
      if (backdrop) backdrop.classList.remove("is-open");
      window.setTimeout(() => {
        if (backdrop && !backdrop.classList.contains("is-open")) backdrop.hidden = true;
      }, 200);
    };
    $$("[data-sidebar-toggle]").forEach((btn) => btn.addEventListener("click", () => {
      sidebar.classList.contains("is-open") ? close() : open();
    }));
    if (backdrop) backdrop.addEventListener("click", close);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
  }

  /* -------------------------------------------------------------- Dropdowns */
  function initDropdowns() {
    $$("[data-dropdown-toggle]").forEach((toggle) => {
      const panel = toggle.parentElement.querySelector("[data-dropdown-panel]");
      if (!panel) return;
      toggle.addEventListener("click", (event) => {
        event.stopPropagation();
        const isOpen = panel.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      });
    });
    document.addEventListener("click", () => {
      $$("[data-dropdown-panel].is-open").forEach((panel) => panel.classList.remove("is-open"));
    });
  }

  /* --------------------------------------------------------- Bestätigungen */
  function initConfirm() {
    const backdrop = $("[data-modal-backdrop]");
    if (!backdrop) return;
    const titleEl = $("[data-modal-title]", backdrop);
    const bodyEl = $("[data-modal-body]", backdrop);
    const confirmBtn = $("[data-modal-confirm]", backdrop);
    let pending = null;

    function close() {
      backdrop.classList.remove("is-open");
      pending = null;
    }
    $$("[data-modal-close]", backdrop).forEach((btn) => btn.addEventListener("click", close));
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) close();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && backdrop.classList.contains("is-open")) close();
    });
    confirmBtn.addEventListener("click", () => {
      if (!pending) return;
      const { form, button, label } = pending;
      if (button) pending.resolved = true;
      close();
      if (button) {
        button.dataset.confirmed = "1";
        submitOptimistic(button, form, label);
      } else if (form) {
        form.dataset.confirmed = "1";
        form.requestSubmit ? form.requestSubmit() : form.submit();
      }
    });

    document.addEventListener("click", (event) => {
      const trigger = event.target.closest("[data-confirm]");
      if (!trigger || trigger.dataset.confirmed === "1") return;
      const form = trigger.closest("form");
      event.preventDefault();
      event.stopPropagation();
      pending = {
        form: form,
        button: trigger.tagName === "BUTTON" && form && trigger.type === "submit" ? trigger : null,
        label: trigger.dataset.confirm,
      };
      titleEl.textContent = trigger.dataset.confirmTitle || "Aktion bestätigen";
      bodyEl.textContent = trigger.dataset.confirm || "Möchten Sie fortfahren?";
      confirmBtn.textContent = trigger.dataset.confirmButton || "Bestätigen";
      confirmBtn.className = "btn " + (trigger.dataset.confirmStyle || "danger");
      backdrop.classList.add("is-open");
    }, true);
  }

  /* ----------------------------------------------------- Optimistische Aktionen */

  function applyPatch(payload) {
    if (payload.patch) {
      Object.entries(payload.patch).forEach(([sel, value]) => {
        $$(sel).forEach((el) => {
          el.textContent = value;
        });
      });
    }
    if (payload.html) {
      Object.entries(payload.html).forEach(([sel, markup]) => {
        $$(sel).forEach((el) => {
          el.innerHTML = markup;
        });
      });
    }
    if (payload.classes) {
      Object.entries(payload.classes).forEach(([sel, changes]) => {
        $$(sel).forEach((el) => {
          (changes.add || []).forEach((c) => el.classList.add(c));
          (changes.remove || []).forEach((c) => el.classList.remove(c));
        });
      });
    }
  }

  async function submitOptimistic(button, form, label, silentForm) {
    const url = button.dataset.url || form.action || window.location.href;
    const mode = button.dataset.mode || form.dataset.mode || "form";
    const data = new FormData(mode === "url" ? undefined : form);
    if (button.name) data.append(button.name, button.value);

    const row = button.closest("[data-row]");
    const revert = [];

    // 1) Sofortige UI-Reaktion (optimistisch)
    if (button.dataset.optimistic === "hide-row" && row) {
      row.style.display = "none";
      revert.push(() => (row.style.display = ""));
    }
    if (button.dataset.optimistic === "remove-row" && row) {
      const placeholder = document.createComment("entfernt");
      row.parentNode.insertBefore(placeholder, row);
      row.remove();
      revert.push(() => placeholder.parentNode.replaceChild(row, placeholder));
    }
    if (button.dataset.optimistic === "flip" && button.dataset.flipTarget) {
      const target = $(button.dataset.flipTarget);
      if (target) {
        target.classList.toggle("is-on");
      }
    }
    if (button.dataset.optimisticText) {
      const labelEl = button.closest("[data-row]") || button;
      labelEl.dataset.optimisticBackup = labelEl.innerHTML;
      button.dataset.optimisticBackupHtml = button.innerHTML;
      button.innerHTML = button.dataset.optimisticText;
    }

    withButtonLoading(button, true);
    showLoading();
    let result;
    try {
      result = await post(url, data);
    } catch (error) {
      result = { ok: false, payload: { message: "Netzwerkfehler – bitte erneut versuchen." } };
    }
    hideLoading();
    withButtonLoading(button, false);

    const payload = result.payload || {};
    if (result.ok && payload.ok !== false) {
      applyPatch(payload);
      if (payload.message) toast(payload.message, "success");
      if (payload.reload) window.location.reload();
      if (payload.redirect) window.location.href = payload.redirect;
      if (button.dataset.ajaxReset !== undefined || (form && form.dataset.ajaxReset !== undefined)) {
        if (form) form.reset();
      }
      if (button.dataset.removeAfter || (form && form.dataset.removeAfter)) {
        const host = button.closest("[data-modal-host]") || document.body;
        void host;
      }
      if (payload.remove_selector) {
        const el = $(payload.remove_selector);
        if (el) el.remove();
      }
      return true;
    }

    // 2) Rollback bei Fehlern
    revert.forEach((fn) => fn());
    if (button.dataset.optimisticBackupHtml) button.innerHTML = button.dataset.optimisticBackupHtml;
    button.dataset.confirmed = "";
    const message = payload.message || Object.values(payload.errors || {}).flat().join(" ") || "Aktion fehlgeschlagen.";
    toast(message, "error");
    if (payload.errors) {
      Object.entries(payload.errors).forEach(([field, errors]) => {
        const wrapper = document.querySelector('[data-field="' + field + '"]');
        if (!wrapper) return;
        let list = wrapper.querySelector(".errorlist");
        if (!list) {
          list = document.createElement("ul");
          list.className = "errorlist";
          wrapper.append(list);
        }
        list.innerHTML = "";
        (Array.isArray(errors) ? errors : [errors]).forEach((msg) => {
          const li = document.createElement("li");
          li.textContent = msg;
          list.append(li);
        });
      });
    }
    if (silentForm) return false;
    return false;
  }
  App.submitOptimistic = submitOptimistic;

  function initAjaxForms() {
    // Buttons mit eigenem Endpunkt (z. B. „Freigeben“, „Mahnung erstellen“)
    document.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-optimistic]");
      if (!button) return;
      if (button.dataset.confirmed === "1") {
        button.dataset.confirmed = "";
        return; // Bestätigungsdialog hat den Klick abgefangen
      }
      event.preventDefault();
      const form = button.closest("form");
      if (button.dataset.kind === "ajax" && form && !button.dataset.url) {
        await submitAjaxForm(form, button);
        return;
      }
      await submitOptimistic(button, form || document.createElement("form"));
    });

    // Komplette Formulare per Fetch (z. B. Zahlung erfassen im Modal)
    document.addEventListener("submit", async (event) => {
      const form = event.target.closest("[data-ajax]");
      if (!form) return;
      event.preventDefault();
      await submitAjaxForm(form, event.submitter || $("button[type=submit]", form));
    });
  }

  async function submitAjaxForm(form, button) {
    const url = form.action || window.location.href;
    const data = new FormData(form);
    if (button && button.name) data.append(button.name, button.value);
    withButtonLoading(button, true);
    showLoading();
    let result;
    try {
      result = await post(url, data);
    } catch (error) {
      result = { ok: false, payload: { message: "Netzwerkfehler – bitte erneut versuchen." } };
    }
    hideLoading();
    withButtonLoading(button, false);
    const payload = result.payload || {};
    if (result.ok && payload.ok !== false) {
      applyPatch(payload);
      if (payload.message) toast(payload.message, "success");
      if (payload.reload) window.location.reload();
      if (payload.redirect) window.location.href = payload.redirect;
      if (form.dataset.ajaxReset !== undefined) form.reset();
      if (payload.close_modal) {
        const modal = form.closest("[data-dialog]");
        if (modal) modal.classList.remove("is-open");
      }
      form.dispatchEvent(new CustomEvent("ajax:success", { detail: payload }));
      return true;
    }
    const message = payload.message || "Bitte Eingaben prüfen.";
    toast(message, "error");
    if (payload.errors) {
      Object.entries(payload.errors).forEach(([field, errors]) => {
        const wrapper = document.querySelector('[data-field="' + field + '"]');
        if (!wrapper) return;
        let list = wrapper.querySelector(".errorlist");
        if (!list) {
          list = document.createElement("ul");
          list.className = "errorlist";
          wrapper.append(list);
        }
        list.innerHTML = "";
        (Array.isArray(errors) ? errors : [errors]).forEach((msg) => {
          const li = document.createElement("li");
          li.textContent = msg;
          list.append(li);
        });
      });
    }
    form.dispatchEvent(new CustomEvent("ajax:error", { detail: payload }));
    return false;
  }

  /* --------------------------------------------------- Optimistische Schalter */
  function initToggles() {
    document.addEventListener("change", async (event) => {
      const input = event.target.closest("[data-toggle-url]");
      if (!input) return;
      const url = input.dataset.toggleUrl;
      const wasChecked = !input.checked;
      const data = new FormData();
      if (input.dataset.toggleParam) data.append(input.dataset.toggleParam, input.checked ? "1" : "0");
      input.disabled = true;
      const result = await post(url, data);
      input.disabled = false;
      const payload = result.payload || {};
      if (result.ok && payload.ok !== false) {
        applyPatch(payload);
        input.checked = payload.checked !== undefined ? payload.checked : input.checked;
        if (payload.message) toast(payload.message, "success");
      } else {
        input.checked = wasChecked;
        toast(payload.message || "Änderung konnte nicht gespeichert werden.", "error");
      }
    });

    // Autosave: Ergebnis-Dropdowns, Status-Wechsel usw.
    document.addEventListener("change", async (event) => {
      const input = event.target.closest("[data-autosave]");
      if (!input || !input.dataset.autosave) return;
      const url = input.dataset.url;
      const data = new FormData();
      data.append(input.dataset.fieldName || input.name, input.value);
      const row = input.closest("[data-row]");
      if (row) row.classList.add("is-loading");
      input.disabled = true;
      const result = await post(url, data);
      input.disabled = false;
      if (row) row.classList.remove("is-loading");
      const payload = result.payload || {};
      if (result.ok && payload.ok !== false) {
        applyPatch(payload);
        if (payload.message) toast(payload.message, "success", 2500);
      } else {
        toast(payload.message || "Speichern fehlgeschlagen.", "error");
      }
    });
  }

  /* ------------------------------------------------- Lokale Tabellenfilter */
  function initQuickFilters() {
    $$("[data-quick-filter]").forEach((input) => {
      const table = $(input.dataset.quickFilter);
      if (!table) return;
      input.addEventListener("input", () => {
        const needle = input.value.trim().toLowerCase();
        $$("tbody tr", table).forEach((row) => {
          const haystack = row.textContent.toLowerCase();
          row.hidden = needle.length > 0 && !haystack.includes(needle);
        });
      });
    });
  }

  /* ----------------------------------------------- Ladezustand bei Navigation */
  function initNavigationFeedback() {
    window.addEventListener("beforeunload", () => showLoading());
    document.addEventListener("submit", (event) => {
      const form = event.target;
      if (form.matches("[data-ajax]")) return;
      const button = event.submitter || $("button[type=submit]", form);
      withButtonLoading(button, true);
      showLoading();
    });
    document.addEventListener("click", (event) => {
      const link = event.target.closest("a[href]");
      if (!link) return;
      if (link.target === "_blank" || link.hasAttribute("download")) return;
      const href = link.getAttribute("href");
      if (!href || href.startsWith("#") || link.dataset.noLoading !== undefined) return;
      if (link.host !== window.location.host) return;
      const skeletonTarget = link.dataset.skeleton;
      if (skeletonTarget) {
        $$(skeletonTarget).forEach((el) => el.classList.add("skeleton"));
      }
      const bar = $("[data-loading-bar]");
      if (bar) bar.classList.add("is-active");
    });
  }

  /* -------------------------------------------------------- Fortschrittsbalken */
  function initProgressBars() {
    $$("[data-progress]").forEach((el) => {
      const value = Math.max(0, Math.min(100, parseInt(el.dataset.progress, 10) || 0));
      const inner = el.querySelector("span");
      if (inner) requestAnimationFrame(() => (inner.style.width = value + "%"));
    });
  }

  /* --------------------------------------------------------------- Dialoge */
  function initDialogs() {
    $$("[data-dialog-open]").forEach((trigger) => {
      trigger.addEventListener("click", (event) => {
        event.preventDefault();
        const dialog = $(trigger.dataset.dialogOpen);
        if (dialog) dialog.classList.add("is-open");
      });
    });
    $$("[data-dialog]").forEach((dialog) => {
      $$("[data-dialog-close]", dialog).forEach((btn) =>
        btn.addEventListener("click", () => dialog.classList.remove("is-open"))
      );
      dialog.addEventListener("click", (event) => {
        if (event.target === dialog) dialog.classList.remove("is-open");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    adoptFlashMessages();
    initSidebar();
    initDropdowns();
    initConfirm();
    initAjaxForms();
    initToggles();
    initQuickFilters();
    initNavigationFeedback();
    initProgressBars();
    initDialogs();
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
