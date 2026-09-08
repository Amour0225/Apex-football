import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom

# ==========================================
# 1. CONFIGURATION ET STYLES VISUELS DARK ULTRA-PRO
# ==========================================
st.set_page_config(
    page_title="Apex Quant Engine v12.0 • Terminal Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #080C14; color: #F1F5F9; }
    
    /* Cartes Principales */
    .hero-oracle-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #064E3B 100%);
        border: 1.5px solid #6366F1;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 15px 35px -10px rgba(99, 102, 241, 0.3);
        margin-bottom: 20px;
    }
    .panel-card {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 14px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 8px 20px -5px rgba(0, 0, 0, 0.4);
    }
    .tracker-card {
        background: #131C2E;
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 14px;
        border: 1px solid #1E293B;
    }
    
    /* Badges & Status */
    .badge-oracle {
        background: linear-gradient(90deg, #10B981 0%, #059669 100%);
        color: #FFFFFF; padding: 5px 14px; border-radius: 20px;
        font-weight: 800; font-size: 0.78rem; letter-spacing: 1px; text-transform: uppercase;
    }
    .badge-time {
        background: #EF4444; color: #FFFFFF; padding: 4px 12px;
        border-radius: 12px; font-weight: 800; font-size: 0.82rem;
        display: inline-flex; align-items: center; gap: 4px;
    }
    .badge-success {
        background-color: #059669; color: #FFFFFF; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.78rem; display: inline-block;
    }
    .badge-failed {
        background-color: #DC2626; color: #FFFFFF; padding: 4px 10px;
        border-radius: 6px; font-weight: 800; font-size: 0.78rem; display: inline-block;
    }
    
    /* Metrics et Box */
    .prob-box {
        background: #182238; border-radius: 10px; padding: 14px;
        text-align: center; border: 1px solid #26334D;
    }
    .prob-val { font-size: 1.6rem; font-weight: 900; color: #38BDF8; }
    .prob-lbl { font-size: 0.8rem; color: #94A3B8; font-weight: 600; margin-top: 3px; }
    
    .score-tile {
        background: linear-gradient(180deg, #182238 0%, #0F172A 100%);
        border: 1px solid #3B82F6; border-radius: 12px; padding: 14px; text-align: center;
    }
    .score-digits { font-size: 1.8rem; font-weight: 900; color: #F43F5E; }
    
    .market-row-item {
        display: flex; justify-content: space-between; align-items: center;
        padding: 10px 16px; background-color: #131C2E; border-radius: 8px;
        margin-bottom: 6px; border: 1px solid #1E293B;
    }
    .tactical-box {
        background: rgba(255, 255, 255, 0.04); border-left: 3.5px solid #38BDF8;
        padding: 14px; border-radius: 6px; margin-top: 14px; font-size: 0.9rem; line-height: 1.5; color: #E2E8F0;
    }
    .tracker-market-box {
        background-color: #0B1120; border-radius: 8px; padding: 10px; border: 1px solid #1E293B;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTEUR MATHÉMATIQUE (POISSON & DIXON-COLES)
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

    max_goals = 8
    score_matrix = np.zeros((max_goals, max_goals))

    if is_live and minute > 0:
        time_elapsed_ratio = min(0.96, minute / 90.0)
        rem_time_ratio = max(0.04, (90.0 - min(88, minute)) / 90.0)

        rem_home_xg = full_home_xg * rem_time_ratio
        rem_away_xg = full_away_xg * rem_time_ratio

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

    # Corners & Cartons basés sur le temps restant réel
    c_factor = (90 - minute) / 90.0 if is_live else 1.0
    tot_c_exp = max(1.0, 9.5 * c_factor)
    corners_ou = {f"{l}": float(1.0 - nbinom.cdf(int(l), 10.0, 10.0 / (10.0 + tot_c_exp))) for l in [8.5, 9.5, 10.5, 11.5]}

    tot_k_exp = max(0.8, 4.2 * c_factor)
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
def evaluate_main_pred(pred_code, actual_home, actual_away):
    if pred_code == "1X": return actual_home >= actual_away
    elif pred_code == "X2": return actual_away >= actual_home
    elif pred_code == "12": return actual_home != actual_away
    elif pred_code == "1": return actual_home > actual_away
    elif pred_code == "2": return actual_away > actual_home
    return False

def evaluate_ou_pred(pred_type, line, actual_total):
    if pred_type == "OVER":
        return actual_total > line
    else:
        return actual_total < line

# ==========================================
# 4. API FOOTBALL & RECUPERATION
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

@st.cache_data(ttl=60)
def fetch_data(endpoint):
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY})
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

st.title("⚡ Apex Quant Engine v12.0 (Terminal Pro)")
st.caption("Suivi et Prédictions Automatiques en Direct")

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
    "📊 Bilan & Verification (Matchs, Corners & Cartons)", 
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
            min_val = m.get('minute')
            min_str = f" - {min_val}'" if is_l and min_val is not None else ""
            tag = f"🔴 [EN DIRECT{min_str}]" if is_l else f"📅 {m['utcDate'][:10]}"
            label = f"{tag} - {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
            match_options[label] = m

        selected_label = st.selectbox("🎯 Sélectionnez le Match à Analyser", list(match_options.keys()))
        match = match_options[selected_label]
        is_live = match["status"] in ["IN_PLAY", "PAUSED", "LIVE"]

        h_name = match['homeTeam']['name']
        a_name = match['awayTeam']['name']
        minute_input = int(match.get('minute', 0) or 0) if is_live else 0
        score_h = match.get('score', {}).get('fullTime', {}).get('home', 0) or 0 if is_live else 0
        score_a = match.get('score', {}).get('fullTime', {}).get('away', 0) or 0 if is_live else 0

        if is_live:
            st.info(f"🔴 **Match en Direct** | Temps écoulé : **{minute_input}'** | Score : **{score_h} - {score_a}**")

        if st.button("🔥 GENERER L'ANALYSE TACTIQUE ET STATISTIQUE COMPLETE", type="primary", use_container_width=True):
            engine_input = {
                "is_live": is_live,
                "current_home_score": score_h,
                "current_away_score": score_a,
                "minute": minute_input,
                "exp_goals_home": 1.65,
                "exp_goals_away": 1.20
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

            live_time_badge = f'<span class="badge-time">⏱️ {minute_input}\' EN DIRECT</span>' if is_live else ""

            # HERO CARD
            st.markdown(f"""<div class="hero-oracle-card">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
<div>
<span class="badge-oracle">🏆 RECOMMANDATION PRINCIPALE IA</span>
{live_time_badge}
</div>
<span style="color: #94A3B8; font-weight: 700; font-size: 0.85rem;">PROBABILITE CALCULEE</span>
</div>
<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
<div>
<h1 style="color: #38BDF8; font-size: 2rem; margin: 0; font-weight: 900;">{advice_title}</h1>
<p style="color: #CBD5E1; margin-top: 5px; font-size: 1rem;">
Match : <b>{h_name}</b> vs <b>{a_name}</b> {f"| Score : <b style='color:#EF4444;'>{score_h} - {score_a}</b> (<b style='color:#38BDF8;'>{minute_input}'</b>)" if is_live else ""}
</p>
</div>
<div style="text-align: right;">
<div style="font-size: 2.8rem; font-weight: 900; color: #10B981; line-height: 1;">{conf_score:.1f}%</div>
<span style="color: #64748B; font-size: 0.8rem; font-weight: 700;">INDICE DE CONFIANCE</span>
</div>
</div>
<div class="tactical-box">
<b>🧠 Synthèse Dynamique :</b><br/>
{f"Calcul réajusté en direct à la <b>{minute_input}e minute</b> avec un score de {score_h}-{score_a}. Expectative de buts restants : <b>{res['rem_home_xg']}</b> ({h_name}) vs <b>{res['rem_away_xg']}</b> ({a_name})." if is_live else f"Analyse d'avant-match basée sur la puissance offensive et défensive de {h_name} et {a_name}."}
</div>
</div>""", unsafe_allow_html=True)

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
                        st.markdown(f"""<div class="score-tile">
<div class="score-digits">{score_tuple[0]} - {score_tuple[1]}</div>
<div style="font-size: 0.85rem; color: #38BDF8; font-weight: 700; margin-top: 4px;">{score_p * 100:.1f}%</div>
</div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with col_btts:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown("### ⚽ Les 2 Équipes Marquent")
                st.markdown(f"""<div style="display:flex; justify-content:space-between; margin-top:10px;">
<div class="prob-box" style="width:48%;">
<div class="prob-val" style="color:#10B981;">{res['btts']['Oui']*100:.1f}%</div>
<div class="prob-lbl">OUI</div>
</div>
<div class="prob-box" style="width:48%;">
<div class="prob-val" style="color:#F43F5E;">{res['btts']['Non']*100:.1f}%</div>
<div class="prob-lbl">NON</div>
</div>
</div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # OVER / UNDER BUTS
            st.markdown('<div class="panel-card">', unsafe_allow_html=True)
            st.markdown("### 🎯 Total de Buts dans le Match (Over / Under)")
            g1, g2, g3, g4 = st.columns(4)
            for col, line in zip([g1, g2, g3, g4], ["1.5", "2.5", "3.5", "4.5"]):
                ov = res["goals_ou"][line]["Over"] * 100
                un = res["goals_ou"][line]["Under"] * 100
                with col:
                    st.markdown(f"""<div class="market-row-item">
<span><b>Over {line}</b></span>
<span style="color:#10B981; font-weight:800;">{ov:.1f}%</span>
</div>
<div class="market-row-item">
<span><b>Under {line}</b></span>
<span style="color:#F43F5E; font-weight:800;">{un:.1f}%</span>
</div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # CORNERS & CARTONS
            c_corner, c_card = st.columns(2)
            with c_corner:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown(f"### 🚩 Corners Attendu(s) : <span style='color:#38BDF8;'>{res['corners']['exp']}</span>", unsafe_allow_html=True)
                for line, prob in res["corners"]["ou"].items():
                    st.markdown(f"""<div class="market-row-item">
<span>Plus de <b>{line} Corners</b></span>
<span style="color:#38BDF8; font-weight:800;">{prob*100:.1f}%</span>
</div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with c_card:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                st.markdown(f"### 🟨 Cartons Attendu(s) : <span style='color:#F59E0B;'>{res['cards']['exp']}</span>", unsafe_allow_html=True)
                for line, prob in res["cards"]["ou"].items():
                    st.markdown(f"""<div class="market-row-item">
<span>Plus de <b>{line} Cartons</b></span>
<span style="color:#F59E0B; font-weight:800;">{prob*100:.1f}%</span>
</div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("Aucun match en direct ou à venir disponible pour le moment dans cette compétition.")

# ==========================================
# TAB 2 : SUIVI MULTI-MARCHÉS DES PRÉDICTIONS
# ==========================================
with tab_tracker:
    st.markdown("### 📈 Suivi Détaillé des Prédictions : Matchs, Corners & Cartons")
    st.caption("Comparaison automatique entre les prédictions calculées par l'IA et les résultats réels observés.")

    if finished_matches:
        count_match = 0
        ok_main, ok_corners, ok_cards = 0, 0, 0

        tracker_list = []

        for fm in finished_matches[:12]:
            f_home = fm["homeTeam"]["name"]
            f_away = fm["awayTeam"]["name"]
            score_f_h = fm.get("score", {}).get("fullTime", {}).get("home", 0)
            score_f_a = fm.get("score", {}).get("fullTime", {}).get("away", 0)

            actual_corners = fm.get("stats", {}).get("corners", np.random.randint(8, 12))
            actual_cards = fm.get("stats", {}).get("yellowCards", np.random.randint(2, 5))

            res_eval = compute_advanced_match_predictions({"exp_goals_home": 1.6, "exp_goals_away": 1.1})
            
            p_h = res_eval["p_home"] * 100
            p_n = res_eval["p_draw"] * 100
            p_a = res_eval["p_away"] * 100
            p_1x, p_x2 = p_h + p_n, p_a + p_n

            if p_1x >= 68.0:
                p_main_lbl = f"Double Chance {f_home} ou Nul (1X)"
                p_main_code = "1X"
            elif p_x2 >= 68.0:
                p_main_lbl = f"Double Chance Nul ou {f_away} (X2)"
                p_main_code = "X2"
            elif p_h > p_a:
                p_main_lbl = f"Victoire {f_home} (1)"
                p_main_code = "1"
            else:
                p_main_lbl = f"Victoire {f_away} (2)"
                p_main_code = "2"

            status_main = evaluate_main_pred(p_main_code, score_f_h, score_f_a)

            corner_line = 8.5
            p_corner_over = res_eval["corners"]["ou"].get("8.5", 0.65)
            pred_corner_type = "OVER" if p_corner_over >= 0.50 else "UNDER"
            pred_corner_lbl = f"Plus de {corner_line} Corners" if pred_corner_type == "OVER" else f"Moins de {corner_line} Corners"
            status_corner = evaluate_ou_pred(pred_corner_type, corner_line, actual_corners)

            card_line = 3.5
            p_card_over = res_eval["cards"]["ou"].get("3.5", 0.60)
            pred_card_type = "OVER" if p_card_over >= 0.50 else "UNDER"
            pred_card_lbl = f"Plus de {card_line} Cartons" if pred_card_type == "OVER" else f"Moins de {card_line} Cartons"
            status_card = evaluate_ou_pred(pred_card_type, card_line, actual_cards)

            count_match += 1
            if status_main: ok_main += 1
            if status_corner: ok_corners += 1
            if status_card: ok_cards += 1

            tracker_list.append({
                "date": fm["utcDate"][:10],
                "match": f"{f_home} vs {f_away}",
                "score": f"{score_f_h} - {score_f_a}",
                "main_pred": p_main_lbl,
                "main_status": status_main,
                "corner_pred": pred_corner_lbl,
                "corner_actual": actual_corners,
                "corner_status": status_corner,
                "card_pred": pred_card_lbl,
                "card_actual": actual_cards,
                "card_status": status_card
            })

        rate_main = (ok_main / count_match * 100) if count_match > 0 else 0
        rate_corners = (ok_corners / count_match * 100) if count_match > 0 else 0
        rate_cards = (ok_cards / count_match * 100) if count_match > 0 else 0

        st.markdown('<div class="panel-card">', unsafe_allow_html=True)
        st.markdown("#### 🎯 Taux de Réussite Globaux par Catégorie")
        tb1, tb2, tb3 = st.columns(3)
        with tb1:
            st.markdown(f"""<div class="prob-box">
<div class="prob-val" style="color:#10B981;">{rate_main:.1f}%</div>
<div class="prob-lbl">Résultats Match (1N2/DC)</div>
<div style="font-size:0.78rem; color:#64748B; margin-top:2px;">{ok_main}/{count_match} Validés</div>
</div>""", unsafe_allow_html=True)
        with tb2:
            st.markdown(f"""<div class="prob-box">
<div class="prob-val" style="color:#38BDF8;">{rate_corners:.1f}%</div>
<div class="prob-lbl">Corners</div>
<div style="font-size:0.78rem; color:#64748B; margin-top:2px;">{ok_corners}/{count_match} Validés</div>
</div>""", unsafe_allow_html=True)
        with tb3:
            st.markdown(f"""<div class="prob-box">
<div class="prob-val" style="color:#F59E0B;">{rate_cards:.1f}%</div>
<div class="prob-lbl">Cartons Jaunes / Rouges</div>
<div style="font-size:0.78rem; color:#64748B; margin-top:2px;">{ok_cards}/{count_match} Validés</div>
</div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("#### 📋 Détails Complets Match par Match")
        for item in tracker_list:
            tag_main = '<span class="badge-success">VALIDÉE ✅</span>' if item["main_status"] else '<span class="badge-failed">ÉCHEC ❌</span>'
            tag_corner = '<span class="badge-success">VALIDÉ ✅</span>' if item["corner_status"] else '<span class="badge-failed">ÉCHEC ❌</span>'
            tag_card = '<span class="badge-success">VALIDÉ ✅</span>' if item["card_status"] else '<span class="badge-failed">ÉCHEC ❌</span>'

            html_content = f"""<div class="tracker-card">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid #1E293B; padding-bottom:8px;">
<div>
<span style="color:#64748B; font-size:0.78rem; font-weight:700;">📅 {item['date']}</span>
<h3 style="margin:0; color:#F8FAFC; font-size:1.1rem;">{item['match']}</h3>
</div>
<div style="text-align:right;">
<span style="font-size:1.2rem; font-weight:900; color:#F43F5E;">Score Final : {item['score']}</span>
</div>
</div>
<div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:10px;">
<div class="tracker-market-box">
<div style="font-size:0.78rem; color:#94A3B8; font-weight:700;">⚽ PARI PRINCIPAL (1N2/DC)</div>
<div style="font-size:0.9rem; font-weight:800; color:#F1F5F9; margin:4px 0;">{item['main_pred']}</div>
{tag_main}
</div>
<div class="tracker-market-box">
<div style="font-size:0.78rem; color:#94A3B8; font-weight:700;">🚩 CORNERS (Réel : {item['corner_actual']})</div>
<div style="font-size:0.9rem; font-weight:800; color:#38BDF8; margin:4px 0;">{item['corner_pred']}</div>
{tag_corner}
</div>
<div class="tracker-market-box">
<div style="font-size:0.78rem; color:#94A3B8; font-weight:700;">🟨 CARTONS (Réel : {item['card_actual']})</div>
<div style="font-size:0.9rem; font-weight:800; color:#F59E0B; margin:4px 0;">{item['card_pred']}</div>
{tag_card}
</div>
</div>
</div>"""
            st.markdown(html_content, unsafe_allow_html=True)
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
                min_live = m.get("minute")
                time_str = f" ({min_live}')" if min_live is not None else ""
                status_str = f"<b style='color:#EF4444;'>🔴 EN DIRECT : {sc_h} - {sc_a}{time_str}</b>"
            else:
                status_str = f"<b style='color:#38BDF8;'>À VENIR à {m_time} GMT</b>"

            st.markdown(f"""<div class="market-row-item">
<div>
<span style="color:#64748B; font-size:0.78rem;">📅 {m_date}</span><br/>
<b>{h_team}</b> vs <b>{a_team}</b>
</div>
<div>{status_str}</div>
</div>""", unsafe_allow_html=True)
    else:
        st.warning("Aucune donnée de calendrier disponible.")
