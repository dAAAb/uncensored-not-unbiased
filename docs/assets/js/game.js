/* Game: "Guess the model" (main mode) and "Will it say yes?" (variant). Rounds come from data/game.json,
   built from the real outputs by site/build_game.py. */
(function () {
  "use strict";
  var U = window.UNU, t = U.t, esc = U.esc, S = U.SCRIPTS;
  var N = 10, MAIN = ["bo", "ba", "qo", "qa"], FAMILY = { bo: "bolt", ba: "bolt", qo: "qwen", qa: "qwen" };
  var pool = null, meta = null, root = null;
  var st = { mode: "guess", rounds: [], i: 0, score: 0, marks: [], answered: null, showFull: false };

  function shuffle(a) {
    a = a.slice();
    for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var x = a[i]; a[i] = a[j]; a[j] = x; }
    return a;
  }
  function L() { return U.lang(); }
  function mname(id) { var m = meta && meta.models.filter(function (x) { return x.id === id; })[0]; return m ? m.name[L()] : id; }
  function maxScore() { return st.mode === "guess" ? N * 2 : N; }

  function pickGuess() {
    var bySign = {};
    pool.guess.forEach(function (r) { (bySign[r.sign] = bySign[r.sign] || []).push(r); });
    var ans = shuffle(Object.keys(bySign).filter(function (s) { return bySign[s][0].type === "answer"; }));
    var py = shuffle(Object.keys(bySign).filter(function (s) { return bySign[s][0].type === "pyes"; }));
    var signs = ans.slice(0, N - 3).concat(py.slice(0, 3));
    var used = {}, out = [];
    signs.forEach(function (s) {
      var c = shuffle(bySign[s]).filter(function (r) { return !used[r.key]; })[0] || shuffle(bySign[s])[0];
      used[c.key] = 1;
      out.push(c);
    });
    return shuffle(out).slice(0, N);
  }

  function pickPredict() {
    var used = {}, out = [], models = {};
    shuffle(pool.predict).forEach(function (r) {
      if (out.length >= N || used[r.key]) return;
      if ((models[r.model] || 0) >= 3) return;
      used[r.key] = 1; models[r.model] = (models[r.model] || 0) + 1;
      out.push(r);
    });
    return out;
  }

  function start(mode) {
    st.mode = mode || st.mode;
    st.rounds = st.mode === "guess" ? pickGuess() : pickPredict();
    st.i = 0; st.score = 0; st.marks = []; st.answered = null; st.showFull = false;
    render(true);
  }

  /* ── views ──────────────────────────────────────────────────────────────── */
  function tabs() {
    return '<div class="gtabs"><div class="seg" role="group" aria-label="mode">' + ["guess", "predict"].map(function (m) {
      return '<button type="button" data-g="mode" data-m="' + m + '" aria-pressed="' + (st.mode === m) + '">' + esc(t("game.mode." + m)) + "</button>";
    }).join("") + "</div></div>";
  }

  function intro() {
    return tabs() + '<p class="gintro">' + esc(t("game.intro." + st.mode)) + '</p><p style="text-align:center"><button type="button" class="btn" data-g="start">' +
      esc(t("game.start")) + "</button></p>";
  }

  function status() {
    return '<div class="gstatus"><span>' + esc(t("game.round", { i: st.i + 1, n: st.rounds.length })) + "</span><span>" +
      esc(t("game.score", { s: st.score, max: maxScore() })) + '</span></div><div class="gprog" aria-hidden="true"><span style="width:' +
      (st.i / st.rounds.length * 100) + '%"></span></div>';
  }

  function langAttr(s) { return s === "en" ? "en" : s === "zh_cn" ? "zh-Hans" : "zh-Hant"; }

  function bars(values, side) {
    return '<div class="gbars">' + S.map(function (s, i) {
      var v = values[i];
      return '<div class="gbar"><span>' + esc(t("script." + s)) + '</span><span class="bt"><span class="half"></span><span class="bf ' +
        (side === "con" ? "con" : "pro") + '" style="width:' + (v == null ? 0 : v * 100).toFixed(1) + '%"></span></span><span class="val">' +
        U.fmtP(v) + "</span></div>";
    }).join("") + "</div>";
  }

  function allTable(values, hitRun) {
    return '<table class="gtable"><thead><tr><th>' + esc(t("ex.model")) + "</th>" + S.map(function (s) {
      return '<th class="num">' + esc(t("script." + s)) + "</th>";
    }).join("") + "</tr></thead><tbody>" + MAIN.map(function (r) {
      return "<tr" + (r === hitRun ? ' class="hit"' : "") + "><td>" + esc(mname(r)) + "</td>" + (values[r] || []).map(function (v) {
        return '<td class="num">' + U.fmtP(v) + "</td>";
      }).join("") + "</tr>";
    }).join("") + "</tbody></table>";
  }

  function stmtText(r) {
    var s = r.statement;
    return typeof s === "string" ? s : (L() === "en" ? s.en : s.zh_tw);
  }

  function choicesGuess(r) {
    var a = st.answered;
    var btn = function (val, label, sub) {
      var cls = "";
      if (a) {
        var correct = r.ask === "family" ? val === FAMILY[r.answer] : val === r.answer;
        if (correct) cls = "correct"; else if (val === a.pick) cls = "wrongpick";
      }
      return '<button type="button" data-g="pick" data-v="' + val + '" class="' + cls + '"' + (a ? " disabled" : "") + ">" + esc(label) +
        (sub ? "<small>" + esc(sub) + "</small>" : "") + "</button>";
    };
    if (r.ask === "family") {
      return '<div class="gchoices">' + btn("bolt", t("game.family.bolt"), "NVIDIA") + btn("qwen", t("game.family.qwen"), L() === "en" ? "Qwen team (Alibaba)" : "阿里巴巴 Qwen 團隊") + "</div>";
    }
    return '<div class="gchoices">' + MAIN.map(function (m) { return btn(m, mname(m)); }).join("") + "</div>";
  }

  function roundGuess(r) {
    var h = status();
    if (r.type === "answer") {
      h += '<h3 class="gq" tabindex="-1" id="gq">' + esc(t("game.qAnswer")) + "</h3>";
      h += '<div class="gbox"><div class="lbl">' + esc(t("game.prompt")) + " · " + esc(t("script." + r.script)) + '</div><div lang="' + langAttr(r.script) + '">' + esc(r.prompt) + "</div></div>";
      var showOrig = st.answered && r.masked;
      var body = st.showFull && r.full ? r.full : r.text;
      if (showOrig) body = st.showFull ? r.orig : r.orig_text;
      h += '<div class="gbox"><div class="lbl">' + esc(t("game.answer")) + '</div><blockquote class="gquote" lang="' + (r.script === "en" ? "en" : "zh") + '">' +
        esc(body) + "</blockquote>" + (r.more ? '<p style="margin:8px 0 0"><button type="button" class="linkbtn" data-g="full">' +
        esc(t(st.showFull ? "game.hideFull" : "game.showFull")) + "</button></p>" : "") + "</div>";
      if (r.masked && !st.answered) h += '<p class="note">' + esc(t("game.redacted")) + "</p>";
    } else {
      h += '<h3 class="gq" tabindex="-1" id="gq">' + esc(t("game.qPyes")) + "</h3>";
      h += '<div class="gbox"><div class="lbl">' + esc(t(r.direct ? "ex.question" : "game.statement")) + "</div><div>" + esc(stmtText(r)) + "</div>" +
        bars(r.values[r.answer], r.side) + '<p class="note" style="margin:0">' + esc(t("game.pyesNote")) + "</p></div>";
    }
    if (r.ask === "family" && !st.answered) h += '<p class="note box">' + esc(t("game.familyOnly")) + "</p>";
    h += choicesGuess(r);
    if (st.answered) h += revealGuess(r);
    return h;
  }

  function revealGuess(r) {
    var a = st.answered;
    var cls = a.points === 2 ? "ok" : a.points === 1 ? "half" : "bad";
    var head = a.points === 2 ? t("game.right") : a.points === 1 ? t("game.half") : t("game.wrong");
    var h = '<div class="greveal ' + cls + '" role="status"><h4 tabindex="-1" id="greveal">' + esc(head) + "</h4>";
    h += "<p><strong>" + esc(t("game.itWas", { m: mname(r.answer) })) + "</strong></p>";
    h += '<p><span class="badge info">' + esc(t("game.tell")) + "</span> " + esc(r.explain[L()]) + "</p>";
    if (r.type === "pyes") h += '<p class="small muted" style="margin:6px 0 0">' + esc(t("game.allModels")) + "</p>" + allTable(r.values, r.answer);
    var link = "#q=" + encodeURIComponent(r.key) + (r.type === "answer" ? "&m=" + r.answer : "");
    h += '<div class="gactions"><a class="btn ghost" href="' + link + '">' + esc(t("game.seeExplorer")) + '</a><button type="button" class="btn" data-g="next">' +
      esc(t(st.i + 1 >= st.rounds.length ? "game.finish" : "game.next")) + "</button></div></div>";
    return h;
  }

  function roundPredict(r) {
    var h = status();
    var q = t(r.direct ? "game.predictQDirect" : "game.predictQ", { m: mname(r.model), s: t("script." + r.script) });
    h += '<h3 class="gq" tabindex="-1" id="gq">' + esc(q) + "</h3>";
    h += '<div class="gbox"><div class="lbl">' + esc(r.c92 ? t("game.c92") : t(r.direct ? "ex.question" : "game.statement")) + " · " + esc(t("script." + r.script)) +
      '</div><div lang="' + langAttr(r.script) + '" style="font-size:1.08rem">' + esc(r.statement) + "</div></div>";
    var a = st.answered;
    var truth = r.p > 0.5 ? "yes" : "no";
    var btn = function (v) {
      var cls = a ? (v === truth ? "correct" : (v === a.pick ? "wrongpick" : "")) : "";
      return '<button type="button" data-g="pick" data-v="' + v + '" class="' + cls + '"' + (a ? " disabled" : "") + ">" + esc(t("game." + v)) + "</button>";
    };
    h += '<div class="gchoices">' + btn("yes") + btn("no") + "</div>";
    if (a) {
      h += '<div class="greveal ' + (a.points ? "ok" : "bad") + '" role="status"><h4 tabindex="-1" id="greveal">' + esc(t(a.points ? "game.predictRight" : "game.predictWrong")) +
        " " + esc(t("game.truth", { p: U.fmtP(r.p) })) + "</h4>";
      h += '<p class="small muted" style="margin:4px 0 0">' + esc(t("game.otherScripts")) + "</p>" + bars(r.values[r.model], r.side === "con" || r.side === "prc" ? "con" : "pro");
      h += '<p class="small muted" style="margin:6px 0 0">' + esc(t("game.allModels")) + "</p>" + allTable(r.values, r.model);
      h += '<div class="gactions"><a class="btn ghost" href="#q=' + encodeURIComponent(r.key) + '">' + esc(t("game.seeExplorer")) +
        '</a><button type="button" class="btn" data-g="next">' + esc(t(st.i + 1 >= st.rounds.length ? "game.finish" : "game.next")) + "</button></div></div>";
    }
    return h;
  }

  function grid() {
    return st.marks.map(function (m) { return st.mode === "guess" ? (m === 2 ? "●" : m === 1 ? "◐" : "○") : (m ? "●" : "○"); }).join("");
  }

  function shareText() {
    var key = st.mode === "guess" ? "game.shareText" : "game.shareTextPredict";
    return t(key, { s: st.score, max: maxScore(), grid: grid() });
  }
  function shareUrl() {
    return (window.UNU_CONFIG.siteUrl || location.href.split("#")[0]) + (L() === "en" ? "?lang=en" : "") + "#game";
  }

  function endView() {
    var text = shareText(), url = shareUrl();
    var h = tabs() + '<div class="gend"><p class="kicker">' + esc(t("game.end")) + '</p><div class="big" tabindex="-1" id="gq">' +
      esc(t("game.endScore", { s: st.score, max: maxScore() })) + '</div><div class="grid" aria-hidden="true">' + grid() + "</div>" +
      (st.mode === "guess" ? '<p class="small muted">' + esc(t("game.gridLegend")) + "</p>" : "") +
      '<div class="sharebox">' + esc(text) + "\n" + esc(url) + "</div>" +
      '<div class="gactions" style="justify-content:center">' +
      '<button type="button" class="btn ghost" data-g="copy">' + esc(t("game.copyResult")) + "</button>" +
      (navigator.share ? '<button type="button" class="btn ghost" data-g="share">' + esc(t("game.share")) + "</button>" : "") +
      '<a class="btn ghost" target="_blank" rel="noopener" href="https://twitter.com/intent/tweet?text=' + encodeURIComponent(text) + "&url=" + encodeURIComponent(url) + '">' +
      esc(t("game.shareX")) + "</a>" +
      '<button type="button" class="btn" data-g="again">' + esc(t("game.again")) + "</button></div></div>";
    return h;
  }

  function render(focus) {
    if (!root || !pool) return;
    var h;
    if (!st.rounds.length) h = intro();
    else if (st.i >= st.rounds.length) h = endView();
    else {
      var r = st.rounds[st.i];
      h = tabs() + (st.mode === "guess" ? roundGuess(r) : roundPredict(r));
    }
    root.innerHTML = h;
    if (focus) {
      var f = root.querySelector(focus === "reveal" ? "#greveal" : "#gq");
      if (f) try { f.focus({ preventScroll: focus !== "reveal" ? false : true }); } catch (e) { f.focus(); }
    }
  }

  function pick(v) {
    if (st.answered) return;
    var r = st.rounds[st.i], pts;
    if (st.mode === "guess") {
      if (r.ask === "family") pts = v === FAMILY[r.answer] ? 2 : 0;
      else pts = v === r.answer ? 2 : (FAMILY[v] === FAMILY[r.answer] ? 1 : 0);
    } else {
      pts = (v === "yes") === (r.p > 0.5) ? 1 : 0;
    }
    st.answered = { pick: v, points: pts };
    st.score += pts;
    st.marks.push(pts);
    render("reveal");
    var rv = document.getElementById("greveal");
    if (rv && rv.getBoundingClientRect().bottom > window.innerHeight) rv.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  function onClick(e) {
    var b = e.target.closest("[data-g]");
    if (!b) return;
    var g = b.getAttribute("data-g");
    if (g === "mode") {
      var m = b.getAttribute("data-m");
      if (m !== st.mode) { st.mode = m; st.rounds = []; render(); }
    } else if (g === "start" || g === "again") start();
    else if (g === "pick") pick(b.getAttribute("data-v"));
    else if (g === "full") { st.showFull = !st.showFull; render(); }
    else if (g === "next") {
      st.i++; st.answered = null; st.showFull = false; render(true);
      var top = root.getBoundingClientRect().top;
      if (top < 0) root.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (g === "copy") U.copyText(shareText() + "\n" + shareUrl());
    else if (g === "share") navigator.share({ title: document.title, text: shareText(), url: shareUrl() }).catch(function () {});
  }

  function init() {
    root = document.getElementById("game-root");
    if (!root) return;
    root.addEventListener("click", onClick);
    var go = function () {
      Promise.all([U.fetchJSON("data/game.json"), U.fetchJSON("data/meta.json")]).then(function (r) {
        pool = r[0]; meta = r[1];
        render();
      }).catch(function () { root.innerHTML = '<p class="muted">' + esc(t("loadError")) + "</p>"; });
    };
    go();
    document.addEventListener("unu:lang", function () { render(); });
  }

  document.addEventListener("DOMContentLoaded", init);
})();
