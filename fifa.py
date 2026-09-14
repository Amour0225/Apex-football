import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. CONFIGURATION DE LA PAGE & STYLES CSS
# ==========================================
st.set_page_config(
    page_title="Apex Quant Engine • fifa.py",
    page_icon="⚽",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #030712; color: #F8FAFC; }
    
    .hero-header {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(3, 7, 18, 0.95) 100%);
        border: 1px solid rgba(56, 189, 248, 0.2);
        box-shadow: 0 20px 40px rgba(0,0,0,0.6);
        border-radius: 20px;
        padding: 24px;
        margin-bottom: 25px;
    }
    
    .coupon-card-v1 {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(6, 78, 59, 0.25));
        border: 1.5px solid #10B981;
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 12px 30px rgba(16, 185, 129, 0.15);
        margin-bottom: 20px;
    }
    
    .coupon-card-v2 {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(30, 58, 138, 0.3));
        border: 1.5px solid #3B82F6;
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 12px 30px rgba(59, 130, 246, 0.15);
        margin-bottom: 20px;
    }

    .badge-gold {
        background: linear-gradient(90deg, #F59E0B, #D97706);
        color: #000;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    
    .badge-blue {
        background: linear-gradient(90deg, #38BDF8, #2563EB);
        color: #FFF;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    .league-pill {
        background: rgba(56, 189, 248, 0.1);
        color: #38BDF8;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    .match-row-item {
        background: rgba(15, 23, 42, 0.6);
        border-left: 4px solid #10B981;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 10px 0;
    }
    
    .match-row-item-blue {
        background: rgba(15, 23, 42, 0.6);
        border-left: 4px solid #3B82F6;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 10px 0;
    }

    .deep-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CLIENT API FOOTBALL-DATA.ORG
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"
TARGET_COMPETITIONS = "PL,CL,EL,FL1,BL1,SA,PD,DED,PPD"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_api(endpoint):
    try:
        headers = {"X-Auth-Token": API_KEY}
        res = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=12)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

# ==========================================
# 3. MODÈLE HYBRIDE : POISSON & DIXON-COLES
# ==========================================
def dixon_coles_tau(x, y, lambda_h, mu_a, rho=-0.13):
    """Facteur de correction de Dixon-Coles pour les scores faibles (0-0, 1-0, 0-1, 1-1)"""
    if x == 0 and y == 0:
        return 1.0 - (lambda_h * mu_a * rho)
    elif x == 1 and y == 0:
        return 1.0 + (mu_a * rho)
    elif x == 0 and y == 1:
        return 1.0 + (lambda_h * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0

@st.cache_data(ttl=3600, show_spinner=False)
def get_league_standings(competition_code):
    data = fetch_api(f"competitions/{competition_code}/standings")
    standings = {}
    
    if data and "standings" in data and len(data["standings"]) > 0:
        all_rows = []
        for st_group in data["standings"]:
            if "table" in st_group:
                all_rows.extend(st_group["table"])
                
        total_goals = sum(t["goalsFor"] for t in all_rows)
        total_played = sum(t["playedGames"] for t in all_rows)
        avg_league_goals = (total_goals / total_played / 2.0) if total_played > 0 else 1.35

        for row in all_rows:
            played = max(1, row["playedGames"])
            standings[row["team"]["name"]] = {
                "att": (row["goalsFor"] / played) / avg_league_goals,
                "def": (row["goalsAgainst"] / played) / avg_league_goals
            }
        return standings, avg_league_goals
    return {}, 1.35

def compute_quant_predictions(home_team, away_team, comp_code):
    standings, avg_goals = get_league_standings(comp_code)
    
    h_att = standings.get(home_team, {}).get("att", 1.15)
    h_def = standings.get(home_team, {}).get("def", 0.90)
    a_att = standings.get(away_team, {}).get("att", 1.05)
    a_def = standings.get(away_team, {}).get("def", 1.10)
    
    home_adv = 1.12 if comp_code in ['EL', 'CL'] else 1.10
    h_xg = max(0.4, h_att * a_def * avg_goals * home_adv)
    a_xg = max(0.3, a_att * h_def * avg_goals * (2.0 - home_adv))
    
    max_goals = 6
    p_matrix = np.zeros((max_goals, max_goals))
    for i in range(max_goals):
        for j in range(max_goals):
            p_raw = poisson.pmf(i, h_xg) * poisson.pmf(j, a_xg)
            tau = dixon_coles_tau(i, j, h_xg, a_xg)
            p_matrix[i, j] = max(0, p_raw * tau)
            
    # Normalisation de la matrice de probabilité
    total_p = np.sum(p_matrix)
    if total_p > 0:
        p_matrix = p_matrix / total_p

    p_h = np.sum(np.triu(p_matrix, 1).T) * 100
    p_n = np.sum(np.diag(p_matrix)) * 100
    p_a = np.sum(np.tril(p_matrix, -1)) * 100
    
    p_1x = p_h + p_n
    p_x2 = p_a + p_n
    
    total_goals_grid = np.add.outer(np.arange(max_goals), np.arange(max_goals))
    p_o15 = np.sum(p_matrix[total_goals_grid > 1]) * 100
    p_o25 = np.sum(p_matrix[total_goals_grid > 2]) * 100
    p_btts = np.sum(p_matrix[1:, 1:]) * 100
    
    best_score_idx = np.unravel_index(np.argmax(p_matrix), p_matrix.shape)
    probable_score = f"{best_score_idx[0]} - {best_score_idx[1]}"
    
    options = [
        ("1X (Double Chance)", round(p_1x, 1)),
        ("X2 (Double Chance)", round(p_x2, 1)),
        ("Plus de 1.5 Buts", round(p_o15, 1)),
        ("Plus de 2.5 Buts", round(p_o25, 1)),
        ("Les 2 Équipes Marquent", round(p_btts, 1)),
        ("Victoire Domicile (1)", round(p_h, 1)),
        ("Victoire Extérieur (2)", round(p_a, 1))
    ]
    
    sorted_options = sorted(options, key=lambda x: x[1], reverse=True)
    best_option = sorted_options[0]
    sec_option = sorted_options[1]
    
    return {
        "h_xg": round(h_xg, 2), "a_xg": round(a_xg, 2),
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "p_1x": round(p_1x, 1), "p_x2": round(p_x2, 1),
        "p_o15": round(p_o15, 1), "p_o25": round(p_o25, 1),
        "p_btts": round(p_btts, 1),
        "probable_score": probable_score,
        "advice": best_option[0], "conf": best_option[1],
        "sec_advice": sec_option[0], "sec_conf": sec_option[1]
    }

# ==========================================
# 4. RÉCUPÉRATION DES MATCHS & HISTORIQUE
# ==========================================
@st.cache_data(ttl=300, show_spinner="Analyse des rencontres en cours...")
def get_today_matches():
    now = datetime.now(timezone.utc)
    date_from = now.strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    raw_data = fetch_api(f"matches?competitions={TARGET_COMPETITIONS}&dateFrom={date_from}&dateTo={date_to}")
    predictions = []
    
    if raw_data and "matches" in raw_data:
        for m in raw_data["matches"]:
            league_name = m.get("competition", {}).get("name", "Autre Ligue")
            comp_code = m.get("competition", {}).get("code", "PL")
            h_team = m["homeTeam"]["name"]
            a_team = m["awayTeam"]["name"]
            
            raw_utc = m["utcDate"]
            date_raw = raw_utc[:10]
            time_raw = raw_utc[11:16]
            formatted_date = datetime.strptime(date_raw, "%Y-%m-%d").strftime("%d/%m/%Y")
            
            q = compute_quant_predictions(h_team, a_team, comp_code)
            
            predictions.append({
                "league": league_name, "comp_code": comp_code,
                "home": h_team, "away": a_team,
                "date_raw": date_raw, "date_formatted": formatted_date, "time": time_raw,
                "match": f"{h_team} vs {a_team}",
                "advice": q["advice"], "conf": q["conf"],
                "sec_advice": q["sec_advice"], "sec_conf": q["sec_conf"],
                "probable_score": q["probable_score"],
                "xg": f"{q['h_xg']} - {q['a_xg']}",
                "p_h": q['p_h'], "p_n": q['p_n'], "p_a": q['p_a'],
                "p_o15": q['p_o15'], "p_o25": q['p_o25'], "p_btts": q['p_btts']
            })
            
    return sorted(predictions, key=lambda x: x["conf"], reverse=True)

@st.cache_data(ttl=600, show_spinner="Calcul de l'audit de performance...")
def get_finished_history():
    now = datetime.now(timezone.utc)
    date_from = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    date_to = now.strftime("%Y-%m-%d")
    
    raw_data = fetch_api(f"matches?status=FINISHED&competitions={TARGET_COMPETITIONS}&dateFrom={date_from}&dateTo={date_to}")
    history = []
    
    if raw_data and "matches" in raw_data:
        for m in raw_data["matches"]:
            h_team = m["homeTeam"]["name"]
            a_team = m["awayTeam"]["name"]
            comp_code = m.get("competition", {}).get("code", "PL")
            league_name = m.get("competition", {}).get("name", "Autre Ligue")
            
            h_score = m["score"]["fullTime"]["home"]
            a_score = m["score"]["fullTime"]["away"]
            
            if h_score is not None and a_score is not None:
                q = compute_quant_predictions(h_team, a_team, comp_code)
                advice = q["advice"]
                
                is_win = False
                if "1X" in advice and (h_score >= a_score): is_win = True
                elif "X2" in advice and (a_score >= h_score): is_win = True
                elif "1.5" in advice and (h_score + a_score > 1): is_win = True
                elif "2.5" in advice and (h_score + a_score > 2): is_win = True
                elif "Marquent" in advice and (h_score > 0 and a_score > 0): is_win = True
                elif "(1)" in advice and (h_score > a_score): is_win = True
                elif "(2)" in advice and (a_score > h_score): is_win = True

                history.append({
                    "date": datetime.strptime(m["utcDate"][:10], "%Y-%m-%d").strftime("%d/%m/%Y"),
                    "league": league_name,
                    "match": f"{h_team} {h_score} - {a_score} {a_team}",
                    "advice": advice,
                    "conf": f"{q['conf']}%",
                    "status": "✅ GAGNÉ" if is_win else "❌ PERDU",
                    "is_win": is_win
                })
    return history

all_predictions = get_today_matches()
history_data = get_finished_history()

# ==========================================
# 5. SIDEBAR : SELECTION DES LIGUES
# ==========================================
st.sidebar.title("🏆 Compétitions")
available_leagues = sorted(list(set(item['league'] for item in all_predictions)))
league_options = ["Toutes les ligues (Global)"] + available_leagues

selected_league = st.sidebar.selectbox("Sélectionnez la compétition :", options=league_options, index=0)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Actualiser les données"):
    st.cache_data.clear()
    st.rerun()

filtered_predictions = all_predictions if selected_league == "Toutes les ligues (Global)" else [p for p in all_predictions if p['league'] == selected_league]

# ==========================================
# 6. INTERFACE UTILISATEUR
# ==========================================
st.markdown(f"""
<div class="hero-header">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span class="badge-gold">MOTEUR DIXON-COLES & POISSON • FIFA.PY</span>
            <h1 style="color:#FFF; margin:10px 0 0 0; font-weight:800; font-size:1.8rem;">{selected_league}</h1>
            <p style="color:#94A3B8; margin:5px 0 0 0; font-size:0.9rem;">Générateur quantitatif de coupons et analyse prédictive à haute fréquence.</p>
        </div>
        <div style="text-align:right;">
            <span class="badge-blue">{len(filtered_predictions)} Rencontres Analysées</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

t_coupons, t_deep, t_hist, t_cal = st.tabs([
    "🎟️ Coupons Optimisés",
    "🔍 Prédiction Détaillée",
    "📜 Audit & Historique (7J)",
    "📅 Programme des Matchs"
])

# ------------------------------------------
# TAB 1 : COUPONS DU JOUR
# ------------------------------------------
with t_coupons:
    if filtered_predictions:
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("""
            <div class="coupon-card-v1">
                <span class="badge-gold">COUPON SÉCURITÉ MAX</span>
                <hr style="border-color:rgba(16, 185, 129, 0.2); margin:15px 0;">
            """, unsafe_allow_html=True)
            
            c1_matches = filtered_predictions[:5]
            conf_c1 = 1.0
            for idx, item in enumerate(c1_matches, 1):
                conf_c1 *= (item['conf'] / 100.0)
                st.markdown(f"""
                <div class="match-row-item">
                    <div style="display:flex; justify-content:space-between;">
                        <div>
                            <span class="league-pill">{item['league']}</span> • <span style="font-size:0.75rem; color:#94A3B8;">{item['time']}</span>
                            <div style="font-weight:700; color:#F8FAFC; margin-top:4px;">{idx}. {item['match']}</div>
                        </div>
                        <div style="text-align:right;">
                            <span style="color:#10B981; font-weight:800;">{item['advice']}</span>
                            <div style="font-size:0.75rem; color:#F59E0B; font-weight:700;">{item['conf']}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(f"<b>Fiabilité Cumulée Estimée : {round(conf_c1*100, 1)}%</b></div>", unsafe_allow_html=True)

        with c2:
            st.markdown("""
            <div class="coupon-card-v2">
                <span class="badge-blue">COUPON ALTERNATIF / VALEUR</span>
                <hr style="border-color:rgba(59, 130, 246, 0.2); margin:15px 0;">
            """, unsafe_allow_html=True)
            
            c2_matches = filtered_predictions[5:10] if len(filtered_predictions) >= 8 else filtered_predictions[:5]
            conf_c2 = 1.0
            for idx, item in enumerate(c2_matches, 1):
                conf_c2 *= (item['sec_conf'] / 100.0)
                st.markdown(f"""
                <div class="match-row-item-blue">
                    <div style="display:flex; justify-content:space-between;">
                        <div>
                            <span class="league-pill">{item['league']}</span> • <span style="font-size:0.75rem; color:#94A3B8;">{item['time']}</span>
                            <div style="font-weight:700; color:#F8FAFC; margin-top:4px;">{idx}. {item['match']}</div>
                        </div>
                        <div style="text-align:right;">
                            <span style="color:#38BDF8; font-weight:800;">{item['sec_advice']}</span>
                            <div style="font-size:0.75rem; color:#38BDF8; font-weight:700;">{item['sec_conf']}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown(f"<b>Fiabilité Cumulée Estimée : {round(conf_c2*100, 1)}%</b></div>", unsafe_allow_html=True)
    else:
        st.info("Aucun match disponible pour cette sélection.")

# ------------------------------------------
# TAB 2 : DEEP DIVE
# ------------------------------------------
with t_deep:
    st.subheader("🔍 Analyse Approfondie par Match")
    if filtered_predictions:
        match_titles = [f"{m['match']} ({m['league']} - {m['time']})" for m in filtered_predictions]
        sel_match_idx = st.selectbox("Sélectionnez le match :", range(len(match_titles)), format_func=lambda x: match_titles[x])
        
        m = filtered_predictions[sel_match_idx]
        
        st.markdown(f"""
        <div class="deep-card">
            <h2 style="color:#FFF; margin:0; text-align:center;">{m['match']}</h2>
            <p style="text-align:center; color:#94A3B8; margin-top:5px;">{m['league']} • Programmé à {m['time']}</p>
            <hr style="border-color:#1E293B; margin:15px 0;">
            
            <div style="display:flex; justify-content:space-around; text-align:center;">
                <div>
                    <span style="color:#94A3B8; font-size:0.85rem;">xG Attendu</span>
                    <div style="font-size:1.4rem; font-weight:800; color:#38BDF8;">{m['xg']}</div>
                </div>
                <div>
                    <span style="color:#94A3B8; font-size:0.85rem;">Score Probable</span>
                    <div style="font-size:1.4rem; font-weight:800; color:#F59E0B;">{m['probable_score']}</div>
                </div>
                <div>
                    <span style="color:#94A3B8; font-size:0.85rem;">Conseil Principal</span>
                    <div style="font-size:1.4rem; font-weight:800; color:#10B981;">{m['advice']} ({m['conf']}%)</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("### 📊 Issus 1N2")
            st.write(f"**Victoire Domicile :** {m['p_h']}%")
            st.progress(int(m['p_h']))
            st.write(f"**Match Nul :** {m['p_n']}%")
            st.progress(int(m['p_n']))
            st.write(f"**Victoire Extérieur :** {m['p_a']}%")
            st.progress(int(m['p_a']))
        with c2:
            st.markdown("### ⚽ Totaux Buts")
            st.write(f"**Plus de 1.5 Buts :** {m['p_o15']}%")
            st.progress(int(m['p_o15']))
            st.write(f"**Plus de 2.5 Buts :** {m['p_o25']}%")
            st.progress(int(m['p_o25']))
        with c3:
            st.markdown("### 💡 Suggérés")
            st.info(f"**Pari Sécurité :** {m['advice']} ({m['conf']}%)")
            st.warning(f"**Pari Secours :** {m['sec_advice']} ({m['sec_conf']}%)")
    else:
        st.info("Aucun match disponible.")

# ------------------------------------------
# TAB 3 : HISTORIQUE ET AUDIT
# ------------------------------------------
with t_hist:
    st.subheader("📜 Historique Récent des 7 Derniers Jours")
    if history_data:
        wins = sum(1 for h in history_data if h['is_win'])
        total = len(history_data)
        rate = round((wins / total) * 100, 1) if total > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Matchs Joués Evalués", total)
        m2.metric("Paris Gagnés", wins)
        m3.metric("Taux de Réussite Réel", f"{rate}%")
        
        st.markdown("---")
        df_hist = pd.DataFrame(history_data)[['date', 'league', 'match', 'advice', 'conf', 'status']]
        df_hist.columns = ['Date', 'Championnat', 'Match & Score', 'Conseil Algo', 'Confiance', 'Résultat']
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun historique récent disponible.")

# ------------------------------------------
# TAB 4 : CALENDRIER DES MATCHS
# ------------------------------------------
with t_cal:
    st.subheader("📅 Programme des Rencontres")
    if filtered_predictions:
        grid = [{
            "⏰ Heure": m['time'],
            "🏆 Ligue": m['league'],
            "⚔️ Rencontre": m['match'],
            "💡 Conseil Securité": m['advice'],
            "📈 Indice de Confiance": f"{m['conf']}%"
        } for m in filtered_predictions]
        st.dataframe(pd.DataFrame(grid), use_container_width=True, hide_index=True)
