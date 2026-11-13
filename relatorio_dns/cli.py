"""Usage:
  relatorio-dns relatorio consultas/2026-11-*_ALL.log [--lista maior.txt] [--saida relatorio.html]
  relatorio-dns exemplo exemplos/   writes a synthetic log and the bigger list used in the demo
"""

import argparse
import glob
import sys
from pathlib import Path

from relatorio_dns.report import aggregate, candidates, parse, read_list, render
from relatorio_dns.sample import BIGGER_LIST, generate


def read_lines(files):
    """Stream the logs line by line: a month of a busy home network does not need to fit in memory."""
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            yield from fh


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="relatorio-dns", description="Relatório HTML do registro de consultas do Blocky.")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("relatorio", help="gera o relatório")
    r.add_argument("logs", nargs="+", help="arquivos de registro do Blocky (aceita curingas como *.log)")
    r.add_argument("--lista", action="append", default=[], help="lista de bloqueio maior para achar candidatos (pode repetir)")
    r.add_argument("--saida", default="relatorio.html")
    e = sub.add_parser("exemplo", help="gera um registro inventado para testar")
    e.add_argument("pasta")
    args = p.parse_args(argv)

    if args.cmd == "exemplo":
        out = Path(args.pasta)
        out.mkdir(parents=True, exist_ok=True)
        (out / "2026-11-01_ALL.log").write_text(generate(), encoding="utf-8")
        (out / "lista-maior.txt").write_text(BIGGER_LIST, encoding="utf-8")
        print(f"exemplo em {out}")
        return

    files = sorted({f for pattern in args.logs for f in (glob.glob(pattern) or [pattern])})  # Windows shells do not expand *
    stats = aggregate(parse(read_lines(files)))
    blocklist = set().union(*(read_list(Path(f).read_text(encoding="utf-8")) for f in args.lista)) if args.lista else None
    cands = candidates(stats, blocklist) if blocklist is not None else None
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(render(stats, cands), encoding="utf-8")
    total, blocked = sum(stats.total.values()), sum(stats.blocked.values())
    print(f"{len(files)} arquivo(s), {total} consultas, {blocked} bloqueadas: relatório em {args.saida}")
