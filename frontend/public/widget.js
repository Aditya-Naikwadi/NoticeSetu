/* NoticeSetu Shadow DOM Embed Widget (< 15 KB, zero external dependencies) */
(function () {
  "use strict";

  var scriptEl = document.currentScript;
  var baseOrigin = window.location.origin;
  if (scriptEl && scriptEl.src) {
    try {
      baseOrigin = new URL(scriptEl.src, window.location.href).origin;
    } catch (_err) {
      baseOrigin = window.location.origin;
    }
  }

  var ATTR_ATTACHED = "data-noticesetu-attached";
  var MODAL_HOST_ID = "noticesetu-shadow-modal-host";

  function isPdfLink(anchor) {
    if (!anchor || !anchor.getAttribute) return false;
    var rawHref = anchor.getAttribute("href");
    if (!rawHref || rawHref.startsWith("#") || rawHref.startsWith("javascript:")) {
      return false;
    }
    try {
      var resolved = new URL(rawHref, window.location.href);
      return /\.pdf($|\?)/i.test(resolved.pathname + resolved.search);
    } catch (_err) {
      return /\.pdf($|\?)/i.test(rawHref);
    }
  }

  function ensureModal() {
    var existing = document.getElementById(MODAL_HOST_ID);
    if (existing && existing._noticesetuOpen) {
      return existing;
    }

    var host = document.createElement("div");
    host.id = MODAL_HOST_ID;
    var shadow = host.attachShadow({ mode: "open" });

    var style = document.createElement("style");
    style.textContent =
      ".ns-backdrop{position:fixed;inset:0;z-index:2147483647;background:rgba(15,23,42,0.72);" +
      "display:none;align-items:center;justify-content:center;padding:16px;font-family:system-ui,-apple-system,sans-serif;}" +
      ".ns-backdrop.open{display:flex;}" +
      ".ns-panel{width:100%;max-width:920px;height:88vh;background:#F8FAFC;border-radius:14px;" +
      "overflow:hidden;display:flex;flex-direction:column;box-shadow:0 24px 48px rgba(15,23,42,0.35);}" +
      ".ns-header{background:#0F172A;color:#F8FAFC;padding:12px 16px;display:flex;" +
      "align-items:center;justify-content:space-between;gap:12px;}" +
      ".ns-title{font-size:14px;font-weight:700;letter-spacing:0.01em;}" +
      ".ns-actions{display:flex;align-items:center;gap:10px;}" +
      ".ns-newtab{color:#5EEAD4;font-size:12px;font-weight:600;text-decoration:none;border:1px solid rgba(94,234,212,0.4);" +
      "padding:5px 10px;border-radius:999px;}" +
      ".ns-newtab:hover{background:rgba(13,148,136,0.25);}" +
      ".ns-close{background:transparent;color:#F8FAFC;border:1px solid rgba(248,250,252,0.3);" +
      "border-radius:8px;padding:4px 10px;font-size:13px;cursor:pointer;font-weight:600;}" +
      ".ns-close:hover{background:rgba(255,255,255,0.12);}" +
      ".ns-frame{width:100%;flex:1;border:0;background:#F8FAFC;}";

    var backdrop = document.createElement("div");
    backdrop.className = "ns-backdrop";
    backdrop.setAttribute("role", "dialog");
    backdrop.setAttribute("aria-modal", "true");
    backdrop.setAttribute("aria-label", "NoticeSetu Action Card Viewer");

    var panel = document.createElement("div");
    panel.className = "ns-panel";

    var header = document.createElement("div");
    header.className = "ns-header";

    var title = document.createElement("span");
    title.className = "ns-title";
    title.textContent = "NoticeSetu — Action Card (EN / हिंदी / मराठी)";

    var actions = document.createElement("div");
    actions.className = "ns-actions";

    var newTabLink = document.createElement("a");
    newTabLink.className = "ns-newtab";
    newTabLink.target = "_blank";
    newTabLink.rel = "noopener noreferrer";
    newTabLink.textContent = "Open in New Tab";

    var closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "ns-close";
    closeBtn.textContent = "Close";

    var iframe = document.createElement("iframe");
    iframe.className = "ns-frame";
    iframe.title = "NoticeSetu Simplified Circular";

    function closeModal() {
      backdrop.classList.remove("open");
      iframe.src = "about:blank";
    }

    closeBtn.addEventListener("click", closeModal);
    backdrop.addEventListener("click", function (ev) {
      if (ev.target === backdrop) closeModal();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && backdrop.classList.contains("open")) {
        closeModal();
      }
    });

    actions.appendChild(newTabLink);
    actions.appendChild(closeBtn);
    header.appendChild(title);
    header.appendChild(actions);
    panel.appendChild(header);
    panel.appendChild(iframe);
    backdrop.appendChild(panel);
    shadow.appendChild(style);
    shadow.appendChild(backdrop);

    document.body.appendChild(host);

    host._noticesetuOpen = function (pdfUrl) {
      var viewUrl = baseOrigin + "/view?url=" + encodeURIComponent(pdfUrl);
      newTabLink.href = viewUrl;
      iframe.src = viewUrl;
      backdrop.classList.add("open");
    };

    return host;
  }

  function injectPill(anchor) {
    if (anchor.getAttribute(ATTR_ATTACHED) === "true") return;
    anchor.setAttribute(ATTR_ATTACHED, "true");

    var resolvedPdfUrl = new URL(anchor.getAttribute("href"), window.location.href).href;

    var pillHost = document.createElement("span");
    pillHost.style.display = "inline-block";
    pillHost.style.marginLeft = "8px";
    pillHost.style.verticalAlign = "middle";

    var shadow = pillHost.attachShadow({ mode: "open" });
    var style = document.createElement("style");
    style.textContent =
      ".ns-pill{all:initial;display:inline-flex;align-items:center;gap:4px;" +
      "background:#0D9488;color:#FFFFFF;font-family:system-ui,-apple-system,sans-serif;" +
      "font-size:12px;font-weight:600;line-height:1.2;padding:4px 10px;border-radius:9999px;" +
      "cursor:pointer;border:1px solid #0F766E;box-shadow:0 1px 2px rgba(15,23,42,0.12);}" +
      ".ns-pill:hover{background:#0F766E;}" +
      ".ns-pill:focus-visible{outline:2px solid #0F172A;outline-offset:2px;}";

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ns-pill";
    btn.textContent = "Simplify (EN/हिं/म)";
    btn.title = "Open simplified NoticeSetu Action Card in English, Hindi, or Marathi";
    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var modal = ensureModal();
      modal._noticesetuOpen(resolvedPdfUrl);
    });

    shadow.appendChild(style);
    shadow.appendChild(btn);
    anchor.insertAdjacentElement("afterend", pillHost);
  }

  function scanLinks(root) {
    var scope = root && root.querySelectorAll ? root : document;
    var anchors = scope.querySelectorAll("a[href]");
    for (var i = 0; i < anchors.length; i++) {
      if (isPdfLink(anchors[i])) {
        injectPill(anchors[i]);
      }
    }
  }

  function init() {
    scanLinks(document);
    if (typeof MutationObserver !== "undefined" && document.body) {
      var observer = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          var added = mutations[i].addedNodes;
          for (var j = 0; j < added.length; j++) {
            var node = added[j];
            if (node.nodeType === 1) {
              if (node.tagName === "A" && isPdfLink(node)) {
                injectPill(node);
              } else {
                scanLinks(node);
              }
            }
          }
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

