from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any

import numpy as np
import pandas as pd
import requests
import streamlit as st
from scipy.optimize import brentq, minimize
from scipy.stats import nbinom, poisson

# ==============================================================================
# 1. CONFIGURATION, SECRETS & DESIGN UI
# ==============================================================================

st.set_page_config(
    page_title="Apex Quant v50.0 Production",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    code, .quant-mono { font-family: 'JetBrains Mono', monospace; }
    .stApp { background-color: #030712; color: #F1F5F9; }
    .matrix-card {
        background: linear-gradient(135deg, #0B132B 0%, #1C2541 50%, #032B45 100%);
        border: 2px solid #38BDF8; border-radius: 18px; padding: 24px; margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(56, 189, 248, 0.25);
    }
    .sofascore-box {
        background-color: #0B0F19; border: 1px solid #1E293B; border-left: 5px solid #10B981;
        border-radius: 0 14px 14px 0; padding: 20px; margin: 16px 0; font-size: 0.95rem; line-height: 1.65; color: #E2E8F0;
    }
    .vip-banner {
        background: linear-gradient(135deg, #311042 0%, #581C87 50%, #1E3A8A 100%);
        border: 2px solid #F59E0B; border-radius: 16px; padding: 22px; text-align: center; margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(245, 158, 11, 0.2);
    }
    .sub-card {
        background: #0B1120; border: 1.5px solid #1E293B;
        border-radius: 14px; padding: 18px; margin-bottom: 16px; transition: all 0.2s ease;
    }
    .sub-card:hover { border-color: #38BDF8; }
    .option-box { background: rgba(16, 185, 129, 0.08); border: 1.5px solid #10B981; border-radius: 14px; padding: 16px; margin: 10px 0; }
    .option-box-sec { background: rgba(56, 189, 248, 0.08); border: 1.5px solid #38BDF8; border-radius: 14px; padding: 16px; margin: 10px 0; }
    .option-box-alt { background: rgba(168, 85, 247, 0.08); border: 1.5px solid #A855F7; border-radius: 14px; padding: 16px; margin: 10px 0; }
    .big-score-box { background: #0F172A; border: 2px solid #38BDF8; border-radius: 14px; padding: 16px; text-align: center; margin: 6px 0; }
    .big-score-val { font-size: 2.2rem; font-weight: 900; color: #38BDF8; line-height: 1.1; font-family: 'JetBrains Mono', monospace; }
    .big-score-prob { font-size: 1.05rem; font-weight: 700; color: #10B981; margin-top: 5px; }
    .badge-quant {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800;
        text-transform: uppercase; background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid #38BDF8; margin-right: 6px;
    }
    .badge-edge {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800;
        background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981;
    }
    .stat-badge { font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 800; color: #38BDF8; }
    </style>
    """,
    unsafe_allow_html=True,
)

FD_BASE_URL = "https://api.football-data.org/v4/"
DEFAULT_FD_API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"

COMPETITIONS: dict[str, str] = {
    "Ligue des Champions 🏆": "CL",
    "Premier League 🦁": "PL",
    "La Liga 🇪🇸": "PD",
    "Ligue 1 🇫🇷": "FL1",
    "Serie A 🇮🇹": "SA",
    "Bundesliga 🇩🇪": "BL1",
    "UEFA Europa League 🇪🇺": "EL",
    "Championship 🏴": "ELC",
}

ODDS_API_SPORTS: dict[str, str] = {
    "CL": "soccer_uefa_champs_league",
    "PL": "soccer_epl",
    "PD": "soccer_spain_la_liga",
    "FL1": "soccer_france_ligue_one",
    "SA": "soccer_italy_serie_a",
    "BL1": "soccer_germany_bundesliga",
    "EL": "soccer_uefa_europa_league",
    "ELC": "soccer_efl_champ",
}

LEAGUE_PROFILES: dict[str, dict[str, float]] = {
    "CL": {"avg_h": 1.62, "avg_a": 1.28, "rho": -0.115, "card_base": 4.1, "corner_base": 9.9, "dispersion": 9.5},
    "PL": {"avg_h": 1.58, "avg_a": 1.24, "rho": -0.110, "card_base": 3.9, "corner_base": 10.4, "dispersion": 10.0},
    "PD": {"avg_h": 1.48, "avg_a": 1.10, "rho": -0.125, "card_base": 4.8, "corner_base": 9.4, "dispersion": 9.2},
    "FL1": {"avg_h": 1.50, "avg_a": 1.16, "rho": -0.118, "card_base": 3.8, "corner_base": 9.3, "dispersion": 9.8},
    "SA": {"avg_h": 1.52, "avg_a": 1.18, "rho": -0.120, "card_base": 4.5, "corner_base": 9.8, "dispersion": 9.4},
    "BL1": {"avg_h": 1.72, "avg_a": 1.35, "rho": -0.095, "card_base": 3.9, "corner_base": 10.1, "dispersion": 11.2},
    "EL": {"avg_h": 1.56, "avg_a": 1.22, "rho": -0.112, "card_base": 4.2, "corner_base": 9.7, "dispersion": 9.6},
    "ELC": {"avg_h": 1.44, "avg_a": 1.14, "rho": -0.108, "card_base": 3.8, "corner_base": 10.2, "dispersion": 10.2},
}

HT_FT_DESCRIPTIONS: dict[str, str] = {
    "1/1": "Domicile mène à la MT et gagne le match",
    "1/X": "Domicile mène à la MT, match nul final",
    "1/2": "Renversement : Domicile mène à la MT, Extérieur gagne",
    "X/1": "Nul à la MT, Domicile gagne en 2nde MT",
    "X/X": "Nul à la MT et nul en fin de match",
    "X/2": "Nul à la MT, Extérieur gagne en 2nde MT",
    "2/1": "Renversement : Extérieur mène à la MT, Domicile gagne",
    "2/X": "Extérieur mène à la MT, match nul final",
    "2/2": "Extérieur mène à la MT et gagne le match",
}


# ==============================================================================
# 2. CLIENTS API RÉSILIENT & APPARIEMENT DES ÉQUIPES
# ==============================================================================

class ApiClientError(Exception):
    """Exception métier levée sur erreur HTTP/réseau pour éviter la mise en cache d'un échec."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(message)


def _get_secret(key_name: str, default: str | None = None) -> str | None:
    try:
        val = st.secrets.get(key_name)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key_name) or default


def _request_football_data(endpoint: str) -> dict[str, Any]:
    api_key = _get_secret("FOOTBALL_DATA_API_KEY", default=DEFAULT_FD_API_KEY)
    if not api_key:
        raise ApiClientError(401, "Clé FOOTBALL_DATA_API_KEY absente.")

    try:
        res = requests.get(f"{FD_BASE_URL}{endpoint}", headers={"X-Auth-Token": api_key}, timeout=8)
    except requests.RequestException as exc:
        raise ApiClientError(0, f"Erreur réseau football-data.org : {exc}") from exc

    if res.status_code == 200:
        return res.json()
    if res.status_code == 429:
        reset_s = res.headers.get("X-RequestCounter-Reset", "60")
        raise ApiClientError(429, f"Rate-limit football-data.org atteint. Réessayez dans ~{reset_s}s.")
    if res.status_code == 403:
        raise ApiClientError(403, "Accès refusé (403) : vérifiez votre clé ou les droits de cette ligue.")
    raise ApiClientError(res.status_code, f"Erreur HTTP {res.status_code} sur {endpoint}.")


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fd_standings(league_code: str) -> dict[str, Any]:
    return _request_football_data(f"competitions/{league_code}/standings")


@st.cache_data(ttl=300, show_spinner=False)
def fetch_fd_matches(league_code: str) -> list[dict[str, Any]]:
    return _request_football_data(f"competitions/{league_code}/matches").get("matches", [])


@st.cache_data(ttl=900, show_spinner=False)
def fetch_real_odds(
    league_code: str,
    markets: str = "h2h,totals",
    regions: str = "eu",
) -> tuple[list[dict[str, Any]], str | None]:
    """Interroge The Odds API v4 et retourne (événements, crédits restants)."""
    sport_key = ODDS_API_SPORTS.get(league_code)
    api_key = _get_secret("ODDS_API_KEY")
    if not sport_key or not api_key:
        return [], None

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
    params = {"apiKey": api_key, "regions": regions, "markets": markets, "oddsFormat": "decimal"}

    try:
        res = requests.get(url, params=params, timeout=8)
    except requests.RequestException as exc:
        raise ApiClientError(0, f"Erreur réseau The Odds API : {exc}") from exc

    remaining = res.headers.get("x-requests-remaining")
    if res.status_code == 200:
        return res.json(), remaining
    if res.status_code == 429:
        raise ApiClientError(429, "Rate-limit The Odds API atteint (429).")
    if res.status_code == 401:
        raise ApiClientError(401, "Clé ODDS_API_KEY invalide ou quota mensuel épuisé.")
    raise ApiClientError(res.status_code, f"Erreur HTTP {res.status_code} sur The Odds API.")


_TEAM_STOPWORDS = r"\b(fc|cf|sc|ac|as|afc|ssc|rc|rcd|sv|vfl|tsg|fsv|ogc|stade)\b"


def normalize_team_name(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(_TEAM_STOPWORDS, "", ascii_name.lower())
    return re.sub(r"[^a-z0-9]+", " ", cleaned).strip()


def find_matching_odds_event(
    home_fd: str,
    away_fd: str,
    odds_events: list[dict[str, Any]],
    threshold: float = 0.72,
) -> dict[str, Any] | None:
    nh, na = normalize_team_name(home_fd), normalize_team_name(away_fd)
    best_event, best_score = None, 0.0
    for ev in odds_events:
        eh = normalize_team_name(ev.get("home_team", ""))
        ea = normalize_team_name(ev.get("away_team", ""))
        score = 0.5 * (SequenceMatcher(None, nh, eh).ratio() + SequenceMatcher(None, na, ea).ratio())
        if score > best_score and score >= threshold:
            best_event, best_score = ev, score
    return best_event


# ==============================================================================
# 3. MOTEUR MATHÉMATIQUE VECTORISÉ (SHIN, DIXON-COLES, HT/FT, KELLY)
# ==============================================================================

def shin_remove_vig(odds_list: list[float]) -> tuple[list[float], float, float]:
    """Démargeage exact de Shin (1993) corrigeant le favorite-longshot bias."""
    if not odds_list or any(o <= 1.0 for o in odds_list):
        raise ValueError("Toutes les cotes décimales doivent être strictement supérieures à 1.0.")

    inv_odds = np.array([1.0 / o for o in odds_list], dtype=float)
    s = float(np.sum(inv_odds))
    margin_pct = round((s - 1.0) * 100.0, 2)
    if s <= 1.0:
        return (inv_odds / s).tolist(), margin_pct, 0.0

    def _shin_sum_diff(z: float) -> float:
        num = np.sqrt(z**2 + 4.0 * (1.0 - z) * (inv_odds**2 / s)) - z
        return float(np.sum(num / (2.0 * (1.0 - z))) - 1.0)

    z_opt = float(brentq(_shin_sum_diff, 0.0, 0.9999))
    true_probs = (
        np.sqrt(z_opt**2 + 4.0 * (1.0 - z_opt) * (inv_odds**2 / s)) - z_opt
    ) / (2.0 * (1.0 - z_opt))
    return true_probs.tolist(), margin_pct, round(z_opt, 4)


def prob_to_odds(prob_pct: float) -> float:
    if prob_pct <= 0.001:
        return 99.00
    return round(min(99.00, 100.0 / prob_pct), 2)


def calculate_quarter_kelly(
    prob_pct: float,
    bookmaker_odds: float,
    bankroll: float,
    estimation_uncertainty: float = 0.08,
    max_cap_pct: float = 0.05,
) -> tuple[float, float]:
    """Critère de Quarter-Kelly découplé du moteur matriciel."""
    if bankroll <= 0 or bookmaker_odds <= 1.0 or prob_pct <= 0.0:
        return 0.0, 0.0

    p = prob_pct / 100.0
    b = bookmaker_odds - 1.0
    ev_pct = round(((p * bookmaker_odds) - 1.0) * 100.0, 2)
    f_star = (p * bookmaker_odds - 1.0) / b
    if f_star <= 0.0:
        return 0.0, ev_pct

    f_adjusted = f_star * 0.25 * (1.0 - estimation_uncertainty)
    f_capped = min(max(0.0, f_adjusted), max_cap_pct)
    return round(bankroll * f_capped, 2), ev_pct


def extract_markets_summary(
    odds_event: dict[str, Any],
    home_name_odds: str,
    away_name_odds: str,
    target_line: float = 2.5,
) -> dict[str, Any]:
    """Extrait meilleures cotes et probabilités Shin pour h2h (1X2) et totals (O/U)."""
    best_h2h = {"1": (0.0, None), "X": (0.0, None), "2": (0.0, None)}
    best_totals = {"Over": (0.0, None), "Under": (0.0, None)}
    pin_h2h, pin_totals = None, None

    for bk in odds_event.get("bookmakers", []):
        bk_title = bk.get("title")
        markets = {m["key"]: m for m in bk.get("markets", [])}

        if "h2h" in markets:
            prices = {o["name"]: o["price"] for o in markets["h2h"].get("outcomes", [])}
            o_h, o_d, o_a = prices.get(home_name_odds), prices.get("Draw"), prices.get(away_name_odds)
            if o_h and o_d and o_a:
                if o_h > best_h2h["1"][0]: best_h2h["1"] = (o_h, bk_title)
                if o_d > best_h2h["X"][0]: best_h2h["X"] = (o_d, bk_title)
                if o_a > best_h2h["2"][0]: best_h2h["2"] = (o_a, bk_title)
                if bk.get("key") == "pinnacle":
                    pin_h2h = [o_h, o_d, o_a]

        if "totals" in markets:
            o_over, o_under = None, None
            for o in markets["totals"].get("outcomes", []):
                if o.get("point") == target_line:
                    if o.get("name") == "Over":
                        o_over = o.get("price")
                    elif o.get("name") == "Under":
                        o_under = o.get("price")
            if o_over and o_under:
                if o_over > best_totals["Over"][0]: best_totals["Over"] = (o_over, bk_title)
                if o_under > best_totals["Under"][0]: best_totals["Under"] = (o_under, bk_title)
                if bk.get("key") == "pinnacle":
                    pin_totals = [o_over, o_under]

    ref_h2h = pin_h2h or [best_h2h["1"][0], best_h2h["X"][0], best_h2h["2"][0]]
    ref_tot = pin_totals or [best_totals["Over"][0], best_totals["Under"][0]]

    shin_h2h, vig_h2h, z_h2h = (
        shin_remove_vig(ref_h2h) if all(x > 1.0 for x in ref_h2h) else ([0.0, 0.0, 0.0], 0.0, 0.0)
    )
    shin_tot, vig_tot, _ = (
        shin_remove_vig(ref_tot) if all(x > 1.0 for x in ref_tot) else ([0.0, 0.0], 0.0, 0.0)
    )

    return {
        "h2h": {"best": best_h2h, "shin_pct": [round(p * 100.0, 1) for p in shin_h2h], "vig_pct": vig_h2h, "shin_z": z_h2h},
        "totals": {"line": target_line, "best": best_totals, "shin_pct": [round(p * 100.0, 1) for p in shin_tot], "vig_pct": vig_tot},
    }


def generate_bivariate_score_matrix(
    lambda_h: float,
    lambda_a: float,
    rho: float = -0.115,
    dispersion: float = 10.0,
    max_g: int = 9,
    score_h: int = 0,
    score_a: int = 0,
) -> np.ndarray:
    """Matrice conjointe vectorisée (Binomiale Négative + Dixon-Coles)."""
    k = np.arange(max_g)
    p_x = nbinom.pmf(k, dispersion, dispersion / (dispersion + max(1e-6, lambda_h)))
    p_y = nbinom.pmf(k, dispersion, dispersion / (dispersion + max(1e-6, lambda_a)))

    rem_matrix = np.outer(p_x, p_y)
    tau_block = np.array([
        [max(0.01, 1.0 - lambda_h * lambda_a * rho), max(0.01, 1.0 + lambda_h * rho)],
        [max(0.01, 1.0 + lambda_a * rho), max(0.01, 1.0 - rho)],
    ])
    rem_matrix[:2, :2] *= tau_block

    if score_h == 0 and score_a == 0:
        tot = rem_matrix.sum()
        return rem_matrix / tot if tot > 0 else rem_matrix

    full_matrix = np.zeros((max_g, max_g), dtype=float)
    if score_h < max_g and score_a < max_g:
        full_matrix[score_h:, score_a:] = rem_matrix[: max_g - score_h, : max_g - score_a]

    tot = full_matrix.sum()
    return full_matrix / tot if tot > 0 else full_matrix


def extract_match_markets(matrix: np.ndarray) -> dict[str, Any]:
    max_g = matrix.shape[0]
    i_grid, j_grid = np.ogrid[:max_g, :max_g]
    tot_goals = i_grid + j_grid

    p_h = float(np.tril(matrix, -1).sum()) * 100.0
    p_n = float(np.diag(matrix).sum()) * 100.0
    p_a = float(np.triu(matrix, 1).sum()) * 100.0
    denom_dnb = max(0.01, p_h + p_a)

    prob_btts_yes = round(float(matrix[1:, 1:].sum()) * 100.0, 1)
    prob_o15 = round(float(matrix[tot_goals > 1].sum()) * 100.0, 1)
    prob_o25 = round(float(matrix[tot_goals > 2].sum()) * 100.0, 1)
    prob_o35 = round(float(matrix[tot_goals > 3].sum()) * 100.0, 1)

    flat_idx = np.argsort(matrix.ravel())[::-1][:3]
    top_3_scores = []
    for idx in flat_idx:
        gh, ga = np.unravel_index(idx, matrix.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "prob": round(float(matrix[gh, ga]) * 100.0, 1)})

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "prob_1x": round(p_h + p_n, 1), "prob_x2": round(p_a + p_n, 1), "prob_12": round(p_h + p_a, 1),
        "prob_dnb_h": round((p_h / denom_dnb) * 100.0, 1), "prob_dnb_a": round((p_a / denom_dnb) * 100.0, 1),
        "prob_btts_yes": prob_btts_yes, "prob_btts_no": round(100.0 - prob_btts_yes, 1),
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u25": round(100.0 - prob_o25, 1),
        "prob_o35": prob_o35, "prob_u35": round(100.0 - prob_o35, 1),
        "prob_g_1_2": round(float(matrix[(tot_goals >= 1) & (tot_goals <= 2)].sum()) * 100.0, 1),
        "prob_g_2_3": round(float(matrix[(tot_goals >= 2) & (tot_goals <= 3)].sum()) * 100.0, 1),
        "prob_g_2_4": round(float(matrix[(tot_goals >= 2) & (tot_goals <= 4)].sum()) * 100.0, 1),
        "prob_ah_h_m1": round(float(matrix[(i_grid - j_grid) >= 2].sum()) * 100.0, 1),
        "prob_ah_a_m1": round(float(matrix[(j_grid - i_grid) >= 2].sum()) * 100.0, 1),
        "top_3_scores": top_3_scores,
    }


def compute_stochastic_ht_ft_engine(
    lambda_h: float,
    lambda_a: float,
    theta_ht: float = 0.445,
    rho: float = -0.115,
    dispersion: float = 10.0,
) -> dict[str, Any]:
    """Moteur HT/FT 100% vectorisé en Binomiale Négative par différence de buts."""
    l_h1, l_a1 = lambda_h * theta_ht, lambda_a * theta_ht
    l_h2, l_a2 = lambda_h * (1.0 - theta_ht), lambda_a * (1.0 - theta_ht)
    disp_1 = max(1.0, dispersion * theta_ht)
    disp_2 = max(1.0, dispersion * (1.0 - theta_ht))

    max_g = 6
    m1 = generate_bivariate_score_matrix(l_h1, l_a1, rho=rho * 1.25, dispersion=disp_1, max_g=max_g)
    m2 = generate_bivariate_score_matrix(l_h2, l_a2, rho=0.0, dispersion=disp_2, max_g=max_g)

    ht_1 = round(float(np.tril(m1, -1).sum()) * 100.0, 1)
    ht_x = round(float(np.diag(m1).sum()) * 100.0, 1)
    ht_2 = round(float(np.triu(m1, 1).sum()) * 100.0, 1)
    ht_o05 = round(float(1.0 - m1[0, 0]) * 100.0, 1)
    ht_o15 = round(float(1.0 - (m1[0, 0] + m1[1, 0] + m1[0, 1])) * 100.0, 1)
    ht_btts = round(float(m1[1:, 1:].sum()) * 100.0, 1)

    diffs = np.arange(-(max_g - 1), max_g)
    p_d1 = np.array([np.trace(m1, offset=-int(d)) for d in diffs])
    p_d2 = np.array([np.trace(m2, offset=-int(d)) for d in diffs])

    joint_diff = np.outer(p_d1, p_d2)
    d1_grid = diffs[:, None]
    d_tot = diffs[:, None] + diffs[None, :]

    masks = {
        "1": (d1_grid > 0, d_tot > 0),
        "X": (d1_grid == 0, d_tot == 0),
        "2": (d1_grid < 0, d_tot < 0),
    }

    ht_ft_results = {}
    for r1, (m_ht, _) in masks.items():
        for r2, (_, m_ft) in masks.items():
            p_val = round(float(joint_diff[m_ht & m_ft].sum()) * 100.0, 2)
            ht_ft_results[f"{r1}/{r2}"] = {"prob": p_val, "odds": prob_to_odds(p_val)}

    return {
        "l_h1": l_h1, "l_a1": l_a1,
        "ht_1": ht_1, "ht_x": ht_x, "ht_2": ht_2,
        "ht_o05": ht_o05, "ht_u05": round(100.0 - ht_o05, 1),
        "ht_o15": ht_o15, "ht_btts": ht_btts,
        "ht_ft": ht_ft_results,
    }


def run_monte_carlo_simulation(matrix: np.ndarray, n_simulations: int = 10000, seed: int = 42) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    flat_probs = matrix.ravel()
    flat_probs = flat_probs / flat_probs.sum()
    flat_indices = rng.choice(len(flat_probs), size=n_simulations, p=flat_probs)
    h_goals, a_goals = np.unravel_index(flat_indices, matrix.shape)
    tot_goals = h_goals + a_goals

    return {
        "mc_h": round(float(np.mean(h_goals > a_goals)) * 100.0, 1),
        "mc_d": round(float(np.mean(h_goals == a_goals)) * 100.0, 1),
        "mc_a": round(float(np.mean(h_goals < a_goals)) * 100.0, 1),
        "mc_o25": round(float(np.mean(tot_goals > 2)) * 100.0, 1),
        "mc_btts": round(float(np.mean((h_goals > 0) & (a_goals > 0))) * 100.0, 1),
        "ci_low": float(np.percentile(tot_goals, 2.5)),
        "ci_high": float(np.percentile(tot_goals, 97.5)),
    }


# ==============================================================================
# 4. PRÉTRAITEMENT TEMPOREL, CALIBRATION & BACKTEST WALK-FORWARD
# ==============================================================================

def compute_advanced_momentum(history: list[dict[str, Any]]) -> tuple[float, str]:
    if not history:
        return 1.0, "Neutre / Standard"
    weights = [0.38, 0.28, 0.18, 0.10, 0.06][: len(history)]
    w_sum = sum(weights)
    perf = 0.0
    for idx, match in enumerate(history):
        pts = 3.0 if match["result"] == "W" else (1.0 if match["result"] == "D" else 0.0)
        margin_bonus = float(np.clip(match["diff"] * 0.25, -0.75, 0.75))
        perf += (weights[idx] / w_sum) * (pts + margin_bonus)

    if perf >= 2.6: return 1.16, "🔥 Dynamique Conquérante (Ascendante)"
    if perf >= 1.9: return 1.08, "✅ Forme Positive & Rassurante"
    if perf >= 1.1: return 0.98, "⚖️ Régulier / Discontinu"
    if perf >= 0.6: return 0.90, "⚠️ Instabilité & Fébrilité"
    return 0.82, "🚨 Crise Aiguë / Décrochage"


def compute_time_decayed_team_stats(
    finished_matches: list[dict[str, Any]],
    profile: dict[str, float],
    k_shrinkage: float = 3.8,
    xi_decay: float = 0.0045,
) -> tuple[dict[str, dict[str, Any]], float, float]:
    """
    Prétraitement avancé : agrège les matchs terminés avec décroissance exponentielle
    exp(-xi * jours_écoulés) et régularisation bayésienne (shrinkage K).
    """
    avg_h, avg_a = profile["avg_h"], profile["avg_a"]
    if not finished_matches:
        return {}, avg_h, avg_a

    ordered = sorted(finished_matches, key=lambda m: m.get("utcDate", ""))
    ref_date_str = ordered[-1].get("utcDate", "")[:10]
    try:
        ref_dt = datetime.strptime(ref_date_str, "%Y-%m-%d")
    except ValueError:
        ref_dt = datetime.now(timezone.utc).replace(tzinfo=None)

    acc: dict[str, dict[str, Any]] = {}
    tot_h_gf, tot_h_w, tot_a_gf, tot_a_w = 0.0, 0.0, 0.0, 0.0

    def _init() -> dict[str, Any]:
        return {
            "played": 0, "pts": 0, "gf": 0, "ga": 0,
            "h_gf_w": 0.0, "h_ga_w": 0.0, "h_w": 0.0,
            "a_gf_w": 0.0, "a_ga_w": 0.0, "a_w": 0.0,
            "last_5": [],
        }

    for m in ordered:
        sc = m.get("score", {}).get("fullTime", {})
        rh, ra = sc.get("home"), sc.get("away")
        if rh is None or ra is None:
            continue

        try:
            m_dt = datetime.strptime(m.get("utcDate", "")[:10], "%Y-%m-%d")
            days_ago = max(0, (ref_dt - m_dt).days)
        except ValueError:
            days_ago = 0
        w = float(np.exp(-xi_decay * days_ago))

        ht, at = m["homeTeam"]["name"], m["awayTeam"]["name"]
        hr, ar = acc.setdefault(ht, _init()), acc.setdefault(at, _init())

        hr["played"] += 1; ar["played"] += 1
        hr["gf"] += rh; hr["ga"] += ra
        ar["gf"] += ra; ar["ga"] += rh
        hr["h_gf_w"] += w * rh; hr["h_ga_w"] += w * ra; hr["h_w"] += w
        ar["a_gf_w"] += w * ra; ar["a_ga_w"] += w * rh; ar["a_w"] += w
        tot_h_gf += w * rh; tot_h_w += w
        tot_a_gf += w * ra; tot_a_w += w

        if rh > ra:
            hr["pts"] += 3; res_h, res_a = "W", "L"
        elif rh == ra:
            hr["pts"] += 1; ar["pts"] += 1; res_h, res_a = "D", "D"
        else:
            ar["pts"] += 3; res_h, res_a = "L", "W"

        hr["last_5"] = ([{"date": m.get("utcDate", "")[:10], "result": res_h, "diff": rh - ra}] + hr["last_5"])[:5]
        ar["last_5"] = ([{"date": m.get("utcDate", "")[:10], "result": res_a, "diff": ra - rh}] + ar["last_5"])[:5]

    if tot_h_w > 0 and tot_a_w > 0:
        avg_h = max(0.9, tot_h_gf / tot_h_w)
        avg_a = max(0.8, tot_a_gf / tot_a_w)

    league_avg_half = max(0.5, (avg_h + avg_a) / 2.0)
    stats: dict[str, dict[str, Any]] = {}
    for name, rec in acc.items():
        played = max(1, rec["played"])
        mom_f, mom_s = compute_advanced_momentum(rec["last_5"])
        stats[name] = {
            "played": played,
            "pts": rec["pts"],
            "gf": rec["gf"],
            "ga": rec["ga"],
            "home_gf_pg": (rec["h_gf_w"] + k_shrinkage * avg_h) / (rec["h_w"] + k_shrinkage),
            "home_ga_pg": (rec["h_ga_w"] + k_shrinkage * avg_a) / (rec["h_w"] + k_shrinkage),
            "away_gf_pg": (rec["a_gf_w"] + k_shrinkage * avg_a) / (rec["a_w"] + k_shrinkage),
            "away_ga_pg": (rec["a_ga_w"] + k_shrinkage * avg_h) / (rec["a_w"] + k_shrinkage),
            "elo": 1500.0 + (rec["pts"] * 13.5) + ((rec["gf"] - rec["ga"]) * 5.2),
            "momentum_factor": mom_f,
            "momentum_status": mom_s,
            "att_intensity": (rec["gf"] / played) / league_avg_half,
            "def_vulnerability": (rec["ga"] / played) / league_avg_half,
            "last_5": rec["last_5"],
        }
    return stats, avg_h, avg_a


def _predict_xg_core(
    h_stat: dict[str, Any],
    a_stat: dict[str, Any],
    avg_h: float,
    avg_a: float,
    weather_mode: str = "Normal (Idéal)",
) -> tuple[float, float, float]:
    raw_h_xg = (h_stat["home_gf_pg"] / max(0.5, avg_h)) * (a_stat["away_ga_pg"] / max(0.5, avg_h)) * avg_h
    raw_a_xg = (a_stat["away_gf_pg"] / max(0.5, avg_a)) * (h_stat["home_ga_pg"] / max(0.5, avg_a)) * avg_a

    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_mult_h = float(np.clip(1.0 + (elo_diff / 850.0), 0.52, 1.60))
    elo_mult_a = float(np.clip(1.0 - (elo_diff / 850.0), 0.52, 1.60))

    weather_mult = 0.88 if ("Pluie" in weather_mode or "Lourd" in weather_mode) else (0.92 if "Canicule" in weather_mode else 1.0)
    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * h_stat["momentum_factor"] * weather_mult, 0.22, 4.20))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * a_stat["momentum_factor"] * weather_mult, 0.20, 3.80))
    return full_h_xg, full_a_xg, elo_diff


def run_walk_forward_audit(
    finished_matches: list[dict[str, Any]],
    profile: dict[str, float],
    k_shrinkage: float = 3.8,
    rho: float | None = None,
    min_games_burnin: int = 4,
) -> dict[str, Any]:
    """Backtest chronologique strict (walk-forward) sans fuite de données."""
    ordered = sorted(finished_matches, key=lambda m: m.get("utcDate", ""))
    avg_h, avg_a = profile["avg_h"], profile["avg_a"]
    rho_val = profile["rho"] if rho is None else rho
    dispersion = profile["dispersion"]

    rolling: dict[str, dict[str, Any]] = {}
    eval_logs, brier_scores, log_losses, hits_1x2 = [], [], [], []

    def _init() -> dict[str, Any]:
        return {"played": 0, "pts": 0, "h_gf": 0, "h_ga": 0, "h_n": 0, "a_gf": 0, "a_ga": 0, "a_n": 0, "last_5": []}

    for m in ordered:
        sc = m.get("score", {}).get("fullTime", {})
        rh, ra = sc.get("home"), sc.get("away")
        if rh is None or ra is None:
            continue

        ht, at = m["homeTeam"]["name"], m["awayTeam"]["name"]
        h_rec, a_rec = rolling.setdefault(ht, _init()), rolling.setdefault(at, _init())

        if h_rec["played"] >= min_games_burnin and a_rec["played"] >= min_games_burnin:
            h_stat = {
                "home_gf_pg": (h_rec["h_gf"] + k_shrinkage * avg_h) / (h_rec["h_n"] + k_shrinkage),
                "home_ga_pg": (h_rec["h_ga"] + k_shrinkage * avg_a) / (h_rec["h_n"] + k_shrinkage),
                "elo": 1500.0 + h_rec["pts"] * 13.5 + ((h_rec["h_gf"] + h_rec["a_gf"]) - (h_rec["h_ga"] + h_rec["a_ga"])) * 5.2,
                "momentum_factor": compute_advanced_momentum(h_rec["last_5"])[0],
            }
            a_stat = {
                "away_gf_pg": (a_rec["a_gf"] + k_shrinkage * avg_a) / (a_rec["a_n"] + k_shrinkage),
                "away_ga_pg": (a_rec["a_ga"] + k_shrinkage * avg_h) / (a_rec["a_n"] + k_shrinkage),
                "elo": 1500.0 + a_rec["pts"] * 13.5 + ((a_rec["h_gf"] + a_rec["a_gf"]) - (a_rec["h_ga"] + a_rec["a_ga"])) * 5.2,
                "momentum_factor": compute_advanced_momentum(a_rec["last_5"])[0],
            }
            h_xg, a_xg, _ = _predict_xg_core(h_stat, a_stat, avg_h, avg_a)
            mk = extract_match_markets(generate_bivariate_score_matrix(h_xg, a_xg, rho=rho_val, dispersion=dispersion))

            probs = np.clip(np.array([mk["p_h"], mk["p_n"], mk["p_a"]]) / 100.0, 1e-6, 1.0)
            probs /= probs.sum()

            actual_idx = 0 if rh > ra else (1 if rh == ra else 2)
            actual_vec = np.zeros(3, dtype=float)
            actual_vec[actual_idx] = 1.0

            brier = float(np.sum((probs - actual_vec) ** 2))
            logloss = float(-np.log(probs[actual_idx]))
            brier_scores.append(brier)
            log_losses.append(logloss)
            hits_1x2.append(int(np.argmax(probs) == actual_idx))
            eval_logs.append({
                "Date": m.get("utcDate", "")[:10],
                "Affiche": f"{ht} vs {at}",
                "Score": f"{rh}-{ra}",
                "Probas 1X2": f"{mk['p_h']}% | {mk['p_n']}% | {mk['p_a']}%",
                "Brier": round(brier, 4),
                "LogLoss": round(logloss, 4),
            })

        h_rec["played"] += 1; a_rec["played"] += 1
        h_rec["h_n"] += 1; a_rec["a_n"] += 1
        h_rec["h_gf"] += rh; h_rec["h_ga"] += ra
        a_rec["a_gf"] += ra; a_rec["a_ga"] += rh

        if rh > ra:
            h_rec["pts"] += 3; res_h, res_a = "W", "L"
        elif rh == ra:
            h_rec["pts"] += 1; a_rec["pts"] += 1; res_h, res_a = "D", "D"
        else:
            a_rec["pts"] += 3; res_h, res_a = "L", "W"

        h_rec["last_5"] = ([{"result": res_h, "diff": rh - ra}] + h_rec["last_5"])[:5]
        a_rec["last_5"] = ([{"result": res_a, "diff": ra - rh}] + a_rec["last_5"])[:5]

    n_eval = len(eval_logs)
    return {
        "n_eval": n_eval,
        "brier_score": round(float(np.mean(brier_scores)), 4) if n_eval else None,
        "log_loss": round(float(np.mean(log_losses)), 4) if n_eval else None,
        "accuracy_1x2_pct": round(float(np.mean(hits_1x2)) * 100.0, 1) if n_eval else None,
        "logs": eval_logs,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def calibrate_league_hyperparameters(
    league_code: str,
    finished_matches: tuple[tuple[str, str, str, int, int], ...],
) -> tuple[float, float]:
    """Optimise (K_shrinkage, rho) par minimisation de la Log-Loss en walk-forward."""
    profile = LEAGUE_PROFILES[league_code]
    if len(finished_matches) < 40:
        return 3.8, profile["rho"]

    reconstructed = [
        {"utcDate": d, "homeTeam": {"name": h}, "awayTeam": {"name": a}, "score": {"fullTime": {"home": sh, "away": sa}}}
        for d, h, a, sh, sa in finished_matches
    ]

    def _objective(params: np.ndarray) -> float:
        k_val, rho_val = float(params[0]), float(params[1])
        audit = run_walk_forward_audit(reconstructed, profile, k_shrinkage=k_val, rho=rho_val, min_games_burnin=4)
        return audit["log_loss"] if audit["log_loss"] is not None else 2.0

    res = minimize(
        _objective,
        x0=np.array([3.8, profile["rho"]]),
        method="Nelder-Mead",
        options={"maxiter": 25, "xatol": 0.15, "fatol": 1e-3},
    )
    k_opt = float(np.clip(res.x[0], 1.5, 8.0))
    rho_opt = float(np.clip(res.x[1], -0.20, -0.02))
    return round(k_opt, 2), round(rho_opt, 4)


# ==============================================================================
# 5. MOTEUR DE PRÉDICTION UNIFIÉ & CACHE CENTRALISÉ
# ==============================================================================

def predict_single_match(
    h_name: str,
    a_name: str,
    team_stats: dict[str, dict[str, Any]],
    avg_h: float,
    avg_a: float,
    profile: dict[str, float],
    rho_override: float | None = None,
    weather_mode: str = "Normal (Idéal)",
) -> dict[str, Any]:
    default_stat = {
        "played": 10, "pts": 15, "gf": 14, "ga": 14,
        "home_gf_pg": avg_h, "home_ga_pg": avg_a,
        "away_gf_pg": avg_a, "away_ga_pg": avg_h,
        "elo": 1500.0, "momentum_factor": 1.0, "momentum_status": "Neutre",
        "att_intensity": 1.0, "def_vulnerability": 1.0, "last_5": [],
    }
    h_stat = team_stats.get(h_name, default_stat)
    a_stat = team_stats.get(a_name, default_stat)

    full_h_xg, full_a_xg, elo_diff = _predict_xg_core(h_stat, a_stat, avg_h, avg_a, weather_mode)
    rho = profile["rho"] if rho_override is None else rho_override
    dispersion = profile["dispersion"]

    matrix = generate_bivariate_score_matrix(full_h_xg, full_a_xg, rho=rho, dispersion=dispersion)
    mk = extract_match_markets(matrix)
    ht_ft_data = compute_stochastic_ht_ft_engine(full_h_xg, full_a_xg, 0.445, rho, dispersion)

    # Corners & Cartons
    tot_xg = full_h_xg + full_a_xg
    pace = (tot_xg / max(0.5, avg_h + avg_a)) ** 0.35
    dom = (full_h_xg ** 1.15) / max(0.1, full_h_xg ** 1.15 + full_a_xg ** 1.15)
    exp_c_h = profile["corner_base"] * 0.54 * (dom ** 0.55) * pace * (h_stat["att_intensity"] ** 0.3)
    exp_c_a = profile["corner_base"] * 0.46 * ((1.0 - dom) ** 0.55) * pace * (a_stat["att_intensity"] ** 0.3)
    tot_corners = round(float(np.clip(exp_c_h + exp_c_a, 5.0, 14.5)), 1)

    tension = 1.25 if abs(elo_diff) < 70.0 else (1.10 if abs(elo_diff) < 140.0 else 0.92)
    def_stress = (h_stat["def_vulnerability"] + a_stat["def_vulnerability"]) / 2.0
    tot_cards = round(float(np.clip(profile["card_base"] * tension * (def_stress ** 0.4), 2.0, 7.5)), 1)

    prob_c85 = round((1.0 - poisson.cdf(8, tot_corners)) * 100.0, 1)
    prob_cards35 = round((1.0 - poisson.cdf(3, tot_cards)) * 100.0, 1)

    # Options hiérarchisées
    options = []
    if mk["prob_1x"] >= 84.0:
        options.append({"type": "🛡️ SÉCURITÉ MAX", "desc": f"Double Chance : {h_name} ou Nul (1X)", "prob": mk["prob_1x"], "odds": prob_to_odds(mk["prob_1x"])})
    elif mk["prob_x2"] >= 84.0:
        options.append({"type": "🛡️ SÉCURITÉ MAX", "desc": f"Double Chance : Nul ou {a_name} (X2)", "prob": mk["prob_x2"], "odds": prob_to_odds(mk["prob_x2"])})
    elif mk["prob_o15"] >= 78.0:
        options.append({"type": "🛡️ SÉCURITÉ MAX", "desc": "Plus de 1.5 Buts dans le match", "prob": mk["prob_o15"], "odds": prob_to_odds(mk["prob_o15"])})
    else:
        options.append({"type": "🛡️ SÉCURITÉ MAX", "desc": "Moins de 3.5 Buts dans le match", "prob": mk["prob_u35"], "odds": prob_to_odds(mk["prob_u35"])})

    if mk["p_h"] >= 52.0:
        options.append({"type": "🎯 VALUE BET PRINCIPAL", "desc": f"Victoire Sèche : {h_name}", "prob": mk["p_h"], "odds": prob_to_odds(mk["p_h"])})
    elif mk["p_a"] >= 52.0:
        options.append({"type": "🎯 VALUE BET PRINCIPAL", "desc": f"Victoire Sèche : {a_name}", "prob": mk["p_a"], "odds": prob_to_odds(mk["p_a"])})
    elif mk["prob_btts_yes"] >= 58.0:
        options.append({"type": "🎯 VALUE BET PRINCIPAL", "desc": "Les Deux Équipes Marquent (BTTS)", "prob": mk["prob_btts_yes"], "odds": prob_to_odds(mk["prob_btts_yes"])})
    else:
        options.append({"type": "🎯 VALUE BET PRINCIPAL", "desc": "Plus de 2.5 Buts (Match Ouvert)", "prob": mk["prob_o25"], "odds": prob_to_odds(mk["prob_o25"])})

    if abs(elo_diff) > 130.0:
        fav, ah_p = (h_name, mk["prob_ah_h_m1"]) if mk["p_h"] >= mk["p_a"] else (a_name, mk["prob_ah_a_m1"])
        options.append({"type": "⚡ SCÉNARIO QUANT TACTIQUE", "desc": f"Handicap Asiatique : {fav} (-1.0)", "prob": ah_p, "odds": prob_to_odds(ah_p)})
    elif mk["prob_btts_no"] >= 55.0:
        options.append({"type": "⚡ SCÉNARIO QUANT TACTIQUE", "desc": "BTTS Non", "prob": mk["prob_btts_no"], "odds": prob_to_odds(mk["prob_btts_no"])})
    else:
        options.append({"type": "⚡ SCÉNARIO QUANT TACTIQUE", "desc": "Fourchette Multi-Buts : 2 à 4 Buts", "prob": mk["prob_g_2_4"], "odds": prob_to_odds(mk["prob_g_2_4"])})

    dom_team = h_name if elo_diff >= 0 else a_name
    press_desc = (
        f"Contrôle territorial appuyé de <b>{dom_team}</b> (xG {max(full_h_xg, full_a_xg):.2f})."
        if abs(elo_diff) > 90.0 else
        "Duel tactique équilibré au milieu de terrain."
    )
    report = (
        f"📊 <b>Rapport Dixon-Coles & Binomiale Négative</b> :<br>"
        f"• 🏠 <b>{h_name}</b> (ELO {h_stat['elo']:.0f} | {h_stat['momentum_status']}) : xG = <b>{full_h_xg:.2f}</b> [MT: <b>{ht_ft_data['l_h1']:.2f}</b>]<br>"
        f"• ✈️ <b>{a_name}</b> (ELO {a_stat['elo']:.0f} | {a_stat['momentum_status']}) : xG = <b>{full_a_xg:.2f}</b> [MT: <b>{ht_ft_data['l_a1']:.2f}</b>]<br>"
        f"• ⚔️ <b>Configuration</b> : {press_desc}<br>"
        f"• ⛳ <b>Corners</b> : ~<b>{tot_corners}</b> (+8.5 : <b>{prob_c85}%</b>) | 🟨 <b>Cartons</b> : ~<b>{tot_cards}</b> (+3.5 : <b>{prob_cards35}%</b>)"
    )

    return {
        **mk,
        "matrix": matrix,
        "options": options,
        "corners": tot_corners,
        "prob_c85": prob_c85,
        "cards": tot_cards,
        "prob_cards35": prob_cards35,
        "sofascore_report": report,
        "full_h_xg": full_h_xg,
        "full_a_xg": full_a_xg,
        "ht_ft": ht_ft_data,
    }


@st.cache_data(ttl=900, show_spinner="Calcul des matrices quantitatives...")
def build_predictions_cache(
    league_code: str,
    weather_condition: str,
    k_shrinkage: float,
    rho_val: float,
    upcoming_keys: tuple[tuple[int, str, str], ...],
    finished_keys: tuple[tuple[str, str, str, int, int], ...],
) -> dict[int, dict[str, Any]]:
    profile = LEAGUE_PROFILES[league_code]
    finished_list = [
        {"utcDate": d, "homeTeam": {"name": h}, "awayTeam": {"name": a}, "score": {"fullTime": {"home": sh, "away": sa}}}
        for d, h, a, sh, sa in finished_keys
    ]
    team_stats, avg_h, avg_a = compute_time_decayed_team_stats(finished_list, profile, k_shrinkage=k_shrinkage)

    return {
        m_id: predict_single_match(ht, at, team_stats, avg_h, avg_a, profile, rho_override=rho_val, weather_mode=weather_condition)
        for m_id, ht, at in upcoming_keys
    }


# ==============================================================================
# 6. INTERFACE STREAMLIT PRODUCTION
# ==============================================================================

st.sidebar.markdown(
    """
    <div style="text-align:center; padding:10px 0;">
        <h2 style="color:#38BDF8; margin:0; font-weight:900;">APEX QUANT</h2>
        <span style="font-size:0.8rem; letter-spacing:2px; color:#F59E0B; font-weight:800;">PRODUCTION v50.0</span>
    </div>
    """,
    unsafe_allow_html=True,
)

selected_comp = st.sidebar.selectbox("🏆 Compétition Analysée", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]
profile = LEAGUE_PROFILES[league_code]

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ CALIBRATION & MÉTÉO")
weather_condition = st.sidebar.selectbox("Conditions Météo & Pelouse", ["Normal (Idéal)", "Pluie / Terrain Lourd & Glissant", "Canicule / Chaleur Élevée"])
enable_auto_tuning = st.sidebar.checkbox("Auto-tuning hyperparamètres (Log-Loss)", value=False)

st.sidebar.divider()
st.sidebar.markdown("### 💰 GESTION DE CAPITAL (QUARTER-KELLY)")
user_bankroll = st.sidebar.number_input("Capital / Bankroll ($ / € / FCFA)", value=1000.0, step=50.0, min_value=10.0)

try:
    all_matches = fetch_fd_matches(league_code)
except ApiClientError as err:
    if err.status_code == 429:
        st.warning(f"⏳ {err}")
    else:
        st.error(f"🚨 {err}")
    st.stop()

now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
next_week_utc = now_utc + timedelta(days=8)

upcoming_matches: list[dict[str, Any]] = []
finished_matches: list[dict[str, Any]] = []

for m in all_matches:
    status = m.get("status")
    if status == "FINISHED":
        finished_matches.append(m)
    elif status in ("SCHEDULED", "TIMED"):
        utc_str = m.get("utcDate", "")
        if utc_str:
            try:
                m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                if now_utc - timedelta(hours=3) <= m_dt <= next_week_utc:
                    upcoming_matches.append(m)
            except ValueError:
                pass

finished_keys = tuple(
    (
        m.get("utcDate", ""),
        m["homeTeam"]["name"],
        m["awayTeam"]["name"],
        m["score"]["fullTime"]["home"],
        m["score"]["fullTime"]["away"],
    )
    for m in finished_matches
    if m.get("score", {}).get("fullTime", {}).get("home") is not None
)

if enable_auto_tuning:
    k_opt, rho_opt = calibrate_league_hyperparameters(league_code, finished_keys)
    st.sidebar.caption(f"🎯 Calibré : K={k_opt} | ρ={rho_opt}")
else:
    k_opt, rho_opt = 3.8, profile["rho"]

upcoming_keys = tuple((m["id"], m["homeTeam"]["name"], m["awayTeam"]["name"]) for m in upcoming_matches)
predictions_by_id = build_predictions_cache(league_code, weather_condition, k_opt, rho_opt, upcoming_keys, finished_keys)

match_map = {
    f"{m['utcDate'][:10]} {m['utcDate'][11:16]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m
    for m in upcoming_matches
}

# Chargement optionnel des cotes réelles The Odds API
odds_events: list[dict[str, Any]] = []
odds_error_msg: str | None = None
try:
    odds_events, credits_left = fetch_real_odds(league_code)
    if credits_left is not None:
        st.sidebar.caption(f"📡 Quota The Odds API restant : {credits_left}")
except ApiClientError as err:
    odds_error_msg = str(err)

tab_scanner, tab_ht_ft, tab_detail, tab_cal, tab_monte_carlo, tab_audit, tab_coupon = st.tabs([
    "🔍 SCANNER VALUE BETS PRO",
    "⏱️ MI-TEMPS & FIN DE MATCH (HT/FT)",
    "📊 ANALYSE MATCH & DÉRIVÉS",
    f"📅 CALENDRIER QUANT ({len(upcoming_matches)})",
    "🎲 MONTE CARLO & SHIN",
    f"📈 AUDIT WALK-FORWARD ({len(finished_matches)})",
    "🎟️ COMBINÉ QUANTIFIÉ",
])

# ------------------------------------------------------------------------------
# ONGLET 1 : SCANNER VALUE BETS RÉELS
# ------------------------------------------------------------------------------
with tab_scanner:
    st.markdown(
        """
        <div class="vip-banner">
            <h2 style="margin:0; color:#38BDF8;">🔍 SCANNER QUANTITATIF DE VALUE BETS</h2>
            <span style="font-size:0.95rem; color:#E2E8F0;">Comparaison directe Dixon-Coles vs. cotes réelles & consensus Shin</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if odds_error_msg:
        st.warning(f"⚠️ Flux The Odds API indisponible : {odds_error_msg}")
    elif not odds_events:
        st.info("ℹ️ Renseignez `ODDS_API_KEY` dans `.streamlit/secrets.toml` pour activer les cotes bookmakers en direct. En mode hors-ligne, le tableau affiche les cotes minimales requises.")

    if upcoming_matches:
        min_ev_threshold = st.slider("Seuil minimum d'Expected Value (EV%) :", min_value=-2.0, max_value=15.0, value=2.0, step=0.5)
        scanner_rows = []

        for m in upcoming_matches:
            ht, at = m["homeTeam"]["name"], m["awayTeam"]["name"]
            pred = predictions_by_id[m["id"]]
            matched_ev = find_matching_odds_event(ht, at, odds_events) if odds_events else None

            if matched_ev:
                summary = extract_markets_summary(matched_ev, matched_ev["home_team"], matched_ev["away_team"], target_line=2.5)
                candidates = [
                    (f"1 ({ht})", pred["p_h"], summary["h2h"]["shin_pct"][0], *summary["h2h"]["best"]["1"]),
                    ("Nul (X)", pred["p_n"], summary["h2h"]["shin_pct"][1], *summary["h2h"]["best"]["X"]),
                    (f"2 ({at})", pred["p_a"], summary["h2h"]["shin_pct"][2], *summary["h2h"]["best"]["2"]),
                    ("Plus de 2.5 Buts", pred["prob_o25"], summary["totals"]["shin_pct"][0], *summary["totals"]["best"]["Over"]),
                    ("Moins de 2.5 Buts", pred["prob_u25"], summary["totals"]["shin_pct"][1], *summary["totals"]["best"]["Under"]),
                ]
                for label, p_mod, p_shin, best_odd, bookie in candidates:
                    if not best_odd or best_odd <= 1.0:
                        continue
                    kelly_st, ev_val = calculate_quarter_kelly(p_mod, best_odd, user_bankroll)
                    if ev_val >= min_ev_threshold:
                        scanner_rows.append({
                            "Match": f"{ht} vs {at}",
                            "Date": f"{m['utcDate'][:10]} {m['utcDate'][11:16]}",
                            "Marché": label,
                            "Proba Modèle": f"{p_mod}%",
                            "Proba Shin": f"{p_shin}%",
                            "Meilleure Cote": f"{best_odd} ({bookie})",
                            "EV (%)": ev_val,
                            "Mise Kelly (1/4)": f"{kelly_st} $",
                        })
            else:
                for label, p_mod in [(f"1 ({ht})", pred["p_h"]), ("Nul (X)", pred["p_n"]), (f"2 ({at})", pred["p_a"]), ("Plus de 2.5 Buts", pred["prob_o25"])]:
                    fair_o = prob_to_odds(p_mod)
                    min_req = round(fair_o * (1.0 + min_ev_threshold / 100.0), 2)
                    scanner_rows.append({
                        "Match": f"{ht} vs {at}",
                        "Date": f"{m['utcDate'][:10]} {m['utcDate'][11:16]}",
                        "Marché": label,
                        "Proba Modèle": f"{p_mod}%",
                        "Cote Équitable": fair_o,
                        f"Cote Min. (EV ≥ {min_ev_threshold}%)": min_req,
                    })

        if scanner_rows:
            df_scan = pd.DataFrame(scanner_rows)
            if "EV (%)" in df_scan.columns:
                df_scan = df_scan.sort_values(by="EV (%)", ascending=False)
                st.dataframe(df_scan.style.format({"EV (%)": "{:+.2f}%"}), use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_scan, use_container_width=True, hide_index=True)
        else:
            st.warning("Aucune opportunité ne dépasse ce seuil d'Expected Value.")
    else:
        st.info("Aucun match à venir dans les 8 prochains jours.")

# ------------------------------------------------------------------------------
# ONGLET 2 : HT/FT VECTORISÉ
# ------------------------------------------------------------------------------
with tab_ht_ft:
    st.markdown(
        """
        <div class="vip-banner">
            <h2 style="margin:0; color:#F59E0B;">⏱️ MODÉLISATION STOCHASTIQUE MI-TEMPS & FIN DE MATCH</h2>
            <span style="font-size:0.95rem; color:#E2E8F0;">Binomiale Négative cohérente (44.5% / 55.5%) et convolution vectorisée des 9 issues</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if upcoming_matches:
        sel_ht_label = st.selectbox("Sélectionnez la rencontre :", list(match_map.keys()), key="ht_select")
        m_ht = match_map[sel_ht_label]
        ht_t, at_t = m_ht["homeTeam"]["name"], m_ht["awayTeam"]["name"]
        ht_res = predictions_by_id[m_ht["id"]]["ht_ft"]

        h1, h2, h3, h4 = st.columns(4)
        with h1: st.markdown(f"<div class='sub-card'><b>xG 1ÈRE MI-TEMPS</b><br>🏠 {ht_t} : <b style='color:#38BDF8;'>{ht_res['l_h1']:.2f}</b><br>✈️ {at_t} : <b style='color:#38BDF8;'>{ht_res['l_a1']:.2f}</b></div>", unsafe_allow_html=True)
        with h2: st.markdown(f"<div class='sub-card'><b>1N2 MI-TEMPS</b><br>1 : <b>{ht_res['ht_1']}%</b><br>N : <b>{ht_res['ht_x']}%</b><br>2 : <b>{ht_res['ht_2']}%</b></div>", unsafe_allow_html=True)
        with h3: st.markdown(f"<div class='sub-card'><b>BUTS MI-TEMPS</b><br>Over 0.5 MT : <b style='color:#10B981;'>{ht_res['ht_o05']}%</b><br>Under 0.5 MT : <b>{ht_res['ht_u05']}%</b><br>Over 1.5 MT : <b>{ht_res['ht_o15']}%</b></div>", unsafe_allow_html=True)
        with h4: st.markdown(f"<div class='sub-card'><b>BTTS MI-TEMPS</b><br>Les 2 marquent en 1MT :<br><b style='color:#F59E0B; font-size:1.4rem;'>{ht_res['ht_btts']}%</b></div>", unsafe_allow_html=True)

        df_htft = pd.DataFrame([
            {"Scénario HT/FT": k, "Description": HT_FT_DESCRIPTIONS[k], "Probabilité": f"{v['prob']}%", "Cote Équitable": v["odds"]}
            for k, v in ht_res["ht_ft"].items()
        ])
        st.dataframe(df_htft, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match disponible.")

# ------------------------------------------------------------------------------
# ONGLET 3 : ANALYSE MATCH & KELLY
# ------------------------------------------------------------------------------
with tab_detail:
    if upcoming_matches:
        chosen_label = st.selectbox("Sélectionnez l'affiche :", list(match_map.keys()), key="detail_select")
        m_obj = match_map[chosen_label]
        ht, at = m_obj["homeTeam"]["name"], m_obj["awayTeam"]["name"]
        res = predictions_by_id[m_obj["id"]]
        best_opt = res["options"][0]

        c1, c2 = st.columns([1, 1])
        with c1:
            input_odds = st.number_input("Cote réelle du bookmaker pour l'Option n°1 :", value=float(best_opt["odds"]), step=0.02, min_value=1.01)
        with c2:
            st.markdown("<div style='padding-top:25px;'><span class='badge-quant'>Dixon-Coles Vectorisé</span><span class='badge-edge'>Negative Binomial</span></div>", unsafe_allow_html=True)

        kelly_stake, ev_pct = calculate_quarter_kelly(best_opt["prob"], input_odds, user_bankroll)

        st.markdown(
            f"""
            <div class="matrix-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h1 style="color:#38BDF8; margin:0; font-size:2rem;">{ht} <span style="color:#94A3B8; font-weight:300;">vs</span> {at}</h1>
                    <span class="badge-quant" style="font-size:0.9rem;">xG Total : {(res['full_h_xg'] + res['full_a_xg']):.2f}</span>
                </div>
                <div class="sofascore-box">{res['sofascore_report']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for opt in res["options"]:
            cls = "option-box" if "SÉCURITÉ" in opt["type"] else ("option-box-sec" if "VALUE" in opt["type"] else "option-box-alt")
            st.markdown(
                f"""
                <div class="{cls}">
                    <div style="font-size:0.8rem; font-weight:800; color:#38BDF8;">{opt['type']}</div>
                    <div style="font-size:1.3rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{opt['desc']}</div>
                    <div style="font-size:1rem; font-weight:700; color:#10B981;">Probabilité : <b>{opt['prob']}%</b> | Cote Équitable : <b>{opt['odds']}</b></div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        col_k, col_sc = st.columns([1, 2])
        with col_k:
            st.markdown("### 💰 OPTIMISATION KELLY")
            ev_sign = "+" if ev_pct >= 0 else ""
            st.metric("Mise Conseillée (1/4 Kelly)", f"{kelly_stake} $", f"EV : {ev_sign}{ev_pct}%")
        with col_sc:
            st.markdown("### 🏆 TOP 3 SCORES EXACTS")
            sc_cols = st.columns(3)
            for idx, col in enumerate(sc_cols):
                with col:
                    st.markdown(
                        f"<div class='big-score-box'><b>#{idx+1} SCORE</b><div class='big-score-val'>{res['top_3_scores'][idx]['score']}</div><div class='big-score-prob'>{res['top_3_scores'][idx]['prob']}%</div></div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.info("Aucun match disponible.")

# ------------------------------------------------------------------------------
# ONGLET 4 : CALENDRIER QUANT
# ------------------------------------------------------------------------------
with tab_cal:
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            ht, at = m["homeTeam"]["name"], m["awayTeam"]["name"]
            pred = predictions_by_id[m["id"]]
            cal_data.append({
                "Date [UTC]": f"{m['utcDate'][:10]} {m['utcDate'][11:16]}",
                "Rencontre": f"{ht} vs {at}",
                "1X2 Équitable": f"{pred['p_h']}% | {pred['p_n']}% | {pred['p_a']}%",
                "Option Sécurité": f"{pred['options'][0]['desc']} ({pred['options'][0]['prob']}%)",
                "Over 1.5": f"{pred['prob_o15']}%",
                "Over 0.5 MT": f"{pred['ht_ft']['ht_o05']}%",
                "Corners": f"~{pred['corners']}",
                "Cartons": f"~{pred['cards']}",
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match à afficher.")

# ------------------------------------------------------------------------------
# ONGLET 5 : MONTE CARLO & SHIN
# ------------------------------------------------------------------------------
with tab_monte_carlo:
    st.markdown("<div class='vip-banner'><h2 style='margin:0; color:#38BDF8;'>🎲 MONTE CARLO & DÉMARGEAGE SHIN</h2></div>", unsafe_allow_html=True)
    if upcoming_matches:
        mc_label = st.selectbox("Match pour simulation :", list(match_map.keys()), key="mc_tab_select")
        mc_obj = match_map[mc_label]
        mc_res = predictions_by_id[mc_obj["id"]]
        mc_stats = run_monte_carlo_simulation(mc_res["matrix"], 10000)

        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric("Domicile (MC)", f"{mc_stats['mc_h']}%", f"Modèle: {mc_res['p_h']}%")
        with k2: st.metric("Nul (MC)", f"{mc_stats['mc_d']}%", f"Modèle: {mc_res['p_n']}%")
        with k3: st.metric("Extérieur (MC)", f"{mc_stats['mc_a']}%", f"Modèle: {mc_res['p_a']}%")
        with k4: st.metric("Over 2.5 (MC)", f"{mc_stats['mc_o25']}%", f"IC 95%: [{int(mc_stats['ci_low'])}-{int(mc_stats['ci_high'])} buts]")

        st.markdown("### 📐 Calculateur Shin (Démargeage Bookmaker 1X2)")
        s1, s2, s3 = st.columns(3)
        with s1: o1 = st.number_input("Cote 1", value=2.10, min_value=1.02, step=0.05)
        with s2: ox = st.number_input("Cote X", value=3.40, min_value=1.02, step=0.05)
        with s3: o2 = st.number_input("Cote 2", value=3.50, min_value=1.02, step=0.05)

        shin_p, vig, z_val = shin_remove_vig([o1, ox, o2])
        st.info(f"Marge bookmaker : **{vig}%** | Indice d'initiés Shin ($z$) : **{z_val}** → Probabilités justes : **1: {shin_p[0]*100:.1f}% | X: {shin_p[1]*100:.1f}% | 2: {shin_p[2]*100:.1f}%**")
    else:
        st.info("Aucun match disponible.")

# ------------------------------------------------------------------------------
# ONGLET 6 : AUDIT WALK-FORWARD (ZÉRO DATA LEAKAGE)
# ------------------------------------------------------------------------------
with tab_audit:
    st.markdown("<div class='vip-banner'><h2 style='margin:0; color:#F59E0B;'>📈 AUDIT CHRONOLOGIQUE WALK-FORWARD</h2></div>", unsafe_allow_html=True)
    if finished_matches:
        audit = run_walk_forward_audit(finished_matches, profile, k_shrinkage=k_opt, rho=rho_opt, min_games_burnin=4)
        if audit["n_eval"] > 0:
            a1, a2, a3, a4 = st.columns(4)
            with a1: st.metric("Matchs Audités", f"{audit['n_eval']}")
            with a2: st.metric("Brier Score (1X2)", f"{audit['brier_score']}", "Aléatoire = 0.667")
            with a3: st.metric("Log-Loss (1X2)", f"{audit['log_loss']}", "Aléatoire = 1.099")
            with a4: st.metric("Précision 1X2", f"{audit['accuracy_1x2_pct']}%")
            st.dataframe(pd.DataFrame(audit["logs"][::-1]), use_container_width=True, hide_index=True)
        else:
            st.info("Pas assez de matchs terminés après la période de chauffe (4 matchs/équipe).")
    else:
        st.info("Aucun match terminé à auditer.")

# ------------------------------------------------------------------------------
# ONGLET 7 : COMBINÉ QUANTIFIÉ
# ------------------------------------------------------------------------------
with tab_coupon:
    st.subheader("🎟️ Ticket Combiné Quantifié (Top 5 Sécurité)")
    if upcoming_matches:
        candidates = []
        for m in upcoming_matches:
            ht, at = m["homeTeam"]["name"], m["awayTeam"]["name"]
            pred = predictions_by_id[m["id"]]
            top_opt = pred["options"][0]
            candidates.append({
                "match": f"{ht} vs {at}",
                "pick": top_opt["desc"],
                "prob": top_opt["prob"],
                "odds": top_opt["odds"],
            })
        candidates.sort(key=lambda x: x["prob"], reverse=True)
        top_5 = candidates[:5]
        combined_odds = float(np.prod([x["odds"] for x in top_5]))
        joint_prob = float(np.prod([x["prob"] / 100.0 for x in top_5])) * 100.0

        st.markdown(
            f"""
            <div class="vip-banner">
                <h2 style="margin:0; color:#F59E0B;">🛡️ COMBINÉ SÉCURITÉ APEX (TOP {len(top_5)})</h2>
                <div style="font-size:1.5rem; font-weight:900; color:#FFFFFF; margin-top:8px;">
                    Cote Équitable Combinée : <span style="color:#38BDF8;">{combined_odds:.2f}</span> |
                    Probabilité Jointe Réelle : <span style="color:#10B981;">{joint_prob:.1f}%</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for idx, item in enumerate(top_5, 1):
            st.markdown(
                f"<div class='sub-card'><b>{idx}. {item['match']}</b><br>👉 <b style='color:#10B981;'>{item['pick']}</b> | Proba : <b>{item['prob']}%</b> (Cote : <b>{item['odds']}</b>)</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Aucun match disponible pour générer un combiné.")
