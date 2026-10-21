/* Core: language, theme, links, Index S chart, corpus bars, hash router. Vanilla JS, no dependencies. */
(function () {
  "use strict";
  var CFG = window.UNU_CONFIG, STR = window.UNU_STRINGS;
  var doc = document.documentElement;
  var cache = {};
  var SCRIPTS = ["zh_tw", "zh_cn", "en"];

  function lang() { return doc.lang === "en" ? "en" : "zh"; }

  function t(key, vars) {
    var s = (STR[lang()] && STR[lang()][key]);
    if (s == null) s = (STR.zh[key] != null ? STR.zh[key] : key);
    if (vars) s = s.replace(/\{(\w+)\}/g, function (m, k) { return vars[k] != null ? vars[k] : m; });
    return s;
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtP(x) { return x == null ? "–" : x.toFixed(2); }
  function fmtS(x) {
    if (x == null) return "–";
    var v = Math.round(x * 100) / 100;
    if (v === 0) return "0.00";
    return (v > 0 ? "+" : "−") + Math.abs(v).toFixed(2);
  }

  function fetchJSON(path) {
    if (!cache[path]) {
      cache[path] = fetch(path, { cache: "default" }).then(function (r) {
        if (!r.ok) throw new Error(path + " " + r.status);
        return r.json();
      });
      cache[path].catch(function () { delete cache[path]; });
    }
    return cache[path];
  }

  var toastTimer;
  function toast(msg) {
    var el = document.getElementById("toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("show"); }, 1800);
  }

  function copyText(text, okMsg) {
    var done = function () { toast(okMsg || t("copied")); };
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(done, function () { fallback(); });
    }
    fallback();
    function fallback() {
      var ta = document.createElement("textarea");
      ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); done(); } catch (e) { /* ignore */ }
      document.body.removeChild(ta);
    }
    return Promise.resolve();
  }

  /* ── language ─────────────────────────────────────────────────────────────── */
  function applyI18n(root) {
    (root || document).querySelectorAll("[data-i18n]").forEach(function (el) {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    (root || document).querySelectorAll("[data-i18n-ph]").forEach(function (el) {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-ph")));
    });
  }

  function applyLinks() {
    var L = CFG.links, l = lang();
    document.querySelectorAll("[data-link]").forEach(function (a) {
      var v = L[a.getAttribute("data-link")];
      if (v) a.href = typeof v === "string" ? v : (v[l] || v.zh);
    });
    document.querySelectorAll("[data-file]").forEach(function (a) { a.href = L.repoFile + a.getAttribute("data-file"); });
    var ax = document.getElementById("arxivBtn");
    if (ax) {
      var id = CFG.arxiv && CFG.arxiv.id;
      var label = ax.querySelector("[data-i18n]");
      if (id) {
        ax.href = "https://arxiv.org/abs/" + id;
        ax.removeAttribute("aria-disabled");
        if (label) { label.removeAttribute("data-i18n"); label.textContent = "arXiv:" + id; }
      } else {
        ax.href = "#cite";
        ax.setAttribute("aria-disabled", "true");
      }
    }
    var bib = document.getElementById("bibtex");
    if (bib && CFG.arxiv && CFG.arxiv.id && bib.textContent.indexOf("eprint") < 0) {
      bib.textContent = bib.textContent.replace("  note         = {Preprint}",
        "  eprint       = {" + CFG.arxiv.id + "},\n  archivePrefix = {arXiv},\n  note         = {Preprint}");
    }
  }

  function applyVideo() {
    var v = document.getElementById("teaser");
    if (!v) return;
    var c = CFG.video[lang()] || CFG.video.zh;
    var src = v.querySelector("source");
    if (src && src.getAttribute("src") === c.src) return;
    var wasPlaying = !v.paused;
    v.pause();
    v.poster = c.poster;
    if (src) src.setAttribute("src", c.src);
    v.load();
    if (wasPlaying) v.play().catch(function () {});
  }

  function setLang(l, persist) {
    doc.lang = l === "en" ? "en" : "zh-Hant-TW";
    if (persist) { try { localStorage.setItem("unu-lang", l); } catch (e) { /* ignore */ } }
    var b = document.getElementById("langBtn");
    if (b) {
      b.setAttribute("aria-label", t("lang.switchLabel"));
      b.setAttribute("lang", l === "en" ? "zh-Hant" : "en");
    }
    document.title = l === "en" ? "Uncensored Is Not Unbiased · 去審查 ≠ 去偏見" : "去審查 ≠ 去偏見 · Uncensored Is Not Unbiased";
    applyI18n();
    applyLinks();
    applyVideo();
    updateThemeBtn();
    var url = new URL(location.href);
    if (url.searchParams.has("lang")) { url.searchParams.set("lang", l); history.replaceState(null, "", url); }
    document.dispatchEvent(new CustomEvent("unu:lang", { detail: l }));
  }

  /* ── theme ────────────────────────────────────────────────────────────────── */
  function isDark() {
    var a = doc.getAttribute("data-theme");
    if (a) return a === "dark";
    return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function updateThemeBtn() {
    var b = document.getElementById("themeBtn");
    if (!b) return;
    b.setAttribute("aria-label", isDark() ? t("theme.toLight") : t("theme.toDark"));
    b.setAttribute("title", b.getAttribute("aria-label"));
    b.innerHTML = isDark()
      ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>';
  }

  /* ── Index S chart ────────────────────────────────────────────────────────── */
  var chartSet = "sov";
  var CHART_RUNS = { sov: ["bo", "ba", "qo", "qa", "qs"], roc: ["bo", "ba", "qo", "qa", "qs"],
                     tam: ["bo", "ba", "qo", "qa", "qs"], ctl: ["bo", "ba", "qo", "qa", "qs"] };

  function renderChart() {
    var body = document.getElementById("ichart-body");
    if (!body) return;
    Promise.all([fetchJSON("data/summary.json"), fetchJSON("data/meta.json")]).then(function (res) {
      var S = res[0], M = res[1];
      var names = {};
      M.models.forEach(function (m) { names[m.id] = m.name[lang()]; });
      var title = document.getElementById("ichart-title");
      if (title) title.textContent = t("chart.title." + chartSet);
      var pos = function (v) { return ((v + 1) / 2 * 100).toFixed(2) + "%"; };
      var rows = "", tbl = "";
      CHART_RUNS[chartSet].forEach(function (run) {
        var d = chartSet === "roc" ? S.roc[run] : (S.index[run] && S.index[run][chartSet]);
        if (!d) return;
        rows += '<div class="igroup"><div class="ig-name">' + esc(names[run]) + "</div>";
        tbl += "<tr><th scope=\"row\">" + esc(names[run]) + "</th>";
        SCRIPTS.forEach(function (s, i) {
          var v = d[s][0], lo = d[s][1], hi = d[s][2];
          var cls = v > 0.05 ? "pos" : (v < -0.05 ? "neg" : "nil");
          var tip = t("chart.tip", { m: names[run], s: t("script." + s), v: fmtS(v), lo: fmtS(lo), hi: fmtS(hi) });
          rows += '<div class="irow" role="img" aria-label="' + esc(tip) + '" title="' + esc(tip) + '">' +
            '<span class="m">' + (i === 0 ? esc(names[run]) : "") + "</span>" +
            '<span class="s">' + esc(t("script." + s)) + "</span>" +
            '<span class="track"><span class="zero"></span>' +
            '<span class="ci" style="left:' + pos(lo) + ";width:calc(" + pos(hi) + " - " + pos(lo) + ')"></span>' +
            '<span class="dot ' + cls + '" style="left:' + pos(v) + '"></span></span>' +
            '<span class="v">' + fmtS(v) + "</span></div>";
          tbl += "<td>" + fmtS(v) + ' <span class="muted">[' + fmtS(lo) + ", " + fmtS(hi) + "]</span></td>";
        });
        tbl += "<td>" + fmtS(d.gap[0]) + "</td></tr>";
        rows += "</div>";
      });
      var ticks = [-1, -0.5, 0, 0.5, 1].map(function (v) {
        return '<span style="left:' + pos(v) + '">' + (v === 0 ? "0" : fmtS(v).replace(".00", "").replace(".50", ".5")) + "</span>";
      }).join("");
      body.innerHTML = '<div class="irows">' + rows + "</div>" +
        '<div class="iaxis" aria-hidden="true"><span></span><span></span><span class="ticks">' + ticks + "</span><span></span></div>" +
        '<div class="iaxis" aria-hidden="true"><span></span><span></span><span class="poles"><span>' + esc(t("chart.left")) +
        "</span><span>" + esc(t("chart.right")) + "</span></span><span></span></div>" +
        '<details class="tableview"><summary>' + esc(t("chart.tableView")) + '</summary><div class="tbl-scroll"><table class="tbl"><thead><tr><th>' +
        esc(t("chart.model")) + "</th>" + SCRIPTS.map(function (s) { return "<th>" + esc(t("script." + s)) + "</th>"; }).join("") +
        "<th>" + esc(t("chart.gap")) + "</th></tr></thead><tbody>" + tbl + "</tbody></table></div></details>";
    }).catch(function () { body.innerHTML = '<p class="muted">' + esc(t("loadError")) + "</p>"; });
  }

  function initChart() {
    var seg = document.getElementById("ichart-seg");
    if (!seg) return;
    seg.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-set]");
      if (!b) return;
      chartSet = b.getAttribute("data-set");
      seg.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
      renderChart();
    });
    renderChart();
    document.addEventListener("unu:lang", renderChart);
  }

  /* ── corpus bars (from data_audit/results.json via summary.json) ──────────── */
  function renderCorpus() {
    var el = document.getElementById("corpus-bars");
    if (!el) return;
    fetchJSON("data/summary.json").then(function (S) {
      var c = S.corpus, max = Math.max(c.simp.prc, c.trad.prc, c.simp.roc, c.trad.roc);
      var row = function (lbl, v, cls) {
        return '<div class="cmpbar"><span>' + esc(lbl) + '</span><span class="bt"><span class="bf ' + cls + '" style="width:' +
          (v / max * 100).toFixed(1) + '%"></span></span><span class="val">' + (v * 100).toFixed(1) + "%</span></div>";
      };
      var zh = lang() === "zh";
      el.innerHTML =
        row(zh ? "简体·北京" : "Simp. · PRC", c.simp.prc, "prc") + row(zh ? "繁體·北京" : "Trad. · PRC", c.trad.prc, "prc") +
        row(zh ? "简体·中華民國" : "Simp. · ROC", c.simp.roc, "roc") + row(zh ? "繁體·中華民國" : "Trad. · ROC", c.trad.roc, "roc");
    }).catch(function () {});
  }

  /* ── router ───────────────────────────────────────────────────────────────── */
  function parseHash() {
    var h = location.hash.replace(/^#/, "");
    if (h.indexOf("q=") !== 0 && h.indexOf("&q=") < 0) return null;
    var out = {};
    h.split("&").forEach(function (kv) {
      var i = kv.indexOf("=");
      if (i > 0) out[decodeURIComponent(kv.slice(0, i))] = decodeURIComponent(kv.slice(i + 1));
    });
    return out.q ? out : null;
  }

  function route(scroll) {
    var p = parseHash();
    if (p && window.UNU.explorer) {
      window.UNU.explorer.open(p.q, p, { scroll: scroll !== false });
    }
  }

  window.UNU = {
    t: t, esc: esc, lang: lang, fmtP: fmtP, fmtS: fmtS, fetchJSON: fetchJSON, toast: toast, copyText: copyText,
    applyI18n: applyI18n, SCRIPTS: SCRIPTS, parseHash: parseHash, route: route,
    setHash: function (params) {
      var parts = [];
      Object.keys(params).forEach(function (k) {
        if (params[k] != null && params[k] !== "" && params[k] !== false) parts.push(k + "=" + encodeURIComponent(params[k]));
      });
      var h = "#" + parts.join("&");
      if (location.hash !== h) history.replaceState(null, "", location.pathname + location.search + h);
    },
    itemUrl: function (key) {
      var base = CFG.siteUrl || (location.origin + location.pathname);
      return base + (lang() === "en" ? "?lang=en" : "") + "#q=" + encodeURIComponent(key);
    }
  };

  document.addEventListener("DOMContentLoaded", function () {
    var l = lang();
    var lb = document.getElementById("langBtn");
    if (lb) lb.addEventListener("click", function () { setLang(lang() === "en" ? "zh" : "en", true); });
    var tb = document.getElementById("themeBtn");
    if (tb) tb.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      doc.setAttribute("data-theme", next);
      try { localStorage.setItem("unu-theme", next); } catch (e) { /* ignore */ }
      updateThemeBtn();
    });
    if (window.matchMedia) matchMedia("(prefers-color-scheme: dark)").addEventListener("change", updateThemeBtn);
    var bc = document.getElementById("bibCopy");
    if (bc) bc.addEventListener("click", function () { copyText(document.getElementById("bibtex").textContent); });
    setLang(l, false);
    initChart();
    renderCorpus();
    document.addEventListener("unu:lang", renderCorpus);
    window.addEventListener("hashchange", function () { route(true); });
    /* the explorer's first render changes the page height: land on a section anchor again */
    var t0 = Date.now(), userScrolled = false;
    ["wheel", "touchstart", "keydown", "mousedown"].forEach(function (ev) { window.addEventListener(ev, function () { userScrolled = true; }, { once: true, passive: true }); });
    document.addEventListener("unu:explorer-ready", function () {
      var h = location.hash.slice(1);
      if (!h || h.indexOf("q=") === 0 || userScrolled || Date.now() - t0 > 5000) return;
      var el = document.getElementById(h);
      if (el) el.scrollIntoView({ behavior: "auto" });
    });
    document.addEventListener("click", function (e) {
      var a = e.target.closest('a[href^="#q="]');
      if (a && a.getAttribute("href") === location.hash) { e.preventDefault(); route(true); }
      var d = e.target.closest('a[aria-disabled="true"]');
      if (d) e.preventDefault();
    });
  });
  window.addEventListener("load", function () { route(true); });
})();
