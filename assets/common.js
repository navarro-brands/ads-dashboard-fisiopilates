/* Utilidades compartidas por las tres páginas del Centro de Comando. Requiere assets/data.js (DATA). */
const NF = new Intl.NumberFormat('es-CO');
const COP = n => (n == null ? '—' : NF.format(Math.round(n)));
const money = n => (n == null || !isFinite(n) ? '—' : '<span class="cur">COP</span>' + COP(n));
const K = n => n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : String(n);
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

const PAGES = [
  { href: 'index.html',       cls: 'both', label: 'Resumen comparativo' },
  { href: 'tradicional.html', cls: 'trad', label: 'Pauta tradicional' },
  { href: 'nbb.html',         cls: 'nbb',  label: 'Estrategia NBB' },
];
function renderNav(active) {
  const el = document.getElementById('topnav'); if (!el) return;
  el.innerHTML = PAGES.map(p => `<a href="${p.href}" class="${p.cls}${p.href === active ? ' on' : ''}"><span class="sw"></span>${p.label}</a>`).join('')
    + `<span class="spacer"></span><span class="upd">Datos al ${fmtDate(DATA.weeks[DATA.weeks.length - 1].end)}</span>`;
}
function fmtDate(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'][m - 1]} ${y}`;
}
function weekLabel(id) { const w = DATA.weeks.find(w => w.id === id); return w ? w.label : id; }

/* ───────── Deltas ───────── */
function pct(now, prev) { if (prev === 0 || prev == null || now == null) return null; return (now / prev - 1) * 100; }
function deltaHTML(now, prev, lowerIsBetter, suffix) {
  const d = pct(now, prev); if (d === null) return '';
  const good = lowerIsBetter ? d < 0 : d > 0;
  const cls = Math.abs(d) < 1 ? 'flat' : (good ? 'up' : 'down');
  const arrow = Math.abs(d) < 1 ? '→' : (d > 0 ? '▲' : '▼');
  return `<span class="delta ${cls}">${arrow} ${Math.abs(d).toFixed(1)}% ${suffix || 'vs sem. previa'}</span>`;
}
function fDelta(v, lower) {
  if (v === null || v === undefined || !isFinite(v)) return '<b class="flat">—</b>';
  const good = lower ? v < 0 : v > 0;
  const cls = Math.abs(v) < 1 ? 'flat' : (good ? 'up' : 'down');
  return `<b class="${cls}">${v > 0 ? '+' : ''}${v.toFixed(0)}%</b>`;
}

/* ───────── KPIs ───────── */
function kpiHTML(list, variant) {
  return list.map(k => `
    <div class="kpi ${variant || ''} ${k.star ? 'star' : ''}"><div class="label">${k.label}</div>
    <div class="val ${k.pending ? 'pending' : ''}">${k.val}</div><div class="foot">${k.foot || ''}</div>
    ${k.tag ? `<span class="tag">${k.tag}</span>` : ''}${k.delta || ''}</div>`).join('');
}
function reachKPI(t, prev, tagText) {
  if (t.reach == null) return { label: 'Alcance', val: 'pendiente<br>Meta Informes', pending: true, foot: 'alcance deduplicado no cargado', tag: tagText };
  return { label: 'Alcance', val: COP(t.reach), foot: 'personas únicas · frec. ' + t.freq, tag: tagText,
           delta: prev && prev.reach != null ? deltaHTML(t.reach, prev.reach, false) : '' };
}
function standardKPIs(t, prev, unitsFoot) {
  return [
    { label: 'Inversión total', val: money(t.spend), foot: unitsFoot, delta: prev ? deltaHTML(t.spend, prev.spend, false) : '' },
    { label: 'Conversaciones WA', val: COP(t.conv), foot: money(t.cpconv) + ' por conversación', star: true, delta: prev ? deltaHTML(t.conv, prev.conv, false) : '' },
    reachKPI(t, prev, 'Informes de Meta'),
    { label: 'Clics en el enlace', val: COP(t.clicks), foot: t.ctr + '% CTR', delta: prev ? deltaHTML(t.clicks, prev.clicks, false) : '' },
    { label: 'CPC promedio', val: money(t.cpc), foot: 'costo por clic', delta: prev ? deltaHTML(t.cpc, prev.cpc, true) : '' },
    { label: 'Costo / conversación', val: money(t.cpconv), foot: 'métrica principal', star: true, delta: prev ? deltaHTML(t.cpconv, prev.cpconv, true) : '' },
  ];
}

/* ───────── Toggle de período y tabs ───────── */
function buildPeriodToggle(el, periods, cur, onChange, variant) {
  el.innerHTML = periods.map(p => `<button data-p="${p.id}" class="${p.id === cur ? 'on ' + (variant || '') : ''}">${p.label}</button>`).join('');
  el.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    el.querySelectorAll('button').forEach(x => x.className = '');
    b.className = 'on ' + (variant || '');
    onChange(b.dataset.p);
  });
}
function bindTabs(el, prefix) {
  el.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    el.querySelectorAll('button').forEach(x => x.classList.remove('on')); b.classList.add('on');
    el.querySelectorAll('button').forEach(x => document.getElementById(prefix + x.dataset.v).classList.toggle('hidden', x !== b));
  });
}

/* ───────── Semáforo de urgencia ───────── */
function scoreUnit(c, avg, opts) {
  opts = opts || {};
  let score = 0; const reasons = [];
  if (!c.conv) { score += 3; reasons.push(['bad', 'Sin conversaciones en el período']); }
  else {
    const ratio = c.cpconv / avg;
    if (ratio >= 1.6) { score += 3; reasons.push(['bad', `Costo por conversación ${Math.round((ratio - 1) * 100)}% sobre el promedio`]); }
    else if (ratio >= 1.2) { score += 2; reasons.push(['warn', 'Costo por conversación por encima del promedio']); }
    else if (ratio <= 0.8) { reasons.push(['good', `Costo por conversación ${Math.round((1 - ratio) * 100)}% bajo el promedio`]); }
  }
  if (c.below_q > 0) { score += Math.min(c.below_q, 3); reasons.push(['warn', `${c.below_q} anuncio(s) con calidad por debajo del promedio`]); }
  if (c.below_cvr > 0) { score += 1; reasons.push(['warn', `${c.below_cvr} anuncio(s) con conversión débil`]); }
  if (c.freq >= 1.8) { score += 1; reasons.push(['warn', `Frecuencia alta (${c.freq}) — posible fatiga`]); }
  if (!opts.skipSets && c.sets > 1) { reasons.push(['info', `${c.sets} conjuntos — revisar solapamiento de público`]); }
  const minConv = opts.minConv == null ? 20 : opts.minConv;
  if (c.conv && c.conv < minConv) { score += 1; reasons.push(['warn', `Volumen bajo de conversaciones (${c.conv})`]); }
  return { score, level: score >= 4 ? 'r' : score >= 2 ? 'y' : 'g', reasons };
}
function applyScores(list, avg, opts) {
  list.forEach(c => { const s = scoreUnit(c, avg, opts); c._score = s.score; c._level = s.level; c._reasons = s.reasons; });
  return [...list].sort((a, b) => b._score - a._score || b.spend - a.spend);
}
function levelText(l) { return l === 'r' ? 'ACTUAR YA' : l === 'y' ? 'VIGILAR' : 'ESTABLE'; }
function alertCount(list) {
  const r = list.filter(c => c._level === 'r').length, y = list.filter(c => c._level === 'y').length;
  return `${r} actuar ya · ${y} vigilar · ${list.length - r - y} estables`;
}
function freqColor(f) { return f >= 1.8 ? 'var(--red)' : f >= 1.5 ? 'var(--yellow)' : 'var(--teal)'; }
function adviceFor(c, unitWord) {
  const r = c._reasons.find(x => x[0] === 'bad') || c._reasons.find(x => x[0] === 'warn') || c._reasons.find(x => x[0] === 'good') || c._reasons[0];
  const icon = c._level === 'r' ? '🔴' : c._level === 'y' ? '🟡' : '🟢';
  let msg;
  if (c._level === 'r') msg = `<b>Actuar ya.</b> ${r ? r[1] : ''}. Revisa creativos y segmentación de ${unitWord}.`;
  else if (c._level === 'y') msg = `<b>Vigilar.</b> ${r ? r[1] : ''}. Margen de optimización en creativo o público.`;
  else msg = `<b>Estable.</b> ${r ? r[1] : 'Rinde en línea o mejor que el promedio'}. Mantener y usar como referencia.`;
  return [icon, msg];
}

/* ───────── Tarjetas ───────── */
function cmpRow(c, prev, variant) {
  if (!prev) return '';
  const dc = pct(c.conv, prev.conv), dk = pct(c.cpconv, prev.cpconv);
  return `<div class="cmp"><span>vs sem. previa:</span> <span>conv ${fDelta(dc, false)}</span> <span>costo/conv ${fDelta(dk, true)}</span></div>`;
}
/* Tarjeta de unidad (campaña/sede tradicional, sede NBB, conjunto NBB). */
function unitCardHTML(c, o) {
  const fpct = Math.min(c.freq / 2.5 * 100, 100);
  const adv = adviceFor(c, o.unitWord || 'esta sede');
  return `<div class="card ${c._level} ${o.variant || ''}">
    <div class="top"><div><div class="acct">${o.eyebrow}</div><div class="cname">${esc(o.title)}</div>${o.sub ? `<div class="single-note">${o.sub}</div>` : ''}</div>
    <div class="badges"><span class="pill ${c._level}">${levelText(c._level)}</span>${o.badge || ''}${c.sets > 1 && !o.hideSets ? `<span class="pill y">${c.sets} CONJUNTOS</span>` : ''}</div></div>
    <div class="hero-metric"><span class="big">${c.conv}</span><span class="cap">conversaciones<br>WhatsApp</span>
    <span class="cost"><b>${c.conv ? money(c.cpconv) : '—'}</b><span>por conversación</span></span></div>
    ${cmpRow(c, o.prev)}
    <div class="stats">
      <div class="stat"><div class="k">Inversión</div><div class="v">${money(c.spend)}</div></div>
      <div class="stat"><div class="k">CTR</div><div class="v">${c.ctr}%</div></div>
      <div class="stat"><div class="k">CPC</div><div class="v">${money(c.cpc)}</div></div>
      <div class="stat"><div class="k">Alcance</div><div class="v">${COP(c.reach)}<span class="ap">aprox.</span></div></div>
      <div class="stat"><div class="k">Impres.</div><div class="v">${COP(c.imp)}</div></div>
      <div class="stat"><div class="k">Clics</div><div class="v">${c.clicks}</div></div>
    </div>
    <div class="freqrow"><div class="flabel"><span>Frecuencia (aprox.)</span><span>${c.freq}</span></div>
    <div class="fbar"><i style="width:${fpct}%;background:${freqColor(c.freq)}"></i></div></div>
    ${o.extra || ''}
    <div class="advice"><span class="dot">${adv[0]}</span><span>${adv[1]}</span></div>
  </div>`;
}
/* Tarjeta de anuncio con desglose por parte (campaña/sede o audiencia). */
function adCardHTML(a, o) {
  o = o || {};
  const multi = a.campaigns > 1;
  const partName = p => o.partName ? o.partName(p) : p.sede;
  let breakdown;
  if (multi) {
    breakdown = `<div class="breakdown"><div class="bh">${o.breakdownTitle ? o.breakdownTitle(a) : `Detalle por campaña (${a.campaigns} sedes)`}</div>` +
      a.parts.map(p => `<div class="brow">
        <div><div class="bsede">${esc(partName(p))}</div><div class="bsub">${money(p.spend)} · ${p.clicks} clics · CTR ${p.ctr}%</div></div>
        <div class="bconv ${o.variant || ''}">${p.conv}<div class="bsub" style="color:var(--faint)">conv</div></div>
        <div class="bcost">${p.conv ? money(p.cpconv) : '—'}<div class="bsub">c/conv</div></div>
      </div>`).join('') + `</div>`;
  } else {
    breakdown = `<div class="single-note">${o.singleLabel || 'Campaña'}: ${esc(partName(a.parts[0]))}</div>`;
  }
  const prev = o.prev;
  return `<div class="adcard ${o.variant || ''}">
    <div class="atop"><div class="aname">${esc(a.ad)}</div>
    ${multi ? `<span class="pill ${o.variant === 'nbb' ? 'a' : 'y'}">×${a.campaigns} ${o.multiWord || 'SEDES'}</span>` : ''}</div>
    <div class="ameta">${multi ? 'Anuncio compartido' : 'Anuncio único'} · ${money(a.spend)} invertidos</div>
    <div class="adhero"><span class="big">${a.conv}</span><span class="cap">conversaciones<br>WhatsApp</span>
    <span class="cost"><b>${a.conv ? money(a.cpconv) : '—'}</b><span>por conversación</span></span></div>
    ${prev ? cmpRow(a, prev) : ''}
    <div class="stats">
      <div class="stat"><div class="k">CTR</div><div class="v">${a.ctr}%</div></div>
      <div class="stat"><div class="k">CPC</div><div class="v">${money(a.cpc)}</div></div>
      <div class="stat"><div class="k">Clics</div><div class="v">${a.clicks}</div></div>
      <div class="stat"><div class="k">Alcance</div><div class="v">${COP(a.reach)}<span class="ap">aprox.</span></div></div>
      <div class="stat"><div class="k">Impres.</div><div class="v">${COP(a.imp)}</div></div>
      <div class="stat"><div class="k">Inversión</div><div class="v">${K(a.spend)}</div></div>
    </div>
    ${breakdown}
  </div>`;
}

/* ───────── Tendencia ───────── */
/* T: puntos {label, conv, cpconv, ...}; opts.stack: función que devuelve [{cls,conv}] para apilar. */
function renderTrend(el, T, opts) {
  opts = opts || {};
  const maxConv = Math.max(...T.map(t => t.conv), 1);
  el.innerHTML = T.map((t, i) => {
    const prev = i > 0 ? T[i - 1] : null;
    const dConv = prev && prev.conv ? ((t.conv / prev.conv - 1) * 100) : null;
    const dCost = prev && prev.cpconv ? ((t.cpconv / prev.cpconv - 1) * 100) : null;
    const convTag = dConv === null ? '' : `<span style="color:${dConv > 0 ? 'var(--green)' : 'var(--red)'};font-weight:700">${dConv > 0 ? '+' : ''}${dConv.toFixed(0)}%</span>`;
    const costTag = dCost === null ? '' : `<span style="color:${dCost < 0 ? 'var(--green)' : 'var(--red)'};font-weight:700">${dCost > 0 ? '+' : ''}${dCost.toFixed(0)}%</span>`;
    const isLast = i === T.length - 1;
    const H = Math.round(t.conv / maxConv * 70) + 8;
    let bar;
    if (opts.stack) {
      const parts = opts.stack(t).filter(p => p.conv > 0);
      // la cifra va fuera de .stack (overflow:hidden la recortaría)
      bar = `<div style="position:relative;display:flex;justify-content:center;width:100%"><span style="position:absolute;top:-18px;font-family:var(--mono);font-size:13px;font-weight:700;color:var(--ink)">${t.conv}</span>
        <div class="stack" style="height:${H}px">${parts.map(p => `<i class="${p.cls}" style="height:${(p.conv / t.conv * 100).toFixed(1)}%"></i>`).join('')}</div></div>`;
    } else {
      const col = opts.color || 'var(--teal)', colDim = opts.colorDim || 'var(--teal-dim)';
      bar = `<div style="width:60%;max-width:56px;min-width:38px;height:${H}px;background:${isLast ? col : colDim};border-radius:6px 6px 0 0;position:relative">
        <span style="position:absolute;top:-18px;left:50%;transform:translateX(-50%);font-family:var(--mono);font-size:13px;font-weight:700;color:var(--ink)">${t.conv}</span></div>`;
    }
    return `<div class="tbar ${isLast ? 'last' : ''}" style="text-align:center">
      <div style="height:98px;display:flex;align-items:flex-end;justify-content:center;margin-bottom:8px">${bar}</div>
      <div style="font-family:var(--mono);font-size:10px;color:${isLast ? 'var(--ink)' : 'var(--muted)'};margin-bottom:6px">${t.label}</div>
      <div style="font-size:10px;color:var(--faint);line-height:1.5">
        <div>conv ${convTag || '<span style=\'color:var(--faint)\'>base</span>'}</div>
        <div>costo/conv <span class="cur" style="font-size:9px">COP</span>${NF.format(t.cpconv)} ${costTag}</div>
        ${opts.extraLine ? opts.extraLine(t) : ''}
      </div>
    </div>`;
  }).join('');
  if (opts.scrollToEnd !== false) { const sc = el.parentElement; requestAnimationFrame(() => { sc.scrollLeft = sc.scrollWidth; }); }
}

/* ───────── Comentarios del analista ───────── */
function renderComments(el, key) {
  const c = DATA.comments && DATA.comments[key];
  if (!el) return;
  if (!c || !c.paragraphs || !c.paragraphs.length) { el.innerHTML = `<div class="mh">Comentarios del analista</div><p>Sin comentarios para este período.</p>`; return; }
  el.innerHTML = `<div class="mh">Comentarios del analista${c.draft ? '<span class="draft">borrador</span>' : ''}</div>` +
    c.paragraphs.map(p => `<p>${p}</p>`).join('');
}
function stamp() { const g = document.getElementById('genstamp'); if (g) g.textContent = 'Generado ' + fmtDate(DATA.generated); }
