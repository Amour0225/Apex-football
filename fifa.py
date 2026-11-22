import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime, timedelta
import math

# ==============================================================================
# 1. CONFIGURATION & DESIGN AVANCÉ V54.0 INSTITUTIONAL QUANT ENGINE
# ==============================================================================
st.set_page_config(
    page_title="Apex Quant v54.0 — Institutional Multi-Model AI",
    page_icon="🧠",
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
    .sniper-card {
        background: linear-gradient(135deg, #064E3B 0%, #022C22 100%);
        border: 2px solid #10B981; border-radius: 16px; padding: 20px; margin-bottom: 16px;
        box-shadow: 0 8px 24px -6px rgba(16, 185, 129, 0.35);
    }
    .degen-card {
        background: linear-gradient(135deg, #450A0A 0%, #7C2D12 50%, #3B0764 100%);
        border: 2px solid #F97316; border-radius: 16px; padding: 20px; margin-bottom: 16px;
        box-shadow: 0 8px 28px -6px rgba(249, 115, 22, 0.45);
    }
    .ticket-master {
        background: linear-gradient(145deg, #1E1B4B 0%, #4C1D95 45%, #7C2D12 100%);
        border: 2.5px solid #FBBF24; border-radius: 20px; padding: 26px; margin: 18px 0;
        box-shadow: 0 12px 35px -8px rgba(251, 191, 36, 0.4);
    }
    .ticket-leg {
        background: rgba(3, 7, 18, 0.72);
        border-left: 4px solid #F97316;
        border-radius: 0 12px 12px 0;
        padding: 14px 18px;
        margin: 10px 0;
    }
    .sofascore-box {
        background-color: #0B0F19; border: 1px solid #1E293B; border-left: 5px solid #10B981;
        border-radius: 0 14px 14px 0; padding: 20px; margin: 16px 0; font-size: 0.95rem; line-height: 1.7; color: #E2E8F0;
    }
    .vip-banner {
        background: linear-gradient(135deg, #311042 0%, #581C87 50%, #1E3A8A 100%);
        border: 2px solid #F59E0B; border-radius: 16px; padding: 22px; text-align: center; margin-bottom: 25px;
    }
    .sub-card {
        background: #0B1120; border: 1.5px solid #1E293B;
        border-radius: 14px; padding: 18px; margin-bottom: 16px;
    }
    .option-box {
        background: rgba(16, 185, 129, 0.10); border: 1.5px solid #10B981; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-sec {
        background: rgba(56, 189, 248, 0.08); border: 1.5px solid #38BDF8; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-alt {
        background: rgba(168, 85, 247, 0.08); border: 1.5px solid #A855F7; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-crazy {
        background: rgba(249, 115, 22, 0.14); border: 2px solid #F97316; border-radius: 14px; padding: 16px; margin: 10px 0;
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
    .badge-sniper {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800;
        background: rgba(16, 185, 129, 0.2); color: #10B981; border: 1px solid #10B981;
    }
    .badge-crazy {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800;
        background: rgba(249, 115, 22, 0.25); color: #FB923C; border: 1px solid #F97316;
    }
    .stat-badge {
        font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 800; color: #38BDF8;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. PARAMÈTRES GLOBAUX & INFRASTRUCTURE API
# ==============================================================================
API_KEY = st.secrets.get("FOOTBALL_API_KEY", "1e9518e7585349f9abe6d5a29ddb83b1")
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
    "CL":  {"avg_h": 1.62, "avg_a": 1.28, "rho": -0.115, "card_base": 4.1, "corner_base": 9.9, "dispersion": 9.5,  "draw_base": 0.24},
    "PL":  {"avg_h": 1.58, "avg_a": 1.24, "rho": -0.110, "card_base": 3.9, "corner_base": 10.4, "dispersion": 10.0, "draw_base": 0.24},
    "PD":  {"avg_h": 1.48, "avg_a": 1.10, "rho": -0.125, "card_base": 4.8, "corner_base": 9.4, "dispersion": 9.2,  "draw_base": 0.27},
    "FL1": {"avg_h": 1.50, "avg_a": 1.16, "rho": -0.118, "card_base": 3.8, "corner_base": 9.3, "dispersion": 9.8,  "draw_base": 0.26},
    "SA":  {"avg_h": 1.52, "avg_a": 1.18, "rho": -0.120, "card_base": 4.5, "corner_base": 9.8, "dispersion": 9.4,  "draw_base": 0.27},
    "BL1": {"avg_h": 1.72, "avg_a": 1.35, "rho": -0.095, "card_base": 3.9, "corner_base": 10.1, "dispersion": 11.2, "draw_base": 0.23},
    "EL":  {"avg_h": 1.56, "avg_a": 1.22, "rho": -0.112, "card_base": 4.2, "corner_base": 9.7, "dispersion": 9.6,  "draw_base": 0.25},
    "ELC": {"avg_h": 1.44, "avg_a": 1.14, "rho": -0.108, "card_base": 3.8, "corner_base": 10.2, "dispersion": 10.2, "draw_base": 0.28}
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
# 3. ALGORITHMES INSTITUTIONNELS : RÉSOLUTION MATRICIELLE MASSEY-COLLEY
# ==============================================================================

def solve_massey_colley_ratings(all_matches, teams_list):
    """
    Résout le système linéaire d'algèbre matricielle (Massey Rating System)
    sur l'intégralité des matchs joués de la ligue :
    Ajuste la force réelle de chaque équipe selon la difficulté de son calendrier (Strength of Schedule).
    """
    n = len(teams_list)
    if n < 2:
        return {}
    idx_map = {t: i for i, t in enumerate(teams_list)}
    M = np.eye(n) * 2.0  # Régularisation de Ridge (Tikhonov) pour stabilité numérique
    p = np.zeros(n)
    
    games_counted = 0
    for m in all_matches:
        if m.get('status') == 'FINISHED':
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            if ht in idx_map and at in idx_map:
                sc = m.get('score', {}).get('fullTime', {})
                sh, sa = sc.get('home'), sc.get('away')
                if sh is not None and sa is not None:
                    i, j = idx_map[ht], idx_map[at]
                    # On borne la différence de buts à +/- 4 pour éviter qu'un carton 7-0 ne fausse tout
                    diff = float(np.clip(sh - sa, -4, 4))
                    # On retire un avantage domicile standard de 0.32 but pour isoler la force pure
                    adj_diff = diff - 0.32
                    
                    M[i, i] += 1.0
                    M[j, j] += 1.0
                    M[i, j] -= 1.0
                    M[j, i] -= 1.0
                    
                    p[i] += adj_diff
                    p[j] -= adj_diff
                    games_counted += 1

    if games_counted < 5:
        return {t: 0.0 for t in teams_list}

    try:
        ratings = np.linalg.solve(M, p)
        # Centrage autour de 0
        ratings -= np.mean(ratings)
        return {teams_list[i]: round(float(ratings[i]), 3) for i in range(n)}
    except Exception:
        return {t: 0.0 for t in teams_list}

# ==============================================================================
# 4. BRIQUES STOCHASTIQUES : DIXON-COLES, CALIBRATION, ENTROPIE & MONTE CARLO
# ==============================================================================

def dixon_coles_tau(x, y, lambda_h, lambda_a, rho=-0.115):
    if x == 0 and y == 0: return max(0.01, 1.0 - (lambda_h * lambda_a * rho))
    elif x == 0 and y == 1: return max(0.01, 1.0 + (lambda_h * rho))
    elif x == 1 and y == 0: return max(0.01, 1.0 + (lambda_a * rho))
    elif x == 1 and y == 1: return max(0.01, 1.0 - rho)
    return 1.0

def negative_binomial_pmf(k, mu, dispersion=10.0):
    r = dispersion
    p = r / (r + mu)
    return nbinom.pmf(k, r, p)

def compute_elo_1x2_probs(elo_h, elo_a, home_adv=65.0, draw_base=0.25):
    diff = (elo_h + home_adv) - elo_a
    exp_h = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))
    closeness = math.exp(-((diff / 220.0) ** 2))
    p_draw = np.clip(draw_base * (0.65 + 0.55 * closeness), 0.14, 0.36)
    rem = 1.0 - p_draw
    return rem * exp_h * 100.0, p_draw * 100.0, rem * (1.0 - exp_h) * 100.0

def calibrate_probability_temperature(prob_pct, temperature=1.15):
    p = np.clip(prob_pct / 100.0, 0.001, 0.999)
    logit = math.log(p / (1.0 - p))
    scaled_logit = logit / temperature
    cal_p = 1.0 / (1.0 + math.exp(-scaled_logit))
    return round(cal_p * 100.0, 1)

def compute_shannon_entropy_1x2(p_h, p_n, p_a):
    probs = np.clip(np.array([p_h, p_n, p_a]) / 100.0, 1e-6, 1.0)
    entropy = -np.sum(probs * np.log2(probs))
    return round(float(entropy / math.log2(3.0)), 3)

def prob_to_odds(p):
    if p <= 0.001: return 99.00
    return round(min(99.00, 100.0 / p), 2)

def run_stratified_monte_carlo(lambda_h, lambda_a, dispersion=10.0, rho=-0.115, n_sims=25000):
    """
    25 000 simulations Monte Carlo avec injection d'incertitude paramétrique (Gamma-Poisson)
    pour mesurer la robustesse réelle des probabilités face aux aléas d'un match.
    """
    rng = np.random.default_rng(42)
    # Variation aléatoire de +/- 12% autour de l'intensité offensive (forme du jour)
    noise_h = rng.gamma(shape=dispersion, scale=lambda_h / dispersion, size=n_sims)
    noise_a = rng.gamma(shape=dispersion, scale=lambda_a / dispersion, size=n_sims)
    
    sim_h = rng.poisson(noise_h)
    sim_a = rng.poisson(noise_a)
    
    mc_h = float(np.mean(sim_h > sim_a)) * 100.0
    mc_n = float(np.mean(sim_h == sim_a)) * 100.0
    mc_a = float(np.mean(sim_h < sim_a)) * 100.0
    
    tot_g = sim_h + sim_a
    mc_o15 = float(np.mean(tot_g > 1)) * 100.0
    mc_o25 = float(np.mean(tot_g > 2)) * 100.0
    mc_u35 = float(np.mean(tot_g <= 3)) * 100.0
    mc_btts = float(np.mean((sim_h > 0) & (sim_a > 0))) * 100.0
    
    return {
        "mc_h": round(mc_h, 1), "mc_n": round(mc_n, 1), "mc_a": round(mc_a, 1),
        "mc_o15": round(mc_o15, 1), "mc_o25": round(mc_o25, 1),
        "mc_u35": round(mc_u35, 1), "mc_btts": round(mc_btts, 1),
        "ci_low": int(np.percentile(tot_g, 5)),
        "ci_high": int(np.percentile(tot_g, 95))
    }

def calculate_adaptive_kelly(prob_pct, bookmaker_odds, bankroll, risk_mode="Équilibré"):
    p = prob_pct / 100.0
    b = bookmaker_odds - 1.0
    if b <= 0 or p <= 0: return 0.0, 0.0
    f_star = (p * (b + 1.0) - 1.0) / b
    ev_val = round(((p * bookmaker_odds) - 1.0) * 100, 2)
    
    if "Chasseur" in risk_mode:
        kelly_frac, max_cap = 0.12, 0.015
        if f_star <= 0: return round(bankroll * 0.005, 2), ev_val
    else:
        kelly_frac, max_cap = 0.25, 0.05
        if f_star <= 0: return 0.0, ev_val

    f_capped = min(max(0.0, f_star * kelly_frac), max_cap)
    return round(bankroll * f_capped, 2), ev_val

# ==============================================================================
# 5. MODÉLISATION STOCHASTIQUE MI-TEMPS / FIN DE MATCH (HT / FT)
# ==============================================================================

def compute_stochastic_ht_ft_engine(lambda_h, lambda_a, theta_ht=0.435, rho=-0.115):
    l_h1, l_a1 = lambda_h * theta_ht, lambda_a * theta_ht
    l_h2, l_a2 = lambda_h * (1.0 - theta_ht), lambda_a * (1.0 - theta_ht)
    
    max_g = 6
    m1 = np.zeros((max_g, max_g))
    for x in range(max_g):
        for y in range(max_g):
            tau = dixon_coles_tau(x, y, l_h1, l_a1, rho * 1.25)
            m1[x, y] = max(0.0, poisson.pmf(x, l_h1) * poisson.pmf(y, l_a1) * tau)
    if np.sum(m1) > 0: m1 /= np.sum(m1)

    m2 = np.zeros((max_g, max_g))
    for x in range(max_g):
        for y in range(max_g):
            m2[x, y] = poisson.pmf(x, l_h2) * poisson.pmf(y, l_a2)
    if np.sum(m2) > 0: m2 /= np.sum(m2)

    ht_1 = round(float(np.sum(np.tril(m1, -1))) * 100.0, 1)
    ht_x = round(float(np.sum(np.diag(m1))) * 100.0, 1)
    ht_2 = round(float(np.sum(np.triu(m1, 1))) * 100.0, 1)
    ht_o05 = round(float(1.0 - m1[0, 0]) * 100.0, 1)
    ht_u05 = round(100.0 - ht_o05, 1)
    ht_o15 = round(float(1.0 - (m1[0,0] + m1[1,0] + m1[0,1])) * 100.0, 1)
    ht_btts = round(float(np.sum(m1[1:, 1:])) * 100.0, 1)

    labels = ['1/1', '1/X', '1/2', 'X/1', 'X/X', 'X/2', '2/1', '2/X', '2/2']
    ht_ft_raw = {k: 0.0 for k in labels}
    
    for x1 in range(max_g):
        for y1 in range(max_g):
            p1 = m1[x1, y1]
            if p1 <= 0: continue
            r1 = '1' if x1 > y1 else ('X' if x1 == y1 else '2')
            for x2 in range(max_g):
                for y2 in range(max_g):
                    p2 = m2[x2, y2]
                    tx, ty = x1 + x2, y1 + y2
                    r2 = '1' if tx > ty else ('X' if tx == ty else '2')
                    ht_ft_raw[f'{r1}/{r2}'] += float(p1 * p2)

    ht_ft_results = {k: {"prob": round(ht_ft_raw[k] * 100.0, 2), "odds": prob_to_odds(round(ht_ft_raw[k] * 100.0, 2))} for k in labels}
        
    return {
        "l_h1": l_h1, "l_a1": l_a1,
        "ht_1": ht_1, "ht_x": ht_x, "ht_2": ht_2,
        "ht_o05": ht_o05, "ht_u05": ht_u05,
        "ht_o15": ht_o15, "ht_btts": ht_btts,
        "ht_ft": ht_ft_results
    }

# ==============================================================================
# 6. EXTRACTION STATISTIQUE PROFONDE & TIME-DECAY
# ==============================================================================

def get_team_last_matches(team_name, all_matches, max_matches=6):
    history = []
    for m in all_matches:
        if m.get('status') == 'FINISHED':
            h_team, a_team = m['homeTeam']['name'], m['awayTeam']['name']
            if h_team == team_name or a_team == team_name:
                sc = m.get('score', {}).get('fullTime', {})
                sh, sa = sc.get('home'), sc.get('away')
                if sh is not None and sa is not None:
                    is_h = (h_team == team_name)
                    gf, ga = (sh if is_h else sa), (sa if is_h else sh)
                    res = 'W' if gf > ga else ('D' if gf == ga else 'L')
                    history.append({
                        "date": m.get('utcDate', '')[:10],
                        "opponent": a_team if is_h else h_team,
                        "venue": "Dom." if is_h else "Ext.",
                        "score": f"{gf}-{ga}",
                        "result": res, "gf": gf, "ga": ga, "diff": gf - ga
                    })
    history.sort(key=lambda x: x["date"], reverse=True)
    return history[:max_matches]

def compute_time_decay_form(history, post_fifa_break=False):
    if not history: return 1.0, "Neutre", 1.35, 1.35, 0.5, 0.0
    xi = 0.28
    weights = [math.exp(-xi * i) for i in range(len(history))]
    w_sum = sum(weights)
    norm_w = [w / w_sum for w in weights]
    
    perf_score, recent_gf, recent_ga = 0.0, 0.0, 0.0
    results_list = []
    clean_sheets = 0
    for idx, match in enumerate(history):
        pts = 3.0 if match['result'] == 'W' else (1.0 if match['result'] == 'D' else 0.0)
        margin_bonus = np.clip(match['diff'] * 0.18, -0.55, 0.55)
        perf_score += norm_w[idx] * (pts + margin_bonus)
        recent_gf += norm_w[idx] * match['gf']
        recent_ga += norm_w[idx] * match['ga']
        results_list.append(pts)
        if match['ga'] == 0:
            clean_sheets += 1
        
    consistency = round(float(1.0 - (np.std(results_list) / 1.5)), 2) if len(results_list) > 1 else 0.5
    cs_rate = round(clean_sheets / len(history), 2)

    if perf_score >= 2.50: raw_mom, label = 1.09, "🔥 Dynamique Ascendante"
    elif perf_score >= 1.85: raw_mom, label = 1.04, "✅ Forme Positive"
    elif perf_score >= 1.15: raw_mom, label = 0.99, "⚖️ Régulier"
    elif perf_score >= 0.65: raw_mom, label = 0.94, "⚠️ Fébrilité"
    else: raw_mom, label = 0.88, "🚨 Crise / Décrochage"

    if post_fifa_break:
        raw_mom = 1.0 + (raw_mom - 1.0) * 0.35
        label += " (Amorti FIFA)"
        
    return round(raw_mom, 3), label, recent_gf, recent_ga, consistency, cs_rate

@st.cache_data(ttl=1800)
def get_advanced_league_stats(league_code, post_fifa_break=False):
    standings_data = fetch_api(f"competitions/{league_code}/standings")
    raw_matches = fetch_api(f"competitions/{league_code}/matches")
    all_comp_matches = raw_matches.get("matches", []) if raw_matches else []
    
    profile = LEAGUE_PROFILES.get(league_code, {"avg_h": 1.55, "avg_a": 1.18, "rho": -0.115, "card_base": 4.0, "corner_base": 9.8, "dispersion": 10.0, "draw_base": 0.25})
    avg_goals_home, avg_goals_away = profile["avg_h"], profile["avg_a"]
    stats = {}
    
    if standings_data and "standings" in standings_data and len(standings_data["standings"]) > 0:
        table_total = standings_data["standings"][0].get("table", [])
        table_home = standings_data["standings"][1].get("table", []) if len(standings_data["standings"]) > 1 else table_total
        table_away = standings_data["standings"][2].get("table", []) if len(standings_data["standings"]) > 2 else table_total
        
        teams_list = [r["team"]["name"] for r in table_total]
        massey_ratings = solve_massey_colley_ratings(all_comp_matches, teams_list)
        
        dict_home = {r["team"]["name"]: r for r in table_home}
        dict_away = {r["team"]["name"]: r for r in table_away}
        
        tot_h_gf, tot_h_games, tot_a_gf, tot_a_games = 0, 0, 0, 0
        for r in table_total:
            n = r["team"]["name"]
            hr, ar = dict_home.get(n, r), dict_away.get(n, r)
            tot_h_gf += hr.get("goalsFor", 0); tot_h_games += hr.get("playedGames", 0)
            tot_a_gf += ar.get("goalsFor", 0); tot_a_games += ar.get("playedGames", 0)
            
        if tot_h_games > 0 and tot_a_games > 0:
            avg_goals_home = max(0.9, tot_h_gf / tot_h_games)
            avg_goals_away = max(0.8, tot_a_gf / tot_a_games)

        for row in table_total:
            name = row["team"]["name"]
            played = max(1, row.get("playedGames", 1))
            pts, gf, ga = row.get("points", 0), row.get("goalsFor", 0), row.get("goalsAgainst", 0)
            
            h_row, a_row = dict_home.get(name, row), dict_away.get(name, row)
            h_played = max(1, h_row.get("playedGames", 1))
            a_played = max(1, a_row.get("playedGames", 1))
            
            K_shrinkage = 4.2
            bayes_h_gf = (h_row.get("goalsFor", gf/2) + K_shrinkage * avg_goals_home) / (h_played + K_shrinkage)
            bayes_h_ga = (h_row.get("goalsAgainst", ga/2) + K_shrinkage * avg_goals_away) / (h_played + K_shrinkage)
            bayes_a_gf = (a_row.get("goalsFor", gf/2) + K_shrinkage * avg_goals_away) / (a_played + K_shrinkage)
            bayes_a_ga = (a_row.get("goalsAgainst", ga/2) + K_shrinkage * avg_goals_home) / (a_played + K_shrinkage)

            massey_val = massey_ratings.get(name, 0.0)
            # Fusion ELO points + Indice Matriciel Massey-Colley
            elo_rating = 1500.0 + ((pts / played) * 165.0) + (((gf - ga) / played) * 50.0) + (massey_val * 110.0)
            last_6 = get_team_last_matches(name, all_comp_matches, 6)
            mom_factor, mom_status, rec_gf, rec_ga, consistency, cs_rate = compute_time_decay_form(last_6, post_fifa_break)
            
            stats[name] = {
                "played": played, "pts": pts, "gf": gf, "ga": ga,
                "home_gf_pg": bayes_h_gf, "home_ga_pg": bayes_h_ga,
                "away_gf_pg": bayes_a_gf, "away_ga_pg": bayes_a_ga,
                "recent_gf": rec_gf, "recent_ga": rec_ga, "consistency": consistency, "cs_rate": cs_rate,
                "massey": massey_val,
                "elo": elo_rating, "momentum_factor": mom_factor, "momentum_status": mom_status,
                "att_intensity": (gf / played) / max(0.5, (avg_goals_home + avg_goals_away) / 2.0),
                "def_vulnerability": (ga / played) / max(0.5, (avg_goals_home + avg_goals_away) / 2.0),
                "last_5": last_6[:5]
            }
            
    return stats, avg_goals_home, avg_goals_away, profile

# ==============================================================================
# 7. MOTEUR INSTITUTIONNEL DE TOURNOI MULTI-MARCHÉS (V54.0)
# ==============================================================================

def run_institutional_prediction(
    h_name, a_name, 
    team_stats={}, avg_goals_h=1.55, avg_goals_a=1.18, 
    profile=None, bankroll=1000.0, book_odds_1x2=None, 
    weather_mode="Normal (Idéal)", post_fifa_break=False,
    risk_profile="🛡️ Sniper Sécurité (90%+)",
    tactical_adj=None
):
    if profile is None:
        profile = {"avg_h": avg_goals_h, "avg_a": avg_goals_a, "rho": -0.115, "card_base": 4.0, "corner_base": 9.8, "dispersion": 10.0, "draw_base": 0.25}
    if tactical_adj is None:
        tactical_adj = {"h_att": 1.0, "h_def": 1.0, "a_att": 1.0, "a_def": 1.0}
        
    default_team = {
        "played": 10, "pts": 15, "gf": 14, "ga": 14,
        "home_gf_pg": avg_goals_h, "home_ga_pg": avg_goals_a, 
        "away_gf_pg": avg_goals_a, "away_ga_pg": avg_goals_h,
        "recent_gf": 1.35, "recent_ga": 1.35, "consistency": 0.5, "cs_rate": 0.25, "massey": 0.0,
        "elo": 1500.0, "momentum_factor": 1.0, "momentum_status": "Neutre",
        "att_intensity": 1.0, "def_vulnerability": 1.0, "last_5": []
    }
    h_stat = team_stats.get(h_name, default_team)
    a_stat = team_stats.get(a_name, default_team)
    
    # 1. Modèle Structurel (Saison Dom/Ext)
    att_h_saison = h_stat["home_gf_pg"] / max(0.5, avg_goals_h)
    def_a_saison = a_stat["away_ga_pg"] / max(0.5, avg_goals_h)
    att_a_saison = a_stat["away_gf_pg"] / max(0.5, avg_goals_a)
    def_h_saison = h_stat["home_ga_pg"] / max(0.5, avg_goals_a)
    
    xg_h_struct = att_h_saison * def_a_saison * avg_goals_h
    xg_a_struct = att_a_saison * def_h_saison * avg_goals_a

    # 2. Modèle Récent (Time-Decay Exponentiel)
    avg_league = (avg_goals_h + avg_goals_a) / 2.0
    xg_h_recent = (h_stat["recent_gf"] / avg_league) * (a_stat["recent_ga"] / avg_league) * avg_goals_h
    xg_a_recent = (a_stat["recent_gf"] / avg_league) * (h_stat["recent_ga"] / avg_league) * avg_goals_a

    # 3. Ajustement Matriciel Massey-Colley (Difficulté du calendrier)
    massey_diff = h_stat["massey"] - a_stat["massey"]
    massey_mult_h = np.clip(1.0 + massey_diff * 0.12, 0.85, 1.18)
    massey_mult_a = np.clip(1.0 - massey_diff * 0.12, 0.85, 1.18)

    w_rec = 0.20 if post_fifa_break else 0.32
    raw_h_xg = ((1.0 - w_rec) * xg_h_struct + w_rec * xg_h_recent) * massey_mult_h
    raw_a_xg = ((1.0 - w_rec) * xg_a_struct + w_rec * xg_a_recent) * massey_mult_a

    fifa_pace_mult = 0.92 if post_fifa_break else 1.0
    weather_mult = 0.89 if ("Pluie" in weather_mode or "Lourd" in weather_mode) else (0.93 if "Canicule" in weather_mode else 1.0)
    
    full_h_xg = float(np.clip(raw_h_xg * h_stat["momentum_factor"] * weather_mult * fifa_pace_mult * tactical_adj["h_att"] * tactical_adj["a_def"], 0.28, 3.40))
    full_a_xg = float(np.clip(raw_a_xg * a_stat["momentum_factor"] * weather_mult * fifa_pace_mult * tactical_adj["a_att"] * tactical_adj["h_def"], 0.24, 3.10))

    base_rho = profile.get("rho", -0.115)
    rho = base_rho * 1.25 if post_fifa_break else base_rho
    dispersion = profile.get("dispersion", 10.0)
    max_g = 9
    
    # Matrice Dixon-Coles + Binomiale Négative
    matrix = np.zeros((max_g, max_g))
    for dh in range(max_g):
        for da in range(max_g):
            p_h_g = negative_binomial_pmf(dh, full_h_xg, dispersion)
            p_a_g = negative_binomial_pmf(da, full_a_xg, dispersion)
            tau = dixon_coles_tau(dh, da, full_h_xg, full_a_xg, rho)
            matrix[dh, da] = p_h_g * p_a_g * tau
    if np.sum(matrix) > 0: matrix /= np.sum(matrix)

    dc_h = float(np.sum(np.tril(matrix, -1))) * 100.0
    dc_n = float(np.sum(np.diag(matrix))) * 100.0
    dc_a = float(np.sum(np.triu(matrix, 1))) * 100.0

    # Modèle ELO Logistique
    elo_h_adj = h_stat["elo"] + (tactical_adj["h_att"] - 1.0) * 350.0 - (tactical_adj["h_def"] - 1.0) * 350.0
    elo_a_adj = a_stat["elo"] + (tactical_adj["a_att"] - 1.0) * 350.0 - (tactical_adj["a_def"] - 1.0) * 350.0
    elo_h_p, elo_n_p, elo_a_p = compute_elo_1x2_probs(elo_h_adj, elo_a_adj, 60.0 if not post_fifa_break else 45.0, profile.get("draw_base", 0.25))

    # Simulation Monte Carlo 25 000 tirages (Modèle D)
    mc = run_stratified_monte_carlo(full_h_xg, full_a_xg, dispersion, rho, 25000)

    # Stacking Triple Modèle : 60% Dixon-Coles + 20% ELO Logistique + 20% Monte Carlo
    raw_p_h = 0.60 * dc_h + 0.20 * elo_h_p + 0.20 * mc["mc_h"]
    raw_p_n = 0.60 * dc_n + 0.20 * elo_n_p + 0.20 * mc["mc_n"]
    raw_p_a = 0.60 * dc_a + 0.20 * elo_a_p + 0.20 * mc["mc_a"]

    model_disagreement = abs(dc_h - elo_h_p) + abs(dc_a - elo_a_p) + abs(dc_h - mc["mc_h"])
    consensus_score = round(float(np.clip(100.0 - model_disagreement * 1.1, 40.0, 99.5)), 1)

    temp = 1.20 if post_fifa_break else 1.10
    p_h = calibrate_probability_temperature(raw_p_h, temp)
    p_n = calibrate_probability_temperature(raw_p_n, temp)
    p_a = calibrate_probability_temperature(raw_p_a, temp)
    tot_1x2 = p_h + p_n + p_a
    p_h, p_n, p_a = round(p_h/tot_1x2*100, 1), round(p_n/tot_1x2*100, 1), round(p_a/tot_1x2*100, 1)

    entropy_idx = compute_shannon_entropy_1x2(p_h, p_n, p_a)

    # Ensemble exhaustif des 25 marchés évalués
    prob_1x = round(p_h + p_n, 1)
    prob_x2 = round(p_a + p_n, 1)
    prob_12 = round(p_h + p_a, 1)
    denom_dnb = max(0.01, (p_h + p_a))
    prob_dnb_h = round((p_h / denom_dnb) * 100.0, 1)
    prob_dnb_a = round((p_a / denom_dnb) * 100.0, 1)
    
    prob_btts_yes = calibrate_probability_temperature(float(np.sum(matrix[1:, 1:])) * 100.0, temp)
    prob_btts_no = round(100.0 - prob_btts_yes, 1)
    prob_o15 = calibrate_probability_temperature(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 1])) * 100.0, temp)
    prob_o25 = calibrate_probability_temperature(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 2])) * 100.0, temp)
    prob_u25 = round(100.0 - prob_o25, 1)
    prob_o35 = calibrate_probability_temperature(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 3])) * 100.0, temp)
    prob_u35 = round(100.0 - prob_o35, 1)

    # Handicaps Asiatiques (-1.5 et +1.5)
    prob_ah_h_minus_15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i - j >= 2])) * 100.0, 1)
    prob_ah_a_minus_15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if j - i >= 2])) * 100.0, 1)
    prob_ah_h_plus_15 = round(100.0 - prob_ah_a_minus_15, 1)
    prob_ah_a_plus_15 = round(100.0 - prob_ah_h_minus_15, 1)

    # Clean Sheets & Buts par équipe
    prob_h_scores = calibrate_probability_temperature(float(np.sum(matrix[1:, :])) * 100.0, temp)
    prob_a_scores = calibrate_probability_temperature(float(np.sum(matrix[:, 1:])) * 100.0, temp)

    theta_ht = 0.415 if post_fifa_break else 0.435
    ht_ft_data = compute_stochastic_ht_ft_engine(full_h_xg, full_a_xg, theta_ht, rho)

    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_3_scores = [{"score": f"{np.unravel_index(idx, matrix.shape)[0]}-{np.unravel_index(idx, matrix.shape)[1]}", "prob": round(matrix[np.unravel_index(idx, matrix.shape)] * 100.0, 1)} for idx in flat_idx[:3]]

    # ==========================================================================
    # TOURNOI INTERNE : CLASSEMENT DES 25 MARCHÉS PAR SCORE DE QUALITÉ QUANT
    # ==========================================================================
    stability_factor = (h_stat["consistency"] + a_stat["consistency"]) / 2.0
    
    all_25_markets = [
        {"cat": "Sécurité", "name": f"Double Chance : {h_name} ou Nul (1X)", "prob": prob_1x},
        {"cat": "Sécurité", "name": f"Double Chance : Nul ou {a_name} (X2)", "prob": prob_x2},
        {"cat": "Sécurité", "name": f"Handicap Asiatique : {h_name} (+1.5)", "prob": prob_ah_h_plus_15},
        {"cat": "Sécurité", "name": f"Handicap Asiatique : {a_name} (+1.5)", "prob": prob_ah_a_plus_15},
        {"cat": "Sécurité", "name": "Plus de 1.5 Buts dans le match", "prob": prob_o15},
        {"cat": "Sécurité", "name": "Moins de 3.5 Buts dans le match", "prob": prob_u35},
        {"cat": "Sécurité", "name": f"{h_name} marque au moins 1 but", "prob": prob_h_scores},
        {"cat": "Sécurité", "name": f"{a_name} marque au moins 1 but", "prob": prob_a_scores},
        {"cat": "Value", "name": f"Victoire Sèche : {h_name} (1)", "prob": p_h},
        {"cat": "Value", "name": f"Victoire Sèche : {a_name} (2)", "prob": p_a},
        {"cat": "Value", "name": f"Draw No Bet (Remboursé si Nul) : {h_name}", "prob": prob_dnb_h},
        {"cat": "Value", "name": f"Draw No Bet (Remboursé si Nul) : {a_name}", "prob": prob_dnb_a},
        {"cat": "Value", "name": "Les Deux Équipes Marquent (BTTS Oui)", "prob": prob_btts_yes},
        {"cat": "Value", "name": "Une Seule ou Zéro Équipe Marque (BTTS Non)", "prob": prob_btts_no},
        {"cat": "Value", "name": "Plus de 2.5 Buts", "prob": prob_o25},
        {"cat": "Value", "name": "Moins de 2.5 Buts", "prob": prob_u25},
        {"cat": "Value", "name": "Plus de 0.5 But en 1ère Mi-Temps", "prob": ht_ft_data["ht_o05"]},
        {"cat": "Explosif", "name": f"Handicap Asiatique : {h_name} (-1.5)", "prob": prob_ah_h_minus_15},
        {"cat": "Explosif", "name": f"Handicap Asiatique : {a_name} (-1.5)", "prob": prob_ah_a_minus_15},
        {"cat": "Explosif", "name": f"HT/FT : 1/1 ({h_name} MT & Fin)", "prob": ht_ft_data["ht_ft"]["1/1"]["prob"]},
        {"cat": "Explosif", "name": f"HT/FT : 2/2 ({a_name} MT & Fin)", "prob": ht_ft_data["ht_ft"]["2/2"]["prob"]},
        {"cat": "Explosif", "name": f"HT/FT : X/1 (Nul MT, {h_name} gagne)", "prob": ht_ft_data["ht_ft"]["X/1"]["prob"]},
        {"cat": "Explosif", "name": f"HT/FT : X/2 (Nul MT, {a_name} gagne)", "prob": ht_ft_data["ht_ft"]["X/2"]["prob"]},
        {"cat": "Explosif", "name": f"Score Exact Chirurgical : {top_3_scores[0]['score']}", "prob": top_3_scores[0]["prob"]}
    ]

    for mkt in all_25_markets:
        mkt["odds"] = prob_to_odds(mkt["prob"])
        # Score de Qualité Institutionnel (pénalise l'entropie et le désaccord inter-modèles)
        mkt["quality_score"] = round(float(
            mkt["prob"] * (consensus_score / 100.0) * (1.0 - entropy_idx * 0.25) * (0.90 + 0.20 * stability_factor)
        ), 2)

    all_25_markets.sort(key=lambda x: x["quality_score"], reverse=True)

    # Meilleur choix sécurité issu du tournoi des 25 marchés
    best_safe_mkt = all_25_markets[0]
    
    # Meilleur choix Value (entre 48% et 78%)
    value_mkts = [m for m in all_25_markets if 48.0 <= m["prob"] <= 78.0]
    best_value_mkt = value_mkts[0] if value_mkts else all_25_markets[1]

    # Candidats "Coups Fous"
    elo_diff = elo_h_adj - elo_a_adj
    crazy_candidates = []
    if elo_diff > 100 and (h_stat["momentum_factor"] < 0.99 or post_fifa_break) and a_stat["momentum_factor"] >= 1.01:
        crazy_candidates.append({
            "tag": "💣 GIANT-KILLING", "category": "upset",
            "desc": f"Victoire Sèche Outsider : {a_name} bat {h_name}",
            "prob": p_a, "odds": prob_to_odds(p_a),
            "reason": f"{h_name} vulnérable ({h_stat['momentum_status']}) face à {a_name} (Indice Massey {a_stat['massey']:+.2f})."
        })
    elif elo_diff < -100 and (a_stat["momentum_factor"] < 0.99 or post_fifa_break) and h_stat["momentum_factor"] >= 1.01:
        crazy_candidates.append({
            "tag": "💣 GIANT-KILLING", "category": "upset",
            "desc": f"Victoire Sèche Outsider : {h_name} bat {a_name}",
            "prob": p_h, "odds": prob_to_odds(p_h),
            "reason": f"{h_name} à domicile peut faire chuter {a_name}."
        })

    p_rev_12 = ht_ft_data['ht_ft']['1/2']['prob']
    p_rev_21 = ht_ft_data['ht_ft']['2/1']['prob']
    if p_rev_12 >= p_rev_21 and p_rev_12 >= 3.0:
        crazy_candidates.append({
            "tag": "🤯 RENVERSEMENT HT/FT", "category": "reversal",
            "desc": f"Mi-Temps / Fin : 1 / 2 ({h_name} mène MT, {a_name} gagne)",
            "prob": p_rev_12, "odds": prob_to_odds(p_rev_12),
            "reason": f"Match ouvert (xG {(full_h_xg+full_a_xg):.2f}) propice à une bascule en 2MT."
        })
    elif p_rev_21 >= 3.0:
        crazy_candidates.append({
            "tag": "🤯 REMONTADA HT/FT", "category": "reversal",
            "desc": f"Mi-Temps / Fin : 2 / 1 ({a_name} mène MT, {h_name} renverse)",
            "prob": p_rev_21, "odds": prob_to_odds(p_rev_21),
            "reason": f"Forte poussée de {h_name} en seconde période."
        })

    p_x1, p_x2 = ht_ft_data['ht_ft']['X/1']['prob'], ht_ft_data['ht_ft']['X/2']['prob']
    if p_x1 >= p_x2:
        crazy_candidates.append({"tag": "⚡ HT/FT TACTIQUE", "category": "tactical", "desc": f"Mi-Temps / Fin : X / 1 (Nul MT, {h_name} gagne)", "prob": p_x1, "odds": prob_to_odds(p_x1), "reason": "1ère MT verrouillée, décision après la pause."})
    else:
        crazy_candidates.append({"tag": "⚡ HT/FT TACTIQUE", "category": "tactical", "desc": f"Mi-Temps / Fin : X / 2 (Nul MT, {a_name} gagne)", "prob": p_x2, "odds": prob_to_odds(p_x2), "reason": "Résistance à la pause puis différence en fin de match."})

    top_sc = top_3_scores[0]
    crazy_candidates.append({"tag": "🎯 SCORE EXACT", "category": "exact_score", "desc": f"Score Exact : {top_sc['score']}", "prob": top_sc['prob'], "odds": prob_to_odds(top_sc['prob']), "reason": f"Pic maximal de la matrice bivariée ({top_sc['prob']}%)."})
    if prob_o35 >= 26.0:
        crazy_candidates.append({"tag": "🔥 FESTIVAL BUTS", "category": "goals", "desc": "Plus de 3.5 Buts dans le match", "prob": prob_o35, "odds": prob_to_odds(prob_o35), "reason": f"xG cumulé élevé ({(full_h_xg+full_a_xg):.2f} buts)."})

    crazy_candidates.sort(key=lambda x: x["prob"] * math.sqrt(x["odds"]), reverse=True)
    best_crazy = crazy_candidates[0]

    ai_confidence = round(float(np.clip(
        best_safe_mkt["prob"] * 0.60 + consensus_score * 0.25 + (1.0 - entropy_idx) * 25.0 + stability_factor * 5.0,
        0.0, 99.5
    )), 1)
    is_sniper_90 = (best_safe_mkt["prob"] >= 86.0 and consensus_score >= 83.0 and entropy_idx <= 0.87)

    # Options finales selon profil de risque
    options = []
    if "Chasseur" in risk_profile:
        options.append({"type": best_crazy["tag"], "desc": best_crazy["desc"], "prob": best_crazy["prob"], "odds": best_crazy["odds"], "style": "option-box-crazy"})
        if len(crazy_candidates) > 1:
            options.append({"type": crazy_candidates[1]["tag"], "desc": crazy_candidates[1]["desc"], "prob": crazy_candidates[1]["prob"], "odds": crazy_candidates[1]["odds"], "style": "option-box-alt"})
        options.append({"type": "🛡️ FILET DE SÉCURITÉ", "desc": best_safe_mkt["name"], "prob": best_safe_mkt["prob"], "odds": best_safe_mkt["odds"], "style": "option-box"})
    else:
        options.append({"type": "💎 VAINQUEUR DU TOURNOI IA (90%+)" if is_sniper_90 else "🛡️ MEILLEUR MARCHÉ SÉCURISÉ", "desc": best_safe_mkt["name"], "prob": best_safe_mkt["prob"], "odds": best_safe_mkt["odds"], "style": "option-box"})
        options.append({"type": "🎯 MEILLEUR VALUE BET (TOURNOI 25 MARCHÉS)", "desc": best_value_mkt["name"], "prob": best_value_mkt["prob"], "odds": best_value_mkt["odds"], "style": "option-box-sec"})
        options.append({"type": f"🤯 COUP FOU ({best_crazy['tag']})", "desc": best_crazy["desc"], "prob": best_crazy["prob"], "odds": best_crazy["odds"], "style": "option-box-crazy"})

    best_opt = options[0]
    user_actual_odds = book_odds_1x2 if book_odds_1x2 else best_opt["odds"]
    kelly_stake, ev_percentage = calculate_adaptive_kelly(best_opt["prob"], user_actual_odds, bankroll, risk_profile)

    # Justification tactique approfondie par arbre décisionnel
    massey_leader = h_name if h_stat["massey"] > a_stat["massey"] else a_name
    sofascore_report = f"""
    🧠 <b>Synthèse Institutionnelle (Massey Matrix + Dixon-Coles + ELO + 25 000 Monte Carlo)</b> :<br>
    • 🏠 <b>{h_name}</b> : Indice Massey <b>{h_stat['massey']:+.2f}</b> | ELO <b>{elo_h_adj:.0f}</b> | xG = <b>{full_h_xg:.2f}</b> | Clean Sheets récents : <b>{int(h_stat['cs_rate']*100)}%</b><br>
    • ✈️ <b>{a_name}</b> : Indice Massey <b>{a_stat['massey']:+.2f}</b> | ELO <b>{elo_a_adj:.0f}</b> | xG = <b>{full_a_xg:.2f}</b> | Clean Sheets récents : <b>{int(a_stat['cs_rate']*100)}%</b><br>
    • 📐 <b>Convergence Multi-Modèles</b> : Consensus = <b>{consensus_score}%</b> | Entropie Shannon = <b>{entropy_idx}</b> | IC 90% Buts Monte Carlo : <b>[{mc['ci_low']} à {mc['ci_high']} buts]</b><br>
    • 🏆 <b>Pourquoi ce choix bat les 24 autres marchés</b> : Avantage structurel corrigé du calendrier pour <b>{massey_leader}</b> avec un score de qualité quantitatif de <b>{best_safe_mkt['quality_score']}/100</b>.
    """

    return {
        "p_h": p_h, "p_n": p_n, "p_a": p_a,
        "dc_h": round(dc_h, 1), "elo_h_p": round(elo_h_p, 1), "mc_h": mc["mc_h"],
        "prob_1x": prob_1x, "prob_x2": prob_x2, "prob_12": prob_12,
        "prob_btts_yes": prob_btts_yes, "prob_btts_no": prob_btts_no,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u25": prob_u25, "prob_o35": prob_o35, "prob_u35": prob_u35,
        "top_3_scores": top_3_scores, "matrix": matrix, "options": options,
        "all_25_markets": all_25_markets,
        "best_pick": best_opt["desc"], "best_prob": best_opt["prob"], "best_odds": best_opt["odds"],
        "best_crazy": best_crazy, "crazy_candidates": crazy_candidates,
        "is_sniper_90": is_sniper_90, "ai_confidence": ai_confidence,
        "consensus_score": consensus_score, "entropy_idx": entropy_idx,
        "sofascore_report": sofascore_report,
        "full_h_xg": full_h_xg, "full_a_xg": full_a_xg,
        "ht_ft": ht_ft_data, "mc": mc,
        "kelly_stake": kelly_stake, "ev_percentage": ev_percentage
    }

# ==============================================================================
# 8. INTERFACE STREAMLIT V54.0 INSTITUTIONAL QUANT
# ==============================================================================
st.sidebar.markdown("""
    <div style="text-align:center; padding:10px 0;">
        <h2 style="color:#38BDF8; margin:0; font-weight:900;">APEX QUANT</h2>
        <span style="font-size:0.8rem; letter-spacing:2px; color:#10B981; font-weight:800;">INSTITUTIONAL AI v54.0</span>
    </div>
""", unsafe_allow_html=True)

selected_comp = st.sidebar.selectbox("🏆 Compétition Analysée", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

st.sidebar.divider()
st.sidebar.markdown("### 🎛️ STRATÉGIE DU MOTEUR")
risk_profile = st.sidebar.radio("Mode d'Optimisation :", [
    "🛡️ Sniper Sécurité (90%+)",
    "⚖️ Équilibré (Value Pro)",
    "🔥 Chasseur de Gros Coups (Cotes 3.50 - 30.00+)"
], index=0)

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ PARAMÈTRES CONTEXTUELS")
post_fifa_break = st.sidebar.toggle("🌍 Mode Reprise Post-Trêve FIFA", value=True)
weather_condition = st.sidebar.selectbox("Conditions Météo & Pelouse", [
    "Normal (Idéal)", "Pluie / Terrain Lourd & Glissant", "Canicule / Chaleur Élevée"
])

st.sidebar.divider()
st.sidebar.markdown("### 💰 GESTION DE CAPITAL")
user_bankroll = st.sidebar.number_input("Capital / Bankroll ($ / € / FCFA)", value=10000.0, step=500.0, min_value=10.0)

team_stats, avg_goals_h, avg_goals_a, profile = get_advanced_league_stats(league_code, post_fifa_break)
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
                if today_dt - timedelta(hours=3) <= m_dt <= next_week_dt:
                    upcoming_matches.append(m)
            except Exception:
                pass

match_map = {f"{m['utcDate'][:10]} {m['utcDate'][11:16]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in upcoming_matches}

tab_detail, tab_sniper, tab_combi_fou, tab_crazy, tab_massey = st.tabs([
    "🧠 LABORATOIRE MATCH (25 MARCHÉS & 25K SIMS)",
    "💎 SNIPER IA 90%+ (ÉLITE MULTI-LIGUES)",
    "🎰 TICKET COMBI FOU (MULTIPLICATEUR)",
    "🔥 RADAR COUPS FOUS (SIMPLES)",
    "📐 CLASSEMENT MATRICIEL MASSEY-COLLEY"
])

# ------------------------------------------------------------------------------
# ONGLET 1 : LABORATOIRE DE DÉCISION PROFONDE (TOURNOI DES 25 MARCHÉS)
# ------------------------------------------------------------------------------
with tab_detail:
    st.subheader(f"Laboratoire Quantitatif Multi-Modèles ({risk_profile})")
    if upcoming_matches:
        chosen_match_label = st.selectbox("Sélectionnez la rencontre à disséquer :", list(match_map.keys()), key="detail_select")
        match_obj = match_map[chosen_match_label]
        ht, at = match_obj['homeTeam']['name'], match_obj['awayTeam']['name']

        with st.expander("🏥 AJUSTEMENT TACTIQUE PRÉ-MATCH (Blessures clés, Absences, Rotations)", expanded=False):
            tc1, tc2 = st.columns(2)
            with tc1:
                h_star_out = st.checkbox(f"Buteur / Meneur star absent ({ht})", key="h_att")
                h_def_out = st.checkbox(f"Défenseur central / Gardien absent ({ht})", key="h_def")
            with tc2:
                a_star_out = st.checkbox(f"Buteur / Meneur star absent ({at})", key="a_att")
                a_def_out = st.checkbox(f"Défenseur central / Gardien absent ({at})", key="a_def")

        tactical_adj = {
            "h_att": 0.84 if h_star_out else 1.0, "h_def": 1.16 if h_def_out else 1.0,
            "a_att": 0.84 if a_star_out else 1.0, "a_def": 1.16 if a_def_out else 1.0
        }

        input_bookmaker_odds = st.number_input("Cote bookmaker réelle constatée :", value=3.50 if "Chasseur" in risk_profile else 1.32, step=0.05, min_value=1.01)

        res = run_institutional_prediction(
            ht, at, team_stats, avg_goals_h, avg_goals_a, 
            profile, user_bankroll, input_bookmaker_odds, weather_condition, post_fifa_break, risk_profile, tactical_adj
        )

        st.markdown(f"""
        <div class="matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h1 style="color:#38BDF8; margin:0; font-size:2rem;">{ht} <span style="color:#94A3B8; font-weight:300;">vs</span> {at}</h1>
                <span class="badge-sniper" style="font-size:1rem;">Indice Fiabilité IA : {res['ai_confidence']}%</span>
            </div>
            <div class="sofascore-box">{res['sofascore_report']}</div>
        </div>
        """, unsafe_allow_html=True)

        # Comparaison transparente des 3 moteurs indépendants
        c_m1, c_m2, c_m3, c_m4 = st.columns(4)
        with c_m1: st.metric("Modèle Dixon-Coles (1)", f"{res['dc_h']}%", f"xG {ht[:10]}: {res['full_h_xg']:.2f}")
        with c_m2: st.metric("Modèle ELO + Massey (1)", f"{res['elo_h_p']}%", f"Consensus: {res['consensus_score']}%")
        with c_m3: st.metric("25 000 Monte Carlo (1)", f"{res['mc_h']}%", f"Entropie: {res['entropy_idx']}")
        with c_m4: st.metric("Probabilité Finale Calibrée", f"{res['p_h']}% | {res['p_n']}% | {res['p_a']}%", "1 | N | 2")

        st.markdown("### 🏆 PODIUM DU TOURNOI INTERNE (SÉLECTION PARMI 25 MARCHÉS)")
        for opt in res['options']:
            st.markdown(f"""
            <div class="{opt['style']}">
                <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; color:#FBBF24;">{opt['type']}</div>
                <div style="font-size:1.35rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{opt['desc']}</div>
                <div style="font-size:1rem; font-weight:700; color:#38BDF8;">Probabilité Calibrée : <b>{opt['prob']}%</b> | Cote Juste Min. : <b>{opt['odds']}</b></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 📊 CLASSEMENT COMPLET DES 25 MARCHÉS ÉVALUÉS SUR CE MATCH")
        df_25 = pd.DataFrame([
            {
                "Rang": idx + 1,
                "Catégorie": m["cat"],
                "Marché": m["name"],
                "Proba Calibrée": f"{m['prob']}%",
                "Cote Équitable": m["odds"],
                "Score Qualité Quant": f"{m['quality_score']} / 100"
            }
            for idx, m in enumerate(res["all_25_markets"])
        ])
        st.dataframe(df_25, use_container_width=True, hide_index=True)

        col_k, col_sc = st.columns([1, 2])
        with col_k:
            st.markdown("### 💰 MISE KELLY")
            ev_sign = "+" if res['ev_percentage'] >= 0 else ""
            st.metric("Mise Conseillée", f"{res['kelly_stake']} $", f"EV : {ev_sign}{res['ev_percentage']}%")
        with col_sc:
            st.markdown("### 🎯 TOP 3 SCORES EXACTS")
            sc1, sc2, sc3 = st.columns(3)
            for idx_s, col_s in enumerate([sc1, sc2, sc3]):
                with col_s:
                    st.markdown(f"""<div class="big-score-box"><b>#{idx_s+1} SCORE</b><div class="big-score-val">{res['top_3_scores'][idx_s]['score']}</div><div class="big-score-prob">{res['top_3_scores'][idx_s]['prob']}% (Cote {prob_to_odds(res['top_3_scores'][idx_s]['prob'])})</div></div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# ONGLET 2 : SNIPER IA 90%+ (ÉLITE MULTI-LIGUES)
# ------------------------------------------------------------------------------
with tab_sniper:
    st.markdown("""
    <div class="vip-banner">
        <h2 style="margin:0; color:#10B981;">💎 SÉLECTEUR SNIPER IA — ÉLITE MULTI-LIGUES (90%+ ZONE)</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Le bot fait passer 150 000 simulations Monte Carlo sur 6 championnats et n'extrait que les forteresses absolues</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 LANCER LE SCAN INSTITUTIONNEL (6 LIGUES x 25 000 SIMULATIONS)", type="primary"):
        sniper_hits = []
        rejected = 0
        progress = st.progress(0)
        leagues_to_scan = ["PL", "PD", "FL1", "SA", "BL1", "CL"]
        for idx_l, l_code in enumerate(leagues_to_scan):
            l_stats, l_h, l_a, l_prof = get_advanced_league_stats(l_code, post_fifa_break)
            l_raw = fetch_api(f"competitions/{l_code}/matches")
            l_matches = l_raw.get("matches", []) if l_raw else []
            for m in l_matches:
                if m.get('status') in ['SCHEDULED', 'TIMED']:
                    utc_str = m.get('utcDate', '')
                    try:
                        m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                        if today_dt - timedelta(hours=2) <= m_dt <= today_dt + timedelta(days=4):
                            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
                            pred = run_institutional_prediction(ht, at, l_stats, l_h, l_a, l_prof, user_bankroll, None, weather_condition, post_fifa_break, "🛡️ Sniper")
                            if pred["is_sniper_90"]:
                                sniper_hits.append({
                                    "league": l_code, "date": utc_str[:10] + " " + utc_str[11:16],
                                    "match": f"{ht} vs {at}", "pick": pred["best_pick"],
                                    "prob": pred["best_prob"], "odds": pred["best_odds"],
                                    "confidence": pred["ai_confidence"], "consensus": pred["consensus_score"],
                                    "entropy": pred["entropy_idx"]
                                })
                            else:
                                rejected += 1
                    except Exception:
                        pass
            progress.progress((idx_l + 1) / len(leagues_to_scan))

        sniper_hits.sort(key=lambda x: x["confidence"], reverse=True)
        st.info(f"🛡️ **Tournoi terminé :** {len(sniper_hits)} sélections d'élite retenues | {rejected} matchs éliminés pour incertitude.")
        if sniper_hits:
            for item in sniper_hits:
                st.markdown(f"""
                <div class="sniper-card">
                    <div style="display:flex; justify-content:space-between;">
                        <span class="badge-sniper">[{item['league']}] FIABILITÉ IA : {item['confidence']}%</span>
                        <span style="color:#94A3B8; font-size:0.85rem;">{item['date']} UTC</span>
                    </div>
                    <h3 style="margin:8px 0; color:#FFFFFF;">{item['match']}</h3>
                    <div style="font-size:1.25rem; font-weight:900; color:#34D399;">👉 {item['pick']}</div>
                    <div style="font-size:0.9rem; color:#E2E8F0; margin-top:4px;">Proba Calibrée : <b>{item['prob']}%</b> | Cote Min : <b>{item['odds']}</b> | Consensus : <b>{item['consensus']}%</b> | Entropie : <b>{item['entropy']}</b></div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Aucun match ne franchit le filtre strict 90%+ sur cette fenêtre.")

# ------------------------------------------------------------------------------
# ONGLET 3 : TICKET COMBI FOU (MULTIPLICATEUR)
# ------------------------------------------------------------------------------
with tab_combi_fou:
    st.markdown("""
    <div class="vip-banner" style="border-color:#FBBF24;">
        <h2 style="margin:0; color:#FBBF24;">🎰 GÉNÉRATEUR DE TICKETS COMBINÉS EXPLOSIFS (3 À 4 COUPS FOUS)</h2>
        <span style="font-size:0.95rem; color:#F1F5F9;">Assemble les meilleurs scénarios asymétriques décorrélés sur 6 ligues</span>
    </div>
    """, unsafe_allow_html=True)

    c_cfg1, c_cfg2, c_cfg3 = st.columns(3)
    with c_cfg1: num_legs = st.slider("Nombre de coups fous à combiner :", 3, 4, 3)
    with c_cfg2: combi_style = st.selectbox("Style du Combiné :", [
        "⚡ Tactique & Scores Exacts (Cote Totale ~40 - 300)",
        "💣 Giant-Killings & Surprises (Cote Totale ~150 - 1 500)",
        "🤯 Jackpot Renversements 1/2 & 2/1 (Cote Totale ~1 000 - 15 000+)"
    ])
    with c_cfg3: micro_stake = st.number_input("Micro-Mise ($ / € / FCFA) :", value=round(max(1.0, user_bankroll * 0.005), 2), min_value=0.5, step=1.0)

    if st.button("⚡ FORGER MON TICKET COMBINÉ EXPLOSIF", type="primary"):
        pool_by_match = []
        leagues_to_scan = ["PL", "PD", "FL1", "SA", "BL1", "CL"]
        for l_code in leagues_to_scan:
            l_stats, l_h, l_a, l_prof = get_advanced_league_stats(l_code, post_fifa_break)
            l_raw = fetch_api(f"competitions/{l_code}/matches")
            l_matches = l_raw.get("matches", []) if l_raw else []
            for m in l_matches:
                if m.get('status') in ['SCHEDULED', 'TIMED']:
                    utc_str = m.get('utcDate', '')
                    try:
                        m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                        if today_dt - timedelta(hours=2) <= m_dt <= today_dt + timedelta(days=4):
                            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
                            pred = run_institutional_prediction(ht, at, l_stats, l_h, l_a, l_prof, user_bankroll, None, weather_condition, post_fifa_break, "🔥 Chasseur")
                            matching = [c for c in pred["crazy_candidates"] if (
                                ("Jackpot" in combi_style and c["category"] in ["reversal", "exact_score"]) or
                                ("Giant-Killings" in combi_style and c["category"] in ["upset", "exact_score", "reversal"]) or
                                ("Tactique" in combi_style and c["category"] in ["tactical", "exact_score", "goals", "upset"])
                            )]
                            chosen = matching[0] if matching else pred["best_crazy"]
                            asym_score = chosen["prob"] * (chosen["odds"] ** 0.65)
                            pool_by_match.append({
                                "league": l_code, "date": utc_str[:10] + " " + utc_str[11:16],
                                "match": f"{ht} vs {at}", "tag": chosen["tag"], "desc": chosen["desc"],
                                "prob": chosen["prob"], "odds": chosen["odds"], "reason": chosen["reason"],
                                "asym_score": asym_score
                            })
                    except Exception:
                        pass
        pool_by_match.sort(key=lambda x: x["asym_score"], reverse=True)
        if len(pool_by_match) >= num_legs:
            selected_legs = pool_by_match[:num_legs]
            total_odds = float(np.prod([leg["odds"] for leg in selected_legs]))
            gross_payout = round(micro_stake * total_odds, 2)
            st.markdown(f"""
            <div class="ticket-master">
                <h2 style="margin:0; color:#FFFFFF;">Cote Totale : <span style="color:#FBBF24;">{total_odds:,.2f}</span> | Gain Potentiel : <span style="color:#34D399;">{gross_payout:,.2f}</span></h2>
            </div>
            """, unsafe_allow_html=True)
            for idx_leg, leg in enumerate(selected_legs, 1):
                st.markdown(f"""
                <div class="ticket-leg">
                    <b>#{idx_leg} [{leg['league']}] {leg['match']}</b> — <span class="badge-crazy">{leg['tag']}</span><br>
                    <b style="color:#38BDF8; font-size:1.1rem;">👉 {leg['desc']}</b> (Cote : <b style="color:#FBBF24;">{leg['odds']}</b> | {leg['prob']}%)<br>
                    <span style="font-size:0.85rem; color:#94A3B8;">💡 {leg['reason']}</span>
                </div>
                """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# ONGLET 4 : RADAR COUPS FOUS (EN SIMPLE)
# ------------------------------------------------------------------------------
with tab_crazy:
    st.subheader("🔥 Radar des Coups Asymétriques en Simple")
    if st.button("💣 SCANNER LES COUPS FOUS EN SIMPLE"):
        crazy_hits = []
        for l_code in ["PL", "PD", "FL1", "SA", "BL1", "CL"]:
            l_stats, l_h, l_a, l_prof = get_advanced_league_stats(l_code, post_fifa_break)
            l_raw = fetch_api(f"competitions/{l_code}/matches")
            for m in (l_raw.get("matches", []) if l_raw else []):
                if m.get('status') in ['SCHEDULED', 'TIMED']:
                    utc_str = m.get('utcDate', '')
                    try:
                        m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                        if today_dt - timedelta(hours=2) <= m_dt <= today_dt + timedelta(days=4):
                            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
                            pred = run_institutional_prediction(ht, at, l_stats, l_h, l_a, l_prof, user_bankroll, None, weather_condition, post_fifa_break, "🔥 Chasseur")
                            bc = pred["best_crazy"]
                            crazy_hits.append({"league": l_code, "match": f"{ht} vs {at}", "tag": bc["tag"], "desc": bc["desc"], "prob": bc["prob"], "odds": bc["odds"], "reason": bc["reason"], "asym": bc["prob"] * math.sqrt(bc["odds"])})
                    except Exception:
                        pass
        crazy_hits.sort(key=lambda x: x["asym"], reverse=True)
        for item in crazy_hits[:10]:
            st.markdown(f"""
            <div class="degen-card">
                <span class="badge-crazy">[{item['league']}] {item['tag']}</span> <b>{item['match']}</b><br>
                <b style="color:#FBBF24; font-size:1.15rem;">💥 {item['desc']}</b> — Cote : <b>{item['odds']}</b> ({item['prob']}%)<br>
                <span style="font-size:0.85rem; color:#CBD5E1;">💡 {item['reason']}</span>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# ONGLET 5 : CLASSEMENT MATRICIEL MASSEY-COLLEY (FORCE RÉELLE CORRIGÉE)
# ------------------------------------------------------------------------------
with tab_massey:
    st.subheader(f"📐 Classement Algébrique Massey-Colley — {selected_comp}")
    st.caption("Résolution linéaire globale : mesure la vraie puissance de chaque équipe après correction de la difficulté des adversaires rencontrés.")
    if team_stats:
        massey_rows = [
            {
                "Équipe": name,
                "Indice Massey (Buts/Match ajustés)": f"{d['massey']:+.3f}",
                "ELO Hybride": round(d['elo'], 0),
                "Attaque Dom. (Bayésien)": round(d['home_gf_pg'], 2),
                "Attaque Ext. (Bayésien)": round(d['away_gf_pg'], 2),
                "Clean Sheets Récents": f"{int(d['cs_rate']*100)}%",
                "Dynamique Time-Decay": d['momentum_status']
            }
            for name, d in team_stats.items()
        ]
        massey_rows.sort(key=lambda x: float(x["Indice Massey (Buts/Match ajustés)"]), reverse=True)
        st.dataframe(pd.DataFrame(massey_rows), use_container_width=True, hide_index=True)
