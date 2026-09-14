import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. CONFIGURATION & DESIGN INTERFACE
# ==========================================
st.set_page_config(
    page_title="Apex Quant Engine v25.5 • High-Precision Terminal",
    page_icon="⚡",
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
        box-shadow: 0 20px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1);
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
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CLIENT API & CACHING
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

@st.cache_data(ttl=600, show_spinner=False)
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
# 3. MOTEUR MATHÉMATIQUE DE PRÉDICTION (POISSON MODEL)
# ==========================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_league_standings(competition_code):
    """Récupère le classement pour calculer les forces réelles des équipes"""
    data = fetch_api(f"competitions/{competition_code}/standings")
    standings = {}
    if data and "standings" in data and len(data["standings"]) > 0:
        table = data["standings"][0]["table"]
        total_goals = sum(t["goalsFor"] for t in table)
        total_played = sum(t["playedGames"] for t in table)
        avg_league_goals = (total_goals / total_played / 2.0) if total_played > 0 else 1.35

        for row in table:
            played = max(1, row["playedGames"])
            standings[row["team"]["name"]] = {
                "att": (row["goalsFor"] / played) / avg_league_goals,
                "def": (row["goalsAgainst"] / played) / avg_league_goals
            }
        return standings, avg_league_goals
    return {}, 1.35

def compute_quant_predictions(home_team, away_team, comp_code):
    """Calcule la matrice de probabilités de Poisson exacte"""
    standings, avg_goals = get_league_standings(comp_code)
    
    # Récupération des forces réelles (ou valeurs par défaut pondérées)
    h_att = standings.get(home_team, {}).get("att", 1.15)
    h_def = standings.get(home_team, {}).get("def", 0.90)
    a_att = standings.get(away_team, {}).get("att", 1.05)
    a_def = standings.get(away_team, {}).get("def", 1.10)
    
    # Expected Goals (xG)
    h_xg = max(0.4, h_att * a_def * avg_goals * 1.10) # Avantage domicile +10%
    a_xg = max(0.3, a_att * h_def * avg_goals * 0.90)
    
    # Matrice de Poisson (Scores de 0 à 5)
    max_goals = 6
    p_matrix = np.zeros((max_goals, max_goals))
    for i in range(max_goals):
        for j in range(max_goals):
            p_matrix[i, j] = poisson.pmf(i, h_xg) * poisson.pmf(j, a_xg)
            
    p_h = np.sum(np.triu(p_matrix, 1).T) * 100  # Victoire Domicile
    p_n = np.sum(np.diag(p_matrix)) * 100       # Nul
    p_a = np.sum(np.tril(p_matrix, -1)) * 100   # Victoire Extérieur
    
    p_1x = p_h + p_n
    p_x2 = p_a + p_n
    p_12 = p_h + p_a
    
    # Over / Under / BTTS
    total_goals_grid = np.add.outer(np.arange(max_goals), np.arange(max_goals))
    p_o15 = np.sum(p_matrix[total_goals_grid > 1]) * 100
    p_o25 = np.sum(p_matrix[total_goals_grid > 2]) * 100
    
    # BTTS (Both Teams To Score)
    p_btts = np.sum(p_matrix[1:, 1:]) * 100
    
    # Identification du pari le plus sûr
    options = [
        ("1X (Double Chance)", round(p_1x, 1)),
        ("X2 (Double Chance)", round(p_x2, 1)),
        ("Plus de 1.5 Buts", round(p_o15, 1)),
        ("Plus de 2.5 Buts", round(p_o25, 1)),
        ("Les 2 Équipes Marquent", round(p_btts, 1)),
        ("Victoire Domicile (1)", round(p_h, 1)),
        ("Victoire Extérieur (2)", round(p_a, 1))
    ]
    
    # Tri par niveau de confiance
    best_option = max(options, key=lambda x: x[1])
    
    return {
        "h_xg": round(h_xg, 2),
        "a_xg": round(a_xg, 2),
        "p_h": round(p_h, 1),
        "p_n": round(p_n, 1),
        "p_a": round(p_a, 1),
        "advice": best_option[0],
        "conf": best_option[1]
    }

# ==========================================
# 4. RÉCUPÉRATION DES MATCHS DU FLUX
# ==========================================
@st.cache_data(ttl=300, show_spinner="Analyse statistique avancée des matchs...")
def get_all_upcoming_matches():
    now = datetime.now(timezone.utc)
    date_from = now.strftime("%Y-%m-%d")
    date_to = (now + timedelta(days=10)).strftime("%Y-%m-%d")
    
    endpoint = f"matches?dateFrom={date_from}&dateTo={date_to}"
    raw_data = fetch_api(endpoint)
    
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
            
            dt_obj = datetime.strptime(date_raw, "%Y-%m-%d")
            formatted_date = dt_obj.strftime("%d/%m/%Y")
            
            q = compute_quant_predictions(h_team, a_team, comp_code)
            
            predictions.append({
                "league": league_name,
                "comp_code": comp_code,
                "date_raw": date_raw,
                "date_formatted": formatted_date,
                "time": time_raw,
                "match": f"{h_team} vs {a_team}",
                "advice": q["advice"],
                "conf": q["conf"],
                "xg": f"{q['h_xg']} - {q['a_xg']}",
                "probs": f"1:{q['p_h']}% | X:{q['p_n']}% | 2:{q['p_a']}%"
            })
            
    return sorted(predictions, key=lambda x: x["conf"], reverse=True)

# Charger les données
all_predictions = get_all_upcoming_matches()

# ==========================================
# 5. SIDEBAR : FILTRE PAR LIGUES
# ==========================================
st.sidebar.title("🏆 Choix du Championnat")

available_leagues = sorted(list(set(item['league'] for item in all_predictions)))
league_options = ["Toutes les ligues (Global)"] + available_leagues

selected_league = st.sidebar.selectbox(
    "Sélectionnez la compétition :",
    options=league_options,
    index=0
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Actualiser les Prédictions"):
    st.cache_data.clear()
    st.rerun()

# Filtrage par ligue
if selected_league == "Toutes les ligues (Global)":
    filtered_predictions = all_predictions
else:
    filtered_predictions = [p for p in all_predictions if p['league'] == selected_league]

# ==========================================
# 6. AFFICHAGE PRINCIPAL
# ==========================================
st.markdown(f"""
<div class="hero-header">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span class="badge-gold">QUANT ENGINE v25.5 • STATISTIQUES POISSON</span>
            <h1 style="color:#FFF; margin:10px 0 0 0; font-weight:800; font-size:1.8rem;">{selected_league}</h1>
            <p style="color:#94A3B8; margin:5px 0 0 0; font-size:0.9rem;">Calculateur Poisson basé sur les xG et l'historique d'efficacité offensive/défensive.</p>
        </div>
        <div style="text-align:right;">
            <span class="badge-blue">{len(filtered_predictions)} Matchs Analysés</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

t_coupons, t_cal = st.tabs([
    "🎟️ Coupons à Forte Probabilité Mathématique",
    "📊 Analyse Détaillée & Matrice Poisson"
])

# ------------------------------------------
# TAB 1 : COUPONS HAUTE FIABILITÉ
# ------------------------------------------
with t_coupons:
    if filtered_predictions:
        dates_in_league = sorted(list(set(p['date_raw'] for p in filtered_predictions)))
        
        c_filter, _ = st.columns([1, 2])
        with c_filter:
            selected_date = st.selectbox(
                "Filtrer par date de match :",
                options=["Toutes les dates"] + [datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y") for d in dates_in_league]
            )
        
        if selected_date != "Toutes les dates":
            raw_sel_date = datetime.strptime(selected_date, "%d/%m/%Y").strftime("%Y-%m-%d")
            coupon_predictions = [p for p in filtered_predictions if p['date_raw'] == raw_sel_date]
        else:
            coupon_predictions = filtered_predictions

        if len(coupon_predictions) >= 3:
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("""
                <div class="coupon-card-v1">
                    <span class="badge-gold">COUPON #1 • MAX PROBABILITÉ (>75%)</span>
                    <hr style="border-color:rgba(16, 185, 129, 0.2); margin:15px 0;">
                """, unsafe_allow_html=True)
                
                c1_matches = coupon_predictions[:5]
                conf_c1 = 1.0
                for idx, item in enumerate(c1_matches, 1):
                    conf_c1 *= (item['conf'] / 100.0)
                    st.markdown(f"""
                    <div class="match-row-item">
                        <div style="display:flex; justify-content:space-between;">
                            <div>
                                <span class="league-pill">{item['league']}</span> • <span style="font-size:0.75rem; color:#94A3B8;">{item['date_formatted']} {item['time']}</span>
                                <div style="font-weight:700; color:#F8FAFC; margin-top:4px;">{idx}. {item['match']}</div>
                                <div style="font-size:0.72rem; color:#64748B;">xG prévu : {item['xg']}</div>
                            </div>
                            <div style="text-align:right;">
                                <span style="color:#10B981; font-weight:800;">{item['advice']}</span>
                                <div style="font-size:0.8rem; color:#F59E0B; font-weight:700;">{item['conf']}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown(f"<b>Fiabilité Cumulée Théorique : {round(conf_c1*100, 1)}%</b></div>", unsafe_allow_html=True)

            with c2:
                st.markdown("""
                <div class="coupon-card-v2">
                    <span class="badge-blue">COUPON #2 • VALEUR ÉQUILIBRÉE</span>
                    <hr style="border-color:rgba(59, 130, 246, 0.2); margin:15px 0;">
                """, unsafe_allow_html=True)
                
                c2_matches = coupon_predictions[5:10] if len(coupon_predictions) >= 8 else coupon_predictions[:5]
                conf_c2 = 1.0
                for idx, item in enumerate(c2_matches, 1):
                    conf_c2 *= (item['conf'] / 100.0)
                    st.markdown(f"""
                    <div class="match-row-item-blue">
                        <div style="display:flex; justify-content:space-between;">
                            <div>
                                <span class="league-pill">{item['league']}</span> • <span style="font-size:0.75rem; color:#94A3B8;">{item['date_formatted']} {item['time']}</span>
                                <div style="font-weight:700; color:#F8FAFC; margin-top:4px;">{idx}. {item['match']}</div>
                                <div style="font-size:0.72rem; color:#64748B;">xG prévu : {item['xg']}</div>
                            </div>
                            <div style="text-align:right;">
                                <span style="color:#38BDF8; font-weight:800;">{item['advice']}</span>
                                <div style="font-size:0.8rem; color:#38BDF8; font-weight:700;">{item['conf']}%</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown(f"<b>Fiabilité Cumulée Théorique : {round(conf_c2*100, 1)}%</b></div>", unsafe_allow_html=True)
        else:
            st.info(f"Seulement {len(coupon_predictions)} match(s) disponible(s) pour la sélection. Essayez de sélectionner 'Toutes les ligues' à gauche pour générer un coupon combiné.")
            st.dataframe(pd.DataFrame(coupon_predictions)[['date_formatted', 'time', 'league', 'match', 'advice', 'conf', 'probs']], use_container_width=True)
    else:
        st.warning("Aucun match trouvé pour ce championnat dans les prochains jours.")

# ------------------------------------------
# TAB 2 : CALENDRIER & MATRICE
# ------------------------------------------
with t_cal:
    st.subheader(f"📅 Tableau Analytique Quantitatif : {selected_league}")
    if filtered_predictions:
        grid = []
        for m in sorted(filtered_predictions, key=lambda x: (x['date_raw'], x['time'])):
            grid.append({
                "🗓️ Date & Heure": f"{m['date_formatted']} {m['time']}",
                "🏆 Championnat": m['league'],
                "⚔️ Match": m['match'],
                "⚽ xG Attendu": m['xg'],
                "📊 Probas (1-X-2)": m['probs'],
                "💡 Conseil Sécurité": m['advice'],
                "📈 Indice de Confiance": f"{m['conf']}%"
            })
        st.dataframe(pd.DataFrame(grid), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune rencontre programmée à court terme pour cette sélection.")
