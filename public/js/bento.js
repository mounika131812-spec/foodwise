/**
 * Bento analytics — vanilla port of the AnalyticsBento component.
 * Four live cards: waste trend line, pantry inventory waves, category
 * treemap (weekly/monthly/all-time), seasonality radar. Pure SVG,
 * no chart library. Fed by GET /api/analytics -> stats.bento.
 *
 * Public API: ABENTO.render(rootEl, bento, stats)
 */

const ABENTO = (() => {
  'use strict';

  const EASE = (t) => 1 - Math.pow(1 - t, 3);
  const REDUCE = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ARROW =
    '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M6 10.5V1.5M2 5.5l4-4 4 4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const TILE_ICON =
    '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="1" y="1" width="12" height="12" rx="4" fill="currentColor" opacity=".9"/><path d="M7 3.6l1 2.4 2.4 1-2.4 1L7 10.4 6 8 3.6 7 6 6z" fill="var(--tile-bg)"/></svg>';

  let gen = 0;                 // generation guard: invalidates rAF loops & observers
  let ro = null;               // shared ResizeObserver
  let tipEl = null;
  let uid = 0;                 // unique svg gradient ids
  const state = { period: 0, year: 0 };
  let data = null;             // last bento payload
  let root = null;

  /* ---------------- helpers ---------------- */

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const fmt = (n) => (Math.round(n * 10) / 10)
    .toLocaleString('en-US', { maximumFractionDigits: 1 });

  /** smooth path through points (catmull-rom as cubic beziers) */
  function smooth(P) {
    const n = P.length;
    if (n < 2) return '';
    const g = (i) => P[Math.max(0, Math.min(n - 1, i))];
    let d = `M${P[0][0]},${P[0][1]}`;
    for (let i = 0; i < n - 1; i++) {
      const p0 = g(i - 1), p1 = g(i), p2 = g(i + 1), p3 = g(i + 2), k = 0.18;
      d += `C${(p1[0] + (p2[0] - p0[0]) * k).toFixed(2)},${(p1[1] + (p2[1] - p0[1]) * k).toFixed(2)} ` +
           `${(p2[0] - (p3[0] - p1[0]) * k).toFixed(2)},${(p2[1] - (p3[1] - p1[1]) * k).toFixed(2)} ` +
           `${p2[0].toFixed(2)},${p2[1].toFixed(2)}`;
    }
    return d;
  }

  function countUp(el, target, g, prefix = '', suffix = '', duration = 1100) {
    if (!el) return;
    if (REDUCE()) { el.textContent = prefix + fmt(target) + suffix; el._cu = target; return; }
    const from = typeof el._cu === 'number' ? el._cu : 0;
    const t0 = performance.now();
    const step = (now) => {
      if (g !== gen) return;
      const t = Math.min(1, (now - t0) / duration);
      const v = from + (target - from) * EASE(t);
      el._cu = v;
      el.textContent = prefix + fmt(v) + suffix;
      if (t < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function deltaHtml(d) {
    if (!d || d.delta == null) return '';
    const cls = (!d.up ? ' down' : '') + (d.worse ? ' bad' : '');
    return `<span class="ab-delta${cls}" title="vs previous period">${ARROW}${esc(d.delta)}</span>`;
  }

  /* ---------------- tooltip ---------------- */

  function showTip(x, y, { title, rows }) {
    if (!tipEl) {
      tipEl = document.createElement('div');
      tipEl.className = 'ab-tip';
      document.body.appendChild(tipEl);
    }
    tipEl.innerHTML =
      `<div class="h">${esc(title)}</div>` +
      rows.map((r) => `<div class="r"><span>${r.color ? `<i style="background:${r.color}"></i>` : ''}${esc(r.label)}</span><b>${esc(r.value)}</b></div>`).join('');
    tipEl.classList.add('on');
    const rect = tipEl.getBoundingClientRect();
    let l = x + 14, t = y - rect.height - 12;
    if (l + rect.width > window.innerWidth - 8) l = x - rect.width - 14;
    if (t < 8) t = y + 16;
    tipEl.style.left = `${l}px`;
    tipEl.style.top = `${t}px`;
  }
  function hideTip() { if (tipEl) tipEl.classList.remove('on'); }

  /* ---------------- squarified treemap ---------------- */

  function squarify(items, x, y, w, h) {
    const total = items.reduce((a, b) => a + b.v, 0) || 1;
    const scale = (w * h) / total;
    const out = [];
    let rest = items.map((i) => ({ ...i, a: i.v * scale }));
    const worst = (row, len) => {
      const s = row.reduce((a, b) => a + b.a, 0);
      const mx = Math.max(...row.map((r) => r.a));
      const mn = Math.min(...row.map((r) => r.a));
      return Math.max((len * len * mx) / (s * s), (s * s) / (len * len * mn));
    };
    while (rest.length) {
      const len = Math.min(w, h);
      const row = [rest[0]];
      let i = 1;
      while (i < rest.length && worst([...row, rest[i]], len) <= worst(row, len)) row.push(rest[i++]);
      rest = rest.slice(i);
      const s = row.reduce((a, b) => a + b.a, 0);
      if (w >= h) {
        const cw = s / h;
        let cy = y;
        for (const r of row) { const rh = r.a / cw; out.push({ ...r, x, y: cy, w: cw, h: rh }); cy += rh; }
        x += cw; w -= cw;
      } else {
        const rh = s / w;
        let cx = x;
        for (const r of row) { const rw = r.a / rh; out.push({ ...r, x: cx, y, w: rw, h: rh }); cx += rw; }
        y += rh; h -= rh;
      }
    }
    return out;
  }

  /* ---------------- card A: waste trend line ---------------- */

  function drawTrend() {
    const wrap = root.querySelector('#ab-trend-plot');
    if (!wrap) return;
    const W = wrap.clientWidth, H = wrap.clientHeight;
    if (!W || !H) return;
    const trend = data.trend;
    const vals = trend.points.map((p) => p.value);
    const n = vals.length;
    const lo = Math.min(...vals), hi = Math.max(...vals), span = hi - lo || 1;
    const raw = span / 4;
    const mag = Math.pow(10, Math.floor(Math.log10(raw) || 0));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || raw || 1;
    const mn = lo - span * 0.45, mx = hi + span * 0.08;
    const top = 30, bot = 30;
    const Y = (v) => top + (1 - (v - mn) / (mx - mn || 1)) * (H - top - bot);
    const ticks = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) ticks.push(v);
    const xOf = (i) => 14 + (i / (n - 1)) * (W - 66);
    const P = vals.map((v, i) => [xOf(i), Y(v)]);
    const d = smooth(P);
    const last = P[P.length - 1];
    const id = `t${++uid}`;
    const compact = (v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : fmt(v));

    // sparse x-axis labels: first, two middles, last
    const xl = [0, Math.round((n - 1) / 3), Math.round(((n - 1) * 2) / 3), n - 1]
      .filter((v, i, a) => a.indexOf(v) === i);

    wrap.querySelector('svg')?.remove();
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', `Waste over the last 30 days: from ${fmt(vals[0])} to ${fmt(vals[n - 1])} ${data.unit}`);
    svg.innerHTML = `
      <defs>
        <linearGradient id="${id}l" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" style="stop-color:var(--primary)"/>
          <stop offset="1" style="stop-color:var(--accent)"/>
        </linearGradient>
        <linearGradient id="${id}a" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" style="stop-color:var(--accent);stop-opacity:0.2"/>
          <stop offset="1" style="stop-color:var(--accent);stop-opacity:0"/>
        </linearGradient>
        <linearGradient id="${id}m" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stop-color="#fff" stop-opacity="0.15"/>
          <stop offset="1" stop-color="#fff" stop-opacity="1"/>
        </linearGradient>
        <mask id="${id}k"><rect width="${W}" height="${H}" fill="url(#${id}m)"/></mask>
      </defs>
      ${ticks.map((v) => `
        <g>
          <line x1="0" x2="${W}" y1="${Y(v)}" y2="${Y(v)}" class="ab-grid-line"/>
          <text x="${W - 8}" y="${Y(v) - 5}" text-anchor="end" font-size="10" class="ab-tick">${compact(v)}</text>
        </g>`).join('')}
      ${xl.map((i) => `<text x="${Math.min(W - 34, Math.max(14, xOf(i)))}" y="${H - 8}" text-anchor="middle" font-size="9.5" class="ab-tick">${esc(trend.points[i].label)}</text>`).join('')}
      <path d="${d}L${last[0]},${H}L${P[0][0]},${H}Z" fill="url(#${id}a)" mask="url(#${id}k)"/>
      <path class="ab-line" d="${d}" pathLength="1" fill="none" stroke="url(#${id}l)" stroke-width="2.5" stroke-linecap="round"/>
      <circle class="ab-end" cx="${last[0]}" cy="${last[1]}" r="4.5" style="fill:var(--accent)" stroke="var(--card-solid)" stroke-width="2"/>
      <g class="ab-hover" style="display:none">
        <line y1="0" y2="${H}" class="ab-guide"/>
        <circle r="4.5" style="fill:var(--accent)" stroke="var(--card-solid)" stroke-width="2"/>
      </g>
      <rect width="${W}" height="${H}" fill="transparent"/>`;
    wrap.appendChild(svg);

    // draw-in
    const line = svg.querySelector('.ab-line');
    if (!REDUCE()) {
      line.style.strokeDasharray = '1';
      line.style.strokeDashoffset = '1';
      requestAnimationFrame(() => requestAnimationFrame(() => {
        line.style.transition = 'stroke-dashoffset 1.4s cubic-bezier(.3,.8,.2,1) .2s';
        line.style.strokeDashoffset = '0';
      }));
    }

    const hover = svg.querySelector('.ab-hover');
    const hl = hover.querySelector('line'), hc = hover.querySelector('circle');
    svg.querySelector('rect').addEventListener('pointermove', (e) => {
      const r = svg.getBoundingClientRect();
      const i = Math.max(0, Math.min(n - 1, Math.round(((e.clientX - r.left - 14) / (W - 66)) * (n - 1))));
      hl.setAttribute('x1', P[i][0]); hl.setAttribute('x2', P[i][0]);
      hc.setAttribute('cx', P[i][0]); hc.setAttribute('cy', P[i][1]);
      hover.style.display = '';
      showTip(r.left + P[i][0], r.top + P[i][1], {
        title: trend.points[i].label,
        rows: [{ label: `Wasted (${data.unit})`, value: fmt(vals[i]), color: 'var(--accent)' }],
      });
    });
    svg.querySelector('rect').addEventListener('pointerleave', () => { hover.style.display = 'none'; hideTip(); });
  }

  /* ---------------- card B: inventory waves ---------------- */

  function drawWaves() {
    const wrap = root.querySelector('#ab-waves-plot');
    if (!wrap) return;
    const W = wrap.clientWidth, H = wrap.clientHeight;
    if (!W || !H) return;
    const inv = data.inventory;
    const n = inv.inDate.length;
    const max = Math.max(1, ...inv.inDate, ...inv.past, ...inv.inDatePrev, ...inv.pastPrev);
    const pad = 18, mid = H / 2, amp = H / 2 - 16;
    const X = (i) => pad + 6 + (i / (n - 1)) * (W - 2 * pad - 12);
    const id = `w${++uid}`;
    const sets = [
      { a: inv.inDate, dir: -1, op: 1, g: 'd' },
      { a: inv.inDatePrev, dir: -1, op: 0.4, g: 'd' },
      { a: inv.past, dir: 1, op: 1, g: 'm' },
      { a: inv.pastPrev, dir: 1, op: 0.4, g: 'm' },
    ];

    wrap.querySelector('svg')?.remove();
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', 'Pantry items in date vs past expiry, by day, with the prior two weeks behind');
    svg.innerHTML = `
      <defs>
        <linearGradient id="${id}d" x1="0" x2="1" y1="0" y2="0">
          <stop offset=".1" style="stop-color:#34d399"/><stop offset=".9" style="stop-color:var(--primary)"/>
        </linearGradient>
        <linearGradient id="${id}m" x1="0" x2="1" y1="0" y2="0">
          <stop offset=".15" style="stop-color:var(--warning)"/><stop offset=".85" style="stop-color:var(--danger)"/>
        </linearGradient>
      </defs>
      ${Array.from({ length: 7 }, (_, i) => 10 + ((H - 20) * i) / 6).map((y) => `
        <g stroke="color-mix(in srgb, var(--ab-mut) 45%, transparent)" stroke-width="1">
          <line x1="8" x2="13" y1="${y}" y2="${y}"/><line x1="${W - 13}" x2="${W - 8}" y1="${y}" y2="${y}"/>
        </g>`).join('')}
      <line x1="${pad + 6}" x2="${W - pad - 6}" y1="${mid}" y2="${mid}" class="ab-grid-line"/>
      ${sets.map((s, j) => `<path class="ab-wave" data-j="${j}" fill="none" stroke="url(#${id}${s.g})" stroke-width="${s.op === 1 ? 2.5 : 1.5}" stroke-linecap="round" opacity="${s.op}"/>`).join('')}
      <line class="ab-wave-guide" y1="4" y2="${H - 4}" style="display:none" stroke="color-mix(in srgb, var(--ab-mut) 60%, transparent)" stroke-width="1"/>
      <rect width="${W}" height="${H}" fill="transparent"/>`;
    wrap.appendChild(svg);

    const paths = Array.from(svg.querySelectorAll('.ab-wave'), (el) => ({
      el, set: sets[+el.dataset.j],
    }));
    const g = gen;
    const t0 = performance.now();
    const frame = (now) => {
      // Stop when re-rendered, detached, or when the view is hidden —
      // navigating back re-renders and restarts the loop.
      if (g !== gen || !svg.isConnected || !wrap.offsetParent) return;
      const t = (now - t0) / 1000;
      const grow = REDUCE() ? 1 : EASE(Math.min(1, t / 1.3));
      for (const { el, set } of paths) {
        const breathe = REDUCE() ? 1 : 1 + Math.sin(t * 1.2 + (set.dir * (set.op === 1 ? 0 : 1)) * 0.9) * 0.035;
        const P = set.a.map((v, i) => [X(i), mid + set.dir * (3 + (v / max) * amp * grow * breathe)]);
        el.setAttribute('d', smooth(P));
      }
      if (!REDUCE()) requestAnimationFrame(frame);
    };
    requestAnimationFrame(frame);

    const guide = svg.querySelector('.ab-wave-guide');
    svg.querySelector('rect').addEventListener('pointermove', (e) => {
      const r = svg.getBoundingClientRect();
      const i = Math.max(0, Math.min(n - 1, Math.round(((e.clientX - r.left - pad - 6) / (W - 2 * pad - 12)) * (n - 1))));
      guide.setAttribute('x1', X(i)); guide.setAttribute('x2', X(i));
      guide.style.display = '';
      showTip(r.left + X(i), r.top + 12, {
        title: `${inv.labels[i]} · this fortnight`,
        rows: [
          { label: 'In date', value: `${inv.inDate[i]} items`, color: '#34d399' },
          { label: 'Past expiry', value: `${inv.past[i]} items`, color: 'var(--danger)' },
        ],
      });
    });
    svg.querySelector('rect').addEventListener('pointerleave', () => { guide.style.display = 'none'; hideTip(); });
  }

  /* ---------------- card C: treemap ---------------- */

  function drawTreemap() {
    const wrap = root.querySelector('#ab-treemap');
    if (!wrap) return;
    const cats = data.categories;
    const period = state.period;
    const items = cats.items
      .map((i) => ({ name: i.name, group: i.group, v: i.values[period] ?? 0 }))
      .filter((i) => i.v > 0)
      .sort((a, b) => b.v - a.v);
    const total = items.reduce((a, b) => a + b.v, 0);

    if (!items.length) {
      wrap.innerHTML = '<div class="ab-empty">Nothing wasted in this period — the best possible chart. 🌱</div>';
      return;
    }

    const W = wrap.clientWidth, H = wrap.clientHeight;
    if (!W || !H) return;
    const G = 6;
    const rects = squarify(items, 0, 0, W + G, H + G);
    const gById = Object.fromEntries(cats.groups.map((g) => [g.id, g]));
    const g = gen;
    const reduce = REDUCE();

    wrap.innerHTML = '';
    const tiles = rects.map((r) => {
      const grp = gById[r.group] || { color: 'var(--accent)', ink: 'light', name: r.group };
      const w = r.w - G, h = r.h - G;
      const shareNum = (r.v / total) * 100;
      const share = `${shareNum.toFixed(shareNum < 10 ? 1 : 0)}%`;
      const chars = fmt(r.v).length;
      let fs = Math.min(30, (w - 24 - 58) / (chars * 0.62));
      let showPct = true;
      if (fs < 17) { showPct = false; fs = Math.min(30, (w - 24) / (chars * 0.62)); }
      const tiny = fs < 12 || h < 54 || w < 60;
      const showName = h >= 78 && w >= 96;
      const ink = grp.ink === 'light' ? '#fff' : grp.ink === 'dark' ? '#0b0b0c' : '';

      const tile = document.createElement('div');
      tile.className = 'ab-tile';
      tile.style.cssText = `left:${W / 2}px;top:${H / 2}px;width:0;height:0;background:${grp.color};--tile-bg:${grp.color};` +
        (ink ? `color:${ink};` : '');
      tile.innerHTML =
        `<div class="n">${TILE_ICON}${showName ? `<span style="overflow:hidden;text-overflow:ellipsis">${esc(r.name.replace(/-/g, ' '))}</span>` : ''}</div>` +
        (tiny ? '' : `<div class="v"><b style="font-size:${Math.max(12, fs)}px">0</b>${showPct ? `<em>${share}</em>` : ''}</div>`);
      tile.addEventListener('pointermove', (e) => {
        showTip(e.clientX, e.clientY, {
          title: `${cats.periods[period].label} · ${esc(grp.name)}`,
          rows: [
            { label: r.name.replace(/-/g, ' '), value: `${fmt(r.v)} ${data.unit}`, color: grp.color },
            { label: 'Share', value: share },
          ],
        });
      });
      tile.addEventListener('pointerleave', hideTip);
      wrap.appendChild(tile);
      return { tile, r, w, h };
    });

    // Tiles start collapsed at the centre and settle into place on the next
    // frame, so the CSS left/top/width/height transition reads as a bloom.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (g !== gen) return;
      for (const { tile, r, w, h } of tiles) {
        tile.style.left = `${r.x}px`;
        tile.style.top = `${r.y}px`;
        tile.style.width = `${Math.max(0, w)}px`;
        tile.style.height = `${Math.max(0, h)}px`;
      }
      tiles.forEach(({ tile }, i) => {
        const num = tile.querySelector('.v b');
        if (num) countUp(num, rects[i].v, g, '', '', reduce ? 0 : 900);
      });
    }));
  }

  /* ---------------- card D: seasonality radar ---------------- */

  function drawRadar() {
    const wrap = root.querySelector('#ab-radar');
    if (!wrap) return;
    const years = data.seasonality.years;
    const year = years[state.year];
    const values = year.values;
    const axis = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const W = wrap.clientWidth || 320;
    const S = Math.min(W, 420);
    const R = S / 2 - 34, C = S / 2;
    const N = 12;
    const color = 'var(--primary)';
    const g = gen;
    const ang = (i) => -Math.PI / 2 + (i / N) * Math.PI * 2;

    const norm = (v) => {
      const lo = Math.min(...v), hi = Math.max(...v);
      return v.map((x) => 0.42 + ((x - lo) / (hi - lo || 1)) * 0.58);
    };
    const fit = (v) => {
      const K = Math.min(5, Math.floor(N / 2));
      const co = [];
      for (let k = 0; k <= K; k++) {
        let a = 0, b = 0;
        v.forEach((x, i) => { const th = (i / N) * Math.PI * 2; a += x * Math.cos(k * th); b += x * Math.sin(k * th); });
        co.push([(a * (k ? 2 : 1)) / N, (b * (k ? 2 : 1)) / N]);
      }
      return (th) => co.reduce((r, [a, b], k) => r + a * Math.cos(k * th) + b * Math.sin(k * th), 0);
    };
    const at = (f, th) => {
      const v = Math.max(0.05, f(th));
      const a = -Math.PI / 2 + th;
      return [C + Math.cos(a) * (R * 0.2 + v * R * 0.8), C + Math.sin(a) * (R * 0.2 + v * R * 0.8)];
    };
    const shape = (v) => {
      const f = fit(norm(v));
      let d = '';
      for (let j = 0; j <= 180; j++) {
        const p = at(f, (j / 180) * Math.PI * 2);
        d += `${j ? 'L' : 'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`;
      }
      return `${d}Z`;
    };
    const point = (v, i) => at(fit(norm(v)), (i / N) * Math.PI * 2);

    wrap.innerHTML = '';
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', S);
    svg.setAttribute('height', S);
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', `Waste by month, ${year.label}`);
    svg.innerHTML = `
      ${[0.33, 0.66, 1].map((k) => `<circle cx="${C}" cy="${C}" r="${R * k}" fill="none" class="ab-grid-line"/>`).join('')}
      ${axis.map((m, i) => `
        <g>
          <line x1="${C + Math.cos(ang(i)) * R * 0.2}" y1="${C + Math.sin(ang(i)) * R * 0.2}"
                x2="${C + Math.cos(ang(i)) * R}" y2="${C + Math.sin(ang(i)) * R}" class="ab-grid-line"/>
          <text x="${C + Math.cos(ang(i)) * (R + 17)}" y="${C + Math.sin(ang(i)) * (R + 17)}" text-anchor="middle" dominant-baseline="central">${m}</text>
        </g>`).join('')}
      <path class="ab-radar-line" fill="none" stroke-width="2.5" stroke-linejoin="round" style="stroke:${color}"/>
      <circle cx="${C}" cy="${C}" r="${R * 0.2}" fill="var(--card-solid)" class="ab-grid-line"/>
      <g transform="translate(${C - 9} ${C - 9})" fill="none" stroke="var(--ab-mut)" stroke-width="1.4" stroke-linejoin="round" opacity=".75">
        <path d="M9 1.5C4.5 5.5 3.5 9.5 9 16.5C14.5 9.5 13.5 5.5 9 1.5Z"/><path d="M9 5.5v11"/>
      </g>
      <circle class="ab-radar-dot" r="4.5" style="display:none;fill:${color}" stroke="var(--card-solid)" stroke-width="2"/>
      <rect width="${S}" height="${S}" fill="transparent"/>`;
    wrap.appendChild(svg);

    const line = svg.querySelector('.ab-radar-line');
    const dot = svg.querySelector('.ab-radar-dot');
    const from = wrap._cur || values.map(() => 1);
    const t0 = performance.now();
    const stepf = (now) => {
      if (g !== gen || !svg.closest('#analytics-bento')) return;
      const t = REDUCE() ? 1 : EASE(Math.min(1, (now - t0) / 900));
      wrap._cur = from.map((v, i) => v + (values[i] - v) * t);
      line.setAttribute('d', shape(wrap._cur));
      if (t < 1) requestAnimationFrame(stepf);
    };
    requestAnimationFrame(stepf);

    svg.querySelector('rect').addEventListener('pointermove', (e) => {
      const r = svg.getBoundingClientRect();
      const x = e.clientX - r.left - C, y = e.clientY - r.top - C;
      if (Math.hypot(x, y) < R * 0.2) { dot.style.display = 'none'; hideTip(); return; }
      let a = Math.atan2(y, x) + Math.PI / 2;
      if (a < 0) a += Math.PI * 2;
      const i = Math.round((a / (Math.PI * 2)) * N) % N;
      const p = point(values, i);
      dot.setAttribute('cx', p[0]); dot.setAttribute('cy', p[1]);
      dot.style.display = '';
      showTip(r.left + p[0], r.top + p[1], {
        title: `${axis[i]} ${year.label}`,
        rows: [{ label: `Wasted (${data.unit})`, value: fmt(values[i]), color: 'var(--primary)' }],
      });
    });
    svg.querySelector('rect').addEventListener('pointerleave', () => { dot.style.display = 'none'; hideTip(); });
  }

  function renderSeasonSide() {
    const year = data.seasonality.years[state.year];
    const stats = root.querySelector('#ab-season-stats');
    const rows = root.querySelector('#ab-season-rows');
    if (stats) {
      stats.innerHTML = year.stats.map((s) => `
        <div>
          <div class="k">${esc(s.label)} (${data.unit})</div>
          <div class="v"><span class="cu" data-v="${s.value}">0</span></div>
          <div class="d">${deltaHtml(s)}${esc(s.note)}</div>
        </div>`).join('');
      const g = gen;
      stats.querySelectorAll('.cu').forEach((el) => countUp(el, +el.dataset.v, g));
    }
    if (rows) {
      rows.innerHTML = year.rows.length
        ? year.rows.map((r) => `<div><span>Top: ${esc(r.label)}</span><b>${esc(r.value)} ${data.unit}</b></div>`).join('')
        : '<div><span>No entries this year yet</span><b>—</b></div>';
    }
  }

  /* ---------------- shell ---------------- */

  function shell() {
    const b = data;
    const trend = b.trend, inv = b.inventory, cats = b.categories;
    const groupsPresent = cats.groups.filter((g) => cats.items.some((i) => i.group === g.id));
    const groupsLegend = groupsPresent.map((g) =>
      `<span><i class="sq" style="background:${g.color}"></i>${esc(g.name)}</span>`).join('');

    root.innerHTML = `
      <div class="ab-grid">
        <!-- A: waste trend -->
        <section class="ab-card ab-a" aria-label="Waste trend">
          <div class="ab-head">
            <div class="ab-side">
              <div class="ab-kicker">Waste Trend (${esc(b.unit)})</div>
              <div class="ab-figure"><span class="cu" data-v="${trend.total}">0</span>${deltaHtml(trend)}</div>
              <div class="ab-note">vs <b>${fmt(trend.prevTotal)}</b> ${esc(b.unit)} prev 30 days · <b>${trend.entries}</b> entries</div>
            </div>
            <div class="ab-plot" id="ab-trend-plot"><span class="cap">Last 30 days</span></div>
          </div>
        </section>

        <!-- B: pantry inventory waves -->
        <section class="ab-card ab-b" aria-label="Pantry inventory">
          <div class="ab-head">
            <div class="ab-side">
              <div class="ab-kicker">Pantry Inventory</div>
              <div class="ab-figure"><span class="cu" data-v="${inv.today}">0</span>${deltaHtml(inv)}</div>
              <div class="ab-note">items in date · by day, last 2 weeks</div>
              <div class="ab-legend">
                <span><i style="background:linear-gradient(90deg,#34d399,var(--primary))"></i>In date</span>
                <span><i style="background:linear-gradient(90deg,var(--warning),var(--danger))"></i>Past expiry</span>
                <span><i class="dash"></i>Prior 2 weeks</span>
              </div>
            </div>
            <div class="ab-plot" id="ab-waves-plot"></div>
          </div>
        </section>

        <!-- C: categories treemap -->
        <section class="ab-card ab-c" aria-label="Waste by category">
          <div class="ab-c-head">
            <h3>Waste by Category (${esc(b.unit)})</h3>
            <div class="ab-legend">${groupsLegend}</div>
          </div>
          <div class="ab-periods" role="group" aria-label="Time period">
            ${cats.periods.map((p, i) => `
              <button type="button" class="ab-period" data-i="${i}" aria-pressed="${i === state.period}">
                <div class="t">${esc(p.label)}</div>
                <div class="v">${fmt(p.total)}${deltaHtml(p)}</div>
                <div class="c">${esc(p.compare)}</div>
              </button>`).join('')}
          </div>
          <div class="ab-treemap" id="ab-treemap"></div>
        </section>

        <!-- D: seasonality radar -->
        <section class="ab-card ab-d" aria-label="Seasonality">
          <div class="ab-c-head">
            <h3>Seasonality</h3>
            <div class="ab-seg" role="tablist" aria-label="Year">
              <span class="thumb"></span>
              ${b.seasonality.years.map((y, i) =>
                `<button role="tab" type="button" data-i="${i}" aria-selected="${i === state.year}">${esc(y.label)}</button>`).join('')}
            </div>
          </div>
          <div class="ab-radar" id="ab-radar"></div>
          <div class="ab-mini" id="ab-season-stats"></div>
          <div class="ab-rows" id="ab-season-rows"></div>
        </section>
      </div>`;

    // figure count-ups
    const g = gen;
    root.querySelectorAll('.ab-figure .cu').forEach((el) => countUp(el, +el.dataset.v, g));

    // period tabs
    root.querySelectorAll('.ab-period').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.period = +btn.dataset.i;
        root.querySelectorAll('.ab-period').forEach((b2) =>
          b2.setAttribute('aria-pressed', String(+b2.dataset.i === state.period)));
        drawTreemap();
      });
    });

    // year segmented control
    const seg = root.querySelector('.ab-seg');
    const moveThumb = () => {
      const btn = seg.querySelectorAll('button')[state.year];
      if (!btn) return;
      const thumb = seg.querySelector('.thumb');
      thumb.style.width = `${btn.offsetWidth}px`;
      thumb.style.transform = `translateX(${btn.offsetLeft - 2}px)`;
    };
    seg.querySelectorAll('button').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.year = +btn.dataset.i;
        seg.querySelectorAll('button').forEach((b2) =>
          b2.setAttribute('aria-selected', String(+b2.dataset.i === state.year)));
        moveThumb();
        const radar = root.querySelector('#ab-radar');
        if (radar) radar._cur = null;   // re-grow from the hub
        drawRadar();
        renderSeasonSide();
      });
    });
    requestAnimationFrame(moveThumb);

    // charts
    drawTrend();
    drawWaves();
    drawTreemap();
    drawRadar();
    renderSeasonSide();
  }

  function destroy() {
    gen++;
    if (ro) { ro.disconnect(); ro = null; }
    hideTip();
  }

  function render(rootEl, bento) {
    if (!rootEl) return;
    destroy();
    root = rootEl;
    data = bento;
    if (!data) { root.removeAttribute('aria-busy'); return; }
    state.period = Math.min(state.period, data.categories.periods.length - 1);
    state.year = Math.min(state.year, data.seasonality.years.length - 1);
    root.removeAttribute('aria-busy');
    shell();

    // re-draw vector charts when the grid resizes (debounced, size-equal guarded)
    let lastW = root.clientWidth;
    ro = new ResizeObserver(() => {
      const w = root.clientWidth;
      if (w === lastW) return;
      lastW = w;
      drawTrend();
      drawWaves();
      drawTreemap();
      drawRadar();
      const segBtn = root.querySelector(`.ab-seg button[data-i="${state.year}"]`);
      if (segBtn) {
        const thumb = root.querySelector('.ab-seg .thumb');
        thumb.style.width = `${segBtn.offsetWidth}px`;
        thumb.style.transform = `translateX(${segBtn.offsetLeft - 2}px)`;
      }
    });
    ro.observe(root);
  }

  return { render, destroy };
})();

window.ABENTO = ABENTO;
