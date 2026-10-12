import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION & DESIGN V37.0
# ==========================================
st.set_page_config(
    page_title="Apex Quant v37.0 - Master Synthesis Engine",
    page_icon="👑",
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
    
    .big-score-box { background: #1E293B; border: 2px solid #38BDF8; border-radius: 12px; padding: 15px; text-align: center; margin: 8px 0; }
    .big-score-val { font-size: 2.1rem; font-weight: 900; color: #38BDF8; line-height: 1.1; }
    .big-score-prob { font-size: 1rem; font-weight: 700; color: #10B981; margin-top: 4px; }

    .value-pick-card {
        background: linear-gradient(135deg, #064E3B 0%, #047857 100%);
        border: 2px solid #10B981; border-radius: 14px; padding: 16px; color: #FFFFFF; text-align: center; margin-bottom: 20px;
    }
    .value-pick-title { font-size: 0.9rem; font-weight: 800; text-transform: uppercase; color: #A7F3D0; }
    .value-pick-main { font-size: 1.6rem; font-weight: 900; color: #FFFFFF; margin: 4px 0; }

    .analysis-report {
        background-color: #0B0F19; border-left: 4px solid #38BDF8; padding: 15px; border-radius: 0 12px 12px 0; margin: 15px 0; font-size: 0.95rem; line-height: 1.6; color: #CBD5E1;
    }

    .audit-stat-box {
        background-color: #1E293B; border: 2px solid #3B82F6; border-radius: 12px; padding: 15px; text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API & EXTRACTION DES DONNÉES SYNTHÉTIQUES
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Ligue des Champions": "CL",
    "UEFA Europa League": "EL",
    "Championship (Angleterre)": "ELC"
}

@st.cache_data(ttl=30)
def fetch_api(endpoint):
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=8)
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
                        "result": res_char
                    })
    team_history.sort(key=lambda x: x["date"], reverse=True)
    return team_history[:4]

@st.cache_data(ttl=1200)
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
            form = row.get("form", "D,D,D,D,D")
            
            h_row = dict_home.get(name, row)
            h_played = max(1, h_row.get("playedGames", 1))
            h_gf = h_row.get("goalsFor", gf / 2)
            h_ga = h_row.get("goalsAgainst", ga / 2)
            
            a_row = dict_away.get(name, row)
            a_played = max(1, a_row.get("playedGames", 1))
            a_gf = a_row.get("goalsFor", gf / 2)
            a_ga = a_row.get("goalsAgainst", ga / 2)
            
            elo_rating = 1500 + (pts * 12) + ((gf - ga) * 4)
            
            form_pts = 0
            if form:
                clean_form = str(form).replace(",", "").upper()
                for char in clean_form[-5:]:
                    if char == 'W': form_pts += 3
                    elif char == 'D': form_pts += 1
            form_factor = np.clip(0.80 + (form_pts / 25.0), 0.70, 1.30)
            
            seed_val = sum(ord(c) for c in name)
            card_rate = float(np.clip(1.8 + (seed_val % 10) * 0.20 + (ga / played) * 0.30, 1.5, 4.5))
            corner_rate = float(np.clip(4.0 + (seed_val % 12) * 0.25 + (gf / played) * 0.50, 3.5, 8.0))
            midfield_control = float(np.clip(0.80 + (pts / (played * 3.0)) * 0.40, 0.70, 1.35))
            
            last_4 = get_team_last_4_matches_history(name, all_comp_matches)
            
            stats[name] = {
                "played": played, "pts": pts, "gf": gf, "ga": ga,
                "home_gf_pg": h_gf / h_played, "home_ga_pg": h_ga / h_played,
                "away_gf_pg": a_gf / a_played, "away_ga_pg": a_ga / a_played,
                "elo": elo_rating, "form_factor": form_factor,
                "card_rate": card_rate, "corner_rate": corner_rate,
                "midfield": midfield_control, "form_string": form,
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
# 3. MOTEUR MATHÉMATIQUE SYNTHÉTIQUE (V37.0)
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
    if not last_4_list:
        return "Données récentes non disponibles."
    res_str = []
    for item in last_4_list:
        icon = "✅" if item['result'] == 'W' else ("🤝" if item['result'] == 'D' else "❌")
        res_str.append(f"{icon} {item['venue']} vs {item['opponent']} ({item['score']})")
    return " | ".join(res_str)

def generate_master_synthesis_report(h_name, a_name, h_stat, a_stat, full_h_xg, full_a_xg, p_h, p_n, p_a, prob_o15, prob_o25, exp_corners):
    h_history = format_last_4_summary(h_stat.get('last_4', []))
    a_history = format_last_4_summary(a_stat.get('last_4', []))
    
    report = f"👑 **Rapport de Synthèse Master Apex (v37.0)** :<br>"
    report += f"• 🏠 **Dynamique Récente {h_name}** : {h_history}<br>"
    report += f"• ✈️ **Dynamique Récente {a_name}** : {a_history}<br>"
    report += f"• 📊 **Modèle Quant & xG Global** : xG Domicile = <b>{full_h_xg:.2f}</b> | xG Extérieur = <b>{full_a_xg:.2f}</b> (Écart ELO : <code>{h_stat['elo'] - a_stat['elo']:+.0f} pts</code>).<br>"
    report += f"• ⚽ **Indicateurs Buts & Rythme** : Over 1.5 estimé à <b>{prob_o15}%</b> | Over 2.5 à <b>{prob_o25}%</b> | Volume Corners Attendu : ~<b>{exp_corners}</b>.<br>"
    report += f"• ⚖️ **Probabilités Matrice 1X2** : {h_name} ({p_h:.1f}%) | Nul ({p_n:.1f}%) | {a_name} ({p_a:.1f}%)."
    return report

def run_quant_prediction_v37(h_name, a_name, score_h=0, score_a=0, elapsed_min=0, team_stats={}, avg_goals_h=1.45, avg_goals_a=1.15, is_live=False, post_break_active=False, bankroll=1000.0, book_odds_input=None):
    default_stat = {
        "played": 10, "pts": 15, "gf": 12, "ga": 12,
        "home_gf_pg": 1.45, "home_ga_pg": 1.10, "away_gf_pg": 1.15, "away_ga_pg": 1.35,
        "elo": 1500, "form_factor": 1.0, "card_rate": 2.3, "corner_rate": 5.0, "midfield": 1.0, "form_string": "D,D,D,D,D",
        "last_4": []
    }
    
    h_stat = team_stats.get(h_name, default_stat)
    a_stat = team_stats.get(a_name, default_stat)
    
    att_h = h_stat["home_gf_pg"] / max(0.5, avg_goals_h)
    def_a = a_stat["away_ga_pg"] / max(0.5, avg_goals_h)
    att_a = a_stat["away_gf_pg"] / max(0.5, avg_goals_a)
    def_h = h_stat["home_ga_pg"] / max(0.5, avg_goals_a)
    
    raw_h_xg = att_h * def_a * avg_goals_h
    raw_a_xg = att_a * def_h * avg_goals_a
    
    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_mult_h = np.clip(1.0 + (elo_diff / 1100.0), 0.60, 1.45)
    elo_mult_a = np.clip(1.0 - (elo_diff / 1100.0), 0.60, 1.45)
    
    if post_break_active and not is_live:
        effective_form_h = 1.0 + (h_stat["form_factor"] - 1.0) * 0.4
        effective_form_a = 1.0 + (a_stat["form_factor"] - 1.0) * 0.4
        dampener = 0.90
    else:
        effective_form_h = h_stat["form_factor"]
        effective_form_a = a_stat["form_factor"]
        dampener = 1.0

    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * effective_form_h * dampener, 0.25, 3.80))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * effective_form_a * dampener, 0.25, 3.20))

    rem_factor = max(0.05, (90.0 - float(elapsed_min)) / 90.0) if is_live and elapsed_min > 0 else 1.0
    rem_h_xg = full_h_xg * rem_factor
    rem_a_xg = full_a_xg * rem_factor

    abs_elo_diff = abs(h_stat["elo"] - a_stat["elo"])
    tenacity_index = float(np.clip(1.50 - (abs_elo_diff / 200.0), 0.80, 1.70))

    max_g = 8
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

    attack_drive = (full_h_xg + full_a_xg) / 2.3
    exp_corners = round(np.clip(((h_stat["corner_rate"] + a_stat["corner_rate"]) * attack_drive * tenacity_index * 0.88) * rem_factor, 2.5, 16.0), 1)

    threshold_dc = 72.0 if post_break_active else 69.0

    # ==========================================
    # RÈGLE D'OR : CONSEILS PRINCIPAUX SOLIDES ET ROYAUX (PAS DE MARCHÉS SECONDAIRES LOUCHES)
    # ==========================================
    if is_live:
        if prob_o15 >= 65.0:
            best_pick = "⚡ En Direct : +1 But supplémentaire"
            best_prob = prob_o15
            pick_type = "LIVE_GOAL"
        else:
            best_pick = f"🔒 En Direct : Score {score_h}-{score_a} protégé"
            best_prob = round(100.0 - prob_o15, 1)
            pick_type = "LIVE_STABLE"
    else:
        # Priorité aux options majeures de pro : Double Chance VIP ou Victoire / Over 1.5 combiné
        if (p_h + p_n) >= threshold_dc:
            best_pick = f"🛡️ Double Chance VIP : {h_name} ou Nul (1X)"
            best_prob = round(p_h + p_n, 1)
            pick_type = "1X"
        elif (p_a + p_n) >= threshold_dc:
            best_pick = f"🛡️ Double Chance VIP : Nul ou {a_name} (X2)"
            best_prob = round(p_a + p_n, 1)
            pick_type = "X2"
        elif prob_o15 >= 75.0:
            best_pick = "⚽ Plus de 1.5 Buts au Total (Sécurité Match Ouvert)"
            best_prob = prob_o15
            pick_type = "O15"
        elif prob_o25 >= 62.0:
            best_pick = "🔥 Plus de 2.5 Buts (Tendance Offensive Forte)"
            best_prob = prob_o25
            pick_type = "O25"
        else:
            fav = h_name if p_h > p_a else a_name
            best_pick = f"👑 Victoire Sèche / Solide : {fav}"
            best_prob = round(max(p_h, p_a), 1)
            pick_type = "HOME_WIN" if p_h > p_a else "AWAY_WIN"

    model_odds = prob_to_odds(best_prob)
    actual_odds = book_odds_input if book_odds_input else round(model_odds * 1.08, 2)
    kelly_stake, ev_value = calculate_kelly(best_prob, actual_odds, bankroll)
    
    analysis_text = generate_master_synthesis_report(h_name, a_name, h_stat, a_stat, full_h_xg, full_a_xg, p_h, p_n, p_a, prob_o15, prob_o25, exp_corners)

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "top_3_scores": top_3_scores,
        "prob_o15": prob_o15, "prob_o25": prob_o25,
        "best_pick": best_pick, "best_prob": best_prob, "pick_type": pick_type,
        "model_odds": model_odds, "actual_odds": actual_odds,
        "kelly_stake": kelly_stake, "ev_value": ev_value,
        "corners": exp_corners,
        "analysis_text": analysis_text
    }

# ==========================================
# 4. INTERFACE STREAMLIT (5 ONGLETS)
# ==========================================
st.sidebar.title("Apex Quant v37.0 👑")
selected_comp = st.sidebar.selectbox("Compétition Principale", list(COMPETITIONS.keys()))

st.sidebar.divider()
st.sidebar.markdown("### 💰 GESTION DE BANKROLL KELLY")
user_bankroll = st.sidebar.number_input("Bankroll Totale ($ / FCFA)", value=1000.0, step=50.0)
post_break_mode = st.sidebar.checkbox("🔒 Filtre Post-Trêve Internationale", value=True)

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

tab_live, tab_calendar, tab_detail, tab_audit, tab_coupon = st.tabs([
    f"🔴 EN DIRECT ({len(live_matches)})",
    f"📅 CALENDRIER ({len(upcoming_matches)})", 
    "📊 SYNTHÈSE MASTER & ANALYSE 4 MATCHS",
    f"📈 AUDIT & BANQUE VIP ({len(finished_matches)})",
    "🎟️ COMBINÉ VIP (4-5 MATCHS OR)"
])

# ------------------------------------------
# ONGLET 1 : MATCHS EN DIRECT
# ------------------------------------------
with tab_live:
    st.subheader(f"Suivi Live & Synthèse - {selected_comp}")
    if live_matches:
        for m in live_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            score_obj = m.get('score', {}).get('fullTime', {})
            score_h = score_obj.get('home', 0) if score_obj.get('home') is not None else 0
            score_a = score_obj.get('away', 0) if score_obj.get('away') is not None else 0
            
            res_live = run_quant_prediction_v37(ht, at, score_h, score_a, 55, team_stats, avg_goals_h, avg_goals_a, True, post_break_mode, user_bankroll)
            
            st.markdown(f"""
            <div class="hedge-card">
                <span class="badge-live">LIVE MASTER (55') — {score_h} - {score_a}</span>
                <h2 style="color:#38BDF8; margin:10px 0 5px 0;">{ht} vs {at}</h2>
                <div class="analysis-report">{res_live['analysis_text']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.divider()
    else:
        st.info("Aucun match en direct actuellement.")

# ------------------------------------------
# ONGLET 2 : CALENDRIER
# ------------------------------------------
with tab_calendar:
    st.subheader(f"Calendrier & Signaux VIP - {selected_comp}")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_quant_prediction_v37(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, False, post_break_mode, user_bankroll)
            cal_data.append({
                "Date": m['utcDate'][:10] + " [" + m['utcDate'][11:16] + "]",
                "Match": f"{ht} vs {at}",
                "Score Exact #1": f"{pred['top_3_scores'][0]['score']} ({pred['top_3_scores'][0]['prob']}%)",
                "Conseil VIP": f"{pred['best_pick']} ({pred['best_prob']}%)"
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match programmé.")

# ------------------------------------------
# ONGLET 3 : SYNTHÈSE MASTER & ANALYSE 4 MATCHS
# ------------------------------------------
with tab_detail:
    st.subheader("Synthèse Avancée : Historique des 4 Matchs + Modèle Quant & Buts")
    if upcoming_matches or all_matches:
        match_options = {f"{m['utcDate'][:10]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in (upcoming_matches if upcoming_matches else all_matches[:10])}
        selected_label = st.selectbox("Sélectionner la rencontre :", list(match_options.keys()))
        selected_m = match_options[selected_label]
        
        ht, at = selected_m['homeTeam']['name'], selected_m['awayTeam']['name']
        book_odds = st.number_input("Cote proposée par le bookmaker :", value=1.70, step=0.05)
        
        res = run_quant_prediction_v37(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, False, post_break_mode, user_bankroll, book_odds)
        
        st.markdown(f"""
        <div class="hedge-card">
            <h1 style="color:#38BDF8; margin:0;">{ht} vs {at}</h1>
            <div class="analysis-report">{res['analysis_text']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="value-pick-card">
            <div class="value-pick-title">💎 CONSEIL VIP MASTER RECOMMANDÉ</div>
            <div class="value-pick-main">{res['best_pick']}</div>
            <div style="font-size:1.1rem; font-weight:800;">Probabilité : {res['best_prob']}% | EV+ : {res['ev_value']:+.1f}% | Mise Kelly : {res['kelly_stake']} $</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🏆 TOP 3 SCORES EXACTS LES PLUS PROBABLES")
        sc1, sc2, sc3 = st.columns(3)
        with sc1: st.markdown(f"""<div class="big-score-box"><b>1er SCORE</b><div class="big-score-val">{res['top_3_scores'][0]['score']}</div><div class="big-score-prob">{res['top_3_scores'][0]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc2: st.markdown(f"""<div class="big-score-box"><b>2ème SCORE</b><div class="big-score-val">{res['top_3_scores'][1]['score']}</div><div class="big-score-prob">{res['top_3_scores'][1]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc3: st.markdown(f"""<div class="big-score-box"><b>3ème SCORE</b><div class="big-score-val">{res['top_3_scores'][2]['score']}</div><div class="big-score-prob">{res['top_3_scores'][2]['prob']}%</div></div>""", unsafe_allow_html=True)

        st.divider()
        st.markdown("### 📢 FICHE TÉLÉGRAM VIP PRÊTE")
        telegram_card = f"👑 **RAPPORT MASTER APEX (v37.0)** ⚡\n\n⚽ **Match** : {ht} vs {at}\n🎯 **Conseil Clé** : {res['best_pick']} ({res['best_prob']}%)\n📊 **Buts** : +1.5 ({res['prob_o15']}%) | +2.5 ({res['prob_o25']}%)\n🏆 **Top Scores** : 1️⃣ {res['top_3_scores'][0]['score']} | 2️⃣ {res['top_3_scores'][1]['score']} | 3️⃣ {res['top_3_scores'][2]['score']}\n💰 **Mise Kelly** : {res['kelly_stake']} $"
        st.code(telegram_card, language="text")

# ------------------------------------------
# ONGLET 4 : AUDIT & BANQUE VIP
# ------------------------------------------
with tab_audit:
    st.markdown("""
    <div class="vip-banner">
        <h2 style="margin:0; color:#F59E0B;">👑 AUDIT & SUIVI DE BANQUE VIP</h2>
        <p style="color:#E2E8F0; margin-top:5px;">Vérification rigoureuse des signaux passés.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if finished_matches:
        audit_rows = []
        total_eval, success_pick_count, net_units = 0, 0, 0.0
        
        for m in finished_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            rh, ra = m['score']['fullTime']['home'], m['score']['fullTime']['away']
            
            if rh is not None and ra is not None:
                real_score_str = f"{rh}-{ra}"
                pred = run_quant_prediction_v37(ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, False, False, user_bankroll)
                
                ptype = pred['pick_type']
                tot_goals = rh + ra
                pick_hit = (ptype == "1X" and rh >= ra) or (ptype == "X2" and ra >= rh) or (ptype == "O15" and tot_goals > 1) or (ptype == "O25" and tot_goals > 2) or (ptype == "HOME_WIN" and rh > ra) or (ptype == "AWAY_WIN" and ra > rh)
                
                if pick_hit:
                    success_pick_count += 1
                    net_units += 10.0 * (pred['actual_odds'] - 1.0)
                    eval_status = "✅ GAGNÉ"
                else:
                    net_units -= 10.0
                    eval_status = "❌ PERDU"
                
                total_eval += 1
                audit_rows.append({
                    "Date": m['utcDate'][:10], "Rencontre": f"{ht} vs {at}",
                    "Score Réel": real_score_str, "Conseil": pred['best_pick'], "Statut": eval_status
                })
        
        if total_eval > 0:
            winrate_pick = round((success_pick_count / total_eval) * 100, 1)
            roi = round((net_units / (total_eval * 10.0)) * 100, 1)
            
            k1, k2, k3 = st.columns(3)
            with k1: st.markdown(f"""<div class="audit-stat-box"><b>MATCHS</b><br><span style="font-size:1.6rem; color:#38BDF8;">{total_eval}</span></div>""", unsafe_allow_html=True)
            with k2: st.markdown(f"""<div class="audit-stat-box"><b>WINRATE</b><br><span style="font-size:1.6rem; color:#10B981;">{winrate_pick}%</span></div>""", unsafe_allow_html=True)
            with k3: st.markdown(f"""<div class="audit-stat-box"><b>PROFIT NET / ROI</b><br><span style="font-size:1.6rem; color:{'#10B981' if net_units>=0 else '#EF4444'};">{net_units:+.1f} U ({roi:+.1f}%)</span></div>""", unsafe_allow_html=True)
            
            st.write(" ")
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun match terminé à évaluer.")
    else:
        st.info("Aucun match terminé disponible.")

# ------------------------------------------
# ONGLET 5 : COMBINÉ VIP (4-5 MATCHS OR)
# ------------------------------------------
with tab_coupon:
    st.subheader("🎟️ Générateur de Combiné VIP (4 à 5 Matchs d'Élite — Sweet Spot)")
    with st.spinner("Analyse approfondie de tous les championnats..."):
        all_multi, multi_stats, multi_avg_h, multi_avg_a = get_all_competitions_upcoming()
    
    if len(all_multi) >= 4:
        dates_dict = {}
        for m in all_multi: dates_dict.setdefault(m['utcDate'][:10], []).append(m)
        
        sel_date = st.selectbox("Sélectionner la date du combiné :", sorted(list(dates_dict.keys())))
        pool = dates_dict.get(sel_date, []) if len(dates_dict.get(sel_date, [])) >= 4 else all_multi
        
        analyzed = []
        for m in pool:
            lg = m['league_name']
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_quant_prediction_v37(
                ht, at, 0, 0, 0, 
                multi_stats.get(lg, {}), 
                multi_avg_h.get(lg, 1.45), 
                multi_avg_a.get(lg, 1.15), 
                False, post_break_mode, user_bankroll
            )
            analyzed.append({
                "league": lg, "match": f"{ht} vs {at}", "time": m['utcDate'][11:16],
                "pick": pred['best_pick'], "prob": pred['best_prob'], "odds": pred['actual_odds'],
                "top_score": pred['top_3_scores'][0]['score']
            })
        
        analyzed.sort(key=lambda x: x["prob"], reverse=True)
        coupon_4_5 = analyzed[:4]
        
        total_odds = np.prod([c['odds'] for c in coupon_4_5])
        avg_conf = np.mean([c['prob'] for c in coupon_4_5])
        
        st.markdown(f"""
        <div class="vip-banner">
            <h2 style="margin:0; color:#F59E0B;">👑 COMBINÉ VIP OR (SWEET SPOT 4 MATCHS) ({sel_date})</h2>
            <div style="font-size:1.6rem; font-weight:900; color:#FFFFFF; margin-top:8px;">Cote Totale : <span style="color:#38BDF8;">{total_odds:.2f}</span></div>
            <div style="font-size:1.1rem; color:#10B981; font-weight:700;">Fiabilité Moyenne : {avg_conf:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        telegram_coupon = f"👑 **COMBINÉ VIP OR (APEX QUANT v37.0)** ⚡\n🗓 Date : {sel_date}\n📊 Cote Totale : {total_odds:.2f} | Fiabilité : {avg_conf:.1f}%\n\n"
        for idx, leg in enumerate(coupon_4_5, 1):
            st.markdown(f"""
            <div class="sub-card">
                <span class="badge-league">{leg['league']}</span> <b>[{leg['time']} UTC]</b>
                <h3 style="color:#38BDF8; margin:6px 0;">{leg['match']}</h3>
                👉 Conseil : <b>{leg['pick']}</b> (Cote : {leg['odds']}) | Score Exact #1 : <b>{leg['top_score']}</b>
            </div>
            """, unsafe_allow_html=True)
            telegram_coupon += f"{idx}. [{leg['league']}] {leg['match']}\n   👉 {leg['pick']} (Cote: {leg['odds']}) | Score probable: {leg['top_score']}\n"
        
        st.write(" ")
        st.code(telegram_coupon, language="text")
    else:
        st.warning("Pas assez de matchs programmés pour former un combiné optimal.")
