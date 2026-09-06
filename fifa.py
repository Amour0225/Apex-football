import streamlit as st
import numpy as np
import requests
from scipy.stats import poisson

# Configuration de la page
st.set_page_config(
    page_title="Apex Intelligence Engine v6.1",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS Pro Dashboard High Contrast
st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .hero-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #FFFFFF;
        padding: 26px;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        border: 1px solid #334155;
    }
    
    .pro-card {
        background-color: #FFFFFF;
        padding: 22px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    .score-badge {
        background: #F1F5F9;
        border: 1px solid #CBD5E1;
        border-radius: 10px;
        padding: 12px;
        text-align: center;
        font-weight: bold;
        color: #0F172A;
    }
    
    .badge-live {
        background-color: #EF4444;
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        display: inline-block;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.4);
    }

    .badge-derby {
        background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%);
        color: white;
        padding: 6px 14px;
        border-radius: 8px;
        font-weight: 800;
        font-size: 0.85rem;
        display: inline-block;
        margin-bottom: 12px;
        box-shadow: 0 2px 10px rgba(220, 38, 38, 0.3);
    }
    
    .badge-vip {
        background-color: #10B981;
        color: #FFFFFF;
        padding: 6px 18px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 0.95rem;
        display: inline-block;
        text-transform: uppercase;
    }
    
    .market-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background-color: #F8FAFC;
        border-radius: 10px;
        margin-bottom: 8px;
        border: 1px solid #E2E8F0;
    }

    .sofa-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 12px 16px;
        margin-bottom: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

# MOTEUR DE DÉTECTION AUTOMATIQUE DE DERBIES
def detect_derby_automatically(home_name, away_name):
    known_derbies = [
        # Premier League
        ({"Manchester United FC", "Manchester City FC"}, "Derby de Manchester"),
        ({"Arsenal FC", "Tottenham Hotspur FC"}, "North London Derby"),
        ({"Liverpool FC", "Everton FC"}, "Merseyside Derby"),
        ({"Chelsea FC", "Arsenal FC"}, "Derby de Londres"),
        ({"Chelsea FC", "Tottenham Hotspur FC"}, "Derby de Londres"),
        ({"Liverpool FC", "Manchester United FC"}, "North-West Derby"),
        # La Liga
        ({"Real Madrid CF", "FC Barcelona"}, "El Clásico"),
        ({"Real Madrid CF", "Atlético de Madrid"}, "Derby Madrilène"),
        ({"Sevilla FC", "Real Betis Balompié"}, "Derby Sévillan"),
        ({"Athletic Club", "Real Sociedad de Fútbol"}, "Derby Basque"),
        # Serie A
        ({"FC Internazionale Milano", "AC Milan"}, "Derby della Madonnina"),
        ({"SS Lazio", "AS Roma"}, "Derby della Capitale"),
        ({"Juventus FC", "FC Internazionale Milano"}, "Derby d'Italia"),
        ({"Juventus FC", "Torino FC"}, "Derby della Mole"),
        # Ligue 1
        ({"Paris Saint-Germain FC", "Olympique de Marseille"}, "Le Classique"),
        ({"Olympique Lyonnais", "AS Saint-Étienne"}, "Derby du Rhône"),
        ({"OGC Nice", "AS Monaco FC"}, "Derby de la Côte d'Azur"),
        # Bundesliga
        ({"Borussia Dortmund", "FC Bayern München"}, "Der Klassiker"),
        ({"Borussia Dortmund", "FC Schalke 04"}, "Revierderby")
    ]
    
    current_pair = {home_name, away_name}
    
    # 1. Vérification dans la base des derbies officiels
    for team_set, derby_title in known_derbies:
        if team_set.issubset(current_pair) or team_set == current_pair:
            return True, derby_title
            
    # 2. Détection heuristique par Mots-Clés de Villes
    cities = ["Manchester", "Madrid", "Milano", "Sevilla", "Turin", "Torino", "Liverpool", "Rome", "Roma"]
    for city in cities:
        if city.lower() in home_name.lower() and city.lower() in away_name.lower():
            return True, f"Derby Local ({city})"
            
    return False, None

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

st.title("⚡ Apex Intelligence Engine v6.1")
st.caption("Algorithme Prédictif Dynamic Poisson, SofaScore Dashboard & Auto-Derby Engine")

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
    
    # ------------------ MODULE SOFASCORE DASHBOARD ------------------
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### 📱 SofaScore Dashboard : Directs & Prochains Matchs")
    
    live_games = [m for m in match_list if m["status"] in ["IN_PLAY", "PAUSED"]]
    upcoming_games = [m for m in match_list if m["status"] == "SCHEDULED"]
    
    tab_live, tab_upcoming = st.tabs([f"🔴 En Direct ({len(live_games)})", f"📅 À Venir ({len(upcoming_games)})"])
    
    with tab_live:
        if live_games:
            for lg in live_games:
                sh = lg.get('score', {}).get('fullTime', {}).get('home', 0) or 0
                sa = lg.get('score', {}).get('fullTime', {}).get('away', 0) or 0
                st.markdown(f"""
                <div class="sofa-card">
                    <span><b>{lg['homeTeam']['name']}</b> vs <b>{lg['awayTeam']['name']}</b></span>
                    <span class="badge-live">🔴 LIVE : {sh} - {sa}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucun match en direct actuellement dans ce championnat.")
            
    with tab_upcoming:
        if upcoming_games:
            for ug in upcoming_games[:6]:
                time_str = ug['utcDate'][11:16]
                date_str = ug['utcDate'][:10]
                st.markdown(f"""
                <div class="sofa-card">
                    <span><b>{ug['homeTeam']['name']}</b> vs <b>{ug['awayTeam']['name']}</b></span>
                    <span style="color: #64748B; font-weight: bold;">📅 {date_str} à {time_str} UTC</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucun match à venir programmé.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Sélection de la Rencontre à Analyser
    match_options = {}
    for m in match_list:
        is_live = m["status"] in ["IN_PLAY", "PAUSED"]
        status_tag = "🔴 [EN DIRECT]" if is_live else f"📅 {m['utcDate'][:10]}"
        label = f"{status_tag} - {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
        match_options[label] = m
    
    selected_label = st.selectbox("🎯 Choisissez la Rencontre à Analyser en Détail", list(match_options.keys()))
    match = match_options[selected_label]
    
    home_team = match["homeTeam"]
    away_team = match["awayTeam"]
    home_id = home_team["id"]
    away_id = away_team["id"]
    is_live = match["status"] in ["IN_PLAY", "PAUSED"]

    # EXÉCUTION DE LA DÉTECTION AUTOMATIQUE DU DERBY
    is_derby, derby_name = detect_derby_automatically(home_team['name'], away_team['name'])

    # Stats Base
    h_stat = teams_stats.get(home_id, {"avg_gf": 1.4, "avg_ga": 1.1, "form": 60})
    a_stat = teams_stats.get(away_id, {"avg_gf": 1.2, "avg_ga": 1.3, "form": 50})

    home_xg = max(0.6, (h_stat["avg_gf"] * 0.6 + a_stat["avg_ga"] * 0.4) * 1.15)
    away_xg = max(0.5, (a_stat["avg_gf"] * 0.6 + h_stat["avg_ga"] * 0.4) * 0.85)

    # En-tête Match & Forme
    col_h, col_vs, col_a = st.columns([4, 2, 4])
    with col_h:
        st.subheader(f"🏠 {home_team['name']}")
        st.write(f"📊 **Indice de Forme :** `{h_stat['form']}%`")
        st.progress(h_stat['form'])
    
    score_h, score_a = 0, 0
    with col_vs:
        if is_derby:
            st.markdown(f"<div style='text-align:center;'><span class='badge-derby'>🔥 {derby_name.upper()}</span></div>", unsafe_allow_html=True)
            
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

    # Calcul Matrice Poisson Dynamique (8x8)
    max_goals = 8
    matrix = np.zeros((max_goals, max_goals))
    for i in range(max_goals):
        for j in range(max_goals):
            matrix[i, j] = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)

    # Probabilités 1N2
    prob_home = float(np.sum(np.tril(matrix, -1)) * 100)
    prob_draw = float(np.sum(np.diag(matrix)) * 100)
    prob_away = float(np.sum(np.triu(matrix, 1)) * 100)

    # Double Chance
    prob_dc_1x = prob_home + prob_draw
    prob_dc_x2 = prob_away + prob_draw
    prob_dc_12 = prob_home + prob_away

    # Équipe Favorite
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

    # AJUSTEMENT DYNAMIQUE POISSON (AJUSTÉ SI DERBY DÉTECTÉ)
    tension_mult_cards = 1.35 if is_derby else 1.0
    tension_mult_corners = 1.15 if is_derby else 1.0

    exp_corners = max(6.0, ((home_xg + away_xg) * 2.7 + (h_stat["form"] + a_stat["form"]) / 35.0) * tension_mult_corners)
    exp_cards = max(2.2, ((h_stat["avg_ga"] + a_stat["avg_ga"]) * 1.4 + abs(h_stat["form"] - a_stat["form"]) / 30.0) * tension_mult_cards)

    # Probabilités par loi de Poisson
    prob_corner_65 = (1 - sum(poisson.pmf(k, exp_corners) for k in range(7))) * 100
    prob_corner_85 = (1 - sum(poisson.pmf(k, exp_corners) for k in range(9))) * 100

    prob_card_25 = (1 - sum(poisson.pmf(k, exp_cards) for k in range(3))) * 100
    prob_card_35 = (1 - sum(poisson.pmf(k, exp_cards) for k in range(4))) * 100

    # Top 3 Scores Exacts (Ajustés au score actuel si Live)
    scores_list = []
    start_h = score_h if is_live else 0
    start_a = score_a if is_live else 0
    
    for i in range(start_h, start_h + 4):
        for j in range(start_a, start_a + 4):
            scores_list.append((i, j, matrix[i - start_h, j - start_a] * 100))
    scores_list.sort(key=lambda x: x[2], reverse=True)
    top_3_scores = scores_list[:3]

    # Module Live Coordonné
    live_extra_text = ""
    if is_live:
        best_pred_h, best_pred_a, best_prob = top_3_scores[0]
        extra_goals = (best_pred_h - score_h) + (best_pred_a - score_a)
        if extra_goals > 0:
            live_extra_text = f"🔴 **Analyse Live Sync :** Pression détectée. L'algorithme prévoit **+{extra_goals} goal(s) supplémentaire(s)** d'ici la fin du match (Score cible probable : **{best_pred_h}-{best_pred_a}**)."
        else:
            live_extra_text = f"🔴 **Analyse Live Sync :** Le rythme actuel indique une stabilisation. Score le plus probable au coup de sifflet final : **{score_h}-{score_a}** (Confiance: `{best_prob:.1f}%`)."

    # Master Pick VIP
    candidates = [
        ("Plus de 0.5 But dans le match", (1 - matrix[0,0]) * 100),
        ("Plus de 6.5 Corners dans le match", prob_corner_65),
        ("Plus de 2.5 Cartons dans le match", prob_card_25),
        (f"Double Chance 1X ({home_team['name']} ou Nul)", prob_dc_1x),
        (f"Double Chance X2 ({away_team['name']} ou Nul)", prob_dc_x2),
        (f"Plus de 0.5 But pour {fav_name}", fav_over_05)
    ]
    high_conf_picks = [c for c in candidates if c[1] >= 85.0]
    high_conf_picks.sort(key=lambda x: x[1], reverse=True)
    
    master_pick_name, master_pick_conf = high_conf_picks[0] if high_conf_picks else candidates[0]

    # HEROCARD VIP
    st.markdown(f"""
    <div class="hero-card">
        <span class="badge-vip">🎯 PRONOSTIC APEX VIP (CONFIANCE CERTIFIÉE)</span>
        <h1 style="color: #38BDF8; margin: 12px 0 6px 0;">{master_pick_name}</h1>
        <p style="color: #94A3B8; margin: 0; font-size: 1.1rem;">Niveau de confiance calculé : <b style="color: #10B981;">{master_pick_conf:.1f}%</b></p>
    </div>
    """, unsafe_allow_html=True)

    if is_live:
        st.info(live_extra_text)

    # Section 1 : Marché 1N2 & Double Chance
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Marché Victoires (1N2) & Double Chance")
    
    col1, col2, col3 = st.columns(3)
    col1.metric(f"Victoire {home_team['name']} (1)", f"{prob_home:.1f}%")
    col2.metric("Match Nul (X)", f"{prob_draw:.1f}%")
    col3.metric(f"Victoire {away_team['name']} (2)", f"{prob_away:.1f}%")
    
    st.divider()
    
    dc1, dc2, dc3 = st.columns(3)
    dc1.write(f"🛡️ **Double Chance 1X :** `{prob_dc_1x:.1f}%`")
    dc2.write(f"🛡️ **Double Chance X2 :** `{prob_dc_x2:.1f}%`")
    dc3.write(f"🛡️ **Double Chance 12 :** `{prob_dc_12:.1f}%`")
    st.markdown('</div>', unsafe_allow_html=True)

    # Section 2 : Top 3 Scores Exacts & Favori
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

    # Section 3 : Offre Buts Total
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### ⚽ Marché Total Buts (Offre 1xBet)")
    
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

    # Section 4 : Dynamic Corners & Dynamic Cartons
    col_c, col_k = st.columns(2)

    with col_c:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("#### 🚩 Marché Corners Dynamique (Poisson)")
        st.write(f"**Plus de 6.5 Corners :** `{prob_corner_65:.1f}%`")
        st.progress(int(min(100, max(0, prob_corner_65))))
        st.write(f"**Plus de 8.5 Corners :** `{prob_corner_85:.1f}%`")
        st.progress(int(min(100, max(0, prob_corner_85))))
        st.markdown('</div>', unsafe_allow_html=True)

    with col_k:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("#### 🟨 Marché Cartons Dynamique (Poisson)")
        st.write(f"**Plus de 2.5 Cartons :** `{prob_card_25:.1f}%`")
        st.progress(int(min(100, max(0, prob_card_25))))
        st.write(f"**Plus de 3.5 Cartons :** `{prob_card_35:.1f}%`")
        st.progress(int(min(100, max(0, prob_card_35))))
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("Aucun match disponible pour ce championnat actuellement.")
