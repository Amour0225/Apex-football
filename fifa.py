import streamlit as st
import numpy as np
import requests

# Importation du moteur hybride (hybrid_engine.py)
try:
    from hybrid_engine import run_hybrid_match_prediction
except ImportError:
    st.error("⚠️ Le fichier 'hybrid_engine.py' est introuvable. Assurez-vous qu'il est bien placé dans le même dossier que 'fifa.py'.")

# Configuration de la page
st.set_page_config(
    page_title="Apex Quant Engine v8.4 AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Style CSS Pro
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

# DÉTECTION AUTOMATIQUE DE DERBIES & CHOCS EN C1
def detect_derby_automatically(home_name, away_name):
    known_derbies = [
        ({"Manchester United FC", "Manchester City FC"}, "Derby de Manchester"),
        ({"Arsenal FC", "Tottenham Hotspur FC"}, "North London Derby"),
        ({"Liverpool FC", "Everton FC"}, "Merseyside Derby"),
        ({"Chelsea FC", "Arsenal FC"}, "Derby de Londres"),
        ({"Real Madrid CF", "FC Barcelona"}, "El Clásico"),
        ({"Real Madrid CF", "Atlético de Madrid"}, "Derby Madrilène"),
        ({"FC Internazionale Milano", "AC Milan"}, "Derby della Madonnina"),
        ({"SS Lazio", "AS Roma"}, "Derby della Capitale"),
        ({"Juventus FC", "FC Internazionale Milano"}, "Derby d'Italia"),
        ({"Paris Saint-Germain FC", "Olympique de Marseille"}, "Le Classique"),
        ({"Borussia Dortmund", "FC Bayern München"}, "Der Klassiker"),
        ({"Real Madrid CF", "Manchester City FC"}, "Choc Européen (C1)"),
        ({"FC Bayern München", "Real Madrid CF"}, "Choc Européen (C1)"),
        ({"Paris Saint-Germain FC", "FC Barcelona"}, "Choc Européen (C1)")
    ]
    current_pair = {home_name, away_name}
    for team_set, derby_title in known_derbies:
        if team_set.issubset(current_pair) or team_set == current_pair:
            return True, derby_title
    cities = ["Manchester", "Madrid", "Milano", "Sevilla", "Turin", "Torino", "Liverpool", "Rome", "Roma", "London"]
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
    except Exception:
        return None
    return None

st.title("🤖 Apex Quant Engine v8.4 (Hybrid Dixon-Coles & NegBinomial)")
st.caption("Moteur Décisionnel Quantitatif • Prédiction Haute Précision")

# Sélection du Championnat
st.sidebar.header("🕹️ Compétition")
leagues = {
    "Ligue des Champions": "CL",
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1"
}
selected_league = st.sidebar.selectbox("Sélectionnez la Compétition", list(leagues.keys()))
league_code = leagues[selected_league]

# 1. TRAITEMENT DES CLASSEMENTS ET CALCUL DE FORME
standings_data = fetch_data(f"competitions/{league_code}/standings")
teams_stats = {}
league_total_goals = 0
league_total_games = 0

if standings_data and "standings" in standings_data:
    for st_group in standings_data["standings"]:
        table = st_group.get("table", [])
        for item in table:
            played = item.get("playedGames", 0) or 0
            gf = item.get("goalsFor", 0) or 0
            ga = item.get("goalsAgainst", 0) or 0
            if played > 0:
                league_total_goals += gf
                league_total_games += played

    if league_total_games > 0 and league_total_goals > 0:
        league_avg_goals_per_game = league_total_goals / league_total_games
    else:
        league_avg_goals_per_game = 1.45

    league_avg_goals_per_game = max(0.8, league_avg_goals_per_game)

    for st_group in standings_data["standings"]:
        table = st_group.get("table", [])
        for item in table:
            team_id = item["team"]["id"]
            played = item.get("playedGames", 0) or 0
            gf = item.get("goalsFor", 0) or 0
            ga = item.get("goalsAgainst", 0) or 0
            pts = item.get("points", 0) or 0

            if played > 0:
                teams_stats[team_id] = {
                    "att_strength": (gf / played) / league_avg_goals_per_game,
                    "def_weakness": (ga / played) / league_avg_goals_per_game,
                    "form": min(100, max(20, int((pts / (played * 3)) * 100))),
                    "avg_gf": gf / played,
                    "avg_ga": ga / played
                }
            else:
                teams_stats[team_id] = {
                    "att_strength": 1.0,
                    "def_weakness": 1.0,
                    "form": 50,
                    "avg_gf": 1.3,
                    "avg_ga": 1.1
                }
else:
    league_avg_goals_per_game = 1.45

# 2. RÉCUPÉRATION DES MATCHS (AVEC DÉTECTION ÉLARGIE C1)
raw_matches = fetch_data(f"competitions/{league_code}/matches")

valid_statuses = ["SCHEDULED", "TIMED", "LIVE", "IN_PLAY", "PAUSED", "FINISHED"]
match_list = []

if raw_matches and "matches" in raw_matches:
    # On filtre les matchs programmés, en cours ou récents
    for m in raw_matches["matches"]:
        if m.get("status") in ["SCHEDULED", "TIMED", "LIVE", "IN_PLAY", "PAUSED"]:
            match_list.append(m)

if match_list:
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### 📱 Dashboard : Directs & Matchs Programmés")

    live_games = [m for m in match_list if m["status"] in ["IN_PLAY", "PAUSED", "LIVE"]]
    upcoming_games = [m for m in match_list if m["status"] in ["SCHEDULED", "TIMED"]]

    tab_upcoming, tab_live = st.tabs([f"📅 Matchs Programmés ({len(upcoming_games)})", f"🔴 En Direct ({len(live_games)})"])

    with tab_upcoming:
        if upcoming_games:
            for ug in upcoming_games[:10]:
                time_str = ug['utcDate'][11:16]
                date_str = ug['utcDate'][:10]
                st.markdown(f"""
                <div class="sofa-card">
                    <span><b>{ug['homeTeam']['name']}</b> vs <b>{ug['awayTeam']['name']}</b></span>
                    <span style="color: #64748B; font-weight: bold;">📅 {date_str} à {time_str} UTC</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Aucun match à venir disponible dans le calendrier immédiat de l'API.")

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
            st.info("Aucun match en direct actuellement dans cette compétition.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Sélecteur de rencontre
    match_options = {}
    for m in match_list:
        is_l = m["status"] in ["IN_PLAY", "PAUSED", "LIVE"]
        status_tag = "🔴 [EN DIRECT]" if is_l else f"📅 {m['utcDate'][:10]}"
        label = f"{status_tag} - {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
        match_options[label] = m

    selected_label = st.selectbox("🎯 Choisissez la Rencontre à Analyser en Détail", list(match_options.keys()))
    match = match_options[selected_label]

    home_team = match["homeTeam"]
    away_team = match["awayTeam"]
    home_id = home_team["id"]
    away_id = away_team["id"]
    is_live = match["status"] in ["IN_PLAY", "PAUSED", "LIVE"]

    is_derby, derby_name = detect_derby_automatically(home_team['name'], away_team['name'])

    # Récupération statistiques d'équipes (avec fallback sécurisé pour la C1)
    default_stats = {"att_strength": 1.1, "def_weakness": 0.95, "form": 60, "avg_gf": 1.5, "avg_ga": 1.1}
    h_stat = teams_stats.get(home_id, default_stats)
    a_stat = teams_stats.get(away_id, default_stats)

    home_xg = max(0.5, h_stat["att_strength"] * a_stat["def_weakness"] * league_avg_goals_per_game * 1.12)
    away_xg = max(0.4, a_stat["att_strength"] * h_stat["def_weakness"] * league_avg_goals_per_game * 0.88)

    score_h = match.get('score', {}).get('fullTime', {}).get('home', 0) or 0 if is_live else 0
    score_a = match.get('score', {}).get('fullTime', {}).get('away', 0) or 0 if is_live else 0
    current_total_goals = score_h + score_a

    # En-tête du match
    col_h, col_vs, col_a = st.columns([4, 2, 4])
    with col_h:
        st.subheader(f"🏠 {home_team['name']}")
        st.write(f"📊 **Indice Forme :** `{h_stat['form']}%` | **xG Attendu :** `{home_xg:.2f}`")
        st.progress(h_stat['form'] / 100)

    with col_vs:
        if is_derby:
            st.markdown(f"<div style='text-align:center;'><span class='badge-derby'>🔥 {derby_name.upper()}</span></div>", unsafe_allow_html=True)
        if is_live:
            st.markdown(f"<div class='badge-live'>🔴 EN DIRECT<br>{score_h} - {score_a}</div>", unsafe_allow_html=True)
        else:
            st.markdown("<h3 style='text-align: center; color: #0F172A;'>VS</h3>", unsafe_allow_html=True)

    with col_a:
        st.subheader(f"✈️ {away_team['name']}")
        st.write(f"📊 **Indice Forme :** `{a_stat['form']}%` | **xG Attendu :** `{away_xg:.2f}`")
        st.progress(a_stat['form'] / 100)

    # 3. PRÉDICTIONS VIA LE MOTEUR HYBRIDE
    tension_cards = 1.45 if is_derby else 1.0
    tension_corners = 1.20 if is_derby else 1.0

    home_exp_corners = max(2.8, (h_stat["att_strength"] * 4.8 + a_stat["def_weakness"] * 0.9) * tension_corners)
    away_exp_corners = max(2.2, (a_stat["att_strength"] * 4.0 + h_stat["def_weakness"] * 0.8) * tension_corners)

    home_exp_cards = max(1.2, (h_stat["def_weakness"] * 1.8 + a_stat["att_strength"] * 0.6) * tension_cards)
    away_exp_cards = max(1.3, (a_stat["def_weakness"] * 2.0 + h_stat["att_strength"] * 0.7) * tension_cards)

    hybrid_input = {
        "exp_goals_home": home_xg,
        "exp_goals_away": away_xg,
        "exp_corners_home": home_exp_corners,
        "exp_corners_away": away_exp_corners,
        "exp_cards_home": home_exp_cards,
        "exp_cards_away": away_exp_cards
    }

    hybrid_out = run_hybrid_match_prediction(hybrid_input)

    # Traitement probabilités 1N2
    prob_1n2 = hybrid_out["goals_and_1N2"]["prob_1N2"]
    prob_home = prob_1n2["1"] * 100.0
    prob_draw = prob_1n2["N"] * 100.0
    prob_away = prob_1n2["2"] * 100.0

    prob_dc_1x = prob_home + prob_draw
    prob_dc_x2 = prob_away + prob_draw
    prob_dc_12 = prob_home + prob_away

    # DECISION ORACLE IA
    ai_candidates = []
    prob_over_05 = hybrid_out["goals_and_1N2"]["over_under"].get("Over_1.5", 0.75) * 100

    if is_live:
        target_line = current_total_goals + 0.5
        ai_candidates.append({
            "pick": f"Plus de {target_line} Buts dans le match (Live)",
            "prob": 70.0,
            "reason": f"Analyse en direct : xG cumulé élevé et pressing offensif."
        })
    else:
        ai_candidates.append({
            "pick": "Plus de 0.5 But dans le match",
            "prob": prob_over_05,
            "reason": f"Sécurité Dixon-Coles : Espérance de buts totale de {(home_xg + away_xg):.2f}."
        })
        if prob_dc_1x >= 68.0:
            ai_candidates.append({
                "pick": f"Double Chance 1X ({home_team['name']} ou Nul)",
                "prob": prob_dc_1x,
                "reason": f"{home_team['name']} solide à domicile."
            })
        if prob_dc_x2 >= 68.0:
            ai_candidates.append({
                "pick": f"Double Chance X2 ({away_team['name']} ou Nul)",
                "prob": prob_dc_x2,
                "reason": f"{away_team['name']} performant à l'extérieur."
            })

    ai_candidates.sort(key=lambda x: x["prob"], reverse=True)
    best_ai_pick = ai_candidates[0]
    stake_kelly = max(2, min(8, int((best_ai_pick["prob"] - 50) / 6))) if best_ai_pick["prob"] > 50 else 1

    # CARTE IA HEROIC
    st.markdown(f"""
    <div class="ai-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="badge-ai-safe">🛡️ CONSEIL ORACLE IA • MOTEUR HYBRIDE v8.4</span>
            <span style="color: #A5B4FC; font-weight: bold; font-size: 0.9rem;">DIXON-COLES & NEGBINOMIAL</span>
        </div>
        <h1 style="color: #67E8F9; margin: 5px 0 10px 0; font-size: 2rem;">👉 {best_ai_pick['pick']}</h1>
        <div style="display: flex; gap: 20px; align-items: center; margin-top: 15px;">
            <div>
                <span style="color: #94A3B8; font-size: 0.9rem;">Indice de Confiance Calculé</span>
                <div style="color: #10B981; font-size: 1.8rem; font-weight: 800;">{best_ai_pick['prob']:.1f}%</div>
            </div>
            <div style="border-left: 1px solid #334155; padding-left: 20px;">
                <span style="color: #94A3B8; font-size: 0.9rem;">Mise Suggérée (Kelly)</span>
                <div style="color: #F59E0B; font-size: 1.8rem; font-weight: 800;">{stake_kelly}% du Capital</div>
            </div>
        </div>
        <div class="ai-reason-box">
            <b>🧠 Synthèse Tactique de l'IA :</b> {best_ai_pick['reason']}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1N2 & Double Chance
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Marché Victoires (1N2) & Double Chance (Dixon-Coles)")

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

    # Top Scores Exacts
    matrix_scores = hybrid_out["goals_and_1N2"]["score_matrix"]
    scores_list = []
    for h_g in range(matrix_scores.shape[0]):
        for a_g in range(matrix_scores.shape[1]):
            scores_list.append((h_g, a_g, matrix_scores[h_g, a_g] * 100.0))
    scores_list.sort(key=lambda x: x[2], reverse=True)
    top_3 = scores_list[:3]

    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### 🎲 Top 3 Scores Exacts Probables")
    sc1, sc2, sc3 = st.columns(3)
    for idx, (col_sc, sc_item) in enumerate(zip([sc1, sc2, sc3], top_3)):
        with col_sc:
            st.markdown(f"""
            <div class="score-badge">
                <div style="font-size: 1.3rem; color: #2563EB;">{sc_item[0]} - {sc_item[1]}</div>
                <div style="font-size: 0.85rem; color: #64748B;">Probabilité : {sc_item[2]:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Offre Total Buts
    st.markdown('<div class="pro-card">', unsafe_allow_html=True)
    st.markdown("### ⚽ Marché Total Buts (Dixon-Coles)")

    goals_ou = hybrid_out["goals_and_1N2"]["over_under"]
    for line in [1.5, 2.5, 3.5, 4.5]:
        over_p = goals_ou.get(f"Over_{line}", 0.0) * 100.0
        under_p = goals_ou.get(f"Under_{line}", 0.0) * 100.0
        st.markdown(f"""
        <div class="market-row">
            <span><b>Ligne {line} Buts</b></span>
            <span>Plus de {line} : <b style="color: #059669;">{over_p:.1f}%</b></span>
            <span>Moins de {line} : <b style="color: #2563EB;">{under_p:.1f}%</b></span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Corners & Cartons
    st.markdown("### 🚩 & 🟨 Analyse Duale Corners et Cartons (Loi Binomiale Négative)")
    col_c, col_k = st.columns(2)

    corners_ou = hybrid_out["corners"]["over_under"]
    cards_ou = hybrid_out["cards"]["over_under"]

    with col_c:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown(f"#### 🚩 Marché Corners *(Total Estimé : {hybrid_out['corners']['exp_total']})*")
        for line in [8.5, 9.5, 10.5, 11.5]:
            over_p = corners_ou.get(f"Over_{line}", 0.0) * 100.0
            under_p = corners_ou.get(f"Under_{line}", 0.0) * 100.0
            st.markdown(f"""
            <div class="market-row">
                <span><b>Ligne {line} Corners</b></span>
                <span>Plus : <b style="color: #059669;">{over_p:.1f}%</b></span>
                <span>Moins : <b style="color: #2563EB;">{under_p:.1f}%</b></span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_k:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown(f"#### 🟨 Marché Cartons Jaunes *(Total Estimé : {hybrid_out['cards']['exp_total']})*")
        for line in [3.5, 4.5, 5.5, 6.5]:
            over_p = cards_ou.get(f"Over_{line}", 0.0) * 100.0
            under_p = cards_ou.get(f"Under_{line}", 0.0) * 100.0
            st.markdown(f"""
            <div class="market-row">
                <span><b>Ligne {line} Cartons</b></span>
                <span>Plus : <b style="color: #059669;">{over_p:.1f}%</b></span>
                <span>Moins : <b style="color: #2563EB;">{under_p:.1f}%</b></span>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

else:
    st.warning("Aucun match disponible immédiatement dans cette compétition.")
