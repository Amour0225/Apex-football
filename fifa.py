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

# CSS Personnalisé
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .card-corners {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #28A745;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .card-cards {
        background-color: #FFFFFF;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #FFC107;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .winner-box {
        background-color: #E8F4FF;
        border: 1px solid #B8DAFF;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
        color: #004085;
        margin-bottom: 20px;
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

st.title("⚡ Apex Intelligence Engine v2.1")
st.caption("Moteur dynamique d'analyse tactique et prédictions personnalisées")

# Sélection du Championnat
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

# Récupération du classement pour statistiques réelles
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

# Récupération des matchs
matches_data = fetch_data(f"competitions/{league_code}/matches?status=SCHEDULED,LIVE")

if matches_data and matches_data.get("matches"):
    match_list = matches_data["matches"]
    
    # Construction de la liste déroulante avec état LIVE / Programmé
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

    # Calcul dynamique des xG réels basés sur les données d'équipe
    h_stat = teams_stats.get(home_id, {"avg_gf": 1.4, "avg_ga": 1.1})
    a_stat = teams_stats.get(away_id, {"avg_gf": 1.2, "avg_ga": 1.3})

    home_xg = max(0.4, (h_stat["avg_gf"] * 0.6 + a_stat["avg_ga"] * 0.4) * 1.15)
    away_xg = max(0.3, (a_stat["avg_gf"] * 0.6 + h_stat["avg_ga"] * 0.4) * 0.85)

    st.divider()

    # En-tête des Équipes
    col_h, col_vs, col_a = st.columns([4, 2, 4])
    with col_h:
        st.subheader(f"🏠 {home_team['name']}")
        st.caption(f"Buts marqués (Moy) : {h_stat['avg_gf']:.2f} / match")
    with col_vs:
        if is_live:
            st.markdown("<h3 style='text-align: center; color: red;'>🔴 EN DIRECT</h3>", unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='text-align: center;'>VS</h3>", unsafe_allow_html=True)
    with col_a:
        st.subheader(f"✈️ {away_team['name']}")
        st.caption(f"Buts marqués (Moy) : {a_stat['avg_gf']:.2f} / match")

    # Calcul des Probabilités (Poisson)
    max_goals = 6
    matrix = np.zeros((max_goals, max_goals))
    for i in range(max_goals):
        for j in range(max_goals):
            matrix[i, j] = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)

    prob_home = float(np.sum(np.tril(matrix, -1)) * 100)
    prob_draw = float(np.sum(np.diag(matrix)) * 100)
    prob_away = float(np.sum(np.triu(matrix, 1)) * 100)

    # Détermination du Vainqueur Prédictif
    if prob_home > prob_away and prob_home > prob_draw:
        predicted_winner = f"Victoire de {home_team['name']}"
        win_confidence = prob_home
    elif prob_away > prob_home and prob_away > prob_draw:
        predicted_winner = f"Victoire de {away_team['name']}"
        win_confidence = prob_away
    else:
        predicted_winner = "Match Nul"
        win_confidence = prob_draw

    # Affichage clair du Vainqueur
    st.markdown(f"""
    <div class="winner-box">
        🏆 Pronostic Principal : <u>{predicted_winner}</u> (Confiance : {win_confidence:.1f}%)
    </div>
    """, unsafe_allow_html=True)

    # Grille 1N2
    st.markdown("### 📊 Probabilités Détaillées (1N2)")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Victoire {home_team['name']}", f"{prob_home:.1f}%", f"Cote théo: {100/prob_home:.2f}" if prob_home > 0 else "-")
    c2.metric("Match Nul", f"{prob_draw:.1f}%", f"Cote théo: {100/prob_draw:.2f}" if prob_draw > 0 else "-")
    c3.metric(f"Victoire {away_team['name']}", f"{prob_away:.1f}%", f"Cote théo: {100/prob_away:.2f}" if prob_away > 0 else "-")

    st.divider()

    # Sections Distinctes : Corners & Cartons
    col_corners, col_cards = st.columns(2)

    est_corners = round((home_xg + away_xg) * 3.4 + 2.8, 1)
    est_cards = round((home_xg + away_xg) * 1.6 + 1.2, 1)

    with col_corners:
        st.markdown("""
        <div class="card-corners">
            <h4>🚩 Section Corners</h4>
            <p>Estimation basée sur la pression d'attaque accumulée.</p>
        </div>
        """, unsafe_allow_html=True)
        st.metric("Total Corners Estimé", f"~{est_corners}")
        st.write(f"**Ligne Suggérée :** Over {round(est_corners - 0.5, 1)} Corners")
        st.progress(min(100, int((est_corners / 14) * 100)))

    with col_cards:
        st.markdown("""
        <div class="card-cards">
            <h4>🟨 Section Cartons Jaunes</h4>
            <p>Estimation basée sur l'intensité et les fautes tactiques.</p>
        </div>
        """, unsafe_allow_html=True)
        st.metric("Total Cartons Estimé", f"~{est_cards}")
        st.write(f"**Ligne Suggérée :** Over {round(est_cards - 0.5, 1)} Cartons")
        st.progress(min(100, int((est_cards / 8) * 100)))

else:
    st.warning("Aucun match disponible pour ce championnat actuellement.")
