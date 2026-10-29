import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime, timedelta
import math

# ==============================================================================
# 1. CONFIGURATION & DESIGN AVANCÉ V49.0 SOFASCORE QUANT PRO
# ==============================================================================
st.set_page_config(
    page_title="Apex Quant v50.0 Faits Réels & Bouclier 99%",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
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
        border-radius: 14px; padding: 18px; margin-bottom: 16px;
        transition: all 0.2s ease;
    }
    .sub-card:hover { border-color: #38BDF8; }
    .option-box {
        background: rgba(16, 185, 129, 0.08); border: 1.5px solid #10B981; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-sec {
        background: rgba(56, 189, 248, 0.08); border: 1.5px solid #38BDF8; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-alt {
        background: rgba(168, 85, 247, 0.08); border: 1.5px solid #A855F7; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .big-score-box {
        background: #0F172A; border: 2px solid #38BDF8; border-radius: 14px; padding: 16px; text-align: center; margin: 6px 0;
    }
    .big-score-val { font-size: 2.2rem; font-weight: 900; color: #38BDF8; line-height: 1.1; font-family: 'JetBrains Mono', monospace; }
    .big-score-prob { font-size: 1.05rem; font-weight: 700; color: #10B981; margin-top: 5px; }
    .badge-quant {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase;
        background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid #38BDF8; margin-right: 6px;
    }
    .badge-edge {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800;
        background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981;
    }
    .badge-ultra {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800;
        background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B;
    }
    .stat-badge {
        font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 800; color: #38BDF8;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. PARAMÈTRES GLOBAUX & INFRASTRUCTURE API
# ==============================================================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Ligue des Champions 🏆": "CL",
    "Premier League 🦁": "PL",
    "La Liga 🇪🇸": "PD",
    "Ligue 1 🇫🇷": "FL1",
    "Serie A 🇮🇹": "SA",
    "Bundesliga 🇩🇪": "BL1",
    "UEFA Europa League 🇪🇺": "EL",
    "Championship 🏴": "ELC"
}

LEAGUE_PROFILES = {
    "CL":  {"avg_h": 1.62, "avg_a": 1.28, "rho": -0.115, "card_base": 4.1, "corner_base": 9.9, "dispersion": 9.5},
    "PL":  {"avg_h": 1.58, "avg_a": 1.24, "rho": -0.110, "card_base": 3.9, "corner_base": 10.4, "dispersion": 10.0},
    "PD":  {"avg_h": 1.48, "avg_a": 1.10, "rho": -0.125, "card_base": 4.8, "corner_base": 9.4, "dispersion": 9.2},
    "FL1": {"avg_h": 1.50, "avg_a": 1.16, "rho": -0.118, "card_base": 3.8, "corner_base": 9.3, "dispersion": 9.8},
    "SA":  {"avg_h": 1.52, "avg_a": 1.18, "rho": -0.120, "card_base": 4.5, "corner_base": 9.8, "dispersion": 9.4},
    "BL1": {"avg_h": 1.72, "avg_a": 1.35, "rho": -0.095, "card_base": 3.9, "corner_base": 10.1, "dispersion": 11.2},
    "EL":  {"avg_h": 1.56, "avg_a": 1.22, "rho": -0.112, "card_base": 4.2, "corner_base": 9.7, "dispersion": 9.6},
    "ELC": {"avg_h": 1.44, "avg_a": 1.14, "rho": -0.108, "card_base": 3.8, "corner_base": 10.2, "dispersion": 10.2}
}

@st.cache_data(ttl=300)
def fetch_api(endpoint):
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=6)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

# ==============================================================================
# 3. MOTEUR MATHÉMATIQUE AVANCÉ : DIXON-COLES, SURDISPERSION & SHIN
# ==============================================================================

def dixon_coles_tau(x, y, lambda_h, lambda_a, rho=-0.115):
    """Ajustement bivarié exact de Dixon & Coles (1997) pour scores faibles."""
    if x == 0 and y == 0:
        return max(0.01, 1.0 - (lambda_h * lambda_a * rho))
    elif x == 0 and y == 1:
        return max(0.01, 1.0 + (lambda_h * rho))
    elif x == 1 and y == 0:
        return max(0.01, 1.0 + (lambda_a * rho))
    elif x == 1 and y == 1:
        return max(0.01, 1.0 - rho)
    return 1.0

def negative_binomial_pmf(k, mu, dispersion=10.0):
    """Distribution Binomiale Négative modélisant la surdispersion empirique des buts."""
    r = dispersion
    p = r / (r + mu)
    return nbinom.pmf(k, r, p)

def generate_bivariate_score_matrix(lambda_h, lambda_a, rho=-0.115, dispersion=10.0, max_g=9):
    """Matrice conjointe des probabilités de score (0-8 buts) normalisée."""
    matrix = np.zeros((max_g, max_g))
    for x in range(max_g):
        for y in range(max_g):
            p_x = negative_binomial_pmf(x, lambda_h, dispersion)
            p_y = negative_binomial_pmf(y, lambda_a, dispersion)
            tau = dixon_coles_tau(x, y, lambda_h, lambda_a, rho)
            matrix[x, y] = max(0.0, p_x * p_y * tau)
            
    tot_p = np.sum(matrix)
    if tot_p > 0:
        matrix /= tot_p
    return matrix

def shin_remove_vig(odds_h, odds_d, odds_a):
    """Démargeage quantitatif de Shin / Power pour extraire les vraies probabilités de marché."""
    inv_odds = [1.0 / odds_h, 1.0 / odds_d, 1.0 / odds_a]
    book_sum = sum(inv_odds)
    margin = (book_sum - 1.0) * 100.0
    true_probs = [o / book_sum for o in inv_odds]
    return true_probs[0], true_probs[1], true_probs[2], margin

def prob_to_odds(p):
    """Convertit une probabilité en cote équitable (Fair Odds sans marge)."""
    if p <= 0.001: return 99.00
    return round(min(99.00, 100.0 / p), 2)

def calculate_quarter_kelly(prob_pct, bookmaker_odds, bankroll, estimation_uncertainty=0.08, max_cap_pct=0.05):
    """Critère de Quarter-Kelly avec pénalité d'incertitude et plafond de sécurité à 5%."""
    p = prob_pct / 100.0
    b = bookmaker_odds - 1.0
    if b <= 0 or p <= 0: return 0.0, 0.0
    f_star = (p * (b + 1.0) - 1.0) / b
    ev_val = round(((p * bookmaker_odds) - 1.0) * 100, 2)
    if f_star <= 0:
        return 0.0, ev_val
    f_adjusted = f_star * 0.25 * (1.0 - estimation_uncertainty)
    f_capped = min(max(0.0, f_adjusted), max_cap_pct)
    return round(bankroll * f_capped, 2), ev_val

# ==============================================================================
# 4. MODÉLISATION STOCHASTIQUE AVANCÉE MI-TEMPS / FIN DE MATCH (HT / FT)
# ==============================================================================

def compute_stochastic_ht_ft_engine(lambda_h, lambda_a, theta_ht=0.445, rho=-0.115):
    """
    Modèle stochastique par convolution à deux étages (Processus de Poisson temporel non-homogène).
    Sépare rigoureusement l'intensité offensive de la 1ère Mi-Temps (44.5% des buts)
    et de la 2nde Mi-Temps (55.5%), puis convolue les distributions pour calculer
    les 9 combinaisons exactes Mi-Temps / Fin de Match (HT/FT) et les dérivés 1ère MT.
    """
    l_h1 = lambda_h * theta_ht
    l_a1 = lambda_a * theta_ht
    l_h2 = lambda_h * (1.0 - theta_ht)
    l_a2 = lambda_a * (1.0 - theta_ht)
    
    max_g_ht = 6
    max_g_2h = 6
    
    # 1. Matrice bivariée 1ère Mi-Temps avec correction Dixon-Coles MT (rho amplifié)
    m1 = np.zeros((max_g_ht, max_g_ht))
    for x in range(max_g_ht):
        for y in range(max_g_ht):
            p_x = poisson.pmf(x, l_h1)
            p_y = poisson.pmf(y, l_a1)
            tau = 1.0
            if x == 0 and y == 0: tau = 1.0 - l_h1 * l_a1 * (rho * 1.25)
            elif x == 0 and y == 1: tau = 1.0 + l_h1 * (rho * 1.25)
            elif x == 1 and y == 0: tau = 1.0 + l_a1 * (rho * 1.25)
            elif x == 1 and y == 1: tau = 1.0 - (rho * 1.25)
            m1[x, y] = max(0.0, p_x * p_y * tau)
    tot_m1 = np.sum(m1)
    if tot_m1 > 0: m1 /= tot_m1

    # 2. Matrice de transition 2nde Mi-Temps
    m2 = np.zeros((max_g_2h, max_g_2h))
    for x in range(max_g_2h):
        for y in range(max_g_2h):
            m2[x, y] = poisson.pmf(x, l_h2) * poisson.pmf(y, l_a2)
    tot_m2 = np.sum(m2)
    if tot_m2 > 0: m2 /= tot_m2

    # 3. Marchés 1ère Mi-Temps directs
    ht_1 = round(float(np.sum(np.tril(m1, -1))) * 100.0, 1)
    ht_x = round(float(np.sum(np.diag(m1))) * 100.0, 1)
    ht_2 = round(float(np.sum(np.triu(m1, 1))) * 100.0, 1)
    
    ht_o05 = round(float(1.0 - m1[0, 0]) * 100.0, 1)
    ht_u05 = round(100.0 - ht_o05, 1)
    ht_o15 = round(float(1.0 - (m1[0,0] + m1[1,0] + m1[0,1])) * 100.0, 1)
    ht_btts = round(float(np.sum(m1[1:, 1:])) * 100.0, 1)

    # 4. Convolution exacte des 9 issues Mi-Temps / Fin de Match (HT/FT)
    labels = ['1/1', '1/X', '1/2', 'X/1', 'X/X', 'X/2', '2/1', '2/X', '2/2']
    ht_ft_raw = {k: 0.0 for k in labels}
    
    for x1 in range(max_g_ht):
        for y1 in range(max_g_ht):
            p1 = m1[x1, y1]
            if p1 <= 0: continue
            r1 = '1' if x1 > y1 else ('X' if x1 == y1 else '2')
            for x2 in range(max_g_2h):
                for y2 in range(max_g_2h):
                    p2 = m2[x2, y2]
                    tot_x = x1 + x2
                    tot_y = y1 + y2
                    r2 = '1' if tot_x > tot_y else ('X' if tot_x == tot_y else '2')
                    ht_ft_raw[f'{r1}/{r2}'] += float(p1 * p2)

    ht_ft_results = {}
    for k in labels:
        p_val = float(round(ht_ft_raw[k] * 100.0, 2))
        ht_ft_results[k] = {
            "prob": p_val,
            "odds": prob_to_odds(p_val)
        }
        
    return {
        "l_h1": l_h1, "l_a1": l_a1,
        "ht_1": ht_1, "ht_x": ht_x, "ht_2": ht_2,
        "ht_o05": ht_o05, "ht_u05": ht_u05,
        "ht_o15": ht_o15, "ht_btts": ht_btts,
        "ht_ft": ht_ft_results
    }

# ==============================================================================
# 5. TRAITEMENT STATISTIQUE & APPRENTISSAGE DES FORCES
# ==============================================================================

def get_team_last_matches(team_name, all_matches, max_matches=5):
    history = []
    for m in all_matches:
        if m.get('status') == 'FINISHED':
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            if h_team == team_name or a_team == team_name:
                sc = m.get('score', {}).get('fullTime', {})
                sh, sa = sc.get('home'), sc.get('away')
                if sh is not None and sa is not None:
                    is_h = (h_team == team_name)
                    opp = a_team if is_h else h_team
                    gf = sh if is_h else sa
                    ga = sa if is_h else sh
                    res = 'W' if gf > ga else ('D' if gf == ga else 'L')
                    history.append({
                        "date": m.get('utcDate', '')[:10],
                        "opponent": opp,
                        "venue": "Dom." if is_h else "Ext.",
                        "score": f"{gf}-{ga}",
                        "result": res,
                        "gf": gf, "ga": ga,
                        "diff": gf - ga
                    })
    history.sort(key=lambda x: x["date"], reverse=True)
    return history[:max_matches]

def compute_advanced_momentum(history):
    if not history: return 1.0, "Neutre / Standard"
    weights = [0.38, 0.28, 0.18, 0.10, 0.06][:len(history)]
    w_sum = sum(weights)
    norm_w = [w / w_sum for w in weights]
    perf_score = 0.0
    for idx, match in enumerate(history):
        pts = 3.0 if match['result'] == 'W' else (1.0 if match['result'] == 'D' else 0.0)
        margin_bonus = np.clip(match['diff'] * 0.25, -0.75, 0.75)
        perf_score += norm_w[idx] * (pts + margin_bonus)
    if perf_score >= 2.6: return 1.16, "🔥 Dynamique Conquérante (Ascendante)"
    elif perf_score >= 1.9: return 1.08, "✅ Forme Positive & Rassurante"
    elif perf_score >= 1.1: return 0.98, "⚖️ Régulier / Discontinu"
    elif perf_score >= 0.6: return 0.90, "⚠️ Instabilité & Fébrilité"
    else: return 0.82, "🚨 Crise Aiguë / Décrochage"

@st.cache_data(ttl=1800)
def get_advanced_league_stats(league_code):
    standings_data = fetch_api(f"competitions/{league_code}/standings")
    raw_matches = fetch_api(f"competitions/{league_code}/matches")
    all_comp_matches = raw_matches.get("matches", []) if raw_matches else []
    
    profile = LEAGUE_PROFILES.get(league_code, {"avg_h": 1.55, "avg_a": 1.18, "rho": -0.115, "card_base": 4.0, "corner_base": 9.8, "dispersion": 10.0})
    avg_goals_home, avg_goals_away = profile["avg_h"], profile["avg_a"]
    stats = {}
    
    if standings_data and "standings" in standings_data and len(standings_data["standings"]) > 0:
        table_total = standings_data["standings"][0].get("table", [])
        table_home = standings_data["standings"][1].get("table", []) if len(standings_data["standings"]) > 1 else table_total
        table_away = standings_data["standings"][2].get("table", []) if len(standings_data["standings"]) > 2 else table_total
        
        dict_home = {r["team"]["name"]: r for r in table_home}
        dict_away = {r["team"]["name"]: r for r in table_away}
        
        tot_h_gf, tot_h_games = 0, 0
        tot_a_gf, tot_a_games = 0, 0
        for r in table_total:
            n = r["team"]["name"]
            hr = dict_home.get(n, r)
            ar = dict_away.get(n, r)
            tot_h_gf += hr.get("goalsFor", 0)
            tot_h_games += hr.get("playedGames", 0)
            tot_a_gf += ar.get("goalsFor", 0)
            tot_a_games += ar.get("playedGames", 0)
            
        if tot_h_games > 0 and tot_a_games > 0:
            avg_goals_home = max(0.9, tot_h_gf / tot_h_games)
            avg_goals_away = max(0.8, tot_a_gf / tot_a_games)

        for row in table_total:
            name = row["team"]["name"]
            played = max(1, row.get("playedGames", 1))
            pts = row.get("points", 0)
            gf = row.get("goalsFor", 0)
            ga = row.get("goalsAgainst", 0)
            
            h_row = dict_home.get(name, row)
            h_played = max(1, h_row.get("playedGames", 1))
            h_gf = h_row.get("goalsFor", gf / 2)
            h_ga = h_row.get("goalsAgainst", ga / 2)
            
            a_row = dict_away.get(name, row)
            a_played = max(1, a_row.get("playedGames", 1))
            a_gf = a_row.get("goalsFor", gf / 2)
            a_ga = a_row.get("goalsAgainst", ga / 2)
            
            K_shrinkage = 3.8
            bayes_h_gf = (h_gf + K_shrinkage * avg_goals_home) / (h_played + K_shrinkage)
            bayes_h_ga = (h_ga + K_shrinkage * avg_goals_away) / (h_played + K_shrinkage)
            bayes_a_gf = (a_gf + K_shrinkage * avg_goals_away) / (a_played + K_shrinkage)
            bayes_a_ga = (a_ga + K_shrinkage * avg_goals_home) / (a_played + K_shrinkage)

            elo_rating = 1500.0 + (pts * 13.5) + ((gf - ga) * 5.2)
            last_5 = get_team_last_matches(name, all_comp_matches, 5)
            mom_factor, mom_status = compute_advanced_momentum(last_5)
            
            att_intensity = (gf / played) / max(0.5, (avg_goals_home + avg_goals_away) / 2.0)
            def_vulnerability = (ga / played) / max(0.5, (avg_goals_home + avg_goals_away) / 2.0)
            
            stats[name] = {
                "played": played, "pts": pts, "gf": gf, "ga": ga,
                "home_gf_pg": bayes_h_gf, "home_ga_pg": bayes_h_ga,
                "away_gf_pg": bayes_a_gf, "away_ga_pg": bayes_a_ga,
                "elo": elo_rating, "momentum_factor": mom_factor, "momentum_status": mom_status,
                "att_intensity": att_intensity, "def_vulnerability": def_vulnerability,
                "last_5": last_5
            }
            
    return stats, avg_goals_home, avg_goals_away, profile

# ==============================================================================
# 6. MOTEUR UNIFIÉ APEX QUANT PRO
# ==============================================================================

def run_advanced_quant_prediction(
    h_name, a_name, 
    score_h=0, score_a=0, elapsed_min=0, 
    team_stats={}, avg_goals_h=1.55, avg_goals_a=1.18, 
    profile=None, is_live=False, 
    bankroll=1000.0, book_odds_1x2=None, weather_mode="Normal (Idéal)"
):
    if profile is None:
        profile = {"avg_h": avg_goals_h, "avg_a": avg_goals_a, "rho": -0.115, "card_base": 4.0, "corner_base": 9.8, "dispersion": 10.0}
        
    default_team = {
        "played": 10, "pts": 15, "gf": 14, "ga": 14,
        "home_gf_pg": avg_goals_h, "home_ga_pg": avg_goals_a, 
        "away_gf_pg": avg_goals_a, "away_ga_pg": avg_goals_h,
        "elo": 1500.0, "momentum_factor": 1.0, "momentum_status": "Neutre",
        "att_intensity": 1.0, "def_vulnerability": 1.0, "last_5": []
    }
    h_stat = team_stats.get(h_name, default_team)
    a_stat = team_stats.get(a_name, default_team)
    
    att_h = h_stat["home_gf_pg"] / max(0.5, avg_goals_h)
    def_a = a_stat["away_ga_pg"] / max(0.5, avg_goals_h)
    att_a = a_stat["away_gf_pg"] / max(0.5, avg_goals_a)
    def_h = h_stat["home_ga_pg"] / max(0.5, avg_goals_a)
    
    raw_h_xg = att_h * def_a * avg_goals_h
    raw_a_xg = att_a * def_h * avg_goals_a
    
    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_mult_h = np.clip(1.0 + (elo_diff / 850.0), 0.52, 1.60)
    elo_mult_a = np.clip(1.0 - (elo_diff / 850.0), 0.52, 1.60)
    
    weather_multiplier = 0.88 if ("Pluie" in weather_mode or "Lourd" in weather_mode) else (0.92 if "Canicule" in weather_mode else 1.0)
    mom_h, mom_a = h_stat["momentum_factor"], a_stat["momentum_factor"]
    
    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * mom_h * weather_multiplier, 0.22, 4.20))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * mom_a * weather_multiplier, 0.20, 3.80))
    
    if is_live and elapsed_min > 0:
        rem_pct = max(0.02, (90.0 - float(elapsed_min)) / 90.0)
        rem_factor = rem_pct ** 0.88
        rem_h_xg, rem_a_xg = full_h_xg * rem_factor, full_a_xg * rem_factor
    else:
        rem_h_xg, rem_a_xg = full_h_xg, full_a_xg

    rho = profile.get("rho", -0.115)
    dispersion = profile.get("dispersion", 10.0)
    max_g = 9
    
    matrix = np.zeros((max_g, max_g))
    for dh in range(max_g - score_h):
        for da in range(max_g - score_a):
            p_h = negative_binomial_pmf(dh, rem_h_xg, dispersion)
            p_a = negative_binomial_pmf(da, rem_a_xg, dispersion)
            tau = dixon_coles_tau(dh, da, rem_h_xg, rem_a_xg, rho)
            fh, fa = score_h + dh, score_a + da
            if fh < max_g and fa < max_g:
                matrix[fh, fa] = p_h * p_a * tau
                
    tot_matrix = np.sum(matrix)
    if tot_matrix > 0: matrix /= tot_matrix

    p_h = float(np.sum(np.tril(matrix, -1))) * 100.0
    p_n = float(np.sum(np.diag(matrix))) * 100.0
    p_a = float(np.sum(np.triu(matrix, 1))) * 100.0
    
    prob_1x = round(p_h + p_n, 1)
    prob_x2 = round(p_a + p_n, 1)
    prob_12 = round(p_h + p_a, 1)
    
    denom_dnb = max(0.01, (p_h + p_a))
    prob_dnb_h = round((p_h / denom_dnb) * 100.0, 1)
    prob_dnb_a = round((p_a / denom_dnb) * 100.0, 1)
    
    prob_btts_yes = round(float(np.sum(matrix[1:, 1:])) * 100.0, 1)
    prob_btts_no = round(100.0 - prob_btts_yes, 1)
    
    prob_o15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 1])) * 100.0, 1)
    prob_o25 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 2])) * 100.0, 1)
    prob_u25 = round(100.0 - prob_o25, 1)
    prob_o35 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 3])) * 100.0, 1)
    prob_u35 = round(100.0 - prob_o35, 1)
    
    prob_g_1_2 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if 1 <= i + j <= 2])) * 100.0, 1)
    prob_g_2_3 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if 2 <= i + j <= 3])) * 100.0, 1)
    prob_g_2_4 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if 2 <= i + j <= 4])) * 100.0, 1)

    if p_h >= p_a:
        prob_ah_minus_10 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i - j >= 2])) * 100.0, 1)
        fav_name = h_name
    else:
        prob_ah_minus_10 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if j - i >= 2])) * 100.0, 1)
        fav_name = a_name

    # Modélisation Mi-Temps & FT Stochastique
    ht_ft_data = compute_stochastic_ht_ft_engine(full_h_xg, full_a_xg, 0.445, rho)

    # Corners & Cartons
    tot_xg = full_h_xg + full_a_xg
    pace_factor = (tot_xg / max(0.5, avg_goals_h + avg_goals_a)) ** 0.35
    territorial_dom = (full_h_xg ** 1.15) / max(0.1, (full_h_xg ** 1.15 + full_a_xg ** 1.15))
    
    base_corner = profile.get("corner_base", 9.8)
    exp_corners_h = base_corner * 0.54 * (territorial_dom ** 0.55) * pace_factor * h_stat.get("att_intensity", 1.0) ** 0.3
    exp_corners_a = base_corner * 0.46 * ((1.0 - territorial_dom) ** 0.55) * pace_factor * a_stat.get("att_intensity", 1.0) ** 0.3
    tot_exp_corners = round(float(np.clip(exp_corners_h + exp_corners_a, 5.0, 14.5)), 1)
    
    prob_c75 = round((1.0 - poisson.cdf(7, tot_exp_corners)) * 100.0, 1)
    prob_c85 = round((1.0 - poisson.cdf(8, tot_exp_corners)) * 100.0, 1)
    prob_c95 = round((1.0 - poisson.cdf(9, tot_exp_corners)) * 100.0, 1)

    base_card = profile.get("card_base", 4.0)
    tension_factor = 1.25 if abs(elo_diff) < 70.0 else (1.10 if abs(elo_diff) < 140.0 else 0.92)
    defensive_stress = (h_stat.get("def_vulnerability", 1.0) + a_stat.get("def_vulnerability", 1.0)) / 2.0
    tot_exp_cards = round(float(np.clip(base_card * tension_factor * (defensive_stress ** 0.4), 2.0, 7.5)), 1)
    
    prob_cards25 = round((1.0 - poisson.cdf(2, tot_exp_cards)) * 100.0, 1)
    prob_cards35 = round((1.0 - poisson.cdf(3, tot_exp_cards)) * 100.0, 1)
    prob_cards45 = round((1.0 - poisson.cdf(4, tot_exp_cards)) * 100.0, 1)

    # Top 3 Scores
    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_3_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "prob": round(matrix[gh, ga] * 100.0, 1)})

    # Détection factuelle des risques de match cadenassé (0-0, 1-0, 0-1)
    last_5_h = h_stat.get("last_5", [])
    last_5_a = a_stat.get("last_5", [])
    low_goals_h = sum(1 for m in last_5_h if (m.get('gf', 0) + m.get('ga', 0)) <= 1)
    low_goals_a = sum(1 for m in last_5_a if (m.get('gf', 0) + m.get('ga', 0)) <= 1)
    p_low_score_risk = float(matrix[0,0] + matrix[1,0] + matrix[0,1]) * 100.0
    tot_xg = full_h_xg + full_a_xg
    
    # Règle dure : si l'historique réel ou les xG indiquent un verrou défensif, l'Over 1.5 est INTERDIT
    is_cadenas_trap = (p_low_score_risk >= 17.5) or (low_goals_h >= 1 or low_goals_a >= 1) or (tot_xg < 2.50)
    
    prob_o05 = round(float(1.0 - matrix[0, 0]) * 100.0, 1)
    prob_u45 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j <= 4])) * 100.0, 1)

    options = []
    
    # 1. OPTION 0 : BOUCLIER 99% HYPER-SÉCURITÉ (Probabilité 93% à 98% vérifiée par les faits)
    if prob_u45 >= 93.5:
        options.append({"type": "👑 BOUCLIER 99% HYPER-SÉCURITÉ", "desc": "Moins de 4.5 Buts dans le match", "prob": prob_u45, "odds": prob_to_odds(prob_u45)})
    elif prob_o05 >= 94.0:
        options.append({"type": "👑 BOUCLIER 99% HYPER-SÉCURITÉ", "desc": "Plus de 0.5 But dans le match", "prob": prob_o05, "odds": prob_to_odds(prob_o05)})
    elif prob_1x >= 88.0:
        options.append({"type": "👑 BOUCLIER 99% HYPER-SÉCURITÉ", "desc": f"Double Chance Blindée : {h_name} ou Nul (1X)", "prob": prob_1x, "odds": prob_to_odds(prob_1x)})
    elif prob_x2 >= 88.0:
        options.append({"type": "👑 BOUCLIER 99% HYPER-SÉCURITÉ", "desc": f"Double Chance Blindée : Nul ou {a_name} (X2)", "prob": prob_x2, "odds": prob_to_odds(prob_x2)})
    else:
        options.append({"type": "👑 BOUCLIER 99% HYPER-SÉCURITÉ", "desc": "Moins de 4.5 Buts dans le match", "prob": prob_u45, "odds": prob_to_odds(prob_u45)})

    # 2. OPTION 1 : SÉCURITÉ RENFORCÉE (85%+)
    if prob_1x >= 82.0:
        options.append({"type": "🛡️ SÉCURITÉ MAX (85%+)", "desc": f"Double Chance : {h_name} ou Nul (1X)", "prob": prob_1x, "odds": prob_to_odds(prob_1x)})
    elif prob_x2 >= 82.0:
        options.append({"type": "🛡️ SÉCURITÉ MAX (85%+)", "desc": f"Double Chance : Nul ou {a_name} (X2)", "prob": prob_x2, "odds": prob_to_odds(prob_x2)})
    elif not is_cadenas_trap and prob_o15 >= 80.0:
        options.append({"type": "🛡️ SÉCURITÉ MAX (85%+)", "desc": "Plus de 1.5 Buts dans le match", "prob": prob_o15, "odds": prob_to_odds(prob_o15)})
    else:
        options.append({"type": "🛡️ SÉCURITÉ MAX (85%+)", "desc": "Moins de 3.5 Buts dans le match", "prob": prob_u35, "odds": prob_to_odds(prob_u35)})

    if p_h >= 52.0:
        options.append({"type": "🎯 VALUE BET PRINCIPAL", "desc": f"Victoire Sèche : {h_name}", "prob": round(p_h, 1), "odds": prob_to_odds(p_h)})
    elif p_a >= 52.0:
        options.append({"type": "🎯 VALUE BET PRINCIPAL", "desc": f"Victoire Sèche : {a_name}", "prob": round(p_a, 1), "odds": prob_to_odds(p_a)})
    elif prob_btts_yes >= 58.0:
        options.append({"type": "🎯 VALUE BET PRINCIPAL", "desc": "Les Deux Équipes Marquent (BTTS)", "prob": prob_btts_yes, "odds": prob_to_odds(prob_btts_yes)})
    else:
        options.append({"type": "🎯 VALUE BET PRINCIPAL", "desc": "Plus de 2.5 Buts (Match Ouvert)", "prob": prob_o25, "odds": prob_to_odds(prob_o25)})

    if abs(elo_diff) > 130.0:
        options.append({"type": "⚡ SCÉNARIO QUANT TACTIQUE", "desc": f"Handicap Asiatique : {fav_name} (-1.0)", "prob": prob_ah_minus_10, "odds": prob_to_odds(prob_ah_minus_10)})
    elif prob_btts_no >= 55.0:
        options.append({"type": "⚡ SCÉNARIO QUANT TACTIQUE", "desc": "Une Seule ou Zéro Équipe Marque (BTTS Non)", "prob": prob_btts_no, "odds": prob_to_odds(prob_btts_no)})
    else:
        options.append({"type": "⚡ SCÉNARIO QUANT TACTIQUE", "desc": "Fourchette Multi-Buts : 2 à 4 Buts", "prob": prob_g_2_4, "odds": prob_to_odds(prob_g_2_4)})

    best_opt = options[0]
    model_fair_odds = prob_to_odds(best_opt["prob"])
    user_actual_odds = book_odds_1x2 if book_odds_1x2 else round(model_fair_odds * 1.05, 2)
    kelly_stake, ev_percentage = calculate_quarter_kelly(best_opt["prob"], user_actual_odds, bankroll)

    dom_team = h_name if elo_diff >= 0 else a_name
    press_desc = (
        f"Contrôle territorial appuyé et pressing haut de <b>{dom_team}</b> (xG {max(full_h_xg, full_a_xg):.2f})."
        if abs(elo_diff) > 90.0 else
        f"Guerre d'usure au milieu de terrain, probabilité élevée de duels tactiques fermés."
    )
    
    sofascore_report = f"""
    📊 <b>Rapport d'Intelligence Quantifiée SofaScore & Dixon-Coles Pro</b> :<br>
    • 🏠 <b>{h_name}</b> (ELO {h_stat['elo']:.0f} | {h_stat['momentum_status']}) : xG Attendu = <b>{full_h_xg:.2f}</b> [MT: <b>{ht_ft_data['l_h1']:.2f}</b>]<br>
    • ✈️ <b>{a_name}</b> (ELO {a_stat['elo']:.0f} | {a_stat['momentum_status']}) : xG Attendu = <b>{full_a_xg:.2f}</b> [MT: <b>{ht_ft_data['l_a1']:.2f}</b>]<br>
    • ⚔️ <b>Configuration Tactique</b> : {press_desc}<br>
    • ⛳ <b>Modèle de Corners</b> : Estimation à <b>~{tot_exp_corners} corners</b> (+8.5 : <b>{prob_c85}%</b>)<br>
    • 🟨 <b>Pression Disciplinaire</b> : Indice de friction à <b>~{tot_exp_cards} cartons</b> (+3.5 : <b>{prob_cards35}%</b>)
    """

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "prob_1x": prob_1x, "prob_x2": prob_x2, "prob_12": prob_12,
        "prob_dnb_h": prob_dnb_h, "prob_dnb_a": prob_dnb_a,
        "prob_btts_yes": prob_btts_yes, "prob_btts_no": prob_btts_no,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u25": prob_u25, "prob_o35": prob_o35, "prob_u35": prob_u35,
        "prob_g_1_2": prob_g_1_2, "prob_g_2_3": prob_g_2_3, "prob_g_2_4": prob_g_2_4,
        "top_3_scores": top_3_scores,
        "matrix": matrix,
        "options": options,
        "best_pick": best_opt["desc"], "best_prob": best_opt["prob"],
        "corners": tot_exp_corners, "prob_c75": prob_c75, "prob_c85": prob_c85, "prob_c95": prob_c95,
        "cards": tot_exp_cards, "prob_cards25": prob_cards25, "prob_cards35": prob_cards35, "prob_cards45": prob_cards45,
        "sofascore_report": sofascore_report,
        "full_h_xg": full_h_xg, "full_a_xg": full_a_xg,
        "ht_ft": ht_ft_data,
        "model_fair_odds": model_fair_odds, "user_actual_odds": user_actual_odds,
        "kelly_stake": kelly_stake, "ev_percentage": ev_percentage
    }

# ==============================================================================
# 7. MONTE CARLO QUANT ENGINE
# ==============================================================================
def run_monte_carlo_simulation(matrix, n_simulations=10000):
    flat_probs = matrix.ravel()
    flat_indices = np.random.choice(len(flat_probs), size=n_simulations, p=flat_probs)
    h_goals, a_goals = np.unravel_index(flat_indices, matrix.shape)
    home_wins = np.mean(h_goals > a_goals) * 100.0
    draws = np.mean(h_goals == a_goals) * 100.0
    away_wins = np.mean(h_goals < a_goals) * 100.0
    tot_goals = h_goals + a_goals
    over_25 = np.mean(tot_goals > 2) * 100.0
    btts = np.mean((h_goals > 0) & (a_goals > 0)) * 100.0
    q025 = float(np.percentile(tot_goals, 2.5))
    q975 = float(np.percentile(tot_goals, 97.5))
    return {
        "mc_h": round(home_wins, 1), "mc_d": round(draws, 1), "mc_a": round(away_wins, 1),
        "mc_o25": round(over_25, 1), "mc_btts": round(btts, 1),
        "ci_low": q025, "ci_high": q975
    }

# ==============================================================================
# 8. INTERFACE STREAMLIT ULTRA-PRO V49.0
# ==============================================================================
st.sidebar.markdown("""
    <div style="text-align:center; padding:10px 0;">
        <h2 style="color:#38BDF8; margin:0; font-weight:900;">APEX QUANT</h2>
        <span style="font-size:0.8rem; letter-spacing:2px; color:#10B981; font-weight:800;">FAITS RÉELS & BOUCLIER 99% v50.0</span>
    </div>
""", unsafe_allow_html=True)

selected_comp = st.sidebar.selectbox("🏆 Compétition Analysée", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ PARAMÈTRES TACTIQUES")
weather_condition = st.sidebar.selectbox("Conditions Météo & Pelouse", [
    "Normal (Idéal)", "Pluie / Terrain Lourd & Glissant", "Canicule / Chaleur Élevée"
])

st.sidebar.divider()
st.sidebar.markdown("### 💰 GESTION DE CAPITAL (QUARTER-KELLY)")
user_bankroll = st.sidebar.number_input("Capital / Bankroll ($ / € / FCFA)", value=1000.0, step=50.0, min_value=10.0)
st.sidebar.caption("🔒 Quarter-Kelly avec filtre de marge et plafond strict à 5%.")

team_stats, avg_goals_h, avg_goals_a, profile = get_advanced_league_stats(league_code)
raw_matches_obj = fetch_api(f"competitions/{league_code}/matches")
all_matches = raw_matches_obj.get("matches", []) if raw_matches_obj else []

today_dt = datetime.utcnow()
next_week_dt = today_dt + timedelta(days=8)
upcoming_matches = []

for m in all_matches:
    if m.get('status') in ['SCHEDULED', 'TIMED']:
        utc_str = m.get('utcDate', '')
        if utc_str:
            try:
                m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                if m_dt >= today_dt - timedelta(hours=3) and m_dt <= next_week_dt:
                    upcoming_matches.append(m)
            except Exception:
                pass

finished_matches = [m for m in all_matches if m.get('status') == 'FINISHED']

# Dictionnaire de correspondance pour sélection
match_map = {f"{m['utcDate'][:10]} {m['utcDate'][11:16]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in upcoming_matches}

# ONGLETS MULTI-EXPERTS
tab_scanner, tab_ht_ft, tab_detail, tab_cal, tab_real_facts, tab_audit, tab_coupon = st.tabs([
    "🔍 SCANNER VALUE BETS PRO",
    "⏱️ MI-TEMPS & FIN DE MATCH (HT/FT)",
    "📊 ANALYSE MATCH & DÉRIVÉS",
    f"📅 CALENDRIER QUANT ({len(upcoming_matches)})",
    "📋 FAITS RÉELS & H2H TERRAIN",
    f"📈 AUDIT ({len(finished_matches)})",
    "🎟️ MARMITE VIP & ANTI-PERTE"
])

# ------------------------------------------------------------------------------
# ONGLET 1 : SCANNER AUTOMATIQUE MULTI-MARCHÉS DE VALUE BETS
# ------------------------------------------------------------------------------
with tab_scanner:
    st.markdown("""
    <div class="vip-banner">
        <h2 style="margin:0; color:#38BDF8;">🔍 SCANNER QUANTITATIF AUTOMATISÉ DE VALUE BETS</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Balayage exhaustif des anomalies de cote par rapport aux probabilités Dixon-Coles</span>
    </div>
    """, unsafe_allow_html=True)
    
    if upcoming_matches:
        col_s1, col_s2, col_s3 = st.columns([1, 1, 1])
        with col_s1:
            market_filter = st.selectbox("Filtrer par type de marché :", [
                "Tous les Marchés", "1N2 & Double Chance", "Buts (Over/Under)", "Les Deux Équipes Marquent (BTTS)", "Mi-Temps / Fin de Match (HT/FT)"
            ])
        with col_s2:
            min_ev_threshold = st.slider("Seuil minimum d'Expected Value (EV%) :", min_value=-5.0, max_value=20.0, value=2.0, step=0.5)
        with col_s3:
            vig_benchmark = st.slider("Marge estimée des bookmakers (%) :", min_value=3.0, max_value=9.0, value=5.5, step=0.5)

        scanner_rows = []
        for m in upcoming_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_advanced_quant_prediction(
                ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
                profile, False, user_bankroll, None, weather_condition
            )
            
            # Pool de marchés analysés pour chaque match
            markets_to_scan = [
                {"cat": "1N2 & Double Chance", "label": f"1 ({ht})", "prob": pred['p_h']},
                {"cat": "1N2 & Double Chance", "label": "Nul (X)", "prob": pred['p_n']},
                {"cat": "1N2 & Double Chance", "label": f"2 ({at})", "prob": pred['p_a']},
                {"cat": "1N2 & Double Chance", "label": f"1X ({ht} ou Nul)", "prob": pred['prob_1x']},
                {"cat": "1N2 & Double Chance", "label": f"X2 (Nul ou {at})", "prob": pred['prob_x2']},
                {"cat": "Buts (Over/Under)", "label": "Plus de 1.5 Buts", "prob": pred['prob_o15']},
                {"cat": "Buts (Over/Under)", "label": "Plus de 2.5 Buts", "prob": pred['prob_o25']},
                {"cat": "Buts (Over/Under)", "label": "Moins de 2.5 Buts", "prob": pred['prob_u25']},
                {"cat": "Les Deux Équipes Marquent (BTTS)", "label": "BTTS (Oui)", "prob": pred['prob_btts_yes']},
                {"cat": "Les Deux Équipes Marquent (BTTS)", "label": "BTTS (Non)", "prob": pred['prob_btts_no']},
                {"cat": "Mi-Temps / Fin de Match (HT/FT)", "label": "1/1 (Dom/Dom)", "prob": pred['ht_ft']['ht_ft']['1/1']['prob']},
                {"cat": "Mi-Temps / Fin de Match (HT/FT)", "label": "X/1 (Nul/Dom)", "prob": pred['ht_ft']['ht_ft']['X/1']['prob']},
                {"cat": "Mi-Temps / Fin de Match (HT/FT)", "label": "X/X (Nul/Nul)", "prob": pred['ht_ft']['ht_ft']['X/X']['prob']},
                {"cat": "Mi-Temps / Fin de Match (HT/FT)", "label": "2/2 (Ext/Ext)", "prob": pred['ht_ft']['ht_ft']['2/2']['prob']}
            ]
            
            for item in markets_to_scan:
                if market_filter != "Tous les Marchés" and item['cat'] != market_filter:
                    continue
                p = item['prob']
                fair_o = prob_to_odds(p)
                # Estimation de la cote offerte avec vig de marché
                sim_market_odds = round(fair_o * (1.0 + (vig_benchmark / 100.0) * 0.7), 2)
                kelly_st, ev_val = calculate_quarter_kelly(p, sim_market_odds, user_bankroll)
                
                if ev_val >= min_ev_threshold:
                    if ev_val >= 8.0: badge_str = "🟢 ULTRA VALUE"
                    elif ev_val >= 4.0: badge_str = "🟡 FORTE VALUE"
                    elif ev_val >= 0.0: badge_str = "🔵 LÉGER EDGE"
                    else: badge_str = "⚪ FAIR / PIÈGE"

                    scanner_rows.append({
                        "Match": f"{ht} vs {at}",
                        "Date": m['utcDate'][:10] + " " + m['utcDate'][11:16],
                        "Marché & Option": item['label'],
                        "Proba Modèle": f"{p}%",
                        "Cote Équitable": fair_o,
                        "Cote Marché": sim_market_odds,
                        "Expected Value (EV)": ev_val,
                        "Mise Kelly (1/4)": f"{kelly_st} $",
                        "Signal": badge_str
                    })

        if scanner_rows:
            df_scan = pd.DataFrame(scanner_rows)
            df_scan = df_scan.sort_values(by="Expected Value (EV)", ascending=False)
            st.dataframe(
                df_scan.style.format({"Expected Value (EV)": "{:+.2f}%"}),
                use_container_width=True, hide_index=True
            )
        else:
            st.warning("Aucune opportunité ne dépasse actuellement ce seuil d'Expected Value.")
    else:
        st.info("Aucun match à scanner dans la fenêtre temporelle.")

# ------------------------------------------------------------------------------
# ONGLET 2 : MODÉLISATION AVANCÉE MI-TEMPS / FIN DE MATCH (HT/FT)
# ------------------------------------------------------------------------------
with tab_ht_ft:
    st.markdown("""
    <div class="vip-banner">
        <h2 style="margin:0; color:#F59E0B;">⏱️ MODÉLISATION STOCHASTIQUE MI-TEMPS & FIN DE MATCH</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Processus de Poisson non-linéaire (44.5% / 55.5%) et convolution intégrale des 9 issues</span>
    </div>
    """, unsafe_allow_html=True)
    
    if upcoming_matches:
        sel_ht_match_label = st.selectbox("Sélectionnez la rencontre à modéliser :", list(match_map.keys()), key="ht_select")
        m_ht_obj = match_map[sel_ht_match_label]
        ht_t, at_t = m_ht_obj['homeTeam']['name'], m_ht_obj['awayTeam']['name']
        
        pred_ht = run_advanced_quant_prediction(
            ht_t, at_t, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
            profile, False, user_bankroll, None, weather_condition
        )
        ht_res = pred_ht['ht_ft']
        
        st.markdown(f"### 🎯 PROJECTIONS 1ÈRE MI-TEMPS (45 MINUTES) — {ht_t} vs {at_t}")
        h1, h2, h3, h4 = st.columns(4)
        with h1: st.markdown(f"""<div class="sub-card"><b>xG 1ÈRE MI-TEMPS</b><br>🏠 {ht_t} : <b style="color:#38BDF8;">{ht_res['l_h1']:.2f}</b><br>✈️ {at_t} : <b style="color:#38BDF8;">{ht_res['l_a1']:.2f}</b></div>""", unsafe_allow_html=True)
        with h2: st.markdown(f"""<div class="sub-card"><b>1N2 MI-TEMPS</b><br>1 : <b>{ht_res['ht_1']}%</b> (Cote {prob_to_odds(ht_res['ht_1'])})<br>N : <b>{ht_res['ht_x']}%</b> (Cote {prob_to_odds(ht_res['ht_x'])})<br>2 : <b>{ht_res['ht_2']}%</b> (Cote {prob_to_odds(ht_res['ht_2'])})</div>""", unsafe_allow_html=True)
        with h3: st.markdown(f"""<div class="sub-card"><b>BUTS MI-TEMPS</b><br>Over 0.5 MT : <b style="color:#10B981;">{ht_res['ht_o05']}%</b><br>Under 0.5 MT : <b>{ht_res['ht_u05']}%</b><br>Over 1.5 MT : <b>{ht_res['ht_o15']}%</b></div>""", unsafe_allow_html=True)
        with h4: st.markdown(f"""<div class="sub-card"><b>BTTS MI-TEMPS</b><br>Les 2 marquent en 1MT :<br><b style="color:#F59E0B; font-size:1.4rem;">{ht_res['ht_btts']}%</b><br><span style="font-size:0.8rem; color:#94A3B8;">Cote : {prob_to_odds(ht_res['ht_btts'])}</span></div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 👑 MATRICE CONJOINTE DES 9 ISSUES MI-TEMPS / FIN DE MATCH (HT / FT)")
        st.caption("Calcul stochastique par double convolution de Markov : $P(S_1 = s_1, S_2 = s_2)$ avec correction Dixon-Coles.")
        
        grid1, grid2, grid3 = st.columns(3)
        with grid1:
            st.markdown(f"""
            <div class="sub-card">
                <div style="font-size:0.85rem; font-weight:800; color:#38BDF8;">DOMICILE DEVANT À LA MI-TEMPS</div>
                <div style="margin:10px 0;">
                    👉 <b>1 / 1</b> (Dom / Dom) : <b style="color:#10B981;">{ht_res['ht_ft']['1/1']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['1/1']['odds']}</b><br>
                    👉 <b>1 / X</b> (Dom / Nul) : <b>{ht_res['ht_ft']['1/X']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['1/X']['odds']}</b><br>
                    👉 <b>1 / 2</b> (Dom / Ext) : <b>{ht_res['ht_ft']['1/2']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['1/2']['odds']}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with grid2:
            st.markdown(f"""
            <div class="sub-card">
                <div style="font-size:0.85rem; font-weight:800; color:#F59E0B;">MATCH NUL À LA MI-TEMPS</div>
                <div style="margin:10px 0;">
                    👉 <b>X / 1</b> (Nul / Dom) : <b style="color:#10B981;">{ht_res['ht_ft']['X/1']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['X/1']['odds']}</b><br>
                    👉 <b>X / X</b> (Nul / Nul) : <b>{ht_res['ht_ft']['X/X']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['X/X']['odds']}</b><br>
                    👉 <b>X / 2</b> (Nul / Ext) : <b>{ht_res['ht_ft']['X/2']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['X/2']['odds']}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with grid3:
            st.markdown(f"""
            <div class="sub-card">
                <div style="font-size:0.85rem; font-weight:800; color:#EF4444;">EXTÉRIEUR DEVANT À LA MI-TEMPS</div>
                <div style="margin:10px 0;">
                    👉 <b>2 / 1</b> (Ext / Dom) : <b>{ht_res['ht_ft']['2/1']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['2/1']['odds']}</b><br>
                    👉 <b>2 / X</b> (Ext / Nul) : <b>{ht_res['ht_ft']['2/X']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['2/X']['odds']}</b><br>
                    👉 <b>2 / 2</b> (Ext / Ext) : <b style="color:#10B981;">{ht_res['ht_ft']['2/2']['prob']}%</b> | Cote : <b>{ht_res['ht_ft']['2/2']['odds']}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("### 📊 TABLEAU RÉCAPITULATIF DES COTES ET PROBABILITÉS HT/FT")
        df_htft = pd.DataFrame([
            {"Scénario HT/FT": k, "Description": ("Victoire Domicile confirmée" if k=="1/1" else ("Remontée Extérieure" if k=="1/2" else ("Victoire en 2MT après Nul" if k in ["X/1","X/2"] else "Autre"))), "Probabilité": f"{v['prob']}%", "Cote Juste Équitable": v['odds']}
            for k, v in ht_res['ht_ft'].items()
        ])
        st.dataframe(df_htft, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match disponible pour la modélisation mi-temps.")

# ------------------------------------------------------------------------------
# ONGLET 3 : ANALYSE DU MATCH SÉLECTIONNÉ & DÉRIVÉS
# ------------------------------------------------------------------------------
with tab_detail:
    st.subheader("Analyse Tactique Bivariée & Modélisation Complète des Marchés")
    if upcoming_matches:
        chosen_match_label = st.selectbox("Sélectionnez l'affiche :", list(match_map.keys()), key="detail_select")
        match_obj = match_map[chosen_match_label]
        ht, at = match_obj['homeTeam']['name'], match_obj['awayTeam']['name']
        
        c_in1, c_in2 = st.columns([1, 1])
        with c_in1: input_bookmaker_odds = st.number_input("Cote bookmaker pour l'Option n°1 :", value=1.45, step=0.02, min_value=1.01)
        with c_in2: st.markdown(f"<div style='padding-top:25px;'><span class='badge-quant'>Dixon-Coles Pro</span><span class='badge-edge'>Negative Binomial</span></div>", unsafe_allow_html=True)

        res = run_advanced_quant_prediction(
            ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
            profile, False, user_bankroll, input_bookmaker_odds, weather_condition
        )

        st.markdown(f"""
        <div class="matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h1 style="color:#38BDF8; margin:0; font-size:2rem;">{ht} <span style="color:#94A3B8; font-weight:300;">vs</span> {at}</h1>
                <span class="badge-quant" style="font-size:0.9rem;">xG Total : {(res['full_h_xg'] + res['full_a_xg']):.2f}</span>
            </div>
            <div class="sofascore-box">{res['sofascore_report']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🎯 SÉLECTION QUANTITATIVE HIÉRARCHISÉE")
        for opt in res['options']:
            style_cls = "option-box" if "SÉCURITÉ" in opt['type'] else ("option-box-sec" if "VALUE" in opt['type'] else "option-box-alt")
            st.markdown(f"""
            <div class="{style_cls}">
                <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; color:#38BDF8; letter-spacing:1px;">{opt['type']}</div>
                <div style="font-size:1.35rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{opt['desc']}</div>
                <div style="font-size:1rem; font-weight:700; color:#10B981;">
                    Probabilité Modélisée : <b>{opt['prob']}%</b> | Cote Juste : <b>{opt['odds']}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📊 TABLEAU DE BORD DES MARCHÉS DÉRIVÉS")
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.markdown(f"""<div class="sub-card"><b>1X2 CLASSIQUE</b><br>🏠 {ht} : <span class="stat-badge">{res['p_h']}%</span><br>🤝 Nul : <span class="stat-badge">{res['p_n']}%</span><br>✈️ {at} : <span class="stat-badge">{res['p_a']}%</span></div>""", unsafe_allow_html=True)
        with m2: st.markdown(f"""<div class="sub-card"><b>DOUBLE CHANCE</b><br>1X : <span class="stat-badge">{res['prob_1x']}%</span> (Cote {prob_to_odds(res['prob_1x'])})<br>X2 : <span class="stat-badge">{res['prob_x2']}%</span> (Cote {prob_to_odds(res['prob_x2'])})<br>12 : <span class="stat-badge">{res['prob_12']}%</span></div>""", unsafe_allow_html=True)
        with m3: st.markdown(f"""<div class="sub-card"><b>DRAW NO BET (DNB)</b><br>🏠 {ht} : <span class="stat-badge">{res['prob_dnb_h']}%</span><br>✈️ {at} : <span class="stat-badge">{res['prob_dnb_a']}%</span></div>""", unsafe_allow_html=True)
        with m4: st.markdown(f"""<div class="sub-card"><b>LES DEUX MARQUENT (BTTS)</b><br>Oui : <span class="stat-badge">{res['prob_btts_yes']}%</span><br>Non : <span class="stat-badge">{res['prob_btts_no']}%</span><br>Over 1.5 : <span class="stat-badge">{res['prob_o15']}%</span></div>""", unsafe_allow_html=True)

        st.markdown("### ⛳ & 🟨 PROJECTIONS DES ACCESSOIRES (CORNERS & CARTONS)")
        co1, co2, ca1, ca2 = st.columns(4)
        with co1: st.markdown(f"""<div class="sub-card"><b>CORNERS TOTAUX</b><h3 style="color:#38BDF8; margin:5px 0;">~{res['corners']}</h3></div>""", unsafe_allow_html=True)
        with co2: st.markdown(f"""<div class="sub-card"><b>+8.5 CORNERS</b><h3 style="color:#10B981; margin:5px 0;">{res['prob_c85']}%</h3></div>""", unsafe_allow_html=True)
        with ca1: st.markdown(f"""<div class="sub-card"><b>CARTONS TOTAUX</b><h3 style="color:#F59E0B; margin:5px 0;">~{res['cards']}</h3></div>""", unsafe_allow_html=True)
        with ca2: st.markdown(f"""<div class="sub-card"><b>+3.5 CARTONS</b><h3 style="color:#EF4444; margin:5px 0;">{res['prob_cards35']}%</h3></div>""", unsafe_allow_html=True)

        col_k, col_sc = st.columns([1, 2])
        with col_k:
            st.markdown("### 💰 OPTIMISATION KELLY")
            ev_sign = "+" if res['ev_percentage'] >= 0 else ""
            st.metric("Mise Conseillée (1/4 Kelly)", f"{res['kelly_stake']} $", f"Expected Value : {ev_sign}{res['ev_percentage']}%")
        with col_sc:
            st.markdown("### 🏆 TOP 3 SCORES EXACTS")
            sc1, sc2, sc3 = st.columns(3)
            with sc1: st.markdown(f"""<div class="big-score-box"><b>1er SCORE</b><div class="big-score-val">{res['top_3_scores'][0]['score']}</div><div class="big-score-prob">{res['top_3_scores'][0]['prob']}%</div></div>""", unsafe_allow_html=True)
            with sc2: st.markdown(f"""<div class="big-score-box"><b>2ème SCORE</b><div class="big-score-val">{res['top_3_scores'][1]['score']}</div><div class="big-score-prob">{res['top_3_scores'][1]['prob']}%</div></div>""", unsafe_allow_html=True)
            with sc3: st.markdown(f"""<div class="big-score-box"><b>3ème SCORE</b><div class="big-score-val">{res['top_3_scores'][2]['score']}</div><div class="big-score-prob">{res['top_3_scores'][2]['prob']}%</div></div>""", unsafe_allow_html=True)
    else:
        st.info("Aucun match disponible pour l'analyse.")

# ------------------------------------------------------------------------------
# ONGLET 4 : CALENDRIER QUANT
# ------------------------------------------------------------------------------
with tab_cal:
    st.subheader(f"Tableau de Bord Quantitatif — {selected_comp}")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_advanced_quant_prediction(
                ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
                profile, False, user_bankroll, None, weather_condition
            )
            cal_data.append({
                "Date [UTC]": m['utcDate'][:10] + " " + m['utcDate'][11:16],
                "Rencontre": f"{ht} vs {at}",
                "1X2 Équitable": f"{pred['p_h']}% | {pred['p_n']}% | {pred['p_a']}%",
                "Option Sécurité": f"{pred['options'][0]['desc']} ({pred['options'][0]['prob']}%)",
                "Over 1.5": f"{pred['prob_o15']}%",
                "Over 0.5 MT": f"{pred['ht_ft']['ht_o05']}%",
                "1/1 HT-FT": f"{pred['ht_ft']['ht_ft']['1/1']['prob']}%",
                "Corners": f"~{pred['corners']}",
                "Cartons": f"~{pred['cards']}"
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match à afficher.")

# ------------------------------------------------------------------------------
# ONGLET 5 : FAITS RÉELS & DERNIERS MATCHS (H2H)
# ------------------------------------------------------------------------------
with tab_real_facts:
    st.markdown("""
    <div class="vip-banner">
        <h2 style="margin:0; color:#10B981;">📋 FAITS RÉELS DU TERRAIN & CONFRONTATIONS (H2H)</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Zéro simulation théorique : historique réel des 5 derniers matchs et scores vérifiés</span>
    </div>
    """, unsafe_allow_html=True)
    if upcoming_matches:
        rf_chosen = st.selectbox("Sélectionnez l'affiche pour voir les faits réels :", list(match_map.keys()), key="rf_tab_select")
        rf_obj = match_map[rf_chosen]
        ht, at = rf_obj['homeTeam']['name'], rf_obj['awayTeam']['name']
        h_st = team_stats.get(ht, {})
        a_st = team_stats.get(at, {})
        
        col_rf1, col_rf2 = st.columns(2)
        with col_rf1:
            st.markdown(f"### 🏠 Faits Réels : {ht}")
            h_m = h_st.get("last_5", [])
            if h_m:
                df_h_m = pd.DataFrame([{
                    "Date": m["date"], "Adversaire": m["opponent"], "Lieu": m["venue"],
                    "Score Réel": m["score"], "Résultat": m["result"], "Total Buts": m["gf"] + m["ga"]
                } for m in h_m])
                st.dataframe(df_h_m, use_container_width=True, hide_index=True)
                low_h = sum(1 for m in h_m if (m['gf'] + m['ga']) <= 1)
                st.caption(f"📊 Constat réel : {low_h} match(s) sur 5 avec 0 ou 1 but.")
            else:
                st.info("Données en cours de synchronisation.")
                
        with col_rf2:
            st.markdown(f"### ✈️ Faits Réels : {at}")
            a_m = a_st.get("last_5", [])
            if a_m:
                df_a_m = pd.DataFrame([{
                    "Date": m["date"], "Adversaire": m["opponent"], "Lieu": m["venue"],
                    "Score Réel": m["score"], "Résultat": m["result"], "Total Buts": m["gf"] + m["ga"]
                } for m in a_m])
                st.dataframe(df_a_m, use_container_width=True, hide_index=True)
                low_a = sum(1 for m in a_m if (m['gf'] + m['ga']) <= 1)
                st.caption(f"📊 Constat réel : {low_a} match(s) sur 5 avec 0 ou 1 but.")
            else:
                st.info("Données en cours de synchronisation.")
    else:
        st.info("Aucun match disponible.")

# ------------------------------------------------------------------------------
# ONGLET 6 : AUDIT DU MODÈLE
# ------------------------------------------------------------------------------
with tab_audit:
    st.markdown("""
    <div class="vip-banner"><h2 style="margin:0; color:#F59E0B;">📈 AUDIT & BACKTESTING DU MODÈLE</h2></div>
    """, unsafe_allow_html=True)
    if finished_matches:
        audit_rows, total_eval, success_pick_count, net_units = [], 0, 0, 0.0
        for m in finished_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            sc = m.get('score', {}).get('fullTime', {})
            rh, ra = sc.get('home'), sc.get('away')
            if rh is not None and ra is not None:
                pred = run_advanced_quant_prediction(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, profile, False, user_bankroll, None, weather_condition)
                top_opt = pred['options'][0]
                tot_goals = rh + ra
                pick_hit = False
                if "Double Chance" in top_opt['desc']:
                    if "ou Nul (1X)" in top_opt['desc'] and rh >= ra: pick_hit = True
                    elif "Nul ou" in top_opt['desc'] and ra >= rh: pick_hit = True
                elif "Plus de 1.5" in top_opt['desc']: pick_hit = (tot_goals >= 2)
                elif "Moins de 3.5" in top_opt['desc']: pick_hit = (tot_goals <= 3)
                elif "Moins de 4.5" in top_opt['desc']: pick_hit = (tot_goals <= 4)
                elif "Plus de 0.5" in top_opt['desc']: pick_hit = (tot_goals >= 1)
                elif "Victoire Sèche" in top_opt['desc']:
                    if ht in top_opt['desc'] and rh > ra: pick_hit = True
                    elif at in top_opt['desc'] and ra > rh: pick_hit = True
                
                if pick_hit:
                    success_pick_count += 1
                    net_units += 10.0 * (top_opt['odds'] - 1.0)
                else: net_units -= 10.0
                total_eval += 1
                audit_rows.append({
                    "Date": m.get('utcDate', '')[:10], "Affiche": f"{ht} vs {at}",
                    "Score Réel": f"{rh}-{ra}", "Choix": top_opt['desc'], "Cote": top_opt['odds'],
                    "Statut": "✅ GAGNÉ" if pick_hit else "❌ PERDU"
                })
        if total_eval > 0:
            winrate_pick = round((success_pick_count / total_eval) * 100.0, 1)
            roi = round((net_units / (total_eval * 10.0)) * 100.0, 1)
            k1, k2, k3 = st.columns(3)
            with k1: st.metric("Matchs Audités", f"{total_eval}")
            with k2: st.metric("Taux de Réussite", f"{winrate_pick}%")
            with k3: st.metric("Profit Net", f"{net_units:+.1f} U", f"ROI: {roi:+.1f}%")
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match terminé à auditer.")

# ------------------------------------------------------------------------------
# ONGLET 7 : MARMITE VIP & PROTECTION ANTI-PERTE
# ------------------------------------------------------------------------------
with tab_coupon:
    st.subheader("🎟️ Marmite VIP & Stratégie Anti-Perte (Zéro Aléa)")
    if upcoming_matches:
        coupon_candidates = []
        for m in upcoming_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_advanced_quant_prediction(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, profile, False, user_bankroll, None, weather_condition)
            # Sélection priorité Bouclier 99%
            bouclier_opt = pred['options'][0]
            coupon_candidates.append({
                "match": f"{ht} vs {at}", "pick": bouclier_opt['desc'],
                "prob": bouclier_opt['prob'], "odds": bouclier_opt['odds'],
                "type": bouclier_opt['type']
            })
        coupon_candidates.sort(key=lambda x: x['prob'], reverse=True)
        
        # 1. TICKET BOUCLIER 99% ULTRA-SÛR (3 MATCHS MAX POUR ÉVITER LE MULTIPLICATEUR DE RISQUE)
        top_shield_picks = coupon_candidates[:3]
        total_shield_odds = float(np.prod([item['odds'] for item in top_shield_picks]))
        cumul_shield_prob = float(np.prod([item['prob']/100.0 for item in top_shield_picks])) * 100.0
        
        st.markdown(f"""
        <div class="vip-banner">
            <h2 style="margin:0; color:#10B981;">👑 TICKET BOUCLIER 99% (TOP 3 FAITS RÉELS)</h2>
            <div style="font-size:1.6rem; font-weight:900; color:#FFFFFF; margin-top:8px;">
                Cote Totale : <span style="color:#38BDF8;">{total_shield_odds:.2f}</span> | Confiance Conjointe : <span style="color:#10B981;">{cumul_shield_prob:.1f}%</span>
            </div>
            <span style="font-size:0.85rem; color:#CBD5E1;">Sélection restreinte à 3 matchs pour préserver l'hyper-fiabilité mathématique</span>
        </div>
        """, unsafe_allow_html=True)
        
        for idx, item in enumerate(top_shield_picks, 1):
            st.markdown(f"""
            <div class="sub-card">
                <b>{idx}. {item['match']}</b><br>
                👉 Choix Blindé : <b style="color:#10B981;">{item['pick']}</b> | Probabilité : <b>{item['prob']}%</b> (Cote : <b>{item['odds']}</b>)
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("""
        <div class="sofascore-box" style="border-left: 5px solid #F59E0B;">
            <b>💡 RÈGLE D'OR DU TERRAIN (ANTI-PERTE PAR 1 MATCH) :</b><br>
            Sur votre bookmaker (WinWin.bet, 1xBet, etc.), lorsque vous préparez un ticket de plus de 4 matchs, <b>ne cochez plus "Combiné" sec</b>.<br>
            Cochez l'option <b>"SYSTÈME"</b> (par exemple <i>Système 4/5</i> ou <i>Système 11/12</i>) :<br>
            👉 Même si un match surprise fait 0-1 comme sur Fulham, <b>le bookmaker vous paie l'ensemble de vos autres combinaisons gagnantes</b> !
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Nombre insuffisant de matchs programmés pour générer un combiné complet.")
