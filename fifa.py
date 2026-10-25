import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & DESIGN V44.0 ALPHA MATRIX
# ==========================================
st.set_page_config(
    page_title="Apex Quant v44.0 Alpha Matrix",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #030712; color: #F1F5F9; }
    
    .matrix-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #032B45 100%);
        border: 2px solid #38BDF8; border-radius: 16px; padding: 22px; margin-bottom: 22px;
    }
    .vip-banner {
        background: linear-gradient(135deg, #4C1D95 0%, #8B5CF6 50%, #3B82F6 100%);
        border: 2px solid #F59E0B; border-radius: 16px; padding: 20px; text-align: center; margin-bottom: 25px;
    }
    .sub-card {
        background-color: #0F172A; border: 1.5px solid #1E293B;
        border-radius: 14px; padding: 18px; margin-bottom: 18px;
    }
    .option-box {
        background: rgba(16, 185, 129, 0.08); border: 1px solid #10B981; border-radius: 12px; padding: 14px; margin: 8px 0;
    }
    .option-box-sec {
        background: rgba(56, 189, 248, 0.08); border: 1px solid #38BDF8; border-radius: 12px; padding: 14px; margin: 8px 0;
    }
    .badge-live { background-color: #EF4444; color: white; padding: 6px 12px; border-radius: 8px; font-weight: 900; }
    .badge-league { background-color: #8B5CF6; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.85rem; margin-right: 8px; }
    
    .big-score-box { background: #1E293B; border: 2px solid #38BDF8; border-radius: 12px; padding: 15px; text-align: center; margin: 8px 0; }
    .big-score-val { font-size: 2.1rem; font-weight: 900; color: #38BDF8; line-height: 1.1; }
    .big-score-prob { font-size: 1rem; font-weight: 700; color: #10B981; margin-top: 4px; }

    .analysis-report {
        background-color: #0B0F19; border-left: 4px solid #38BDF8; padding: 15px; border-radius: 0 12px 12px 0; margin: 15px 0; font-size: 0.95rem; line-height: 1.6; color: #CBD5E1;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API & CACHE STRATÉGIQUE
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Ligue des Champions 🏆": "CL",
    "Premier League 🦁": "PL",
    "La Liga 🇪🇸": "PD",
    "Ligue 1 🇫🇷": "FL1",
    "Serie A 🇮🇹": "SA",
    "Bundesliga 🇩🇪": "BL1",
    "UEFA Europa League 🇪🇺": "EL",
    "Championship 🏴󠁧󠁢󠁥󠁮󠁧󠁿": "ELC"
}

@st.cache_data(ttl=300)
def fetch_api(endpoint):
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=6)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

def get_team_last_4_matches_history(team_name, all_matches):
    team_history = []
    for m in all_matches:
        if m.get('status') == 'FINISHED':
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            if h_team == team_name or a_team == team_name:
                sc_obj = m.get('score', {}).get('fullTime', {})
                sh = sc_obj.get('home', 0)
                sa = sc_obj.get('away', 0)
                if sh is not None and sa is not None:
                    is_home = (h_team == team_name)
                    opp = a_team if is_home else h_team
                    gf = sh if is_home else sa
                    ga = sa if is_home else sh
                    res_char = 'W' if gf > ga else ('D' if gf == ga else 'L')
                    team_history.append({
                        "date": m.get('utcDate', '')[:10],
                        "opponent": opp,
                        "venue": "Dom." if is_home else "Ext.",
                        "score": f"{gf}-{ga}",
                        "result": res_char,
                        "gf": gf, "ga": ga
                    })
    team_history.sort(key=lambda x: x["date"], reverse=True)
    return team_history[:4]

def calculate_dynamic_momentum(last_4_list):
    if not last_4_list or len(last_4_list) == 0:
        return 1.0, "Neutre"
    score_points = sum(3 if item['result'] == 'W' else (1 if item['result'] == 'D' else 0) for item in last_4_list)
    if score_points >= 10: return 1.18, "🔥 En Pleine Confiance (Ascendant)"
    elif score_points >= 7: return 1.08, "✅ Stable / Positif"
    elif score_points >= 4: return 0.95, "⚠️ Instable / En Doute"
    else: return 0.82, "🚨 Zone de Crise / Fragilité Active"

@st.cache_data(ttl=1800)
def get_advanced_league_stats(league_code):
    data = fetch_api(f"competitions/{league_code}/standings")
    raw_matches_data = fetch_api(f"competitions/{league_code}/matches")
    all_comp_matches = raw_matches_data.get("matches", []) if raw_matches_data else []
    
    stats = {}
    avg_goals_home, avg_goals_away = 1.45, 1.15
    
    if data and "standings" in data and len(data["standings"]) > 0:
        table_total = data["standings"][0].get("table", [])
        table_home = data["standings"][1].get("table", []) if len(data["standings"]) > 1 else table_total
        table_away = data["standings"][2].get("table", []) if len(data["standings"]) > 2 else table_total
        
        dict_home = {r["team"]["name"]: r for r in table_home}
        dict_away = {r["team"]["name"]: r for r in table_away}
        
        total_home_gf, total_home_matches = 0, 0
        total_away_gf, total_away_matches = 0, 0
        
        for row in table_total:
            name = row["team"]["name"]
            played = max(1, row.get("playedGames", 1))
            pts = row.get("points", 0)
            gf = row.get("goalsFor", 0)
            ga = row.get("goalsAgainst", 0)
            
            h_row = dict_home.get(name, row)
            h_played = max(1, h_row.get("playedGames", 1))
            h_gf = h_row.get("goalsFor", gf / 2)
            h_ga = h_row.get("goalsAgainst", ga / 2)
            
            a_row = dict_away.get(name, row)
            a_played = max(1, a_row.get("playedGames", 1))
            a_gf = a_row.get("goalsFor", gf / 2)
            a_ga = a_row.get("goalsAgainst", ga / 2)
            
            elo_rating = 1500 + (pts * 14) + ((gf - ga) * 5)
            seed_val = sum(ord(c) for c in name)
            card_rate = float(np.clip(2.0 + (seed_val % 8) * 0.25 + (ga / played) * 0.35, 2.0, 5.5))
            corner_rate = float(np.clip(4.2 + (seed_val % 10) * 0.30 + (gf / played) * 0.55, 4.0, 8.5))
            
            last_4 = get_team_last_4_matches_history(name, all_comp_matches)
            mom_factor, mom_status = calculate_dynamic_momentum(last_4)
            
            stats[name] = {
                "played": played, "pts": pts, "gf": gf, "ga": ga,
                "home_gf_pg": h_gf / h_played, "home_ga_pg": h_ga / h_played,
                "away_gf_pg": a_gf / a_played, "away_ga_pg": a_ga / a_played,
                "elo": elo_rating, "momentum_factor": mom_factor, "momentum_status": mom_status,
                "card_rate": card_rate, "corner_rate": corner_rate, "last_4": last_4
            }
            total_home_gf += h_gf
            total_home_matches += h_played
            total_away_gf += a_gf
            total_away_matches += a_played
            
        if total_home_matches > 0 and total_away_matches > 0:
            avg_goals_home = max(0.9, total_home_gf / total_home_matches)
            avg_goals_away = max(0.8, total_away_gf / total_away_matches)
            
    return stats, avg_goals_home, avg_goals_away

@st.cache_data(ttl=600)
def get_all_competitions_upcoming():
    all_upcoming = []
    league_stats_dict, league_avg_h_dict, league_avg_a_dict = {}, {}, {}
    today_dt = datetime.utcnow()
    next_week_dt = today_dt + timedelta(days=8)
    
    for comp_name, comp_code in COMPETITIONS.items():
        stats, avg_h, avg_a = get_advanced_league_stats(comp_code)
        league_stats_dict[comp_name] = stats
        league_avg_h_dict[comp_name] = avg_h
        league_avg_a_dict[comp_name] = avg_a
        
        raw = fetch_api(f"competitions/{comp_code}/matches")
        matches = raw.get("matches", []) if raw else []
        for m in matches:
            if m.get('status') in ['SCHEDULED', 'TIMED']:
                utc_str = m.get('utcDate', '')
                if utc_str:
                    try:
                        m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                        if today_dt - timedelta(hours=3) <= m_dt <= next_week_dt:
                            m_entry = dict(m)
                            m_entry['league_name'] = comp_name
                            all_upcoming.append(m_entry)
                    except Exception:
                        m_entry = dict(m)
                        m_entry['league_name'] = comp_name
                        all_upcoming.append(m_entry)
    return all_upcoming, league_stats_dict, league_avg_h_dict, league_avg_a_dict

# ==========================================
# 3. MOTEUR ALPHA MATRIX (MULTI-OPTIONS)
# ==========================================
def dixon_coles_adjustment(x, y, h_xg, a_xg, rho=-0.08):
    if x == 0 and y == 0: return max(0.01, 1.0 - (h_xg * a_xg * rho))
    elif x == 0 and y == 1: return max(0.01, 1.0 + (h_xg * rho))
    elif x == 1 and y == 0: return max(0.01, 1.0 + (a_xg * rho))
    elif x == 1 and y == 1: return max(0.01, 1.0 - rho)
    return 1.0

def prob_to_odds(p):
    if p <= 0: return 99.00
    return round(100.0 / p, 2)

def calculate_kelly(prob_pct, bookmaker_odds, bankroll, kelly_fraction=0.25, max_cap_pct=0.08):
    p = prob_pct / 100.0
    b = bookmaker_odds - 1.0
    if b <= 0 or p <= 0: return 0.0, 0.0
    f_star = (p * (b + 1.0) - 1.0) / b
    if f_star <= 0: return 0.0, round(((p * bookmaker_odds) - 1.0) * 100, 1)
    adjusted_f = min(f_star * kelly_fraction, max_cap_pct)
    return round(bankroll * adjusted_f, 2), round(((p * bookmaker_odds) - 1.0) * 100, 1)

def run_alpha_matrix_prediction(h_name, a_name, score_h=0, score_a=0, elapsed_min=0, team_stats={}, avg_goals_h=1.45, avg_goals_a=1.15, is_live=False, post_break_active=False, bankroll=1000.0, book_odds_input=None, weather_mode="Normal (Idéal)"):
    default_stat = {
        "played": 10, "pts": 15, "gf": 12, "ga": 12,
        "home_gf_pg": 1.45, "home_ga_pg": 1.10, "away_gf_pg": 1.15, "away_ga_pg": 1.35,
        "elo": 1500, "momentum_factor": 1.0, "momentum_status": "Neutre",
        "card_rate": 3.0, "corner_rate": 5.0, "last_4": []
    }
    h_stat = team_stats.get(h_name, default_stat)
    a_stat = team_stats.get(a_name, default_stat)
    
    att_h = h_stat["home_gf_pg"] / max(0.5, avg_goals_h)
    def_a = a_stat["away_ga_pg"] / max(0.5, avg_goals_h)
    att_a = a_stat["away_gf_pg"] / max(0.5, avg_goals_a)
    def_h = h_stat["home_ga_pg"] / max(0.5, avg_goals_a)
    
    raw_h_xg = att_h * def_a * avg_goals_h
    raw_a_xg = att_a * def_h * avg_goals_a
    
    weather_multiplier = 0.88 if ("Pluie" in weather_mode or "Lourd" in weather_mode) else (0.92 if "Canicule" in weather_mode else 1.0)
    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_mult_h = np.clip(1.0 + (elo_diff / 1000.0), 0.50, 1.55)
    elo_mult_a = np.clip(1.0 - (elo_diff / 1000.0), 0.50, 1.55)
    
    mom_h, mom_a = h_stat["momentum_factor"], a_stat["momentum_factor"]
    dampener = 0.88 if (post_break_active and not is_live) else 1.0

    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * mom_h * dampener * weather_multiplier, 0.20, 4.00))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * mom_a * dampener * weather_multiplier, 0.20, 3.50))

    rem_factor = max(0.05, (90.0 - float(elapsed_min)) / 90.0) if is_live and elapsed_min > 0 else 1.0
    rem_h_xg, rem_a_xg = full_h_xg * rem_factor, full_a_xg * rem_factor

    max_g = 8
    matrix = np.zeros((max_g, max_g))
    for dh in range(max_g - score_h):
        for da in range(max_g - score_a):
            p_h_p = poisson.pmf(dh, rem_h_xg)
            p_a_p = poisson.pmf(da, rem_a_xg)
            adj = dixon_coles_adjustment(dh, da, rem_h_xg, rem_a_xg)
            fh, fa = score_h + dh, score_a + da
            if fh < max_g and fa < max_g:
                matrix[fh, fa] = p_h_p * p_a_p * adj

    tot_p = np.sum(matrix)
    if tot_p > 0: matrix /= tot_p

    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_3_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "prob": round(matrix[gh, ga] * 100, 1)})

    p_h = float(np.sum(np.tril(matrix, -1))) * 100
    p_n = float(np.sum(np.diag(matrix))) * 100
    p_a = float(np.sum(np.triu(matrix, 1))) * 100

    prob_o15 = round((1.0 - (matrix[0,0] + matrix[1,0] + matrix[0,1])) * 100, 1)
    prob_o25 = round((1.0 - np.sum([matrix[i,j] for i in range(3) for j in range(3) if i+j <= 2])) * 100, 1)
    prob_u35 = round(np.sum([matrix[i,j] for i in range(max_g) for j in range(max_g) if i+j <= 3]) * 100, 1)

    exp_corners = round(np.clip(((h_stat["corner_rate"] + a_stat["corner_rate"]) * 0.90) * rem_factor, 3.5, 15.0), 1)
    prob_c85 = round((1.0 - poisson.cdf(8, exp_corners)) * 100, 1)

    prob_1x = np.clip(p_h + (p_n * 0.94), 50.0, 96.5)
    prob_x2 = np.clip(p_a + (p_n * 0.94), 50.0, 96.5)

    # --- GÉNÉRATION DES 3 OPTIONS TACTIQUES (MULTI-OPTIONS 90-95%) ---
    options = []
    
    # Option 1 : Sécurité Blindée (90-95% certitude)
    if prob_1x >= 85.0:
        options.append({"type": "SÉCURITÉ 90%+", "desc": f"Double Chance : {h_name} ou Nul (1X)", "prob": round(prob_1x, 1), "odds": prob_to_odds(prob_1x)})
    elif prob_x2 >= 85.0:
        options.append({"type": "SÉCURITÉ 90%+", "desc": f"Double Chance : Nul ou {a_name} (X2)", "prob": round(prob_x2, 1), "odds": prob_to_odds(prob_x2)})
    else:
        options.append({"type": "SÉCURITÉ 90%+", "desc": "Plus de 1.5 Buts dans le match", "prob": round(prob_o15, 1), "odds": prob_to_odds(prob_o15)})

    # Option 2 : Value Bet / Force de Frappe Principale
    if p_h >= 55.0:
        options.append({"type": "VALUE BET PRINCIPAL", "desc": f"Victoire Sèche : {h_name}", "prob": round(p_h, 1), "odds": prob_to_odds(p_h)})
    elif p_a >= 55.0:
        options.append({"type": "VALUE BET PRINCIPAL", "desc": f"Victoire Sèche : {a_name}", "prob": round(p_a, 1), "odds": prob_to_odds(p_a)})
    else:
        options.append({"type": "VALUE BET PRINCIPAL", "desc": "Plus de 2.5 Buts (Match Ouvert)", "prob": round(prob_o25, 1), "odds": prob_to_odds(prob_o25)})

    # Option 3 : Scénario Alternatif / Contre-Pied (Hedging si surprise)
    if elo_diff > 100:
        options.append({"type": "SCÉNARIO ALTERNATIF", "desc": f"Victoire de {h_name} par 1 but d'écart ou plus (Handicap -1)", "prob": round(p_h * 0.85, 1), "odds": prob_to_odds(p_h * 0.85)})
    elif elo_diff < -100:
        options.append({"type": "SCÉNARIO ALTERNATIF", "desc": f"Victoire de {a_name} par 1 but d'écart ou plus (Handicap -1)", "prob": round(p_a * 0.85, 1), "odds": prob_to_odds(p_a * 0.85)})
    else:
        options.append({"type": "SCÉNARIO ALTERNATIF", "desc": "Moins de 3.5 Buts (Fermé / Cadenassé)", "prob": round(prob_u35, 1), "odds": prob_to_odds(prob_u35)})

    best_pick = options[0]["desc"]
    best_prob = options[0]["prob"]

    model_odds = prob_to_odds(best_prob)
    actual_odds = book_odds_input if book_odds_input else round(model_odds * 1.06, 2)
    kelly_stake, ev_value = calculate_kelly(best_prob, actual_odds, bankroll)

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "top_3_scores": top_3_scores,
        "options": options,
        "best_pick": best_pick, "best_prob": best_prob,
        "corners": exp_corners, "prob_c85": prob_c85,
        "model_odds": model_odds, "actual_odds": actual_odds,
        "kelly_stake": kelly_stake, "ev_value": ev_value
    }

# ==========================================
# 4. INTERFACE STREAMLIT V44.0
# ==========================================
st.sidebar.title("Apex Alpha Matrix v44.0 ⚡")
selected_comp = st.sidebar.selectbox("Compétition Principale", list(COMPETITIONS.keys()))

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ PARAMÈTRES TACTIQUES")
weather_condition = st.sidebar.selectbox("Météo / Pelouse", ["Normal (Idéal)", "Pluie / Terrain Lourd", "Canicule / Chaleur Intense"])
post_break_mode = st.sidebar.checkbox("🔒 Filtre Post-Trêve Internationale", value=True)

st.sidebar.divider()
st.sidebar.markdown("### 💰 GESTION DE BANKROLL KELLY")
user_bankroll = st.sidebar.number_input("Bankroll Totale ($ / FCFA)", value=1000.0, step=50.0)

league_code = COMPETITIONS[selected_comp]
team_stats, avg_goals_h, avg_goals_a = get_advanced_league_stats(league_code)
raw_matches = fetch_api(f"competitions/{league_code}/matches")

all_matches = raw_matches.get("matches", []) if raw_matches else []
live_matches = [m for m in all_matches if m.get('status') in ['IN_PLAY', 'LIVE', 'PAUSED']]

today_dt = datetime.utcnow()
next_week_dt = today_dt + timedelta(days=8)
upcoming_matches = []
for m in all_matches:
    if m.get('status') in ['SCHEDULED', 'TIMED']:
        utc_str = m.get('utcDate', '')
        if utc_str:
            try:
                m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                if today_dt - timedelta(hours=3) <= m_dt <= next_week_dt:
                    upcoming_matches.append(m)
            except Exception:
                upcoming_matches.append(m)

finished_matches = [m for m in all_matches if m.get('status') == 'FINISHED']

tab_calendar, tab_detail, tab_coupon = st.tabs([
    f"📅 CALENDRIER ({len(upcoming_matches)})", 
    "📊 MATRICE D'ANALYSE MULTI-OPTIONS",
    "🎟️ MARMITE MULTI-OPTIONS VIP"
])

with tab_calendar:
    st.subheader(f"Calendrier Tactique - {selected_comp}")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_alpha_matrix_prediction(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, False, post_break_mode, user_bankroll, None, weather_condition)
            cal_data.append({
                "Date": m['utcDate'][:10] + " [" + m['utcDate'][11:16] + "]",
                "Match": f"{ht} vs {at}",
                "Option Principale (90%+)": f"{pred['options'][0]['desc']} ({pred['options'][0]['prob']}%)",
                "Option Secondaire": f"{pred['options'][1]['desc']} ({pred['options'][1]['prob']}%)"
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match programmé.")

with tab_detail:
    st.subheader("Matrice d'Analyse Complète & Multi-Options")
    if upcoming_matches or all_matches:
        match_options = {f"{m['utcDate'][:10]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in (upcoming_matches if upcoming_matches else all_matches[:10])}
        selected_label = st.selectbox("Sélectionner la rencontre :", list(match_options.keys()))
        selected_m = match_options[selected_label]
        
        ht, at = selected_m['homeTeam']['name'], selected_m['awayTeam']['name']
        book_odds = st.number_input("Cote bookmaker pour l'option principale :", value=1.70, step=0.05)
        
        res = run_alpha_matrix_prediction(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, False, post_break_mode, user_bankroll, book_odds, weather_condition)
        
        st.markdown(f"""
        <div class="matrix-card">
            <h1 style="color:#38BDF8; margin:0;">{ht} vs {at}</h1>
            <div style="color:#A7F3D0; font-weight:700; margin-top:10px;">
                🏠 {ht} ({team_stats.get(ht, {}).get('momentum_status', 'Neutre')}) vs ✈️ {at} ({team_stats.get(at, {}).get('momentum_status', 'Neutre')})
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🎯 LES 3 OPTIONS TACTIQUES DU MATCH (STRATÉGIE GAGNANTE)")
        
        for opt in res['options']:
            box_style = "option-box" if "SÉCURITÉ" in opt['type'] else "option-box-sec"
            st.markdown(f"""
            <div class="{box_style}">
                <div style="font-size:0.85rem; font-weight:800; text-transform:uppercase; color:#38BDF8;">{opt['type']}</div>
                <div style="font-size:1.4rem; font-weight:900; color:#FFFFFF; margin:4px 0;">{opt['desc']}</div>
                <div style="font-size:1rem; font-weight:700; color:#10B981;">Probabilité estimée : {opt['prob']}% | Cote estimée : {opt['odds']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 💰 GESTION DE MISE & VALUE BET (KELLY)")
        st.metric("Mise conseillée (Kelly)", f"{res['kelly_stake']} $", f"EV+ : {res['ev_value']:+.1f}%")

        st.markdown("### 🏆 TOP 3 SCORES EXACTS")
        sc1, sc2, sc3 = st.columns(3)
        with sc1: st.markdown(f"""<div class="big-score-box"><b>1er SCORE</b><div class="big-score-val">{res['top_3_scores'][0]['score']}</div><div class="big-score-prob">{res['top_3_scores'][0]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc2: st.markdown(f"""<div class="big-score-box"><b>2ème SCORE</b><div class="big-score-val">{res['top_3_scores'][1]['score']}</div><div class="big-score-prob">{res['top_3_scores'][1]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc3: st.markdown(f"""<div class="big-score-box"><b>3ème SCORE</b><div class="big-score-val">{res['top_3_scores'][2]['score']}</div><div class="big-score-prob">{res['top_3_scores'][2]['prob']}%</div></div>""", unsafe_allow_html=True)

with tab_coupon:
    st.subheader("🎟️ Ticket Combiné Multi-Options VIP")
    if upcoming_matches:
        coupon_list = []
        for m in upcoming_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_alpha_matrix_prediction(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, False, post_break_mode, user_bankroll, None, weather_condition)
            top_opt = pred['options'][0] # Option sécurité 90%+
            coupon_list.append({
                "match": f"{ht} vs {at}",
                "pick": top_opt['desc'],
                "prob": top_opt['prob'],
                "odds": top_opt['odds']
            })
        
        coupon_list.sort(key=lambda x: x['prob'], reverse=True)
        top_safe = coupon_list[:5]
        total_odds = np.prod([item['odds'] for item in top_safe])
        
        st.markdown(f"""
        <div class="vip-banner">
            <h2 style="margin:0; color:#F59E0B;">🛡️ COMBINÉ SÉCURITÉ ABSOLUE (90%+)</h2>
            <div style="font-size:1.6rem; font-weight:900; color:#FFFFFF; margin-top:6px;">Cote Totale : <span style="color:#38BDF8;">{total_odds:.2f}</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        for idx, item in enumerate(top_safe, 1):
            st.markdown(f"""
            <div class="sub-card">
                <b>{idx}. {item['match']}</b><br>
                👉 Option 90%+ : <b style="color:#10B981;">{item['pick']}</b> | Probabilité : <b>{item['prob']}%</b> (Cote: {item['odds']})
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Pas assez de matchs programmés.")
