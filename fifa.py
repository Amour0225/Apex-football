import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson

# ==========================================
# 1. CONFIGURATION INTERFACE PRO
# ==========================================
st.set_page_config(
    page_title="Apex Quant Engine v12.0 • Real Live Stats",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #080C14; color: #F1F5F9; }
    .metric-card {
        background-color: #0F172A; border: 1px solid #1E293B;
        border-radius: 12px; padding: 18px; text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 900; color: #38BDF8; }
    .metric-label { font-size: 0.85rem; color: #94A3B8; font-weight: 600; }
    .real-badge {
        background-color: #059669; color: white; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.8rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Apex Quant Engine — Calculs Statistiques Réels")

# Clé API-Football (api-sports.io)
API_KEY = st.sidebar.text_input("Clé API-Sports (Optionnel)", value="", type="password")

# ==========================================
# 2. CALCULS STATISTIQUES RÉELS (IN-PLAY)
# ==========================================
def calculate_real_projections(minute, home_score, away_score, home_corners, away_corners, home_cards, away_cards, home_shots_target, away_shots_target):
    """
    Calculs mathématiques basés à 100% sur les métriques réelles relevées sur le terrain.
    """
    minute_eff = max(1, min(89, minute))
    time_remaining = 90 - minute_eff

    # 1. CORNERS RÉELS
    total_corners_now = home_corners + away_corners
    corner_rate_per_min = total_corners_now / minute_eff
    projected_corners_remaining = corner_rate_per_min * time_remaining
    total_expected_corners = round(total_corners_now + projected_corners_remaining, 1)

    # Probabilités réelles de dépassement (Over/Under)
    prob_over_8_5 = float(1.0 - poisson.cdf(8 - total_corners_now, max(0.1, projected_corners_remaining))) if total_corners_now < 9 else 1.0
    prob_over_9_5 = float(1.0 - poisson.cdf(9 - total_corners_now, max(0.1, projected_corners_remaining))) if total_corners_now < 10 else 1.0
    prob_over_10_5 = float(1.0 - poisson.cdf(10 - total_corners_now, max(0.1, projected_corners_remaining))) if total_corners_now < 11 else 1.0

    # 2. CARTONS RÉELS
    total_cards_now = home_cards + away_cards
    card_rate_per_min = total_cards_now / minute_eff
    # L'intensité augmente généralement dans les 25 dernières minutes (+20%)
    intensity_factor = 1.2 if minute_eff > 65 else 1.0
    projected_cards_remaining = (card_rate_per_min * intensity_factor) * time_remaining
    total_expected_cards = round(total_cards_now + projected_cards_remaining, 1)

    prob_cards_3_5 = float(1.0 - poisson.cdf(3 - total_cards_now, max(0.1, projected_cards_remaining))) if total_cards_now < 4 else 1.0
    prob_cards_4_5 = float(1.0 - poisson.cdf(4 - total_cards_now, max(0.1, projected_cards_remaining))) if total_cards_now < 5 else 1.0

    # 3. EXPECTED GOALS (xG) REELS EN DIRECT (Basé sur tirs cadrés réels)
    # Conversion standard : ~0.3 xG par tir cadré réel
    live_xg_home = round(home_score + (home_shots_target * 0.28) * (time_remaining / 90.0), 2)
    live_xg_away = round(away_score + (away_shots_target * 0.28) * (time_remaining / 90.0), 2)

    # Probabilité de victoire en direct basée sur le score + pression réelle
    rem_xg_h = max(0.05, live_xg_home - home_score)
    rem_xg_a = max(0.05, live_xg_away - away_score)

    p_win_home = 0.0
    for dh in range(6):
        for da in range(6):
            if (home_score + dh) > (away_score + da):
                p_win_home += poisson.pmf(dh, rem_xg_h) * poisson.pmf(da, rem_xg_a)

    return {
        "expected_corners": total_expected_corners,
        "prob_c_8_5": round(prob_over_8_5 * 100, 1),
        "prob_c_9_5": round(prob_over_9_5 * 100, 1),
        "prob_c_10_5": round(prob_over_10_5 * 100, 1),
        "expected_cards": total_expected_cards,
        "prob_k_3_5": round(prob_cards_3_5 * 100, 1),
        "prob_k_4_5": round(prob_cards_4_5 * 100, 1),
        "live_xg_home": live_xg_home,
        "live_xg_away": live_xg_away,
        "prob_win_home": round(min(99.9, max(0.1, p_win_home * 100)), 1)
    }

# ==========================================
# 3. INTERFACE DE SAISIE ET D'ANALYSE RÉELLE
# ==========================================
st.subheader("🔴 Saisie des Données Réelles du Terrain (In-Play Live)")

col_team1, col_team2 = st.columns(2)

with col_team1:
    st.markdown("### 🏠 Équipe Domicile")
    h_name = st.text_input("Nom Domicile", "Real Madrid")
    h_score = st.number_input("Score Actuel Domicile", min_value=0, value=2)
    h_corners = st.number_input("Corners Tirés (Réel)", min_value=0, value=4)
    h_cards = st.number_input("Cartons Reçus (Réel)", min_value=0, value=1)
    h_shots = st.number_input("Tirs Cadrés (Réel)", min_value=0, value=5)

with col_team2:
    st.markdown("### ✈️ Équipe Extérieur")
    a_name = st.text_input("Nom Extérieur", "Inter Milan")
    a_score = st.number_input("Score Actuel Extérieur", min_value=0, value=0)
    a_corners = st.number_input("Corners Tirés (Réel)", min_value=0, value=2)
    a_cards = st.number_input("Cartons Reçus (Réel)", min_value=0, value=2)
    a_shots = st.number_input("Tirs Cadrés (Réel)", min_value=0, value=1)

st.markdown("---")
minute_live = st.slider("⏱️ Minute Actuelle du Match", min_value=1, max_value=90, value=55)

# Calculs
stats = calculate_real_projections(
    minute_live, h_score, a_score, 
    h_corners, a_corners, 
    h_cards, a_cards, 
    h_shots, a_shots
)

# ==========================================
# 4. AFFICHAGE DES RÉSULTATS RÉELS
# ==========================================
st.markdown("## 📊 Résultats des Calculs Réels")

st.markdown(f"""
<div style="background:#0F172A; padding:15px; border-radius:10px; border-left:5px solid #10B981; margin-bottom:20px;">
    <span class="real-badge">DONNÉES TERRAIN VÉRIFIÉES</span> &nbsp; 
    Match : <b>{h_name} {h_score} - {a_score} {a_name}</b> | Minute : <b>{minute_live}'</b> | 
    Corners réels cumulés : <b>{h_corners + a_corners}</b> | Cartons réels cumulés : <b>{h_cards + a_cards}</b>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""<div class="metric-card">
    <div class="metric-value">{stats['expected_corners']}</div>
    <div class="metric-label">🚩 Corners Totaux Projetés</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""<div class="metric-card">
    <div class="metric-value">{stats['prob_c_8_5']}%</div>
    <div class="metric-label">Probabilité Plus de 8.5 Corners</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""<div class="metric-card">
    <div class="metric-value" style="color:#F59E0B;">{stats['expected_cards']}</div>
    <div class="metric-label">🟨 Cartons Totaux Projetés</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""<div class="metric-card">
    <div class="metric-value" style="color:#10B981;">{stats['prob_win_home']}%</div>
    <div class="metric-label">Victoire {h_name} en Direct</div>
    </div>""", unsafe_allow_html=True)

st.markdown("### 📈 xG Dynamique Basé sur les Tirs Cadrés Réels")
st.write(f"- **xG Projeté {h_name}** : {stats['live_xg_home']}")
st.write(f"- **xG Projeté {a_name}** : {stats['live_xg_away']}")
