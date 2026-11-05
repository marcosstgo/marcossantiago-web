// Modo Director: pide el plan, lo pinta mientras llega y recolora la página.
(function () {
  var sec = document.getElementById('director'), f = document.getElementById('dr-f'), R = document.getElementById('dr-r'),
      inp = document.getElementById('dr-i'), go = f.querySelector('.dr-b'), cat = null, vivo = 0, ultimo = {};
  var INK = '#0d0c0b', PAPEL = '#f3eee5', WA = 'https://wa.me/17872439670?text=';

  // ── Color: nada de lo que invente el modelo puede dejar la página ilegible ──
  function hex(h) { return /^#[0-9a-f]{6}$/i.test(h || '') ? h : null }
  function lum(h) {
    return [1, 3, 5].map(function (i, k) {
      var c = parseInt(h.substr(i, 2), 16) / 255; c = c <= .03928 ? c / 12.92 : Math.pow((c + .055) / 1.055, 2.4);
      return c * [.2126, .7152, .0722][k];
    }).reduce(function (a, b) { return a + b });
  }
  function ratio(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + .05) / (Math.min(x, y) + .05) }
  function sobre(bg) { return ratio(bg, INK) >= ratio(bg, PAPEL) ? INK : PAPEL }
  function aclara(h) {
    var c = [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16) });
    return '#' + c.map(function (v) { return Math.min(255, Math.round(v + (255 - v) * .12)).toString(16).padStart(2, '0') }).join('');
  }
  function legibleEnTinta(h) { var n = 0; while (ratio(h, INK) < 4.5 && n++ < 24) h = aclara(h); return h }
  function aplicaAcento(h) {
    var a = legibleEnTinta(h), s = document.documentElement.style;
    s.setProperty('--flame', a);
    try { sessionStorage.setItem('ms-acento', a) } catch (e) {}
  }
  function pinta(p) {
    var fo = hex(p.fondo), ac = hex(p.acento);
    if (!fo || !ac) return;
    var tx = sobre(fo), s = sec.style;
    s.setProperty('--d-bg', fo); s.setProperty('--d-tx', tx);
    s.setProperty('--d-ac', ratio(ac, fo) >= 3 ? ac : tx);
    aplicaAcento(ac);
  }

  // ── JSON a medio llegar: se cierra lo abierto; si aún no cuaja, se espera ──
  function parcial(s) {
    var pila = [], enS = false, esc = false;
    for (var i = 0; i < s.length; i++) {
      var c = s[i];
      if (enS) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') enS = false; continue }
      if (c === '"') enS = true; else if (c === '{') pila.push('}'); else if (c === '[') pila.push(']');
      else if (c === '}' || c === ']') pila.pop();
    }
    if (esc) return null;
    var cierre = (enS ? '"' : '') + pila.reverse().join('');
    try { return JSON.parse(s + cierre) } catch (e) { return null }
  }

  // ── Armar el resultado una sola vez y actualizarlo por partes ──
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e }
  var U;
  function arma() {
    R.replaceChildren(); R.hidden = false; U = {};
    U.st = el('p', 'dr-st anda'); R.append(U.st);
    U.ti = el('h3', 'dr-ti'); U.no = el('p', 'dr-no'); R.append(U.ti, U.no);
    var g = el('div', 'dr-g'), a = el('div'), b = el('div');
    U.hTo = el('p', 'dr-h', 'Lo que no puede faltar'); U.to = el('ol', 'dr-to'); a.append(U.hTo, U.to);
    U.hPa = el('p', 'dr-h', 'La paleta'); U.pa = el('div', 'dr-pa'); U.pn = el('p', 'dr-pn');
    U.hPz = el('p', 'dr-h', 'Desde mi lista de precios'); U.hPz.style.marginTop = '28px'; U.pz = el('ul', 'dr-pz');
    b.append(U.hPa, U.pa, U.pn, U.hPz, U.pz);
    g.append(a, b); R.append(g); U.g = g; g.hidden = true;
    U.hTr = el('p', 'dr-h', 'De lo que ya he hecho'); U.hTr.style.marginTop = 'clamp(28px, 4vw, 56px)'; U.hTr.hidden = true;
    U.tr = el('div', 'dr-tr'); R.append(U.hTr, U.tr);
    U.en = el('div', 'dr-en'); U.en.hidden = true;
    U.bu = el('p', 'dr-bu');
    U.wa = el('a', 'dr-wa', 'Enviárselo a Marcos'); U.wa.target = '_blank'; U.wa.rel = 'noopener'; U.wa.dataset.track = 'director-whatsapp';
    U.en.append(U.bu, U.wa); R.append(U.en);
    U.aj = el('div', 'dr-aj'); U.aj.hidden = true; U.aj.append(el('span', '', '¿Le damos otra vuelta?'));
    [['atrevido', 'Más atrevido'], ['sobrio', 'Más sobrio'], ['otra', 'Otra mirada']].forEach(function (x) {
      var b = el('button', '', x[1]); b.type = 'button'; b.dataset.a = x[0]; U.aj.append(b);
    });
    R.append(U.aj);
    U.le = el('p', 'dr-le', 'Esto lo armó una IA (Claude) con mi portafolio y mis precios. Es un punto de partida: la fecha, el alcance y el precio final los hablamos tú y yo.');
    U.le.hidden = true; R.append(U.le);
  }
  function pon(n, t) { if (t != null && n.textContent !== t) n.textContent = t }
  function lista(n, arr, fn) {
    arr.forEach(function (v, i) { var e = n.children[i]; if (e) fn(v, e); else { e = fn(v); if (e) n.append(e) } });
    while (n.children.length > arr.length) n.lastChild.remove();
  }
  function tarjeta(t, porQue) {
    var a = el('a', 'dr-c');
    if (t.v) { a.href = 'https://vimeo.com/' + t.v; a.dataset.video = t.v; a.dataset.title = t.t } else { a.href = t.u }
    a.target = '_blank'; a.rel = 'noopener';
    var im = el('img'); im.src = t.i; im.alt = ''; im.width = 800; im.height = 500; im.decoding = 'async';
    a.append(im, el('strong', '', t.t), el('small', 'dr-pq', porQue || t.c));
    return a;
  }
  function render(o) {
    pon(U.ti, o.titulo); pon(U.no, o.nota);
    if (o.titulo) pon(U.st, '');
    if (o.relevante === false) return;
    var p = o.paleta || {};
    if (hex(p.fondo) && hex(p.acento) && hex(p.apoyo)) {
      if (!U.pa.children.length) [p.fondo, p.acento, p.apoyo].forEach(function (c) {
        var b = el('button'); b.type = 'button'; b.style.background = c; b.setAttribute('aria-label', 'Usar ' + c + ' como color de la página'); b.title = 'Usar este color en la página';
        b.onclick = function () { aplicaAcento(c) }; U.pa.append(b);
      });
      U.g.hidden = false;
    }
    pon(U.pn, p.nombre);
    if (hex(p.fondo) && hex(p.acento)) pinta(p);
    lista(U.to, (o.tomas || []).filter(Boolean), function (v, e) { e = e || el('li'); pon(e, v); return e });
    var trs = (o.trabajos || []).filter(function (x) { return x && cat.trabajos[x.id] }).slice(0, 3);
    U.hTr.hidden = !trs.length;
    trs.forEach(function (x, i) {
      var c = U.tr.children[i];
      if (!c || c.dataset.id !== x.id) { var n = tarjeta(cat.trabajos[x.id], x.por_que); n.dataset.id = x.id; if (c) c.replaceWith(n); else U.tr.append(n) }
      else pon(c.querySelector('.dr-pq'), x.por_que);
    });
    var srv = (o.servicios || []).filter(function (s) { return cat.servicios[s] }).slice(0, 2);
    U.hPz.hidden = !srv.length;
    lista(U.pz, srv, function (s, e) {
      var d = cat.servicios[s]; e = e || el('li'); e.replaceChildren();
      var a = el('a', '', d.n); a.href = d.h; e.append(a, el('span', '', d.p)); return e;
    });
    if (o.mensaje) { pon(U.bu, o.mensaje); U.wa.href = WA + encodeURIComponent(o.mensaje); U.en.hidden = false }
  }
  function falla(t, idea) {
    pon(U.st, t); U.st.classList.remove('anda');
    pon(U.bu, 'Hola Marcos. ' + idea); U.wa.href = WA + encodeURIComponent('Hola Marcos. ' + idea); U.en.hidden = false;
  }

  // ── Pedido ──
  var FRASES = function () { return ['Leyendo tu idea', 'Buscando en ' + cat.nv + ' videos y ' + cat.nb + ' marcas', 'Probando colores', 'Pensando las tomas'] };
  function ocupado(si) { go.disabled = si; R.querySelectorAll('.dr-aj button').forEach(function (b) { b.disabled = si }) }
  async function dirige(ajuste) {
    var idea = inp.value.trim(); if (!idea) { inp.focus(); return }
    var sentir = (f.sentir && f.sentir.value) || '', id = ++vivo;
    ultimo = { idea: idea, sentir: sentir };
    ocupado(true);
    try { cat = cat || await (await fetch('/director-catalogo.json')).json() } catch (e) { cat = { trabajos: {}, servicios: {}, nv: 29, nb: 12 } }
    arma(); R.scrollIntoView();
    var fr = FRASES(), k = 0; pon(U.st, fr[0]);
    var giro = setInterval(function () { if (U.st.textContent) pon(U.st, fr[++k % fr.length]) }, 1800);
    var fin = null, txt = '', t0 = performance.now();
    try {
      var r = await fetch('/api/director', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ idea: idea, sentir: sentir, ajuste: ajuste || '' }) });
      if (!r.ok) {
        var er = await r.json().catch(function () { return {} });
        fin = er.error === 'limite' ? 'limite' : 'error';
      } else {
        var rd = r.body.getReader(), dec = new TextDecoder(), buf = '';
        for (;;) {
          var c = await rd.read(); if (c.done) break;
          buf += dec.decode(c.value, { stream: true });
          var ls = buf.split('\n'); buf = ls.pop();
          for (var i = 0; i < ls.length; i++) {
            if (!ls[i]) continue;
            var m = JSON.parse(ls[i]);
            if (m.t) { txt += m.t; var o = parcial(txt); if (o && id === vivo) render(o) }
            if (m.fin) fin = m.fin;
          }
        }
      }
    } catch (e) { fin = 'error' }
    clearInterval(giro);
    if (id !== vivo) return;
    ocupado(false);
    if (fin === 'ok') {
      var o2 = parcial(txt) || {};
      render(o2); pon(U.st, ''); U.st.classList.remove('anda');
      if (o2.relevante !== false) { U.aj.hidden = false; U.le.hidden = false }
      if (typeof gtag === 'function') gtag('event', 'director_plan', { event_category: 'director', value: Math.round(performance.now() - t0) });
    } else if (fin === 'limite') falla('Ya le diste varias vueltas. Dale un chin de tiempo, o envíame la idea directo.', idea);
    else falla('Ahora mismo no pude armarlo. Tu idea sí me puede llegar directo:', idea);
  }

  // ── Interacción ──
  function mide() { inp.size = Math.max(inp.value.length, inp.placeholder.length) + 1 }
  inp.addEventListener('input', mide); mide();
  document.getElementById('dr-ej').addEventListener('click', function (e) {
    var d = e.target.dataset && e.target.dataset.e; if (d) { inp.value = d; mide(); inp.focus({ preventScroll: true }) }
  });
  f.addEventListener('submit', function (e) { e.preventDefault(); dirige() });
  R.addEventListener('click', function (e) { var a = e.target.dataset && e.target.dataset.a; if (a) dirige(a) });
  R.addEventListener('click', function (e) {
    if (e.target.closest && e.target.closest('.dr-wa') && typeof gtag === 'function') gtag('event', 'whatsapp_click', { event_category: 'contacto', event_label: 'director', page_path: location.pathname });
  });
})();
