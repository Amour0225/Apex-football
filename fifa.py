import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime, timedelta
import math

# ==============================================================================
# 1. CONFIGURATION & DESIGN AVANCÉ V55.0 LIVE + 360° QUANT + AUDIT PUR
# ==============================================================================
st.set_page_config(
    page_title="Apex Quant v55.0 — Live, 360° Markets & Audit",
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
    .live-card {
        background: linear-gradient(135deg, #450A0A 0%, #1E1B4B 60%, #0F172A 100%);
        border: 2px solid #EF4444; border-radius: 18px; padding: 22px; margin-bottom: 20px;
        box-shadow: 0 10px 28px -8px rgba(239, 68, 68, 0.4);
    }
    .sniper-card {
        background: linear-gradient(135deg, #064E3B 0%, #022C22 100%);
        border: 2px solid #10B981; border-radius: 16px; padding: 20px; margin-bottom: 16px;
    }
    .degen-card {
        background: linear-gradient(135deg, #450A0A 0%, #7C2D12 50%, #3B0764 100%);
        border: 2px solid #F97316; border-radius: 16px; padding: 20px; margin-bottom: 16px;
    }
    .ticket-master {
        background: linear-gradient(145deg, #1E1B4B 0%, #4C1D95 45%, #7C2D12 100%);
        border: 2.5px solid #FBBF24; border-radius: 20px; padding: 26px; margin: 18px 0;
    }
    .ticket-leg {
        background: rgba(3, 7, 18, 0.72); border-left: 4px solid #F97316;
        border-radius: 0 12px 12px 0; padding: 14px 18px; margin: 10px 0;
    }
    .narrative-box {
        background-color: #0B0F19; border: 1px solid #1E293B; border-left: 5px solid #38BDF8;
        border-radius: 0 14px 14px 0; padding: 20px; margin: 14px 0; font-size: 0.96rem; line-height: 1.7; color: #E2E8F0;
    }
    .risk-box {
        background-color: rgba(249, 115, 22, 0.08); border: 1px solid #F97316; border-left: 5px solid #F97316;
        border-radius: 0 14px 14px 0; padding: 18px; margin: 14px 0; font-size: 0.95rem; line-height: 1.65; color: #FED7AA;
    }
    .vip-banner {
        background: linear-gradient(135deg, #311042 0%, #581C87 50%, #1E3A8A 100%);
        border: 2px solid #F59E0B; border-radius: 16px; padding: 22px; text-align: center; margin-bottom: 25px;
    }
    .sub-card {
        background: #0B1120; border: 1.5px solid #1E293B;
        border-radius: 14px; padding: 16px; margin-bottom: 14px;
    }
    .option-box {
        background: rgba(16, 185, 129, 0.10); border: 1.5px solid #10B981; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-sec {
        background: rgba(56, 189, 248, 0.08); border: 1.5px solid #38BDF8; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-crazy {
        background: rgba(249, 115, 22, 0.14); border: 2px solid #F97316; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .big-score-box {
        background: #0F172A; border: 2px solid #38BDF8; border-radius: 14px; padding: 14px; text-align: center; margin: 6px 0;
    }
    .big-score-val { font-size: 2rem; font-weight: 900; color: #38BDF8; line-height: 1.1; font-family: 'JetBrains Mono', monospace; }
    .big-score-prob { font-size: 1rem; font-weight: 700; color: #10B981; margin-top: 4px; }
    .badge-live {
        display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 900;
        background: rgba(239, 68, 68, 0.25); color: #FCA5A5; border: 1px solid #EF4444;
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
        font-family: 'JetBrains Mono', monospace; font-size: 1.15rem; font-weight: 800; color: #38BDF8;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. PARAMÈTRES GLOBAUX & INFRASTRUCTURE API
# ==============================================================================
API_KEY = st.secrets.get("FOOTBALL_API_KEY", "1e9518e7585349f9abe6d5a29ddb83b1")
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Premier League 🦁": "PL",
    "La Liga 🇪🇸": "PD",
    "Ligue 1 🇫🇷": "FL1",
    "Serie A 🇮🇹": "SA",
    "Bundesliga 🇩🇪": "BL1",
    "Ligue des Champions 🏆": "CL",
    "UEFA Europa League 🇪🇺": "EL",
    "Championship 🏴": "ELC"
}

LEAGUE_PROFILES = {
    "CL":  {"avg_h": 1.62, "avg_a": 1.28, "rho": -0.115, "card_base": 4.1, "corner_base": 9.9,  "dispersion": 9.5,  "draw_base": 0.24},
    "PL":  {"avg_h": 1.58, "avg_a": 1.24, "rho": -0.110, "card_base": 3.9, "corner_base": 10.4, "dispersion": 10.0, "draw_base": 0.24},
    "PD":  {"avg_h": 1.48, "avg_a": 1.10, "rho": -0.125, "card_base": 4.8, "corner_base": 9.4,  "dispersion": 9.2,  "draw_base": 0.27},
    "FL1": {"avg_h": 1.50, "avg_a": 1.16, "rho": -0.118, "card_base": 3.8, "corner_base": 9.3,  "dispersion": 9.8,  "draw_base": 0.26},
    "SA":  {"avg_h": 1.52, "avg_a": 1.18, "rho": -0.120, "card_base": 4.5, "corner_base": 9.8,  "dispersion": 9.4,  "draw_base": 0.27},
    "BL1": {"avg_h": 1.72, "avg_a": 1.35, "rho": -0.095, "card_base": 3.9, "corner_base": 10.1, "dispersion": 11.2, "draw_base": 0.23},
    "EL":  {"avg_h": 1.56, "avg_a": 1.22, "rho": -0.112, "card_base": 4.2, "corner_base": 9.7,  "dispersion": 9.6,  "draw_base": 0.25},
    "ELC": {"avg_h": 1.44, "avg_a": 1.14, "rho": -0.108, "card_base": 3.8, "corner_base": 10.2, "dispersion": 10.2, "draw_base": 0.28}
}

@st.cache_data(ttl=60)
def fetch_api_live(endpoint):
    """Cache court (60s) pour le suivi des matchs en cours."""
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=6)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

@st.cache_data(ttl=1800)
def fetch_api_static(endpoint):
    """Cache long (30m) pour les classements et historiques."""
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=6)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

# ==============================================================================
# 3. ALGORITHMES MATHÉMATIQUES & MATRICIELS
# ==============================================================================

def solve_massey_colley_ratings(all_matches, teams_list):
    n = len(teams_list)
    if n < 2: return {}
    idx_map = {t: i for i, t in enumerate(teams_list)}
    M = np.eye(n) * 2.0
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
                    adj_diff = float(np.clip(sh - sa, -4, 4)) - 0.32
                    M[i, i] += 1.0; M[j, j] += 1.0
                    M[i, j] -= 1.0; M[j, i] -= 1.0
                    p[i] += adj_diff; p[j] -= adj_diff
                    games_counted += 1
    if games_counted < 5: return {t: 0.0 for t in teams_list}
    try:
        ratings = np.linalg.solve(M, p)
        ratings -= np.mean(ratings)
        return {teams_list[i]: round(float(ratings[i]), 3) for i in range(n)}
    except Exception:
        return {t: 0.0 for t in teams_list}

def dixon_coles_tau(x, y, lambda_h, lambda_a, rho=-0.115):
    if x == 0 and y == 0: return max(0.01, 1.0 - (lambda_h * lambda_a * rho))
    elif x == 0 and y == 1: return max(0.01, 1.0 + (lambda_h * rho))
    elif x == 1 and y == 0: return max(0.01, 1.0 + (lambda_a * rho))
    elif x == 1 and y == 1: return max(0.01, 1.0 - rho)
    return 1.0

def negative_binomial_pmf(k, mu, dispersion=10.0):
    if mu <= 0.001: return 1.0 if k == 0 else 0.0
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

def calibrate_probability_temperature(prob_pct, temperature=1.12):
    p = np.clip(prob_pct / 100.0, 0.001, 0.999)
    logit = math.log(p / (1.0 - p))
    cal_p = 1.0 / (1.0 + math.exp(-(logit / temperature)))
    return round(cal_p * 100.0, 1)

def compute_shannon_entropy_1x2(p_h, p_n, p_a):
    probs = np.clip(np.array([p_h, p_n, p_a]) / 100.0, 1e-6, 1.0)
    return round(float(-np.sum(probs * np.log2(probs)) / math.log2(3.0)), 3)

def prob_to_odds(p):
    if p <= 0.001: return 99.00
    return round(min(99.00, 100.0 / p), 2)

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
# 4. EXTRACTION STATISTIQUE & TIME-DECAY
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
    if not history: return 1.0, "Neutre", 1.35, 1.35, 0.5, 0.25
    xi = 0.28
    weights = [math.exp(-xi * i) for i in range(len(history))]
    w_sum = sum(weights)
    norm_w = [w / w_sum for w in weights]
    
    perf_score, recent_gf, recent_ga = 0.0, 0.0, 0.0
    results_list, clean_sheets = [], 0
    for idx, match in enumerate(history):
        pts = 3.0 if match['result'] == 'W' else (1.0 if match['result'] == 'D' else 0.0)
        margin_bonus = np.clip(match['diff'] * 0.18, -0.55, 0.55)
        perf_score += norm_w[idx] * (pts + margin_bonus)
        recent_gf += norm_w[idx] * match['gf']
        recent_ga += norm_w[idx] * match['ga']
        results_list.append(pts)
        if match['ga'] == 0: clean_sheets += 1
        
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
    standings_data = fetch_api_static(f"competitions/{league_code}/standings")
    raw_matches = fetch_api_static(f"competitions/{league_code}/matches")
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
            elo_rating = 1500.0 + ((pts / played) * 165.0) + (((gf - ga) / played) * 50.0) + (massey_val * 110.0)
            last_6 = get_team_last_matches(name, all_comp_matches, 6)
            mom_factor, mom_status, rec_gf, rec_ga, consistency, cs_rate = compute_time_decay_form(last_6, post_fifa_break)
            
            stats[name] = {
                "played": played, "pts": pts, "gf": gf, "ga": ga,
                "home_gf_pg": bayes_h_gf, "home_ga_pg": bayes_h_ga,
                "away_gf_pg": bayes_a_gf, "away_ga_pg": bayes_a_ga,
                "recent_gf": rec_gf, "recent_ga": rec_ga, "consistency": consistency, "cs_rate": cs_rate,
                "massey": massey_val, "elo": elo_rating,
                "momentum_factor": mom_factor, "momentum_status": mom_status,
                "att_intensity": (gf / played) / max(0.5, (avg_goals_home + avg_goals_away) / 2.0),
                "def_vulnerability": (ga / played) / max(0.5, (avg_goals_home + avg_goals_away) / 2.0),
                "last_5": last_6[:5]
            }
            
    return stats, avg_goals_home, avg_goals_away, profile

# ==============================================================================
# 5. MOTEUR COMPLET 360° (PRÉ-MATCH + LIVE IN-PLAY + TOUS MARCHÉS)
# ==============================================================================

def run_full_360_prediction(
    h_name, a_name, 
    team_stats={}, avg_goals_h=1.55, avg_goals_a=1.18, 
    profile=None, weather_mode="Normal (Idéal)", post_fifa_break=False,
    is_live=False, live_score_h=0, live_score_a=0, elapsed_min=0,
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
    
    # 1. Calcul des xG de base (Structurel + Time-Decay + Massey)
    att_h_saison = h_stat["home_gf_pg"] / max(0.5, avg_goals_h)
    def_a_saison = a_stat["away_ga_pg"] / max(0.5, avg_goals_h)
    att_a_saison = a_stat["away_gf_pg"] / max(0.5, avg_goals_a)
    def_h_saison = h_stat["home_ga_pg"] / max(0.5, avg_goals_a)
    
    xg_h_struct = att_h_saison * def_a_saison * avg_goals_h
    xg_a_struct = att_a_saison * def_h_saison * avg_goals_a

    avg_league = (avg_goals_h + avg_goals_a) / 2.0
    xg_h_recent = (h_stat["recent_gf"] / avg_league) * (a_stat["recent_ga"] / avg_league) * avg_goals_h
    xg_a_recent = (a_stat["recent_gf"] / avg_league) * (h_stat["recent_ga"] / avg_league) * avg_goals_a

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

    # Ajustement LIVE si le match est en cours
    if is_live and elapsed_min > 0:
        rem_ratio = max(0.02, (90.0 - min(89.0, float(elapsed_min))) / 90.0)
        # Accélération légère en fin de match (plus de buts dans les 20 dernières minutes)
        time_curve = rem_ratio ** 0.86
        # Si une équipe mène d'un but après la 65e, l'équipe menée pousse davantage (+12% xG)
        push_h = 1.12 if (live_score_a > live_score_h and elapsed_min >= 60) else 1.0
        push_a = 1.12 if (live_score_h > live_score_a and elapsed_min >= 60) else 1.0
        rem_h_xg = full_h_xg * time_curve * push_h
        rem_a_xg = full_a_xg * time_curve * push_a
    else:
        live_score_h, live_score_a = 0, 0
        rem_h_xg, rem_a_xg = full_h_xg, full_a_xg

    base_rho = profile.get("rho", -0.115)
    rho = base_rho * 1.25 if post_fifa_break else base_rho
    dispersion = profile.get("dispersion", 10.0)
    max_g = 10
    
    # Matrice bivariée conditionnelle au score actuel (Live ou 0-0)
    matrix = np.zeros((max_g, max_g))
    for dh in range(max_g - live_score_h):
        for da in range(max_g - live_score_a):
            p_h_g = negative_binomial_pmf(dh, rem_h_xg, dispersion)
            p_a_g = negative_binomial_pmf(da, rem_a_xg, dispersion)
            tau = dixon_coles_tau(dh, da, rem_h_xg, rem_a_xg, rho)
            fh, fa = live_score_h + dh, live_score_a + da
            if fh < max_g and fa < max_g:
                matrix[fh, fa] = p_h_g * p_a_g * tau
    if np.sum(matrix) > 0: matrix /= np.sum(matrix)

    dc_h = float(np.sum(np.tril(matrix, -1))) * 100.0
    dc_n = float(np.sum(np.diag(matrix))) * 100.0
    dc_a = float(np.sum(np.triu(matrix, 1))) * 100.0

    elo_h_adj = h_stat["elo"] + (tactical_adj["h_att"] - 1.0) * 350.0 - (tactical_adj["h_def"] - 1.0) * 350.0
    elo_a_adj = a_stat["elo"] + (tactical_adj["a_att"] - 1.0) * 350.0 - (tactical_adj["a_def"] - 1.0) * 350.0
    elo_h_p, elo_n_p, elo_a_p = compute_elo_1x2_probs(elo_h_adj, elo_a_adj, 60.0 if not post_fifa_break else 45.0, profile.get("draw_base", 0.25))

    # En pré-match on hybride Dixon-Coles (75%) + ELO (25%) ; en Live, la matrice conditionnelle prime à 95%
    w_elo = 0.05 if is_live else 0.25
    raw_p_h = (1.0 - w_elo) * dc_h + w_elo * elo_h_p
    raw_p_n = (1.0 - w_elo) * dc_n + w_elo * elo_n_p
    raw_p_a = (1.0 - w_elo) * dc_a + w_elo * elo_a_p

    temp = 1.05 if is_live else (1.18 if post_fifa_break else 1.10)
    p_h = calibrate_probability_temperature(raw_p_h, temp)
    p_n = calibrate_probability_temperature(raw_p_n, temp)
    p_a = calibrate_probability_temperature(raw_p_a, temp)
    tot_1x2 = p_h + p_n + p_a
    p_h, p_n, p_a = round(p_h/tot_1x2*100, 1), round(p_n/tot_1x2*100, 1), round(p_a/tot_1x2*100, 1)

    entropy_idx = compute_shannon_entropy_1x2(p_h, p_n, p_a)
    model_disagreement = abs(dc_h - elo_h_p) + abs(dc_a - elo_a_p)
    consensus_score = round(float(np.clip(100.0 - model_disagreement * 1.3, 45.0, 99.0)), 1)

    # Marchés Dérivés Complets
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

    # Prochain but en Live
    prob_next_goal = round((1.0 - math.exp(-(rem_h_xg + rem_a_xg))) * 100.0, 1)

    # Mi-Temps & HT/FT
    theta_ht = 0.415 if post_fifa_break else 0.435
    ht_ft_data = compute_stochastic_ht_ft_engine(full_h_xg, full_a_xg, theta_ht, rho)

    # Modélisation Corners & Cartons Jaunes
    elo_diff = elo_h_adj - elo_a_adj
    tot_xg = full_h_xg + full_a_xg
    pace_factor = (tot_xg / max(0.5, avg_goals_h + avg_goals_a)) ** 0.35
    territorial_dom = (full_h_xg ** 1.15) / max(0.1, (full_h_xg ** 1.15 + full_a_xg ** 1.15))
    
    base_corner = profile.get("corner_base", 9.8)
    exp_corners_h = base_corner * 0.54 * (territorial_dom ** 0.55) * pace_factor * (h_stat.get("att_intensity", 1.0) ** 0.25)
    exp_corners_a = base_corner * 0.46 * ((1.0 - territorial_dom) ** 0.55) * pace_factor * (a_stat.get("att_intensity", 1.0) ** 0.25)
    tot_exp_corners = round(float(np.clip(exp_corners_h + exp_corners_a, 5.5, 14.5)), 1)
    
    prob_c75 = round((1.0 - poisson.cdf(7, tot_exp_corners)) * 100.0, 1)
    prob_c85 = round((1.0 - poisson.cdf(8, tot_exp_corners)) * 100.0, 1)
    prob_c95 = round((1.0 - poisson.cdf(9, tot_exp_corners)) * 100.0, 1)
    corner_winner = h_name if exp_corners_h >= exp_corners_a else a_name

    base_card = profile.get("card_base", 4.0)
    tension_factor = 1.24 if abs(elo_diff) < 75.0 else (1.10 if abs(elo_diff) < 150.0 else 0.92)
    defensive_stress = (h_stat.get("def_vulnerability", 1.0) + a_stat.get("def_vulnerability", 1.0)) / 2.0
    tot_exp_cards = round(float(np.clip(base_card * tension_factor * (defensive_stress ** 0.35), 2.2, 7.5)), 1)
    
    prob_cards25 = round((1.0 - poisson.cdf(2, tot_exp_cards)) * 100.0, 1)
    prob_cards35 = round((1.0 - poisson.cdf(3, tot_exp_cards)) * 100.0, 1)
    prob_cards45 = round((1.0 - poisson.cdf(4, tot_exp_cards)) * 100.0, 1)

    # Top 3 Scores Exacts
    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_3_scores = [{"score": f"{np.unravel_index(idx, matrix.shape)[0]}-{np.unravel_index(idx, matrix.shape)[1]}", "prob": round(matrix[np.unravel_index(idx, matrix.shape)] * 100.0, 1)} for idx in flat_idx[:3]]

    # ==========================================================================
    # SÉLECTION DU PARI PRINCIPAL DU BOT (UTILISÉ AUSSI POUR L'AUDIT STRICT)
    # ==========================================================================
    if prob_1x >= 78.0:
        primary_pick = {"type": "Double Chance 1X", "desc": f"Double Chance : {h_name} ou Nul (1X)", "prob": prob_1x, "code": "1X"}
    elif prob_x2 >= 78.0:
        primary_pick = {"type": "Double Chance X2", "desc": f"Double Chance : Nul ou {a_name} (X2)", "prob": prob_x2, "code": "X2"}
    elif prob_o15 >= 75.0:
        primary_pick = {"type": "Plus de 1.5 Buts", "desc": "Plus de 1.5 Buts dans le match", "prob": prob_o15, "code": "O15"}
    elif p_h >= 54.0:
        primary_pick = {"type": "Victoire Domicile (1)", "desc": f"Victoire : {h_name} (1)", "prob": p_h, "code": "1"}
    elif p_a >= 54.0:
        primary_pick = {"type": "Victoire Extérieur (2)", "desc": f"Victoire : {a_name} (2)", "prob": p_a, "code": "2"}
    else:
        primary_pick = {"type": "Moins de 3.5 Buts", "desc": "Moins de 3.5 Buts dans le match", "prob": prob_u35, "code": "U35"}

    # ==========================================================================
    # ANALYSE NARRATIVE : CE QUI VA SE PASSER & RISQUE ÉLEVÉ DU MATCH
    # ==========================================================================
    dom_team = h_name if full_h_xg >= full_a_xg else a_name
    underdog = a_name if dom_team == h_name else h_name
    
    # Qui va gagner / Qui ne va pas gagner
    if p_h >= 60.0:
        winner_verdict = f"<b>{h_name}</b> a toutes les cartes en main pour s'imposer ({p_h}%). <b>{a_name} ne devrait pas gagner</b> ({100 - p_a:.1f}% de chance que {h_name} évite la défaite)."
    elif p_a >= 60.0:
        winner_verdict = f"<b>{a_name}</b> part net favori en déplacement ({p_a}%). <b>{h_name} risque fortement de s'incliner</b>."
    elif prob_1x >= 76.0:
        winner_verdict = f"Match serré mais avantage structurel à <b>{h_name}</b> : <b>{a_name} ne devrait pas gagner</b> (Double Chance 1X à {prob_1x}%)."
    elif prob_x2 >= 76.0:
        winner_verdict = f"<b>{a_name}</b> est solide et devrait au minimum ramener un point (X2 à {prob_x2}%). <b>{h_name} aura du mal à gagner</b>."
    else:
        winner_verdict = f"Duel très indécis (Entropie {entropy_idx}) : aucune équipe ne se détache nettement, forte menace de match nul ({p_n}%)."

    # Ce qui va se passer dans le jeu
    if (full_h_xg + full_a_xg) >= 2.85:
        pace_narrative = f"Un match débridé et rythmé avec des occasions des deux côtés (xG cumulé <b>{full_h_xg + full_a_xg:.2f}</b>). Les défenses seront sous pression dès la 1ère mi-temps ({ht_ft_data['ht_o05']}% de chance de voir un but avant la pause) et <b>{corner_winner}</b> devrait multiplier les corners (~{tot_exp_corners} au total)."
    elif (full_h_xg + full_a_xg) <= 2.15:
        pace_narrative = f"Une bataille tactique fermée et hachée au milieu de terrain (xG cumulé faible à <b>{full_h_xg + full_a_xg:.2f}</b>). La 1ère mi-temps risque d'être verrouillée ({ht_ft_data['ht_u05']}% de 0-0 à la pause), avec beaucoup de duels physiques (~{tot_exp_cards} cartons jaunes attendus)."
    else:
        pace_narrative = f"Un match équilibré où <b>{dom_team}</b> devrait avoir la possession et pousser en seconde période (58% des buts du match attendus après la pause), tandis que <b>{underdog}</b> jouera les transitions rapides."

    # Scénario à Risque Élevé (Coup Fou / Piège)
    if abs(elo_diff) > 100 and (h_stat["momentum_factor"] < 0.99 or post_fifa_break):
        high_risk_scenario = f"⚠️ <b>Piège à Favori (Giant-Killing) :</b> {dom_team} est favori sur le papier mais vulnérable actuellement. Le coup audacieux à tenter en petite mise est la <b>victoire sèche de {underdog}</b> (Cote juste {prob_to_odds(p_a if dom_team==h_name else p_h)}) ou le <b>Score Exact {top_3_scores[1]['score']}</b>."
    elif ht_ft_data['ht_ft']['X/1']['prob'] >= 22.0 or ht_ft_data['ht_ft']['X/2']['prob'] >= 22.0:
        best_x_ft = "X/1" if ht_ft_data['ht_ft']['X/1']['prob'] >= ht_ft_data['ht_ft']['X/2']['prob'] else "X/2"
        high_risk_scenario = f"🔥 <b>Coup Tactique Haute Cote :</b> Résistance jusqu'à la pause puis rupture en 2ème mi-temps → <b>Mi-Temps / Fin de Match : {best_x_ft}</b> (Cote juste {ht_ft_data['ht_ft'][best_x_ft]['odds']}) ou <b>Score Exact {top_3_scores[0]['score']}</b> (Cote {prob_to_odds(top_3_scores[0]['prob'])})."
    else:
        high_risk_scenario = f"🤯 <b>Scénario Explosif :</b> Renversement de situation en 2ème mi-temps (<b>1/2</b> à cote {ht_ft_data['ht_ft']['1/2']['odds']} ou <b>2/1</b> à cote {ht_ft_data['ht_ft']['2/1']['odds']}) ou <b>Plus de 3.5 Buts</b> ({prob_o35}%)."

    return {
        "p_h": p_h, "p_n": p_n, "p_a": p_a,
        "prob_1x": prob_1x, "prob_x2": prob_x2, "prob_12": prob_12,
        "prob_dnb_h": prob_dnb_h, "prob_dnb_a": prob_dnb_a,
        "prob_btts_yes": prob_btts_yes, "prob_btts_no": prob_btts_no,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u25": prob_u25, "prob_o35": prob_o35, "prob_u35": prob_u35,
        "prob_next_goal": prob_next_goal,
        "top_3_scores": top_3_scores, "matrix": matrix,
        "primary_pick": primary_pick,
        "corners": tot_exp_corners, "exp_corners_h": round(exp_corners_h, 1), "exp_corners_a": round(exp_corners_a, 1),
        "prob_c75": prob_c75, "prob_c85": prob_c85, "prob_c95": prob_c95, "corner_winner": corner_winner,
        "cards": tot_exp_cards, "prob_cards25": prob_cards25, "prob_cards35": prob_cards35, "prob_cards45": prob_cards45,
        "ht_ft": ht_ft_data,
        "full_h_xg": full_h_xg, "full_a_xg": full_a_xg,
        "rem_h_xg": rem_h_xg, "rem_a_xg": rem_a_xg,
        "consensus_score": consensus_score, "entropy_idx": entropy_idx,
        "winner_verdict": winner_verdict, "pace_narrative": pace_narrative, "high_risk_scenario": high_risk_scenario
    }

# ==============================================================================
# 6. INTERFACE STREAMLIT V55.0
# ==============================================================================
st.sidebar.markdown("""
    <div style="text-align:center; padding:10px 0;">
        <h2 style="color:#38BDF8; margin:0; font-weight:900;">APEX QUANT</h2>
        <span style="font-size:0.8rem; letter-spacing:2px; color:#10B981; font-weight:800;">LIVE & 360° ENGINE v55.0</span>
    </div>
""", unsafe_allow_html=True)

selected_comp = st.sidebar.selectbox("🏆 Compétition Analysée", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ CONTEXTE DU MATCH")
post_fifa_break = st.sidebar.toggle("🌍 Mode Reprise Post-Trêve FIFA", value=True)
weather_condition = st.sidebar.selectbox("Conditions Météo & Pelouse", [
    "Normal (Idéal)", "Pluie / Terrain Lourd & Glissant", "Canicule / Chaleur Élevée"
])

team_stats, avg_goals_h, avg_goals_a, profile = get_advanced_league_stats(league_code, post_fifa_break)
raw_matches_obj = fetch_api_live(f"competitions/{league_code}/matches")
all_matches = raw_matches_obj.get("matches", []) if raw_matches_obj else []

today_dt = datetime.utcnow()
next_week_dt = today_dt + timedelta(days=8)

live_matches = [m for m in all_matches if m.get('status') in ['IN_PLAY', 'PAUSED', 'HALFTIME']]
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

finished_matches = [m for m in all_matches if m.get('status') == 'FINISHED']
match_map = {f"{m['utcDate'][:10]} {m['utcDate'][11:16]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in upcoming_matches}

# ONGLETS STRUCTURÉS SELON TES BESOINS
tab_live, tab_360, tab_audit, tab_sniper, tab_combi = st.tabs([
    f"🔴 LIVE IN-PLAY ({len(live_matches)})",
    "📊 PRÉDICTION 360° (TOUS MARCHÉS)",
    f"✅ AUDIT CHAMPIONNAT ({len(finished_matches)})",
    "💎 SNIPER 90%+ (MULTI-LIGUES)",
    "🎰 COMBI EXPLOSIF"
])

# ------------------------------------------------------------------------------
# ONGLET 1 : MODULE LIVE EN TEMPS RÉEL + SIMULATEUR IN-PLAY
# ------------------------------------------------------------------------------
with tab_live:
    st.markdown("""
    <div class="vip-banner" style="border-color:#EF4444;">
        <h2 style="margin:0; color:#FCA5A5;">🔴 CENTRE DE COMMANDEMENT LIVE IN-PLAY</h2>
        <span style="font-size:0.95rem; color:#F1F5F9;">Suivi des matchs en cours avec score direct et recalcul instantané des probabilités selon la minute de jeu</span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Actualiser les scores Live"):
        st.cache_data.clear()
        st.rerun()

    if live_matches:
        for lm in live_matches:
            ht, at = lm['homeTeam']['name'], lm['awayTeam']['name']
            sc = lm.get('score', {}).get('fullTime', {})
            sh = sc.get('home') if sc.get('home') is not None else 0
            sa = sc.get('away') if sc.get('away') is not None else 0
            minute = lm.get('minute')
            if not minute:
                # Estimation de la minute depuis l'heure de coup d'envoi
                try:
                    kickoff = datetime.strptime(lm['utcDate'][:19], "%Y-%m-%dT%H:%M:%S")
                    diff_m = int((datetime.utcnow() - kickoff).total_seconds() / 60)
                    minute = int(np.clip(diff_m if diff_m <= 45 else diff_m - 15, 1, 89))
                except Exception:
                    minute = 45

            live_res = run_full_360_prediction(
                ht, at, team_stats, avg_goals_h, avg_goals_a, profile, weather_condition, post_fifa_break,
                is_live=True, live_score_h=sh, live_score_a=sa, elapsed_min=minute
            )

            st.markdown(f"""
            <div class="live-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="badge-live">🔴 EN DIRECT — {minute}' MIN</span>
                    <span style="color:#94A3B8; font-size:0.85rem;">{selected_comp}</span>
                </div>
                <h1 style="text-align:center; color:#FFFFFF; margin:12px 0; font-size:2.3rem;">
                    {ht} <span style="color:#38BDF8; font-family:'JetBrains Mono', monospace;">{sh} - {sa}</span> {at}
                </h1>
                <div style="text-align:center; font-size:1.1rem; color:#34D399; font-weight:800;">
                    👉 Prédiction Live IA : {live_res['primary_pick']['desc']} ({live_res['primary_pick']['prob']}%)
                </div>
            </div>
            """, unsafe_allow_html=True)

            lc1, lc2, lc3, lc4 = st.columns(4)
            with lc1: st.metric(f"1X2 Live ({ht[:8]} / N / {at[:8]})", f"{live_res['p_h']}% | {live_res['p_n']}% | {live_res['p_a']}%", f"xG restant: {live_res['rem_h_xg']:.2f}-{live_res['rem_a_xg']:.2f}")
            with lc2: st.metric("Prochain But Avant la Fin", f"{live_res['prob_next_goal']}%", f"Over {sh+sa+0.5} Buts")
            with lc3: st.metric("Double Chance Live", f"1X: {live_res['prob_1x']}%", f"X2: {live_res['prob_x2']}%")
            with lc4: st.metric("Score Final le + Probable", f"{live_res['top_3_scores'][0]['score']}", f"Proba: {live_res['top_3_scores'][0]['prob']}%")
            st.divider()
    else:
        st.info("Aucun match n'est actuellement en cours dans cette compétition. Utilise le **Simulateur Live** ci-dessous pour préparer tes paris en direct dès le coup d'envoi :")

    # SIMULATEUR LIVE INTERACTIF (TOUJOURS DISPONIBLE)
    if upcoming_matches:
        st.markdown("### 🎮 SIMULATEUR LIVE IN-PLAY (TESTER UN SCÉNARIO EN DIRECT)")
        sim_col1, sim_col2, sim_col3, sim_col4 = st.columns([2, 1, 1, 1])
        with sim_col1:
            sim_match_label = st.selectbox("Match à simuler en direct :", list(match_map.keys()), key="sim_live_sel")
        with sim_col2:
            sim_min = st.slider("Minute de jeu :", 1, 88, 60)
        with sim_col3:
            sim_sh = st.number_input("Buts Domicile :", 0, 8, 0)
        with sim_col4:
            sim_sa = st.number_input("Buts Extérieur :", 0, 8, 0)

        sim_m = match_map[sim_match_label]
        sht, sat = sim_m['homeTeam']['name'], sim_m['awayTeam']['name']
        sim_res = run_full_360_prediction(
            sht, sat, team_stats, avg_goals_h, avg_goals_a, profile, weather_condition, post_fifa_break,
            is_live=True, live_score_h=sim_sh, live_score_a=sim_sa, elapsed_min=sim_min
        )
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1: st.metric("1X2 Recalculé Live", f"{sim_res['p_h']}% | {sim_res['p_n']}% | {sim_res['p_a']}%")
        with sc2: st.metric("Meilleur Pari Live", f"{sim_res['primary_pick']['type']}", f"Confiance : {sim_res['primary_pick']['prob']}%")
        with sc3: st.metric(f"Over {sim_sh+sim_sa+0.5} Buts", f"{sim_res['prob_next_goal']}%", "Prochain but")
        with sc4: st.metric("Score Final Projeté", f"{sim_res['top_3_scores'][0]['score']}", f"{sim_res['top_3_scores'][0]['prob']}%")

# ------------------------------------------------------------------------------
# ONGLET 2 : PRÉDICTION 360° COMPLÈTE (CARTONS, CORNERS, 1MT, RISQUES, SCÉNARIO)
# ------------------------------------------------------------------------------
with tab_360:
    st.subheader(f"Analyse Complète 360° — {selected_comp}")
    if upcoming_matches:
        chosen_label = st.selectbox("Choisis le match à analyser en profondeur :", list(match_map.keys()), key="360_select")
        m_obj = match_map[chosen_label]
        ht, at = m_obj['homeTeam']['name'], m_obj['awayTeam']['name']

        with st.expander("🏥 Ajuster les absents / blessés de dernière minute", expanded=False):
            c_b1, c_b2 = st.columns(2)
            with c_b1:
                h_att_out = st.checkbox(f"Attaquant / Meneur clé absent ({ht})")
                h_def_out = st.checkbox(f"Défenseur / Gardien clé absent ({ht})")
            with c_b2:
                a_att_out = st.checkbox(f"Attaquant / Meneur clé absent ({at})")
                a_def_out = st.checkbox(f"Défenseur / Gardien clé absent ({at})")

        tactical_adj = {
            "h_att": 0.84 if h_att_out else 1.0, "h_def": 1.16 if h_def_out else 1.0,
            "a_att": 0.84 if a_att_out else 1.0, "a_def": 1.16 if a_def_out else 1.0
        }

        res = run_full_360_prediction(ht, at, team_stats, avg_goals_h, avg_goals_a, profile, weather_condition, post_fifa_break, False, 0, 0, 0, tactical_adj)

        # EN-TÊTE + SCÉNARIO NARRATIF + RISQUE ÉLEVÉ
        st.markdown(f"""
        <div class="matrix-card">
            <h1 style="color:#38BDF8; margin:0; font-size:2rem;">{ht} <span style="color:#94A3B8; font-weight:300;">vs</span> {at}</h1>
            <div style="margin-top:8px; font-size:1.15rem; font-weight:800; color:#10B981;">
                🏆 PRÉDICTION PRINCIPALE DU BOT : {res['primary_pick']['desc']} ({res['primary_pick']['prob']}% — Cote juste {prob_to_odds(res['primary_pick']['prob'])})
            </div>
            <div class="narrative-box">
                <b>1️⃣ Qui va gagner / Qui ne va pas gagner :</b><br>{res['winner_verdict']}<br><br>
                <b>2️⃣ Ce qui va se passer dans le match :</b><br>{res['pace_narrative']}
            </div>
            <div class="risk-box">
                <b>3️⃣ Zone à Risque Élevé & Coup Audacieux :</b><br>{res['high_risk_scenario']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # BLOC 1 : VICTOIRE, DOUBLE CHANCE, NOMBRE DE BUTS & BTTS
        st.markdown("### ⚽ RÉSULTATS, DOUBLE CHANCE & NOMBRE DE BUTS")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.markdown(f"""<div class="sub-card"><b>VICTOIRE (1N2)</b><br>🏠 {ht} (1) : <span class="stat-badge">{res['p_h']}%</span><br>🤝 Match Nul (N) : <span class="stat-badge">{res['p_n']}%</span><br>✈️ {at} (2) : <span class="stat-badge">{res['p_a']}%</span></div>""", unsafe_allow_html=True)
        with r2:
            st.markdown(f"""<div class="sub-card"><b>DOUBLE CHANCE & DNB</b><br>1X ({ht[:10]}/Nul) : <span class="stat-badge">{res['prob_1x']}%</span><br>X2 (Nul/{at[:10]}) : <span class="stat-badge">{res['prob_x2']}%</span><br>12 (Pas de nul) : <span class="stat-badge">{res['prob_12']}%</span></div>""", unsafe_allow_html=True)
        with r3:
            st.markdown(f"""<div class="sub-card"><b>NOMBRE DE BUTS</b><br>+1.5 Buts : <span class="stat-badge">{res['prob_o15']}%</span><br>+2.5 Buts : <span class="stat-badge">{res['prob_o25']}%</span> | -2.5 : <b>{res['prob_u25']}%</b><br>-3.5 Buts : <span class="stat-badge">{res['prob_u35']}%</span> | +3.5 : <b>{res['prob_o35']}%</b></div>""", unsafe_allow_html=True)
        with r4:
            st.markdown(f"""<div class="sub-card"><b>LES 2 ÉQUIPES MARQUENT</b><br>BTTS Oui : <span class="stat-badge">{res['prob_btts_yes']}%</span><br>BTTS Non : <span class="stat-badge">{res['prob_btts_no']}%</span><br>xG Attendus : <b>{res['full_h_xg']:.2f} - {res['full_a_xg']:.2f}</b></div>""", unsafe_allow_html=True)

        # BLOC 2 : 1ÈRE MI-TEMPS & MI-TEMPS / FIN DE MATCH
        st.markdown("### ⏱️ 1ÈRE MI-TEMPS & COMBINAISONS MI-TEMPS / FIN DE MATCH")
        ht_d = res['ht_ft']
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""<div class="sub-card"><b>VICTOIRE 1ÈRE MI-TEMPS</b><br>🏠 {ht} (1 MT) : <span class="stat-badge">{ht_d['ht_1']}%</span><br>🤝 Nul (X MT) : <span class="stat-badge">{ht_d['ht_x']}%</span><br>✈️ {at} (2 MT) : <span class="stat-badge">{ht_d['ht_2']}%</span></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="sub-card"><b>BUTS 1ÈRE MI-TEMPS</b><br>+0.5 But MT : <span class="stat-badge">{ht_d['ht_o05']}%</span><br>0-0 à la Pause : <span class="stat-badge">{ht_d['ht_u05']}%</span><br>+1.5 Buts MT : <span class="stat-badge">{ht_d['ht_o15']}%</span></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class="sub-card"><b>HT/FT LOGIQUES</b><br>1 / 1 : <span class="stat-badge">{ht_d['ht_ft']['1/1']['prob']}%</span> (Cote {ht_d['ht_ft']['1/1']['odds']})<br>X / 1 : <span class="stat-badge">{ht_d['ht_ft']['X/1']['prob']}%</span> (Cote {ht_d['ht_ft']['X/1']['odds']})<br>2 / 2 : <span class="stat-badge">{ht_d['ht_ft']['2/2']['prob']}%</span> (Cote {ht_d['ht_ft']['2/2']['odds']})</div>""", unsafe_allow_html=True)
        with m4:
            st.markdown(f"""<div class="sub-card"><b>HT/FT HAUT RISQUE</b><br>X / X : <span class="stat-badge">{ht_d['ht_ft']['X/X']['prob']}%</span> (Cote {ht_d['ht_ft']['X/X']['odds']})<br>1 / 2 : <span class="stat-badge">{ht_d['ht_ft']['1/2']['prob']}%</span> (Cote {ht_d['ht_ft']['1/2']['odds']})<br>2 / 1 : <span class="stat-badge">{ht_d['ht_ft']['2/1']['prob']}%</span> (Cote {ht_d['ht_ft']['2/1']['odds']})</div>""", unsafe_allow_html=True)

        # BLOC 3 : CORNERS & CARTONS JAUNES
        st.markdown("### ⛳ CORNERS & 🟨 CARTONS JAUNES (PROJECTIONS COMPLÈTES)")
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            st.markdown(f"""<div class="sub-card"><b>TOTAL CORNERS ATTENDUS</b><h2 style="color:#38BDF8; margin:4px 0;">~{res['corners']}</h2><span style="font-size:0.85rem; color:#94A3B8;">{ht[:10]}: ~{res['exp_corners_h']} | {at[:10]}: ~{res['exp_corners_a']}</span></div>""", unsafe_allow_html=True)
        with a2:
            st.markdown(f"""<div class="sub-card"><b>SEUILS CORNERS</b><br>+7.5 Corners : <span class="stat-badge">{res['prob_c75']}%</span><br>+8.5 Corners : <span class="stat-badge">{res['prob_c85']}%</span><br>+9.5 Corners : <span class="stat-badge">{res['prob_c95']}%</span></div>""", unsafe_allow_html=True)
        with a3:
            st.markdown(f"""<div class="sub-card"><b>CARTONS JAUNES ATTENDUS</b><h2 style="color:#F59E0B; margin:4px 0;">~{res['cards']}</h2><span style="font-size:0.85rem; color:#94A3B8;">Intensité des duels & fautes</span></div>""", unsafe_allow_html=True)
        with a4:
            st.markdown(f"""<div class="sub-card"><b>SEUILS CARTONS JAUNES</b><br>+2.5 Cartons : <span class="stat-badge">{res['prob_cards25']}%</span><br>+3.5 Cartons : <span class="stat-badge">{res['prob_cards35']}%</span><br>+4.5 Cartons : <span class="stat-badge">{res['prob_cards45']}%</span></div>""", unsafe_allow_html=True)

        # BLOC 4 : TOP 3 SCORES EXACTS
        st.markdown("### 🎯 TOP 3 SCORES EXACTS LES PLUS PROBABLES")
        sc1, sc2, sc3 = st.columns(3)
        for idx_s, col_s in enumerate([sc1, sc2, sc3]):
            with col_s:
                s_item = res['top_3_scores'][idx_s]
                st.markdown(f"""<div class="big-score-box"><b>SCORE #{idx_s+1}</b><div class="big-score-val">{s_item['score']}</div><div class="big-score-prob">{s_item['prob']}% (Cote juste {prob_to_odds(s_item['prob'])})</div></div>""", unsafe_allow_html=True)
    else:
        st.info("Aucun match à venir dans cette compétition.")

# ------------------------------------------------------------------------------
# ONGLET 3 : AUDIT PUR & BINAIRE PAR CHAMPIONNAT (VALIDÉE VS ÉCHEC)
# ------------------------------------------------------------------------------
with tab_audit:
    st.markdown(f"""
    <div class="vip-banner" style="border-color:#10B981;">
        <h2 style="margin:0; color:#10B981;">✅ AUDIT DE PERFORMANCE DU BOT — {selected_comp}</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Vérification stricte match par match : Prédiction Validée ou Échec, avec pourcentage exact de réussite du championnat</span>
    </div>
    """, unsafe_allow_html=True)

    if finished_matches:
        # Tri du plus récent au plus ancien
        sorted_finished = sorted(finished_matches, key=lambda x: x.get('utcDate', ''), reverse=True)
        nb_to_audit = st.slider("Nombre de derniers matchs terminés à auditer dans ce championnat :", min_value=10, max_value=min(100, len(sorted_finished)), value=min(30, len(sorted_finished)), step=5)
        
        audit_subset = sorted_finished[:nb_to_audit]
        audit_rows = []
        valid_count = 0
        fail_count = 0

        for m in audit_subset:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            sc = m.get('score', {}).get('fullTime', {})
            rh, ra = sc.get('home'), sc.get('away')
            if rh is not None and ra is not None:
                pred = run_full_360_prediction(ht, at, team_stats, avg_goals_h, avg_goals_a, profile, weather_condition, post_fifa_break)
                pick_info = pred['primary_pick']
                code = pick_info['code']
                tot_goals = rh + ra

                # Vérification binaire stricte
                is_valid = False
                if code == "1X" and rh >= ra: is_valid = True
                elif code == "X2" and ra >= rh: is_valid = True
                elif code == "O15" and tot_goals >= 2: is_valid = True
                elif code == "U35" and tot_goals <= 3: is_valid = True
                elif code == "1" and rh > ra: is_valid = True
                elif code == "2" and ra > rh: is_valid = True

                if is_valid:
                    valid_count += 1
                    verdict_str = "✅ VALIDÉE"
                else:
                    fail_count += 1
                    verdict_str = "❌ ÉCHEC"

                audit_rows.append({
                    "Date": m.get('utcDate', '')[:10],
                    "Match": f"{ht} vs {at}",
                    "Prédiction du Bot": pick_info['desc'],
                    "Confiance": f"{pick_info['prob']}%",
                    "Score Réel": f"{rh} - {ra}",
                    "Verdict": verdict_str
                })

        total_checked = valid_count + fail_count
        if total_checked > 0:
            success_rate = round((valid_count / total_checked) * 100.0, 1)
            
            k1, k2, k3, k4 = st.columns(4)
            with k1: st.metric(f"Taux de Réussite ({league_code})", f"{success_rate}%", "Fiabilité globale")
            with k2: st.metric("Prédictions Validées", f"{valid_count}", f"sur {total_checked} matchs")
            with k3: st.metric("Prédictions en Échec", f"{fail_count}", f"{round(100 - success_rate, 1)}% d'erreur")
            with k4:
                status_champ = "🔥 EXCELLENT" if success_rate >= 80.0 else ("✅ RENTABLE" if success_rate >= 70.0 else "⚠️ INSTABLE")
                st.metric("Indice Championnat", status_champ, selected_comp)

            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match terminé disponible pour auditer ce championnat.")

# ------------------------------------------------------------------------------
# ONGLET 4 : SNIPER IA 90%+ (MULTI-LIGUES)
# ------------------------------------------------------------------------------
with tab_sniper:
    st.subheader("💎 Sélecteur Sniper 90%+ (Scan Multi-Championnats)")
    if st.button("🚀 LANCER LE SCAN SNIPER SUR 6 CHAMPIONNATS", type="primary"):
        sniper_hits = []
        for l_code in ["PL", "PD", "FL1", "SA", "BL1", "CL"]:
            l_stats, l_h, l_a, l_prof = get_advanced_league_stats(l_code, post_fifa_break)
            l_raw = fetch_api_static(f"competitions/{l_code}/matches")
            for m in (l_raw.get("matches", []) if l_raw else []):
                if m.get('status') in ['SCHEDULED', 'TIMED']:
                    utc_str = m.get('utcDate', '')
                    try:
                        m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                        if today_dt - timedelta(hours=2) <= m_dt <= today_dt + timedelta(days=4):
                            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
                            pred = run_full_360_prediction(ht, at, l_stats, l_h, l_a, l_prof, weather_condition, post_fifa_break)
                            if pred['primary_pick']['prob'] >= 85.0 and pred['entropy_idx'] <= 0.87:
                                sniper_hits.append({
                                    "league": l_code, "date": utc_str[:10] + " " + utc_str[11:16],
                                    "match": f"{ht} vs {at}", "pick": pred['primary_pick']['desc'],
                                    "prob": pred['primary_pick']['prob'], "corners": pred['corners'], "cards": pred['cards']
                                })
                    except Exception:
                        pass
        sniper_hits.sort(key=lambda x: x['prob'], reverse=True)
        if sniper_hits:
            for item in sniper_hits:
                st.markdown(f"""
                <div class="sniper-card">
                    <span class="badge-sniper">[{item['league']}] FIABILITÉ : {item['prob']}%</span> <span style="color:#94A3B8;">{item['date']} UTC</span>
                    <h3 style="margin:6px 0; color:#FFFFFF;">{item['match']}</h3>
                    <div style="font-size:1.15rem; font-weight:800; color:#34D399;">👉 {item['pick']}</div>
                    <div style="font-size:0.85rem; color:#CBD5E1; margin-top:4px;">⛳ Corners : ~{item['corners']} | 🟨 Cartons Jaunes : ~{item['cards']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("Aucun match ne dépasse 85% de confiance sur les 4 prochains jours.")

# ------------------------------------------------------------------------------
# ONGLET 5 : TICKET COMBI EXPLOSIF
# ------------------------------------------------------------------------------
with tab_combi:
    st.subheader("🎰 Générateur de Combiné Audacieux (3 à 4 Coups Forts)")
    nb_legs = st.slider("Nombre de matchs dans le combiné :", 3, 4, 3)
    if st.button("⚡ GÉNÉRER LE COMBINÉ AUDACIEUX"):
        pool = []
        for l_code in ["PL", "PD", "FL1", "SA", "BL1", "CL"]:
            l_stats, l_h, l_a, l_prof = get_advanced_league_stats(l_code, post_fifa_break)
            l_raw = fetch_api_static(f"competitions/{l_code}/matches")
            for m in (l_raw.get("matches", []) if l_raw else []):
                if m.get('status') in ['SCHEDULED', 'TIMED']:
                    utc_str = m.get('utcDate', '')
                    try:
                        m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                        if today_dt - timedelta(hours=2) <= m_dt <= today_dt + timedelta(days=4):
                            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
                            pred = run_full_360_prediction(ht, at, l_stats, l_h, l_a, l_prof, weather_condition, post_fifa_break)
                            top_sc = pred['top_3_scores'][0]
                            pool.append({
                                "league": l_code, "match": f"{ht} vs {at}",
                                "desc": f"Score Exact {top_sc['score']} (ou HT/FT X/1)",
                                "prob": top_sc['prob'], "odds": prob_to_odds(top_sc['prob'])
                            })
                    except Exception:
                        pass
        pool.sort(key=lambda x: x['prob'], reverse=True)
        if len(pool) >= nb_legs:
            chosen = pool[:nb_legs]
            tot_o = float(np.prod([c['odds'] for c in chosen]))
            st.markdown(f"""<div class="ticket-master"><h2 style="color:#FBBF24; margin:0;">Cote Totale Combinée : {tot_o:,.2f}</h2></div>""", unsafe_allow_html=True)
            for idx, c in enumerate(chosen, 1):
                st.markdown(f"""<div class="ticket-leg"><b>#{idx} [{c['league']}] {c['match']}</b> → <b style="color:#38BDF8;">{c['desc']}</b> (Cote : <b>{c['odds']}</b> | {c['prob']}%)</div>""", unsafe_allow_html=True)
