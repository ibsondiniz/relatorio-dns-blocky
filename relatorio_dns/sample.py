"""Synthetic Blocky log for demos and tests: invented home network, public domain names, fixed seed."""

import random

DEVICES = [  # (ip, name, queries per day, domains it uses)
    ("192.168.0.10", "notebook", 1800, ["github.com", "pypi.org", "www.google.com", "fonts.gstatic.com", "web.whatsapp.com",
                                       "www.youtube.com", "i.ytimg.com", "login.microsoftonline.com"]),
    ("192.168.0.11", "celular", 1500, ["graph.instagram.com", "scontent.cdninstagram.com", "web.whatsapp.com", "www.google.com",
                                      "api.spotify.com", "i.scdn.co", "gateway.icloud.com"]),
    ("192.168.0.12", "tv-sala", 2600, ["www.netflix.com", "occ-0-1234.1.nflxso.net", "www.youtube.com", "i.ytimg.com",
                                      "telemetria.smarttv-exemplo.com", "ntp.smarttv-exemplo.com"]),
    ("192.168.0.13", "", 300, ["pool.ntp.org", "connectivitycheck.gstatic.com"]),  # device without a name in Blocky
]
ADS = ["ad.doubleclick.net", "pagead2.googlesyndication.com", "app-measurement.com", "ads.smarttv-exemplo.com",
       "graph.facebook.com", "googleads.g.doubleclick.net", "track.exemplo-anuncios.com"]
HOURS = [1, 1, 1, 1, 1, 1, 2, 4, 6, 6, 6, 7, 8, 6, 6, 6, 6, 7, 9, 12, 14, 13, 10, 4]  # evenings are busier

# a "bigger list" that would also block what the base list lets through
BIGGER_LIST = "# lista maior de exemplo\n*.smarttv-exemplo.com\ngraph.instagram.com\napp-measurement.com\n"


def generate(day="2026-11-01", seed=42):
    rnd = random.Random(seed)
    lines = []
    for ip, name, n, domains in DEVICES:
        for _ in range(n):
            hour = rnd.choices(range(24), HOURS)[0]
            t = f"{day} {hour:02d}:{rnd.randrange(60):02d}:{rnd.randrange(60):02d}"
            if rnd.random() < 0.12:
                dom, reason, ans = rnd.choice(ADS), "BLOCKED (anuncios)", "A (0.0.0.0)"
            else:
                dom = rnd.choice(domains)
                reason = "CACHED" if rnd.random() < 0.4 else "RESOLVED (https://1.1.1.1/dns-query)"
                ans = f"A (93.184.{rnd.randrange(256)}.{rnd.randrange(256)})"
            lines.append((t, f"{t}\t{ip}\t{name}\t{rnd.randrange(1, 60)}\t{reason}\t{dom}.\t{ans}\n"))
    return "".join(line for _, line in sorted(lines))
