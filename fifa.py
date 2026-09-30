"""apex_national.py : CAN et Ligue des Nations UEFA pour Apex Quant.

Source : football-data.org (même clé API que le reste de l'appli).
Les stats sont calculées à partir des résultats (pas de classement par groupes).
"""
from datetime import datetime

import numpy as np
import requests
import streamlit as st

NATIONAL_COMPETITIONS = {
    "UEFA Nations League": "NL",
    "Coupe d'Afrique des Nations (CAN)": "CAN",
}

# home_adv : avantage du terrain en points Elo (0 = terrain neutre)
# field    : écart domicile/extérieur sur les buts (0 = neutre)
# hist     : mot-clé d'une 2e compétition (qualifications) pour enrichir l'historique
_CFG = {
    "NL": {"names": ["uefa nations league"], "skip": ["women", "u-"], "hist": None,
           "home_adv": 100.0, "field": 0.06},
    "CAN": {"names": ["africa cup", "african cup"], "skip": ["qualification", "women", "u-"],
            "hist": "qualification", "home_adv": 0.0, "field": 0.0},
}
PRIOR_GAMES = 4   # matchs "moyenne" ajoutés : régression vers la moyenne
ELO_K = 40.0


def is_national(code):
    return code in _CFG


def _get(url, key, params=None):
    try:
        r = requests.get(url, headers={"X-Auth-Token": key}, params=params, timeout=10)
        return r.json() if r.status_code == 200 else {"_status": r.status_code}
    except Exception:
        return {"_status": 0}


@st.cache_data(ttl=86400)
def _catalog(key, base):
    d = _get(f"{base}competitions", key)
    return d.get("competitions", []) if "_status" not in d else []


def _resolve(code, key, base):
    """Retrouve les ids des compétitions par leur nom (pas de code deviné)."""
    cfg, comps = _CFG[code], _catalog(key, base)

    def find(must=None, skip=()):
        for c in comps:
            n = str(c.get("name", "")).lower()
            if (any(p in n for p in cfg["names"]) and not any(s in n for s in skip)
                    and (must is None or must in n)):
                return c.get("id")
        return None

    main = find(skip=cfg["skip"])
    hist = find(must=cfg["hist"], skip=("women", "u-")) if cfg["hist"] else None
    return main, hist


def _score90(m):
    """Score après 90 minutes (exclut prolongations et tirs au but si fournis)."""
    s = m.get("score") or {}
    reg = s.get("regularTime") or {}
    if s.get("duration") in ("EXTRA_TIME", "PENALTY_SHOOTOUT") and reg.get("home") is not None:
        return reg
    return s.get("fullTime") or {}


def _finished(cid, key, base):
    out, year = [], datetime.utcnow().year
    for season in (year, year - 1, year - 2, year - 3):
        d = _get(f"{base}competitions/{cid}/matches", key, {"season": season, "status": "FINISHED"})
        if d.get("_status") == 429:   # quota atteint : on garde ce qu'on a
            break
        out += d.get("matches", [])
    return out


def _build(matches, cfg):
    seen, rows = set(), []
    for m in sorted(matches, key=lambda x: x.get("utcDate", "")):
        if m.get("id") in seen:
            continue
        seen.add(m.get("id"))
        h = (m.get("homeTeam") or {}).get("name")
        a = (m.get("awayTeam") or {}).get("name")
        s = _score90(m)
        gh, ga = s.get("home"), s.get("away")
        if h and a and gh is not None and ga is not None:
            rows.append((h, a, gh, ga))

    meta = {"__home_adv__": cfg["home_adv"]}
    if not rows:
        return meta, 1.30

    avg = sum(r[2] + r[3] for r in rows) / (2 * len(rows))
    elo, t = {}, {}
    for h, a, gh, ga in rows:
        # Elo : K fixe, bonus selon l'écart de buts, avantage du terrain selon la compétition
        eh, ea = elo.get(h, 1500.0), elo.get(a, 1500.0)
        exp_h = 1.0 / (1.0 + 10.0 ** (-(eh - ea + cfg["home_adv"]) / 400.0))
        res = 1.0 if gh > ga else 0.5 if gh == ga else 0.0
        d = abs(gh - ga)
        mult = 1.0 if d <= 1 else 1.5 if d == 2 else (11 + d) / 8.0
        delta = ELO_K * mult * (res - exp_h)
        elo[h], elo[a] = eh + delta, ea - delta
        for name, gf, gc in ((h, gh, ga), (a, ga, gh)):
            e = t.setdefault(name, {"gf": 0, "ga": 0, "n": 0, "hist": []})
            e["gf"] += gf
            e["ga"] += gc
            e["n"] += 1
            r = "W" if gf > gc else "D" if gf == gc else "L"
            e["hist"].append((r, 3 if r == "W" else 1 if r == "D" else 0))

    w = [0.35, 0.25, 0.20, 0.12, 0.08]
    f = cfg["field"]
    stats = dict(meta)
    for name, e in t.items():
        n = e["n"]
        gf = (e["gf"] + PRIOR_GAMES * avg) / (n + PRIOR_GAMES)
        ga = (e["ga"] + PRIOR_GAMES * avg) / (n + PRIOR_GAMES)
        last = e["hist"][-5:][::-1]                       # le plus récent d'abord
        wp = sum(w[i] * p for i, (_, p) in enumerate(last)) / sum(w[:len(last)])
        stats[name] = {
            "gf_pg": gf, "ga_pg": ga,
            "home_gf_pg": gf * (1 + f), "home_ga_pg": ga * (1 - f),
            "away_gf_pg": gf * (1 - f), "away_ga_pg": ga * (1 + f),
            "elo": elo[name],
            "form_factor": float(np.clip(0.85 + (wp / 3.0) * 0.30, 0.85, 1.15)),
            "recent_results": [r for r, _ in e["hist"][-5:]],
            # pas de vraies données cartons/corners : valeurs neutres
            "card_rate": 2.3, "corner_rate": 5.0, "midfield": 1.0, "played_total": n,
        }
    return stats, avg


@st.cache_data(ttl=3600)
def national_stats(code, key, base):
    cfg = _CFG[code]
    main, hist = _resolve(code, key, base)
    if main is None:
        st.sidebar.warning(f"{code} : compétition introuvable avec cette clé API "
                           "(elle n'est pas dans les 12 compétitions gratuites de football-data.org).")
        return {"__home_adv__": cfg["home_adv"]}, 1.30
    matches = _finished(main, key, base) + (_finished(hist, key, base) if hist else [])
    if not matches:
        st.sidebar.warning(f"{code} : aucun match terminé récupéré (accès refusé ou quota atteint).")
    return _build(matches, cfg)


def national_matches(endpoint, key, base):
    """Intercepte 'competitions/<NL|CAN>/matches' ; renvoie None pour tout le reste."""
    p = endpoint.split("/")
    if len(p) != 3 or p[0] != "competitions" or p[2] != "matches" or p[1] not in _CFG:
        return None
    main, _ = _resolve(p[1], key, base)
    if main is None:
        return {"matches": []}
    d = _get(f"{base}competitions/{main}/matches", key)
    return {"matches": []} if "_status" in d else d
