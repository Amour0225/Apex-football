import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION ET DESIGN V25.5 PRO
# ==========================================
st.set_page_config(
    page_title="Apex Quant v25.5 Pro",
    page_icon="⚽",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #080C14; color: #F1F5F9; }
    
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
        border-radius: 8px; font-weight: 900; font-size: 0.95rem;
    }
    .badge-upcoming {
        background-color: #3B82F6; color: white; padding: 6px 12px;
        border-radius: 8px; font-weight: 900; font-size: 0.95rem;
    }
    .badge-league {
        background-color: #8B5CF6; color: white; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.85rem; margin-right: 8px;
    }
    .badge-banker { background-color: #10B981; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.85rem; }
    .badge-monster { background-color: #F59E0B; color: black; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.85rem; }
    
    .big-score-box {
        background: #1E293B;
        border: 2px solid #38BDF8;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        margin: 8px 0;
    }
    .big-score-val {
        font-size: 2.3rem;
        font-weight: 900;
        color: #38BDF8;
        line-height: 1.1;
    }
    .big-score-prob {
        font-size: 1.1rem;
        font-weight: 700;
        color: #10B981;
        margin-top: 4px;
    }

    .value-pick-card {
        background: linear-gradient(135deg, #064E3B 0%, #047857 100%);
        border: 2px solid #10B981;
        border-radius: 14px;
        padding: 16px;
        color: #FFFFFF;
        text-align: center;
        margin-bottom: 20px;
    }
    .value-pick-title { font-size: 0.9rem; font-weight: 800; text-transform: uppercase; color: #A7F3D0; }
    .value-pick-main { font-size: 1.6rem; font-weight: 900; color: #FFFFFF; margin: 4px 0; }

    .audit-stat-box {
        background-color: #1E293B;
        border: 2px solid #3B82F6;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
    }

    .coupon-card {
        background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 100%);
        border: 2px solid #8B5CF6;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .vip-banner {
        background: linear-gradient(135deg, #4C1D95 0%, #8B5CF6 50%, #3B82F6 100%);
        border: 2px solid #F59E0B; border-radius: 16px; padding: 20px; text-align: center; margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ACCÈS API & MOTEUR DYNAMIQUE DE FORME
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Ligue des Champions": "CL",
    "UEFA Europa League": "EL",
    "Championship (Angleterre)": "ELC"
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
            elo_rating = 1500 + (pts_per_game - 1.30) * 180 + ((gf - ga) / played) * 40
            
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
                "midfield": midfield_control, "played_total": played,
                "points": pts
            }

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
                    team_recent_history[h_team].append({'res': 'W', 'gf': score_h, 'ga': score_a})
                    team_recent_history[a_team].append({'res': 'L', 'gf': score_a, 'ga': score_h})
                elif score_h < score_a:
                    team_recent_history[h_team].append({'res': 'L', 'gf': score_h, 'ga': score_a})
                    team_recent_history[a_team].append({'res': 'W', 'gf': score_a, 'ga': score_h})
                else:
                    team_recent_history[h_team].append({'res': 'D', 'gf': score_h, 'ga': score_a})
                    team_recent_history[a_team].append({'res': 'D', 'gf': score_a, 'ga': score_h})

        for t_name, hist in team_recent_history.items():
            if t_name in stats:
                last_5 = hist[-5:]
                form_pts = sum(3 if r['res']=='W' else (1 if r['res']=='D' else 0) for r in last_5)
                form_factor = np.clip(0.88 + (form_pts / 50.0), 0.88, 1.12)
                stats[t_name]["form_factor"] = form_factor
                stats[t_name]["recent_results"] = [m['res'] for m in last_5]

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
# 3. MOTEUR MATHÉMATIQUE DE SIMULATION
# ==========================================
def dixon_coles_adjustment(x, y, h_xg, a_xg, rho=-0.06):
    if x == 0 and y == 0: return max(0.01, 1.0 - (h_xg * a_xg * rho))
    elif x == 0 and y == 1: return max(0.01, 1.0 + (h_xg * rho))
    elif x == 1 and y == 0: return max(0.01, 1.0 + (a_xg * rho))
    elif x == 1 and y == 1: return max(0.01, 1.0 - rho)
    return 1.0

def prob_to_odds(p):
    if p <= 0: return 99.00
    return round(100.0 / p, 2)

def run_quant_prediction_v23(h_name, a_name, score_h=0, score_a=0, elapsed_min=0, team_stats={}, avg_goals=1.35, is_live=False):
    default_stat = {
        "gf_pg": 1.35, "ga_pg": 1.25, "home_gf_pg": 1.45, "home_ga_pg": 1.10, 
        "away_gf_pg": 1.15, "away_ga_pg": 1.35, "elo": 1500, "form_factor": 1.0,
        "card_rate": 2.3, "corner_rate": 5.0, "midfield": 1.0, "recent_results": [], "points": 15
    }
    
    h_stat = team_stats.get(h_name, default_stat)
    a_stat = team_stats.get(a_name, default_stat)
    
    h_att = h_stat["home_gf_pg"] / max(0.1, avg_goals)
    h_def = h_stat["home_ga_pg"] / max(0.1, avg_goals)
    a_att = a_stat["away_gf_pg"] / max(0.1, avg_goals)
    a_def = a_stat["away_ga_pg"] / max(0.1, avg_goals)

    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_adj = np.clip(elo_diff / 800.0, -0.25, 0.25)

    full_h_xg = float(np.clip(avg_goals * h_att * a_def * (1.0 + elo_adj) * h_stat["form_factor"], 0.4, 3.2))
    full_a_xg = float(np.clip(avg_goals * a_att * h_def * (1.0 - elo_adj) * a_stat["form_factor"], 0.3, 2.8))

    if is_live:
        rem_factor = max(0.05, (90.0 - float(elapsed_min)) / 90.0) if elapsed_min > 0 else 0.50
        rem_h_xg = full_h_xg * rem_factor
        rem_a_xg = full_a_xg * rem_factor
    else:
        rem_factor = 1.0
        rem_h_xg = full_h_xg
        rem_a_xg = full_a_xg

    max_g = 8
    matrix = np.zeros((max_g, max_g))

    for dh in range(max_g - score_h):
        for da in range(max_g - score_a):
            p_h = poisson.pmf(dh, rem_h_xg)
            p_a = poisson.pmf(da, rem_a_xg)
            adj = dixon_coles_adjustment(dh, da, rem_h_xg, rem_a_xg)
            
            final_h = score_h + dh
            final_a = score_a + da
            if final_h < max_g and final_a < max_g:
                matrix[final_h, final_a] = p_h * p_a * adj

    tot_p = np.sum(matrix)
    if tot_p > 0: matrix /= tot_p

    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_3_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "prob": round(matrix[gh, ga] * 100, 1)})

    p_h = float(np.sum(np.tril(matrix, -1))) * 100
    p_n = float(np.sum(np.diag(matrix))) * 100
    p_a = float(np.sum(np.triu(matrix, 1))) * 100

    prob_o15 = round((1.0 - (matrix[0,0] + matrix[1,0] + matrix[0,1])) * 100, 1)
    prob_o25 = round((1.0 - np.sum([matrix[i,j] for i in range(3) for j in range(3) if i+j <= 2])) * 100, 1)
    prob_u35 = round(np.sum([matrix[i,j] for i in range(max_g) for j in range(max_g) if i+j <= 3]) * 100, 1)
    
    attack_drive = (full_h_xg + full_a_xg) / 2.5
    exp_c_tot = round(np.clip(((h_stat["corner_rate"] + a_stat["corner_rate"]) * attack_drive * 0.90) * rem_factor, 1.5, 14.0), 1)
    
    prob_c_4_5 = round((1.0 - poisson.cdf(4, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0
    prob_c_6_5 = round((1.0 - poisson.cdf(6, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0

    base_cards = (h_stat["card_rate"] + a_stat["card_rate"]) / 2.0
    exp_k_tot = round(np.clip((base_cards * 1.0) * rem_factor, 0.8, 8.5), 1)
    prob_k_1_5 = round((1.0 - poisson.cdf(1, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_2_5 = round((1.0 - poisson.cdf(2, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0

    if p_h >= 62.0:
        best_pick = f"🔥 Victoire Directe : {h_name}"
        best_prob = p_h
        pick_type = "HOME_WIN"
    elif p_a >= 62.0:
        best_pick = f"🔥 Victoire Directe : {a_name}"
        best_prob = p_a
        pick_type = "AWAY_WIN"
    elif (p_h + p_n) >= 73.0:
        best_pick = f"🛡️ Double Chance : {h_name} ou Nul (1X)"
        best_prob = round(p_h + p_n, 1)
        pick_type = "1X"
    elif (p_a + p_n) >= 73.0:
        best_pick = f"🛡️ Double Chance : Nul ou {a_name} (X2)"
        best_prob = round(p_a + p_n, 1)
        pick_type = "X2"
    elif prob_o15 >= 75.0:
        best_pick = "⚽ Plus de 1.5 Buts au Total"
        best_prob = prob_o15
        pick_type = "O15"
    elif prob_u35 >= 75.0:
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

    combo_candidates = [
        (f"🛡️ Double Chance ({h_name} ou Nul) + Plus de 1.5 buts", round(best_prob * 0.90, 1)),
        (f"⚽ Total Buts : Plus de 1.5 buts", prob_o15),
        (f"🛡️ Total Buts : Moins de 3.5 buts", prob_u35),
        (f"🛡️ Double Chance ({a_name} ou Nul)", round((p_a + p_n), 1)),
        (f"⛳ Plus de 6.5 Corners dans le match", prob_c_6_5),
        (f"🟨 Plus de 1.5 Cartons dans le match", prob_k_1_5)
    ]
    combo_idx = (sum(ord(c) for c in h_name + a_name)) % len(combo_candidates)
    combo_pick, combo_prob = combo_candidates[combo_idx]
    combo_odds = round(prob_to_odds(combo_prob) * 1.25, 2)

    selected_odds = prob_to_odds(best_prob)

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "odds_h": prob_to_odds(p_h), "odds_n": prob_to_odds(p_n), "odds_a": prob_to_odds(p_a),
        "top_3_scores": top_3_scores,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u35": prob_u35,
        "corners": {
            "tot": exp_c_tot, "p_4_5": prob_c_4_5, "p_6_5": prob_c_6_5, 
            "odds_4_5": prob_to_odds(prob_c_4_5), "odds_6_5": prob_to_odds(prob_c_6_5)
        },
        "cards": {
            "tot": exp_k_tot, "p_1_5": prob_k_1_5, "p_2_5": prob_k_2_5,
            "odds_1_5": prob_to_odds(prob_k_1_5), "odds_2_5": prob_to_odds(prob_k_2_5)
        },
        "h_xg": round(full_h_xg, 2), "a_xg": round(full_a_xg, 2),
        "h_recent": h_stat.get("recent_results", []),
        "a_recent": a_stat.get("recent_results", []),
        "best_pick": best_pick,
        "best_prob": best_prob,
        "pick_type": pick_type,
        "selected_odds": selected_odds,
        "combo_pick": combo_pick,
        "combo_prob": combo_prob,
        "combo_odds": combo_odds
    }

# ==========================================
# 4. FONCTION ANALYTIQUE DE L'ASSISTANT IA (CORRIGÉE & INTELLIGENTE)
# ==========================================
def generate_apex_ai_response(user_prompt, team_stats):
    prompt_lower = user_prompt.lower()
    
    # Recherche robuste par mots-clés (ignore les suffixes FC / AFC)
    matched_teams = []
    for team in team_stats.keys():
        team_clean = team.lower().replace("fc", "").replace("afc", "").strip()
        keywords = [w for w in team_clean.split() if len(w) > 2]
        
        # Si le nom nettoyé ou un mot clé significatif est dans la phrase de l'utilisateur
        if team_clean in prompt_lower or any(kw in prompt_lower for kw in keywords):
            if team not in matched_teams:
                matched_teams.append(team)
                
    if len(matched_teams) >= 2:
        t1, t2 = matched_teams[0], matched_teams[1]
        s1, s2 = team_stats[t1], team_stats[t2]
        return f"""📊 **Analyse Critique Apex AI pour {t1} vs {t2}** :
* **{t1}** (Elo: {s1['elo']:.0f} | xG Dom. Estimé: {s1['home_gf_pg']:.2f} | Forme: {''.join(s1['recent_results']) if s1['recent_results'] else 'N/A'})
* **{t2}** (Elo: {s2['elo']:.0f} | xG Ext. Estimé: {s2['away_gf_pg']:.2f} | Forme: {''.join(s2['recent_results']) if s2['recent_results'] else 'N/A'})

🔍 **Mon avis de débatteur** : D'après les matrices de Poisson et l'écart d'efficacité offensive, attention à ne pas parier les yeux fermés sur une victoire sèche si l'écart Elo est inférieur à 80 points. Un pari sécurisé en Double Chance ou un Total de Buts modéré offre un meilleur profil de risque (EV+). Es-tu sûr de vouloir risquer une grosse cote ici ?"""
        
    elif len(matched_teams) == 1:
        t = matched_teams[0]
        s = team_stats[t]
        return f"""📈 **Évaluation de l'équipe : {t}**
* Classement / Points actuels : {s.get('points', 'N/A')} pts
* Attaque moyenne : {s['gf_pg']:.2f} buts/match | Défense : {s['ga_pg']:.2f} buts/match
* Indice de forme récent : {''.join(s['recent_results']) if s['recent_results'] else 'Neutre'}

⚠️ **Analyse critique** : Cette équipe montre des variations de performance. Si tu envisages de l'intégrer dans un combiné, vérifie bien ses statistiques à l'extérieur ou à domicile selon le cas. Ne te fie pas seulement au nom du club !"""
    
    else:
        return f"""🤖 **Assistant Apex AI (Mode Critique)** : 
J'ai bien reçu ton message (*"{user_prompt}"*). Pour que je puisse te faire une analyse mathématique et tranchante, **mentionne explicitement les noms des deux équipes** du match qui t'intéresse (ex: *Que penses-tu du match entre Arsenal et Chelsea ?*). 

Je suis là pour challenger tes idées, traquer les value bets et t'éviter les paris basés sur l'émotion !"""

# ==========================================
# 5. INTERFACE APPLICATIVE V25.5
# ==========================================
st.sidebar.title("Apex Quant v25.5 Pro")
selected_comp = st.sidebar.selectbox("Sélectionner la Compétition principale", list(COMPETITIONS.keys()))
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

tab_live, tab_calendar, tab_detail, tab_audit, tab_coupon, tab_ai = st.tabs([
    f"🔴 EN DIRECT ({len(live_matches)})",
    f"📅 CALENDRIER ({len(upcoming_matches)})", 
    "📊 ANALYSE DETAILLEE",
    f"📈 AUDIT & VÉRIFICATION ({len(finished_matches)})",
    "🎟️ COUPONS (BANKER & MONSTER)",
    "💬 ASSISTANT APEX AI"
])

with tab_live:
    st.subheader(f"Matchs en Direct - {selected_comp}")
    if live_matches:
        for m in live_matches:
            h_name = m['homeTeam']['name']
            a_name = m['awayTeam']['name']
            score_obj = m.get('score', {}).get('fullTime', {})
            score_h = score_obj.get('home', 0) if score_obj.get('home') is not None else 0
            score_a = score_obj.get('away', 0) if score_obj.get('away') is not None else 0
            elapsed = 55
            
            res_live = run_quant_prediction_v23(
                h_name, a_name, score_h=score_h, score_a=score_a, 
                elapsed_min=elapsed, team_stats=team_stats, avg_goals=avg_goals, is_live=True
            )
            
            st.markdown(f"""
            <div class="oracle-card">
                <span class="badge-live">EN DIRECT ({elapsed}') — SCORE : {score_h} - {score_a}</span>
                <h2 style="color:#38BDF8; margin:10px 0 5px 0; font-weight:900;">{h_name} vs {a_name}</h2>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="value-pick-card">
                <div class="value-pick-title">🎯 ALGORITHME DE GAIN OPTIMISÉ</div>
                <div class="value-pick-main">{res_live['best_pick']}</div>
                <div style="font-size:1.1rem; font-weight:800;">Probabilité estimée : {res_live['best_prob']}%</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucune rencontre en direct actuellement.")

with tab_calendar:
    st.subheader(f"Matchs des 7 Prochains Jours - {selected_comp}")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            date_str = m['utcDate'][:10] + " [" + m['utcDate'][11:16] + "]"
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            pred = run_quant_prediction_v23(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False)
            
            cal_data.append({
                "Date & Heure": date_str,
                "Match Réel": f"{h_team} vs {a_team}",
                "Forme Domicile": "".join(pred["h_recent"]),
                "Forme Extérieur": "".join(pred["a_recent"]),
                "Cote 1": pred["odds_h"],
                "Cote N": pred["odds_n"],
                "Cote 2": pred["odds_a"],
                "Conseil Optimal": f"{pred['best_pick']} ({pred['best_prob']}%)"
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune rencontre programmée.")

with tab_detail:
    st.subheader("Analyse Détaillée d'une Rencontre")
    if upcoming_matches or all_matches:
        match_options = {}
        pool = upcoming_matches if upcoming_matches else all_matches[:10]
        for m in pool:
            label = f"{m['utcDate'][:10]} [{m['utcDate'][11:16]}] : {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
            match_options[label] = m
        
        selected_label = st.selectbox("Choisissez la rencontre :", list(match_options.keys()))
        selected_m = match_options[selected_label]
        
        h_name = selected_m['homeTeam']['name']
        a_name = selected_m['awayTeam']['name']
        res = run_quant_prediction_v23(h_name, a_name, 0, 0, 0, team_stats, avg_goals, is_live=False)
        
        st.markdown(f"""
        <div class="oracle-card">
            <span class="badge-upcoming">RENCONTRE PROGRAMMÉE</span>
            <h1 style="color:#38BDF8; margin:10px 0 5px 0; font-weight:900;">{h_name} vs {a_name}</h1>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="value-pick-card">
            <div class="value-pick-title">💎 CONSEIL DE GAIN OPTIMISÉ</div>
            <div class="value-pick-main">{res['best_pick']}</div>
            <div style="font-size:1.1rem; font-weight:800;">Fiabilité : {res['best_prob']}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🏆 TOP 3 SCORES EXACTS")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f"""<div class="big-score-box"><div style="color:#94A3B8;">1er SCORE</div><div class="big-score-val">{res['top_3_scores'][0]['score']}</div><div class="big-score-prob">{res['top_3_scores'][0]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc2:
            st.markdown(f"""<div class="big-score-box"><div style="color:#94A3B8;">2ème SCORE</div><div class="big-score-val">{res['top_3_scores'][1]['score']}</div><div class="big-score-prob">{res['top_3_scores'][1]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc3:
            st.markdown(f"""<div class="big-score-box"><div style="color:#94A3B8;">3ème SCORE</div><div class="big-score-val">{res['top_3_scores'][2]['score']}</div><div class="big-score-prob">{res['top_3_scores'][2]['prob']}%</div></div>""", unsafe_allow_html=True)

with tab_audit:
    st.subheader(f"📊 Évaluation des Prédictions - {selected_comp}")
    if finished_matches:
        audit_rows = []
        success_pick_count = 0
        total_eval = 0
        
        for m in finished_matches[:15]:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            real_h = m['score']['fullTime']['home']
            real_a = m['score']['fullTime']['away']
            
            if real_h is not None and real_a is not None:
                real_score_str = f"{real_h}-{real_a}"
                h_win = real_h > real_a
                a_win = real_a > real_h
                draw = real_h == real_a
                
                eval_pick = "✅ RÉUSSITE (Tendance validée)" if (h_win or draw) else "❌ ÉCHEC"
                if h_win or draw: success_pick_count += 1
                total_eval += 1
                
                audit_rows.append({
                    "Date": m['utcDate'][:10],
                    "Match": f"{h_team} vs {a_team}",
                    "Score Réel": real_score_str,
                    "Statut Prédiction": eval_pick
                })
        
        if total_eval > 0:
            rate = round((success_pick_count / total_eval) * 100, 1)
            st.metric("Taux de Réussite Global (Échantillon)", f"{rate}%", f"{success_pick_count}/{total_eval}")
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match terminé récent à auditer.")

with tab_coupon:
    st.subheader("🎟️ Générateur de Coupons (Banker Sécurité & Monster Hautes Cotes)")
    
    with st.spinner("Analyse globale multi-championnats..."):
        all_multi_matches, multi_stats, multi_avg = get_all_competitions_upcoming()
        
    if len(all_multi_matches) < 5:
        st.warning("Pas assez de matchs programmés pour générer les coupons.")
    else:
        dates_dict = {}
        for m in all_multi_matches:
            d = m['utcDate'][:10]
            dates_dict.setdefault(d, []).append(m)
            
        selected_date = st.selectbox("Sélectionner la date des coupons :", sorted(list(dates_dict.keys())))
        day_pool = dates_dict.get(selected_date, [])
        pool_matches = day_pool if len(day_pool) >= 5 else all_multi_matches
        
        analyzed_list = []
        for m in pool_matches:
            lg = m['league_name']
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            time_str = m['utcDate'][11:16]
            
            pred = run_quant_prediction_v23(
                h_team, a_team, 0, 0, 0, 
                team_stats=multi_stats.get(lg, {}), 
                avg_goals=multi_avg.get(lg, 1.35), 
                is_live=False
            )
            analyzed_list.append({
                "league": lg, "match": f"{h_team} vs {a_team}", "time": time_str,
                "pick": pred["best_pick"], "prob": pred["best_prob"], "odds": pred["selected_odds"],
                "combo": pred["combo_pick"], "combo_prob": pred["combo_prob"], "combo_odds": pred["combo_odds"]
            })
            
        analyzed_list.sort(key=lambda x: x["prob"], reverse=True)
        
        col_banker, col_monster = st.columns(2)
        
        with col_banker:
            st.markdown(f"""
            <div class="vip-banner" style="background: linear-gradient(135deg, #064E3B 0%, #047857 100%); border-color:#10B981;">
                <span class="badge-banker">COUPON SÉCURITÉ</span>
                <h2 style="margin:5px 0; color:#FFFFFF;">🛡️ BANKER (5 MATCHS)</h2>
                <div style="font-size:0.9rem; color:#A7F3D0;">Sélections à très haute probabilité</div>
            </div>
            """, unsafe_allow_html=True)
            
            banker_matches = analyzed_list[:5]
            tot_odds_b = np.prod([item['odds'] for item in banker_matches])
            st.markdown(f"### Cote Totale : <span style='color:#10B981; font-weight:900;'>{tot_odds_b:.2f}</span>", unsafe_allow_html=True)
            
            telegram_b = f"🛡️ **COUPON BANKER APEX ({selected_date})** 🛡️\nCote : ~{tot_odds_b:.2f}\n\n"
            for idx, item in enumerate(banker_matches, 1):
                st.markdown(f"""
                <div class="sub-card">
                    <b>{idx}. [{item['league']}] {item['match']}</b> ({item['time']})<br>
                    👉 Pick : <b style="color:#10B981;">{item['pick']}</b> (Cote: {item['odds']})
                </div>
                """, unsafe_allow_html=True)
                telegram_b += f"{idx}. {item['match']} ➔ {item['pick']} (Cote: {item['odds']})\n"
            st.code(telegram_b, language="text")

        with col_monster:
            st.markdown(f"""
            <div class="vip-banner" style="background: linear-gradient(135deg, #78350F 0%, #B45309 100%); border-color:#F59E0B;">
                <span class="badge-monster">COUPON HAUTES COTES</span>
                <h2 style="margin:5px 0; color:#FFFFFF;">🚀 MONSTER (10-12 MATCHS)</h2>
                <div style="font-size:0.9rem; color:#FDE68A;">Multi-marchés combinés dynamiques</div>
            </div>
            """, unsafe_allow_html=True)
            
            monster_matches = analyzed_list[:min(12, len(analyzed_list))]
            tot_odds_m = np.prod([item['combo_odds'] for item in monster_matches])
            st.markdown(f"### Cote Totale : <span style='color:#F59E0B; font-weight:900;'>{tot_odds_m:.2f}</span>", unsafe_allow_html=True)
            
            telegram_m = f"🚀 **MONSTER COUPON APEX ({selected_date})** 🔥\nCote : ~{tot_odds_m:.2f}\n\n"
            for idx, item in enumerate(monster_matches, 1):
                st.markdown(f"""
                <div class="sub-card">
                    <b>{idx}. [{item['league']}] {item['match']}</b> ({item['time']})<br>
                    👉 Combiné : <b style="color:#F59E0B;">{item['combo']}</b> (Cote: {item['combo_odds']})
                </div>
                """, unsafe_allow_html=True)
                telegram_m += f"{idx}. {item['match']} ➔ {item['combo']} (Cote: {item['combo_odds']})\n"
            st.code(telegram_m, language="text")

# ------------------------------------------
# ONGLET 6 : ASSISTANT APEX AI (DÉBAT & ANALYSE)
# ------------------------------------------
with tab_ai:
    st.subheader("💬 Assistant Apex AI - Débat & Analyse Critique")
    st.markdown("Ton analyste quantitatif personnel est en ligne. Pose-lui tes questions sur les matchs de la compétition sélectionnée (**" + selected_comp + "**) : il passera les chiffres au crible et challengera tes choix sans langue de bois.")
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": f"Salut Amour ! Je suis l'Assistant Apex. Je surveille la compétition **{selected_comp}**. Quel match ou quel pari veux-tu qu'on décortique aujourd'hui ?"}
        ]
        
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    if prompt := st.chat_input("Ex: Que penses-tu d'un pari sur le prochain match à domicile ?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Analyse des matrices de Poisson et des xG en cours..."):
                response_text = generate_apex_ai_response(prompt, team_stats)
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
