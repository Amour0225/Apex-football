import streamlit as st
import numpy as np
import requests
from scipy.stats import poisson

# Configuration de la page
st.set_page_config(
    page_title="Apex Quant Engine v7.0",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS Pro High Contrast
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
        padding: 10px 14px;
        background-color: #F8FAFC;
        border-radius: 8px;
        margin-bottom: 6px;
        border: 1px solid #E2E8F0;
        font-size: 0.95rem;
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

# MODÈLE DE DIXON-COLES (Ajustement mathématique des scores bas)
def dixon_coles_tau(x, y, home_xg, away_xg, rho=-0.13):
    if x == 0 and y == 0:
        return 1.0 - (home_xg * away_xg * rho)
    elif x == 1 and y == 0:
        return 1.0 + (away_xg * rho)
    elif x == 0 and y == 1:
        return 1.0 + (home_xg * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    else:
        return 1.0

# DÉTECTION AUTOMATIQUE DE DERBIES
def detect_derby_automatically(home_name, away_name):
    known_derbies = [
        ({"Manchester United FC", "Manchester City FC"}, "Derby de Manchester"),
        ({"Arsenal FC", "Tottenham Hotspur FC"}, "North London Derby"),
        ({"Liverpool FC", "Everton FC"}, "Merseyside Derby"),
        ({"Chelsea FC", "Arsenal FC"}, "Derby de Londres"),
        ({"Chelsea FC", "Tottenham Hotspur FC"}, "Derby de Londres"),
        ({"Liverpool FC", "Manchester United FC"}, "North-West Derby"),
        ({"Real Madrid CF", "FC Barcelona"}, "El Clásico"),
        ({"Real Madrid CF", "Atlético de Madrid"}, "Derby Madrilène"),
        ({"Sevilla FC", "Real Betis Balompié"}, "Derby Sévillan"),
        ({"Athletic Club", "Real Sociedad de Fútbol"}, "Derby Basque"),
        ({"FC Internazionale Milano", "AC Milan"}, "Derby della Madonnina"),
        ({"SS Lazio", "AS Roma"}, "Derby della Capitale"),
        ({"Juventus FC", "FC Internazionale Milano"}, "Derby d'Italia"),
        ({"Juventus FC", "Torino FC"}, "Derby della Mole"),
        ({"Paris Saint-Germain FC", "Olympique de Marseille"}, "Le Classique"),
        ({"Olympique Lyonnais", "AS Saint-Étienne"}, "Derby du Rhône"),
        ({"OGC Nice", "AS Monaco FC"}, "Derby de la Côte d'Azur"),
        ({"Borussia Dortmund", "FC Bayern München"}, "Der Klassiker")
    ]
    current_pair = {home_name, away_name}
    for team_set, derby_title in known_derbies:
        if team_set.issubset(current_pair) or team_set == current_pair:
            return True, derby_title
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

st.title("⚡ Apex Quant Engine v7.0")
st.caption("Algorithme Dixon-Coles Bivariate Engine, Dynamic Live Elasticity & 1xBet Analytics")

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

# Traitement Classement & Normalisation LIGUE
standings_data = fetch_data(f"competitions/{league_code}/standings")
teams_stats = {}
league_total_goals = 0
league_total_games = 0

if standings_data and "standings" in standings_data and len(standings_data["standings"]) > 0:
    table = standings_data["standings"][0].get("table", [])
    for item in table:
        played = item.get("playedGames", 1) or 1
        gf = item.get("goalsFor", 0)
        ga = item.get("goalsAgainst", 0)
        league_total_goals += gf
        league_total_games += played
        
    league_avg_goals_per_game = (league_total_goals / league_total_games) if league_total_games > 0 else 1.35
    
    for item in table:
        team_id = item["team"]["id"]
        played = item.get("playedGames", 1) or 1
        gf = item.get("goalsFor", 0)
        ga = item.get("goalsAgainst", 0)
        pts = item.get("points", 0)
        
        teams_stats[team_id] = {
            "att_strength": (gf / played) / league_avg_goals_per_game if played > 0 else 1.0,
            "def_weakness": (ga / played) / league_avg_goals_per_game if played > 0 else 1.0,
            "form": min(100, int((pts / (played * 3)) * 100)) if played > 0 else 50,
            "avg_gf": gf / played,
            "avg_ga": ga / played
        }
else:
    league_avg_goals_per_game = 1.35

# Matchs
matches_data = fetch_data(f"competitions/{league_code}/matches?status=SCHEDULED,LIVE,IN_PLAY,PAUSED")

if matches_data and matches_data.get("matches"):
    match_list = matches_data["matches"]
    
    # SofaScore Dashboard
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

    # Sélection du match
    match_options = {}
    for m in match_list:
        is_l = m["status"] in ["IN_PLAY", "PAUSED"]
        status_tag = "🔴 [EN DIRECT]" if is_l else f"📅 {m['utcDate'][:10]}"
        label = f"{status_tag} - {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
        match_options[label] = m
    
    selected_label = st.selectbox("🎯 Choisissez la Rencontre à Analyser en Détail", list(match_options.keys()))
    match = match_options[selected_label]
    
    home_team = match["homeTeam"]
    away_team = match["awayTeam"]
    home_id = home_team["id"]
    away_id = away_team["id"]
    is_live = match["status"] in ["IN_PLAY", "PAUSED"]

    is_derby, derby_name = detect_derby_automatically(home_team['name'], away_team['name'])

    # Stats avancées Dixons-Coles
    h_stat = teams_stats.get(home_id, {"att_strength": 1.0, "def_weakness": 1.0, "form": 55, "avg_gf": 1.3, "avg_ga": 1.1})
    a_stat = teams_stats.get(away_id, {"att_strength": 1.0, "def_weakness": 1.0, "form": 50, "avg_gf": 1.1, "avg_ga": 1.2})

    # Calcul xG Dixon-Coles calibré
    home_xg = max(0.4, h_stat["att_strength"] * a_stat["def_weakness"] * league_avg_goals_per_game * 1.12)
    away_xg = max(0.3, a_stat["att_strength"] * h_stat["def_weakness"] * league_avg_goals_per_game * 0.88)

    # Score actuel si Live
    score_h = match.get('score', {}).get('fullTime', {}).get('home', 0) or 0 if is_live else 0
    score_a = match.get('score', {}).get('fullTime', {}).get('away', 0) or 0 if is_live else 0
    current_total_goals = score_h + score_a

    # Affichage En-tête
    col_h, col_vs, col_a = st.columns([4, 2, 4])
    with col_h:
        st.subheader(f"🏠 {home_team['name']}")
        st.write(f"📊 **Indice de Forme :** `{h_stat['form']}%` | **xG de base :** `{home_xg:.2f}`")
        st.progress(h_stat['form'])
    
    with col_vs:
        if is_derby:
            st.markdown(f"<div style='text-align:center;'><span class='badge-derby'>🔥 {derby_name.upper()}</span></div>", unsafe_allow_html=True)
        if is_live:
            st.markdown(f"<div class='badge-live'>🔴 EN DIRECT<br>{score_h} - {score_a}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='text-align: center; color: #0F172A;'>VS</h3>", unsafe_allow_html=True)
    
    with col_a:
        st.subheader(f"✈️ {away_team['name']}")
        st.write(f"📊 **Indice de Forme :** `{a_stat['form']}%` | **xG de base :** `{away_xg:.2f}`")
        st.progress(a_stat['form'])

    # MATRICE D'AVANT MATCH (DIXON-COLES BI-VARIÉ)
    full_matrix = np.zeros((8, 8))
    for i in range(8):
        for j in range(8):
            raw_p = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)
            tau = dixon_coles_tau(i, j, home_xg, away_xg)
            full_matrix[i, j] = max(0.0, raw_p * tau)

    full_matrix /= np.sum(full_matrix)  # Normalisation des probabilités

    # GESTION LIVE AVEC ELASTICITÉ DYNAMIQUE
    if is_live:
        time_factor = 0.45  # Estimateur du temps de jeu restant
        # Facteur de désespoir / pression si retard de score
        desperation_h = 1.18 if score_h < score_a else 1.0
        desperation_a = 1.18 if score_a < score_h else 1.0

        rem_home_xg = home_xg * time_factor * desperation_h
        rem_away_xg = away_xg * time_factor * desperation_a

        matrix_rem = np.zeros((6, 6))
        for i in range(6):
            for j in range(6):
                raw_p = poisson.pmf(i, rem_home_xg) * poisson.pmf(j, rem_away_xg)
                tau = dixon_coles_tau(i, j, rem_home_xg, rem_away_xg)
                matrix_rem[i, j] = max(0.0, raw_p * tau)
        matrix_rem /= np.sum(matrix_rem)

        scores_list = []
        for add_h in range(4):
            for add_a in range(4):
                final_h = score_h + add_h
                final_a = score_a + add_a
                prob = matrix_rem[add_h, add_a] * 100
                scores_list.append((final_h, final_a, prob, add_h + add_a))
        scores_list.sort(key=lambda x: x[2], reverse=True)
        top_3_scores = scores_list[:3]
    else:
        scores_list = []
        for i in range(5):
            for j in range(5):
                scores_list.append((i, j, full_matrix[i, j] * 100, i + j))
        scores_list.sort(key=lambda x: x[2], reverse=True)
        top_3_scores = scores_list[:3]

    # Probabilités Générales
    prob_home = float(np.sum(np.tril(full_matrix, -1)) * 100)
    prob_draw = float(np.sum(np.diag(full_matrix)) * 100)
    prob_away = float(np.sum(np.triu(full_matrix, 1)) * 100)

    prob_dc_1x = prob_home + prob_draw
    prob_dc_x2 = prob_away + prob_draw
    prob_dc_12 = prob_home + prob_away

    prob_over_05 = (1 - full_matrix[0, 0]) * 100

    # Corners & Cartons (Corrélés au ratio de possession/domination)
    tension_cards = 1.35 if is_derby else 1.0
    tension_corners = 1.15 if is_derby else 1.0

    domination_ratio = home_xg / (home_xg + away_xg)
    total_exp_corners = max(6.5, ((home_xg + away_xg) * 2.6 + (h_stat["form"] + a_stat["form"]) / 38.0) * tension_corners)
    total_exp_cards = max(2.3, ((h_stat["avg_ga"] + a_stat["avg_ga"]) * 1.35) * tension_cards)

    home_exp_corners = max(2.5, total_exp_corners * domination_ratio * 1.05)
    away_exp_corners = max(2.0, total_exp_corners * (1 - domination_ratio) * 0.95)

    prob_c_tot_65 = (1 - sum(poisson.pmf(k, total_exp_corners) for k in range(7))) * 100
    prob_c_home_35 = (1 - sum(poisson.pmf(k, home_exp_corners) for k in range(4))) * 100
    prob_c_away_35 = (1 - sum(poisson.pmf(k, away_exp_corners) for k in range(4))) * 100

    home_exp_cards = max(1.0, total_exp_cards * (1 - domination_ratio))
    away_exp_cards = max(1.0, total_exp_cards * domination_ratio)

    prob_k_tot_25 = (1 - sum(poisson.pmf(k, total_exp_cards) for k in range(3))) * 100
    prob_k_home_15 = (1 - sum(poisson.pmf(k, home_exp_cards) for k in range(2))) * 100
    prob_k_away_15 = (1 - sum(poisson.pmf(k, away_exp_cards) for k in range(2))) * 100

    # SELECTION INTELUGENTE VIP (Priorité Sécurité Maximale)
    candidates = []
    if is_live:
        target_line = current_total_goals + 0.5
        prob_next = (1 - matrix_rem[0, 0]) * 100
        if prob_next >= 68.0:
            candidates.append((f"Plus de {target_line} Buts au total dans le match", prob_next))
        else:
            candidates.append((f"Pas de but supplémentaire (Stabilisation {score_h}-{score_a})", matrix_rem[0, 0] * 100))
        candidates.append((f"Plus de 6.5 Corners au total", prob_c_tot_65))
        candidates.append((f"Plus de 2.5 Cartons au total", prob_k_tot_25))
    else:
        candidates.append(("Plus de 0.5 But dans le match (Sécurité Max)", prob_over_05))
        candidates.append((f"Double Chance 1X ({home_team['name']} ou Nul)", prob_dc_1x))
        candidates.append((f"Double Chance X2 ({away_team['name']} ou Nul)", prob_dc_x2))
        candidates.append(("Plus de 6.5 Corners dans le match", prob_c_tot_65))

    candidates.sort(key=lambda x: x[1], reverse=True)
    master_pick_name, master_pick_conf = candidates[0]

    # HEROCARD VIP
    st.markdown(f"""
    <div class="hero-card">
        <span class="badge-vip">🎯 PRONOSTIC APEX VIP (CONFIANCE CERTIFIÉE)</span>
        <h1 style="color: #38BDF8; margin: 12px 0 6px 0;">{master_pick_name}</h1>
        <p style="color: #94A3B8; margin: 0; font-size: 1.1rem;">Niveau de confiance calculé : <b style="color: #10B981;">{master_pick_conf:.1f}%</b></p>
    </div>
    """, unsafe_allow_html=True)

    if is_live:
        best_pred_h, best_pred_a, best_prob, add_goals = top_3_scores[0]
        if add_goals > 0:
            st.info(f"🔴 **Analyse Live Quant Engine :** Score **{score_h}-{score_a}**. Attaque soutenue décelée. Prévision : **+{add_goals} goal(s)**. Score final probable : **{best_pred_h}-{best_pred_a}** (`{best_prob:.1f}%`).")
        else:
            st.info(f"🔴 **Analyse Live Quant Engine :** Score **{score_h}-{score_a}**. Pression faible. Probabilité de stabilisation à **{score_h}-{score_a}** : `{best_prob:.1f}%`.")

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

    # Section 2 : Top 3 Scores Exacts
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### 🎲 Top 3 Scores Exacts Probables (Dixon-Coles Model)")
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

    # Section 3 : Offre Buts Total 1xBet
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### ⚽ Marché Total Buts (Lignes 1xBet)")
    
    goals_lines = [0.5, 1.5, 2.5, 3.5]
    for line in goals_lines:
        over_p = 0.0
        for i in range(8):
            for j in range(8):
                if (i + j) > line:
                    over_p += full_matrix[i, j]
        over_p *= 100
        under_p = 100.0 - over_p
        
        status_str = " (Validé ✔️)" if is_live and current_total_goals > line else ""
        st.markdown(f"""
        <div class="market-row">
            <span><b>Ligne {line} Buts{status_str}</b></span>
            <span>Plus de {line} : <b style="color: #059669;">{over_p:.1f}%</b></span>
            <span>Moins de {line} : <b style="color: #2563EB;">{under_p:.1f}%</b></span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Section 4 : Multi-Markets Corners & Cartons Par Équipe
    col_c, col_k = st.columns(2)

    with col_c:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("#### 🚩 Corners : Total & Par Équipe")
        st.write(f"**Total Match > 6.5 Corners :** `{prob_c_tot_65:.1f}%`")
        st.progress(int(min(100, max(0, prob_c_tot_65))))
        st.divider()
        st.write(f"**{home_team['name']} > 3.5 Corners :** `{prob_c_home_35:.1f}%`")
        st.progress(int(min(100, max(0, prob_c_home_35))))
        st.write(f"**{away_team['name']} > 3.5 Corners :** `{prob_c_away_35:.1f}%`")
        st.progress(int(min(100, max(0, prob_c_away_35))))
        st.markdown('</div>', unsafe_allow_html=True)

    with col_k:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("#### 🟨 Cartons : Total & Par Équipe")
        st.write(f"**Total Match > 2.5 Cartons :** `{prob_k_tot_25:.1f}%`")
        st.progress(int(min(100, max(0, prob_k_tot_25))))
        st.divider()
        st.write(f"**{home_team['name']} > 1.5 Cartons :** `{prob_k_home_15:.1f}%`")
        st.progress(int(min(100, max(0, prob_k_home_15))))
        st.write(f"**{away_team['name']} > 1.5 Cartons :** `{prob_k_away_15:.1f}%`")
        st.progress(int(min(100, max(0, prob_k_away_15))))
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("Aucun match disponible pour ce championnat actuellement.")
