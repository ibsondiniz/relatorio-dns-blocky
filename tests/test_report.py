from relatorio_dns.cli import main
from relatorio_dns.report import aggregate, candidates, listed, parse, read_list, render
from relatorio_dns.sample import generate

LINES = [
    "2026-11-01 20:58:01\t192.168.0.12\ttv-sala\t12\tRESOLVED (https://1.1.1.1/dns-query)\tad.doubleclick.net.\tA (1.2.3.4)\n",
    "2026-11-01 20:58:01\t192.168.0.12\ttv-sala\t0\tBLOCKED (anuncios)\tpagead2.googlesyndication.com.\tA (0.0.0.0)\n",
    "2026-11-01 21:10:02\t192.168.0.12\ttv-sala\t0\tCACHED\tad.doubleclick.net.\tA (1.2.3.4)\n",
    "2026-11-01 08:00:00\t192.168.0.13\t\t3\tRESOLVED (https://1.1.1.1/dns-query)\tGitHub.com.\tA (4.4.4.4)\n",
    "linha quebrada\n",
]


def test_parse_skips_broken_lines_and_names_unnamed_devices_by_ip():
    rows = list(parse(LINES))
    assert len(rows) == 4
    assert rows[3] == ("2026-11-01", 8, "192.168.0.13", "RESOLVED", "github.com")


def test_aggregate_counts_per_device_and_hour():
    s = aggregate(parse(LINES))
    assert s.total == {"tv-sala": 3, "192.168.0.13": 1}
    assert s.blocked == {"tv-sala": 1}
    assert s.hour_total[20] == 2 and s.hour_blocked[20] == 1 and s.hour_total[21] == 1
    assert s.allowed["tv-sala"]["ad.doubleclick.net"] == 2
    assert s.blocked_by["pagead2.googlesyndication.com"] == {"tv-sala"}


def test_bigger_list_matches_parent_domains_only():
    bl = read_list("# comentario\n*.doubleclick.net\nads.exemplo.com\n")
    assert listed("ad.doubleclick.net", bl) and listed("doubleclick.net", bl)
    assert not listed("exemplo.com", bl)  # a parent of a listed name is not blocked
    s = aggregate(parse(LINES))
    assert candidates(s, bl) == [("ad.doubleclick.net", 2, {"tv-sala"})]


def test_html_is_escaped_and_has_both_charts():
    evil = "2026-11-01 10:00:00\t192.168.0.20\t<script>x</script>\t1\tCACHED\ta.com.\tA (1.1.1.1)\n"
    page = render(aggregate(parse(LINES + [evil])), [])
    assert "<script>x" not in page and "&lt;script&gt;x" in page
    assert page.count("<svg") == 2 and 'aria-labelledby="t-hora"' in page
    assert "Liberados que uma lista maior bloquearia (0)" in page


def test_sample_is_deterministic_and_realistic():
    a, b = generate(), generate()
    assert a == b
    s = aggregate(parse(a.splitlines(keepends=True)))
    share = sum(s.blocked.values()) / sum(s.total.values())
    assert 0.08 < share < 0.16
    assert s.hour_total[20] > s.hour_total[4]  # evenings busier than early morning


def test_cli_end_to_end(tmp_path, capsys):
    main(["exemplo", str(tmp_path)])
    out = tmp_path / "r.html"
    main(["relatorio", str(tmp_path / "*.log"), "--lista", str(tmp_path / "lista-maior.txt"), "--saida", str(out)])
    assert "1 arquivo(s)" in capsys.readouterr().out
    page = out.read_text(encoding="utf-8")
    assert "telemetria.smarttv-exemplo.com" in page and "graph.instagram.com" in page
