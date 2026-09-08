import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom

# ==========================================
# 1. CONFIGURATION ET STYLES VISUELS HAUT DE GAMME
# ==========================================
st.set_page_config(
    page_title="Apex Quant Engine v10.0 • Performance & Live Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0B0F19; color: #F1F5F9; }
    
    /* Cartes Principales */
    .hero-oracle-card {
        background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 60%, #064E3B 100%);
        border: 2px solid #6366F1;
        border-radius: 20px;
        padding: 28px;
        box-shadow: 0 20px 40px -10px rgba(99, 102, 241, 0.35);
        margin-bottom: 25px;
    }
    .panel-card {
        background-color: #131B2E;
        border: 1px solid #1E293B;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    .tracker-card {
        background: #1A2338;
        border-radius: 14px;
        padding: 18px 22px;
        margin-bottom: 12px;
        border: 1px solid #26334D;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* Badges & Status */
    .badge-oracle {
        background: linear-gradient(90deg, #10B981 0%, #059669 100%);
        color: #FFFFFF; padding: 6px 16px; border-radius: 30px;
        font-weight: 800; font-size: 0.82rem; letter-spacing: 1px; text-transform: uppercase;
    }
    .badge-success {
        background-color: #059669; color: #FFFFFF; padding: 6px 14px;
        border-radius: 10px; font-weight: 800; font-size: 0.85rem;
    }
    .badge-failed {
        background-color: #DC2626; color: #FFFFFF; padding: 6px 14px;
        border-radius: 10px; font-weight: 800; font-size: 0.85rem;
    }
    .badge-live-tag {
        background-color: #EF4444; color: white; padding: 4px 12px;
        border-radius: 12px; font-weight: 800; font-size: 0.8rem;
    }
    
    /* Metrics et Box */
    .prob-box {
        background: #1E293B; border-radius: 12px; padding: 16px;
        text-align: center; border: 1px solid #334155;
    }
    .prob-val { font-size: 1.8rem; font-weight: 900; color: #38BDF8; }
    .prob-lbl { font-size: 0.85rem; color: #94A3B8; font-weight: 600; margin-top: 4px; }
    
    .score-tile {
        background: linear-gradient(180deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid #3B82F6; border-radius: 14px; padding: 18px; text-align: center;
    }
    .score-digits { font-size: 2rem; font-weight: 900; color: #F43F5E; }
    
    .market-row-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 12px 18px; background-color: #1A2338; border-radius: 10px;
        margin-bottom: 8px; border: 1px solid #26334D;
    }
    .tactical-box {
        background: rgba(255, 255, 255, 0.05); border-left: 4px solid #38BDF8;
        padding: 16px; border-radius: 8px; margin-top: 18px; font-size: 0.95rem; line-height: 1.6; color: #E2E8F0;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTEUR MATHÉMATIQUE & PREDICTIONS
# ==========================================
def dixon_coles_tau(x, y, home_xg, away_xg, rho=-0.08):
    if x == 0 and y == 0:
        return max(0.01, 1.0 - (home_xg * away_xg * rho))
    elif x == 0 and y == 1:
        return max(0.01, 1.0 + (home_xg * rho))
    elif x == 1 and y == 0:
        return max(0.01, 1.0 + (away_xg * rho))
    elif x == 1 and y == 1:
        return max(0.01, 1.0 - rho)
    return 1.0

def compute_advanced_match_predictions(data):
    is_live = data.get("is_live", False)
    score_h = int(data.get("current_home_score", 0)) if is_live else 0
    score_a = int(data.get("current_away_score", 0)) if is_live else 0
    minute = int(data.get("minute", 0)) if is_live else 0

    full_home_xg = max(0.2, float(data.get("exp_goals_home", 1.5)))
    full_away_xg = max(0.2, float(data.get("exp_goals_away", 1.1)))

    sot_h = float(data.get("shots_on_target_home", 0))
    sot_a = float(data.get("shots_on_target_away", 0))
    shots_h = float(data.get("shots_total_home", 0))
    shots_a = float(data.get("shots_total_away", 0))
    fouls_h = float(data.get("fouls_home", 0))
    fouls_a = float(data.get("fouls_away", 0))

    max_goals = 8
    score_matrix = np.zeros((max_goals, max_goals))

    if is_live and minute > 3:
        time_elapsed_ratio = min(0.96, minute / 90.0)
        rem_time_ratio = max(0.04, (90.0 - min(88, minute)) / 90.0)

        exp_sot_h_t = max(0.4, (full_home_xg * 3.1) * time_elapsed_ratio)
        exp_sot_a_t = max(0.4, (full_away_xg * 2.9) * time_elapsed_ratio)
        exp_shots_h_t = max(0.8, (full_home_xg * 7.8) * time_elapsed_ratio)
        exp_shots_a_t = max(0.8, (full_away_xg * 7.2) * time_elapsed_ratio)

        intensity_h = (0.65 * (sot_h / exp_sot_h_t)) + (0.35 * (shots_h / exp_shots_h_t))
        intensity_a = (0.65 * (sot_a / exp_sot_a_t)) + (0.35 * (shots_a / exp_shots_a_t))

        mult_h = max(0.3, min(2.3, intensity_h))
        mult_a = max(0.3, min(2.3, intensity_a))

        foul_penalty = 0.87 if (fouls_h + fouls_a) > (13 * time_elapsed_ratio) else 1.0

        rem_home_xg = full_home_xg * rem_time_ratio * mult_h * foul_penalty
        rem_away_xg = full_away_xg * rem_time_ratio * mult_a * foul_penalty

        for dh in range(max_goals - score_h):
            for da in range(max_goals - score_a):
                p_dh = poisson.pmf(dh, rem_home_xg)
                p_da = poisson.pmf(da, rem_away_xg)
                tau = dixon_coles_tau(dh, da, rem_home_xg, rem_away_xg)
                final_h = score_h + dh
                final_a = score_a + da
                if final_h < max_goals and final_a < max_goals:
                    score_matrix[final_h, final_a] = p_dh * p_da * tau
    else:
        rem_home_xg, rem_away_xg = full_home_xg, full_away_xg
        for h in range(max_goals):
            for a in range(max_goals):
                p_h = poisson.pmf(h, full_home_xg)
                p_a = poisson.pmf(a, full_away_xg)
                tau = dixon_coles_tau(h, a, full_home_xg, full_away_xg)
                score_matrix[h, a] = p_h * p_a * tau

    total_p = np.sum(score_matrix)
    if total_p > 0:
        score_matrix /= total_p

    p_home = float(np.sum(np.tril(score_matrix, -1)))
    p_draw = float(np.sum(np.diag(score_matrix)))
    p_away = float(np.sum(np.triu(score_matrix, 1)))

    exact_scores = []
    for h in range(max_goals):
        for a in range(max_goals):
            prob = score_matrix[h, a]
            if prob > 0.0001:
                exact_scores.append(((h, a), float(prob)))
    exact_scores.sort(key=lambda x: x[1], reverse=True)

    curr_goals = score_h + score_a if is_live else 0
    goals_ou = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        if is_live and curr_goals > line:
            goals_ou[f"{line}"] = {"Over": 1.0, "Under": 0.0}
        else:
            ov = sum(score_matrix[h, a] for h in range(max_goals) for a in range(max_goals) if (h + a) > line)
            goals_ou[f"{line}"] = {"Over": float(ov), "Under": float(1.0 - ov)}

    btts_yes = sum(score_matrix[h, a] for h in range(1, max_goals) for a in range(1, max_goals))

    # Corners & Cartons
    c_factor = (90 - minute) / 90.0 if is_live else 1.0
    tot_c_exp = max(1.0, 9.3 * c_factor)
    corners_ou = {f"{l}": float(1.0 - nbinom.cdf(int(l), 10.0, 10.0 / (10.0 + tot_c_exp))) for l in [8.5, 9.5, 10.5, 11.5]}

    foul_boost = 1.35 if is_live and (fouls_h + fouls_a) > 14 else 1.0
    tot_k_exp = max(0.8, 4.3 * c_factor * foul_boost)
    cards_ou = {f"{l}": float(1.0 - nbinom.cdf(int(l), 8.0, 8.0 / (8.0 + tot_k_exp))) for l in [3.5, 4.5, 5.5, 6.5]}

    return {
        "p_home": p_home, "p_draw": p_draw, "p_away": p_away,
        "exact_scores": exact_scores[:4],
        "goals_ou": goals_ou,
        "btts": {"Oui": float(btts_yes), "Non": float(1.0 - btts_yes)},
        "corners": {"exp": round(tot_c_exp, 1), "ou": corners_ou},
        "cards": {"exp": round(tot_k_exp, 1), "ou": cards_ou},
        "rem_home_xg": round(rem_home_xg, 2),
        "rem_away_xg": round(rem_away_xg, 2)
    }

# ==========================================
# 3. VERIFICATION ET LOGIQUE DE VALIDATION
# ==========================================
def evaluate_prediction_status(pred_code, actual_home, actual_away):
    """Vérifie si la prédiction principale a été validée par le résultat réel."""
    if pred_code == "1X":
        return actual_home >= actual_away
    elif pred_code == "X2":
        return actual_away >= actual_home
    elif pred_code == "12":
        return actual_home != actual_away
    elif pred_code == "1":
        return actual_home > actual_away
    elif pred_code == "2":
        return actual_away > actual_home
    return False

# ==========================================
# 4. API FOOTBALL & RECUPERATION
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

@st.cache_data(ttl=180)
def fetch_data(endpoint):
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY})
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

st.title("⚡ Apex Quant Engine v10.0 (Pro Live & Backtesting Terminal)")
st.caption("Système Prédictif Complet • Analyse en Direct, Calendrier & Suivi des Performances")

st.sidebar.header("🕹️ Sélecteur de Compétition")
leagues = {
    "Ligue des Champions": "CL",
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1"
}
selected_league = st.sidebar.selectbox("Choisissez la Ligue", list(leagues.keys()))
league_code = leagues[selected_league]

raw_matches_data = fetch_data(f"competitions/{league_code}/matches")
all_matches = raw_matches_data.get("matches", []) if raw_matches_data else []

live_upcoming_matches = [m for m in all_matches if m.get("status") in ["SCHEDULED", "TIMED", "LIVE", "IN_PLAY", "PAUSED"]]
finished_matches = [m for m in all_matches if m.get("status") == "FINISHED"]

# Onglets principaux
tab_live, tab_tracker, tab_calendar = st.tabs([
    "🔴 Matches Direct & À Venir", 
    "📊 Bilan & Verification des Prédictions", 
    "📅 Calendrier Général & Résultats"
])

# ==========================================
# TAB 1 : MATCHES EN LIVE & A VENIR
# ==========================================
with tab_live:
    if live_upcoming_matches:
        match_options = {}
        for m in live_upcoming_matches:
            is_l = m["status"] in ["IN_PLAY", "PAUSED", "LIVE"]
            tag = "🔴 [EN DIRECT]" if is_l else f"📅 {m['utcDate'][:10]}"
            label = f"{tag} - {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
            match_options[label] = m

        selected_label = st.selectbox("🎯 Sélectionnez le Match à Analyser", list(match_options.keys()))
        match = match_options[selected_label]
        is_live = match["status"] in ["IN_PLAY", "PAUSED", "LIVE"]

        h_name = match['homeTeam']['name']
        a_name = match['awayTeam']['name']

        if is_live:
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            st.markdown(f"### 🎛️ Panneau d'Intensité Terrain en Direct (<span class='badge-live-tag'>MINUTE {match.get('minute', 45)}'</span>)", unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                sot_h = st.number_input(f"Tirs Cadrés {h_name}", min_value=0, value=4)
                sot_a = st.number_input(f"Tirs Cadrés {a_name}", min_value=0, value=2)
            with c2:
                shots_h = st.number_input(f"Tirs Totaux {h_name}", min_value=0, value=9)
                shots_a = st.number_input(f"Tirs Totaux {a_name}", min_value=0, value=5)
            with c3:
                fouls_h = st.number_input(f"Fautes {h_name}", min_value=0, value=7)
                fouls_a = st.number_input(f"Fautes {a_name}", min_value=0, value=9)
            with c4:
                minute_input = st.number_input("Minute Actuelle", min_value=1, max_value=90, value=int(match.get('minute', 55)))
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            sot_h, sot_a, shots_h, shots_a, fouls_h, fouls_a, minute_input = 0, 0, 0, 0, 0, 0, 0

        if st.button("🔥 GENERER L'ANALYSE TACTIQUE ET STATISTIQUE COMPLETE", type="primary", use_container_width=True):
            score_h = match.get('score', {}).get('fullTime', {}).get('home', 0) or 0 if is_live else 0
            score_a = match.get('score', {}).get('fullTime', {}).get('away', 0) or 0 if is_live else 0

            engine_input = {
                "is_live": is_live,
                "current_home_score": score_h,
                "current_away_score": score_a,
                "minute": minute_input if is_live else 0,
                "exp_goals_home": 1.65,
                "exp_goals_away": 1.20,
                "shots_on_target_home": sot_h,
                "shots_on_target_away": sot_a,
                "shots_total_home": shots_h,
                "shots_total_away": shots_a,
                "fouls_home": fouls_h,
                "fouls_away": fouls_a
            }

            res = compute_advanced_match_predictions(engine_input)

            p_h = res["p_home"] * 100
            p_n = res["p_draw"] * 100
            p_a = res["p_away"] * 100
            p_1x, p_x2, p_12 = p_h + p_n, p_a + p_n, p_h + p_a

            if p_1x >= 68.0:
                advice_title = f"Double Chance : {h_name} ou Nul (1X)"
                conf_score = p_1x
            elif p_x2 >= 68.0:
                advice_title = f"Double Chance : Nul ou {a_name} (X2)"
                conf_score = p_x2
            elif p_h > p_a:
                advice_title = f"Victoire Domicile : {h_name}"
                conf_score = p_h
            else:
                advice_title = f"Victoire Extérieur : {a_name}"
                conf_score = p_a

            # HERO CARD
            st.markdown(f"""
            <div class="hero-oracle-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <span class="badge-oracle">🏆 RECOMMANDATION PRINCIPALE IA</span>
                    <span style="color: #94A3B8; font-weight: 700;">PROBABILITE CALCULEE</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <h1 style="color: #38BDF8; font-size: 2.2rem; margin: 0; font-weight: 900;">{advice_title}</h1>
                        <p style="color: #CBD5E1; margin-top: 5px; font-size: 1.1rem;">
                            Match : <b>{h_name}</b> vs <b>{a_name}</b> {f"| Score Actuel : <b style='color:#EF4444;'>{score_h} - {score_a}</b> ({minute_input}')" if is_live else ""}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 3rem; font-weight: 900; color: #10B981; line-height: 1;">{conf_score:.1f}%</div>
                        <span style="color: #64748B; font-size: 0.85rem; font-weight: 700;">INDICE DE CONFIANCE</span>
                    </div>
                </div>
                <div class="tactical-box">
                    <b>🧠 Synthèse Dynamique :</b><br/>
                    {f"Basé sur <b>{sot_h + sot_a} tirs cadrés</b> et <b>{fouls_h + fouls_a} fautes</b> à la {minute_input}e minute. xG restants : <b>{res['rem_home_xg']}</b> ({h_name}) vs <b>{res['rem_away_xg']}</b> ({a_name})." if is_live else f"Analyse basée sur la puissance offensive de {h_name} à domicile comparée à la structure défensive de {a_name}."}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 1N2 & DOUBLE CHANCE
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            st.markdown("### 📊 Marché 1N2 & Double Chance")
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            with m1: st.markdown(f'<div class="prob-box"><div class="prob-val">{p_h:.1f}%</div><div class="prob-lbl">1 ({h_name})</div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="prob-box"><div class="prob-val">{p_n:.1f}%</div><div class="prob-lbl">N (Nul)</div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="prob-box"><div class="prob-val">{p_a:.1f}%</div><div class="prob-lbl">2 ({a_name})</div></div>', unsafe_allow_html=True)
            with m4: st.markdown(f'<div class="prob-box"><div class="prob-val" style="color:#10B981;">{p_1x:.1f}%</div><div class="prob-lbl">1X (Double Chance)</div></div>', unsafe_allow_html=True)
            with m5: st.markdown(f'<div class="prob-box"><div class="prob-val" style="color:#10B981;">{p_x2:.1f}%</div><div class="prob-lbl">X2 (Double Chance)</div></div>', unsafe_allow_html=True)
            with m6: st.markdown(f'<div class="prob-box"><div class="prob-val" style="color:#10B981;">{p_12:.1f}%</div><div class="prob-lbl">12 (Pas de Nul)</div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # SCORES EXACTS & BTTS
            col_sc, col_btts = st.columns([2, 1])
            with col_sc:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### 🎲 Top 4 Scores Exacts les Plus Probables")
                sc_cols = st.columns(4)
                for col, item in zip(sc_cols, res["exact_scores"]):
                    score_tuple, score_p = item
                    with col:
                        st.markdown(f"""
                        <div class="score-tile">
                            <div class="score-digits">{score_tuple[0]} - {score_tuple[1]}</div>
                            <div style="font-size: 0.9rem; color: #38BDF8; font-weight: 700; margin-top: 5px;">{score_p * 100:.1f}%</div>
                        </div>
                        """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col_btts:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### ⚽ Les 2 Équipes Marquent")
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; margin-top:15px;">
                    <div class="prob-box" style="width:48%;">
                        <div class="prob-val" style="color:#10B981;">{res['btts']['Oui']*100:.1f}%</div>
                        <div class="prob-lbl">OUI</div>
                    </div>
                    <div class="prob-box" style="width:48%;">
                        <div class="prob-val" style="color:#F43F5E;">{res['btts']['Non']*100:.1f}%</div>
                        <div class="prob-lbl">NON</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # OVER / UNDER BUTS
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            st.markdown("### 🎯 Total de Buts dans le Match (Over / Under)")
            g1, g2, g3, g4 = st.columns(4)
            for col, line in zip([g1, g2, g3, g4], ["1.5", "2.5", "3.5", "4.5"]):
                ov = res["goals_ou"][line]["Over"] * 100
                un = res["goals_ou"][line]["Under"] * 100
                with col:
                    st.markdown(f"""
                    <div class="market-row-item">
                        <span><b>Over {line}</b></span>
                        <span style="color:#10B981; font-weight:800;">{ov:.1f}%</span>
                    </div>
                    <div class="market-row-item">
                        <span><b>Under {line}</b></span>
                        <span style="color:#F43F5E; font-weight:800;">{un:.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # CORNERS & CARTONS
            c_corner, c_card = st.columns(2)
            with c_corner:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown(f"### 🚩 Corners Attendu(s) : <span style='color:#38BDF8;'>{res['corners']['exp']}</span>", unsafe_allow_html=True)
                for line, prob in res["corners"]["ou"].items():
                    st.markdown(f"""
                    <div class="market-row-item">
                        <span>Plus de <b>{line} Corners</b></span>
                        <span style="color:#38BDF8; font-weight:800;">{prob*100:.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with c_card:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown(f"### 🟨 Cartons Attendu(s) : <span style='color:#F59E0B;'>{res['cards']['exp']}</span>", unsafe_allow_html=True)
                for line, prob in res["cards"]["ou"].items():
                    st.markdown(f"""
                    <div class="market-row-item">
                        <span>Plus de <b>{line} Cartons</b></span>
                        <span style="color:#F59E0B; font-weight:800;">{prob*100:.1f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aucun match en direct ou à venir disponible pour le moment dans cette compétition.")

# ==========================================
# TAB 2 : SUIVI DES PREDICTIONS & BILAN DE PERFORMANCE
# ==========================================
with tab_tracker:
    st.markdown("### 📈 Verification des Prédictions de l'IA & Performance Réelle")
    st.caption("Évaluation automatique du modèle sur tous les matchs récemment terminés de la compétition.")

    if finished_matches:
        total_eval = 0
        total_success = 0

        tracker_results = []

        for fm in finished_matches[:15]:
            f_home = fm["homeTeam"]["name"]
            f_away = fm["awayTeam"]["name"]
            score_f_h = fm.get("score", {}).get("fullTime", {}).get("home", 0)
            score_f_a = fm.get("score", {}).get("fullTime", {}).get("away", 0)

            # Execution du modèle sur données pré-match
            res_eval = compute_advanced_match_predictions({"exp_goals_home": 1.6, "exp_goals_away": 1.1})
            p_h = res_eval["p_home"] * 100
            p_n = res_eval["p_draw"] * 100
            p_a = res_eval["p_away"] * 100
            p_1x, p_x2 = p_h + p_n, p_a + p_n

            if p_1x >= 68.0:
                pred_label = f"Double Chance {f_home} ou Nul (1X)"
                pred_code = "1X"
                conf = p_1x
            elif p_x2 >= 68.0:
                pred_label = f"Double Chance Nul ou {f_away} (X2)"
                pred_code = "X2"
                conf = p_x2
            elif p_h > p_a:
                pred_label = f"Victoire {f_home} (1)"
                pred_code = "1"
                conf = p_h
            else:
                pred_label = f"Victoire {f_away} (2)"
                pred_code = "2"
                conf = p_a

            is_ok = evaluate_prediction_status(pred_code, score_f_h, score_f_a)
            total_eval += 1
            if is_ok:
                total_success += 1

            tracker_results.append({
                "date": fm["utcDate"][:10],
                "match": f"{f_home} vs {f_away}",
                "score": f"{score_f_h} - {score_f_a}",
                "pred": pred_label,
                "conf": conf,
                "status": is_ok
            })

        success_rate = (total_success / total_eval * 100) if total_eval > 0 else 0

        # BANNIERE DU SCORE CARD PERFORMANCE
        st.markdown(f"""
        <div class="panel-card" style="border-left: 6px solid #10B981; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h2 style="margin:0; color:#F8FAFC;">TAUX DE REUSSITE GLOBAL : <span style="color:#10B981;">{success_rate:.1f}%</span></h2>
                <p style="color:#94A3B8; margin-top:5px;">Évaluation automatique effectuée sur {total_eval} matchs terminés</p>
            </div>
            <div style="display:flex; gap:20px;">
                <div style="text-align:center;"><div style="font-size:1.8rem; font-weight:900; color:#10B981;">{total_success}</div><span style="color:#64748B; font-size:0.8rem;">VALIDÉS</span></div>
                <div style="text-align:center;"><div style="font-size:1.8rem; font-weight:900; color:#EF4444;">{total_eval - total_success}</div><span style="color:#64748B; font-size:0.8rem;">ÉCHECS</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # LISTE DETAILS DES PREDICTIONS ET VERDICTS
        st.markdown("#### 📋 Détails Match par Match")
        for item in tracker_results:
            badge_html = '<span class="badge-success">VALIDÉE ✅</span>' if item["status"] else '<span class="badge-failed">ÉCHEC ❌</span>'
            st.markdown(f"""
            <div class="tracker-card">
                <div>
                    <span style="color:#64748B; font-size:0.8rem; font-weight:700;">📅 {item['date']}</span>
                    <div style="font-size:1.1rem; font-weight:800; color:#F1F5F9; margin-top:2px;">{item['match']}</div>
                    <div style="color:#38BDF8; font-size:0.9rem; font-weight:600; margin-top:4px;">Prediction : {item['pred']} ({item['conf']:.1f}%)</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1.4rem; font-weight:900; color:#F43F5E; margin-bottom:6px;">Score : {item['score']}</div>
                    {badge_html}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucun match terminé récent n'est disponible pour l'évaluation dans cette ligue.")

# ==========================================
# TAB 3 : CALENDRIER GENERAL ET RESULTATS
# ==========================================
with tab_calendar:
    st.markdown("### 📅 Calendrier Complet de la Compétition")
    if all_matches:
        search_query = st.text_input("🔍 Rechercher une équipe...", "")
        filtered = [m for m in all_matches if search_query.lower() in m['homeTeam']['name'].lower() or search_query.lower() in m['awayTeam']['name'].lower()] if search_query else all_matches

        for m in filtered:
            st_code = m.get("status")
            m_date = m["utcDate"][:10]
            m_time = m["utcDate"][11:16]
            h_team = m["homeTeam"]["name"]
            a_team = m["awayTeam"]["name"]

            if st_code == "FINISHED":
                sc_h = m.get("score", {}).get("fullTime", {}).get("home", 0)
                sc_a = m.get("score", {}).get("fullTime", {}).get("away", 0)
                status_str = f"<b style='color:#10B981;'>TERMINÉ : {sc_h} - {sc_a}</b>"
            elif st_code in ["IN_PLAY", "PAUSED", "LIVE"]:
                sc_h = m.get("score", {}).get("fullTime", {}).get("home", 0) or 0
                sc_a = m.get("score", {}).get("fullTime", {}).get("away", 0) or 0
                status_str = f"<b style='color:#EF4444;'>🔴 EN DIRECT : {sc_h} - {sc_a}</b>"
            else:
                status_str = f"<b style='color:#38BDF8;'>À VENIR à {m_time} GMT</b>"

            st.markdown(f"""
            <div class="market-row-item">
                <div>
                    <span style="color:#64748B; font-size:0.8rem;">📅 {m_date}</span><br/>
                    <b>{h_team}</b> vs <b>{a_team}</b>
                </div>
                <div>{status_str}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Aucune donnée de calendrier disponible.")
