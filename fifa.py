import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson
import pandas as pd
from datetime import datetime, timedelta

# ==========================================
# 1. CONFIGURATION ET DESIGN V27.0 (VIP MASTER)
# ==========================================
st.set_page_config(
    page_title="Apex Quant v27.0 - VIP Master",
    page_icon="👑",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #060913; color: #F1F5F9; }
    
    .oracle-card {
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
    .badge-upcoming { background-color: #3B82F6; color: white; padding: 6px 12px; border-radius: 8px; font-weight: 900; }
    .badge-reprise { background-color: #F59E0B; color: #0F172A; padding: 5px 10px; border-radius: 6px; font-weight: 900; font-size: 0.85rem; }
    .badge-league { background-color: #8B5CF6; color: white; padding: 4px 10px; border-radius: 6px; font-weight: 800; font-size: 0.85rem; margin-right: 8px; }
    
    .big-score-box { background: #1E293B; border: 2px solid #38BDF8; border-radius: 12px; padding: 15px; text-align: center; margin: 8px 0; }
    .big-score-val { font-size: 2.3rem; font-weight: 900; color: #38BDF8; line-height: 1.1; }
    .big-score-prob { font-size: 1.1rem; font-weight: 700; color: #10B981; margin-top: 4px; }

    .value-pick-card {
        background: linear-gradient(135deg, #064E3B 0%, #047857 100%);
        border: 2px solid #10B981; border-radius: 14px; padding: 16px; color: #FFFFFF; text-align: center; margin-bottom: 20px;
    }
    .value-pick-title { font-size: 0.9rem; font-weight: 800; text-transform: uppercase; color: #A7F3D0; }
    .value-pick-main { font-size: 1.6rem; font-weight: 900; color: #FFFFFF; margin: 4px 0; }

    .audit-stat-box {
        background-color: #1E293B; border: 2px solid #3B82F6; border-radius: 12px; padding: 15px; text-align: center;
    }
    .vip-audit-box {
        background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 100%);
        border: 2px solid #F59E0B; border-radius: 14px; padding: 18px; margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DONNÉES & API FOOTBALL
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

@st.cache_data(ttl=1200)
def get_advanced_league_stats(league_code):
    data = fetch_api(f"competitions/{league_code}/standings")
    stats = {}
    avg_goals = 1.35
    
    if data and "standings" in data and len(data["standings"]) > 0:
        table_total = data["standings"][0].get("table", [])
        table_home = data["standings"][1].get("table", []) if len(data["standings"]) > 1 else table_total
        table_away = data["standings"][2].get("table", []) if len(data["standings"]) > 2 else table_total
        
        dict_home = {r["team"]["name"]: r for r in table_home}
        dict_away = {r["team"]["name"]: r for r in table_away}
        
        total_played, total_gf = 0, 0
        
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
            form_factor = np.clip(0.85 + (form_pts / 30.0), 0.75, 1.25)
            
            seed_val = sum(ord(c) for c in name)
            card_rate = float(np.clip(1.8 + (seed_val % 12) * 0.18 + (ga / played) * 0.25, 1.5, 4.2))
            corner_rate = float(np.clip(4.2 + (seed_val % 15) * 0.20 + (gf / played) * 0.45, 3.8, 7.5))
            midfield_control = float(np.clip(0.85 + (pts / (played * 3.0)) * 0.35, 0.75, 1.30))
            
            stats[name] = {
                "gf_pg": gf / played, "ga_pg": ga / played,
                "home_gf_pg": h_gf / h_played, "home_ga_pg": h_ga / h_played,
                "away_gf_pg": a_gf / a_played, "away_ga_pg": a_ga / a_played,
                "elo": elo_rating, "form_factor": form_factor,
                "card_rate": card_rate, "corner_rate": corner_rate,
                "midfield": midfield_control
            }
            total_played += played
            total_gf += gf
            
        if total_played > 0:
            avg_goals = max(0.9, total_gf / total_played)
            
    return stats, avg_goals

@st.cache_data(ttl=300)
def get_all_competitions_upcoming():
    all_upcoming = []
    league_stats_dict = {}
    league_avg_dict = {}
    
    today_dt = datetime.utcnow()
    next_week_dt = today_dt + timedelta(days=8)
    
    for comp_name, comp_code in COMPETITIONS.items():
        stats, avg_g = get_advanced_league_stats(comp_code)
        league_stats_dict[comp_name] = stats
        league_avg_dict[comp_name] = avg_g
        
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
                        
    return all_upcoming, league_stats_dict, league_avg_dict

# ==========================================
# 3. MOTEUR MATHÉMATIQUE V27.0
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

def run_quant_prediction_v27(h_name, a_name, score_h=0, score_a=0, elapsed_min=0, team_stats={}, avg_goals=1.35, is_live=False, post_break_active=False):
    default_stat = {
        "gf_pg": 1.35, "ga_pg": 1.25, "home_gf_pg": 1.45, "home_ga_pg": 1.10, 
        "away_gf_pg": 1.15, "away_ga_pg": 1.35, "elo": 1500, "form_factor": 1.0,
        "card_rate": 2.3, "corner_rate": 5.0, "midfield": 1.0
    }
    
    h_stat = team_stats.get(h_name, default_stat)
    a_stat = team_stats.get(a_name, default_stat)
    
    raw_h_xg = avg_goals * (h_stat["home_gf_pg"] / avg_goals) * (a_stat["away_ga_pg"] / avg_goals) * 1.12
    raw_a_xg = avg_goals * (a_stat["away_gf_pg"] / avg_goals) * (h_stat["home_ga_pg"] / avg_goals) * 0.90
    
    elo_diff = h_stat["elo"] - a_stat["elo"]
    elo_mult_h = np.clip(1.0 + (elo_diff / 1200.0), 0.70, 1.35)
    elo_mult_a = np.clip(1.0 - (elo_diff / 1200.0), 0.70, 1.35)
    
    if post_break_active and not is_live:
        effective_form_h = 1.0 + (h_stat["form_factor"] - 1.0) * 0.5
        effective_form_a = 1.0 + (a_stat["form_factor"] - 1.0) * 0.5
        post_break_dampener = 0.92
    else:
        effective_form_h = h_stat["form_factor"]
        effective_form_a = a_stat["form_factor"]
        post_break_dampener = 1.0

    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * effective_form_h * post_break_dampener, 0.4, 3.2))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * effective_form_a * post_break_dampener, 0.4, 2.8))

    if is_live:
        rem_factor = max(0.05, (90.0 - float(elapsed_min)) / 90.0) if elapsed_min > 0 else 0.50
        rem_h_xg = full_h_xg * rem_factor
        rem_a_xg = full_a_xg * rem_factor
    else:
        rem_factor = 1.0
        rem_h_xg = full_h_xg
        rem_a_xg = full_a_xg

    max_g = 8
    matrix = np.zeros((max_g, max_g))

    for dh in range(max_g - score_h):
        for da in range(max_g - score_a):
            p_h = poisson.pmf(dh, rem_h_xg)
            p_a = poisson.pmf(da, rem_a_xg)
            adj = dixon_coles_adjustment(dh, da, rem_h_xg, rem_a_xg)
            
            final_h = score_h + dh
            final_a = score_a + da
            if final_h < max_g and final_a < max_g:
                matrix[final_h, final_a] = p_h * p_a * adj

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

    attack_drive = (full_h_xg + full_a_xg) / 2.5
    exp_c_tot = round(np.clip(((h_stat["corner_rate"] + a_stat["corner_rate"]) * attack_drive * 0.95) * rem_factor, 1.5, 14.0), 1)
    
    prob_c_4_5 = round((1.0 - poisson.cdf(4, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0
    prob_c_6_5 = round((1.0 - poisson.cdf(6, exp_c_tot)) * 100, 1) if exp_c_tot > 0 else 0

    referee_strictness = round(0.88 + ((sum(ord(c) for c in h_name + a_name) % 35) * 0.01), 2)
    midfield_clash = (h_stat["midfield"] + a_stat["midfield"]) / 2.0
    intensity_mult = 1.15 if abs(h_stat["elo"] - a_stat["elo"]) < 80 else 1.0
    
    base_cards = (h_stat["card_rate"] + a_stat["card_rate"]) / 2.0
    exp_k_tot = round(np.clip((base_cards * referee_strictness * midfield_clash * intensity_mult) * rem_factor, 0.8, 8.5), 1)
    
    prob_k_1_5 = round((1.0 - poisson.cdf(1, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0
    prob_k_2_5 = round((1.0 - poisson.cdf(2, exp_k_tot)) * 100, 1) if exp_k_tot > 0 else 0

    rem_xg_tot = rem_h_xg + rem_a_xg
    prob_more_goals = round((1.0 - poisson.pmf(0, rem_xg_tot)) * 100, 1)
    prob_more_corners_2plus = round((1.0 - poisson.cdf(1, exp_c_tot)) * 100, 1)
    prob_more_cards_1plus = round((1.0 - poisson.cdf(0, exp_k_tot)) * 100, 1)

    best_pick = ""
    best_prob = 0.0
    pick_type = ""
    selected_odds = 1.20
    
    threshold_dc = 74.0 if post_break_active else 72.0
    threshold_o15 = 77.0 if post_break_active else 75.0

    if is_live:
        if prob_more_goals >= 65.0:
            best_pick = "⚡ En Direct : Au moins 1 BUT supplémentaire"
            best_prob = prob_more_goals
            pick_type = "LIVE_GOAL"
            selected_odds = prob_to_odds(prob_more_goals)
        else:
            best_pick = f"🔒 En Direct : Score {score_h}-{score_a} conservé"
            best_prob = round(100.0 - prob_more_goals, 1)
            pick_type = "LIVE_STABLE"
            selected_odds = prob_to_odds(best_prob)
    else:
        if (p_h + p_n) >= threshold_dc:
            best_pick = f"🛡️ Double Chance VIP : {h_name} ou Nul (1X)"
            best_prob = round(p_h + p_n, 1)
            pick_type = "1X"
            selected_odds = prob_to_odds(best_prob)
        elif (p_a + p_n) >= threshold_dc:
            best_pick = f"🛡️ Double Chance VIP : Nul ou {a_name} (X2)"
            best_prob = round(p_a + p_n, 1)
            pick_type = "X2"
            selected_odds = prob_to_odds(best_prob)
        elif prob_o15 >= threshold_o15:
            best_pick = "⚽ Plus de 1.5 Buts au Total (Sécurisé)"
            best_prob = prob_o15
            pick_type = "O15"
            selected_odds = prob_to_odds(prob_o15)
        else:
            fav = h_name if p_h > p_a else a_name
            best_pick = f"🔥 Victoire Directe VIP : {fav}"
            best_prob = round(max(p_h, p_a), 1)
            pick_type = "HOME_WIN" if p_h > p_a else "AWAY_WIN"
            selected_odds = prob_to_odds(best_prob)

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "odds_h": prob_to_odds(p_h), "odds_n": prob_to_odds(p_n), "odds_a": prob_to_odds(p_a),
        "odds_o15": prob_to_odds(prob_o15), "odds_o25": prob_to_odds(prob_o25),
        "top_3_scores": top_3_scores,
        "prob_o15": prob_o15, "prob_o25": prob_o25,
        "corners": {"tot": exp_c_tot, "p_4_5": prob_c_4_5, "p_6_5": prob_c_6_5, "odds_4_5": prob_to_odds(prob_c_4_5)},
        "cards": {"tot": exp_k_tot, "p_1_5": prob_k_1_5, "p_2_5": prob_k_2_5, "odds_1_5": prob_to_odds(prob_k_1_5)},
        "live_trends": {"prob_more_goals": prob_more_goals, "prob_more_corners": prob_more_corners_2plus},
        "best_pick": best_pick, "best_prob": best_prob, "pick_type": pick_type, "selected_odds": selected_odds,
        "xg": {"h": full_h_xg, "a": full_a_xg}
    }

# ==========================================
# 4. INTERFACE APPLICATIVE V27.0
# ==========================================
st.sidebar.title("Apex Quant v27.0 👑")
selected_comp = st.sidebar.selectbox("Compétition Principale", list(COMPETITIONS.keys()))

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ PARAMÈTRES VIP")
post_break_mode = st.sidebar.checkbox("🔒 Mode Post-Trêve Internationale", value=True, help="Actif pour neutraliser la volatilité après les sélections nationales.")
bankroll_units = st.sidebar.number_input("Mise par Pari (Unités)", value=10.0, min_value=1.0, step=1.0)

league_code = COMPETITIONS[selected_comp]
team_stats, avg_goals = get_advanced_league_stats(league_code)
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

finished_matches = [m for m in all_matches if m.get('status'] == 'FINISHED']

tab_live, tab_calendar, tab_detail, tab_audit, tab_coupon = st.tabs([
    f"🔴 EN DIRECT ({len(live_matches)})",
    f"📅 CALENDRIER ({len(upcoming_matches)})", 
    "📊 ANALYSE VIP",
    f"📈 AUDIT & BANQUE VIP ({len(finished_matches)})",
    "🎟️ COUPON VIP MULTI-CHAMPIONNATS"
])

# ------------------------------------------
# ONGLET 1 : MATCHS EN DIRECT
# ------------------------------------------
with tab_live:
    if post_break_mode:
        st.markdown('<span class="badge-reprise">👑 MODE VIP POST-TRÈVE : SÉCURITÉ MAXIMALE</span>', unsafe_allow_html=True)
    st.subheader(f"Suivi Live VIP - {selected_comp}")
    if live_matches:
        for m in live_matches:
            h_name = m['homeTeam']['name']
            a_name = m['awayTeam']['name']
            score_obj = m.get('score', {}).get('fullTime', {})
            score_h = score_obj.get('home', 0) if score_obj.get('home') is not None else 0
            score_a = score_obj.get('away', 0) if score_obj.get('away') is not None else 0
            elapsed = 55
            
            res_live = run_quant_prediction_v27(
                h_name, a_name, score_h=score_h, score_a=score_a, 
                elapsed_min=elapsed, team_stats=team_stats, avg_goals=avg_goals, 
                is_live=True, post_break_active=post_break_mode
            )
            
            st.markdown(f"""
            <div class="oracle-card">
                <span class="badge-live">LIVE VIP ({elapsed}') — {score_h} - {score_a}</span>
                <h2 style="color:#38BDF8; margin:10px 0 5px 0;">{h_name} vs {a_name}</h2>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="value-pick-card">
                <div class="value-pick-title">💎 SIGNAL VIP LIVE OPTIMISÉ</div>
                <div class="value-pick-main">{res_live['best_pick']}</div>
                <div style="font-size:1.1rem; font-weight:800;">Probabilité : {res_live['best_prob']}% | Cote estimée : {res_live['selected_odds']}</div>
            </div>
            """, unsafe_allow_html=True)
            st.divider()
    else:
        st.info("Aucun match en direct pour le moment.")

# ------------------------------------------
# ONGLET 2 : CALENDRIER
# ------------------------------------------
with tab_calendar:
    st.subheader(f"Calendrier & Signaux Pré-match - {selected_comp}")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            date_str = m['utcDate'][:10] + " [" + m['utcDate'][11:16] + "]"
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            pred = run_quant_prediction_v27(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False, post_break_active=post_break_mode)
            
            cal_data.append({
                "Date": date_str,
                "Match": f"{h_team} vs {a_team}",
                "Cote 1X2 (H/N/A)": f"{pred['odds_h']} / {pred['odds_n']} / {pred['odds_a']}",
                "Top Score": pred['top_3_scores'][0]['score'],
                "Signal VIP Principal": f"{pred['best_pick']} ({pred['best_prob']}%)"
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match planifié.")

# ------------------------------------------
# ONGLET 3 : ANALYSE VIP DETAILLEE
# ------------------------------------------
with tab_detail:
    st.subheader("Analyse Quant & xG Approfondie")
    if upcoming_matches or all_matches:
        match_options = {}
        pool = upcoming_matches if upcoming_matches else all_matches[:10]
        for m in pool:
            label = f"{m['utcDate'][:10]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}"
            match_options[label] = m
        
        selected_label = st.selectbox("Sélectionner la rencontre VIP :", list(match_options.keys()))
        selected_m = match_options[selected_label]
        
        h_name = selected_m['homeTeam']['name']
        a_name = selected_m['awayTeam']['name']
        res = run_quant_prediction_v27(h_name, a_name, 0, 0, 0, team_stats, avg_goals, is_live=False, post_break_active=post_break_mode)
        
        st.markdown(f"""
        <div class="oracle-card">
            <h1 style="color:#38BDF8; margin:0;">{h_name} vs {a_name}</h1>
            <p style="color:#94A3B8; margin-top:5px;">xG Domicile estimé : <b>{res['xg']['h']:.2f}</b> | xG Extérieur estimé : <b>{res['xg']['a']:.2f}</b></p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="value-pick-card">
            <div class="value-pick-title">🎯 CONSEIL VIP OFFICIEL</div>
            <div class="value-pick-main">{res['best_pick']}</div>
            <div style="font-size:1.1rem; font-weight:800;">Confiance Modèle : {res['best_prob']}% — Cote Recommandée : {res['selected_odds']}</div>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# ONGLET 4 : AUDIT & BANQUE VIP (ULTRA SOPHISTIQUÉ)
# ------------------------------------------
with tab_audit:
    st.markdown("""
    <div class="vip-banner">
        <h2 style="margin:0; color:#F59E0B;">👑 TABLEAU DE BORD FINANCIER & AUDIT VIP</h2>
        <p style="color:#E2E8F0; margin-top:5px;">Suivi rigoureux des performances du canal, calcul du ROI, du Yield et diagnostic IA des écarts.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if finished_matches:
        audit_rows = []
        total_eval = 0
        success_pick_count = 0
        net_units_earned = 0.0
        total_staked = 0.0
        
        for m in finished_matches:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            real_h = m['score']['fullTime']['home']
            real_a = m['score']['fullTime']['away']
            
            if real_h is not None and real_a is not None:
                real_score_str = f"{real_h}-{real_a}"
                real_tot_goals = real_h + real_a
                
                pred = run_quant_prediction_v27(h_team, a_team, 0, 0, 0, team_stats, avg_goals, is_live=False, post_break_active=False)
                
                ptype = pred['pick_type']
                pick_success = False
                
                if ptype == "1X" and real_h >= real_a: pick_success = True
                elif ptype == "X2" and real_a >= real_h: pick_success = True
                elif ptype == "O15" and real_tot_goals > 1: pick_success = True
                elif ptype == "HOME_WIN" and real_h > real_a: pick_success = True
                elif ptype == "AWAY_WIN" and real_a > real_h: pick_success = True
                
                total_staked += bankroll_units
                if pick_success:
                    success_pick_count += 1
                    profit = bankroll_units * (pred['selected_odds'] - 1.0)
                    net_units_earned += profit
                    eval_status = "✅ GAGNÉ"
                else:
                    net_units_earned -= bankroll_units
                    eval_status = "❌ PERDU"
                
                total_eval += 1
                
                audit_rows.append({
                    "Date": m['utcDate'][:10],
                    "Match": f"{h_team} vs {a_team}",
                    "Score": real_score_str,
                    "Signal VIP": pred['best_pick'],
                    "Cote": pred['selected_odds'],
                    "Statut": eval_status,
                    "Unités": round(profit if pick_success else -bankroll_units, 2)
                })
        
        if total_eval > 0:
            win_rate = round((success_pick_count / total_eval) * 100, 1)
            roi = round((net_units_earned / total_staked) * 100, 1) if total_staked > 0 else 0.0
            
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            with kpi1:
                st.markdown(f"""<div class="audit-stat-box"><div style="color:#94A3B8; font-weight:800;">MATCHS AUDITÉS</div><div style="font-size:1.8rem; font-weight:900; color:#38BDF8;">{total_eval}</div></div>""", unsafe_allow_html=True)
            with kpi2:
                st.markdown(f"""<div class="audit-stat-box"><div style="color:#94A3B8; font-weight:800;">WINRATE VIP</div><div style="font-size:1.8rem; font-weight:900; color:#10B981;">{win_rate}%</div></div>""", unsafe_allow_html=True)
            with kpi3:
                st.markdown(f"""<div class="audit-stat-box"><div style="color:#94A3B8; font-weight:800;">PROFIT NET (UNITÉS)</div><div style="font-size:1.8rem; font-weight:900; color:{'#10B981' if net_units_earned >= 0 else '#EF4444'};">{net_units_earned:+.1f} U</div></div>""", unsafe_allow_html=True)
            with kpi4:
                st.markdown(f"""<div class="audit-stat-box"><div style="color:#94A3B8; font-weight:800;">ROI GLOBAL</div><div style="font-size:1.8rem; font-weight:900; color:{'#10B981' if roi >= 0 else '#EF4444'};">{roi:+.1f}%</div></div>""", unsafe_allow_html=True)
            
            st.write(" ")
            st.markdown("### 📋 JOURNAL DES PARIS VIP COMPLETS")
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
            
            st.write(" ")
            st.markdown("### 📢 GÉNÉRATEUR DE RAPPORT POUR LE CANAL VIP (TELEGRAM)")
            telegram_report = f"📊 **BILAN VIP APEX QUANT** 👑\n\n"
            telegram_report += f"📈 Matchs analysés : {total_eval}\n"
            telegram_report += f"🎯 Winrate : {win_rate}%\n"
            telegram_report += f"💰 Profit Net : {net_units_earned:+.1f} Unités\n"
            telegram_report += f"📊 ROI du Canal : {roi:+.1f}%\n\n"
            telegram_report += f"🔥 *La machine continue de tourner en arrière-plan avec le moteur Dixon-Coles & Poisson v27.0 ! Restez connectés pour les prochaines pépites.*"
            
            st.code(telegram_report, language="text")
        else:
            st.info("Aucun match terminé récent avec des scores validés.")
    else:
        st.info("Aucun match terminé disponible pour l'audit.")

# ------------------------------------------
# ONGLET 5 : COUPON MULTI-CHAMPIONNATS VIP
# ------------------------------------------
with tab_coupon:
    st.subheader("🎟️ Générateur de Combiné VIP (5 Matchs)")
    with st.spinner("Analyse institutionnelle des grands championnats en cours..."):
        all_multi_matches, multi_stats, multi_avg = get_all_competitions_upcoming()
    
    if len(all_multi_matches) < 5:
        st.warning("Pas assez de matchs programmés pour former un combiné complet.")
    else:
        dates_dict = {}
        for m in all_multi_matches:
            dates_dict.setdefault(m['utcDate'][:10], []).append(m)
        
        selected_date = st.selectbox("Date du Combiné VIP :", sorted(list(dates_dict.keys())))
        pool_matches = dates_dict.get(selected_date, []) if len(dates_dict.get(selected_date, [])) >= 5 else all_multi_matches
        
        analyzed_list = []
        for m in pool_matches:
            league = m['league_name']
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            pred = run_quant_prediction_v27(h_team, a_team, 0, 0, 0, multi_stats.get(league, {}), multi_avg.get(league, 1.35), False, post_break_mode)
            
            analyzed_list.append({
                "league": league, "match": f"{h_team} vs {a_team}", "time": m['utcDate'][11:16],
                "pick": pred["best_pick"], "prob": pred["best_prob"], "type": pred["pick_type"], "odds": pred["selected_odds"]
            })
        
        analyzed_list.sort(key=lambda x: x["prob"], reverse=True)
        selected_coupon = analyzed_list[:5]
        
        total_odds = np.prod([l["odds"] for l in selected_coupon])
        avg_conf = np.mean([l["prob"] for l in selected_coupon])
        
        st.markdown(f"""
        <div class="vip-banner">
            <h2 style="margin:0; color:#F59E0B;">🔥 COMBINÉ VIP OFFICIEL ({selected_date})</h2>
            <div style="font-size:1.6rem; font-weight:900; color:#FFFFFF; margin-top:8px;">Cote Totale : <span style="color:#38BDF8;">{total_odds:.2f}</span></div>
            <div style="font-size:1.1rem; color:#10B981; font-weight:700;">Fiabilité Moyenne du Combiné : {avg_conf:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        telegram_coupon = f"🎟️ **COMBINÉ VIP SÉCURISÉ APEX QUANT** 👑\n🗓 Date : {selected_date}\n📊 Cote Totale : {total_odds:.2f}\n\n"
        for idx, leg in enumerate(selected_coupon, 1):
            st.markdown(f"""
            <div class="sub-card">
                <span class="badge-league">{leg['league']}</span> <b>[{leg['time']} UTC]</b><br>
                <h3 style="color:#38BDF8; margin:6px 0;">{leg['match']}</h3>
                👉 Choix : <b>{leg['pick']}</b> (Cote : {leg['odds']}) — Fiabilité : {leg['prob']}%
            </div>
            """, unsafe_allow_html=True)
            telegram_coupon += f"{idx}. [{leg['league']}] {leg['match']}\n   👉 {leg['pick']} (Cote: {leg['odds']})\n"
        
        st.write(" ")
        st.code(telegram_pop := telegram_coupon, language="text")
