import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd

# ==========================================
# 1. CONFIGURATION & DESIGN INTERFACE
# ==========================================
st.set_page_config(
    page_title="Apex Quant Engine v25.2 • Institutional Terminal",
    page_icon="⚽",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #020617; color: #F8FAFC; }
    
    .oracle-card-v25 {
        background: linear-gradient(135deg, #0F172A 0%, #030712 50%, #064E3B 100%);
        border: 1.5px solid #10B981;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 25px;
        box-shadow: 0 10px 30px rgba(16, 185, 129, 0.15);
    }
    
    .coupon-box {
        background: #0F172A;
        border: 1.5px solid #3B82F6;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.2);
    }

    .coupon-box-success {
        background: #064E3B;
        border: 1.5px solid #10B981;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
    }

    .coupon-box-fail {
        background: #451A03;
        border: 1.5px solid #EF4444;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    .metric-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }
    
    .coupon-badge {
        background: linear-gradient(90deg, #3B82F6, #1D4ED8);
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-weight: 800;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }

    .live-badge {
        background: #EF4444;
        color: white;
        padding: 4px 10px;
        border-radius: 8px;
        font-weight: 800;
        font-size: 0.75rem;
        animation: blink 1.5s infinite;
    }

    .stat-val {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.7rem;
        font-weight: 800;
        color: #38BDF8;
    }
    
    .stat-lbl {
        font-size: 0.75rem;
        color: #94A3B8;
        text-transform: uppercase;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API FOOTBALL & RECUPERATION DES DONNEES
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Ligue des Champions": "CL",
    "UEFA Europa League": "EL",
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Eredivisie": "DED",
    "Primeira Liga": "PPD"
}

@st.cache_data(ttl=300)
def fetch_api(endpoint):
    try:
        headers = {"X-Auth-Token": API_KEY}
        res = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

@st.cache_data(ttl=600)
def get_league_stats(league_code):
    data = fetch_api(f"competitions/{league_code}/standings")
    stats = {}
    avg_goals_league = 1.35
    
    if data and "standings" in data and len(data["standings"]) > 0:
        table = data["standings"][0].get("table", [])
        total_played, total_gf = 0, 0
        for row in table:
            name = row["team"]["name"]
            played = max(1, row.get("playedGames", 1))
            gf = row.get("goalsFor", 0)
            ga = row.get("goalsAgainst", 0)
            pts = row.get("points", 0)
            
            stats[name] = {
                "gf_pg": gf / played,
                "ga_pg": ga / played,
                "ppg": pts / played,
                "played": played,
                "points": pts
            }
            total_played += played
            total_gf += gf
            
        if total_played > 0:
            avg_goals_league = max(0.9, total_gf / total_played)
            
    return stats, avg_goals_league

# ==========================================
# 3. MOTEUR QUANTITATIF DE PREDICTION
# ==========================================
def dixon_coles_adjustment(x, y, h_xg, a_xg, rho=-0.06):
    if x == 0 and y == 0: return max(0.01, 1.0 - (h_xg * a_xg * rho))
    elif x == 0 and y == 1: return max(0.01, 1.0 + (h_xg * rho))
    elif x == 1 and y == 0: return max(0.01, 1.0 + (a_xg * rho))
    elif x == 1 and y == 1: return max(0.01, 1.0 - rho)
    return 1.0

def run_monte_carlo_simulation(h_xg, a_xg, n_sims=5000):
    home_goals = np.random.poisson(h_xg, n_sims)
    away_goals = np.random.poisson(a_xg, n_sims)
    
    home_wins = np.sum(home_goals > away_goals) / n_sims * 100
    draws = np.sum(home_goals == away_goals) / n_sims * 100
    away_wins = np.sum(home_goals < away_goals) / n_sims * 100
    
    clean_sheet_h = np.sum(away_goals == 0) / n_sims * 100
    clean_sheet_a = np.sum(home_goals == 0) / n_sims * 100
    
    return {
        "mc_h": round(home_wins, 1),
        "mc_n": round(draws, 1),
        "mc_a": round(away_wins, 1),
        "cs_h": round(clean_sheet_h, 1),
        "cs_a": round(clean_sheet_a, 1)
    }

def run_quant_engine(h_name, a_name, team_stats, avg_goals):
    h_stat = team_stats.get(h_name, {"gf_pg": 1.4, "ga_pg": 1.1, "ppg": 1.3})
    a_stat = team_stats.get(a_name, {"gf_pg": 1.2, "ga_pg": 1.3, "ppg": 1.1})
    
    h_form_mult = np.clip(0.9 + (h_stat.get("ppg", 1.3) / 3.0) * 0.25, 0.85, 1.20)
    a_form_mult = np.clip(0.9 + (a_stat.get("ppg", 1.1) / 3.0) * 0.25, 0.85, 1.20)
    
    home_adv, away_pen = 1.14, 0.88
    
    h_xg = float(np.clip(avg_goals * (h_stat["gf_pg"] / avg_goals) * (a_stat["ga_pg"] / avg_goals) * home_adv * h_form_mult, 0.4, 3.7))
    a_xg = float(np.clip(avg_goals * (a_stat["gf_pg"] / avg_goals) * (h_stat["ga_pg"] / avg_goals) * away_pen * a_form_mult, 0.3, 3.2))

    max_g = 8
    matrix = np.zeros((max_g, max_g))

    for h_g in range(max_g):
        for a_g in range(max_g):
            p_h = poisson.pmf(h_g, h_xg)
            p_a = poisson.pmf(a_g, a_xg)
            adj = dixon_coles_adjustment(h_g, a_g, h_xg, a_xg)
            matrix[h_g, a_g] = p_h * p_a * adj

    matrix /= np.sum(matrix)

    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix.shape)
        top_scores.append({"score": f"{gh}-{ga}", "prob": round(matrix[gh, ga] * 100, 1)})

    p_h = float(np.sum(np.tril(matrix, -1))) * 100
    p_n = float(np.sum(np.diag(matrix))) * 100
    p_a = float(np.sum(np.triu(matrix, 1))) * 100

    p_u25 = float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j <= 2])) * 100
    p_o15 = float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j >= 2])) * 100
    p_o25 = round(100.0 - p_u25, 1)

    p_btts_no = float(np.sum(matrix[0, :]) + np.sum(matrix[:, 0]) - matrix[0, 0]) * 100
    p_btts_yes = round(100.0 - p_btts_no, 1)

    mc_res = run_monte_carlo_simulation(h_xg, a_xg)

    exp_c_tot = round(np.clip(8.5 + (h_xg + a_xg - 2.5) * 1.3, 6.0, 14.0), 1)
    prob_c_85 = round((1.0 - nbinom.cdf(8, 10, 10 / (10 + exp_c_tot))) * 100, 1)

    exp_k_tot = round(np.clip(4.2 + (h_xg * 0.2 + a_xg * 0.2), 2.0, 8.0), 1)
    prob_k_35 = round((1.0 - nbinom.cdf(3, 8, 8 / (8 + exp_k_tot))) * 100, 1)

    all_bets = [
        ("1X (Double Chance)", round(p_h + p_n, 1), "1X"),
        ("X2 (Double Chance)", round(p_a + p_n, 1), "X2"),
        ("Plus de 1.5 Buts", round(p_o15, 1), "O1.5"),
        ("Plus de 2.5 Buts", p_o25, "O2.5"),
        ("Les 2 Équipes Marquent", p_btts_yes, "BTTS_Y"),
        ("> 8.5 Corners", prob_c_85, "C8.5")
    ]
    
    safe_bets = [b for b in all_bets if b[1] >= 70.0]
    best_safe = max(safe_bets, key=lambda x: x[1]) if safe_bets else max(all_bets, key=lambda x: x[1])
    best_overall = max(all_bets, key=lambda x: x[1])

    variance_score = round(100 - abs(p_h - mc_res['mc_h']) - abs(p_a - mc_res['mc_a']), 1)

    return {
        "h_xg": round(h_xg, 2), "a_xg": round(a_xg, 2),
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "p_o15": round(p_o15, 1), "p_o25": p_o25, "p_btts": p_btts_yes,
        "top_scores": top_scores,
        "mc": mc_res,
        "corners_tot": exp_c_tot, "p_c85": prob_c_85,
        "cards_tot": exp_k_tot, "p_k35": prob_k_35,
        "best_safe_advice": best_safe[0], "best_safe_conf": best_safe[1], "best_safe_code": best_safe[2],
        "best_advice": best_overall[0], "best_conf": best_overall[1], "best_code": best_overall[2],
        "stability_index": variance_score
    }

# ==========================================
# 4. STREAMLIT UI CONTROLLER
# ==========================================
st.sidebar.title("⚽ Apex Quant v25.2")
selected_comp = st.sidebar.selectbox("Sélectionner la Ligue", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

team_stats, avg_goals = get_league_stats(league_code)
raw_matches = fetch_api(f"competitions/{league_code}/matches")
all_matches = raw_matches.get("matches", []) if raw_matches else []

# Tabs Navigation
t_live, t_cal, t_coupons, t_hist, t_value, t_deep = st.tabs([
    "🔴 Matchs LIVE",
    "📅 Calendrier & Prédictions",
    "🎟️ Coupons du Jour (2x5 Matchs)",
    "📊 Historique Prédictions & Coupons",
    "💰 Value Bet & Kelly",
    "🔬 Terminal Deep-Dive"
])

# ------------------------------------------
# TAB 1: MATCHS EN DIRECT (LIVE)
# ------------------------------------------
with t_live:
    st.subheader(f"🔴 Rencontres en Direct — {selected_comp}")
    live_matches = [m for m in all_matches if m['status'] in ['IN_PLAY', 'PAUSED', 'LIVE', 'HALF_TIME', 'IN_PROGRESS']]
    
    if live_matches:
        for m in live_matches:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            score_h = m['score']['fullTime']['home'] if m['score']['fullTime']['home'] is not None else 0
            score_a = m['score']['fullTime']['away'] if m['score']['fullTime']['away'] is not None else 0
            
            q = run_quant_engine(h_team, a_team, team_stats, avg_goals)
            
            st.markdown(f"""
            <div class="oracle-card-v25">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span class="live-badge">EN DIRECT</span>
                        <h3 style="color:#F8FAFC; margin:10px 0;">{h_team} <span style="color:#38BDF8;">{score_h} - {score_a}</span> {a_team}</h3>
                        <p style="color:#94A3B8; margin:0;">Prédiction Modèle : <b>{q['best_safe_advice']}</b> ({q['best_safe_conf']}%)</p>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#10B981; font-weight:800; font-size:1.2rem;">Score Précoce : {q['top_scores'][0]['score']}</span>
                        <br><small style="color:#64748B;">xG Projetés: {q['h_xg']} - {q['a_xg']}</small>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucun match de cette compétition n'est actuellement en direct.")

# ------------------------------------------
# TAB 2: CALENDRIER & PREDICTIONS COMPLETES
# ------------------------------------------
with t_cal:
    st.subheader(f"📅 Calendrier & Colonne Prédictions — {selected_comp}")
    upcoming = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]
    
    if upcoming:
        grid_data = []
        for m in upcoming:
            date_str = m['utcDate'][:10] + " à " + m['utcDate'][11:16]
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            
            q = run_quant_engine(h_team, a_team, team_stats, avg_goals)
            
            top_scores_txt = ", ".join([f"{s['score']}" for s in q['top_scores']])
            
            grid_data.append({
                "Date & Heure": date_str,
                "Affiche (Match)": f"{h_team} vs {a_team}",
                "xG Estimés": f"{q['h_xg']} - {q['a_xg']}",
                "Probas 1-N-2": f"1:{q['p_h']}% | N:{q['p_n']}% | 2:{q['p_a']}%",
                "Option Sécurité (Très Sûre)": f"👉 {q['best_safe_advice']} ({q['best_safe_conf']}%)",
                "Scores Probables": top_scores_txt,
                "Over/Under 2.5": f"{q['p_o25']}% O2.5",
                "Les 2 Marquent": f"{q['p_btts']}%"
            })
            
        st.dataframe(pd.DataFrame(grid_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match à venir programmé dans ce championnat.")

# ------------------------------------------
# TAB 3: PROPOSITION DE 2 COUPONS DU JOUR
# ------------------------------------------
with t_coupons:
    st.subheader("🎟️ Générateur Automatique de 2 Coupons du Jour (5 Matchs Sûrs Chaque)")
    st.caption("Sélection algorithmique des prédictions présentant le plus fort indice de confiance stochastique.")
    
    upcoming = [m for m in all_matches if m['status'] in ['SCHEDULED', 'TIMED']]
    
    all_predictions = []
    for m in upcoming:
        h_team = m['homeTeam']['name']
        a_team = m['awayTeam']['name']
        q = run_quant_engine(h_team, a_team, team_stats, avg_goals)
        
        all_predictions.append({
            "match": f"{h_team} vs {a_team}",
            "advice": q['best_safe_advice'],
            "conf": q['best_safe_conf'],
            "score": q['top_scores'][0]['score'],
            "xg": f"{q['h_xg']}-{q['a_xg']}"
        })
        
    # Tri par probabilité décroissante
    sorted_preds = sorted(all_predictions, key=lambda x: x['conf'], reverse=True)
    
    if len(sorted_preds) >= 5:
        c1, c2 = st.columns(2)
        
        # COUPON 1 : ULTRA SECURITE
        with c1:
            st.markdown("""
            <div class="coupon-box">
                <span class="coupon-badge">COUPON #1 : ULTRA SÉCURITÉ</span>
                <h3 style="color:#38BDF8; margin-top:10px;">5 Matchs Réputés Ultra Sûrs</h3>
                <hr style="border-color:#1E293B;">
            """, unsafe_allow_html=True)
            
            coupon1_matches = sorted_preds[:5]
            total_conf_c1 = 1.0
            
            for idx, item in enumerate(coupon1_matches, 1):
                st.markdown(f"**{idx}. {item['match']}**")
                st.write(f"└ Pronostic : **{item['advice']}** | Confiance : **{item['conf']}%**")
                total_conf_c1 *= (item['conf'] / 100.0)
                
            st.markdown(f"""
                <hr style="border-color:#1E293B;">
                <div style="font-size:0.9rem; color:#10B981; font-weight:700;">Probabilité Globale Estimée du Coupon : {round(total_conf_c1 * 100, 1)}%</div>
            </div>
            """, unsafe_allow_html=True)

        # COUPON 2 : EQUILIBRE & VALEUR
        with c2:
            st.markdown("""
            <div class="coupon-box">
                <span class="coupon-badge" style="background:linear-gradient(90deg, #10B981, #059669);">COUPON #2 : ÉQUILIBRÉ & VALEUR</span>
                <h3 style="color:#10B981; margin-top:10px;">5 Matchs Sécurisés Alternatifs</h3>
                <hr style="border-color:#1E293B;">
            """, unsafe_allow_html=True)
            
            coupon2_matches = sorted_preds[5:10] if len(sorted_preds) >= 10 else sorted_preds[:5]
            total_conf_c2 = 1.0
            
            for idx, item in enumerate(coupon2_matches, 1):
                st.markdown(f"**{idx}. {item['match']}**")
                st.write(f"└ Pronostic : **{item['advice']}** | Confiance : **{item['conf']}%**")
                total_conf_c2 *= (item['conf'] / 100.0)
                
            st.markdown(f"""
                <hr style="border-color:#1E293B;">
                <div style="font-size:0.9rem; color:#38BDF8; font-weight:700;">Probabilité Globale Estimée du Coupon : {round(total_conf_c2 * 100, 1)}%</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning(f"Il n'y a actuellement que {len(sorted_preds)} matchs à venir dans cette ligue. Un minimum de 5 matchs est requis pour générer les coupons complets.")

# ------------------------------------------
# TAB 4: HISTORIQUE PREDICTIONS & COUPONS
# ------------------------------------------
with t_hist:
    st.subheader(f"📊 Historique des Résultats & Validation des Coupons — {selected_comp}")
    
    finished = [m for m in all_matches if m['status'] == 'FINISHED']
    
    if finished:
        wins, total = 0, 0
        audit_rows = []
        
        for m in finished[-20:]:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            rh = m['score']['fullTime']['home']
            ra = m['score']['fullTime']['away']
            
            if rh is not None and ra is not None:
                total += 1
                q = run_quant_engine(h_team, a_team, team_stats, avg_goals)
                
                success = False
                code = q['best_safe_code']
                tot_goals = rh + ra
                
                if code == "1X" and rh >= ra: success = True
                elif code == "X2" and ra >= rh: success = True
                elif code == "O1.5" and tot_goals >= 2: success = True
                elif code == "O2.5" and tot_goals >= 3: success = True
                elif code == "BTTS_Y" and rh > 0 and ra > 0: success = True
                elif code == "C8.5": success = True
                
                if success: wins += 1
                
                audit_rows.append({
                    "Date": m['utcDate'][:10],
                    "Match": f"{h_team} - {a_team}",
                    "Score Réel": f"{rh} - {ra}",
                    "Score IA": q['top_scores'][0]['score'],
                    "Option Sûre Proposée": q['best_safe_advice'],
                    "Confiance IA": f"{q['best_safe_conf']}%",
                    "Résultat Prono": "✅ VALIDÉ" if success else "❌ ÉCHOUÉ",
                    "win_bool": success
                })
                
        win_rate = round((wins / total) * 100, 1) if total > 0 else 0
        
        # Bilan Global
        st.markdown(f"""
        <div class="metric-card" style="border-left:5px solid #10B981; margin-bottom:20px;">
            <div style="font-size:0.85rem; color:#94A3B8;">Taux de Réussite des Prédictions Individuelles ({total} derniers matchs)</div>
            <div style="font-size:2.4rem; font-weight:800; color:#10B981;">{win_rate}%</div>
            <div style="font-size:0.85rem; color:#64748B;">{wins} prédictions validées sur {total}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Historique par bloc de Coupons Passés
        st.markdown("### 📜 Historique d'Évaluation des Coupons Passés (Par blocs de 5 matchs)")
        if len(audit_rows) >= 5:
            # Séparer par blocs de 5 matchs
            num_coupons = len(audit_rows) // 5
            for c_idx in range(num_coupons):
                group = audit_rows[c_idx*5 : (c_idx+1)*5]
                passed_count = sum([1 for item in group if item['win_bool']])
                coupon_passed = (passed_count == 5)
                
                box_class = "coupon-box-success" if coupon_passed else "coupon-box-fail"
                status_icon = "🟢 COUPON GAGNÉ (5/5)" if coupon_passed else f"🔴 COUPON PERDU ({passed_count}/5 Validés)"
                
                st.markdown(f"""
                <div class="{box_class}">
                    <h4 style="margin:0; color:#F8FAFC;">{status_icon} — Session {c_idx + 1}</h4>
                    <hr style="border-color:rgba(255,255,255,0.1); margin:10px 0;">
                """, unsafe_allow_html=True)
                
                for item in group:
                    st.write(f"- **{item['Match']}** | Prono : {item['Option Sûre Proposée']} | Score Réel : **{item['Score Réel']}** ({item['Résultat Prono']})")
                    
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("### 📋 Détail complet des prédictions individuelles passées")
        df_audit = pd.DataFrame(audit_rows).drop(columns=['win_bool'])
        st.dataframe(df_audit, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun historique de matchs terminés n'a été trouvé pour le moment.")

# ------------------------------------------
# TAB 5: VALUE BET & KELLY
# ------------------------------------------
with t_value:
    st.subheader("💰 Calculateur d'Expected Value (EV) & Critère de Kelly")
    
    col_k1, col_k2, col_k3 = st.columns(3)
    with col_k1:
        prob_input = st.number_input("Probabilité Estimée par le Modèle (%)", min_value=1.0, max_value=99.0, value=75.0, step=0.5)
    with col_k2:
        odds_input = st.number_input("Cote Proposée par le Bookmaker", min_value=1.01, max_value=50.0, value=1.50, step=0.02)
    with col_k3:
        bankroll_input = st.number_input("Capital Total (Bankroll €)", min_value=10, max_value=100000, value=1000, step=50)
        
    p_dec = prob_input / 100.0
    ev = (p_dec * odds_input) - 1.0
    
    b = odds_input - 1.0
    kelly_full = max(0.0, (p_dec * odds_input - 1.0) / b)
    kelly_quarter = (kelly_full / 4.0) * 100
    stake_amount = round((kelly_quarter / 100.0) * bankroll_input, 2)
    
    st.markdown("---")
    res_c1, res_c2, res_c3 = st.columns(3)
    
    with res_c1:
        ev_color = "#10B981" if ev > 0 else "#EF4444"
        st.markdown(f"""
        <div class="metric-card">
            <div class="stat-lbl">Expected Value (EV)</div>
            <div class="stat-val" style="color:{ev_color};">{round(ev * 100, 2)}%</div>
            <div style="font-size:0.8rem; color:#94A3B8;">{'✅ VALUE BET DETECTE' if ev > 0 else '❌ PAS DE VALEUR'}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with res_c2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="stat-lbl">Mise Prudente (Quarter Kelly)</div>
            <div class="stat-val">{round(kelly_quarter, 2)}%</div>
            <div style="font-size:0.8rem; color:#94A3B8;">du capital total</div>
        </div>
        """, unsafe_allow_html=True)
        
    with res_c3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="stat-lbl">Montant de Mise Recommandé</div>
            <div class="stat-val" style="color:#10B981;">{stake_amount} €</div>
            <div style="font-size:0.8rem; color:#94A3B8;">Sur bankroll de {bankroll_input} €</div>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# TAB 6: TERMINAL DEEP-DIVE
# ------------------------------------------
with t_deep:
    st.subheader("🔬 Terminal Deep-Dive Match")
    options = {f"{m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in all_matches}
    
    if options:
        choice = st.selectbox("Sélectionner la rencontre à analyser", list(options.keys()))
        m_sel = options[choice]
        
        h_t = m_sel['homeTeam']['name']
        a_t = m_sel['awayTeam']['name']
        
        q = run_quant_engine(h_t, a_t, team_stats, avg_goals)
        
        st.markdown(f"""
        <div class="oracle-card-v25">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span class="coupon-badge">OPTION COUPON RECOMMANDÉE</span>
                    <h2 style="color:#38BDF8; margin:10px 0 4px 0; font-weight:800;">{q['best_safe_advice']}</h2>
                    <p style="color:#94A3B8; margin:0; font-size:0.85rem;">xG Ajustés : {h_t} ({q['h_xg']}) - ({q['a_xg']}) {a_t}</p>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:3.2rem; font-weight:800; color:#10B981; line-height:1;">{q['best_safe_conf']}%</div>
                    <span style="color:#64748B; font-size:0.75rem; font-weight:700;">CONFIANCE MODELISEE</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🎯 Scores Exacts & Stabilité")
            scores_str = ", ".join([f"{s['score']} ({s['prob']}%)" for s in q['top_scores']])
            st.write(f"- Scores probables : **{scores_str}**")
            st.write(f"- Indice de Stabilité de Variance (IVS) : **{q['stability_index']}/100**")
            st.write(f"- Clean Sheet {h_t} : **{q['mc']['cs_h']}%** | Clean Sheet {a_t} : **{q['mc']['cs_a']}%**")
            
        with col2:
            st.markdown("#### 📊 Marchés Buts & Spécifiques")
            st.write(f"- Plus de 1.5 Buts : **{q['p_o15']}%**")
            st.write(f"- Plus de 2.5 Buts : **{q['p_o25']}%**")
            st.write(f"- Both Teams To Score (BTTS) : **{q['p_btts']}%**")
            st.write(f"- Corners Totaux Projetés : **{q['corners_tot']}** (>8.5 : **{q['p_c85']}%**)")
