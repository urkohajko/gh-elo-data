#!/usr/bin/env python3
"""
GH-Elo Builder
Descarga Sackmann, calcula Elo general + superficie, guarda elo_state.json
"""

import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timedelta
from collections import defaultdict

# --- Configuración ---
YEAR_START = 2015
YEAR_END = datetime.now().year
BASE_URL = "https://raw.githubusercontent.com/JeffSackmann"
REPOS = {
    "ATP": [
        f"{BASE_URL}/tennis_atp/master/atp_matches_{y}.csv"
        for y in range(YEAR_START, YEAR_END + 1)
    ] + [
        f"{BASE_URL}/tennis_atp/master/atp_matches_futures_{y}.csv"
        for y in range(YEAR_START, YEAR_END + 1)
    ] + [
        f"{BASE_URL}/tennis_atp/master/atp_matches_qual_chall_{y}.csv"
        for y in range(YEAR_START, YEAR_END + 1)
    ],
    "WTA": [
        f"{BASE_URL}/tennis_wta/master/wta_matches_{y}.csv"
        for y in range(YEAR_START, YEAR_END + 1)
    ] + [
        f"{BASE_URL}/tennis_wta/master/wta_matches_qual_itf_{y}.csv"
        for y in range(YEAR_START, YEAR_END + 1)
    ],
}

ELO_INIT = 1500
K_FACTOR_BASE = 250


def normalize(name):
    if not name:
        return None
    import unicodedata
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower().strip()


def k_factor(n):
    return K_FACTOR_BASE / ((n + 5) ** 0.4)


def expected(rw, rl):
    return 1 / (1 + 10 ** (-(rw - rl) / 400))


def surface_key(surface):
    if not surface or surface.lower() in ("", "carpet"):
        return "Hard"
    s = surface.lower()
    if "clay" in s:
        return "Clay"
    if "grass" in s:
        return "Grass"
    return "Hard"


def download_csv(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "gh-elo/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  FALLO {url}: {e}", file=sys.stderr)
        return None


def process_tour(tour, urls):
    players = defaultdict(lambda: {
        "elo": ELO_INIT,
        "eloS": {"Hard": ELO_INIT, "Clay": ELO_INIT, "Grass": ELO_INIT},
        "n": 0,
        "n_sup": {"Hard": 0, "Clay": 0, "Grass": 0},
        "matches": [],
        "last": None,
    })

    print(f"\n=== {tour} ===")
    all_matches = []

    for url in urls:
        csv_text = download_csv(url)
        if not csv_text:
            continue
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            try:
                date = row.get("tourney_date")
                wn = row.get("winner_name")
                ln = row.get("loser_name")
                surf = row.get("surface", "")
                if not (date and wn and ln):
                    continue
                all_matches.append((date, wn, ln, surf))
            except Exception:
                continue

    all_matches.sort(key=lambda x: x[0])
    print(f"  Partidos totales: {len(all_matches)}")

    for date, wn, ln, surf in all_matches:
        wa = normalize(wn)
        la = normalize(ln)
        if not wa or not la:
            continue
        sk = surface_key(surf)
        pw = players[wa]
        pl = players[la]

        # General
        ew = expected(pw["elo"], pl["elo"])
        k_w = k_factor(pw["n"])
        k_l = k_factor(pl["n"])
        pw["elo"] += k_w * (1 - ew)
        pl["elo"] -= k_l * (1 - ew)

        # Superficie
        ew_s = expected(pw["eloS"][sk], pl["eloS"][sk])
        k_ws = k_factor(pw["n_sup"][sk])
        k_ls = k_factor(pl["n_sup"][sk])
        pw["eloS"][sk] += k_ws * (1 - ew_s)
        pl["eloS"][sk] -= k_ls * (1 - ew_s)

        pw["n"] += 1
        pl["n"] += 1
        pw["n_sup"][sk] += 1
        pl["n_sup"][sk] += 1
        pw["last"] = date
        pl["last"] = date

        pw["matches"].append(date)
        pl["matches"].append(date)

    max_date = max((m[0] for m in all_matches), default="19000101")
    cutoff = (datetime.strptime(max_date, "%Y%m%d") - timedelta(days=364)).strftime("%Y%m%d")

    result = {}
    for name, p in players.items():
        n52 = sum(1 for d in p["matches"] if d >= cutoff)
        result[f"{tour}|{name}"] = {
            "elo": round(p["elo"], 1),
            "eloS": {k: round(v, 1) for k, v in p["eloS"].items()},
            "n_sup": p["n_sup"],
            "n52": n52,
            "last": p["last"],
            "n_total": p["n"],
        }
    return result, max_date


def main():
    all_players = {}
    max_dates = []
    for tour, urls in REPOS.items():
        res, md = process_tour(tour, urls)
        all_players.update(res)
        max_dates.append(md)

    max_date = max(max_dates)
    built = datetime.utcnow().isoformat() + "Z"

    state = {
        "built": built,
        "max_date": max_date,
        "players": all_players,
    }

    with open("elo_state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, separators=(",", ":"))

    n_total = len(all_players)
    n_valid = sum(1 for p in all_players.values() if p["n52"] >= 10)
    print(f"\n=== RESUMEN ===")
    print(f"Jugadores: {n_total}")
    print(f"Max date: {max_date}")
    print(f"n52>=10: {n_valid} ({100*n_valid/n_total:.1f}%)")


if __name__ == "__main__":
    main()
