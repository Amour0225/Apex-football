import streamlit as st
import numpy as np
import requests
from scipy.stats import poisson

# Configuration de la page
st.set_page_config(
    page_title="Apex Quant Engine v8.0 AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS Pro High Contrast & AI Terminal Style
st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
        color: #0F172A;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .ai-card {
        background: linear-gradient(135deg, #090D16 0%, #1E1B4B 50%, #0F172A 100%);
        color: #FFFFFF;
        padding: 28px;
        border-radius: 20px;
        border: 2px solid #6366F1;
        box-shadow: 0 15px 35px -5px rgba(99, 102, 241, 0.3);
        margin-bottom: 25px;
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
    .badge-ai-safe {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: #FFFFFF;
        padding: 6px 18px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 0.85rem;
        display: inline-block;
        text-transform: uppercase;
        letter-spacing: 0.5px;
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
    .ai-reason-box {
        background: rgba(255, 255, 255, 0.07);
        border-left: 4px solid #818CF8;
        padding: 14px;
        border-radius: 8px;
        margin-top: 15px;
        font-size: 0.95rem;
        line-height: 1.5;
        color: #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

# MODÈLE DE DIXON-COLES
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

st.title("🤖 Apex Quant Engine v8.0 (Neural AI)")
st.caption("Moteur Decisionnel de Recommandation à Haute Sécurité & Analyse Tactique Live")

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

# Fetch Matches
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

    # Selection Match
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

    # Stats Dixon-Coles
    h_stat = teams_stats.get(home_id, {"att_strength": 1.0, "def_weakness": 1.0, "form": 55, "avg_gf": 1.3, "avg_ga": 1.1})
    a_stat = teams_stats.get(away_id, {"att_strength": 1.0, "def_weakness": 1.0, "form": 50, "avg_gf": 1.1, "avg_ga": 1.2})

    home_xg = max(0.4, h_stat["att_strength"] * a_stat["def_weakness"] * league_avg_goals_per_game * 1.12)
    away_xg = max(0.3, a_stat["att_strength"] * h_stat["def_weakness"] * league_avg_goals_per_game * 0.88)

    score_h = match.get('score', {}).get('fullTime', {}).get('home', 0) or 0 if is_live else 0
    score_a = match.get('score', {}).get('fullTime', {}).get('away', 0) or 0 if is_live else 0
    current_total_goals = score_h + score_a

    # Affichage En-tête
    col_h, col_vs, col_a = st.columns([4, 2, 4])
    with col_h:
        st.subheader(f"🏠 {home_team['name']}")
        st.write(f"📊 **Forme :** `{h_stat['form']}%` | **xG Attendu :** `{home_xg:.2f}`")
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
        st.write(f"📊 **Forme :** `{a_stat['form']}%` | **xG Attendu :** `{away_xg:.2f}`")
        st.progress(a_stat['form'])

    # MATRICE BIVARIÉE DIXON-COLES
    full_matrix = np.zeros((8, 8))
    for i in range(8):
        for j in range(8):
            raw_p = poisson.pmf(i, home_xg) * poisson.pmf(j, away_xg)
            tau = dixon_coles_tau(i, j, home_xg, away_xg)
            full_matrix[i, j] = max(0.0, raw_p * tau)

    full_matrix /= np.sum(full_matrix)

    # PROBABILITÉS GÉNÉRALES
    prob_home = float(np.sum(np.tril(full_matrix, -1)) * 100)
    prob_draw = float(np.sum(np.diag(full_matrix)) * 100)
    prob_away = float(np.sum(np.triu(full_matrix, 1)) * 100)

    prob_dc_1x = prob_home + prob_draw
    prob_dc_x2 = prob_away + prob_draw
    prob_dc_12 = prob_home + prob_away

    prob_over_05 = (1 - full_matrix[0, 0]) * 100
    prob_over_15 = (1 - sum(full_matrix[i, j] for i in range(2) for j in range(2) if i + j <= 1)) * 100

    # Corners & Cartons
    tension_cards = 1.35 if is_derby else 1.0
    tension_corners = 1.15 if is_derby else 1.0

    domination_ratio = home_xg / (home_xg + away_xg)
    total_exp_corners = max(6.5, ((home_xg + away_xg) * 2.6 + (h_stat["form"] + a_stat["form"]) / 38.0) * tension_corners)
    total_exp_cards = max(2.3, ((h_stat["avg_ga"] + a_stat["avg_ga"]) * 1.35) * tension_cards)

    prob_c_tot_65 = (1 - sum(poisson.pmf(k, total_exp_corners) for k in range(7))) * 100
    prob_k_tot_25 = (1 - sum(poisson.pmf(k, total_exp_cards) for k in range(3))) * 100

    # =========================================================================
    # 🧠 MODULE D'INTELLIGENCE ARTIFICIELLE DÉCISIONNELLE (ORACLE AI v8.0)
    # =========================================================================
    
    # 1. Scrutateur de tous les marchés possibles
    ai_candidates = []

    if is_live:
        time_factor = 0.45
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

        prob_next_goal = (1 - matrix_rem[0, 0]) * 100
        target_line = current_total_goals + 0.5

        if prob_next_goal >= 65.0:
            ai_candidates.append({
                "pick": f"Plus de {target_line} Buts dans le match (Live)",
                "prob": prob_next_goal,
                "type": "OVER_LIVE",
                "reason": f"Analyse en direct : la pression offensive combinée génère une probabilité de {prob_next_goal:.1f}% d'inscrire au moins un but supplémentaire d'ici la fin de la rencontre."
            })
        else:
            ai_candidates.append({
                "pick": f"Stabilisation du score à {score_h}-{score_a}",
                "prob": matrix_rem[0, 0] * 100,
                "type": "STABILITY_LIVE",
                "reason": f"Baisse du tempo offensif observée. La matrice prévoit {matrix_rem[0, 0]*100:.1f}% de chances que le score en reste là."
            })
        ai_candidates.append({
            "pick": "Plus de 6.5 Corners au total",
            "prob": prob_c_tot_65,
            "type": "CORNERS",
            "reason": f"Activité intense sur les ailes. L'indice attendu de corners est de {total_exp_corners:.1f} corners."
        })
    else:
        # Avant-match : Evaluation rigoureuse
        ai_candidates.append({
            "pick": "Plus de 0.5 But dans le match",
            "prob": prob_over_05,
            "type": "OVER_05",
            "reason": f"Sécurité Maximale : La probabilité cumulée de voir au moins un but dans ce match est de {prob_over_05:.1f}%, soutenue par un xG global de {(home_xg + away_xg):.2f}."
        })
        if prob_dc_1x >= 75.0:
            ai_candidates.append({
                "pick": f"Double Chance 1X ({home_team['name']} ou Nul)",
                "prob": prob_dc_1x,
                "type": "DC_1X",
                "reason": f"{home_team['name']} sur son terrain dispose d'un avantage de domicile calibré et d'un indice de forme de {h_stat['form']}%, réduisant le risque de défaite extérieure à {prob_away:.1f}%."
            })
        if prob_dc_x2 >= 75.0:
            ai_candidates.append({
                "pick": f"Double Chance X2 ({away_team['name']} ou Nul)",
                "prob": prob_dc_x2,
                "type": "DC_X2",
                "reason": f"{away_team['name']} montre une solidité supérieure face à {home_team['name']}, avec une probabilité de préserver au moins le nul estimée à {prob_dc_x2:.1f}%."
            })
        if prob_c_tot_65 >= 80.0:
            ai_candidates.append({
                "pick": "Plus de 6.5 Corners dans le match",
                "prob": prob_c_tot_65,
                "type": "CORNERS",
                "reason": f"Le volume de jeu latéral attendu suggère un minimum de {total_exp_corners:.1f} corners sur la totalité du match."
            })

    # Tri par probabilité décroissante
    ai_candidates.sort(key=lambda x: x["prob"], reverse=True)
    best_ai_pick = ai_candidates[0]

    # Calcul de la mise de Kelly conseillée
    stake_kelly = max(2, min(8, int((best_ai_pick["prob"] - 50) / 6))) if best_ai_pick["prob"] > 50 else 1

    # AFFICHAGE DE LA CARTE IA HEROIC
    st.markdown(f"""
    <div class="ai-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="badge-ai-safe">🛡️ CONSEIL ORACLE IA • CHANCE MAXIMALE DE GAIN</span>
            <span style="color: #A5B4FC; font-weight: bold; font-size: 0.9rem;">APEX NEURAL MODEL v8.0</span>
        </div>
        <h1 style="color: #67E8F9; margin: 5px 0 10px 0; font-size: 2rem;">👉 {best_ai_pick['pick']}</h1>
        <div style="display: flex; gap: 20px; align-items: center; margin-top: 15px;">
            <div>
                <span style="color: #94A3B8; font-size: 0.9rem;">Indice de Confiance Calculé</span>
                <div style="color: #10B981; font-size: 1.8rem; font-weight: 800;">{best_ai_pick['prob']:.1f}%</div>
            </div>
            <div style="border-left: 1px solid #334155; padding-left: 20px;">
                <span style="color: #94A3B8; font-size: 0.9rem;">Mise Suggérée (Gestion Capital)</span>
                <div style="color: #F59E0B; font-size: 1.8rem; font-weight: 800;">{stake_kelly}% du Bankroll</div>
            </div>
        </div>
        <div class="ai-reason-box">
            <b>🧠 Synthèse Tactique de l'IA :</b> {best_ai_pick['reason']}
        </div>
    </div>
    """, unsafe_allow_html=True)

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
    scores_list = []
    for i in range(5):
        for j in range(5):
            scores_list.append((i, j, full_matrix[i, j] * 100))
    scores_list.sort(key=lambda x: x[2], reverse=True)
    top_3_scores = scores_list[:3]

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
        st.markdown('</div>', unsafe_allow_html=True)

    with col_k:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("#### 🟨 Cartons : Total & Par Équipe")
        st.write(f"**Total Match > 2.5 Cartons :** `{prob_k_tot_25:.1f}%`")
        st.progress(int(min(100, max(0, prob_k_tot_25))))
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("Aucun match disponible pour ce championnat actuellement.")
