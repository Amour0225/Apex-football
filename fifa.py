import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & INTERFACE DESIGN
# ==========================================
st.set_page_config(
    page_title="Apex Quant v18.3 - Live Engine",
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
        border: 1.5px solid #38BDF8; border-radius: 16px; padding: 22px; margin-bottom: 20px;
    }
    .sub-card {
        background-color: #0F172A; border: 1px solid #1E293B;
        border-radius: 12px; padding: 18px; margin-bottom: 15px;
    }
    .badge-live {
        background-color: #EF4444; color: white; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.85rem;
        animation: pulse 2s infinite;
    }
    .badge-upcoming {
        background-color: #3B82F6; color: white; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.85rem;
    }
    .horizontal-scores-container {
        display: flex; flex-direction: row; justify-content: space-between;
        gap: 12px; margin-top: 10px; flex-wrap: nowrap;
    }
    .score-card {
        flex: 1; background: #182238; border-radius: 10px; padding: 12px;
        text-align: center; border: 1px solid #334155; min-width: 0;
    }
    .score-card-top {
        border: 1.5px solid #38BDF8; background: #0F233A;
    }
    .metric-val { font-size: 1.3rem; font-weight: 900; color: #10B981; }
    .metric-lbl { font-size: 0.75rem; color: #94A3B8; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .odds-lbl { font-size: 0.8rem; color: #F59E0B; font-weight: 800; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API FOOTBALL & EXTRACTION
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
            
            stats[name] = {
                "gf_pg": gf / played, "ga_pg": ga / played,
                "home_gf_pg": h_gf / h_played, "home_ga_pg": h_ga / h_played,
                "away_gf_pg": a_gf / a_played, "away_ga_pg": a_ga / a_played,
                "elo": elo_rating,
                "form_factor": form_factor,
                "form_str": form if form else "N/A"
            }
            
            total_played += played
            total_gf += gf
            
        if total_played > 0:
            avg_goals = max(0.9, total_gf / total_played)
            
    return stats, avg_goals

# ==========================================
# 3. MOTEUR QUANTITATIF (AVEC TEMPS REEL)
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

def run_quant_prediction_v18(h_name, a_name, score_h=0, score_a=0, elapsed_min=0, team_stats={}, avg_goals=1.35, is_live=False):
    default_stat = {"gf_pg": 1.35, "ga_pg": 1.25, "home_gf_pg": 1.45, "home_ga_pg": 1.10, 
                    "away_gf_pg": 1.15, "away_ga_pg": 1.35, "elo": 1500, "form_factor": 1.0, "form_str": "N/A"}
    
    h_stat = team_stats.get(h_name, default_stat)
    a_stat = team_stats.get(a_name, default_stat)
    
    raw_h_xg = avg_goals * (h_stat["home_gf_pg"] / avg_goals) * (a_stat["away_ga_pg"] / avg_goals) * 1.12
    raw_a_xg = avg_goals * (a_stat["away_gf_pg"] / avg_goals) * (h_stat["home_ga_pg"] / avg_goals) * 0.90
    
    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_mult_h = np.clip(1.0 + (elo_diff / 1200.0), 0.70, 1.35)
    elo_mult_a = np.clip(1.0 - (elo_diff / 1200.0), 0.70, 1.35)
    
    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * h_stat["form_factor"], 0.5, 3.5))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * a_stat["form_factor"], 0.4, 3.0))

    # AJUSTEMENT EN DIRECT : Calcul du xG restant selon le temps écoulé
    if is_live:
        rem_factor = max(0.05, (90.0 - float(elapsed_min)) / 90.0) if elapsed_min > 0 else 0.50
        rem_h_xg = full_h_xg * rem_factor
        rem_a_xg = full_a_xg * rem_factor
    else:
        rem_h_xg = full_h_xg
        rem_a_xg = full_a_xg

    max_g = 8
    matrix = np.zeros((max_g, max_g))

    # CALCUL DE LA MATRICE PARTANT DU SCORE ACTUEL
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

    # TOP 3 SCORES PROBABLES DE FIN DE MATCH
    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_3_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "home": gh, "away": ga, "prob": round(matrix[gh, ga] * 100, 1)})

    p_h = float(np.sum(np.tril(matrix, -1))) * 100
    p_n = float(np.sum(np.diag(matrix))) * 100
    p_a = float(np.sum(np.triu(matrix, 1))) * 100

    prob_o15 = round((1.0 - (matrix[0,0] + matrix[1,0] + matrix[0,1])) * 100, 1)
    prob_o25 = round((1.0 - np.sum([matrix[i,j] for i in range(3) for j in range(3) if i+j <= 2])) * 100, 1)
    prob_btts = round(float(np.sum(matrix[1:, 1:])) * 100, 1)

    odds_h = prob_to_odds(p_h)
    odds_n = prob_to_odds(p_n)
    odds_a = prob_to_odds(p_a)
    odds_o15 = prob_to_odds(prob_o15)
    odds_o25 = prob_to_odds(prob_o25)
    odds_btts = prob_to_odds(prob_btts)

    if (p_h + p_n) >= 70.0 and p_h >= p_a:
        advice = f"Double Chance : {h_name} ou Nul (1X)"
        conf = round(p_h + p_n, 1)
    elif (p_a + p_n) >= 70.0 and p_a > p_h:
        advice = f"Double Chance : Nul ou {a_name} (X2)"
        conf = round(p_a + p_n, 1)
    elif prob_o15 >= 78.0:
        advice = "Plus de 1.5 Buts au Total"
        conf = prob_o15
    else:
        advice = f"Victoire : {h_name if p_h > p_a else a_name}"
        conf = round(max(p_h, p_a), 1)

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "odds_h": odds_h, "odds_n": odds_n, "odds_a": odds_a,
        "odds_o15": odds_o15, "odds_o25": odds_o25, "odds_btts": odds_btts,
        "xg_h": round(rem_h_xg, 2), "xg_a": round(rem_a_xg, 2),
        "top_3_scores": top_3_scores,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_btts": prob_btts,
        "advice": advice, "conf": conf,
        "h_stat": h_stat, "a_stat": a_stat
    }

# ==========================================
# 4. INTERFACE UTILISATEUR
# ==========================================
st.sidebar.title("Navigation Quant V18.3")
selected_comp = st.sidebar.selectbox("Sélectionner la Compétition", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

team_stats, avg_goals = get_advanced_league_stats(league_code)
raw_matches = fetch_api(f"competitions/{league_code}/matches")

all_matches = raw_matches.get("matches", []) if raw_matches else []

# TRI PAR CATEGORIES
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
    "📈 AUDIT"
])

# ------------------------------------------
# TAB 1 : MATCHS EN DIRECT
# ------------------------------------------
with tab_live:
    st.subheader(f"Matchs en Direct - {selected_comp}")
    if live_matches:
        for m in live_matches:
            h_name = m['homeTeam']['name']
            a_name = m['awayTeam']['name']
            
            # Recupération du score live
            score_obj = m.get('score', {}).get('fullTime', {})
            score_h = score_obj.get('home', 0) if score_obj.get('home') is not None else 0
            score_a = score_obj.get('away', 0) if score_obj.get('away') is not None else 0
            
            # Estimation minute si indisponible
            elapsed = 45 if m.get('status') == 'PAUSED' else 55
            
            res_live = run_quant_prediction_v18(
                h_name, a_name, score_h=score_h, score_a=score_a, 
                elapsed_min=elapsed, team_stats=team_stats, avg_goals=avg_goals, is_live=True
            )
            
            st.markdown(f"""
            <div class="oracle-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="badge-live">EN DIRECT ({elapsed}') — SCORE : {score_h} - {score_a}</span>
                        <h3 style="color:#38BDF8; margin:10px 0 5px 0;">{h_name} vs {a_name}</h3>
                        <p style="color:#CBD5E1; margin:0;">Conseil Live : <b>{res_live['advice']}</b> ({res_live['conf']}%)</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # BANDEAU DE SCORES FINAUX EN DIRECT
            st.markdown(f"""
            <div class="horizontal-scores-container">
                <div class="score-card score-card-top">
                    <div class="metric-lbl" style="color:#38BDF8;">Score Final le + probable</div>
                    <div style="font-size:1.5rem; color:#38BDF8; font-weight:900;">{res_live['top_3_scores'][0]['score']}</div>
                    <div style="color:#10B981; font-size:0.8rem;">{res_live['top_3_scores'][0]['prob']}% proba</div>
                </div>
                <div class="score-card">
                    <div class="metric-lbl">2e Score probable</div>
                    <div style="font-size:1.5rem; color:#F1F5F9; font-weight:900;">{res_live['top_3_scores'][1]['score']}</div>
                    <div style="color:#10B981; font-size:0.8rem;">{res_live['top_3_scores'][1]['prob']}% proba</div>
                </div>
                <div class="score-card">
                    <div class="metric-lbl">Cote Live Victoire H</div>
                    <div class="metric-val">{res_live['p_h']}%</div>
                    <div class="odds-lbl">Cote : {res_live['odds_h']}</div>
                </div>
                <div class="score-card">
                    <div class="metric-lbl">Cote Live Victoire A</div>
                    <div class="metric-val">{res_live['p_a']}%</div>
                    <div class="odds-lbl">Cote : {res_live['odds_a']}</div>
                </div>
            </div>
            <br>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucune rencontre en direct actuellement dans cette compétition.")

# ------------------------------------------
# TAB 2 : CALENDRIER DES MATCHS
# ------------------------------------------
with tab_calendar:
    st.subheader(f"Matchs des 7 Prochains Jours - {selected_comp}")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            date_str = m['utcDate'][:10] + " [" + m['utcDate'][11:16] + "]"
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            
            pred = run_quant_prediction_v18(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False)
            
            cal_data.append({
                "Date & Heure": date_str,
                "Match Réel": f"{h_team} vs {a_team}",
                "Cote 1": pred["odds_h"],
                "Cote N": pred["odds_n"],
                "Cote 2": pred["odds_a"],
                "Cote > 1.5": pred["odds_o15"],
                "Conseil Optimal": f"{pred['advice']} ({pred['conf']}%)"
            })
            
        df_cal = pd.DataFrame(cal_data)
        st.dataframe(df_cal, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune rencontre programmée dans les 7 prochains jours.")

# ------------------------------------------
# TAB 3 : ANALYSE DETAILLEE (AVEC OPTION SIMULATEUR EN DIRECT)
# ------------------------------------------
with tab_detail:
    st.subheader("Analyse & Simulation de Match")
    
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
        
        # PARAMETRES EN DIRECT OU SIMULATION
        st.markdown("**Simulateur d'évolution de score (Test en Direct)**")
        sc_col1, sc_col2, sc_col3 = st.columns(3)
        with sc_col1: sim_h = st.number_input(f"Score {h_name}", min_value=0, value=0)
        with sc_col2: sim_a = st.number_input(f"Score {a_name}", min_value=0, value=0)
        with sc_col3: sim_min = st.slider("Minute du match", 0, 90, 0)
        
        is_sim_live = sim_min > 0 or sim_h > 0 or sim_a > 0
        
        res = run_quant_prediction_v18(h_name, a_name, sim_h, sim_a, sim_min, team_stats, avg_goals, is_live=is_sim_live)
        
        st.markdown(f"""
        <div class="oracle-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="badge-upcoming">PRONOSTIC MATRICIEL ET COTES</span>
                    <h2 style="color:#38BDF8; margin:10px 0 5px 0; font-weight:900;">PRONOSTIC : {res['advice']}</h2>
                    <p style="color:#CBD5E1; margin:0;">xG Restant : {h_name} ({res['xg_h']}) | {a_name} ({res['xg_a']})</p>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:2.8rem; font-weight:900; color:#10B981; line-height:1;">{res['conf']}%</div>
                    <span style="color:#64748B; font-size:0.8rem; font-weight:700;">CONFIANCE APEX</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # TOP 3 SCORES EXACTS (HORIZONTALE)
        st.markdown('<div class="sub-card">', unsafe_allow_html=True)
        st.markdown("### Top 3 Scores Exacts les plus Probables à la Fin")
        
        top1, top2, top3 = res["top_3_scores"][0], res["top_3_scores"][1], res["top_3_scores"][2]
        
        st.markdown(f"""
        <div class="horizontal-scores-container">
            <div class="score-card score-card-top">
                <div class="metric-lbl" style="color:#38BDF8;">1er Plus Probable</div>
                <div style="font-size:1.6rem; color:#38BDF8; font-weight:900; margin:4px 0;">{top1['score']}</div>
                <div style="color:#10B981; font-size:0.85rem; font-weight:800;">{top1['prob']}%</div>
            </div>
            <div class="score-card">
                <div class="metric-lbl">2e Alternatif</div>
                <div style="font-size:1.6rem; color:#F1F5F9; font-weight:900; margin:4px 0;">{top2['score']}</div>
                <div style="color:#10B981; font-size:0.85rem; font-weight:800;">{top2['prob']}%</div>
            </div>
            <div class="score-card">
                <div class="metric-lbl">3e Alternatif</div>
                <div style="font-size:1.6rem; color:#F1F5F9; font-weight:900; margin:4px 0;">{top3['score']}</div>
                <div style="color:#10B981; font-size:0.85rem; font-weight:800;">{top3['prob']}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # 1N2 & COTES (HORIZONTALE)
        st.markdown('<div class="sub-card">', unsafe_allow_html=True)
        st.markdown("### Probabilités & Cotes Équitables 1N2")
        st.markdown(f"""
        <div class="horizontal-scores-container">
            <div class="score-card">
                <div class="metric-lbl">Victoire {h_name}</div>
                <div class="metric-val">{res["p_h"]}%</div>
                <div class="odds-lbl">Cote : {res["odds_h"]}</div>
            </div>
            <div class="score-card">
                <div class="metric-lbl">Match Nul</div>
                <div class="metric-val">{res["p_n"]}%</div>
                <div class="odds-lbl">Cote : {res["odds_n"]}</div>
            </div>
            <div class="score-card">
                <div class="metric-lbl">Victoire {a_name}</div>
                <div class="metric-val">{res["p_a"]}%</div>
                <div class="odds-lbl">Cote : {res["odds_a"]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# TAB 4 : AUDIT
# ------------------------------------------
with tab_audit:
    st.subheader(f"Audit des Matchs Terminés - {selected_comp}")
    if finished_matches:
        audit_list = []
        for m in finished_matches[-10:]:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            real_h_g = m['score']['fullTime']['home']
            real_a_g = m['score']['fullTime']['away']
            if real_h_g is not None and real_a_g is not None:
                pred = run_quant_prediction_v18(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False)
                audit_list.append({
                    "Date": m['utcDate'][:10],
                    "Match": f"{h_team} vs {a_team}",
                    "Score Réel": f"{real_h_g} - {real_a_g}",
                    "Conseil V18": pred["advice"]
                })
        st.dataframe(pd.DataFrame(audit_list), use_container_width=True, hide_index=True)
