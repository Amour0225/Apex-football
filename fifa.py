import streamlit as st
import requests

try:
    from hybrid_engine import run_hybrid_match_prediction
except ImportError as e:
    st.error(f"⚠️ Erreur d'importation du moteur : {e}")
    st.stop()

st.set_page_config(
    page_title="Apex Quant Engine v9.0 Live Intensity",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; color: #0F172A; font-family: 'Inter', sans-serif; }
    .ai-card {
        background: linear-gradient(135deg, #090D16 0%, #1E1B4B 50%, #0F172A 100%);
        color: #FFFFFF; padding: 28px; border-radius: 20px;
        border: 2px solid #6366F1; box-shadow: 0 15px 35px -5px rgba(99, 102, 241, 0.3);
        margin-bottom: 25px;
    }
    .pro-card {
        background-color: #FFFFFF; padding: 22px; border-radius: 14px;
        border: 1px solid #E2E8F0; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    .score-badge {
        background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 10px;
        padding: 12px; text-align: center; font-weight: bold; color: #0F172A;
    }
    .badge-live {
        background-color: #EF4444; color: white; padding: 8px 16px;
        border-radius: 20px; font-weight: 700; font-size: 0.9rem; display: inline-block;
    }
    .badge-derby {
        background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%);
        color: white; padding: 6px 14px; border-radius: 8px; font-weight: 800;
        font-size: 0.85rem; display: inline-block; margin-bottom: 12px;
    }
    .badge-ai-safe {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: #FFFFFF; padding: 6px 18px; border-radius: 20px;
        font-weight: 800; font-size: 0.85rem; display: inline-block;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .market-row {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 14px; background-color: #F8FAFC; border-radius: 8px;
        margin-bottom: 6px; border: 1px solid #E2E8F0; font-size: 0.95rem;
    }
    .sofa-card {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;
        padding: 12px 16px; margin-bottom: 10px; display: flex;
        justify-content: space-between; align-items: center;
    }
    .ai-reason-box {
        background: rgba(255, 255, 255, 0.07); border-left: 4px solid #818CF8;
        padding: 14px; border-radius: 8px; margin-top: 15px; font-size: 0.95rem;
        line-height: 1.5; color: #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

@st.cache_data(ttl=180)
def fetch_data(endpoint):
    headers = {"X-Auth-Token": API_KEY}
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

st.title("🤖 Apex Quant Engine v9.0 (Live Intensity Engine)")
st.caption("Modélisation Quantitative Multi-Facteurs • Intégration Pression Terrain & Tirs")

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

standings_data = fetch_data(f"competitions/{league_code}/standings")
teams_stats = {}
league_avg_goals = 1.35

if standings_data and "standings" in standings_data:
    tot_g, tot_p = 0, 0
    for st_group in standings_data["standings"]:
        for item in st_group.get("table", []):
            p = item.get("playedGames", 0)
            gf = item.get("goalsFor", 0)
            ga = item.get("goalsAgainst", 0)
            pts = item.get("points", 0)
            if p > 0:
                tot_g += gf
                tot_p += p
                teams_stats[item["team"]["id"]] = {
                    "att": (gf / p) / 1.35,
                    "def": (ga / p) / 1.35,
                    "form": min(100, max(15, int((pts / (p * 3)) * 100)))
                }
    if tot_p > 0:
        league_avg_goals = max(0.9, tot_g / tot_p)

raw_matches = fetch_data(f"competitions/{league_code}/matches")
match_list = []

if raw_matches and "matches" in raw_matches:
    for m in raw_matches["matches"]:
        if m.get("status") in ["SCHEDULED", "TIMED", "LIVE", "IN_PLAY", "PAUSED"]:
            match_list.append(m)

if match_list:
    match_options = {}
    for m in match_list:
        is_l = m["status"] in ["IN_PLAY", "PAUSED", "LIVE"]
        tag = "🔴 [EN DIRECT]" if is_l else f"📅 {m['utcDate'][:10]}"
        label = f"{tag} - {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
        match_options[label] = m

    selected_label = st.selectbox("🎯 Choisissez le Match à Analyser", list(match_options.keys()))
    match = match_options[selected_label]
    is_live = match["status"] in ["IN_PLAY", "PAUSED", "LIVE"]

    # Panneau de contrôle des statistiques en direct si le match est en cours
    if is_live:
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Statistiques d'Intensité en Direct (Micro-Match Data)")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            sot_h = st.number_input(f"Tirs Cadrés ({match['homeTeam']['name']})", min_value=0, value=3)
            sot_a = st.number_input(f"Tirs Cadrés ({match['awayTeam']['name']})", min_value=0, value=1)
        with col_s2:
            shots_h = st.number_input(f"Tirs Totaux ({match['homeTeam']['name']})", min_value=0, value=8)
            shots_a = st.number_input(f"Tirs Totaux ({match['awayTeam']['name']})", min_value=0, value=4)
        with col_s3:
            fouls_h = st.number_input(f"Fautes ({match['homeTeam']['name']})", min_value=0, value=6)
            fouls_a = st.number_input(f"Fautes ({match['awayTeam']['name']})", min_value=0, value=8)
        with col_s4:
            minute_input = st.number_input("Minute Actuelle", min_value=1, max_value=90, value=min(88, match.get('minute', 55)))
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        sot_h, sot_a, shots_h, shots_a, fouls_h, fouls_a, minute_input = 0, 0, 0, 0, 0, 0, 0

    if st.button("🚀 Lancer la Simulation d'Intensité Quant", type="primary", use_container_width=True):
        home_team = match["homeTeam"]
        away_team = match["awayTeam"]

        score_h = match.get('score', {}).get('fullTime', {}).get('home', 0) or 0 if is_live else 0
        score_a = match.get('score', {}).get('fullTime', {}).get('away', 0) or 0 if is_live else 0

        def_stat = {"att": 1.0, "def": 1.0, "form": 50}
        h_stat = teams_stats.get(home_team["id"], def_stat)
        a_stat = teams_stats.get(away_team["id"], def_stat)

        home_xg = max(0.4, h_stat["att"] * a_stat["def"] * league_avg_goals * 1.10)
        away_xg = max(0.3, a_stat["att"] * h_stat["def"] * league_avg_goals * 0.90)

        engine_input = {
            "is_live": is_live,
            "current_home_score": score_h,
            "current_away_score": score_a,
            "minute": minute_input if is_live else 0,
            "exp_goals_home": home_xg,
            "exp_goals_away": away_xg,
            "shots_on_target_home": sot_h,
            "shots_on_target_away": sot_a,
            "shots_total_home": shots_h,
            "shots_total_away": shots_a,
            "fouls_home": fouls_h,
            "fouls_away": fouls_a
        }

        res = run_hybrid_match_prediction(engine_input)

        # Résultats & Conseils
        p_1n2 = res["prob_1N2"]
        p_h, p_n, p_a = p_1n2["1"] * 100, p_1n2["N"] * 100, p_1n2["2"] * 100
        p_1x, p_x2 = p_h + p_n, p_a + p_n

        if is_live:
            rem_h_xg = res["intensity_metrics"]["rem_home_xg"]
            rem_a_xg = res["intensity_metrics"]["rem_away_xg"]
            if score_h >= score_a:
                best_pick = f"Victoire ou Couverture {home_team['name']}"
                best_prob = max(p_h, p_1x)
            else:
                best_pick = f"Victoire ou Couverture {away_team['name']}"
                best_prob = max(p_a, p_x2)
            tactical_reason = f"Analyse en direct ({score_h}-{score_a}, ~{minute_input}') : Intensité recensée avec tirs cadrés ({sot_h}-{sot_a}) et fautes ({fouls_h + fouls_a}). Les xG restants sont calibrés à {rem_h_xg} pour {home_team['name']} et {rem_a_xg} pour {away_team['name']}."
        else:
            best_pick = f"Double Chance 1X ({home_team['name']} ou Nul)" if p_1x >= p_x2 else f"Double Chance X2 ({away_team['name']} ou Nul)"
            best_prob = max(p_1x, p_x2)
            tactical_reason = f"Analyse d'avant-match : Solide rendement théorique basé sur le classement général et le ratio d'efficacité offensive."

        st.markdown(f"""
        <div class="ai-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span class="badge-ai-safe">🛡️ CONSEIL ORACLE IA • DYNAMIQUE INTENSITÉ</span>
                <span style="color: #A5B4FC; font-weight: bold; font-size: 0.9rem;">RE-CALIBRÉ PAR SHOTS & FAUTES</span>
            </div>
            <h1 style="color: #67E8F9; margin: 5px 0 10px 0; font-size: 1.9rem;">👉 {best_pick}</h1>
            <div style="display: flex; gap: 20px; align-items: center; margin-top: 15px;">
                <div>
                    <span style="color: #94A3B8; font-size: 0.9rem;">Indice de Confiance Réaliste</span>
                    <div style="color: #10B981; font-size: 1.8rem; font-weight: 800;">{best_prob:.1f}%</div>
                </div>
            </div>
            <div class="ai-reason-box">
                <b>🧠 Synthèse Tactique :</b> {tactical_reason}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Top 3 Scores Exacts
        st.markdown('<div class="pro-card">', unsafe_allow_html=True)
        st.markdown("### 🎲 Top 3 Scores Exacts les Plus Probables (Ajustés à l'Intensité)")
        sc1, sc2, sc3 = st.columns(3)
        for col, item in zip([sc1, sc2, sc3], res["top_3_exact_scores"]):
            score_tuple, score_p = item
            with col:
                st.markdown(f"""
                <div class="score-badge">
                    <div style="font-size: 1.4rem; color: #2563EB;">{score_tuple[0]} - {score_tuple[1]}</div>
                    <div style="font-size: 0.85rem; color: #64748B;">Probabilité Exacte : {score_p * 100:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # Cartons et Corners
        st.markdown("### 🚩 & 🟨 Impact Direct sur Corners & Cartons")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Corners Attendus (Temps Restant) :** `{res['corners']['exp_total']}`")
        with c2:
            st.markdown(f"**Cartons Attendus (Ajustés selon Fautes) :** `{res['cards']['exp_total']}`")
else:
    st.warning("Aucun match disponible.")
