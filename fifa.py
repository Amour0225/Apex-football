import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
import requests
import math
from datetime import datetime

# ---------------------------------------------------------
# 1. CONFIGURATION & DESIGN PREMIUM
# ---------------------------------------------------------
st.set_page_config(
    page_title="Apex Intelligence — Fully Automated Predictor",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    .stApp {
        background-color: #f8fafc;
        color: #0f172a;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .live-badge {
        background-color: #ef4444;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
        animation: blinker 1.5s linear infinite;
    }
    .prematch-badge {
        background-color: #3b82f6;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        display: inline-block;
    }
    @keyframes blinker {
        50% { opacity: 0.4; }
    }
    .metric-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .score-card-gold {
        background: #ffffff;
        border: 2px solid #10b981;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .score-card-sub {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Apex Intelligence Engine")
st.caption("Moteur d'analyse autonome : Probabilités 1N2, Scores Exacts, Corners & Cartons en temps réel")
st.markdown("---")

# ---------------------------------------------------------
# 2. API & EXTRACTION DES MATCHS EN DIRECT ET À VENIR
# ---------------------------------------------------------
FOOTBALL_API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"
headers = {"X-Auth-Token": FOOTBALL_API_KEY}

COMPETITIONS = {
    "🇫🇷 Ligue 1": "FL1",
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": "PL",
    "🇪🇸 La Liga": "PD",
    "🇮🇹 Serie A": "SA",
    "🇩🇪 Bundesliga": "BL1"
}

@st.cache_data(ttl=300)
def fetch_matches_by_league(league_code):
    """Récupère les matchs récents et à venir pour détecter le statut en temps réel."""
    url = f"{BASE_URL}competitions/{league_code}/matches"
    try:
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code == 200:
            return response.json().get("matches", [])
    except Exception:
        pass
    return []

@st.cache_data(ttl=1800)
def get_team_historical_stats(team_id):
    """Calcule l'efficacité moyenne basée sur les 10 derniers matchs réels."""
    url = f"{BASE_URL}teams/{team_id}/matches?status=FINISHED&limit=10"
    try:
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code == 200:
            matches = response.json().get("matches", [])
            scored_h, conceded_h, count_h = 0, 0, 0
            scored_a, conceded_a, count_a = 0, 0, 0
            
            for m in matches:
                score = m.get("score", {}).get("fullTime", {})
                is_home = m.get("homeTeam", {}).get("id") == team_id
                h_g = score.get("home", 0) or 0
                a_g = score.get("away", 0) or 0
                
                if is_home:
                    scored_h += h_g
                    conceded_h += a_g
                    count_h += 1
                else:
                    scored_a += a_g
                    conceded_a += h_g
                    count_a += 1

            att_dom = (scored_h / count_h) if count_h > 0 else 1.3
            def_dom = (conceded_h / count_h) if count_h > 0 else 1.1
            att_ext = (scored_a / count_a) if count_a > 0 else 1.0
            def_ext = (conceded_a / count_a) if count_a > 0 else 1.4

            return {"att_dom": att_dom, "def_dom": def_dom, "att_ext": att_ext, "def_ext": def_ext}
    except Exception:
        pass
    return {"att_dom": 1.3, "def_dom": 1.1, "att_ext": 1.0, "def_ext": 1.4}

def poisson_probability(lmbda, k):
    return (math.pow(lmbda, k) * math.exp(-lmbda)) / math.factorial(k)

# ---------------------------------------------------------
# 3. SÉLECTION DU CHAMPIONNAT ET DU MATCH
# ---------------------------------------------------------
st.subheader("📋 Sélection Automatisée de la Rencontre")

league_label = st.selectbox("Choisir le Championnat :", list(COMPETITIONS.keys()))
matches_list = fetch_matches_by_league(COMPETITIONS[league_label])

if matches_list:
    match_options = {}
    for m in matches_list:
        h_team = m.get("homeTeam", {}).get("name", "Équipe A")
        a_team = m.get("awayTeam", {}).get("name", "Équipe B")
        status = m.get("status", "SCHEDULED")
        
        status_str = "🔴 LIVE" if status in ["IN_PLAY", "PAUSED"] else "📅 À venir / Programmé"
        label = f"{h_team} vs {a_team} ({status_str})"
        match_options[label] = m

    selected_label = st.selectbox("Sélectionner le Match :", list(match_options.keys()))
    match_data = match_options[selected_label]

    home_team = match_data.get("homeTeam", {})
    away_team = match_data.get("awayTeam", {})
    match_status = match_data.get("status", "SCHEDULED")

    is_live = match_status in ["IN_PLAY", "PAUSED"]
    live_score = match_data.get("score", {}).get("fullTime", {})
    live_h = live_score.get("home") if live_score.get("home") is not None else 0
    live_a = live_score.get("away") if live_score.get("away") is not None else 0

    st.markdown("---")

    # ---------------------------------------------------------
    # 4. MOTEUR D'ANALYSE INTELLIGENT
    # ---------------------------------------------------------
    if st.button("🚀 Lancer l'Analyse Apex Complete", type="primary"):
        
        # Récupération des données historiques
        stats_h = get_team_historical_stats(home_team.get("id"))
        stats_a = get_team_historical_stats(away_team.get("id"))

        # Calcul des espérances de buts (xG) de base
        xg_dom = round(stats_h['att_dom'] * stats_a['def_ext'] * 1.1, 2)
        xg_ext = round(stats_a['att_ext'] * stats_h['def_dom'], 2)

        # Ajustement en direct si le match a démarré (Tendance In-Play)
        if is_live:
            st.markdown(f'<span class="live-badge">🔴 MATCH EN COURS EN DIRECT — Score actuel : {live_h} - {live_a}</span>', unsafe_allow_html=True)
            st.write("")
            # Pondération dynamique du xG selon le score actuel
            xg_dom = round((xg_dom * 0.5) + (live_h * 0.5) + 0.3, 2)
            xg_ext = round((xg_ext * 0.5) + (live_a * 0.5) + 0.2, 2)
        else:
            st.markdown('<span class="prematch-badge">📅 MATCH NON COMMENCÉ (Avant-Match)</span>', unsafe_allow_html=True)
            st.write("")

        # Simulation de la Matrice de Poisson (0 à 6 buts)
        prob_win_h, prob_draw, prob_win_a = 0, 0, 0
        score_matrix = []

        for g_h in range(7):
            for g_a in range(7):
                p = poisson_probability(xg_dom, g_h) * poisson_probability(xg_ext, g_a)
                score_matrix.append({"score": f"{g_h} - {g_a}", "prob": p})
                
                if g_h > g_a:
                    prob_win_h += p
                elif g_h == g_a:
                    prob_draw += p
                else:
                    prob_win_a += p

        pct_win_h = round(prob_win_h * 100, 1)
        pct_draw = round(prob_draw * 100, 1)
        pct_win_a = round(prob_win_a * 100, 1)

        sorted_scores = sorted(score_matrix, key=lambda x: x["prob"], reverse=True)
        top_1 = {"score": sorted_scores[0]["score"], "prob": round(sorted_scores[0]["prob"] * 100, 1)}
        top_2 = {"score": sorted_scores[1]["score"], "prob": round(sorted_scores[1]["prob"] * 100, 1)}
        top_3 = {"score": sorted_scores[2]["score"], "prob": round(sorted_scores[2]["prob"] * 100, 1)}

        # ---------------------------------------------------------
        # SECTION 1 : PROBABILITÉS DE VICTOIRE (1N2)
        # ---------------------------------------------------------
        st.markdown(f"### 📊 1. Probabilités d'Issue du Match (1N2)")
        
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Victoire {home_team.get('name')}", f"{pct_win_h} %", f"xG : {xg_dom}")
        c2.metric("Match Nul", f"{pct_draw} %", "Équilibre")
        c3.metric(f"Victoire {away_team.get('name')}", f"{pct_win_a} %", f"xG : {xg_ext}")

        # ---------------------------------------------------------
        # SECTION 2 : SCORES EXACTS LES PLUS PROBABLES
        # ---------------------------------------------------------
        st.markdown("---")
        st.markdown("### 🎯 2. Top 3 des Scores Exacts les Plus Probables")

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.markdown(f"""
            <div class="score-card-gold">
                <span style="color: #10b981; font-weight: 700; font-size: 0.85rem;">🥇 N°1 PLUS PROBABLE</span>
                <h1 style="margin: 10px 0; font-size: 2.8rem; color: #0f172a;">{top_1['score']}</h1>
                <p style="margin: 0; font-weight: 600; color: #059669;">Probabilité : {top_1['prob']} %</p>
            </div>
            """, unsafe_allow_html=True)

        with sc2:
            st.markdown(f"""
            <div class="score-card-sub">
                <span style="color: #64748b; font-weight: 700; font-size: 0.85rem;">🥈 ALTERNATIVE N°2</span>
                <h1 style="margin: 10px 0; font-size: 2.5rem; color: #334155;">{top_2['score']}</h1>
                <p style="margin: 0; font-weight: 600; color: #475569;">Probabilité : {top_2['prob']} %</p>
            </div>
            """, unsafe_allow_html=True)

        with sc3:
            st.markdown(f"""
            <div class="score-card-sub">
                <span style="color: #64748b; font-weight: 700; font-size: 0.85rem;">🥉 ALTERNATIVE N°3</span>
                <h1 style="margin: 10px 0; font-size: 2.5rem; color: #334155;">{top_3['score']}</h1>
                <p style="margin: 0; font-weight: 600; color: #475569;">Probabilité : {top_3['prob']} %</p>
            </div>
            """, unsafe_allow_html=True)

        # ---------------------------------------------------------
        # SECTION 3 : PRÉDICTION CORNERS (INTELLIGENTE & SANS SAISIE)
        # ---------------------------------------------------------
        st.markdown("---")
        st.markdown("### 🚩 3. Prédiction Algorithmique des Corners")

        # Estimation basée sur le xG et l'intensité offensive calculée
        est_corners_dom = round((stats_h['att_dom'] * 3.6) + (0.5 if is_live and live_h > 0 else 0), 1)
        est_corners_ext = round((stats_a['att_ext'] * 3.1) + (0.5 if is_live and live_a > 0 else 0), 1)
        total_corners = round(est_corners_dom + est_corners_ext, 1)

        cr1, cr2, cr3 = st.columns(3)
        cr1.metric(f"Corners {home_team.get('name')}", f"~ {est_corners_dom}", "Attente Dom.")
        cr2.metric(f"Corners {away_team.get('name')}", f"~ {est_corners_ext}", "Attente Ext.")
        cr3.metric("Total Corners Prévus", f"{total_corners}", "Moyenne Match")

        if total_corners >= 9.5:
            prono_corner = "**Plus de 8.5 Corners dans le match** (Ligne haute - Pression offensive forte)"
        elif total_corners >= 8.0:
            prono_corner = "**Plus de 7.5 Corners dans le match** (Fiabilité Élevée)"
        else:
            prono_corner = "**Moins de 9.5 Corners dans le match** (Jeu axial privilégié)"

        st.info(f"💡 **Pronostic Corners Automatique :** {prono_corner}")

        # ---------------------------------------------------------
        # SECTION 4 : PRÉDICTION CARTONS & TENSION
        # ---------------------------------------------------------
        st.markdown("---")
        st.markdown("### 🟨 4. Prédiction de la Discipline & Cartons")

        # Calcul automatique de la tension basé sur le différentiel d'efficacité et le statut live
        tension_factor = abs(stats_h['att_dom'] - stats_a['att_ext']) + (1.2 if is_live else 0.8)
        est_cards_dom = round(1.8 + (tension_factor * 0.4), 1)
        est_cards_ext = round(2.0 + (tension_factor * 0.5), 1)
        total_cards = round(est_cards_dom + est_cards_ext, 1)

        cd1, cd2, cd3 = st.columns(3)
        cd1.metric(f"Cartons {home_team.get('name')}", f"~ {est_cards_dom}", "Jaunes/Rouges")
        cd2.metric(f"Cartons {away_team.get('name')}", f"~ {est_cards_ext}", "Jaunes/Rouges")
        cd3.metric("Total Cartons Prévus", f"{total_cards}", "Indice de Tension")

        if total_cards >= 4.5:
            prono_card = "**Plus de 3.5 Cartons dans le match** (Tension élevée / Match engagé)"
        else:
            prono_card = "**Moins de 4.5 Cartons dans le match** (Match fluide / Faible engagement)"

        st.warning(f"📌 **Pronostic Cartons Automatique :** {prono_card}")
else:
    st.warning("Chargement des rencontres en cours ou aucune rencontre trouvée pour cette compétition.")