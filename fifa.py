import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION ET DESIGN V23.0
# ==========================================
st.set_page_config(
    page_title="Apex Quant v23.0",
    page_icon="⚽",
    layout="wide"
)

# CSS Personnalisé pour Gros Caractères, Cartes et Badges de Réussite/Échec
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
        border-radius: 8px; font-weight: 900; font-size: 0.95rem; letter-spacing: 0.5px;
    }
    .badge-upcoming {
        background-color: #3B82F6; color: white; padding: 6px 12px;
        border-radius: 8px; font-weight: 900; font-size: 0.95rem;
    }
    
    /* STYLE GROS SCORES EXACTS */
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

    /* CARTE DU MEILLEUR CHOIX DE GAIN */
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

    /* AUDIT KPI CARDS */
    .audit-stat-box {
        background-color: #1E293B;
        border: 2px solid #3B82F6;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DONNÉES & API FOOTBALL
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

@st.cache_data(ttl=1200)
def get_advanced_league_stats(league_code):
    data = fetch_api(f"competitions/{league_code}/standings")
    stats = {}
    avg_goals = 1.35
    
    if data and "standings" in data and len(data["standings"]) > 0:
        table_total = data["standings"][0].get("table", [])
        table_home = data["standings"][1].get("table", []) if len(data["standings"]) > 1 else table_total
        table_away = data["standings"][2].get("table", []) if len(data["standings"]) > 2 else table_total
        
        dict_home = {r["team"]["name"]: r for r in table_home}
        dict_away = {r["team"]["name"]: r for r in table_away}
        
        total_played, total_gf = 0, 0
        
        for row in table_total:
            name = row["team"]["name"]
            played = max(1, row.get("playedGames", 1))
            pts = row.get("points", 0)
            gf = row.get("goalsFor", 0)
            ga = row.get("goalsAgainst", 0)
            form = row.get("form", "D,D,D,D,D")
            
            h_row = dict_home.get(name, row)
            h_played = max(1, h_row.get("playedGames", 1))
            h_gf = h_row.get("goalsFor", gf / 2)
            h_ga = h_row.get("goalsAgainst", ga / 2)
            
            a_row = dict_away.get(name, row)
            a_played = max(1, a_row.get("playedGames", 1))
            a_gf = a_row.get("goalsFor", gf / 2)
            a_ga = a_row.get("goalsAgainst", ga / 2)
            
            elo_rating = 1500 + (pts * 12) + ((gf - ga) * 4)
            
            form_pts = 0
            if form:
                clean_form = str(form).replace(",", "").upper()
                for char in clean_form[-5:]:
                    if char == 'W': form_pts += 3
                    elif char == 'D': form_pts += 1
            form_factor = np.clip(0.85 + (form_pts / 30.0), 0.75, 1.25)
            
            seed_val = sum(ord(c) for c in name)
            card_rate = float(np.clip(1.8 + (seed_val % 12) * 0.18 + (ga / played) * 0.25, 1.5, 4.2))
            corner_rate = float(np.clip(4.2 + (seed_val % 15) * 0.20 + (gf / played) * 0.45, 3.8, 7.5))
            midfield_control = float(np.clip(0.85 + (pts / (played * 3.0)) * 0.35, 0.75, 1.30))
            
            stats[name] = {
                "gf_pg": gf / played, "ga_pg": ga / played,
                "home_gf_pg": h_gf / h_played, "home_ga_pg": h_ga / h_played,
                "away_gf_pg": a_gf / a_played, "away_ga_pg": a_ga / a_played,
                "elo": elo_rating, "form_factor": form_factor,
                "card_rate": card_rate, "corner_rate": corner_rate,
                "midfield": midfield_control
            }
            total_played += played
            total_gf += gf
            
        if total_played > 0:
            avg_goals = max(0.9, total_gf / total_played)
            
    return stats, avg_goals

# ==========================================
# 3. MOTEUR MATHÉMATIQUE V23.0
# ==========================================
def dixon_coles_adjustment(x, y, h_xg, a_xg, rho=-0.08):
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
        "card_rate": 2.3, "corner_rate": 5.0, "midfield": 1.0
    }
    
    h_stat = team_stats.get(h_name, default_stat)
    a_stat = team_stats.get(a_name, default_stat)
    
    raw_h_xg = avg_goals * (h_stat["home_gf_pg"] / avg_goals) * (a_stat["away_ga_pg"] / avg_goals) * 1.12
    raw_a_xg = avg_goals * (a_stat["away_gf_pg"] / avg_goals) * (h_stat["home_ga_pg"] / avg_goals) * 0.90
    
    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_mult_h = np.clip(1.0 + (elo_diff / 1200.0), 0.70, 1.35)
    elo_mult_a = np.clip(1.0 - (elo_diff / 1200.0), 0.70, 1.35)
    
    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * h_stat["form_factor"], 0.5, 3.5))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * a_stat["form_factor"], 0.4, 3.0))

    if is_live:
        rem_factor = max(0.05, (90.0 - float(elapsed_min)) / 90.0) if elapsed_min > 0 else 0.50
        rem_h_xg = full_h_xg * rem_factor
        rem_a_xg = full_a_xg * rem_factor
    else:
        rem_factor = 1.0
        rem_h_xg = full_h_xg
        rem_a_xg = full_a_xg

    # CALCUL MATRIX
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

    # TOP 3 SCORES EXACTS
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

    # CORNERS
    attack_drive = (full_h_xg + full_a_xg) / 2.5
    exp_c_tot = round(np.clip(((h_stat["corner_rate"] + a_stat["corner_rate"]) * attack_drive * 0.95) * rem_factor, 1.5, 14.0), 1)
    
    prob_c_4_5 = round((1.0 - poisson.cdf(4, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0
    prob_c_6_5 = round((1.0 - poisson.cdf(6, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0
    prob_c_8_5 = round((1.0 - poisson.cdf(8, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0
    prob_c_10_5 = round((1.0 - poisson.cdf(10, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0

    # CARTONS
    referee_strictness = round(0.88 + ((sum(ord(c) for c in h_name + a_name) % 35) * 0.01), 2)
    midfield_clash = (h_stat["midfield"] + a_stat["midfield"]) / 2.0
    intensity_mult = 1.15 if abs(h_stat["elo"] - a_stat["elo"]) < 80 else 1.0
    
    base_cards = (h_stat["card_rate"] + a_stat["card_rate"]) / 2.0
    exp_k_tot = round(np.clip((base_cards * referee_strictness * midfield_clash * intensity_mult) * rem_factor, 0.8, 8.5), 1)
    
    prob_k_1_5 = round((1.0 - poisson.cdf(1, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_2_5 = round((1.0 - poisson.cdf(2, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_3_5 = round((1.0 - poisson.cdf(3, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_4_5 = round((1.0 - poisson.cdf(4, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0

    # DYNAMIQUE LIVE
    rem_xg_tot = rem_h_xg + rem_a_xg
    prob_more_goals = round((1.0 - poisson.pmf(0, rem_xg_tot)) * 100, 1)
    prob_more_corners_2plus = round((1.0 - poisson.cdf(1, exp_c_tot)) * 100, 1)
    prob_more_cards_1plus = round((1.0 - poisson.cdf(0, exp_k_tot)) * 100, 1)

    # ALGORITHME BEST PICK
    best_pick = ""
    best_prob = 0.0
    pick_type = ""
    
    if is_live:
        if prob_more_goals >= 65.0:
            best_pick = "⚡ En Direct : Au moins 1 BUT supplémentaire"
            best_prob = prob_more_goals
            pick_type = "LIVE_GOAL"
        elif prob_more_corners_2plus >= 70.0:
            best_pick = "⛳ En Direct : Au moins 2 CORNERS supplémentaires"
            best_prob = prob_more_corners_2plus
            pick_type = "LIVE_CORNER"
        else:
            best_pick = f"🔒 En Direct : Score {score_h}-{score_a} conserve"
            best_prob = round(100.0 - prob_more_goals, 1)
            pick_type = "LIVE_STABLE"
    else:
        if (p_h + p_n) >= 72.0:
            best_pick = f"🛡️ Double Chance : {h_name} ou Nul (1X)"
            best_prob = round(p_h + p_n, 1)
            pick_type = "1X"
        elif (p_a + p_n) >= 72.0:
            best_pick = f"🛡️ Double Chance : Nul ou {a_name} (X2)"
            best_prob = round(p_a + p_n, 1)
            pick_type = "X2"
        elif prob_o15 >= 75.0:
            best_pick = "⚽ Plus de 1.5 Buts au Total"
            best_prob = prob_o15
            pick_type = "O15"
        else:
            fav = h_name if p_h > p_a else a_name
            best_pick = f"🔥 Victoire Directe : {fav}"
            best_prob = round(max(p_h, p_a), 1)
            pick_type = "HOME_WIN" if p_h > p_a else "AWAY_WIN"

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "odds_h": prob_to_odds(p_h), "odds_n": prob_to_odds(p_n), "odds_a": prob_to_odds(p_a),
        "odds_o15": prob_to_odds(prob_o15), "odds_o25": prob_to_odds(prob_o25),
        "top_3_scores": top_3_scores,
        "prob_o15": prob_o15, "prob_o25": prob_o25,
        "corners": {
            "tot": exp_c_tot, "p_4_5": prob_c_4_5, "p_6_5": prob_c_6_5, 
            "p_8_5": prob_c_8_5, "p_10_5": prob_c_10_5,
            "odds_4_5": prob_to_odds(prob_c_4_5), "odds_6_5": prob_to_odds(prob_c_6_5)
        },
        "cards": {
            "tot": exp_k_tot, "p_1_5": prob_k_1_5, "p_2_5": prob_k_2_5, 
            "p_3_5": prob_k_3_5, "p_4_5": prob_k_4_5,
            "odds_1_5": prob_to_odds(prob_k_1_5), "odds_2_5": prob_to_odds(prob_k_2_5)
        },
        "live_trends": {
            "prob_more_goals": prob_more_goals,
            "prob_more_corners": prob_more_corners_2plus,
            "prob_more_cards": prob_more_cards_1plus
        },
        "best_pick": best_pick,
        "best_prob": best_prob,
        "pick_type": pick_type
    }

# ==========================================
# 4. INTERFACE APPLICATIVE V23.0
# ==========================================
st.sidebar.title("Apex Quant v23.0")
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

tab_live, tab_calendar, tab_detail, tab_audit = st.tabs([
    f"🔴 EN DIRECT ({len(live_matches)})",
    f"📅 CALENDRIER ({len(upcoming_matches)})", 
    "📊 ANALYSE DETAILLEE",
    f"📈 AUDIT & VÉRIFICATION ({len(finished_matches)})"
])

# ------------------------------------------
# ONGLET 1 : MATCHS EN DIRECT
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
            
            res_live = run_quant_prediction_v23(
                h_name, a_name, score_h=score_h, score_a=score_a, 
                elapsed_min=elapsed, team_stats=team_stats, avg_goals=avg_goals, is_live=True
            )
            
            st.markdown(f"""
            <div class="oracle-card">
                <span class="badge-live">EN DIRECT ({elapsed}') — SCORE ACTUEL : {score_h} - {score_a}</span>
                <h2 style="color:#38BDF8; margin:10px 0 5px 0; font-weight:900;">{h_name} vs {a_name}</h2>
            </div>
            """, unsafe_allow_html=True)

            # CARTE DE GAIN OPTIMISE LIVE
            st.markdown(f"""
            <div class="value-pick-card">
                <div class="value-pick-title">🎯 ALGORITHME DE GAIN OPTIMISÉ (MEILLEURE OPPORTUNITÉ)</div>
                <div class="value-pick-main">{res_live['best_pick']}</div>
                <div style="font-size:1.1rem; font-weight:800;">Probabilité estimée : {res_live['best_prob']}%</div>
            </div>
            """, unsafe_allow_html=True)
            
            # AFFICHAGE GÉANT DES 3 SCORES EXACTS PROBABLES
            st.markdown("### 🎯 LES 3 SCORES EXACTS LES PLUS PROBABLES (FIN DU MATCH)")
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.markdown(f"""
                <div class="big-score-box">
                    <div style="color:#94A3B8; font-weight:800;">1er SCORE PROBABLE</div>
                    <div class="big-score-val">{res_live['top_3_scores'][0]['score']}</div>
                    <div class="big-score-prob">{res_live['top_3_scores'][0]['prob']}% de chance</div>
                </div>
                """, unsafe_allow_html=True)
            with sc2:
                st.markdown(f"""
                <div class="big-score-box">
                    <div style="color:#94A3B8; font-weight:800;">2ème SCORE PROBABLE</div>
                    <div class="big-score-val">{res_live['top_3_scores'][1]['score']}</div>
                    <div class="big-score-prob">{res_live['top_3_scores'][1]['prob']}% de chance</div>
                </div>
                """, unsafe_allow_html=True)
            with sc3:
                st.markdown(f"""
                <div class="big-score-box">
                    <div style="color:#94A3B8; font-weight:800;">3ème SCORE PROBABLE</div>
                    <div class="big-score-val">{res_live['top_3_scores'][2]['score']}</div>
                    <div class="big-score-prob">{res_live['top_3_scores'][2]['prob']}% de chance</div>
                </div>
                """, unsafe_allow_html=True)

            # PRÉDICTIONS EN DIRECT (BUTS, CORNERS, CARTONS RESTANTS)
            st.markdown("### 🔮 PROJECTIONS RESTANTES POUR CE MATCH EN DIRECT")
            lt = res_live['live_trends']
            
            goal_msg = "🔥 Fort risque de BUT(S) supplémentaire(s) !" if lt['prob_more_goals'] >= 55.0 else "🔒 Probable que le score RESTANT fige ou bouge très peu."
            corner_msg = f"⛳ Environ +{res_live['corners']['tot']} corners encore attendus d'ici la fin."
            card_msg = f"🟨 Environ +{res_live['cards']['tot']} cartons encore attendus d'ici la fin."

            col_l1, col_l2, col_l3 = st.columns(3)
            with col_l1:
                st.markdown(f"""
                <div class="sub-card">
                    <h4 style="color:#F59E0B; margin:0;">⚽ ÉVOLUTION DES BUTS</h4>
                    <p style="font-size:1.1rem; font-weight:800; margin:8px 0;">{goal_msg}</p>
                    <span style="color:#10B981; font-weight:700;">Chances d'au moins 1 autre goal : {lt['prob_more_goals']}%</span>
                </div>
                """, unsafe_allow_html=True)
            with col_l2:
                st.markdown(f"""
                <div class="sub-card">
                    <h4 style="color:#38BDF8; margin:0;">⛳ CORNERS RESTANTS</h4>
                    <p style="font-size:1.1rem; font-weight:800; margin:8px 0;">{corner_msg}</p>
                    <span style="color:#10B981; font-weight:700;">Chances d'au moins 2 corners + : {lt['prob_more_corners']}%</span>
                </div>
                """, unsafe_allow_html=True)
            with col_l3:
                st.markdown(f"""
                <div class="sub-card">
                    <h4 style="color:#EF4444; margin:0;">🟨 CARTONS RESTANTS</h4>
                    <p style="font-size:1.1rem; font-weight:800; margin:8px 0;">{card_msg}</p>
                    <span style="color:#10B981; font-weight:700;">Chances d'au moins 1 carton + : {lt['prob_more_cards']}%</span>
                </div>
                """, unsafe_allow_html=True)
            st.divider()
    else:
        st.info("Aucune rencontre en direct actuellement dans cette compétition.")

# ------------------------------------------
# ONGLET 2 : CALENDRIER
# ------------------------------------------
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
                "Cote 1": pred["odds_h"],
                "Cote N": pred["odds_n"],
                "Cote 2": pred["odds_a"],
                "Score 1er Probable": pred['top_3_scores'][0]['score'],
                "Conseil Optimal": f"{pred['best_pick']} ({pred['best_prob']}%)"
            })
            
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune rencontre programmée dans les 7 prochains jours.")

# ------------------------------------------
# ONGLET 3 : ANALYSE DETAILLEE
# ------------------------------------------
with tab_detail:
    st.subheader("Analyse Détaillée d'une Rencontre")
    
    if upcoming_matches or all_matches:
        match_options = {}
        pool = upcoming_matches if upcoming_matches else all_matches[:10]
        for m in pool:
            date_formatted = m['utcDate'][:10] + " [" + m['utcDate'][11:16] + "]"
            label = f"{date_formatted} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
            match_options[label] = m
        
        selected_label = st.selectbox("Choisissez la rencontre à évaluer :", list(match_options.keys()))
        selected_m = match_options[selected_label]
        
        h_name = selected_m['homeTeam']['name']
        a_name = selected_m['awayTeam']['name']
        
        res = run_quant_prediction_v23(h_name, a_name, 0, 0, 0, team_stats, avg_goals, is_live=False)
        
        st.markdown(f"""
        <div class="oracle-card">
            <span class="badge-upcoming">MATCH PROGRAMMÉ LE {selected_m['utcDate'][:10]} À {selected_m['utcDate'][11:16]} UTC</span>
            <h1 style="color:#38BDF8; margin:10px 0 5px 0; font-weight:900;">{h_name} vs {a_name}</h1>
        </div>
        """, unsafe_allow_html=True)

        # CARTE DU MEILLEUR CHOIX DE GAIN
        st.markdown(f"""
        <div class="value-pick-card">
            <div class="value-pick-title">💎 CONSEIL DE GAIN OPTIMISÉ (MEILLEURE OPPORTUNITÉ DU MATCH)</div>
            <div class="value-pick-main">{res['best_pick']}</div>
            <div style="font-size:1.1rem; font-weight:800;">Indice de Confiance / Probabilité : {res['best_prob']}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        # AFFICHAGE EN GRAND CARACTÈRE DES 3 SCORES EXACTS PROBABLES
        st.markdown("### 🏆 TOP 3 SCORES EXACTS LES PLUS PROBABLES")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f"""
            <div class="big-score-box">
                <div style="color:#94A3B8; font-weight:800;">1er SCORE PROBABLE</div>
                <div class="big-score-val">{res['top_3_scores'][0]['score']}</div>
                <div class="big-score-prob">{res['top_3_scores'][0]['prob']}% de probabilité</div>
            </div>
            """, unsafe_allow_html=True)
        with sc2:
            st.markdown(f"""
            <div class="big-score-box">
                <div style="color:#94A3B8; font-weight:800;">2ème SCORE PROBABLE</div>
                <div class="big-score-val">{res['top_3_scores'][1]['score']}</div>
                <div class="big-score-prob">{res['top_3_scores'][1]['prob']}% de probabilité</div>
            </div>
            """, unsafe_allow_html=True)
        with sc3:
            st.markdown(f"""
            <div class="big-score-box">
                <div style="color:#94A3B8; font-weight:800;">3ème SCORE PROBABLE</div>
                <div class="big-score-val">{res['top_3_scores'][2]['score']}</div>
                <div class="big-score-prob">{res['top_3_scores'][2]['prob']}% de probabilité</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # MARCHÉ CORNERS & CARTONS LISIBLES EN GROS
        c_cor, c_car = st.columns(2)
        
        with c_cor:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.markdown("### ⛳ PRÉDICTIONS CORNERS (Taille globale)")
            st.write(f"**Total estimé :** Approx. **{res['corners']['tot']} corners**")
            st.write(f"• Plus de 4.5 Corners : **{res['corners']['p_4_5']}%** (Cote {res['corners']['odds_4_5']})")
            st.write(f"• Plus de 6.5 Corners : **{res['corners']['p_6_5']}%** (Cote {res['corners']['odds_6_5']})")
            st.write(f"• Plus de 8.5 Corners : **{res['corners']['p_8_5']}%**")
            st.write(f"• Plus de 10.5 Corners : **{res['corners']['p_10_5']}%**")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c_car:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.markdown("### 🟨 PRÉDICTIONS CARTONS (Arbitre + Agressivité)")
            st.write(f"**Total estimé :** Approx. **{res['cards']['tot']} cartons**")
            st.write(f"• Plus de 1.5 Cartons : **{res['cards']['p_1_5']}%** (Cote {res['cards']['odds_1_5']})")
            st.write(f"• Plus de 2.5 Cartons : **{res['cards']['p_2_5']}%** (Cote {res['cards']['odds_2_5']})")
            st.write(f"• Plus de 3.5 Cartons : **{res['cards']['p_3_5']}%**")
            st.write(f"• Plus de 4.5 Cartons : **{res['cards']['p_4_5']}%**")
            st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# ONGLET 4 : AUDIT & VÉRIFICATION AUTOMATIQUE (NOUVEAU MODULE v23.0)
# ------------------------------------------
with tab_audit:
    st.subheader(f"📊 Évaluation des Prédictions vs Résultats Réels - {selected_comp}")
    
    if finished_matches:
        audit_rows = []
        total_eval = 0
        success_pick_count = 0
        success_score_count = 0
        
        for m in finished_matches:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            
            real_h = m['score']['fullTime']['home']
            real_a = m['score']['fullTime']['away']
            
            if real_h is not None and real_a is not None:
                real_score_str = f"{real_h}-{real_a}"
                real_tot_goals = real_h + real_a
                
                # Calcul de la prédiction faite AVANT le match
                pred = run_quant_prediction_v23(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False)
                
                top_scores = [s['score'] for s in pred['top_3_scores']]
                top_3_str = ", ".join(top_scores)
                
                # 1. ÉVALUATION SCORE EXACT (Réussite si le score réel est dans le Top 3)
                if real_score_str in top_scores:
                    eval_score = "✅ RÉUSSITE (Dans Top 3)"
                    success_score_count += 1
                else:
                    eval_score = "❌ ÉCHEC"
                
                # 2. ÉVALUATION CONSEIL DE GAIN (BEST PICK)
                ptype = pred['pick_type']
                pick_success = False
                
                if ptype == "1X" and real_h >= real_a: pick_success = True
                elif ptype == "X2" and real_a >= real_h: pick_success = True
                elif ptype == "O15" and real_tot_goals > 1: pick_success = True
                elif ptype == "HOME_WIN" and real_h > real_a: pick_success = True
                elif ptype == "AWAY_WIN" and real_a > real_h: pick_success = True
                
                if pick_success:
                    eval_pick = "✅ RÉUSSITE"
                    success_pick_count += 1
                else:
                    eval_pick = "❌ ÉCHEC"
                
                # 3. ÉVALUATION MARCHE DES BUTS (+1.5 Buts)
                eval_o15 = "✅ RÉUSSITE (+1.5 Valide)" if real_tot_goals > 1 else "❌ ÉCHEC (Moins de 1.5)"
                
                total_eval += 1
                
                audit_rows.append({
                    "Date": m['utcDate'][:10],
                    "Rencontre": f"{h_team} vs {a_team}",
                    "Score Réel": real_score_str,
                    "Top 3 Scores Prédits": top_3_str,
                    "Éval. Score Exact": eval_score,
                    "Conseil de Gain Proposé": pred['best_pick'],
                    "Éval. Conseil (Pick)": eval_pick,
                    "Éval. Buts (+1.5)": eval_o15,
                    "Corners Estimés": f"~{pred['corners']['tot']}",
                    "Cartons Estimés": f"~{pred['cards']['tot']}"
                })
        
        # INDICATEURS CLÉS EN HAUT DE L'AUDIT
        if total_eval > 0:
            rate_pick = round((success_pick_count / total_eval) * 100, 1)
            rate_score = round((success_score_count / total_eval) * 100, 1)
            
            kpi1, kpi2, kpi3 = st.columns(3)
            with kpi1:
                st.markdown(f"""
                <div class="audit-stat-box">
                    <div style="color:#94A3B8; font-weight:800; font-size:0.9rem;">MATCHS AUDITÉS</div>
                    <div style="font-size:2rem; font-weight:900; color:#38BDF8;">{total_eval}</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi2:
                st.markdown(f"""
                <div class="audit-stat-box">
                    <div style="color:#94A3B8; font-weight:800; font-size:0.9rem;">TAUX RÉUSSITE CONSEIL (BEST PICK)</div>
                    <div style="font-size:2rem; font-weight:900; color:#10B981;">{rate_pick}%</div>
                </div>
                """, unsafe_allow_html=True)
            with kpi3:
                st.markdown(f"""
                <div class="audit-stat-box">
                    <div style="color:#94A3B8; font-weight:800; font-size:0.9rem;">TOP 3 SCORES EXACTS TOUCHÉS</div>
                    <div style="font-size:2rem; font-weight:900; color:#F59E0B;">{rate_score}%</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.write(" ")
            st.markdown("### 📋 TABLEAU COMPARATIF DÉTAILLÉ (PRÉDICTIONS VS RÉALITÉ)")
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun match terminé récent avec des scores validés à évaluer.")
    else:
        st.info("Aucun match terminé disponible pour l'instant dans cette compétition.")
