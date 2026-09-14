import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime, timezone

# ==========================================
# 1. CONFIGURATION & DESIGN INTERFACE ULTIMATE
# ==========================================
st.set_page_config(
    page_title="Apex Quant Engine v26.0 • Premium Terminal",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700;800&display=swap');
    
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .stApp { background-color: #030712; color: #F8FAFC; }
    
    /* En-tête Principal */
    .hero-header {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(3, 7, 18, 0.95) 100%);
        border: 1px solid rgba(56, 189, 248, 0.2);
        box-shadow: 0 20px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1);
        border-radius: 20px;
        padding: 28px;
        margin-bottom: 30px;
    }
    
    /* Cartes de Coupons Glassmorphism */
    .coupon-card-v1 {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(6, 78, 59, 0.25));
        border: 1.5px solid #10B981;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 12px 30px rgba(16, 185, 129, 0.15);
        margin-bottom: 20px;
    }
    
    .coupon-card-v2 {
        background: linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(30, 58, 138, 0.3));
        border: 1.5px solid #3B82F6;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 12px 30px rgba(59, 130, 246, 0.15);
        margin-bottom: 20px;
    }

    /* Badges & Tags */
    .badge-gold {
        background: linear-gradient(90deg, #F59E0B, #D97706);
        color: #000;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    
    .badge-blue {
        background: linear-gradient(90deg, #38BDF8, #2563EB);
        color: #FFF;
        font-weight: 800;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    
    .date-pill {
        background: rgba(56, 189, 248, 0.12);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        padding: 4px 10px;
        border-radius: 8px;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 700;
        font-size: 0.8rem;
    }

    .league-pill {
        background: rgba(241, 245, 249, 0.08);
        color: #94A3B8;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Range de Match dans Coupon */
    .match-row-item {
        background: rgba(15, 23, 42, 0.6);
        border-left: 4px solid #10B981;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 10px 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .match-row-item-blue {
        background: rgba(15, 23, 42, 0.6);
        border-left: 4px solid #3B82F6;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 10px 0;
    }

    /* Modificateurs Streamlit */
    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 800;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONFIGURATION API & COMPÉTITIONS
# ==========================================
API_KEY = "1e9518e7585349f9abe6d5a29ddb83b1"
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "UEFA Europa League": "EL",
    "Ligue des Champions": "CL",
    "Premier League": "PL",
    "La Liga": "PD",
    "Ligue 1": "FL1",
    "Serie A": "SA",
    "Bundesliga": "BL1",
    "Eredivisie": "DED",
    "Primeira Liga": "PPD"
}

@st.cache_data(ttl=300, show_spinner=False)
def fetch_api(endpoint):
    try:
        headers = {"X-Auth-Token": API_KEY}
        res = requests.get(f"{BASE_URL}{endpoint}", headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

@st.cache_data(ttl=1800, show_spinner=False)
def get_league_stats(league_code):
    data = fetch_api(f"competitions/{league_code}/standings")
    stats = {}
    avg_goals_league = 1.35
    
    if data and "standings" in data and len(data["standings"]) > 0:
        table = data["standings"][0].get("table", [])
        total_played, total_gf = 0, 0
        for row in table:
            name = row["team"]["name"]
            played = max(1, row.get("playedGames", 1))
            gf = row.get("goalsFor", 0)
            ga = row.get("goalsAgainst", 0)
            pts = row.get("points", 0)
            
            stats[name] = {
                "gf_pg": gf / played,
                "ga_pg": ga / played,
                "ppg": pts / played,
                "played": played,
                "points": pts
            }
            total_played += played
            total_gf += gf
            
        if total_played > 0:
            avg_goals_league = max(0.9, total_gf / total_played)
            
    return stats, avg_goals_league

# ==========================================
# 3. MOTEUR QUANTITATIF PREDICTIF
# ==========================================
def run_quant_engine(h_name, a_name, team_stats, avg_goals):
    h_stat = team_stats.get(h_name, {"gf_pg": 1.4, "ga_pg": 1.1, "ppg": 1.3})
    a_stat = team_stats.get(a_name, {"gf_pg": 1.2, "ga_pg": 1.3, "ppg": 1.1})
    
    h_form_mult = np.clip(0.9 + (h_stat.get("ppg", 1.3) / 3.0) * 0.25, 0.85, 1.20)
    a_form_mult = np.clip(0.9 + (a_stat.get("ppg", 1.1) / 3.0) * 0.25, 0.85, 1.20)
    
    h_xg = float(np.clip(avg_goals * (h_stat["gf_pg"] / avg_goals) * (a_stat["ga_pg"] / avg_goals) * 1.14 * h_form_mult, 0.4, 3.7))
    a_xg = float(np.clip(avg_goals * (a_stat["gf_pg"] / avg_goals) * (h_stat["ga_pg"] / avg_goals) * 0.88 * a_form_mult, 0.3, 3.2))

    max_g = 7
    matrix = np.zeros((max_g, max_g))

    for h_g in range(max_g):
        for a_g in range(max_g):
            matrix[h_g, a_g] = poisson.pmf(h_g, h_xg) * poisson.pmf(a_g, a_xg)

    matrix /= np.sum(matrix)

    p_h = float(np.sum(np.tril(matrix, -1))) * 100
    p_n = float(np.sum(np.diag(matrix))) * 100
    p_a = float(np.sum(np.triu(matrix, 1))) * 100

    p_u25 = float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j <= 2])) * 100
    p_o15 = float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j >= 2])) * 100
    p_o25 = round(100.0 - p_u25, 1)

    p_btts_no = float(np.sum(matrix[0, :]) + np.sum(matrix[:, 0]) - matrix[0, 0]) * 100
    p_btts_yes = round(100.0 - p_btts_no, 1)

    all_bets = [
        ("1X (Double Chance)", round(p_h + p_n, 1)),
        ("X2 (Double Chance)", round(p_a + p_n, 1)),
        ("Plus de 1.5 Buts", round(p_o15, 1)),
        ("Plus de 2.5 Buts", p_o25),
        ("Les 2 Équipes Marquent", p_btts_yes)
    ]
    
    best_safe = max(all_bets, key=lambda x: x[1])

    return {
        "h_xg": round(h_xg, 2), "a_xg": round(a_xg, 2),
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "p_o15": round(p_o15, 1), "p_o25": p_o25, "p_btts": p_btts_yes,
        "best_safe_advice": best_safe[0], "best_safe_conf": best_safe[1]
    }

# ==========================================
# 4. RECHERCHE GLOBALE MULTI-CHAMPIONNATS
# ==========================================
@st.cache_data(ttl=300, show_spinner="Analyse de tous les matchs en cours...")
def get_all_upcoming_matches():
    all_predictions = []
    
    for comp_name, comp_code in COMPETITIONS.items():
        team_stats, avg_goals = get_league_stats(comp_code)
        raw_matches = fetch_api(f"competitions/{comp_code}/matches")
        matches_list = raw_matches.get("matches", []) if raw_matches else []
        
        upcoming = [m for m in matches_list if m.get('status') in ['SCHEDULED', 'TIMED', 'UPCOMING']]
        
        for m in upcoming:
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            
            # Formate la date (YYYY-MM-DD et HH:MM)
            raw_utc = m['utcDate']
            date_only = raw_utc[:10]
            time_only = raw_utc[11:16]
            
            # Conversion pour affichage élégant DD/MM/YYYY
            dt_obj = datetime.strptime(date_only, "%Y-%m-%d")
            formatted_date = dt_obj.strftime("%d/%m/%Y")
            
            q = run_quant_engine(h_team, a_team, team_stats, avg_goals)
            
            all_predictions.append({
                "league": comp_name,
                "date_raw": date_only,
                "date_formatted": formatted_date,
                "time": time_only,
                "match": f"{h_team} vs {a_team}",
                "home_team": h_team,
                "away_team": a_team,
                "advice": q['best_safe_advice'],
                "conf": q['best_safe_conf'],
                "xg": f"{q['h_xg']} - {q['a_xg']}"
            })
            
    return sorted(all_predictions, key=lambda x: x['conf'], reverse=True)

# ==========================================
# 5. HEADER & BARRE LATÉRALE
# ==========================================
st.markdown("""
<div class="hero-header">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span class="badge-gold">QUANT ENGINE v26.0</span>
            <h1 style="color:#FFF; margin:10px 0 0 0; font-weight:800; font-size:2rem;">Terminal Multi-Championnats & Coupons du Jour</h1>
            <p style="color:#94A3B8; margin:5px 0 0 0; font-size:0.95rem;">Analyse stochastique appliquée et sélection automatique des matchs ultra sûrs.</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.title("⚙️ Paramètres Terminal")
if st.sidebar.button("🔄 Rafraîchir les Données API"):
    st.cache_data.clear()
    st.rerun()

all_data = get_all_upcoming_matches()

# Obtenir toutes les dates uniques triées
available_dates = sorted(list(set(item['date_raw'] for item in all_data)))
today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# Selection de la date pour les coupons du jour
st.sidebar.markdown("---")
st.sidebar.subheader("📅 Sélection Date des Coupons")

if today_str in available_dates:
    default_index = available_dates.index(today_str)
else:
    default_index = 0

selected_coupon_date = st.sidebar.selectbox(
    "Date des matchs pour les 2 coupons :",
    options=available_dates if available_dates else [today_str],
    index=default_index if available_dates else 0
)

# Onglets principaux
t_coupons, t_europa, t_all_cal = st.tabs([
    "🎟️ Coupons du Jour (Matchs du Jour Même)",
    "🏆 Calendrier UEFA Europa League",
    "📊 Calendrier Global Toutes Ligues"
])

# ------------------------------------------
# TAB 1: COUPONS DU JOUR (MATCHS DU JOUR MÊME)
# ------------------------------------------
with t_coupons:
    # Filtrer strictement les matchs se jouant le jour sélectionné
    day_predictions = [p for p in all_data if p['date_raw'] == selected_coupon_date]
    
    formatted_sel_date = datetime.strptime(selected_coupon_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    
    st.markdown(f"""
    <div style="display:flex; align-items:center; gap:15px; margin-bottom:20px;">
        <h2 style="margin:0; font-weight:800; color:#FFF;">Coupons Exclusifs du <span class="date-pill" style="font-size:1.1rem;">{formatted_sel_date}</span></h2>
        <span class="badge-blue">{len(day_predictions)} Matchs Disponibles ce jour</span>
    </div>
    """, unsafe_allow_html=True)

    if len(day_predictions) >= 5:
        c1, c2 = st.columns(2)
        
        # COUPON #1 : TOP 5 DU JOUR
        with c1:
            st.markdown("""
            <div class="coupon-card-v1">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="badge-gold">COUPON #1 • ULTRA SÉCURITÉ DU JOUR</span>
                    <span style="color:#10B981; font-weight:800; font-size:0.85rem;">5 MATCHS DU JOUR</span>
                </div>
                <hr style="border-color:rgba(16, 185, 129, 0.2); margin:15px 0;">
            """, unsafe_allow_html=True)
            
            c1_matches = day_predictions[:5]
            prob_total_c1 = 1.0
            
            for idx, item in enumerate(c1_matches, 1):
                prob_total_c1 *= (item['conf'] / 100.0)
                st.markdown(f"""
                <div class="match-row-item">
                    <div>
                        <span class="league-pill">{item['league']}</span>
                        <div style="font-weight:700; color:#F8FAFC; margin-top:4px;">{idx}. {item['match']}</div>
                        <div style="font-size:0.8rem; color:#94A3B8;">🕒 Heure: <b>{item['time']}</b></div>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#10B981; font-weight:800; font-size:0.95rem;">{item['advice']}</span>
                        <div style="font-size:0.75rem; color:#64748B;">Confiance: {item['conf']}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown(f"""
                <hr style="border-color:rgba(16, 185, 129, 0.2); margin:15px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#94A3B8; font-size:0.85rem;">Indice de Fiabilité Globale:</span>
                    <span style="color:#10B981; font-weight:800; font-size:1.2rem;">{round(prob_total_c1 * 100, 1)}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # COUPON #2 : TOP 5 ALTERNATIF DU JOUR
        with c2:
            st.markdown("""
            <div class="coupon-card-v2">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="badge-blue">COUPON #2 • ÉQUILIBRÉ & SECURE</span>
                    <span style="color:#38BDF8; font-weight:800; font-size:0.85rem;">5 MATCHS DU JOUR</span>
                </div>
                <hr style="border-color:rgba(59, 130, 246, 0.2); margin:15px 0;">
            """, unsafe_allow_html=True)
            
            c2_matches = day_predictions[5:10] if len(day_predictions) >= 10 else day_predictions[:5]
            prob_total_c2 = 1.0
            
            for idx, item in enumerate(c2_matches, 1):
                prob_total_c2 *= (item['conf'] / 100.0)
                st.markdown(f"""
                <div class="match-row-item-blue">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span class="league-pill">{item['league']}</span>
                            <div style="font-weight:700; color:#F8FAFC; margin-top:4px;">{idx}. {item['match']}</div>
                            <div style="font-size:0.8rem; color:#94A3B8;">🕒 Heure: <b>{item['time']}</b></div>
                        </div>
                        <div style="text-align:right;">
                            <span style="color:#38BDF8; font-weight:800; font-size:0.95rem;">{item['advice']}</span>
                            <div style="font-size:0.75rem; color:#64748B;">Confiance: {item['conf']}%</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown(f"""
                <hr style="border-color:rgba(59, 130, 246, 0.2); margin:15px 0;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="color:#94A3B8; font-size:0.85rem;">Indice de Fiabilité Globale:</span>
                    <span style="color:#38BDF8; font-weight:800; font-size:1.2rem;">{round(prob_total_c2 * 100, 1)}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    elif len(day_predictions) > 0:
        st.warning(f"Il y a seulement {len(day_predictions)} match(s) programmé(s) pour le {formatted_sel_date}. 5 matchs minimum sont requis pour former les coupons.")
        st.dataframe(pd.DataFrame(day_predictions)[['date_formatted', 'time', 'league', 'match', 'advice', 'conf']], use_container_width=True)
    else:
        st.info(f"Aucun match au programme pour la date du {formatted_sel_date}. Utilisez la barre latérale pour sélectionner une autre date.")

# ------------------------------------------
# TAB 2: CALENDRIER EUROPA LEAGUE DÉDIÉ
# ------------------------------------------
with t_europa:
    st.markdown("""
    <div style="margin-bottom:20px;">
        <h2 style="font-weight:800; color:#FFF; margin:0;">🏆 Calendrier Officiel UEFA Europa League</h2>
        <p style="color:#94A3B8; margin:5px 0 0 0;">Visualisation claire des rencontres avec la date et l'heure placées devant chaque match.</p>
    </div>
    """, unsafe_allow_html=True)
    
    el_matches = [p for p in all_data if p['league'] == "UEFA Europa League"]
    
    if el_matches:
        # Trier chronologiquement
        el_matches_sorted = sorted(el_matches, key=lambda x: (x['date_raw'], x['time']))
        
        el_grid = []
        for m in el_matches_sorted:
            el_grid.append({
                "🗓️ Date & Heure": f"📅 {m['date_formatted']} à {m['time']}",
                "⚽ Rencontre Europa League": m['match'],
                "🎯 Option Recommandée": m['advice'],
                "🔥 Niveau de Confiance": f"{m['conf']}%",
                "📊 xG Estimés": m['xg']
            })
            
        st.dataframe(
            pd.DataFrame(el_grid),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Aucun match d'Europa League programmé ou disponible dans l'API pour les prochains jours.")

# ------------------------------------------
# TAB 3: CALENDRIER GLOBAL TOUTES LIGUES
# ------------------------------------------
with t_all_cal:
    st.subheader("📊 Calendrier Général Toutes Compétitions")
    
    all_grid = []
    for m in sorted(all_data, key=lambda x: (x['date_raw'], x['time'])):
        all_grid.append({
            "🗓️ Date & Heure": f"{m['date_formatted']} ({m['time']})",
            "🏆 Championnat": m['league'],
            "⚔️ Rencontre": m['match'],
            "💡 Prédiction": m['advice'],
            "📈 Confiance": f"{m['conf']}%"
        })
        
    st.dataframe(pd.DataFrame(all_grid), use_container_width=True, hide_index=True)
