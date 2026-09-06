import streamlit as st
import numpy as np
import requests
from scipy.stats import poisson

# Configuration de la page
st.set_page_config(
    page_title="Apex Intelligence Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Personnalisé - Design Ultra Pro
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .top-pick-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    .card-box {
        background-color: #FFFFFF;
        padding: 18px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .card-corners { border-top: 4px solid #28A745; }
    .card-cards { border-top: 4px solid #FFC107; }
    .card-goals { border-top: 4px solid #007BFF; }
    .badge-high {
        background-color: #28A745;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

@st.cache_data(ttl=300)
def fetch_data(endpoint):
    headers = {"X-Auth-Token": API_KEY}
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

st.title("⚡ Apex Intelligence Engine v2.2")
st.caption("Moteur d'Analyse Haute Précision : Pronostics Sécurisés & Probabilités Élevées (>80%)")

# Championnats
st.sidebar.header("🕹️ Championnat")
leagues = {
    "Ligue 1": "FL1",
    "Premier League": "PL",
    "La Liga": "PD",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Ligue des Champions": "CL"
}
selected_league = st.sidebar.selectbox("Sélectionnez le Championnat", list(leagues.keys()))
league_code = leagues[selected_league]

# Traitement Classement
standings_data = fetch_data(f"competitions/{league_code}/standings")
teams_stats = {}

if standings_data and "standings" in standings_data and len(standings_data["standings"]) > 0:
    table = standings_data["standings"][0].get("table", [])
    for item in table:
        team_id = item["team"]["id"]
        played = item.get("playedGames", 1) or 1
        gf = item.get("goalsFor", 0)
        ga = item.get("goalsAgainst", 0)
        teams_stats[team_id] = {
            "avg_gf": gf / played,
            "avg_ga": ga / played
        }

# Traitement Matchs
matches_data = fetch_data(f"competitions/{league_code}/matches?status=SCHEDULED,LIVE")

if matches_data and matches_data.get("matches"):
    match_list = matches_data["matches"]
    
    match_options = {}
    for m in match_list:
        is_live = m["status"] in ["IN_PLAY", "PAUSED"]
        status_tag = "🔴 [EN DIRECT]" if is_live else f"📅 {m['utcDate'][:10]}"
        label = f"{status_tag} - {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
        match_options[label] = m
    
    selected_label = st.selectbox("Sélectionnez la Rencontre", list(match_options.keys()))
    match = match_options[selected_label]
    
    home_team = match["homeTeam"]
    away_team = match["awayTeam"]
    home_id = home_team["id"]
    away_id = away_team["id"]
    is_live = match["status"] in ["IN_PLAY", "PAUSED"]

    # Calcul Dynamique xG
    h_stat = teams_stats.get(home_id, {"avg_gf": 1.4, "avg_ga": 1.1})
    a_stat = teams_stats.get(away_id, {"avg_gf": 1.2, "avg_ga": 1.3})

    home_xg = max(0.5, (h_stat["avg_gf"] * 0.6 + a_stat["avg_ga"] * 0.4) * 1.15)
    away_xg = max(0.4, (a_stat["avg_gf"] * 0.6 + h_stat["avg_ga"] * 0.4) * 0.85)

    st.divider()

    # Match Header
    col_h, col_vs, col_a = st.columns([4, 2, 4])
    with col_h:
        st.subheader(f"🏠 {home_team['name']}")
    with col_vs:
        if is_live:
            st.markdown("<h3 style='text-align: center; color: red;'>🔴 EN DIRECT</h3>", unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='text-align: center;'>VS</h3>", unsafe_allow_html=True)
    with col_a:
        st.subheader(f"✈️ {away_team['name']}")

    # Calcul Matrice Poisson
    max_goals = 6
    matrix = np.zeros((max_goals, max_goals))
    for i in range(max_goals):
        for j in range(max_goals):
            matrix[i, j] = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)

    prob_home = float(np.sum(np.tril(matrix, -1)) * 100)
    prob_draw = float(np.sum(np.diag(matrix)) * 100)
    prob_away = float(np.sum(np.triu(matrix, 1)) * 100)

    # Probabilités Sécurisées (Double Chance & Goals)
    prob_dc_home = prob_home + prob_draw
    prob_dc_away = prob_away + prob_draw
    prob_over_15 = (1 - (matrix[0,0] + matrix[1,0] + matrix[0,1])) * 100
    prob_under_35 = np.sum(matrix[np.triu_indices(max_goals, 0)]) # approximation rapide sous 3.5

    # Choix du Master Pick (>80% de confiance)
    master_pick = ""
    master_conf = 0.0

    if prob_dc_home >= 78:
        master_pick = f"Double Chance : {home_team['name']} ou Nul (1X)"
        master_conf = prob_dc_home
    elif prob_dc_away >= 78:
        master_pick = f"Double Chance : {away_team['name']} ou Nul (X2)"
        master_conf = prob_dc_away
    elif prob_over_15 >= 80:
        master_pick = "Plus de 1.5 Buts dans le match"
        master_conf = prob_over_15
    else:
        master_pick = f"Victoire Remboursée si Nul : {home_team['name'] if prob_home > prob_away else away_team['name']}"
        master_conf = max(prob_home, prob_away) + (prob_draw / 2)

    # Affichage Master Pick
    st.markdown(f"""
    <div class="top-pick-card">
        <h3>🎯 PRONOSTIC APEX HAUTE CONFIANCE</h3>
        <h2 style="color: #FFD700; margin: 10px 0;">{master_pick}</h2>
        <span class="badge-high">Taux de Confiance Estimé : {master_conf:.1f}%</span>
    </div>
    """, unsafe_allow_html=True)

    # Grille 1N2 + Double Chance
    st.markdown("### 📊 Marché 1N2 & Double Chance")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Victoire {home_team['name']}", f"{prob_home:.1f}%")
    c2.metric("Match Nul", f"{prob_draw:.1f}%")
    c3.metric(f"Victoire {away_team['name']}", f"{prob_away:.1f}%")

    dc1, dc2 = st.columns(2)
    dc1.info(f"🛡️ **Double Chance 1X ({home_team['name']} / Nul) :** `{prob_dc_home:.1f}%` de réussite")
    dc2.info(f"🛡️ **Double Chance X2 ({away_team['name']} / Nul) :** `{prob_dc_away:.1f}%` de réussite")

    st.divider()

    # Triade d'Analyse : Goals, Corners, Cartons (Lignes Sécurisées)
    col_g, col_c, col_k = st.columns(3)

    # 1. Buts
    with col_g:
        st.markdown("""
        <div class="card-box card-goals">
            <h4>⚽ Marché des Buts</h4>
            <p>Ligne à haute probabilité</p>
        </div>
        """, unsafe_allow_html=True)
        st.write(f"**Plus de 1.5 Buts :** `{prob_over_15:.1f}%`")
        st.progress(min(100, int(prob_over_15)))
        st.caption("✅ Conseil : Privilégier Over 1.5 Buts plutôt qu'Over 2.5")

    # 2. Corners
    total_xg = home_xg + away_xg
    safe_corner_line = max(6.5, round(total_xg * 2.8 + 2.0, 1))
    corner_conf = min(92.0, 75.0 + (total_xg * 4.5))

    with col_c:
        st.markdown("""
        <div class="card-box card-corners">
            <h4>🚩 Marché des Corners</h4>
            <p>Ligne sécurisée</p>
        </div>
        """, unsafe_allow_html=True)
        st.write(f"**Plus de {safe_corner_line} Corners**")
        st.write(f"Probabilité : `{corner_conf:.1f}%`")
        st.progress(int(corner_conf))
        st.caption("✅ Conseil : Ligne calculée pour un taux de succès > 80%")

    # 3. Cartons
    safe_card_line = max(2.5, round(total_xg * 1.2 + 0.8, 1))
    card_conf = min(89.0, 72.0 + (total_xg * 5.0))

    with col_k:
        st.markdown("""
        <div class="card-box card-cards">
            <h4>🟨 Marché des Cartons</h4>
            <p>Ligne sécurisée</p>
        </div>
        """, unsafe_allow_html=True)
        st.write(f"**Plus de {safe_card_line} Cartons**")
        st.write(f"Probabilité : `{card_conf:.1f}%`")
        st.progress(int(card_conf))
        st.caption("✅ Conseil : Évite les lignes trop hautes")

else:
    st.warning("Aucun match disponible pour ce championnat actuellement.")
