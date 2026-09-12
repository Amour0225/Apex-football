import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION ET DESIGN
# ==========================================
st.set_page_config(
    page_title="Apex Quant v20.0",
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
        border: 1.5px solid #38BDF8; border-radius: 14px; padding: 20px; margin-bottom: 20px;
    }
    .sub-card {
        background-color: #0F172A; border: 1px solid #1E293B;
        border-radius: 12px; padding: 16px; margin-bottom: 15px;
    }
    .badge-live {
        background-color: #EF4444; color: white; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.85rem;
    }
    .badge-upcoming {
        background-color: #3B82F6; color: white; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.85rem;
    }
    .text-summary {
        background-color: #1E293B; border-left: 4px solid #38BDF8;
        padding: 10px 14px; border-radius: 4px; font-size: 0.95rem; font-weight: 600;
        color: #F1F5F9; margin-bottom: 12px;
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
            
            stats[name] = {
                "gf_pg": gf / played, "ga_pg": ga / played,
                "home_gf_pg": h_gf / h_played, "home_ga_pg": h_ga / h_played,
                "away_gf_pg": a_gf / a_played, "away_ga_pg": a_ga / a_played,
                "elo": elo_rating, "form_factor": form_factor
            }
            total_played += played
            total_gf += gf
            
        if total_played > 0:
            avg_goals = max(0.9, total_gf / total_played)
            
    return stats, avg_goals

# ==========================================
# 3. MOTEUR MATHÉMATIQUE (CORNERS ET CARTONS AJUSTÉS)
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

def run_quant_prediction_v20(h_name, a_name, score_h=0, score_a=0, elapsed_min=0, team_stats={}, avg_goals=1.35, is_live=False):
    default_stat = {"gf_pg": 1.35, "ga_pg": 1.25, "home_gf_pg": 1.45, "home_ga_pg": 1.10, 
                    "away_gf_pg": 1.15, "away_ga_pg": 1.35, "elo": 1500, "form_factor": 1.0}
    
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

    # MODELISATION SCORES & PROBABILITES
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
    prob_btts = round(float(np.sum(matrix[1:, 1:])) * 100, 1)

    # MODELISATION CORNERS (A PARTIR DE 4.5 EN ALLANT)
    exp_c_tot = round((9.2 + (rem_h_xg + rem_a_xg) * 0.8) * rem_factor, 1)
    prob_c_4_5 = round((1.0 - poisson.cdf(4, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0
    prob_c_6_5 = round((1.0 - poisson.cdf(6, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0
    prob_c_8_5 = round((1.0 - poisson.cdf(8, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0
    prob_c_10_5 = round((1.0 - poisson.cdf(10, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0

    likely_c = max(5, int(round(exp_c_tot)))
    corner_summary = f"Sur ce match, il est très probable qu'il y ait au moins jusqu'à {likely_c - 1} à {likely_c + 1} corners."

    # MODELISATION DISCIPLINAIRE (CARTONS : A PARTIR DE 1.5 / 2 EN ALLANT)
    exp_k_tot = round(np.clip((3.8 + abs(rem_h_xg - rem_a_xg) * 0.4 + (rem_h_xg + rem_a_xg) * 0.35) * rem_factor, 1.0, 9.0), 1)
    
    prob_k_1_5 = round((1.0 - poisson.cdf(1, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_2_5 = round((1.0 - poisson.cdf(2, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_3_5 = round((1.0 - poisson.cdf(3, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_4_5 = round((1.0 - poisson.cdf(4, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_5_5 = round((1.0 - poisson.cdf(5, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0

    likely_k = max(2, int(round(exp_k_tot)))
    card_summary = f"Sur ce match, il est probable qu'il y ait au moins jusqu'à {likely_k} ou {likely_k + 1} cartons."

    # CONSEIL ET CONFIANCE
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
        "odds_h": prob_to_odds(p_h), "odds_n": prob_to_odds(p_n), "odds_a": prob_to_odds(p_a),
        "odds_o15": prob_to_odds(prob_o15), "odds_o25": prob_to_odds(prob_o25), "odds_btts": prob_to_odds(prob_btts),
        "xg_h": round(rem_h_xg, 2), "xg_a": round(rem_a_xg, 2),
        "top_3_scores": top_3_scores,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_btts": prob_btts,
        "corners": {
            "tot": exp_c_tot, "summary": corner_summary,
            "p_4_5": prob_c_4_5, "odds_4_5": prob_to_odds(prob_c_4_5),
            "p_6_5": prob_c_6_5, "odds_6_5": prob_to_odds(prob_c_6_5),
            "p_8_5": prob_c_8_5, "odds_8_5": prob_to_odds(prob_c_8_5),
            "p_10_5": prob_c_10_5, "odds_10_5": prob_to_odds(prob_c_10_5)
        },
        "cards": {
            "tot": exp_k_tot, "summary": card_summary,
            "p_1_5": prob_k_1_5, "odds_1_5": prob_to_odds(prob_k_1_5),
            "p_2_5": prob_k_2_5, "odds_2_5": prob_to_odds(prob_k_2_5),
            "p_3_5": prob_k_3_5, "odds_3_5": prob_to_odds(prob_k_3_5),
            "p_4_5": prob_k_4_5, "odds_4_5": prob_to_odds(prob_k_4_5),
            "p_5_5": prob_k_5_5, "odds_5_5": prob_to_odds(prob_k_5_5)
        },
        "advice": advice, "conf": conf
    }

# ==========================================
# 4. INTERFACE APPLICATIVE
# ==========================================
st.sidebar.title("Apex Quant v20.0")
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
    "📈 AUDIT"
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
            
            res_live = run_quant_prediction_v20(
                h_name, a_name, score_h=score_h, score_a=score_a, 
                elapsed_min=elapsed, team_stats=team_stats, avg_goals=avg_goals, is_live=True
            )
            
            st.markdown(f"""
            <div class="oracle-card">
                <span class="badge-live">EN DIRECT ({elapsed}') — SCORE : {score_h} - {score_a}</span>
                <h3 style="color:#38BDF8; margin:8px 0 4px 0;">{h_name} vs {a_name}</h3>
                <p style="color:#10B981; font-size:1.1rem; font-weight:800; margin:0;">Pronostic Live : {res_live['advice']} ({res_live['conf']}%)</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("**Projections Live Restantes (Fin de match) :**")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Score Final Estimé", res_live['top_3_scores'][0]['score'], f"{res_live['top_3_scores'][0]['prob']}% proba")
            with c2:
                st.metric("Cote Live Victoire H", res_live['odds_h'], f"{res_live['p_h']}%")
            with c3:
                st.metric("Corners Restants", f"~{res_live['corners']['tot']}", f">4.5 : {res_live['corners']['p_4_5']}%")
            with c4:
                st.metric("Cartons Restants", f"~{res_live['cards']['tot']}", f">1.5 : {res_live['cards']['p_1_5']}%")
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
            
            pred = run_quant_prediction_v20(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False)
            
            cal_data.append({
                "Date & Heure": date_str,
                "Match Réel": f"{h_team} vs {a_team}",
                "Cote 1": pred["odds_h"],
                "Cote N": pred["odds_n"],
                "Cote 2": pred["odds_a"],
                "Cote > 1.5": pred["odds_o15"],
                "Conseil Optimal": f"{pred['advice']} ({pred['conf']}%)"
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
        
        res = run_quant_prediction_v20(h_name, a_name, 0, 0, 0, team_stats, avg_goals, is_live=False)
        
        st.markdown(f"""
        <div class="oracle-card">
            <span class="badge-upcoming">PROGRAMMÉ LE {selected_m['utcDate'][:10]} À {selected_m['utcDate'][11:16]} UTC</span>
            <h2 style="color:#38BDF8; margin:10px 0 5px 0; font-weight:900;">PRONOSTIC : {res['advice']}</h2>
            <p style="color:#CBD5E1; margin:0;">Indice de Confiance : <b style="color:#10B981; font-size:1.2rem;">{res['conf']}%</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        # SCORES & 1N2
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.markdown("### Top 3 Scores Exacts Probables")
            for i, sc in enumerate(res['top_3_scores'], 1):
                st.write(f"**{i}er score :** `{sc['score']}` — Proba : **{sc['prob']}%**")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with c2:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.markdown("### Probabilités & Cotes Équitables 1N2")
            st.write(f"**Victoire {h_name} (1) :** {res['p_h']}% | Cote : **{res['odds_h']}**")
            st.write(f"**Match Nul (N) :** {res['p_n']}% | Cote : **{res['odds_n']}**")
            st.write(f"**Victoire {a_name} (2) :** {res['p_a']}% | Cote : **{res['odds_a']}**")
            st.markdown('</div>', unsafe_allow_html=True)

        # MARCHÉ DES CORNERS (DÉBUTE À +4.5)
        st.markdown('<div class="sub-card">', unsafe_allow_html=True)
        st.markdown("### Marché des Corners")
        st.markdown(f'<div class="text-summary">💡 {res["corners"]["summary"]}</div>', unsafe_allow_html=True)
        
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            st.metric("Plus de 4.5 Corners", f"{res['corners']['p_4_5']}%", f"Cote : {res['corners']['odds_4_5']}")
        with col_c2:
            st.metric("Plus de 6.5 Corners", f"{res['corners']['p_6_5']}%", f"Cote : {res['corners']['odds_6_5']}")
        with col_c3:
            st.metric("Plus de 8.5 Corners", f"{res['corners']['p_8_5']}%", f"Cote : {res['corners']['odds_8_5']}")
        with col_c4:
            st.metric("Plus de 10.5 Corners", f"{res['corners']['p_10_5']}%", f"Cote : {res['corners']['odds_10_5']}")
        st.markdown('</div>', unsafe_allow_html=True)

        # MARCHÉ DES CARTONS (DÉBUTE À +1.5 / +2.5 EN ALLANT)
        st.markdown('<div class="sub-card">', unsafe_allow_html=True)
        st.markdown("### Marché des Cartons Jaunes / Rouges")
        st.markdown(f'<div class="text-summary">💡 {res["cards"]["summary"]}</div>', unsafe_allow_html=True)
        
        col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
        with col_k1:
            st.metric("Plus de 1.5 Cartons", f"{res['cards']['p_1_5']}%", f"Cote : {res['cards']['odds_1_5']}")
        with col_k2:
            st.metric("Plus de 2.5 Cartons", f"{res['cards']['p_2_5']}%", f"Cote : {res['cards']['odds_2_5']}")
        with col_k3:
            st.metric("Plus de 3.5 Cartons", f"{res['cards']['p_3_5']}%", f"Cote : {res['cards']['odds_3_5']}")
        with col_k4:
            st.metric("Plus de 4.5 Cartons", f"{res['cards']['p_4_5']}%", f"Cote : {res['cards']['odds_4_5']}")
        with col_k5:
            st.metric("Plus de 5.5 Cartons", f"{res['cards']['p_5_5']}%", f"Cote : {res['cards']['odds_5_5']}")
        st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# ONGLET 4 : AUDIT
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
                pred = run_quant_prediction_v20(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False)
                audit_list.append({
                    "Date": m['utcDate'][:10],
                    "Match": f"{h_team} vs {a_team}",
                    "Score Réel": f"{real_h_g} - {real_a_g}",
                    "Conseil V20": pred["advice"]
                })
        st.dataframe(pd.DataFrame(audit_list), use_container_width=True, hide_index=True)
