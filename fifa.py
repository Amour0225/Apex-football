import streamlit as st
import numpy as np
import requests
from scipy.stats import poisson

# Configuration de la page
st.set_page_config(
    page_title="Apex Intelligence Engine v4.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS Pro Dashboard (Light High-Contrast Premium)
st.markdown("""
    <style>
    /* Fond global et typographie */
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Hero Banner */
    .hero-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #FFFFFF;
        padding: 24px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.2);
        border: 1px solid #334155;
    }
    
    /* Cartes de sections */
    .pro-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    /* Cartes de scores exacts */
    .score-badge {
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        color: #0F172A;
    }
    
    /* Badges de statut */
    .badge-live {
        background-color: #EF4444;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    .badge-vip {
        background-color: #10B981;
        color: #FFFFFF;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 0.95rem;
        display: inline-block;
    }
    
    /* Lignes de marché */
    .market-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 14px;
        background-color: #F8FAFC;
        border-radius: 8px;
        margin-bottom: 8px;
        border: 1px solid #E2E8F0;
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

st.title("⚡ Apex Intelligence Engine v4.0")
st.caption("Plateforme d'Analyse Prédictive & Dashboard Analytics Professionnel")

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

# Traitement Matchs
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

    # En-tête Match & Forme
    col_h, col_vs, col_a = st.columns([4, 2, 4])
    with col_h:
        st.subheader(f"🏠 {home_team['name']}")
        st.write(f"📊 **Indice de Forme :** `{h_stat['form']}%`")
        st.progress(h_stat['form'])
    
    with col_vs:
        if is_live:
            score_h = match.get('score', {}).get('fullTime', {}).get('home', 0) or 0
            score_a = match.get('score', {}).get('fullTime', {}).get('away', 0) or 0
            st.markdown(f"<div class='badge-live'>🔴 EN DIRECT<br>{score_h} - {score_a}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='text-align: center; color: #0F172A;'>VS</h3>", unsafe_allow_html=True)
    
    with col_a:
        st.subheader(f"✈️ {away_team['name']}")
        st.write(f"📊 **Indice de Forme :** `{a_stat['form']}%`")
        st.progress(a_stat['form'])

    # Calcul Matrice Poisson (8x8)
    max_goals = 8
    matrix = np.zeros((max_goals, max_goals))
    for i in range(max_goals):
        for j in range(max_goals):
            matrix[i, j] = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)

    prob_home = float(np.sum(np.tril(matrix, -1)) * 100)
    prob_draw = float(np.sum(np.diag(matrix)) * 100)
    prob_away = float(np.sum(np.triu(matrix, 1)) * 100)

    # Identification Équipe Favorite & Buts Favori
    if prob_home >= prob_away:
        fav_name = home_team['name']
        fav_xg = home_xg
        fav_icon = "🏠"
    else:
        fav_name = away_team['name']
        fav_xg = away_xg
        fav_icon = "✈️"

    fav_over_05 = (1 - poisson.pmf(0, fav_xg)) * 100
    fav_over_15 = (1 - (poisson.pmf(0, fav_xg) + poisson.pmf(1, fav_xg))) * 100
    fav_over_25 = (1 - sum(poisson.pmf(k, fav_xg) for k in range(3))) * 100

    # Top 3 Scores Exacts
    scores_list = []
    for i in range(5):
        for j in range(5):
            scores_list.append((i, j, matrix[i, j] * 100))
    scores_list.sort(key=lambda x: x[2], reverse=True)
    top_3_scores = scores_list[:3]

    # Pronostic Principal VIP
    prob_over_15_total = (1 - (matrix[0,0] + matrix[1,0] + matrix[0,1])) * 100
    
    st.markdown(f"""
    <div class="hero-card">
        <span class="badge-vip">🎯 CONSEIL APEX VIP</span>
        <h1 style="color: #38BDF8; margin: 12px 0 6px 0;">Plus de 1.5 Buts dans le match</h1>
        <p style="color: #94A3B8; margin: 0;">Niveau de confiance calculé : <b>{prob_over_15_total:.1f}%</b></p>
    </div>
    """, unsafe_allow_html=True)

    # Section 1 : Top 3 Scores Exacts & Favori
    col_sc, col_fav = st.columns(2)

    with col_sc:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("### 🎲 Top 3 Scores Exacts Probables")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f"""
            <div class="score-badge">
                <div style="font-size: 1.2rem; color: #2563EB;">{top_3_scores[0][0]} - {top_3_scores[0][1]}</div>
                <div style="font-size: 0.85rem; color: #64748B;">Prob: {top_3_scores[0][2]:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with sc2:
            st.markdown(f"""
            <div class="score-badge">
                <div style="font-size: 1.2rem; color: #2563EB;">{top_3_scores[1][0]} - {top_3_scores[1][1]}</div>
                <div style="font-size: 0.85rem; color: #64748B;">Prob: {top_3_scores[1][2]:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with sc3:
            st.markdown(f"""
            <div class="score-badge">
                <div style="font-size: 1.2rem; color: #2563EB;">{top_3_scores[2][0]} - {top_3_scores[2][1]}</div>
                <div style="font-size: 0.85rem; color: #64748B;">Prob: {top_3_scores[2][2]:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_fav:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown(f"### ⭐ Performance Favori : {fav_icon} {fav_name}")
        st.write(f"**Plus de 0.5 But de {fav_name} :** `{fav_over_05:.1f}%`")
        st.progress(int(fav_over_05))
        st.write(f"**Plus de 1.5 Buts de {fav_name} :** `{fav_over_15:.1f}%`")
        st.progress(int(fav_over_15))
        st.markdown('</div>', unsafe_allow_html=True)

    # Section 2 : Marché Buts Total (Pro Display)
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### ⚽ Marché Total Buts (Pro Display)")
    
    goals_lines = [0.5, 1.5, 2.5, 3.5]
    for line in goals_lines:
        over_p = 0.0
        for i in range(max_goals):
            for j in range(max_goals):
                if (i + j) > line:
                    over_p += matrix[i, j]
        over_p *= 100
        under_p = 100.0 - over_p
        
        st.markdown(f"""
        <div class="market-row">
            <span><b>Ligne {line} Buts</b></span>
            <span>Plus de {line} : <b style="color: #059669;">{over_p:.1f}%</b></span>
            <span>Moins de {line} : <b style="color: #2563EB;">{under_p:.1f}%</b></span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Section 3 : Corners, Cartons & 1N2
    col_c, col_k = st.columns(2)

    total_xg = home_xg + away_xg
    corner_line_ultra = 4.5
    prob_corner_ultra = min(98.5, 88.0 + (total_xg * 3.5))
    card_line_ultra = 1.5
    prob_card_ultra = min(96.8, 86.0 + (total_xg * 3.0))

    with col_c:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("#### 🚩 Corners (Ligne Sécurisée)")
        st.write(f"**Plus de {corner_line_ultra} Corners dans le match**")
        st.markdown(f"<h3 style='color: #059669; margin: 0;'>{prob_corner_ultra:.1f}%</h3>", unsafe_allow_html=True)
        st.progress(int(prob_corner_ultra))
        st.markdown('</div>', unsafe_allow_html=True)

    with col_k:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("#### 🟨 Cartons (Ligne Sécurisée)")
        st.write(f"**Plus de {card_line_ultra} Cartons dans le match**")
        st.markdown(f"<h3 style='color: #059669; margin: 0;'>{prob_card_ultra:.1f}%</h3>", unsafe_allow_html=True)
        st.progress(int(prob_card_ultra))
        st.markdown('</div>', unsafe_allow_html=True)

    # Distribution 1N2
    st.markdown("### 📊 Distribution 1N2")
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Victoire {home_team['name']}", f"{prob_home:.1f}%")
    c2.metric("Match Nul", f"{prob_draw:.1f}%")
    c3.metric(f"Victoire {away_team['name']}", f"{prob_away:.1f}%")

else:
    st.warning("Aucun match disponible pour ce championnat actuellement.")
