"""Read Blocky's CSV query log and build a self-contained HTML report (standard library only).

Blocky log line (tab-separated): time, client IP, client name, duration ms, reason, question, answer
  2026-11-01 20:58:01	192.168.0.12	tv-sala	12	RESOLVED (https://1.1.1.1/dns-query)	ad.doubleclick.net.	A (1.2.3.4)
"""

import html
from collections import Counter, defaultdict
from dataclasses import dataclass, field

ALLOWED = {"RESOLVED", "CACHED"}


@dataclass
class Stats:
    total: Counter = field(default_factory=Counter)        # device -> queries
    blocked: Counter = field(default_factory=Counter)      # device -> blocked queries
    hour_total: Counter = field(default_factory=Counter)   # hour -> queries
    hour_blocked: Counter = field(default_factory=Counter)
    blocked_domains: Counter = field(default_factory=Counter)
    blocked_by: dict = field(default_factory=lambda: defaultdict(set))   # domain -> devices
    allowed: dict = field(default_factory=lambda: defaultdict(Counter))  # device -> domain -> count
    days: set = field(default_factory=set)


def parse(lines):
    """(day, hour, device, reason, domain) per valid line; broken lines are skipped."""
    for line in lines:
        c = line.rstrip("\n").split("\t")
        if len(c) < 6 or len(c[0]) < 13:
            continue
        yield c[0][:10], int(c[0][11:13]), c[2] or c[1], c[4].split(" ")[0], c[5].rstrip(".").lower()


def aggregate(records):
    s = Stats()
    for day, hour, device, reason, domain in records:
        s.days.add(day)
        s.total[device] += 1
        s.hour_total[hour] += 1
        if reason == "BLOCKED":
            s.blocked[device] += 1
            s.hour_blocked[hour] += 1
            s.blocked_domains[domain] += 1
            s.blocked_by[domain].add(device)
        elif reason in ALLOWED:
            s.allowed[device][domain] += 1
    return s


def read_list(text):
    """Blocklist in wildcard or plain-domain format: one domain per line, # for comments."""
    return {line.strip().removeprefix("*.").lower() for line in text.splitlines() if line.strip() and not line.startswith("#")}


def listed(domain, blocklist):
    """True if the domain or any parent domain is in the list (a.b.c matches b.c)."""
    parts = domain.split(".")
    return any(".".join(parts[i:]) in blocklist for i in range(len(parts) - 1))


def candidates(s, blocklist):
    """Allowed domains that a bigger blocklist would block: (domain, count, devices), most requested first."""
    found = defaultdict(lambda: [0, set()])
    for device, domains in s.allowed.items():
        for d, n in domains.items():
            if listed(d, blocklist):
                found[d][0] += n
                found[d][1].add(device)
    return sorted(((d, n, devs) for d, (n, devs) in found.items()), key=lambda x: -x[1])


# --- HTML -----------------------------------------------------------------------------------

def esc(x):
    return html.escape(str(x))


def pct(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "0%"


def column_chart(s):
    """Queries per hour of day: allowed and blocked stacked, one column per hour."""
    w, h, left, bottom, top = 720, 240, 44, 26, 10
    peak = max(s.hour_total.values(), default=1)
    step = (w - left) / 24
    bar = step - 6
    def y(v):
        return top + (h - top - bottom) * (1 - v / peak)

    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="t-hora">']
    for frac in (0, 0.5, 1):  # recessive grid
        v = round(peak * frac)
        out.append(f'<line class="grid" x1="{left}" x2="{w}" y1="{y(v):.1f}" y2="{y(v):.1f}"/>'
                   f'<text class="axis" x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end">{v}</text>')
    for hr in range(24):
        x = left + hr * step + 3
        tot, blk = s.hour_total[hr], s.hour_blocked[hr]
        ok = tot - blk
        tip = f"{hr:02d}h: {tot} consultas, {blk} bloqueadas ({pct(blk, tot)})"
        out.append(f'<g><title>{esc(tip)}</title>'
                   f'<rect class="hit" x="{x - 3:.1f}" y="{top}" width="{step:.1f}" height="{h - top - bottom}"/>')
        if ok:
            out.append(f'<rect class="s1" x="{x:.1f}" y="{y(ok):.1f}" width="{bar:.1f}" height="{y(0) - y(ok):.1f}" rx="2"/>')
        if blk:  # 2px surface gap between the stacked segments
            out.append(f'<rect class="s2" x="{x:.1f}" y="{y(tot):.1f}" width="{bar:.1f}" height="{max(y(ok) - y(tot) - 2, 1):.1f}" rx="2"/>')
        out.append("</g>")
        if hr % 3 == 0:
            out.append(f'<text class="axis" x="{x + bar / 2:.1f}" y="{h - 8}" text-anchor="middle">{hr:02d}h</text>')
    out.append("</svg>")
    return "".join(out)


def bar_chart(s):
    """Queries per device: horizontal bars, allowed then blocked, with the share blocked as a direct label."""
    rows = s.total.most_common()
    w, row_h, left, right = 720, 34, 120, 150
    peak = max(s.total.values(), default=1)
    scale = (w - left - right) / peak
    out = [f'<svg viewBox="0 0 {w} {row_h * len(rows) + 8}" role="img" aria-labelledby="t-aparelho">']
    for i, (dev, tot) in enumerate(rows):
        blk = s.blocked[dev]
        ok = tot - blk
        y = 6 + i * row_h
        tip = f"{dev}: {tot} consultas, {blk} bloqueadas ({pct(blk, tot)})"
        out.append(f'<g><title>{esc(tip)}</title><rect class="hit" x="0" y="{y - 3}" width="{w}" height="{row_h}"/>'
                   f'<text class="label" x="{left - 10}" y="{y + 17}" text-anchor="end">{esc(dev)}</text>'
                   f'<rect class="s1" x="{left}" y="{y}" width="{max(ok * scale, 1):.1f}" height="22" rx="2"/>')
        if blk:
            out.append(f'<rect class="s2" x="{left + ok * scale + 2:.1f}" y="{y}" width="{max(blk * scale - 2, 1):.1f}" height="22" rx="2"/>')
        out.append(f'<text class="value" x="{left + tot * scale + 8:.1f}" y="{y + 17}">{tot} · {pct(blk, tot)} bloq.</text></g>')
    out.append("</svg>")
    return "".join(out)


CSS = """
:root{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--grid:#e4e3df;--s1:#2a78d6;--s2:#eb6834}
@media (prefers-color-scheme:dark){:root{--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--grid:#383835;--s1:#3987e5;--s2:#d95926}}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.5 system-ui,sans-serif}
main{max-width:780px;margin:0 auto;padding:24px 16px}
h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.15rem;margin:32px 0 8px}
.sub{color:var(--ink2);margin:0 0 20px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.tile,.card{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:14px 16px}
.tile b{display:block;font-size:1.6rem}.tile span{color:var(--ink2);font-size:.9rem}
svg{width:100%;height:auto;display:block}
.s1{fill:var(--s1)}.s2{fill:var(--s2)}.grid{stroke:var(--grid)}.hit{fill:transparent}
g:hover .s1,g:hover .s2{opacity:.8}
.axis{fill:var(--ink2);font-size:11px}.label{fill:var(--ink);font-size:13px}.value{fill:var(--ink2);font-size:12px}
.legend{display:flex;gap:16px;color:var(--ink2);font-size:.9rem;margin:0 0 8px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
table{width:100%;border-collapse:collapse;font-size:.92rem}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid)}td.n{text-align:right;font-variant-numeric:tabular-nums}
th{color:var(--ink2);font-weight:600}details{margin-top:8px;color:var(--ink2)}
"""


def table(head, rows):
    th = "".join(f"<th>{esc(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f'<td class="n">{esc(c)}</td>' if isinstance(c, int) else f"<td>{esc(c)}</td>" for c in r) + "</tr>"
                   for r in rows)
    return f"<table><tr>{th}</tr>{body}</table>"


def render(s, cands=None, top=15):
    total, blocked = sum(s.total.values()), sum(s.blocked.values())
    days = sorted(s.days)
    period = days[0] if len(days) == 1 else f"{days[0]} a {days[-1]}" if days else "sem dados"
    legend = '<div class="legend"><span><i style="background:var(--s1)"></i>Liberadas</span><span><i style="background:var(--s2)"></i>Bloqueadas</span></div>'
    parts = [
        ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
         f"<title>Relatório DNS {esc(period)}</title><style>{CSS}</style></head><body><main>"),
        "<h1>Relatório do bloqueador de DNS</h1>",
        f'<p class="sub">Registro do Blocky de {esc(period)}</p>',
        ('<div class="tiles">'
         f'<div class="tile"><b>{total}</b><span>consultas</span></div>'
         f'<div class="tile"><b>{pct(blocked, total)}</b><span>bloqueadas ({blocked})</span></div>'
         f'<div class="tile"><b>{len(s.total)}</b><span>aparelhos</span></div>'
         f'<div class="tile"><b>{len(s.blocked_domains)}</b><span>domínios bloqueados</span></div></div>'),
        '<h2 id="t-hora">Consultas por hora do dia</h2>', '<div class="card">', legend, column_chart(s),
        "<details><summary>Ver como tabela</summary>",
        table(["Hora", "Consultas", "Bloqueadas"], [(f"{h:02d}h", s.hour_total[h], s.hour_blocked[h]) for h in range(24)]),
        "</details></div>",
        '<h2 id="t-aparelho">Consultas por aparelho</h2>', '<div class="card">', legend, bar_chart(s),
        "<details><summary>Ver como tabela</summary>",
        table(["Aparelho", "Consultas", "Bloqueadas"], [(d, n, s.blocked[d]) for d, n in s.total.most_common()]),
        "</details></div>",
        f"<h2>Domínios mais bloqueados (top {top})</h2>", '<div class="card">',
        table(["Domínio", "Vezes", "Aparelhos"],
              [(d, n, ", ".join(sorted(s.blocked_by[d]))) for d, n in s.blocked_domains.most_common(top)]),
        "</div>",
    ]
    if cands is not None:
        parts += [f"<h2>Liberados que uma lista maior bloquearia ({len(cands)})</h2>",
                  '<p class="sub">Candidatos a bloqueio: confira cada um antes, porque listas grandes também quebram sites.</p>',
                  '<div class="card">', table(["Domínio", "Vezes", "Aparelhos"], [(d, n, ", ".join(sorted(v))) for d, n, v in cands[:top]]),
                  "</div>"]
    parts.append("<h2>Liberados mais pedidos por aparelho</h2>")
    for dev, domains in sorted(s.allowed.items()):
        parts += [f'<div class="card" style="margin-bottom:12px"><b>{esc(dev)}</b>', table(["Domínio", "Vezes"], domains.most_common(8)), "</div>"]
    parts.append("</main></body></html>\n")
    return "".join(parts)
