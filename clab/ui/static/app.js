/* Shared helpers. No framework, no CDN - the page must work offline on loopback. */

function $(id) { return document.getElementById(id); }

async function getJSON(url) {
  const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
  return r.json();
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/* NO_DATA renders as an em dash, never 0 - a company with no interest-expense tag
   is not a company with terrible interest coverage. */
const DASH = '—';

function num(v, d) {
  if (v === null || v === undefined || v === '' || Number.isNaN(v)) return DASH;
  const n = Number(v);
  if (!isFinite(n)) return DASH;
  return n.toLocaleString(undefined, { minimumFractionDigits: d === undefined ? 1 : d,
                                       maximumFractionDigits: d === undefined ? 1 : d });
}

function pct(v, d) {
  if (v === null || v === undefined || v === '' || Number.isNaN(Number(v))) return DASH;
  return (Number(v) * 100).toFixed(d === undefined ? 0 : d) + '%';
}

function int(v) {
  if (v === null || v === undefined || v === '' || Number.isNaN(Number(v))) return DASH;
  return String(Math.round(Number(v)));
}

function big(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return DASH;
  const n = Number(v), a = Math.abs(n);
  if (a >= 1e12) return (n / 1e12).toFixed(2) + 'T';
  if (a >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (a >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  return n.toFixed(0);
}

function bandHtml(b) {
  if (!b) return DASH;
  return '<span class="band ' + esc(b) + '">' + esc(String(b).replace(/_/g, ' ')) + '</span>';
}

function headline(st) {
  const el = $('headline');
  if (!el) return;
  const s = (st && st.summary) || {};
  if (!st || !st.ok) {
    el.textContent = (st && st.reason) ? st.reason : 'no data yet';
    return;
  }
  const cov = s.median_coverage == null ? DASH : pct(s.median_coverage);
  el.textContent = s.companies + ' companies · median coverage ' + cov +
    ' · ' + s.with_llm_qualitative + ' with LLM half · through ' +
    (s.data_through || DASH);
}

function kv(k, v) { return '<dt>' + esc(k) + '</dt><dd>' + v + '</dd>'; }

/* Component bar: earned (green) + unavailable (hatched). A 12/15 with 3 points
   unavailable must not look like a fully scored 12/15. */
function barHtml(label, earned, available, max, isLlm) {
  const e = Number(earned || 0), av = Number(available || 0), m = Number(max || 1);
  const gap = Math.max(av - e, 0), na = Math.max(m - av, 0);
  return '<div class="bar"><span class="lab">' + esc(label) +
    (isLlm ? '<span class="llm">LLM</span>' : '') + '</span>' +
    '<span class="track">' +
      '<span class="fill" style="width:' + (e / m * 100) + '%"></span>' +
      '<span style="width:' + (gap / m * 100) + '%"></span>' +
      '<span class="na" style="width:' + (na / m * 100) + '%"></span>' +
    '</span>' +
    '<span class="val">' + (earned == null ? DASH : e) + '/' + m +
      (na > 0 ? ' <span class="muted">(' + na + ' n/a)</span>' : '') + '</span></div>';
}
