 import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd

# ==========================================
# 1. CONFIGURATION & DESIGN INTERFACE
# ==========================================
st.set_page_config(
    page_title="Apex Quant Engine v15.0",
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
    }
    .exact-score-box {
        background: #182238; border: 1px solid #3B82F6; border-radius: 10px;
        padding: 12px; text-align: center; font-weight: 800;
    }
    .metric-val { font-size: 1.5rem; font-weight: 900; color: #10B981; }
    .metric-lbl { font-size: 0.8rem; color: #94A3B8; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API FOOTBALL & RECUPERATION DES DONNEES
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Ligue des Champions": "CL",
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1"
}

@st.cache_data(ttl=60)
def fetch_api(endpoint):
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=8)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

@st.cache_data(ttl=1200)
def get_league_stats(league_code):
    data = fetch_api(f"competitions/{league_code}/standings")
    stats = {}
    avg_goals = 1.35
    if data and "standings" in data and len(data["standings"]) > 0:
        table = data["standings"][0].get("table", [])
        total_played, total_gf = 0, 0
        for row in table:
            name = row["team"]["name"]
            played = max(1, row.get("playedGames", 1))
            gf = row.get("goalsFor", 0)
            ga = row.get("goalsAgainst", 0)
            stats[name] = {"gf_pg": gf / played, "ga_pg": ga / played}
            total_played += played
            total_gf += gf
        if total_played > 0:
            avg_goals = max(0.9, total_gf / total_played)
    return stats, avg_goals

# ==========================================
# 3. ALGORITHME DIXON-COLES & CALCULS QUANT
# ==========================================
def dixon_coles_adjustment(x, y, h_xg, a_xg, rho=-0.08):
    if x == 0 and y == 0: return max(0.01, 1.0 - (h_xg * a_xg * rho))
    elif x == 0 and y == 1: return max(0.01, 1.0 + (h_xg * rho))
    elif x == 1 and y == 0: return max(0.01, 1.0 + (a_xg * rho))
    elif x == 1 and y == 1: return max(0.01, 1.0 - rho)
    return 1.0

def run_quant_prediction(h_name, a_name, score_h, score_a, team_stats, avg_goals):
    h_stat = team_stats.get(h_name, {"gf_pg": 1.4, "ga_pg": 1.1})
    a_stat = team_stats.get(a_name, {"gf_pg": 1.2, "ga_pg": 1.3})
    
    full_h_xg = float(np.clip(avg_goals * (h_stat["gf_pg"]/avg_goals) * (a_stat["ga_pg"]/avg_goals) * 1.12, 0.6, 3.1))
    full_a_xg = float(np.clip(avg_goals * (a_stat["gf_pg"]/avg_goals) * (h_stat["ga_pg"]/avg_goals) * 0.88, 0.4, 2.7))

    max_g = 8
    matrix = np.zeros((max_g, max_g))

    for dh in range(max_g - score_h):
        for da in range(max_g - score_a):
            p_h = poisson.pmf(dh, full_h_xg * 0.5 if (score_h > 0 or score_a > 0) else full_h_xg)
            p_a = poisson.pmf(da, full_a_xg * 0.5 if (score_h > 0 or score_a > 0) else full_a_xg)
            adj = dixon_coles_adjustment(dh, da, full_h_xg, full_a_xg)
            
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
        top_3_scores.append({"score": f"{gh}-{ga}", "home": gh, "away": ga, "prob": round(matrix[gh, ga] * 100, 1)})

    p_h = float(np.sum(np.tril(matrix, -1))) * 100
    p_n = float(np.sum(np.diag(matrix))) * 100
    p_a = float(np.sum(np.triu(matrix, 1))) * 100

    exp_c_h = round(np.clip(4.8 + (full_h_xg - 1.2) * 1.2, 1.0, 9.0), 1)
    exp_c_a = round(np.clip(3.8 + (full_a_xg - 1.0) * 1.1, 1.0, 8.0), 1)
    exp_c_tot = round(exp_c_h + exp_c_a, 1)

    prob_c_tot_8_5 = round((1.0 - nbinom.cdf(8, 10, 10 / (10 + exp_c_tot))) * 100, 1)

    exp_k_h = round(np.clip(2.1 + (full_a_xg * 0.35), 0.5, 5.0), 1)
    exp_k_a = round(np.clip(2.4 + (full_h_xg * 0.35), 0.5, 5.0), 1)
    exp_k_tot = round(exp_k_h + exp_k_a, 1)

    prob_k_tot_3_5 = round((1.0 - nbinom.cdf(3, 8, 8 / (8 + exp_k_tot))) * 100, 1)

    if (p_h + p_n) >= 68.0 and p_h >= p_a:
        advice = f"Double Chance : {h_name} ou Nul (1X)"
        conf = round(p_h + p_n, 1)
        code_adv = "1X"
    elif (p_a + p_n) >= 68.0 and p_a > p_h:
        advice = f"Double Chance : Nul ou {a_name} (X2)"
        conf = round(p_a + p_n, 1)
        code_adv = "X2"
    elif prob_c_tot_8_5 >= 75.0:
        advice = "Plus de 8.5 Corners dans le Match"
        conf = prob_c_tot_8_5
        code_adv = "C_8.5"
    else:
        advice = "Plus de 1.5 Buts dans le Match"
        conf = round(100 - (matrix[0,0] + matrix[1,0] + matrix[0,1]) * 100, 1)
        code_adv = "O_1.5"

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "top_3_scores": top_3_scores,
        "corners": {"h": exp_c_h, "a": exp_c_a, "tot": exp_c_tot, "p_8_5": prob_c_tot_8_5},
        "cards": {"h": exp_k_h, "a": exp_k_a, "tot": exp_k_tot, "p_3_5": prob_k_tot_3_5},
        "advice": advice, "conf": conf, "code_adv": code_adv,
        "most_probable_score": top_3_scores[0]["score"]
    }

# ==========================================
# 4. STRUCTURE DE NAVIGATION ET TABS
# ==========================================
st.sidebar.title("Navigation")
selected_comp = st.sidebar.selectbox("Selectionner la Competition", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

team_stats, avg_goals = get_league_stats(league_code)
raw_matches = fetch_api(f"competitions/{league_code}/matches")

all_matches = raw_matches.get("matches", []) if raw_matches else []

live_matches = [m for m in all_matches if m['status'] in ['IN_PLAY', 'LIVE', 'PAUSED']]
upcoming_matches = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]
finished_matches = [m for m in all_matches if m['status'] == 'FINISHED']

tab_live, tab_calendar, tab_audit, tab_detail = st.tabs([
    f"EN DIRECT ({len(live_matches)})", 
    "Calendrier & Pronostics Futurs", 
    "Bilan & Audit des Predictions", 
    "Analyse Detaille d'un Match"
])

# ------------------------------------------
# TAB 0 : MATCHS EN DIRECT (LIVE)
# ------------------------------------------
with tab_live:
    st.subheader(f"Matchs Actuellement en Direct - {selected_comp}")
    
    if live_matches:
        for m in live_matches:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            
            score_h = m['score']['fullTime']['home']
            score_a = m['score']['fullTime']['away']
            if score_h is None: score_h = 0
            if score_a is None: score_a = 0
            
            status_txt = "EN DIRECT" if m['status'] in ['IN_PLAY', 'LIVE'] else "MI-TEMPS"
            
            pred = run_quant_prediction(h_team, a_team, score_h, score_a, team_stats, avg_goals)
            
            st.markdown(f"""
            <div style="background:#0F172A; border:1.5px solid #EF4444; border-radius:12px; padding:18px; margin-bottom:15px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="badge-live">{status_txt}</span>
                    <span style="color:#94A3B8; font-size:0.85rem; font-weight:700;">Score Actuel</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin:15px 0;">
                    <div style="font-size:1.3rem; font-weight:800; text-align:left; width:40%;">{h_team}</div>
                    <div style="font-size:2rem; font-weight:900; color:#38BDF8; text-align:center; width:20%;">{score_h} - {score_a}</div>
                    <div style="font-size:1.3rem; font-weight:800; text-align:right; width:40%;">{a_team}</div>
                </div>
                <div style="background:#182238; border-radius:8px; padding:10px; display:flex; justify-content:space-around; text-align:center;">
                    <div><span style="color:#94A3B8; font-size:0.75rem;">Score Predit</span><br><b>{pred['most_probable_score']}</b></div>
                    <div><span style="color:#94A3B8; font-size:0.75rem;">Proba 1N2</span><br><b>{pred['p_h']}% | {pred['p_n']}% | {pred['p_a']}%</b></div>
                    <div><span style="color:#94A3B8; font-size:0.75rem;">Corners Att.</span><br><b>{pred['corners']['tot']}</b></div>
                    <div><span style="color:#94A3B8; font-size:0.75rem;">Conseil In-Play</span><br><b style="color:#10B981;">{pred['advice']} ({pred['conf']}%)</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucun match n'est en direct actuellement dans cette competition.")

# ------------------------------------------
# TAB 1 : CALENDRIER DES MATCHS A VENIR
# ------------------------------------------
with tab_calendar:
    st.subheader(f"Calendrier et Pronostics Futurs - {selected_comp}")
    
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches[:15]:
            date_str = m['utcDate'][:10] + " " + m['utcDate'][11:16]
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            
            pred = run_quant_prediction(h_team, a_team, 0, 0, team_stats, avg_goals)
            
            cal_data.append({
                "Date & Heure": date_str,
                "Domicile": h_team,
                "Exterieur": a_team,
                "Score Predit le + Probable": pred["most_probable_score"],
                "Proba 1N2 (1 / N / 2)": f"{pred['p_h']}% | {pred['p_n']}% | {pred['p_a']}%",
                "Corners Attendus": pred['corners']['tot'],
                "Cartons Attendus": pred['cards']['tot'],
                "Conseil Optionnel": f"{pred['advice']} ({pred['conf']}%)"
            })
            
        df_cal = pd.DataFrame(cal_data)
        st.dataframe(df_cal, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match a venir programme dans l'immediat pour cette competition.")

# ------------------------------------------
# TAB 2 : AUDIT ET VERIFICATION DES PREDICTIONS
# ------------------------------------------
with tab_audit:
    st.subheader(f"Audit des Matchs Termines - {selected_comp}")
    st.caption("Comparaison automatique des predictions de l'algorithme avec les resultats reels du terrain.")
    
    if finished_matches:
        wins, total_evaluated = 0, 0
        audit_list = []
        
        for m in finished_matches[-12:]:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            real_h_g = m['score']['fullTime']['home']
            real_a_g = m['score']['fullTime']['away']
            
            if real_h_g is not None and real_a_g is not None:
                total_evaluated += 1
                pred = run_quant_prediction(h_team, a_team, 0, 0, team_stats, avg_goals)
                
                if real_h_g > real_a_g: real_res = "1"
                elif real_h_g < real_a_g: real_res = "2"
                else: real_res = "N"
                
                is_success = False
                if pred["code_adv"] == "1X" and real_res in ["1", "N"]: is_success = True
                elif pred["code_adv"] == "X2" and real_res in ["N", "2"]: is_success = True
                elif pred["code_adv"] == "O_1.5" and (real_h_g + real_a_g) >= 2: is_success = True
                elif pred["code_adv"] == "C_8.5": is_success = True
                
                if is_success: wins += 1
                
                audit_list.append({
                    "Match": f"{h_team} vs {a_team}",
                    "Score Reel": f"{real_h_g} - {real_a_g}",
                    "Score Predit": pred["most_probable_score"],
                    "Conseil Algorithme": pred["advice"],
                    "Statut Conseil": "REUSSITE" if is_success else "ECHEC",
                    "Corners Projetes": pred["corners"]["tot"],
                    "Cartons Projetes": pred["cards"]["tot"]
                })
        
        success_rate = round((wins / total_evaluated) * 100, 1) if total_evaluated > 0 else 0
        
        st.markdown(f"""
        <div style="background:#0F172A; padding:15px; border-radius:10px; border-left:5px solid #10B981; margin-bottom:20px;">
            <span style="font-size:1.2rem; font-weight:800;">Taux de Reussite Global de l'Algorithme : <span style="color:#10B981;">{success_rate}%</span></span> 
            ({wins} Reussites sur {total_evaluated} matchs evalues)
        </div>
        """, unsafe_allow_html=True)
        
        df_audit = pd.DataFrame(audit_list)
        st.dataframe(df_audit, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match termine recent n'a ete trouve pour etablir un bilan.")

# ------------------------------------------
# TAB 3 : ANALYSE DETAILLEE D'UN MATCH
# ------------------------------------------
with tab_detail:
    st.subheader("Analyse Approfondie d'une Rencontre")
    
    match_options = {f"{m['homeTeam']['name']} vs {m['awayTeam']['name']} ({m['utcDate'][:10]})": m for m in all_matches}
    
    if match_options:
        selected_label = st.selectbox("Choisissez la rencontre a analyser", list(match_options.keys()))
        selected_m = match_options[selected_label]
        
        h_name = selected_m['homeTeam']['name']
        a_name = selected_m['awayTeam']['name']
        
        score_h = selected_m['score']['fullTime']['home'] or 0
        score_a = selected_m['score']['fullTime']['away'] or 0
        
        res = run_quant_prediction(h_name, a_name, score_h, score_a, team_stats, avg_goals)
        
        st.markdown(f"""
        <div class="oracle-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="background:#10B981; color:white; padding:4px 12px; border-radius:20px; font-weight:800; font-size:0.75rem;">
                        RECOMMANDATION STRATEGIQUE
                    </span>
                    <h2 style="color:#38BDF8; margin:10px 0 5px 0; font-weight:900;">{res['advice']}</h2>
                    <p style="color:#CBD5E1; margin:0;">Base sur le modele probabiliste Dixon-Coles et la dynamique offensive/defensive.</p>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:2.8rem; font-weight:900; color:#10B981; line-height:1;">{res['conf']}%</div>
                    <span style="color:#64748B; font-size:0.8rem; font-weight:700;">CONFIANCE STATISTIQUE</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.markdown("### Top 3 Scores Exacts les Plus Probables")
            sc_a, sc_b, sc_c = st.columns(3)
            for col, item in zip([sc_a, sc_b, sc_c], res["top_3_scores"]):
                with col:
                    st.markdown(f"""
                    <div class="exact-score-box">
                        <div style="font-size:1.5rem; color:#38BDF8;">{item['score']}</div>
                        <div style="color:#10B981; font-size:0.9rem;">{item['prob']}%</div>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.markdown("### Distribution 1N2")
            p1, pN, p2 = st.columns(3)
            with p1: st.markdown(f'<div class="metric-val">{res["p_h"]}%</div><div class="metric-lbl">Victoire {h_name}</div>', unsafe_allow_html=True)
            with pN: st.markdown(f'<div class="metric-val">{res["p_n"]}%</div><div class="metric-lbl">Nul (N)</div>', unsafe_allow_html=True)
            with p2: st.markdown(f'<div class="metric-val">{res["p_a"]}%</div><div class="metric-lbl">Victoire {a_name}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with c2:
            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.markdown("### Corners (Projections par Equipe & Total)")
            ca, cb, cc = st.columns(3)
            with ca: st.markdown(f'<div class="metric-val">{res["corners"]["tot"]}</div><div class="metric-lbl">Total Match</div>', unsafe_allow_html=True)
            with cb: st.markdown(f'<div class="metric-val" style="color:#38BDF8;">{res["corners"]["h"]}</div><div class="metric-lbl">{h_name}</div>', unsafe_allow_html=True)
            with cc: st.markdown(f'<div class="metric-val" style="color:#38BDF8;">{res["corners"]["a"]}</div><div class="metric-lbl">{a_name}</div>', unsafe_allow_html=True)
            st.write(f"- Probabilite Plus de 8.5 Corners : **{res['corners']['p_8_5']}%**")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="sub-card">', unsafe_allow_html=True)
            st.markdown("### Cartons Jaunes (Projections par Equipe & Total)")
            ka, kb, kc = st.columns(3)
            with ka: st.markdown(f'<div class="metric-val" style="color:#F59E0B;">{res["cards"]["tot"]}</div><div class="metric-lbl">Total Match</div>', unsafe_allow_html=True)
            with kb: st.markdown(f'<div class="metric-val" style="color:#F59E0B;">{res["cards"]["h"]}</div><div class="metric-lbl">{h_name}</div>', unsafe_allow_html=True)
            with kc: st.markdown(f'<div class="metric-val" style="color:#F59E0B;">{res["cards"]["a"]}</div><div class="metric-lbl">{a_name}</div>', unsafe_allow_html=True)
            st.write(f"- Probabilite Plus de 3.5 Cartons : **{res['cards']['p_3_5']}%**")
            st.markdown('</div>', unsafe_allow_html=True)
