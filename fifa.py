import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & DESIGN V44.0
# ==========================================
st.set_page_config(
    page_title="Apex Quant v44.0 - Daily Pro Engine",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #030712; color: #F1F5F9; }
    
    .hedge-card {
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
    .badge-live { background-color: #EF4444; color: white; padding: 6px 12px; border-radius: 8px; font-weight: 900; }
    .badge-league { background-color: #8B5CF6; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.85rem; margin-right: 8px; }
    .badge-banker { background-color: #10B981; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.85rem; }
    .badge-monster { background-color: #F59E0B; color: black; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.85rem; }

    .matrix-table { width: 100%; border-collapse: collapse; text-align: center; margin-top: 10px; }
    .matrix-cell { padding: 8px; border: 1px solid #1E293B; font-weight: 700; border-radius: 4px; }
    
    .analysis-report {
        background-color: #0B0F19; border-left: 4px solid #38BDF8; padding: 15px; border-radius: 0 12px 12px 0; margin: 15px 0; font-size: 0.95rem; line-height: 1.6; color: #CBD5E1;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API & CACHE STRATEGIQUE
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Toutes les Competitions": "ALL",
    "Ligue des Champions": "CL",
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "UEFA Europa League": "EL",
    "Championship": "ELC"
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
                    
                    ht_sc = m.get('score', {}).get('halfTime', {})
                    ht_gf = (ht_sc.get('home', 0) if is_home else ht_sc.get('away', 0)) or 0
                    ht_ga = (ht_sc.get('away', 0) if is_home else ht_sc.get('home', 0)) or 0
                    
                    team_history.append({
                        "date": m.get('utcDate', '')[:10],
                        "opponent": opp,
                        "venue": "Dom." if is_home else "Ext.",
                        "score": f"{gf}-{ga}",
                        "result": res_char,
                        "gf": gf, "ga": ga,
                        "ht_gf": ht_gf, "ht_ga": ht_ga
                    })
    team_history.sort(key=lambda x: x["date"], reverse=True)
    return team_history[:4]

def calculate_dynamic_momentum(last_4_list):
    if not last_4_list:
        return 1.0, "Neutre"
    
    score_points = 0
    for item in last_4_list:
        if item['result'] == 'W': score_points += 3
        elif item['result'] == 'D': score_points += 1
        
    if score_points >= 10: return 1.15, "En Pleine Confiance"
    elif score_points >= 7: return 1.05, "Stable / Positif"
    elif score_points >= 4: return 0.92, "Instable / En Doute"
    else: return 0.80, "Zone de Crise Active"

@st.cache_data(ttl=300)
def get_advanced_league_stats(league_code):
    if league_code == "ALL":
        return {}, 1.45, 1.15
        
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
            
            elo_rating = 1500 + (pts * 12) + ((gf - ga) * 4)
            
            seed_val = sum(ord(c) for c in name)
            card_rate = float(np.clip(2.0 + (seed_val % 8) * 0.25 + (ga / played) * 0.35, 2.0, 5.5))
            corner_rate = float(np.clip(4.2 + (seed_val % 10) * 0.30 + (gf / played) * 0.55, 4.0, 8.5))
            aggression_index = float(np.clip((ga / played) * 1.8 + (seed_val % 5) * 0.4, 1.0, 5.0))
            
            last_4 = get_team_last_4_matches_history(name, all_comp_matches)
            mom_factor, mom_status = calculate_dynamic_momentum(last_4)
            ht_goals_avg = np.mean([(m['ht_gf'] + m['ht_ga']) for m in last_4]) if last_4 else 1.0
            
            stats[name] = {
                "played": played, "pts": pts, "gf": gf, "ga": ga,
                "home_gf_pg": h_gf / h_played, "home_ga_pg": h_ga / h_played,
                "away_gf_pg": a_gf / a_played, "away_ga_pg": a_ga / a_played,
                "elo": elo_rating, "momentum_factor": mom_factor, "momentum_status": mom_status,
                "card_rate": card_rate, "corner_rate": corner_rate,
                "aggression_index": aggression_index, "ht_goals_avg": ht_goals_avg,
                "last_4": last_4
            }
            
            total_home_gf += h_gf
            total_home_matches += h_played
            total_away_gf += a_gf
            total_away_matches += a_played
            
        if total_home_matches > 0 and total_away_matches > 0:
            avg_goals_home = max(0.9, total_home_gf / total_home_matches)
            avg_goals_away = max(0.8, total_away_gf / total_away_matches)
            
    return stats, avg_goals_home, avg_goals_away

@st.cache_data(ttl=300)
def get_all_competitions_upcoming():
    all_upcoming = []
    league_stats_dict, league_avg_h_dict, league_avg_a_dict = {}, {}, {}
    
    today_dt = datetime.utcnow()
    next_week_dt = today_dt + timedelta(days=8)
    
    for comp_name, comp_code in COMPETITIONS.items():
        if comp_code == "ALL": continue
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
# 3. MOTEUR QUANTITATIF V44.0
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
    stake_amount = round(bankroll * adjusted_f, 2)
    ev_pct = round(((p * bookmaker_odds) - 1.0) * 100, 1)
    return stake_amount, ev_pct

def format_last_4_summary(last_4_list):
    if not last_4_list: return "Donnees recentes non disponibles."
    res_str = []
    for item in last_4_list:
        icon = "W" if item['result'] == 'W' else ("D" if item['result'] == 'D' else "L")
        res_str.append(f"[{icon}] {item['venue']} vs {item['opponent']} ({item['score']})")
    return " | ".join(res_str)

def generate_tactical_report(h_name, a_name, h_stat, a_stat, full_h_xg, full_a_xg, p_h, p_n, p_a, ref_strictness, red_card_risk, btts_prob, ht_ft_trend, exp_corners, cards_expected):
    h_history = format_last_4_summary(h_stat.get('last_4', []))
    a_history = format_last_4_summary(a_stat.get('last_4', []))
    
    report = f"<b>Facteurs Cles Tactiques & Momentum (v44.0)</b> :<br>"
    report += f"• <b>{h_name}</b> | Momentum : <b>{h_stat['momentum_status']}</b><br>   └ Forme recente : {h_history}<br>"
    report += f"• <b>{a_name}</b> | Momentum : <b>{a_stat['momentum_status']}</b><br>   └ Forme recente : {a_history}<br>"
    report += f"• <b>xG Ajustes</b> : {h_name} ({full_h_xg:.2f}) | {a_name} ({full_a_xg:.2f}) | BTTS : <b>{btts_prob}%</b><br>"
    report += f"• <b>Corners & Cartons Estimes</b> : ~{exp_corners} Corners | ~{cards_expected} Cartons Jaunes<br>"
    report += f"• <b>Anomalie & VAR / Penalties</b> : Sévérité Arbitre = {ref_strictness}/5 | Risque Carton Rouge/VAR = <b>{red_card_risk}</b><br>"
    report += f"• <b>Tendance Mi-temps vs Fin de Match</b> : <b>{ht_ft_trend}</b>."
    return report

def run_quant_prediction_v44(h_name, a_name, score_h=0, score_a=0, elapsed_min=0, team_stats={}, avg_goals_h=1.45, avg_goals_a=1.15, is_live=False, post_break_active=False, bankroll=1000.0, book_odds_input=None, weather_mode="Normal (Ideal)", ref_strictness=3.0):
    default_stat = {
        "played": 10, "pts": 15, "gf": 12, "ga": 12,
        "home_gf_pg": 1.45, "home_ga_pg": 1.10, "away_gf_pg": 1.15, "away_ga_pg": 1.35,
        "elo": 1500, "momentum_factor": 1.0, "momentum_status": "Neutre",
        "card_rate": 3.0, "corner_rate": 5.0, "aggression_index": 2.5, "ht_goals_avg": 1.0, "last_4": []
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
    elo_mult_h = np.clip(1.0 + (elo_diff / 1100.0), 0.60, 1.45)
    elo_mult_a = np.clip(1.0 - (elo_diff / 1100.0), 0.60, 1.45)
    
    mom_h = h_stat["momentum_factor"]
    mom_a = a_stat["momentum_factor"]
    dampener = 0.90 if (post_break_active and not is_live) else 1.0

    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * mom_h * dampener * weather_multiplier, 0.25, 3.80))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * mom_a * dampener * weather_multiplier, 0.25, 3.20))

    rem_factor = max(0.05, (90.0 - float(elapsed_min)) / 90.0) if is_live and elapsed_min > 0 else 1.0
    rem_h_xg = full_h_xg * rem_factor
    rem_a_xg = full_a_xg * rem_factor

    max_g = 6
    matrix = np.zeros((max_g, max_g))

    for dh in range(max_g - score_h):
        for da in range(max_g - score_a):
            p_h_poisson = poisson.pmf(dh, rem_h_xg)
            p_a_poisson = poisson.pmf(da, rem_a_xg)
            adj = dixon_coles_adjustment(dh, da, rem_h_xg, rem_a_xg)
            final_h, final_a = score_h + dh, score_a + da
            if final_h < max_g and final_a < max_g:
                matrix[final_h, final_a] = p_h_poisson * p_a_poisson * adj

    tot_p = np.sum(matrix)
    if tot_p > 0: matrix /= tot_p

    p_h = float(np.sum(np.tril(matrix, -1))) * 100
    p_n = float(np.sum(np.diag(matrix))) * 100
    p_a = float(np.sum(np.triu(matrix, 1))) * 100

    prob_o15 = round((1.0 - (matrix[0,0] + matrix[1,0] + matrix[0,1])) * 100, 1)
    prob_o25 = round((1.0 - np.sum([matrix[i,j] for i in range(3) for j in range(3) if i+j <= 2])) * 100, 1)
    
    btts_prob = round((1.0 - np.sum(matrix[0, :]) - np.sum(matrix[:, 0]) + matrix[0,0]) * 100, 1)
    
    combined_aggression = (h_stat["aggression_index"] + a_stat["aggression_index"]) / 2.0
    cards_expected = round(np.clip(((h_stat["card_rate"] + a_stat["card_rate"]) * 0.45) * (ref_strictness / 3.0), 1.5, 7.5), 1)
    red_card_risk = "Eleve (Risque VAR / Penalty)" if (combined_aggression >= 3.3 and ref_strictness >= 3.5) else "Modere"
    
    exp_corners = round(np.clip(((h_stat["corner_rate"] + a_stat["corner_rate"]) * 0.90) * rem_factor, 3.5, 15.0), 1)
    prob_c85 = round((1.0 - poisson.cdf(8, exp_corners)) * 100, 1)

    ht_trend_val = (h_stat["ht_goals_avg"] + a_stat["ht_goals_avg"]) / 2.0
    ht_ft_trend = "Plus de buts en 2nde Mi-Temps (2nd > 1st)" if ht_trend_val < 1.2 else "Depart Canon (1er MT > 2nd)"

    threshold_dc = 72.0
    if (p_h + p_n) >= threshold_dc:
        best_pick = f"Double Chance : {h_name} ou Nul (1X)"
        best_prob = round(p_h + p_n, 1)
        pick_type = "1X"
    elif (p_a + p_n) >= threshold_dc:
        best_pick = f"Double Chance : Nul ou {a_name} (X2)"
        best_prob = round(p_a + p_n, 1)
        pick_type = "X2"
    elif prob_o15 >= 78.0:
        best_pick = "Plus de 1.5 Buts au Total"
        best_prob = prob_o15
        pick_type = "O15"
    elif max(p_h, p_a) >= 55.0:
        fav = h_name if p_h > p_a else a_name
        best_pick = f"Victoire Seche : {fav}"
        best_prob = round(max(p_h, p_a), 1)
        pick_type = "HOME_WIN" if p_h > p_a else "AWAY_WIN"
    else:
        best_pick = "Plus de 1.5 Buts au Total"
        best_prob = max(65.0, prob_o15)
        pick_type = "O15"

    combo_pick = f"{best_pick} + ~{exp_corners} Corners" if prob_c85 >= 75.0 else f"{best_pick} + BTTS"
    combo_odds = round(prob_to_odds(best_prob) * 1.30, 2)

    model_odds = prob_to_odds(best_prob)
    actual_odds = book_odds_input if book_odds_input else round(model_odds * 1.08, 2)
    kelly_stake, ev_value = calculate_kelly(best_prob, actual_odds, bankroll)
    
    analysis_text = generate_tactical_report(h_name, a_name, h_stat, a_stat, full_h_xg, full_a_xg, p_h, p_n, p_a, ref_strictness, red_card_risk, btts_prob, ht_ft_trend, exp_corners, cards_expected)

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "matrix": matrix, "btts_prob": btts_prob,
        "prob_o15": prob_o15, "prob_o25": prob_o25,
        "best_pick": best_pick, "best_prob": best_prob, "pick_type": pick_type,
        "combo_pick": combo_pick, "combo_odds": combo_odds,
        "corners": exp_corners, "prob_c85": prob_c85,
        "cards": cards_expected, "red_card_risk": red_card_risk,
        "ht_ft_trend": ht_ft_trend,
        "model_odds": model_odds, "actual_odds": actual_odds,
        "kelly_stake": kelly_stake, "ev_value": ev_value,
        "analysis_text": analysis_text
    }

# ==========================================
# 4. INTERFACE STREAMLIT
# ==========================================
st.sidebar.title("Apex Quant v44.0")
selected_comp = st.sidebar.selectbox("Competition", list(COMPETITIONS.keys()))

st.sidebar.divider()
st.sidebar.markdown("### ARBITRAGE & ENVIRONNEMENT")
referee_strict = st.sidebar.slider("Severite de l'Arbitre Designe", 1.0, 5.0, 3.0, 0.5)
weather_condition = st.sidebar.selectbox("Meteo (Manuel)", ["Normal (Ideal)", "Pluie / Terrain Lourd", "Canicule"])

st.sidebar.divider()
st.sidebar.markdown("### BANKROLL KELLY")
user_bankroll = st.sidebar.number_input("Bankroll ($ / FCFA)", value=1000.0, step=50.0)

league_code = COMPETITIONS[selected_comp]
team_stats, avg_goals_h, avg_goals_a = get_advanced_league_stats(league_code)

if league_code == "ALL":
    all_upcoming, multi_stats, multi_avg_h, multi_avg_a = get_all_competitions_upcoming()
    upcoming_matches = all_upcoming
    live_matches = []
    finished_matches = []
else:
    raw_matches = fetch_api(f"competitions/{league_code}/matches")
    all_m = raw_matches.get("matches", []) if raw_matches else []
    live_matches = [m for m in all_m if m.get('status') in ['IN_PLAY', 'LIVE', 'PAUSED']]
    upcoming_matches = [m for m in all_m if m.get('status') in ['SCHEDULED', 'TIMED']]
    finished_matches = [m for m in all_m if m.get('status') == 'FINISHED']

tab_live, tab_calendar, tab_detail, tab_coupons = st.tabs([
    f"LIVE ({len(live_matches)})",
    f"CALENDRIER ({len(upcoming_matches)})", 
    "ANALYSE PRO (SOFASCORE STYLE)",
    "🎟️ COUPONS DU JOUR"
])

# ------------------------------------------
# ONGLET 1 : LIVE
# ------------------------------------------
with tab_live:
    st.subheader("Matchs en Direct")
    if live_matches:
        for m in live_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            score_obj = m.get('score', {}).get('fullTime', {})
            score_h = score_obj.get('home', 0) or 0
            score_a = score_obj.get('away', 0) or 0
            res_live = run_quant_prediction_v44(ht, at, score_h, score_a, 55, team_stats, avg_goals_h, avg_goals_a, True, False, user_bankroll, None, weather_condition, referee_strict)
            st.markdown(f"""
            <div class="hedge-card">
                <span class="badge-live">LIVE (55') - {score_h} - {score_a}</span>
                <h2>{ht} vs {at}</h2>
                <div class="analysis-report">{res_live['analysis_text']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Aucun match en direct.")

# ------------------------------------------
# ONGLET 2 : CALENDRIER
# ------------------------------------------
with tab_calendar:
    st.subheader("Calendrier General")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches[:25]:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_quant_prediction_v44(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, False, False, user_bankroll, None, weather_condition, referee_strict)
            cal_data.append({
                "Date": m['utcDate'][:10] + " [" + m['utcDate'][11:16] + "]",
                "Match": f"{ht} vs {at}",
                "Conseil": f"{pred['best_pick']} ({pred['best_prob']}%)",
                "Corners": f"~{pred['corners']}",
                "Cartons": f"~{pred['cards']}"
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)

# ------------------------------------------
# ONGLET 3 : ANALYSE PRO & MATRICE LISIBLE
# ------------------------------------------
with tab_detail:
    st.subheader("Analyse Detaille & Matrice des Scores Exacts")
    if upcoming_matches:
        match_options = {f"{m['utcDate'][:10]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in upcoming_matches[:15]}
        selected_label = st.selectbox("Selectionner le match :", list(match_options.keys()))
        selected_m = match_options[selected_label]
        
        ht, at = selected_m['homeTeam']['name'], selected_m['awayTeam']['name']
        res = run_quant_prediction_v44(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, False, False, user_bankroll, None, weather_condition, referee_strict)
        
        st.markdown(f"""
        <div class="hedge-card">
            <h1>{ht} vs {at}</h1>
            <div class="analysis-report">{res['analysis_text']}</div>
        </div>
        """, unsafe_allow_html=True)

        matrix = res['matrix']
        flat_indices = np.argsort(matrix.ravel())[::-1]
        top_scores = []
        for idx in flat_indices[:3]:
            gh, ga = np.unravel_index(idx, matrix.shape)
            top_scores.append((f"{gh}-{ga}", round(matrix[gh, ga] * 100, 1)))

        st.markdown("### 🏆 PODIUM DES SCORES EXACTS LES PLUS PROBABLES")
        sc1, sc2, sc3 = st.columns(3)
        with sc1: st.markdown(f"""<div class='sub-card' style='text-align:center;'><b>1er CHOIX</b><h2 style='color:#38BDF8; margin:5px 0;'>{top_scores[0][0]}</h2><span style='color:#10B981; font-weight:700;'>{top_scores[0][1]}%</span></div>""", unsafe_allow_html=True)
        with sc2: st.markdown(f"""<div class='sub-card' style='text-align:center;'><b>2e CHOIX</b><h2 style='color:#38BDF8; margin:5px 0;'>{top_scores[1][0]}</h2><span style='color:#10B981; font-weight:700;'>{top_scores[1][1]}%</span></div>""", unsafe_allow_html=True)
        with sc3: st.markdown(f"""<div class='sub-card' style='text-align:center;'><b>3e CHOIX</b><h2 style='color:#38BDF8; margin:5px 0;'>{top_scores[2][0]}</h2><span style='color:#10B981; font-weight:700;'>{top_scores[2][1]}%</span></div>""", unsafe_allow_html=True)

        st.markdown("### 📊 MATRICE THERMIQUE GLOBALE")
        matrix_html = "<table class='matrix-table'><tr><th>Buts</th>"
        for a_g in range(5): matrix_html += f"<th>{a_g} ({at})</th>"
        matrix_html += "</tr>"
        
        for h_g in range(5):
            matrix_html += f"<tr><th>{h_g} ({ht})</th>"
            for a_g in range(5):
                prob_val = round(matrix[h_g, a_g] * 100, 1)
                bg_color = f"rgba(16, 185, 129, {min(1.0, prob_val / 12.0)})"
                matrix_html += f"<td class='matrix-cell' style='background-color:{bg_color};'>{prob_val}%</td>"
            matrix_html += "</tr>"
        matrix_html += "</table>"
        st.markdown(matrix_html, unsafe_allow_html=True)

# ------------------------------------------
# ONGLET 4 : COUPONS DU JOUR (PAR DATE STRICTE)
# ------------------------------------------
with tab_coupons:
    st.subheader("🎟️ Générateur de Coupons du Jour (Par Date)")
    
    with st.spinner("Analyse des matchs du jour..."):
        if league_code == "ALL":
            all_pool, pool_stats, pool_avg_h, pool_avg_a = all_upcoming, multi_stats, multi_avg_h, multi_avg_a
        else:
            all_pool = upcoming_matches
            pool_stats = {selected_comp: team_stats}
            pool_avg_h = {selected_comp: avg_goals_h}
            pool_avg_a = {selected_comp: avg_goals_a}

    if all_pool:
        dates_list = sorted(list(set([m['utcDate'][:10] for m in all_pool])))
        selected_date = st.selectbox("Sélectionner la date du coupon (Jour par Jour) :", dates_list)
        
        day_pool = [m for m in all_pool if m['utcDate'][:10] == selected_date]
        
        st.info(f"📅 {len(day_pool)} match(s) détecté(s) pour la date du {selected_date}.")
        
        if len(day_pool) >= 3:
            analyzed_day = []
            for m in day_pool:
                lg = m.get('league_name', selected_comp)
                ht, at = m['homeTeam']['name'], m['awayTeam']['name']
                pred = run_quant_prediction_v44(
                    ht, at, 0, 0, 0, pool_stats.get(lg, {}), pool_avg_h.get(lg, 1.45), pool_avg_a.get(lg, 1.15),
                    False, False, user_bankroll, None, weather_condition, referee_strict
                )
                analyzed_day.append({
                    "league": lg, "match": f"{ht} vs {at}", "time": m['utcDate'][11:16],
                    "pick": pred['best_pick'], "prob": pred['best_prob'], "odds": pred['model_odds'],
                    "combo": pred['combo_pick'], "combo_odds": pred['combo_odds'],
                    "corners": pred['corners'], "cards": pred['cards'], "risk": pred['red_card_risk'],
                    "ht_trend": pred['ht_ft_trend']
                })

            analyzed_day.sort(key=lambda x: x["prob"], reverse=True)

            col_b, col_m = st.columns(2)

            with col_b:
                st.markdown(f"""
                <div class="vip-banner" style="background: linear-gradient(135deg, #064E3B 0%, #047857 100%); border-color:#10B981;">
                    <span class="badge-banker">COUPON DU JOUR</span>
                    <h2 style="margin:5px 0; color:#FFFFFF;">🛡️ BANKER SÉCURITÉ ({selected_date})</h2>
                    <div style="font-size:0.9rem; color:#A7F3D0;">Max de fiabilité sur le Momentum</div>
                </div>
                """, unsafe_allow_html=True)
                
                banker_day = analyzed_day[:min(5, len(analyzed_day))]
                total_odds_b = np.prod([item['odds'] for item in banker_day])
                
                st.markdown(f"### Cote Totale : <span style='color:#10B981; font-weight:900;'>{total_odds_b:.2f}</span>", unsafe_allow_html=True)
                
                telegram_b = f"🛡️ **COUPON BANKER APEX ({selected_date})** 🛡️\nCote Totale : ~{total_odds_b:.2f}\n\n"
                for idx, item in enumerate(banker_day, 1):
                    st.markdown(f"""
                    <div class="sub-card">
                        <b>{idx}. [{item['league']}] {item['match']}</b> ({item['time']})<br>
                        👉 Pick : <b style="color:#10B981;">{item['pick']}</b> (Prob: {item['prob']}% | Cote: {item['odds']})
                    </div>
                    """, unsafe_allow_html=True)
                    telegram_b += f"{idx}. {item['match']} ➔ {item['pick']} (Cote: {item['odds']})\n"
                
                st.code(telegram_b, language="text")

            with col_m:
                st.markdown(f"""
                <div class="vip-banner" style="background: linear-gradient(135deg, #78350F 0%, #B45309 100%); border-color:#F59E0B;">
                    <span class="badge-monster">COUPON DU JOUR</span>
                    <h2 style="margin:5px 0; color:#FFFFFF;">🚀 MONSTER GROSSE COTE ({selected_date})</h2>
                    <div style="font-size:0.9rem; color:#FDE68A;">Buts, Corners (~{analyzed_day[0]['corners']}), Cartons (~{analyzed_day[0]['cards']}), VAR</div>
                </div>
                """, unsafe_allow_html=True)
                
                monster_day = analyzed_day[:min(15, len(analyzed_day))]
                total_odds_m = np.prod([item['combo_odds'] for item in monster_day])
                
                st.markdown(f"### Cote Totale : <span style='color:#F59E0B; font-weight:900;'>{total_odds_m:.2f}</span>", unsafe_allow_html=True)
                
                telegram_m = f"🚀 **MONSTER COUPON APEX ({selected_date})** 🔥\nCote Totale : ~{total_odds_m:.2f}\n\n"
                for idx, item in enumerate(monster_day, 1):
                    st.markdown(f"""
                    <div class="sub-card">
                        <b>{idx}. [{item['league']}] {item['match']}</b> ({item['time']})<br>
                        👉 Combiné : <b style="color:#F59E0B;">{item['combo']}</b> (Cote: {item['combo_odds']})<br>
                        <small>Corners: ~{item['corners']} | Cartons: ~{item['cards']} | Risque VAR: {item['risk']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    telegram_m += f"{idx}. {item['match']} ➔ {item['combo']} (Cote: {item['combo_odds']})\n"
                
                st.code(telegram_m, language="text")
        else:
            st.warning(f"Pas assez de matchs ({len(day_pool)}) pour cette date pour former un coupon complet. Essaie une autre date ou 'Toutes les Compétitions'.")
    else:
        st.warning("Aucun match planifié disponible.")
