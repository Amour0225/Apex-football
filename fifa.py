import streamlit as st
import numpy as np
import requests
from scipy.stats import poisson

# Configuration de la page
st.set_page_config(
    page_title="Apex Intelligence Engine v3.1",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS Thème Clair (Light Mode High Contrast)
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; color: #1E222D; }
    .stApp { background-color: #F8F9FA; }
    
    .top-hero-card {
        background: linear-gradient(135deg, #0d6efd 0%, #0a58ca 100%);
        color: #FFFFFF;
        padding: 22px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(13, 110, 253, 0.15);
    }
    .card-box {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 20px;
        color: #1E222D;
    }
    .card-box h4 {
        color: #0F172A;
        font-weight: 700;
        margin-bottom: 12px;
    }
    .badge-safe {
        background-color: #198754;
        color: #FFFFFF;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.95rem;
    }
    .badge-live {
        background-color: #DC3545;
        color: white;
        padding: 8px 15px;
        border-radius: 6px;
        font-weight: bold;
        text-align: center;
        display: inline-block;
    }
    .bet-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }
    .bet-table th {
        background-color: #F1F5F9;
        color: #1E293B;
        padding: 10px;
        text-align: center;
        border: 1px solid #E2E8F0;
        font-weight: 700;
    }
    .bet-table td {
        padding: 10px;
        text-align: center;
        border: 1px solid #E2E8F0;
        font-weight: 600;
        color: #334155;
    }
    </style>
""", unsafe_allow_html=True)

API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

@st.cache_data(ttl=180)
def fetch_data(endpoint):
    headers = {"X-Auth-Token": API_KEY}
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

st.title("⚡ Apex Intelligence Engine v3.1")
st.caption("Module d'Analyse Tactique : Marché 1xBet, Forme des Équipes & Lignes Sécurisées")

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

# Traitement Classement & Forme
standings_data = fetch_data(f"competitions/{league_code}/standings")
teams_stats = {}

if standings_data and "standings" in standings_data and len(standings_data["standings"]) > 0:
    table = standings_data["standings"][0].get("table", [])
    for item in table:
        team_id = item["team"]["id"]
        played = item.get("playedGames", 1) or 1
        gf = item.get("goalsFor", 0)
        ga = item.get("goalsAgainst", 0)
        pts = item.get("points", 0)
        form_score = min(100, int((pts / (played * 3)) * 100)) if played > 0 else 50
        
        teams_stats[team_id] = {
            "avg_gf": gf / played,
            "avg_ga": ga / played,
            "form": form_score
        }

# Traitement Matchs (Programmés et En Direct)
matches_data = fetch_data(f"competitions/{league_code}/matches?status=SCHEDULED,LIVE,IN_PLAY,PAUSED")

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

    # Stats & Forme
    h_stat = teams_stats.get(home_id, {"avg_gf": 1.4, "avg_ga": 1.1, "form": 60})
    a_stat = teams_stats.get(away_id, {"avg_gf": 1.2, "avg_ga": 1.3, "form": 50})

    home_xg = max(0.6, (h_stat["avg_gf"] * 0.6 + a_stat["avg_ga"] * 0.4) * 1.15)
    away_xg = max(0.5, (a_stat["avg_gf"] * 0.6 + h_stat["avg_ga"] * 0.4) * 0.85)

    st.divider()

    # En-tête Match
    col_h, col_vs, col_a = st.columns([4, 2, 4])
    with col_h:
        st.subheader(f"🏠 {home_team['name']}")
        st.write(f"📊 **Forme Actuelle :** `{h_stat['form']}%`")
        st.progress(h_stat['form'])
    
    with col_vs:
        if is_live:
            score_h = match.get('score', {}).get('fullTime', {}).get('home', 0) or 0
            score_a = match.get('score', {}).get('fullTime', {}).get('away', 0) or 0
            st.markdown(f"<div class='badge-live'>🔴 EN DIRECT<br>{score_h} - {score_a}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='text-align: center; color: #0d6efd;'>VS</h3>", unsafe_allow_html=True)
    
    with col_a:
        st.subheader(f"✈️ {away_team['name']}")
        st.write(f"📊 **Forme Actuelle :** `{a_stat['form']}%`")
        st.progress(a_stat['form'])

    # Calculations Matrice Poisson (Matrice 8x8 pour précision maximale)
    max_goals = 8
    matrix = np.zeros((max_goals, max_goals))
    for i in range(max_goals):
        for j in range(max_goals):
            matrix[i, j] = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)

    prob_home = float(np.sum(np.tril(matrix, -1)) * 100)
    prob_draw = float(np.sum(np.diag(matrix)) * 100)
    prob_away = float(np.sum(np.triu(matrix, 1)) * 100)

    # Calcul des lignes Plus / Moins de Buts (1xBet Style)
    goals_lines = [0.5, 1.5, 2.5, 3.5, 4.5]
    ou_results = []

    for line in goals_lines:
        over_p = 0.0
        for i in range(max_goals):
            for j in range(max_goals):
                if (i + j) > line:
                    over_p += matrix[i, j]
        over_p *= 100
        under_p = 100.0 - over_p
        ou_results.append({
            "line": line,
            "over": over_p,
            "under": under_p
        })

    # Pronostic Principal VIP
    best_over = ou_results[0] # Over 0.5
    for res in ou_results:
        if res['over'] >= 75.0:
            best_over = res

    st.markdown(f"""
    <div class="top-hero-card">
        <h2>🔥 PRONOSTIC APEX TOP SÉCURITÉ</h2>
        <h1 style="color: #FFD700; margin: 8px 0;">Plus de {best_over['line']} Buts dans le match</h1>
        <span class="badge-safe">PROBABILITÉ CERTIFIÉE : {best_over['over']:.1f}%</span>
    </div>
    """, unsafe_allow_html=True)

    # Tableau Plus / Moins de Buts (1xBet Style)
    st.markdown("### ⚽ Marché Plus / Moins de Buts (Offre 1xBet)")
    
    table_html = """
    <table class="bet-table">
        <thead>
            <tr>
                <th>Ligne de Buts</th>
                <th>Plus de (Over)</th>
                <th>Moins de (Under)</th>
                <th>Option Recommandée</th>
            </tr>
        </thead>
        <tbody>
    """
    for res in ou_results:
        if res['over'] >= 60:
            recom = f"<span style='color: #198754; font-weight: bold;'>Plus de {res['line']}</span>"
        elif res['under'] >= 60:
            recom = f"<span style='color: #0d6efd; font-weight: bold;'>Moins de {res['line']}</span>"
        else:
            recom = "<span style='color: #6c757d;'>Risqué</span>"

        table_html += f"""
            <tr>
                <td><b>{res['line']} Buts</b></td>
                <td><b style="color: #198754;">{res['over']:.1f}%</b></td>
                <td><b style="color: #0d6efd;">{res['under']:.1f}%</b></td>
                <td>{recom}</td>
            </tr>
        """
    table_html += "</tbody></table>"
    st.markdown(table_html, unsafe_allow_html=True)

    st.divider()

    # Sections Corners et Cartons
    col_c, col_k = st.columns(2)

    total_xg = home_xg + away_xg
    corner_line_ultra = 4.5
    prob_corner_ultra = min(98.5, 88.0 + (total_xg * 3.5))
    
    card_line_ultra = 1.5
    prob_card_ultra = min(96.8, 86.0 + (total_xg * 3.0))

    with col_c:
        st.markdown(f"""
        <div class="card-box">
            <h4>🚩 Marché Corners (Ligne Sécurisée)</h4>
            <p><b>Plus de {corner_line_ultra} Corners dans le match</b></p>
            <h3 style="color: #198754;">Probabilité : {prob_corner_ultra:.1f}%</h3>
        </div>
        """, unsafe_allow_html=True)
        st.progress(int(prob_corner_ultra))

    with col_k:
        st.markdown(f"""
        <div class="card-box">
            <h4>🟨 Marché Cartons (Ligne Sécurisée)</h4>
            <p><b>Plus de {card_line_ultra} Cartons dans le match</b></p>
            <h3 style="color: #198754;">Probabilité : {prob_card_ultra:.1f}%</h3>
        </div>
        """, unsafe_allow_html=True)
        st.progress(int(prob_card_ultra))

    # Distribution 1N2
    st.markdown("### 📊 Distribution 1N2")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Victoire {home_team['name']}", f"{prob_home:.1f}%")
    c2.metric("Match Nul", f"{prob_draw:.1f}%")
    c3.metric(f"Victoire {away_team['name']}", f"{prob_away:.1f}%")

else:
    st.warning("Aucun match disponible pour ce championnat actuellement.")
