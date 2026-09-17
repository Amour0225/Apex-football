import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION ET DESIGN V26.0 ULTRA
# ==========================================
st.set_page_config(
    page_title="Apex Quant v26.0 Ultra-Pro",
    page_icon="⚽",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #060913; color: #F1F5F9; }
    
    .oracle-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #032B45 100%);
        border: 2px solid #38BDF8; border-radius: 16px; padding: 22px; margin-bottom: 22px;
    }
    .sub-card {
        background-color: #0F172A; border: 1.5px solid #1E293B;
        border-radius: 14px; padding: 18px; margin-bottom: 18px;
    }
    .badge-live {
        background-color: #EF4444; color: white; padding: 6px 12px;
        border-radius: 8px; font-weight: 900; font-size: 0.95rem; letter-spacing: 0.5px;
    }
    .badge-upcoming {
        background-color: #3B82F6; color: white; padding: 6px 12px;
        border-radius: 8px; font-weight: 900; font-size: 0.95rem;
    }
    .badge-league {
        background-color: #8B5CF6; color: white; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.85rem; margin-right: 8px;
    }
    
    .big-score-box {
        background: #1E293B; border: 2px solid #38BDF8;
        border-radius: 12px; padding: 15px; text-align: center; margin: 8px 0;
    }
    .big-score-val { font-size: 2.3rem; font-weight: 900; color: #38BDF8; line-height: 1.1; }
    .big-score-prob { font-size: 1.1rem; font-weight: 700; color: #10B981; margin-top: 4px; }

    .value-pick-card {
        background: linear-gradient(135deg, #064E3B 0%, #047857 100%);
        border: 2px solid #10B981; border-radius: 14px;
        padding: 18px; color: #FFFFFF; text-align: center; margin-bottom: 20px;
    }
    .value-pick-title { font-size: 0.95rem; font-weight: 800; text-transform: uppercase; color: #A7F3D0; }
    .value-pick-main { font-size: 1.7rem; font-weight: 900; color: #FFFFFF; margin: 6px 0; }

    .audit-stat-box {
        background-color: #1E293B; border: 2px solid #3B82F6;
        border-radius: 12px; padding: 15px; text-align: center;
    }

    .coupon-card {
        background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 100%);
        border: 2px solid #8B5CF6; border-radius: 14px; padding: 16px; margin-bottom: 12px;
    }
    .coupon-header {
        background: linear-gradient(135deg, #4C1D95 0%, #6D28D9 100%);
        border: 2px solid #A855F7; border-radius: 16px; padding: 20px; text-align: center; margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. SELECTION STRICTE DES 6 GRANDS CHAMPIONNATS
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Ligue des Champions": "CL"
}

@st.cache_data(ttl=30)
def fetch_api(endpoint):
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

@st.cache_data(ttl=300)
def get_advanced_league_stats(league_code):
    standings_data = fetch_api(f"competitions/{league_code}/standings")
    matches_data = fetch_api(f"competitions/{league_code}/matches")
    
    stats = {}
    avg_goals = 1.35
    
    if standings_data and "standings" in standings_data and len(standings_data["standings"]) > 0:
        table_total = standings_data["standings"][0].get("table", [])
        table_home = standings_data["standings"][1].get("table", []) if len(standings_data["standings"]) > 1 else table_total
        table_away = standings_data["standings"][2].get("table", []) if len(standings_data["standings"]) > 2 else table_total
        
        dict_home = {r["team"]["name"]: r for r in table_home}
        dict_away = {r["team"]["name"]: r for r in table_away}
        
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
            
            pts_per_game = pts / played
            elo_rating = 1500 + (pts_per_game - 1.30) * 190 + ((gf - ga) / played) * 45
            
            seed_val = sum(ord(c) for c in name)
            card_rate = float(np.clip(1.8 + (seed_val % 12) * 0.18 + (ga / played) * 0.25, 1.5, 4.2))
            corner_rate = float(np.clip(4.2 + (seed_val % 15) * 0.20 + (gf / played) * 0.45, 3.8, 7.5))
            midfield_control = float(np.clip(0.85 + (pts / (played * 3.0)) * 0.35, 0.75, 1.30))
            
            stats[name] = {
                "gf_pg": gf / played, "ga_pg": ga / played,
                "home_gf_pg": h_gf / h_played, "home_ga_pg": h_ga / h_played,
                "away_gf_pg": a_gf / a_played, "away_ga_pg": a_ga / a_played,
                "elo": elo_rating, "form_factor": 1.0, "recent_results": [],
                "card_rate": card_rate, "corner_rate": corner_rate,
                "midfield": midfield_control, "played_total": played
            }

    # Calcul dynamique avec dégradation temporelle exponentielle (Pondération dégressive)
    if matches_data and "matches" in matches_data:
        finished = [m for m in matches_data["matches"] if m.get("status") == "FINISHED"]
        finished.sort(key=lambda x: x.get("utcDate", ""))
        
        team_recent_history = {}
        for m in finished:
            h_team = m["homeTeam"]["name"]
            a_team = m["awayTeam"]["name"]
            score_h = m.get("score", {}).get("fullTime", {}).get("home")
            score_a = m.get("score", {}).get("fullTime", {}).get("away")
            
            if score_h is not None and score_a is not None:
                if h_team not in team_recent_history: team_recent_history[h_team] = []
                if a_team not in team_recent_history: team_recent_history[a_team] = []
                
                if score_h > score_a:
                    team_recent_history[h_team].append({'res': 'W', 'gf': score_h, 'ga': score_a, 'pts': 3})
                    team_recent_history[a_team].append({'res': 'L', 'gf': score_a, 'ga': score_h, 'pts': 0})
                elif score_h < score_a:
                    team_recent_history[h_team].append({'res': 'L', 'gf': score_h, 'ga': score_a, 'pts': 0})
                    team_recent_history[a_team].append({'res': 'W', 'gf': score_a, 'ga': score_h, 'pts': 3})
                else:
                    team_recent_history[h_team].append({'res': 'D', 'gf': score_h, 'ga': score_a, 'pts': 1})
                    team_recent_history[a_team].append({'res': 'D', 'gf': score_a, 'ga': score_h, 'pts': 1})

        weights = [0.35, 0.25, 0.20, 0.12, 0.08] # Poids dégressifs des 5 derniers matchs
        for t_name, hist in team_recent_history.items():
            if t_name in stats:
                last_5 = hist[-5:]
                last_5_reversed = list(reversed(last_5)) # Le plus récent en premier
                
                weighted_pts = 0.0
                recent_gf = 0.0
                recent_ga = 0.0
                w_sum = 0.0
                
                for idx, match_res in enumerate(last_5_reversed):
                    w = weights[idx] if idx < len(weights) else 0.05
                    weighted_pts += match_res['pts'] * w
                    recent_gf += match_res['gf'] * w
                    recent_ga += match_res['ga'] * w
                    w_sum += w
                
                if w_sum > 0:
                    weighted_pts /= w_sum
                    recent_gf /= w_sum
                    recent_ga /= w_sum
                
                form_factor = np.clip(0.85 + (weighted_pts / 15.0) * 0.30, 0.85, 1.15)
                stats[t_name]["form_factor"] = form_factor
                stats[t_name]["recent_results"] = [m['res'] for m in last_5]
                
                stats[t_name]["gf_pg"] = (stats[t_name]["gf_pg"] * 0.6) + (recent_gf * 0.4)
                stats[t_name]["ga_pg"] = (stats[t_name]["ga_pg"] * 0.6) + (recent_ga * 0.4)

    return stats, avg_goals

@st.cache_data(ttl=300)
def get_all_competitions_upcoming():
    all_upcoming = []
    league_stats_dict = {}
    league_avg_dict = {}
    
    today_dt = datetime.utcnow()
    next_week_dt = today_dt + timedelta(days=8)
    
    for comp_name, comp_code in COMPETITIONS.items():
        stats, avg_g = get_advanced_league_stats(comp_code)
        league_stats_dict[comp_name] = stats
        league_avg_dict[comp_name] = avg_g
        
        raw = fetch_api(f"competitions/{comp_code}/matches")
        matches = raw.get("matches", []) if raw else []
        
        for m in matches:
            if m.get('status') in ['SCHEDULED', 'TIMED']:
                utc_str = m.get('utcDate', '')
                if utc_str:
                    try:
                        m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                        if today_dt - timedelta(hours=3) <= m_dt <= next_week_dt:
                            m_entry = dict(m)
                            m_entry['league_name'] = comp_name
                            all_upcoming.append(m_entry)
                    except Exception:
                        m_entry = dict(m)
                        m_entry['league_name'] = comp_name
                        all_upcoming.append(m_entry)
                        
    return all_upcoming, league_stats_dict, league_avg_dict

# ==========================================
# 3. MOTEUR TRI-LOIS HYBRIDE (ENSEMBLE LEARNING)
# ==========================================
def dixon_coles_adjustment(x, y, h_xg, a_xg, rho=-0.06):
    if x == 0 and y == 0: return max(0.01, 1.0 - (h_xg * a_xg * rho))
    elif x == 0 and y == 1: return max(0.01, 1.0 + (h_xg * rho))
    elif x == 1 and y == 0: return max(0.01, 1.0 + (a_xg * rho))
    elif x == 1 and y == 1: return max(0.01, 1.0 - rho)
    return 1.0

def nbinom_pmf_mean_dispersion(k, mu, dispersion=0.12):
    """Calcul de probabilité via la loi Binomiale Négative (Ajustement de sur-dispersion)."""
    if mu <= 0: return 1.0 if k == 0 else 0.0
    r = 1.0 / dispersion
    p = r / (r + mu)
    return nbinom.pmf(k, r, p)

def prob_to_odds(p):
    if p <= 0: return 99.00
    return round(100.0 / p, 2)

def run_quant_prediction_v26(h_name, a_name, score_h=0, score_a=0, elapsed_min=0, team_stats={}, avg_goals=1.35, is_live=False):
    default_stat = {
        "gf_pg": 1.35, "ga_pg": 1.25, "home_gf_pg": 1.45, "home_ga_pg": 1.10, 
        "away_gf_pg": 1.15, "away_ga_pg": 1.35, "elo": 1500, "form_factor": 1.0,
        "card_rate": 2.3, "corner_rate": 5.0, "midfield": 1.0, "recent_results": []
    }
    
    h_stat = team_stats.get(h_name, default_stat)
    a_stat = team_stats.get(a_name, default_stat)
    
    h_att = h_stat["home_gf_pg"] / max(0.1, avg_goals)
    h_def = h_stat["home_ga_pg"] / max(0.1, avg_goals)
    a_att = a_stat["away_gf_pg"] / max(0.1, avg_goals)
    a_def = a_stat["away_ga_pg"] / max(0.1, avg_goals)

    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_adj = np.clip(elo_diff / 800.0, -0.25, 0.25)

    full_h_xg = float(np.clip(avg_goals * h_att * a_def * (1.0 + elo_adj) * h_stat["form_factor"], 0.4, 3.4))
    full_a_xg = float(np.clip(avg_goals * a_att * h_def * (1.0 - elo_adj) * a_stat["form_factor"], 0.3, 3.0))

    if is_live:
        rem_factor = max(0.05, (90.0 - float(elapsed_min)) / 90.0) if elapsed_min > 0 else 0.50
        rem_h_xg = full_h_xg * rem_factor
        rem_a_xg = full_a_xg * rem_factor
    else:
        rem_factor = 1.0
        rem_h_xg = full_h_xg
        rem_a_xg = full_a_xg

    max_g = 8
    
    # 1. Matrice de Poisson Dixon-Coles
    matrix_poisson = np.zeros((max_g, max_g))
    # 2. Matrice Binomiale Négative (Sur-dispersion)
    matrix_nbinom = np.zeros((max_g, max_g))

    for dh in range(max_g - score_h):
        for da in range(max_g - score_a):
            # Poisson Dixon Coles
            p_h_pois = poisson.pmf(dh, rem_h_xg)
            p_a_pois = poisson.pmf(da, rem_a_xg)
            adj = dixon_coles_adjustment(dh, da, rem_h_xg, rem_a_xg)
            
            # Binomiale Négative
            p_h_nb = nbinom_pmf_mean_dispersion(dh, rem_h_xg, dispersion=0.12)
            p_a_nb = nbinom_pmf_mean_dispersion(da, rem_a_xg, dispersion=0.12)

            final_h = score_h + dh
            final_a = score_a + da
            if final_h < max_g and final_a < max_g:
                matrix_poisson[final_h, final_a] = p_h_pois * p_a_pois * adj
                matrix_nbinom[final_h, final_a] = p_h_nb * p_a_nb

    # Normalisation
    if np.sum(matrix_poisson) > 0: matrix_poisson /= np.sum(matrix_poisson)
    if np.sum(matrix_nbinom) > 0: matrix_nbinom /= np.sum(matrix_nbinom)

    # Fusion des matrices (60% Dixon-Coles Poisson + 40% Binomiale Négative)
    matrix = 0.60 * matrix_poisson + 0.40 * matrix_nbinom

    # 3. Modèle Logistique ELO direct pour l'issue 1N2
    p_elo_win_h = 1.0 / (1.0 + 10.0 ** (-(elo_diff + 80.0) / 400.0)) # +80 avantage terrain
    p_elo_win_a = 1.0 / (1.0 + 10.0 ** ((elo_diff + 80.0) / 400.0))
    p_elo_draw = np.clip(1.0 - (p_elo_win_h + p_elo_win_a), 0.18, 0.30)
    
    # Re-normalisation ELO
    tot_elo = p_elo_win_h + p_elo_win_a + p_elo_draw
    p_elo_win_h /= tot_elo
    p_elo_draw /= tot_elo
    p_elo_win_a /= tot_elo

    # Probabilités brutes issues de la matrice
    p_h_mat = float(np.sum(np.tril(matrix, -1)))
    p_n_mat = float(np.sum(np.diag(matrix)))
    p_a_mat = float(np.sum(np.triu(matrix, 1)))

    # FUSION FINALE DE L'ENSEMBLE (75% Matrice Hybride + 25% Logistique ELO)
    p_h = (0.75 * p_h_mat + 0.25 * p_elo_win_h) * 100
    p_n = (0.75 * p_n_mat + 0.25 * p_elo_draw) * 100
    p_a = (0.75 * p_a_mat + 0.25 * p_elo_win_a) * 100

    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_3_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "prob": round(matrix[gh, ga] * 100, 1)})

    prob_o15 = round((1.0 - (matrix[0,0] + matrix[1,0] + matrix[0,1])) * 100, 1)
    prob_o25 = round((1.0 - np.sum([matrix[i,j] for i in range(3) for j in range(3) if i+j <= 2])) * 100, 1)
    prob_u35 = round(np.sum([matrix[i,j] for i in range(max_g) for j in range(max_g) if i+j <= 3]) * 100, 1)
    
    prob_h_goal = round((1.0 - (matrix[0,0] + matrix[0,1] + matrix[0,2] + matrix[0,3])) * 100, 1)
    prob_a_goal = round((1.0 - (matrix[0,0] + matrix[1,0] + matrix[2,0] + matrix[3,0])) * 100, 1)

    # Calcul Corners et Cartons
    attack_drive = (full_h_xg + full_a_xg) / 2.5
    exp_c_tot = round(np.clip(((h_stat["corner_rate"] + a_stat["corner_rate"]) * attack_drive * 0.90) * rem_factor, 1.5, 14.0), 1)
    prob_c_6_5 = round((1.0 - poisson.cdf(6, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0

    referee_strictness = round(0.88 + ((sum(ord(c) for c in h_name + a_name) % 35) * 0.01), 2)
    midfield_clash = (h_stat["midfield"] + a_stat["midfield"]) / 2.0
    intensity_mult = 1.10 if abs(h_stat["elo"] - a_stat["elo"]) < 80 else 1.0
    exp_k_tot = round(np.clip(((h_stat["card_rate"] + a_stat["card_rate"]) / 2.0 * referee_strictness * midfield_clash * intensity_mult) * rem_factor, 0.8, 8.5), 1)
    prob_k_2_5 = round((1.0 - poisson.cdf(2, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0

    # 4. ALGORITHME DE SELECTION ULTRA-STRICTE DE PREDICTION (SECURITÉ MAXIMALE)
    best_pick = ""
    best_prob = 0.0
    pick_type = ""
    
    if is_live:
        rem_xg_tot = rem_h_xg + rem_a_xg
        prob_more_goals = round((1.0 - poisson.pmf(0, rem_xg_tot)) * 100, 1)
        if prob_more_goals >= 72.0:
            best_pick = "⚡ En Direct : Au moins 1 BUT supplémentaire"
            best_prob = prob_more_goals
            pick_type = "LIVE_GOAL"
        else:
            best_pick = f"🔒 En Direct : Score {score_h}-{score_a} conservé"
            best_prob = round(100.0 - prob_more_goals, 1)
            pick_type = "LIVE_STABLE"
    else:
        # Recherche prioritaire de sécurité supérieure à 72%
        if prob_o15 >= 78.0:
            best_pick = "⚽ Plus de 1.5 Buts au Total"
            best_prob = prob_o15
            pick_type = "O15"
        elif (p_h + p_n) >= 76.0:
            best_pick = f"🛡️ Double Chance : {h_name} ou Nul (1X)"
            best_prob = round(p_h + p_n, 1)
            pick_type = "1X"
        elif (p_a + p_n) >= 76.0:
            best_pick = f"🛡️ Double Chance : Nul ou {a_name} (X2)"
            best_prob = round(p_a + p_n, 1)
            pick_type = "X2"
        elif prob_h_goal >= 80.0:
            best_pick = f"⚽ {h_name} marque au moins 1 but"
            best_prob = prob_h_goal
            pick_type = "HOME_GOAL"
        elif prob_a_goal >= 80.0:
            best_pick = f"⚽ {a_name} marque au moins 1 but"
            best_prob = prob_a_goal
            pick_type = "AWAY_GOAL"
        elif p_h >= 65.0:
            best_pick = f"🔥 Victoire Directe : {h_name}"
            best_prob = p_h
            pick_type = "HOME_WIN"
        elif p_a >= 65.0:
            best_pick = f"🔥 Victoire Directe : {a_name}"
            best_prob = p_a
            pick_type = "AWAY_WIN"
        elif prob_u35 >= 76.0:
            best_pick = "🛡️ Moins de 3.5 Buts au Total"
            best_prob = prob_u35
            pick_type = "U35"
        else:
            if (p_h + p_n) >= (p_a + p_n):
                best_pick = f"🛡️ Double Chance : {h_name} ou Nul (1X)"
                best_prob = round(p_h + p_n, 1)
                pick_type = "1X"
            else:
                best_pick = f"🛡️ Double Chance : Nul ou {a_name} (X2)"
                best_prob = round(p_a + p_n, 1)
                pick_type = "X2"

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "odds_h": prob_to_odds(p_h), "odds_n": prob_to_odds(p_n), "odds_a": prob_to_odds(p_a),
        "top_3_scores": top_3_scores,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u35": prob_u35,
        "corners": {"tot": exp_c_tot, "p_6_5": prob_c_6_5, "odds_6_5": prob_to_odds(prob_c_6_5)},
        "cards": {"tot": exp_k_tot, "p_2_5": prob_k_2_5, "odds_2_5": prob_to_odds(prob_k_2_5)},
        "h_recent": h_stat.get("recent_results", []),
        "a_recent": a_stat.get("recent_results", []),
        "best_pick": best_pick,
        "best_prob": best_prob,
        "pick_type": pick_type,
        "selected_odds": prob_to_odds(best_prob)
    }

# ==========================================
# 4. INTERFACE UTILISATEUR V26.0
# ==========================================
st.sidebar.title("Apex Quant v26.0 Ultra")
st.sidebar.caption("Championnats Élite uniquement")
selected_comp = st.sidebar.selectbox("Sélectionner la Compétition", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

team_stats, avg_goals = get_advanced_league_stats(league_code)
raw_matches = fetch_api(f"competitions/{league_code}/matches")

all_matches = raw_matches.get("matches", []) if raw_matches else []
live_matches = [m for m in all_matches if m.get('status') in ['IN_PLAY', 'LIVE', 'PAUSED']]

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
                upcoming_matches.append(m)

finished_matches = [m for m in all_matches if m.get('status') == 'FINISHED']

tab_live, tab_calendar, tab_detail, tab_audit, tab_coupon = st.tabs([
    f"🔴 EN DIRECT ({len(live_matches)})",
    f"📅 CALENDRIER ({len(upcoming_matches)})", 
    "📊 ANALYSE DÉTAILLÉE",
    f"📈 AUDIT & FIABILITÉ ({len(finished_matches)})",
    "🎟️ COUPON DU JOUR (HAUTE PRÉCISION)"
])

# ------------------------------------------
# TAB 1: LIVE
# ------------------------------------------
with tab_live:
    st.subheader(f"Matchs en Direct - {selected_comp}")
    if live_matches:
        for m in live_matches:
            h_name = m['homeTeam']['name']
            a_name = m['awayTeam']['name']
            score_obj = m.get('score', {}).get('fullTime', {})
            score_h = score_obj.get('home', 0) if score_obj.get('home') is not None else 0
            score_a = score_obj.get('away', 0) if score_obj.get('away') is not None else 0
            elapsed = 45 if m.get('status') == 'PAUSED' else 55
            
            res_live = run_quant_prediction_v26(h_name, a_name, score_h, score_a, elapsed, team_stats, avg_goals, is_live=True)
            
            st.markdown(f"""
            <div class="oracle-card">
                <span class="badge-live">EN DIRECT ({elapsed}') — SCORE : {score_h} - {score_a}</span>
                <h2 style="color:#38BDF8; margin:10px 0 5px 0; font-weight:900;">{h_name} vs {a_name}</h2>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="value-pick-card">
                <div class="value-pick-title">🎯 CONSEIL OPTIMISÉ EN DIRECT</div>
                <div class="value-pick-main">{res_live['best_pick']}</div>
                <div style="font-size:1.1rem; font-weight:800;">Probabilité estimée : {res_live['best_prob']}%</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucune rencontre en direct actuellement dans cette compétition.")

# ------------------------------------------
# TAB 2: CALENDRIER
# ------------------------------------------
with tab_calendar:
    st.subheader(f"Matchs des 7 Prochains Jours - {selected_comp}")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            date_str = m['utcDate'][:10] + " [" + m['utcDate'][11:16] + "]"
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            pred = run_quant_prediction_v26(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False)
            
            cal_data.append({
                "Date & Heure": date_str,
                "Match": f"{h_team} vs {a_team}",
                "Forme Dom.": "".join(pred["h_recent"]),
                "Forme Ext.": "".join(pred["a_recent"]),
                "Cote 1": pred["odds_h"],
                "Cote N": pred["odds_n"],
                "Cote 2": pred["odds_a"],
                "1er Score Probable": pred['top_3_scores'][0]['score'],
                "Conseil Ultra-Sûr": f"{pred['best_pick']} ({pred['best_prob']}%)"
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match programmé cette semaine.")

# ------------------------------------------
# TAB 3: ANALYSE DETAILLEE
# ------------------------------------------
with tab_detail:
    st.subheader("Analyse Approfondie de Rencontre")
    if upcoming_matches or all_matches:
        match_options = {f"{m['utcDate'][:10]} {m['utcDate'][11:16]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in (upcoming_matches if upcoming_matches else all_matches[:10])}
        selected_m = match_options[st.selectbox("Choisir le match :", list(match_options.keys()))]
        
        h_name, a_name = selected_m['homeTeam']['name'], selected_m['awayTeam']['name']
        res = run_quant_prediction_v26(h_name, a_name, 0, 0, 0, team_stats, avg_goals, is_live=False)
        
        st.markdown(f"""
        <div class="oracle-card">
            <span class="badge-upcoming">DATE : {selected_m['utcDate'][:10]} À {selected_m['utcDate'][11:16]} UTC</span>
            <h1 style="color:#38BDF8; margin:10px 0;">{h_name} vs {a_name}</h1>
            <div style="color:#A7F3D0; font-weight:700;">
                Série Récente (Pondérée) — {h_name} : <b>{' - '.join(res['h_recent'])}</b> | {a_name} : <b>{' - '.join(res['a_recent'])}</b>
            </div>
        </div>
        <div class="value-pick-card">
            <div class="value-pick-title">💎 MEILLEURE OPPORTUNITÉ (CONSEIL OPTIMISÉ)</div>
            <div class="value-pick-main">{res['best_pick']}</div>
            <div style="font-size:1.18rem; font-weight:800;">Fiabilité Multi-Modèles : {res['best_prob']}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🏆 TOP 3 SCORES EXACTS LES PLUS PROBABLES")
        sc1, sc2, sc3 = st.columns(3)
        for i, col in enumerate([sc1, sc2, sc3]):
            with col:
                st.markdown(f"""
                <div class="big-score-box">
                    <div style="color:#94A3B8; font-weight:800;">RANG #{i+1}</div>
                    <div class="big-score-val">{res['top_3_scores'][i]['score']}</div>
                    <div class="big-score-prob">{res['top_3_scores'][i]['prob']}% de chance</div>
                </div>
                """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 4: AUDIT ET FIABILITE
# ------------------------------------------
with tab_audit:
    st.subheader(f"📊 Audit des Performances de l'Algorithme - {selected_comp}")
    if finished_matches:
        audit_rows, total_eval, success_pick_count, success_score_count = [], 0, 0, 0
        for m in finished_matches:
            h_team, a_team = m['homeTeam']['name'], m['awayTeam']['name']
            real_h, real_a = m['score']['fullTime']['home'], m['score']['fullTime']['away']
            
            if real_h is not None and real_a is not None:
                real_score_str = f"{real_h}-{real_a}"
                real_tot_goals = real_h + real_a
                pred = run_quant_prediction_v26(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False)
                
                top_scores = [s['score'] for s in pred['top_3_scores']]
                eval_score = "✅ TOUCHÉ" if real_score_str in top_scores else "❌ ÉCHEC"
                if real_score_str in top_scores: success_score_count += 1
                
                ptype = pred['pick_type']
                pick_success = False
                if ptype == "1X" and real_h >= real_a: pick_success = True
                elif ptype == "X2" and real_a >= real_h: pick_success = True
                elif ptype == "O15" and real_tot_goals > 1: pick_success = True
                elif ptype == "U35" and real_tot_goals <= 3: pick_success = True
                elif ptype == "HOME_WIN" and real_h > real_a: pick_success = True
                elif ptype == "AWAY_WIN" and real_a > real_h: pick_success = True
                elif ptype == "HOME_GOAL" and real_h >= 1: pick_success = True
                elif ptype == "AWAY_GOAL" and real_a >= 1: pick_success = True
                
                if pick_success: success_pick_count += 1
                total_eval += 1
                
                audit_rows.append({
                    "Date": m['utcDate'][:10],
                    "Match": f"{h_team} vs {a_team}",
                    "Score Réel": real_score_str,
                    "Conseil Proposé": pred['best_pick'],
                    "Résultat Conseil": "✅ RÉUSSITE" if pick_success else "❌ ÉCHEC",
                    "Score Exact Top 3": eval_score
                })
        
        if total_eval > 0:
            k1, k2, k3 = st.columns(3)
            k1.metric("Matchs Analysés", total_eval)
            k2.metric("Taux de Réussite Conseils (Picks)", f"{round((success_pick_count/total_eval)*100, 1)}%")
            k3.metric("Top 3 Scores Touchés", f"{round((success_score_count/total_eval)*100, 1)}%")
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)

# ------------------------------------------
# TAB 5: GENERATEUR DE COUPON SÉCURISÉ (2 À 3 MATCHS)
# ------------------------------------------
with tab_coupon:
    st.subheader("🎟️ Coupon du Jour Haute Fiabilité (2 à 3 Matchs Max)")
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        nb_legs = st.radio("Nombre de matchs dans le coupon :", [2, 3], index=0, horizontal=True)
    with col_opt2:
        min_threshold = st.slider("Seuil minimal de sécurité par match (%) :", min_value=70, max_value=85, value=76, step=1)
    
    with st.spinner("Analyse approfondie des 6 championnats élite..."):
        all_multi_matches, multi_stats, multi_avg = get_all_competitions_upcoming()
    
    if len(all_multi_matches) < nb_legs:
        st.warning("Nombre de matchs programmés insuffisant pour former un combiné.")
    else:
        dates_dict = {}
        for m in all_multi_matches:
            dates_dict.setdefault(m['utcDate'][:10], []).append(m)
        
        selected_date = st.selectbox("Date du Coupon :", sorted(list(dates_dict.keys())))
        pool_matches = dates_dict.get(selected_date, []) if len(dates_dict.get(selected_date, [])) >= nb_legs else all_multi_matches
        
        analyzed_list = []
        for m in pool_matches:
            league = m['league_name']
            h_team, a_team = m['homeTeam']['name'], m['awayTeam']['name']
            match_time = m['utcDate'][11:16]
            
            pred = run_quant_prediction_v26(
                h_team, a_team, 0, 0, 0, 
                team_stats=multi_stats.get(league, {}), 
                avg_goals=multi_avg.get(league, 1.35), 
                is_live=False
            )
            
            # Filtre strict basé sur le seuil sélectionné
            if pred["best_prob"] >= float(min_threshold):
                analyzed_list.append({
                    "league": league, "match": f"{h_team} vs {a_team}",
                    "time": match_time, "pick": pred["best_pick"],
                    "prob": pred["best_prob"], "type": pred["pick_type"],
                    "odds": pred["selected_odds"], "top_score": pred['top_3_scores'][0]['score']
                })
        
        # Tri des matchs par plus forte probabilité
        analyzed_list.sort(key=lambda x: x["prob"], reverse=True)
        selected_coupon = analyzed_list[:nb_legs]
        
        if len(selected_coupon) < nb_legs:
            st.error(f"Seulement {len(selected_coupon)} match(s) franchissent le seuil de {min_threshold}% pour cette date. Réduis le seuil ou choisis un autre format pour éviter de valider des pronostics risqués.")
        else:
            total_odds = 1.0
            combined_prob = 1.0
            
            for leg in selected_coupon:
                total_odds *= leg["odds"]
                combined_prob *= (leg["prob"] / 100.0)
                
            total_prob_pct = round(combined_prob * 100, 1)
            
            st.markdown(f"""
            <div class="coupon-header">
                <h2 style="margin:0; color:#F59E0B; font-weight:900;">⚡ COMBINÉ RESTREINT APEX QUANT ({len(selected_coupon)} MATCHS)</h2>
                <div style="font-size:1.4rem; font-weight:800; margin-top:10px; color:#FFFFFF;">
                    Cote Cumulée : <span style="color:#38BDF8; font-size:2.2rem; font-weight:900;">{round(total_odds, 2)}</span>
                </div>
                <div style="font-size:1.1rem; font-weight:700; color:#10B981; margin-top:5px;">
                    Probabilité Globale Estimée : {total_prob_pct}%
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            coupon_export_text = f"🎟️ COUPON APEX QUANT ({selected_date})\n📊 Cote : {round(total_odds, 2)} | Probabilité cumulée : {total_prob_pct}%\n\n"
            for idx, leg in enumerate(selected_coupon, 1):
                st.markdown(f"""
                <div class="coupon-card">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span class="badge-league">{leg['league']}</span>
                            <span style="color:#A855F7; font-weight:900;">#{idx} — [{leg['time']} UTC]</span>
                        </div>
                        <span style="background-color:#10B981; color:white; padding:3px 10px; border-radius:6px; font-weight:800;">Fiabilité : {leg['prob']}%</span>
                    </div>
                    <h3 style="color:#38BDF8; margin:8px 0;">{leg['match']}</h3>
                    <div style="font-size:1.2rem; font-weight:800; color:#FFFFFF;">
                        🎯 Prédiction : <span style="color:#F59E0B;">{leg['pick']}</span>
                    </div>
                    <div style="font-size:0.95rem; color:#94A3B8; margin-top:4px;">
                        Cote : <b>{leg['odds']}</b> | Score estimé : <b>{leg['top_score']}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                coupon_export_text += f"{idx}. [{leg['league']}] {leg['match']}\n   👉 Choix : {leg['pick']} (Cote : {leg['odds']})\n"

            st.markdown("### 📋 DÉTAIL TEXTE DU COUPON")
            st.code(coupon_export_text, language="text")
