/* Interactive explorer: item list, statement pairs (P(yes) per phrasing), direct questions, open answers. */
(function () {
  "use strict";
  var U = window.UNU, t = U.t, esc = U.esc, S = U.SCRIPTS;
  var MAIN = ["bo", "ba", "qo", "qa"], EXTRA = ["qs", "sb", "sv", "sn"];
  var meta = null, byKey = {}, models = {}, steer = { train: [], test: [] };
  var state = { key: null, m: null, s: "zh_tw", v: "scripts", x: false, cell: null };
  var els = {}, query = "", ready = null, autoOpened = false;

  function $(sel) { return document.querySelector(sel); }
  function pct(p) { return (Math.max(0, Math.min(1, p || 0)) * 100).toFixed(1) + "%"; }
  function L() { return U.lang(); }
  function mname(id) { return models[id] ? models[id].name[L()] : id; }

  function load() {
    if (!ready) {
      ready = Promise.all([U.fetchJSON("data/meta.json"), U.fetchJSON("data/summary.json")]).then(function (r) {
        meta = r[0];
        meta.items.forEach(function (i) { byKey[i.key] = i; });
        meta.models.forEach(function (m) { models[m.id] = m; });
        steer = r[1].steer;
        return meta;
      });
    }
    return ready;
  }

  /* ── item texts ─────────────────────────────────────────────────────────── */
  function itemText(it) {
    var s = L() === "en" ? "en" : "zh_tw";
    if (it.k === "pair") return it.t.pro[s];
    if (it.k === "triple") return it.theme[L()];
    return it.q[s];
  }
  function searchText(it) {
    var parts = [it.key, it.id];
    var add = function (o) { if (o) S.forEach(function (s) { parts.push(o[s]); }); };
    if (it.t) Object.keys(it.t).forEach(function (k) { add(it.t[k]); });
    if (it.q) add(it.q);
    if (it.theme) parts.push(it.theme.zh, it.theme.en);
    return parts.join(" \u0001 ").toLowerCase();
  }

  /* ── list ───────────────────────────────────────────────────────────────── */
  function renderList() {
    if (!meta) return;
    var q = query.trim().toLowerCase(), html = "", any = false;
    meta.groups.forEach(function (g) {
      var items = meta.items.filter(function (i) { return i.g === g.id && (!q || searchText(i).indexOf(q) >= 0); });
      if (!items.length) return;
      any = true;
      var open = q || items.some(function (i) { return i.key === state.key; }) || g.id === "sov";
      html += "<details" + (open ? " open" : "") + "><summary>" + esc(g.name[L()]) + '<span class="n">' + items.length +
        "</span></summary><ul>" + items.map(function (i) {
          return '<li><button type="button" data-key="' + esc(i.key) + '"' + (i.key === state.key ? ' aria-current="true"' : "") +
            '><span class="iid">' + esc(i.id) + '</span><span class="txt">' + esc(itemText(i)) + "</span></button></li>";
        }).join("") + "</ul></details>";
    });
    els.list.innerHTML = any ? html : '<p class="muted small" style="padding:10px">' + esc(t("ex.noMatch")) + "</p>";
  }

  function visibleKeys() {
    var q = query.trim().toLowerCase(), out = [];
    meta.groups.forEach(function (g) {
      meta.items.forEach(function (i) { if (i.g === g.id && (!q || searchText(i).indexOf(q) >= 0)) out.push(i.key); });
    });
    return out;
  }

  /* ── shared pieces ──────────────────────────────────────────────────────── */
  function badge(cls, text, tip) {
    return '<span class="badge ' + (cls || "") + '"' + (tip ? ' title="' + esc(tip) + '"' : "") + ">" + esc(text) + "</span>";
  }

  function header(it) {
    var g = meta.groups.filter(function (x) { return x.id === it.g; })[0];
    return '<div class="ex-top">' + badge("id", it.id) + badge("", g ? g.name[L()] : it.g) +
      (g && g.name[L()].indexOf(t("ex.kind." + it.k)) >= 0 ? "" : badge("", t("ex.kind." + it.k))) + (it.src ? badge("", t("src." + it.src)) : "") +
      '<span class="spacer"></span><button type="button" class="linkbtn" data-act="copylink">' + esc(t("copyLink")) + "</button></div>";
  }

  function related(it) {
    var out = [];
    if (it.mir && byKey[it.mir]) {
      out.push(esc(t("ex.mirrorOf")) + ' <a href="#q=' + esc(it.mir) + '">' + esc(byKey[it.mir].id) + "</a>");
    }
    (it.mirBy || []).forEach(function (k) {
      if (byKey[k]) out.push(esc(t("ex.mirroredBy")) + ': <a href="#q=' + esc(k) + '">' + esc(byKey[k].id) + "</a>");
    });
    return out.length ? '<div class="related">' + out.map(function (x) { return "<span>" + x + "</span>"; }).join("") + "</div>" : "";
  }

  function groupNote(it) {
    if (it.g === "sov" || it.g === "tam" || it.g === "ctl" || (it.g === "open" && it.src === "ko2026")) {
      return it.k === "pair" ? '<p class="note">' + esc(t("ex.inheritedNote")) + "</p>" : "";
    }
    if (it.g === "roc") return '<p class="note">' + esc(t("ex.rocNote")) + "</p>";
    if (it.g === "c92") return '<p class="note box">' + esc(t("ex.c92Note")) + "</p>";
    return "";
  }

  function textTable(rows) {
    /* rows: [{label, swatch, texts:{script:text}}] */
    return '<table class="stmts"><thead><tr><th></th>' + S.map(function (s) { return "<th>" + esc(t("script." + s)) + "</th>"; }).join("") +
      "</tr></thead><tbody>" + rows.map(function (r) {
        return "<tr>" + (r.label != null ? '<td class="sidecell">' + (r.swatch ? '<span class="sw ' + r.swatch + '"></span>' : "") + esc(r.label) + "</td>" : "<td></td>") +
          S.map(function (s) {
            return '<td data-s="' + esc(t("script." + s)) + '" lang="' + (s === "en" ? "en" : s === "zh_cn" ? "zh-Hans" : "zh-Hant") + '">' + esc(r.texts[s]) + "</td>";
          }).join("") + "</tr>";
      }).join("") + "</tbody></table>";
  }

  function modeTag(run) {
    var m = models[run];
    return m ? '<span class="mm">' + esc(t("mode." + m.mode)) + "</span>" : "";
  }

  function sidesOf(it) { return it.k === "triple" ? ["roc", "prc", "dpp"] : ["pro", "con"]; }

  /* ── probe matrix ───────────────────────────────────────────────────────── */
  function barRow(side, e) {
    if (!e) return "";
    var dots = (e.p || []).map(function (p) { return p == null ? "" : '<i class="ph" style="left:' + pct(p) + '"></i>'; }).join("");
    return '<div class="br"><span class="bt"><span class="half"></span><span class="bf ' + side + '" style="width:' + pct(e.m) + '"></span>' +
      dots + '</span><span class="val">' + U.fmtP(e.m) + "</span></div>";
  }
  function dLine(d) {
    if (d == null) return "";
    var w = Math.abs(d) * 50, left = d >= 0 ? 50 : 50 - w;
    return '<div class="dline"><span class="dt"><span class="db ' + (d >= 0 ? "pos" : "neg") + '" style="left:' + left.toFixed(1) +
      "%;width:" + w.toFixed(1) + '%"></span></span><span class="val">' + U.fmtS(d) + "</span></div>";
  }

  function cellButton(run, s, inner, label) {
    var on = state.cell && state.cell[0] === run && state.cell[1] === s;
    return '<button type="button" class="cell" data-run="' + run + '" data-s="' + s + '" aria-pressed="' + on + '" aria-label="' + esc(label) + '">' + inner + "</button>";
  }

  function runsFor(data) {
    var r = MAIN.slice();
    if (state.x) EXTRA.forEach(function (x) { if (data[x]) r.push(x); });
    return r;
  }

  function probeMatrix(it, data, kind) {
    var sides = kind === "direct" ? null : sidesOf(it);
    var runs = runsFor(data);
    var rows = runs.map(function (run, i) {
      var sep = (i === MAIN.length) ? ' class="sep"' : "";
      var cells = S.map(function (s) {
        var c = data[run] && data[run][s];
        if (!c) return '<td data-s="' + esc(t("script." + s)) + '"><div class="cell empty">–</div></td>';
        var inner, label;
        if (kind === "direct") {
          var side = yesSide(it);
          inner = barRow(side, { m: c.p, p: [] });
          label = mname(run) + " · " + t("script." + s) + ": P(yes) " + U.fmtP(c.p);
        } else {
          inner = sides.map(function (sd) { return barRow(sd, c[sd]); }).join("") + (kind === "pair" ? dLine(c.d) : "");
          label = mname(run) + " · " + t("script." + s) + ": " + sides.map(function (sd) {
            return t("side." + sd) + " " + U.fmtP(c[sd] && c[sd].m);
          }).join(", ") + (c.d != null ? ", d " + U.fmtS(c.d) : "");
        }
        return '<td data-s="' + esc(t("script." + s)) + '">' + cellButton(run, s, inner, label) + "</td>";
      }).join("");
      return "<tr" + sep + '><th scope="row" class="mname">' + esc(mname(run)) + modeTag(run) + "</th>" + cells + "</tr>";
    }).join("");
    return '<table class="mx"><thead><tr><th>' + esc(t("ex.model")) + "</th>" +
      S.map(function (s) { return "<th>" + esc(t("script." + s)) + "</th>"; }).join("") + "</tr></thead><tbody>" + rows + "</tbody></table>";
  }

  function yesSide(it) {
    var q = it.qid || it.direct || "";
    return q.indexOf("prc") >= 0 ? "con" : "pro";
  }

  function legend(it, kind) {
    if (kind === "direct") {
      var side = yesSide(it);
      return '<div class="legend"><span><span class="sw ' + side + '"></span>' + esc(t("ex.pyes")) + " · " +
        esc(L() === "en" ? (side === "con" ? "yes = PRC side" : "yes = ROC side") : (side === "con" ? "答「是」＝北京方" : "答「是」＝中華民國方")) + "</span></div>";
    }
    return '<div class="legend">' + sidesOf(it).map(function (sd) {
      return '<span><span class="sw ' + sd + '"></span>' + esc(t("side." + sd)) + "</span>";
    }).join("") + (kind === "pair" ? '<span><span class="sw" style="background:linear-gradient(90deg,var(--prc) 50%,var(--roc) 50%)"></span>d</span>' : "") + "</div>";
  }

  function interventionToggle(data) {
    var has = EXTRA.some(function (x) { return data[x]; });
    if (!has) return "";
    return '<label class="toggle"><input type="checkbox" data-act="x"' + (state.x ? " checked" : "") + "> " + esc(t("ex.showX")) + "</label>";
  }

  function prompts(it, side, s, k) {
    var text = (it.k === "pair" || it.k === "triple") ? it.t[side][s] : "";
    return meta.phrasings[s][k].replace("{s}", text);
  }

  function runNotes(it, run) {
    var out = [];
    var m = models[run];
    if (m) out.push(esc(m.name[L()]) + ": " + esc(t("mode." + m.mode + "Long")));
    if (run === "qs") out.push(esc(t("ex.sysNote")) + '<pre class="prompt" lang="zh-Hant">' + esc(meta.systemPrompt) + "</pre>");
    if (run === "sv" || run === "sn" || run === "sb") {
      out.push(esc(t("ex.steerNote")));
      var base = it.mir && it.g === "roc" ? it.mir : it.id;
      if (steer.train.indexOf(base) >= 0) out.push(esc(t("ex.trainPair")));
      else if (steer.test.indexOf(base) >= 0) out.push(esc(t("ex.heldPair")));
    }
    return out.map(function (x) { return '<p class="note">' + x + "</p>"; }).join("");
  }

  function drawer(it, data, kind) {
    if (!state.cell) return "";
    var run = state.cell[0], s = state.cell[1];
    var c = data[run] && data[run][s];
    if (!c) return "";
    var h = '<div class="drawer" id="ex-drawer"><h4>' + esc(t("ex.detail")) + "：" + esc(mname(run)) + " · " + esc(t("script." + s)) + "</h4>";
    if (kind === "direct") {
      h += '<table class="ptable"><thead><tr><th>' + esc(t("ex.prompt")) + "</th><th>" + esc(t("ex.pyes")) + "</th></tr></thead><tbody><tr>" +
        '<td data-h="' + esc(t("ex.prompt")) + '"><pre class="prompt">' + esc(data._prompt[s]) + "</pre></td>" +
        '<td class="num" data-h="' + esc(t("ex.pyes")) + '">' + U.fmtP(c.p) + '<span class="sub">' +
        (c.c ? esc(t("ex.counts", { y: c.c[0], n: c.c[1], o: c.c[2] })) : esc(t("ex.mass")) + " " + U.fmtP(c.mass)) + "</span>" +
        (c.src ? '<span class="sub">' + esc(t("ex.directSrc." + c.src)) + "</span>" : "") + "</td></tr></tbody></table>";
    } else {
      sidesOf(it).forEach(function (sd) {
        var e = c[sd];
        if (!e) return;
        h += '<p style="margin:12px 0 4px;font-weight:650"><span class="sw ' + sd + '"></span>' + esc(t("side." + sd)) + " · " +
          esc(t("ex.mean")) + " " + U.fmtP(e.m) + "</p>";
        h += '<table class="ptable ph3"><thead><tr><th>' + esc(t("ex.phrasing")) + "</th><th>" + esc(t("ex.prompt")) + "</th><th>" +
          esc(t("ex.pyes")) + "</th></tr></thead><tbody>";
        for (var k = 0; k < 3; k++) {
          var sub = e.c && e.c[k] ? t("ex.counts", { y: e.c[k][0], n: e.c[k][1], o: e.c[k][2] })
            : (e.mass && e.mass[k] != null ? t("ex.mass") + " " + U.fmtP(e.mass[k]) : "");
          h += "<tr><td data-h=\"" + esc(t("ex.phrasing")) + "\">" + (k + 1) + '</td><td data-h="' + esc(t("ex.prompt")) + '"><pre class="prompt">' +
            esc(prompts(it, sd, s, k)) + '</pre></td><td class="num" data-h="' + esc(t("ex.pyes")) + '">' + U.fmtP(e.p[k]) +
            '<span class="sub">' + esc(sub) + "</span></td></tr>";
        }
        h += "</tbody></table>";
      });
      if (c.d != null) h += '<p class="note">d = ' + U.fmtP(c.pro.m) + " − " + U.fmtP(c.con.m) + " = <strong>" + U.fmtS(c.d) + "</strong></p>";
    }
    return h + runNotes(it, run) + "</div>";
  }

  function renderProbe(it, gen) {
    return U.fetchJSON("data/" + it.file + ".json").then(function (P) {
      if (gen !== renderGen) return;
      var data = P[it.id] || {};
      var kind = it.k;
      if (!state.cell) state.cell = [MAIN[0], it.k === "triple" ? "zh_tw" : "zh_cn"];
      var h = header(it) + '<h3 class="ex-title">' + esc(it.k === "triple" ? it.id + " · " + it.theme[L()] : (L() === "en" ? it.t.pro.en : it.t.pro.zh_tw)) + "</h3>";
      h += textTable(sidesOf(it).map(function (sd) { return { label: t("side." + sd), swatch: sd, texts: it.t[sd] }; }));
      h += related(it) + groupNote(it);
      h += '<div class="ctrls">' + interventionToggle(data) + "</div>";
      h += legend(it, kind) + '<p class="note">' + esc(t(kind === "triple" ? "ex.matrixCaptionTriple" : "ex.matrixCaption")) + "</p>";
      h += probeMatrix(it, data, kind) + drawer(it, data, kind) + nav();
      els.main.innerHTML = h;
    });
  }

  function renderDirectBlock(it, D, standalone) {
    var data = {};
    Object.keys(D.runs).forEach(function (r) { data[r] = D.runs[r]; });
    data._prompt = D.prompt;
    var h = "";
    if (standalone) {
      h += '<div class="ctrls">' + interventionToggle(data) + "</div>";
    }
    h += legend(it, "direct") + '<p class="note">' + esc(t("ex.matrixCaptionDirect")) + "</p>";
    h += probeMatrix(it, data, "direct") + drawer(it, data, "direct");
    return h;
  }

  function renderDirect(it, gen) {
    return U.fetchJSON("data/direct.json").then(function (Dall) {
      if (gen !== renderGen) return;
      var D = Dall[it.id];
      if (!state.cell) state.cell = [MAIN[0], "zh_tw"];
      var h = header(it) + '<h3 class="ex-title">' + esc(L() === "en" ? D.prompt.en : D.prompt.zh_tw) + "</h3>";
      h += textTable([{ label: t("ex.question"), texts: D.prompt }]) + related(it) + renderDirectBlock(it, D, true) + nav();
      els.main.innerHTML = h;
    });
  }

  /* ── open answers ───────────────────────────────────────────────────────── */
  function md(s) {
    var inline = function (l) { return l.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>"); };
    return s.split("\n").map(function (line) {
      var l = esc(line);
      var m = l.match(/^\s{0,3}(#{1,6})\s+(.*)$/);
      if (m) return '<span class="h">' + inline(m[2]) + "</span>";
      if (/^\s*([-*_])\s*\1\s*\1[\s\-*_]*$/.test(l)) return "──────";
      l = l.replace(/^(\s*)[*\-+]\s+/, "$1• ");
      return inline(l);
    }).join("\n");
  }

  function tagsHTML(e, ps) {
    var T = e.tags || {}, o = [];
    if (e.sc === "s" && ps !== "zh_cn") o.push(badge("warn", t("tag.simp"), t("tag.simpTip")));
    if (e.sc === "t" && ps === "zh_cn") o.push(badge("", t("tag.trad")));
    if (T.ref) o.push(badge("bad", t("tag.ref")));
    if (T.id) o.push(badge("warn", t("tag.id"), t("tag.idTip")));
    if (T.ai) o.push(badge("", t("tag.ai")));
    if (T.ina80) o.push(badge("bad", t("tag.ina80"), t("tag.inaTip")));
    else if (T.ina) o.push(badge("", t("tag.ina"), t("tag.inaTip")));
    if (T.t89) o.push(badge("warn", t("tag.t89"), t("tag.t89Tip")));
    if (T.c241) o.push(badge("", t("tag.c241")));
    if (T.exag) o.push(badge("bad", t("tag.exag")));
    if (T.deny === "own") o.push(badge("bad", t("tag.denyOwn"), t("tag.denyOwnTip")));
    else if (T.deny === "attr") o.push(badge("info", t("tag.denyAttr")));
    if (T.yn) o.push(badge("info", t("tag.yn." + T.yn)));
    if (T.tsb) {
      var extra = T.tsb.neg ? " · " + t("tag.tsbNeg") : (!T.tsb.A ? " · " + t("tag.tsbNotA") : "");
      o.push(badge("info", t("tag.tsb") + extra, t("tag.tsbTip", { kw: T.tsb.kw.join(L() === "en" ? ", " : "、") })));
    }
    if (T.trunc) o.push(badge("", t("tag.trunc")));
    return '<span class="tags">' + o.join("") + "</span>";
  }

  function answerCard(e, ps, idx) {
    var lab = '<span class="run">' + esc(t("ex.run." + e.run)) + "</span>" + tagsHTML(e, ps);
    var lg = ps === "en" ? "en" : (e.sc === "s" ? "zh-Hans" : "zh-Hant");
    if (idx === 0) {
      var long = e.a.length > 360;
      return '<article class="ans"><header>' + lab + '</header><div class="body' + (long ? " clamp" : "") + '" lang="' + lg + '">' + md(e.a) + "</div>" +
        (long ? '<button type="button" class="more" data-act="more" aria-expanded="false">' + esc(t("ex.expand")) + "</button>" : "") + "</article>";
    }
    return '<details class="ans"><summary>' + lab + '</summary><div class="body" lang="' + lg + '">' + md(e.a) + "</div></details>";
  }

  function openColumns(it, O, D) {
    var cols = [];
    if (state.v === "models") {
      var runs = MAIN.concat(O.sv ? ["sv"] : []);
      runs.forEach(function (r) { cols.push({ run: r, s: state.s, title: mname(r) }); });
    } else {
      S.forEach(function (s) { cols.push({ run: state.m, s: s, title: t("scriptLong." + s) }); });
    }
    var h = '<div class="ocols" style="--cols:' + (cols.length > 3 ? 2 : cols.length) + '">';
    cols.forEach(function (c) {
      var list = O[c.run] && O[c.run][c.s];
      h += '<div class="ocol"><h4>' + esc(c.title) + "</h4>";
      if (state.v !== "models") h += '<pre class="prompt" lang="' + (c.s === "en" ? "en" : c.s === "zh_cn" ? "zh-Hans" : "zh-Hant") + '">' + esc(it.q[c.s]) + "</pre>";
      if (D && D.runs[c.run] && D.runs[c.run][c.s]) {
        h += '<p class="note">' + esc(t("ex.firstToken")) + ": <strong>" + U.fmtP(D.runs[c.run][c.s].p) + "</strong></p>";
      }
      if (!list) h += '<p class="note">' + esc(t("ex.noData")) + "</p>";
      else list.forEach(function (e, i) { h += answerCard(e, c.s, i); });
      h += "</div>";
    });
    return h + "</div>";
  }

  function renderOpen(it, gen) {
    var ps = [U.fetchJSON("data/" + it.file + ".json")];
    if (it.direct) ps.push(U.fetchJSON("data/direct.json"));
    return Promise.all(ps).then(function (r) {
      if (gen !== renderGen) return;
      var O = r[0], D = r[1] ? r[1][it.id] : null;
      var avail = MAIN.concat(O.sv ? ["sv"] : []);
      if (avail.indexOf(state.m) < 0) state.m = "bo";
      var h = header(it) + '<h3 class="ex-title">' + esc(L() === "en" ? it.q.en : it.q.zh_tw) + "</h3>";
      h += textTable([{ label: t("ex.question"), texts: it.q }]) + related(it);
      if (D) {
        if (!state.cell) state.cell = [MAIN[0], "zh_tw"];
        h += '<div class="dpanel"><p style="font-weight:650;margin:6px 0 2px">' + esc(t("ex.firstToken")) + "</p>" + renderDirectBlock(it, D, false) + "</div>";
      }
      h += '<h4 style="margin:18px 0 6px">' + esc(t("ex.answers")) + "</h4>";
      h += '<div class="ctrls"><div class="seg" role="group" aria-label="view">' +
        ["scripts", "models"].map(function (v) {
          return '<button type="button" data-act="view" data-v="' + v + '" aria-pressed="' + (state.v === v) + '">' + esc(t("ex.view." + v)) + "</button>";
        }).join("") + "</div>";
      if (state.v === "models") {
        h += '<div class="mpick" role="group" aria-label="' + esc(t("ex.pickScript")) + '">' + S.map(function (s) {
          return '<button type="button" data-act="script" data-s="' + s + '" aria-pressed="' + (state.s === s) + '">' + esc(t("script." + s)) + "</button>";
        }).join("") + "</div>";
      } else {
        h += '<div class="mpick" role="group" aria-label="' + esc(t("ex.pickModel")) + '">' + avail.map(function (r) {
          return '<button type="button" data-act="model" data-m="' + r + '" aria-pressed="' + (state.m === r) + '">' + esc(models[r].short[L()]) + "</button>";
        }).join("") + "</div>";
      }
      h += "</div>";
      h += openColumns(it, O, D);
      h += '<p class="note">' + esc(t("ex.tagLegend")) + "</p>" + nav();
      els.main.innerHTML = h;
    });
  }

  function nav() {
    var keys = visibleKeys(), i = keys.indexOf(state.key);
    if (i < 0) return "";
    var prev = keys[i - 1], next = keys[i + 1];
    return '<div class="exnav">' +
      (prev ? '<a href="#q=' + esc(prev) + '">← ' + esc(t("ex.prev")) + " · " + esc(byKey[prev].id) + "</a>" : "<span></span>") +
      (next ? '<a href="#q=' + esc(next) + '">' + esc(t("ex.next")) + " · " + esc(byKey[next].id) + " →</a>" : "<span></span>") + "</div>";
  }

  /* ── render + state ─────────────────────────────────────────────────────── */
  var renderGen = 0;
  function render() {
    var it = byKey[state.key];
    if (!it) return;
    renderGen++;
    var gen = renderGen;
    var p = it.k === "open" ? renderOpen(it, gen) : it.k === "direct" ? renderDirect(it, gen) : renderProbe(it, gen);
    p = p.catch(function (err) {
      if (window.console) console.warn(err);
      els.main.innerHTML = '<p class="muted">' + esc(t("loadError")) + "</p>";
    });
    els.list.querySelectorAll("button[data-key]").forEach(function (b) {
      if (b.getAttribute("data-key") === state.key) b.setAttribute("aria-current", "true"); else b.removeAttribute("aria-current");
    });
    return p;
  }

  function syncHash() {
    var it = byKey[state.key];
    var p = { q: state.key };
    if (it && it.k === "open") {
      if (state.v === "models") { p.v = "models"; if (state.s !== "zh_tw") p.s = state.s; }
      else if (state.m !== "bo") p.m = state.m;
    }
    if (state.x) p.x = 1;
    U.setHash(p);
  }

  function open(key, params, opts) {
    params = params || {}; opts = opts || {};
    load().then(function () {
      var k = byKey[key] ? key : (byKey["Q-" + key] ? "Q-" + key : null);
      if (!k) {
        var lower = String(key).toLowerCase();
        k = Object.keys(byKey).filter(function (x) { return x.toLowerCase() === lower; })[0] || null;
      }
      if (!k) return;
      var changed = k !== state.key;
      state.key = k;
      if (changed) state.cell = null;
      if (params.m && models[params.m]) state.m = params.m; else if (changed) state.m = "bo";
      if (params.s && S.indexOf(params.s) >= 0) state.s = params.s; else if (changed) state.s = "zh_tw";
      state.v = params.v === "models" ? "models" : (changed ? "scripts" : state.v);
      if (params.x != null) state.x = params.x === "1" || params.x === 1 || params.x === true;
      else if (changed) state.x = false;
      if (params.m && ["qs", "sb", "sv", "sn"].indexOf(params.m) >= 0 && byKey[k].k !== "open") state.x = true;
      if (byKey[k].k !== "open" && params.m && models[params.m]) state.cell = [params.m, params.s && S.indexOf(params.s) >= 0 ? params.s : "zh_cn"];
      var det = els.list.querySelector('button[data-key="' + k + '"]');
      if (!det) { query = ""; els.search.value = ""; renderList(); }
      else { var d = det.closest("details"); if (d) d.open = true; }
      var done = render();
      if (opts.ready && done) done.then(function () { document.dispatchEvent(new CustomEvent("unu:explorer-ready")); });
      if (!opts.noHash) syncHash();
      if (opts.scroll) {
        document.getElementById("explorer").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
        try { els.main.focus({ preventScroll: true }); } catch (e) { /* ignore */ }
      }
      var b = els.list.querySelector('button[data-key="' + k + '"]');
      if (b && b.scrollIntoView && opts.scrollList !== false) {
        var box = els.list.getBoundingClientRect(), r = b.getBoundingClientRect();
        if (r.top < box.top || r.bottom > box.bottom) els.list.scrollTop += r.top - box.top - box.height / 3;
      }
    });
  }

  function onMainClick(e) {
    var el = e.target.closest("[data-act], .cell[data-run]");
    if (!el) return;
    if (el.classList.contains("cell")) {
      state.cell = [el.getAttribute("data-run"), el.getAttribute("data-s")];
      render();
      setTimeout(function () {
        var d = document.getElementById("ex-drawer");
        if (d && d.getBoundingClientRect().top > window.innerHeight - 80) d.scrollIntoView({ block: "nearest" });
      }, 60);
      return;
    }
    var act = el.getAttribute("data-act");
    if (act === "copylink") {
      var url = U.itemUrl(state.key);
      U.copyText(url, t("linkCopied"));
    } else if (act === "view") {
      state.v = el.getAttribute("data-v"); render(); syncHash();
    } else if (act === "model") {
      state.m = el.getAttribute("data-m"); render(); syncHash();
    } else if (act === "script") {
      state.s = el.getAttribute("data-s"); render(); syncHash();
    } else if (act === "more") {
      var body = el.previousElementSibling;
      var expanded = el.getAttribute("aria-expanded") === "true";
      body.classList.toggle("clamp", expanded);
      el.setAttribute("aria-expanded", String(!expanded));
      el.textContent = t(expanded ? "ex.expand" : "ex.collapse");
    }
  }

  function init() {
    els.list = $("#ex-list"); els.main = $("#ex-main"); els.search = $("#ex-search");
    if (!els.list) return;
    els.search.setAttribute("placeholder", t("ex.searchPh"));
    els.search.addEventListener("input", function () { query = els.search.value; renderList(); });
    els.list.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-key]");
      if (!b) return;
      open(b.getAttribute("data-key"), {}, { scrollList: false });
      if (window.innerWidth <= 960) els.main.scrollIntoView({ behavior: "smooth", block: "start" });
    });
    els.main.addEventListener("click", onMainClick);
    els.main.addEventListener("change", function (e) {
      if (e.target.matches('input[data-act="x"]')) { state.x = e.target.checked; render(); syncHash(); }
    });
    document.addEventListener("unu:lang", function () {
      els.search.setAttribute("placeholder", t("ex.searchPh"));
      if (meta) { renderList(); if (state.key) render(); }
    });
    var start = function () {
      load().then(function () {
        renderList();
        if (!state.key && !U.parseHash() && !autoOpened) { autoOpened = true; open("X-PRC", {}, { noHash: true, scrollList: false, ready: true }); }
      }).catch(function () { els.list.innerHTML = '<p class="muted small" style="padding:10px">' + esc(t("loadError")) + "</p>"; });
    };
    start();  /* eager: meta.json and one probe file are small, and a late render would shift the anchors below */
  }

  U.explorer = { open: open };
  document.addEventListener("DOMContentLoaded", init);
})();
