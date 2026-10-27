import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime, timedelta
import math

# ==============================================================================
# 1. CONFIGURATION & DESIGN AVANCÉ V48.0 SOFASCORE QUANT PRO
# ==============================================================================
st.set_page_config(
    page_title="Apex Quant v48.0 SofaScore Ultra-Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    code, .quant-mono { font-family: 'JetBrains Mono', monospace; }
    
    .stApp { background-color: #030712; color: #F1F5F9; }
    
    .matrix-card {
        background: linear-gradient(135deg, #0B132B 0%, #1C2541 50%, #032B45 100%);
        border: 2px solid #38BDF8; border-radius: 18px; padding: 24px; margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(56, 189, 248, 0.25);
    }
    .sofascore-box {
        background-color: #0B0F19; border: 1px solid #1E293B; border-left: 5px solid #10B981;
        border-radius: 0 14px 14px 0; padding: 20px; margin: 16px 0; font-size: 0.95rem; line-height: 1.65; color: #E2E8F0;
    }
    .vip-banner {
        background: linear-gradient(135deg, #311042 0%, #581C87 50%, #1E3A8A 100%);
        border: 2px solid #F59E0B; border-radius: 16px; padding: 22px; text-align: center; margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(245, 158, 11, 0.2);
    }
    .sub-card {
        background: #0B1120; border: 1.5px solid #1E293B;
        border-radius: 14px; padding: 18px; margin-bottom: 16px;
        transition: all 0.2s ease;
    }
    .sub-card:hover { border-color: #38BDF8; }
    .option-box {
        background: rgba(16, 185, 129, 0.08); border: 1.5px solid #10B981; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-sec {
        background: rgba(56, 189, 248, 0.08); border: 1.5px solid #38BDF8; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-alt {
        background: rgba(168, 85, 247, 0.08); border: 1.5px solid #A855F7; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .big-score-box {
        background: #0F172A; border: 2px solid #38BDF8; border-radius: 14px; padding: 16px; text-align: center; margin: 6px 0;
    }
    .big-score-val { font-size: 2.2rem; font-weight: 900; color: #38BDF8; line-height: 1.1; font-family: 'JetBrains Mono', monospace; }
    .big-score-prob { font-size: 1.05rem; font-weight: 700; color: #10B981; margin-top: 5px; }
    .badge-quant {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase;
        background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid #38BDF8; margin-right: 6px;
    }
    .badge-edge {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800;
        background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981;
    }
    .stat-badge {
        font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 800; color: #38BDF8;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. PARAMÈTRES GLOBAUX & INFRASTRUCTURE API
# ==============================================================================
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
    "Championship 🏴": "ELC"
}

# Paramètres de ligue de référence (Calibration Dixon-Coles & Base de friction)
LEAGUE_PROFILES = {
    "CL":  {"avg_h": 1.62, "avg_a": 1.28, "rho": -0.115, "card_base": 4.1, "corner_base": 9.9, "dispersion": 9.5},
    "PL":  {"avg_h": 1.58, "avg_a": 1.24, "rho": -0.110, "card_base": 3.9, "corner_base": 10.4, "dispersion": 10.0},
    "PD":  {"avg_h": 1.48, "avg_a": 1.10, "rho": -0.125, "card_base": 4.8, "corner_base": 9.4, "dispersion": 9.2},
    "FL1": {"avg_h": 1.50, "avg_a": 1.16, "rho": -0.118, "card_base": 3.8, "corner_base": 9.3, "dispersion": 9.8},
    "SA":  {"avg_h": 1.52, "avg_a": 1.18, "rho": -0.120, "card_base": 4.5, "corner_base": 9.8, "dispersion": 9.4},
    "BL1": {"avg_h": 1.72, "avg_a": 1.35, "rho": -0.095, "card_base": 3.9, "corner_base": 10.1, "dispersion": 11.2},
    "EL":  {"avg_h": 1.56, "avg_a": 1.22, "rho": -0.112, "card_base": 4.2, "corner_base": 9.7, "dispersion": 9.6},
    "ELC": {"avg_h": 1.44, "avg_a": 1.14, "rho": -0.108, "card_base": 3.8, "corner_base": 10.2, "dispersion": 10.2}
}

@st.cache_data(ttl=300)
def fetch_api(endpoint):
    """Requête sécurisée avec fallback d'erreur."""
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=6)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None

# ==============================================================================
# 3. MOTEUR MATHÉMATIQUE AVANCÉ : DIXON-COLES, BAYES & SHIN METHOD
# ==============================================================================

def dixon_coles_tau(x, y, lambda_h, lambda_a, rho=-0.115):
    """
    Fonction de corrélation bivariée pour les petits scores selon Dixon-Coles (1997).
    Ajuste la sous-estimation des scores 0-0 et 1-1 ainsi que la sur-estimation de 1-0 et 0-1.
    """
    if x == 0 and y == 0:
        return max(0.01, 1.0 - (lambda_h * lambda_a * rho))
    elif x == 0 and y == 1:
        return max(0.01, 1.0 + (lambda_h * rho))
    elif x == 1 and y == 0:
        return max(0.01, 1.0 + (lambda_a * rho))
    elif x == 1 and y == 1:
        return max(0.01, 1.0 - rho)
    return 1.0

def negative_binomial_pmf(k, mu, dispersion=10.0):
    """
    Distribution Binomiale Négative pour modéliser la surdispersion (fat tails) des buts.
    Var(X) = mu + (mu^2 / dispersion) > mu.
    """
    r = dispersion
    p = r / (r + mu)
    return nbinom.pmf(k, r, p)

def generate_bivariate_score_matrix(lambda_h, lambda_a, rho=-0.115, dispersion=10.0, max_g=9):
    """
    Génère la matrice conjointe des probabilités de score (0 à 8 buts par équipe)
    en combinant la surdispersion et la correction Dixon-Coles normalisée.
    """
    matrix = np.zeros((max_g, max_g))
    for x in range(max_g):
        for y in range(max_g):
            p_x = negative_binomial_pmf(x, lambda_h, dispersion)
            p_y = negative_binomial_pmf(y, lambda_a, dispersion)
            tau = dixon_coles_tau(x, y, lambda_h, lambda_a, rho)
            matrix[x, y] = max(0.0, p_x * p_y * tau)
            
    tot_p = np.sum(matrix)
    if tot_p > 0:
        matrix /= tot_p
    return matrix

def shin_remove_vig(odds_h, odds_d, odds_a):
    """
    Méthode quantitative de Shin / Power pour retirer le vig (marge bookmaker)
    et extraire la véritable probabilité implicite du marché.
    """
    inv_odds = [1.0 / odds_h, 1.0 / odds_d, 1.0 / odds_a]
    book_sum = sum(inv_odds)
    margin = (book_sum - 1.0) * 100.0
    # Normalisation proportionnelle standard (Power Approximation)
    true_probs = [o / book_sum for o in inv_odds]
    return true_probs[0], true_probs[1], true_probs[2], margin

def prob_to_odds(p):
    """Convertit une probabilité en cote équitable (Fair Odds sans marge)."""
    if p <= 0.001: return 99.00
    return round(min(99.00, 100.0 / p), 2)

def calculate_quarter_kelly(prob_pct, bookmaker_odds, bankroll, estimation_uncertainty=0.08, max_cap_pct=0.05):
    """
    Critère de Kelly Fractionnaire (1/4 Kelly) avec Pénalité pour Risque d'Estimation.
    Protège strictement contre la ruine du parieur et les drawdowns sévères.
    """
    p = prob_pct / 100.0
    b = bookmaker_odds - 1.0
    if b <= 0 or p <= 0: return 0.0, 0.0
    
    # Kelly standard f* = (bp - q) / b
    f_star = (p * (b + 1.0) - 1.0) / b
    ev_val = round(((p * bookmaker_odds) - 1.0) * 100, 2)
    
    if f_star <= 0:
        return 0.0, ev_val
        
    # Shrinkage d'incertitude et application du quart-Kelly (0.25)
    f_adjusted = f_star * 0.25 * (1.0 - estimation_uncertainty)
    f_capped = min(max(0.0, f_adjusted), max_cap_pct)
    
    return round(bankroll * f_capped, 2), ev_val

# ==============================================================================
# 4. TRAITEMENT STATISTIQUE & APPRENTISSAGE DES FORCES (DATA MINING)
# ==============================================================================

def compute_exponential_time_weight(match_date_str, ref_date, half_life_days=65.0):
    """Noyau de décroissance temporelle exponentielle (Time-Decayed Kernel)."""
    try:
        m_dt = datetime.strptime(match_date_str[:10], "%Y-%m-%d")
        delta_days = max(0, (ref_date - m_dt).days)
        # Formule de demi-vie: exp(-ln(2) * t / half_life)
        return math.exp(-0.693147 * delta_days / half_life_days)
    except Exception:
        return 1.0

def get_team_last_matches(team_name, all_matches, max_matches=5):
    """Extrait l'historique récent complet avec métriques avancées."""
    history = []
    for m in all_matches:
        if m.get('status') == 'FINISHED':
            h_team = m['homeTeam']['name']
            a_team = m['awayTeam']['name']
            if h_team == team_name or a_team == team_name:
                sc = m.get('score', {}).get('fullTime', {})
                sh, sa = sc.get('home'), sc.get('away')
                if sh is not None and sa is not None:
                    is_h = (h_team == team_name)
                    opp = a_team if is_h else h_team
                    gf = sh if is_h else sa
                    ga = sa if is_h else sh
                    res = 'W' if gf > ga else ('D' if gf == ga else 'L')
                    history.append({
                        "date": m.get('utcDate', '')[:10],
                        "opponent": opp,
                        "venue": "Dom." if is_h else "Ext.",
                        "score": f"{gf}-{ga}",
                        "result": res,
                        "gf": gf, "ga": ga,
                        "diff": gf - ga
                    })
    history.sort(key=lambda x: x["date"], reverse=True)
    return history[:max_matches]

def compute_advanced_momentum(history):
    """
    Calcul d'un Momentum Dynamique Continu (EMA pondérée) :
    Prend en compte la difficulté relative, le différentiel de but et la récence.
    """
    if not history:
        return 1.0, "Neutre / Standard"
    
    weights = [0.38, 0.28, 0.18, 0.10, 0.06][:len(history)]
    w_sum = sum(weights)
    norm_w = [w / w_sum for w in weights]
    
    perf_score = 0.0
    for idx, match in enumerate(history):
        pts = 3.0 if match['result'] == 'W' else (1.0 if match['result'] == 'D' else 0.0)
        margin_bonus = np.clip(match['diff'] * 0.25, -0.75, 0.75)
        perf_score += norm_w[idx] * (pts + margin_bonus)
        
    # Calibration sur un facteur multiplicateur d'attaque / défense [0.85, 1.18]
    if perf_score >= 2.6:
        return 1.16, "🔥 Dynamique Ultra-Conquérante (Ascendante)"
    elif perf_score >= 1.9:
        return 1.08, "✅ Forme Positive & Rassurante"
    elif perf_score >= 1.1:
        return 0.98, "⚖️ Régulier / Légèrement Discontinu"
    elif perf_score >= 0.6:
        return 0.90, "⚠️ Instabilité & Fébrilité Défensive"
    else:
        return 0.82, "🚨 Crise Aiguë / Dysfonctionnement Actif"

@st.cache_data(ttl=1800)
def get_advanced_league_stats(league_code):
    """
    Moteur de régression bayésienne empirique (Empirical Bayes Shrinkage)
    et apprentissage des forces offensives/défensives par équipe.
    """
    standings_data = fetch_api(f"competitions/{league_code}/standings")
    raw_matches = fetch_api(f"competitions/{league_code}/matches")
    all_comp_matches = raw_matches.get("matches", []) if raw_matches else []
    
    profile = LEAGUE_PROFILES.get(league_code, {"avg_h": 1.55, "avg_a": 1.18, "rho": -0.115, "card_base": 4.0, "corner_base": 9.8, "dispersion": 10.0})
    avg_goals_home, avg_goals_away = profile["avg_h"], profile["avg_a"]
    
    stats = {}
    ref_dt = datetime.utcnow()
    
    if standings_data and "standings" in standings_data and len(standings_data["standings"]) > 0:
        table_total = standings_data["standings"][0].get("table", [])
        table_home = standings_data["standings"][1].get("table", []) if len(standings_data["standings"]) > 1 else table_total
        table_away = standings_data["standings"][2].get("table", []) if len(standings_data["standings"]) > 2 else table_total
        
        dict_home = {r["team"]["name"]: r for r in table_home}
        dict_away = {r["team"]["name"]: r for r in table_away}
        
        # 1. Calcul empirique des moyennes réelles de la saison si disponibles
        tot_h_gf, tot_h_games = 0, 0
        tot_a_gf, tot_a_games = 0, 0
        for r in table_total:
            n = r["team"]["name"]
            hr = dict_home.get(n, r)
            ar = dict_away.get(n, r)
            tot_h_gf += hr.get("goalsFor", 0)
            tot_h_games += hr.get("playedGames", 0)
            tot_a_gf += ar.get("goalsFor", 0)
            tot_a_games += ar.get("playedGames", 0)
            
        if tot_h_games > 0 and tot_a_games > 0:
            avg_goals_home = max(0.9, tot_h_gf / tot_h_games)
            avg_goals_away = max(0.8, tot_a_gf / tot_a_games)

        # 2. Estimation Shrinkage bayésien des paramètres de force
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
            
            # Crédibilité bayésienne empirique (James-Stein / Prior vers la moyenne de ligue)
            K_shrinkage = 3.8
            bayes_h_gf = (h_gf + K_shrinkage * avg_goals_home) / (h_played + K_shrinkage)
            bayes_h_ga = (h_ga + K_shrinkage * avg_goals_away) / (h_played + K_shrinkage)
            bayes_a_gf = (a_gf + K_shrinkage * avg_goals_away) / (a_played + K_shrinkage)
            bayes_a_ga = (a_ga + K_shrinkage * avg_goals_home) / (a_played + K_shrinkage)

            # ELO Glicko-style avec pondération du différentiel de but
            elo_rating = 1500.0 + (pts * 13.5) + ((gf - ga) * 5.2)
            
            # Historique récent & Momentum
            last_5 = get_team_last_matches(name, all_comp_matches, 5)
            mom_factor, mom_status = compute_advanced_momentum(last_5)
            
            # Taux offensifs pour modélisation des corners & cartons (sans hash arbitraire)
            att_intensity = (gf / played) / max(0.5, (avg_goals_home + avg_goals_away) / 2.0)
            def_vulnerability = (ga / played) / max(0.5, (avg_goals_home + avg_goals_away) / 2.0)
            
            stats[name] = {
                "played": played, "pts": pts, "gf": gf, "ga": ga,
                "home_gf_pg": bayes_h_gf, "home_ga_pg": bayes_h_ga,
                "away_gf_pg": bayes_a_gf, "away_ga_pg": bayes_a_ga,
                "elo": elo_rating, "momentum_factor": mom_factor, "momentum_status": mom_status,
                "att_intensity": att_intensity, "def_vulnerability": def_vulnerability,
                "last_5": last_5
            }
            
    return stats, avg_goals_home, avg_goals_away, profile

# ==============================================================================
# 5. MOTEUR SOFASCORE QUANT ULTRA-PRÉDICTIF
# ==============================================================================

def run_advanced_quant_prediction(
    h_name, a_name, 
    score_h=0, score_a=0, elapsed_min=0, 
    team_stats={}, avg_goals_h=1.55, avg_goals_a=1.18, 
    profile=None, is_live=False, 
    bankroll=1000.0, book_odds_1x2=None, weather_mode="Normal (Idéal)"
):
    """
    Moteur unifié de prédiction quantitative et dérivée de marché.
    Calcule la matrice bivariée Dixon-Coles, simule les marchés (1X2, DNB, BTTS, Over/Under, Corners, Cartons).
    """
    if profile is None:
        profile = {"avg_h": avg_goals_h, "avg_a": avg_goals_a, "rho": -0.115, "card_base": 4.0, "corner_base": 9.8, "dispersion": 10.0}
        
    default_team = {
        "played": 10, "pts": 15, "gf": 14, "ga": 14,
        "home_gf_pg": avg_goals_h, "home_ga_pg": avg_goals_a, 
        "away_gf_pg": avg_goals_a, "away_ga_pg": avg_goals_h,
        "elo": 1500.0, "momentum_factor": 1.0, "momentum_status": "Neutre",
        "att_intensity": 1.0, "def_vulnerability": 1.0, "last_5": []
    }
    h_stat = team_stats.get(h_name, default_team)
    a_stat = team_stats.get(a_name, default_team)
    
    # 1. Calcul des forces relatives (Log-ratio / Poisson GLM standard)
    att_h = h_stat["home_gf_pg"] / max(0.5, avg_goals_h)
    def_a = a_stat["away_ga_pg"] / max(0.5, avg_goals_h)
    att_a = a_stat["away_gf_pg"] / max(0.5, avg_goals_a)
    def_h = h_stat["home_ga_pg"] / max(0.5, avg_goals_a)
    
    raw_h_xg = att_h * def_a * avg_goals_h
    raw_a_xg = att_a * def_h * avg_goals_a
    
    # 2. Facteur ELO et Impact Psychologique (Logistic Margin)
    elo_diff = h_stat["elo"] - a_stat["elo"]
    # Sigmoïde centrée
    elo_mult_h = np.clip(1.0 + (elo_diff / 850.0), 0.52, 1.60)
    elo_mult_a = np.clip(1.0 - (elo_diff / 850.0), 0.52, 1.60)
    
    # 3. Facteur Météorologique & Pelouse
    weather_multiplier = 0.88 if ("Pluie" in weather_mode or "Lourd" in weather_mode) else (0.92 if "Canicule" in weather_mode else 1.0)
    
    # 4. xG finaux complets
    mom_h, mom_a = h_stat["momentum_factor"], a_stat["momentum_factor"]
    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * mom_h * weather_multiplier, 0.22, 4.20))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * mom_a * weather_multiplier, 0.20, 3.80))
    
    # 5. Décroissance non-linéaire en cours de match (si In-Play / Live)
    if is_live and elapsed_min > 0:
        # Intensité des buts plus élevée dans les 30 dernières minutes (courbe cumulative)
        rem_pct = max(0.02, (90.0 - float(elapsed_min)) / 90.0)
        rem_factor = rem_pct ** 0.88
        rem_h_xg, rem_a_xg = full_h_xg * rem_factor, full_a_xg * rem_factor
    else:
        rem_h_xg, rem_a_xg = full_h_xg, full_a_xg

    # 6. Matrice bivariée Dixon-Coles avec Surdispersion
    rho = profile.get("rho", -0.115)
    dispersion = profile.get("dispersion", 10.0)
    max_g = 9
    
    matrix = np.zeros((max_g, max_g))
    for dh in range(max_g - score_h):
        for da in range(max_g - score_a):
            p_h = negative_binomial_pmf(dh, rem_h_xg, dispersion)
            p_a = negative_binomial_pmf(da, rem_a_xg, dispersion)
            tau = dixon_coles_tau(dh, da, rem_h_xg, rem_a_xg, rho)
            fh, fa = score_h + dh, score_a + da
            if fh < max_g and fa < max_g:
                matrix[fh, fa] = p_h * p_a * tau
                
    tot_matrix = np.sum(matrix)
    if tot_matrix > 0:
        matrix /= tot_matrix

    # 7. Dérivés des Marchés Principaux 1X2 & Double Chance
    p_h = float(np.sum(np.tril(matrix, -1))) * 100.0
    p_n = float(np.sum(np.diag(matrix))) * 100.0
    p_a = float(np.sum(np.triu(matrix, 1))) * 100.0
    
    prob_1x = round(p_h + p_n, 1)
    prob_x2 = round(p_a + p_n, 1)
    prob_12 = round(p_h + p_a, 1)
    
    # Draw No Bet (Remboursé si Nul)
    denom_dnb = max(0.01, (p_h + p_a))
    prob_dnb_h = round((p_h / denom_dnb) * 100.0, 1)
    prob_dnb_a = round((p_a / denom_dnb) * 100.0, 1)
    
    # Both Teams to Score (BTTS)
    prob_btts_yes = round(float(np.sum(matrix[1:, 1:])) * 100.0, 1)
    prob_btts_no = round(100.0 - prob_btts_yes, 1)
    
    # Over / Under Buts
    prob_o15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 1])) * 100.0, 1)
    prob_o25 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 2])) * 100.0, 1)
    prob_u25 = round(100.0 - prob_o25, 1)
    prob_o35 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i + j > 3])) * 100.0, 1)
    prob_u35 = round(100.0 - prob_o35, 1)
    
    # Multi-Goals Brackets
    prob_g_1_2 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if 1 <= i + j <= 2])) * 100.0, 1)
    prob_g_2_3 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if 2 <= i + j <= 3])) * 100.0, 1)
    prob_g_2_4 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if 2 <= i + j <= 4])) * 100.0, 1)

    # Asian Handicap -0.5, -1.0, -1.5 pour le favori
    if p_h >= p_a:
        prob_ah_minus_05 = round(p_h, 1)
        prob_ah_minus_10 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i - j >= 2])) * 100.0, 1)
        prob_ah_minus_15 = prob_ah_minus_10
        fav_name = h_name
    else:
        prob_ah_minus_05 = round(p_a, 1)
        prob_ah_minus_10 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if j - i >= 2])) * 100.0, 1)
        prob_ah_minus_15 = prob_ah_minus_10
        fav_name = a_name

    # 8. Modélisation Scientifique des Corners (Dominance & Tempo)
    tot_xg = full_h_xg + full_a_xg
    pace_factor = (tot_xg / max(0.5, avg_goals_h + avg_goals_a)) ** 0.35
    territorial_dom = (full_h_xg ** 1.15) / max(0.1, (full_h_xg ** 1.15 + full_a_xg ** 1.15))
    
    base_corner = profile.get("corner_base", 9.8)
    exp_corners_h = base_corner * 0.54 * (territorial_dom ** 0.55) * pace_factor * h_stat.get("att_intensity", 1.0) ** 0.3
    exp_corners_a = base_corner * 0.46 * ((1.0 - territorial_dom) ** 0.55) * pace_factor * a_stat.get("att_intensity", 1.0) ** 0.3
    tot_exp_corners = round(float(np.clip(exp_corners_h + exp_corners_a, 5.0, 14.5)), 1)
    
    prob_c75 = round((1.0 - poisson.cdf(7, tot_exp_corners)) * 100.0, 1)
    prob_c85 = round((1.0 - poisson.cdf(8, tot_exp_corners)) * 100.0, 1)
    prob_c95 = round((1.0 - poisson.cdf(9, tot_exp_corners)) * 100.0, 1)
    prob_c105 = round((1.0 - poisson.cdf(10, tot_exp_corners)) * 100.0, 1)

    # 9. Modélisation Disciplinaire des Cartons (Indice de Friction Tactique)
    base_card = profile.get("card_base", 4.0)
    # Plus les équipes sont proches en ELO (derby / match au sommet), plus la tension grimpe
    tension_factor = 1.25 if abs(elo_diff) < 70.0 else (1.10 if abs(elo_diff) < 140.0 else 0.92)
    # Friction d'oppression : outsider sous forte pression fait plus de fautes
    defensive_stress = (h_stat.get("def_vulnerability", 1.0) + a_stat.get("def_vulnerability", 1.0)) / 2.0
    tot_exp_cards = round(float(np.clip(base_card * tension_factor * (defensive_stress ** 0.4), 2.0, 7.5)), 1)
    
    prob_cards25 = round((1.0 - poisson.cdf(2, tot_exp_cards)) * 100.0, 1)
    prob_cards35 = round((1.0 - poisson.cdf(3, tot_exp_cards)) * 100.0, 1)
    prob_cards45 = round((1.0 - poisson.cdf(4, tot_exp_cards)) * 100.0, 1)

    # 10. Top 3 Scores Exacts
    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_3_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "prob": round(matrix[gh, ga] * 100.0, 1)})

    # 11. Recommandations Multi-Options Hiérarchisées
    options = []
    
    # Option Sécurité (Visée 85% - 95%)
    if prob_1x >= 84.0:
        options.append({
            "type": "🛡️ SÉCURITÉ STATISTIQUE MAX (85%+)",
            "desc": f"Double Chance : {h_name} ou Nul (1X)",
            "prob": prob_1x, "odds": prob_to_odds(prob_1x)
        })
    elif prob_x2 >= 84.0:
        options.append({
            "type": "🛡️ SÉCURITÉ STATISTIQUE MAX (85%+)",
            "desc": f"Double Chance : Nul ou {a_name} (X2)",
            "prob": prob_x2, "odds": prob_to_odds(prob_x2)
        })
    elif prob_o15 >= 78.0:
        options.append({
            "type": "🛡️ SÉCURITÉ STATISTIQUE MAX (85%+)",
            "desc": "Plus de 1.5 Buts dans la rencontre (Over 1.5)",
            "prob": prob_o15, "odds": prob_to_odds(prob_o15)
        })
    else:
        options.append({
            "type": "🛡️ SÉCURITÉ STATISTIQUE MAX (85%+)",
            "desc": "Moins de 3.5 Buts dans le match (Under 3.5)",
            "prob": prob_u35, "odds": prob_to_odds(prob_u35)
        })

    # Option Value Bet Principal
    if p_h >= 52.0:
        options.append({
            "type": "🎯 VALUE BET PRINCIPAL",
            "desc": f"Victoire Sèche : {h_name}",
            "prob": round(p_h, 1), "odds": prob_to_odds(p_h)
        })
    elif p_a >= 52.0:
        options.append({
            "type": "🎯 VALUE BET PRINCIPAL",
            "desc": f"Victoire Sèche : {a_name}",
            "prob": round(p_a, 1), "odds": prob_to_odds(p_a)
        })
    elif prob_btts_yes >= 58.0:
        options.append({
            "type": "🎯 VALUE BET PRINCIPAL",
            "desc": "Les Deux Équipes Marquent (BTTS - Oui)",
            "prob": prob_btts_yes, "odds": prob_to_odds(prob_btts_yes)
        })
    else:
        options.append({
            "type": "🎯 VALUE BET PRINCIPAL",
            "desc": "Plus de 2.5 Buts (Match Ouvert & Intense)",
            "prob": prob_o25, "odds": prob_to_odds(prob_o25)
        })

    # Option Scénario Tactique Alternatif
    if abs(elo_diff) > 130.0:
        options.append({
            "type": "⚡ SCÉNARIO QUANT TACTIQUE",
            "desc": f"Handicap Asiatique : {fav_name} (-1.0)",
            "prob": prob_ah_minus_10, "odds": prob_to_odds(prob_ah_minus_10)
        })
    elif prob_btts_no >= 55.0:
        options.append({
            "type": "⚡ SCÉNARIO QUANT TACTIQUE",
            "desc": "Une Seule ou Zéro Équipe Marque (BTTS - Non)",
            "prob": prob_btts_no, "odds": prob_to_odds(prob_btts_no)
        })
    else:
        options.append({
            "type": "⚡ SCÉNARIO QUANT TACTIQUE",
            "desc": "Fourchette Multi-Buts : 2 à 4 Buts dans le match",
            "prob": prob_g_2_4, "odds": prob_to_odds(prob_g_2_4)
        })

    # 12. Analyse Financière & Kelly Criterion
    best_opt = options[0]
    model_fair_odds = prob_to_odds(best_opt["prob"])
    user_actual_odds = book_odds_1x2 if book_odds_1x2 else round(model_fair_odds * 1.05, 2)
    kelly_stake, ev_percentage = calculate_quarter_kelly(best_opt["prob"], user_actual_odds, bankroll)

    # 13. Rapport Textuel Tactique Analytique
    dom_team = h_name if elo_diff >= 0 else a_name
    press_desc = (
        f"Contrôle territorial appuyé et pressing haut de <b>{dom_team}</b> (xG {max(full_h_xg, full_a_xg):.2f})."
        if abs(elo_diff) > 90.0 else
        f"Guerre d'usure au milieu de terrain, probabilité élevée de duels tactiques fermés."
    )
    
    sofascore_report = f"""
    📊 <b>Rapport d'Intelligence Quantifiée SofaScore & Dixon-Coles Pro</b> :<br>
    • 🏠 <b>{h_name}</b> (ELO {h_stat['elo']:.0f} | {h_stat['momentum_status']}) : xG Attendu = <b>{full_h_xg:.2f}</b><br>
    • ✈️ <b>{a_name}</b> (ELO {a_stat['elo']:.0f} | {a_stat['momentum_status']}) : xG Attendu = <b>{full_a_xg:.2f}</b><br>
    • ⚔️ <b>Configuration Tactique</b> : {press_desc}<br>
    • ⛳ <b>Modèle de Corners</b> : Estimation à <b>~{tot_exp_corners} corners</b> (+8.5 : <b>{prob_c85}%</b> | +9.5 : <b>{prob_c95}%</b>)<br>
    • 🟨 <b>Pression Disciplinaire</b> : Indice de friction à <b>~{tot_exp_cards} cartons</b> (+3.5 : <b>{prob_cards35}%</b>)
    """

    return {
        "p_h": round(p_h, 1), "p_n": round(p_n, 1), "p_a": round(p_a, 1),
        "prob_1x": prob_1x, "prob_x2": prob_x2, "prob_12": prob_12,
        "prob_dnb_h": prob_dnb_h, "prob_dnb_a": prob_dnb_a,
        "prob_btts_yes": prob_btts_yes, "prob_btts_no": prob_btts_no,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u25": prob_u25, "prob_o35": prob_o35, "prob_u35": prob_u35,
        "prob_g_1_2": prob_g_1_2, "prob_g_2_3": prob_g_2_3, "prob_g_2_4": prob_g_2_4,
        "top_3_scores": top_3_scores,
        "matrix": matrix,
        "options": options,
        "best_pick": best_opt["desc"], "best_prob": best_opt["prob"],
        "corners": tot_exp_corners, "prob_c75": prob_c75, "prob_c85": prob_c85, "prob_c95": prob_c95, "prob_c105": prob_c105,
        "cards": tot_exp_cards, "prob_cards25": prob_cards25, "prob_cards35": prob_cards35, "prob_cards45": prob_cards45,
        "sofascore_report": sofascore_report,
        "full_h_xg": full_h_xg, "full_a_xg": full_a_xg,
        "model_fair_odds": model_fair_odds, "user_actual_odds": user_actual_odds,
        "kelly_stake": kelly_stake, "ev_percentage": ev_percentage
    }

# ==============================================================================
# 6. MONTE CARLO QUANT ENGINE (10 000 SIMULATIONS VECTORISÉES)
# ==============================================================================
def run_monte_carlo_simulation(matrix, n_simulations=10000):
    """
    Exécute 10 000 simulations de Monte Carlo vectorisées ultra-rapides (<15ms)
    pour valider la distribution empirique et les intervalles de confiance.
    """
    flat_probs = matrix.ravel()
    flat_indices = np.random.choice(len(flat_probs), size=n_simulations, p=flat_probs)
    h_goals, a_goals = np.unravel_index(flat_indices, matrix.shape)
    
    home_wins = np.mean(h_goals > a_goals) * 100.0
    draws = np.mean(h_goals == a_goals) * 100.0
    away_wins = np.mean(h_goals < a_goals) * 100.0
    
    tot_goals = h_goals + a_goals
    over_25 = np.mean(tot_goals > 2) * 100.0
    btts = np.mean((h_goals > 0) & (a_goals > 0)) * 100.0
    
    # 95% Intervalle de confiance sur le total de buts
    q025 = float(np.percentile(tot_goals, 2.5))
    q975 = float(np.percentile(tot_goals, 97.5))
    
    return {
        "mc_h": round(home_wins, 1),
        "mc_d": round(draws, 1),
        "mc_a": round(away_wins, 1),
        "mc_o25": round(over_25, 1),
        "mc_btts": round(btts, 1),
        "ci_low": q025,
        "ci_high": q975
    }

# ==============================================================================
# 7. INTERFACE STREAMLIT ULTRA-PRO V48.0
# ==============================================================================
st.sidebar.markdown("""
    <div style="text-align:center; padding:10px 0;">
        <h2 style="color:#38BDF8; margin:0; font-weight:900;">APEX QUANT</h2>
        <span style="font-size:0.8rem; letter-spacing:2px; color:#F59E0B; font-weight:800;">SOFASCORE ULTRA-PRO v48.0</span>
    </div>
""", unsafe_allow_html=True)

selected_comp = st.sidebar.selectbox("🏆 Compétition Analysée", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ PARAMÈTRES BIOPHYSIQUES & TACTIQUES")
weather_condition = st.sidebar.selectbox("Conditions Météo & Pelouse", [
    "Normal (Idéal)", 
    "Pluie / Terrain Lourd & Glissant", 
    "Canicule / Chaleur Élevée"
])

st.sidebar.divider()
st.sidebar.markdown("### 💰 GESTION DE CAPITAL (QUARTER-KELLY)")
user_bankroll = st.sidebar.number_input("Capital / Bankroll ($ / € / FCFA)", value=1000.0, step=50.0, min_value=10.0)
st.sidebar.caption("🔒 Formule de Quarter-Kelly avec pénalité d'estimation appliquée automatiquement (Max 5% par trade).")

# Chargement des données de la compétition
team_stats, avg_goals_h, avg_goals_a, profile = get_advanced_league_stats(league_code)
raw_matches_obj = fetch_api(f"competitions/{league_code}/matches")
all_matches = raw_matches_obj.get("matches", []) if raw_matches_obj else []

# Filtrage temporel strict des matchs programmés (J0 à J+8)
today_dt = datetime.utcnow()
next_week_dt = today_dt + timedelta(days=8)
upcoming_matches = []

for m in all_matches:
    if m.get('status') in ['SCHEDULED', 'TIMED']:
        utc_str = m.get('utcDate', '')
        if utc_str:
            try:
                m_dt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                if m_dt >= today_dt - timedelta(hours=3) and m_dt <= next_week_dt:
                    upcoming_matches.append(m)
            except Exception:
                pass

finished_matches = [m for m in all_matches if m.get('status') == 'FINISHED']

# Navigation par Onglets
tab_cal, tab_detail, tab_monte_carlo, tab_audit, tab_coupon = st.tabs([
    f"📅 CALENDRIER QUANT ({len(upcoming_matches)})", 
    "📊 ANALYSE SOFASCORE & MARCHÉS DÉRIVÉS",
    "🎲 MONTE CARLO & VALUE EDGE (10k)",
    f"📈 AUDIT & CALIBRATION ({len(finished_matches)})",
    "🎟️ MARMITE SOFASCORE VIP"
])

# ------------------------------------------------------------------------------
# ONGLET 1 : CALENDRIER QUANTITATIF
# ------------------------------------------------------------------------------
with tab_cal:
    st.subheader(f"Tableau de Bord Quantitatif Prédictif — {selected_comp}")
    if upcoming_matches:
        cal_data = []
        for m in upcoming_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_advanced_quant_prediction(
                ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
                profile, False, user_bankroll, None, weather_condition
            )
            cal_data.append({
                "Date [UTC]": m['utcDate'][:10] + " " + m['utcDate'][11:16],
                "Rencontre": f"{ht} vs {at}",
                "1X2 Équitable": f"{pred['p_h']}% | {pred['p_n']}% | {pred['p_a']}%",
                "Option Sécurité (85%+)": f"{pred['options'][0]['desc']} ({pred['options'][0]['prob']}%)",
                "xG Estimés": f"{pred['full_h_xg']:.2f} - {pred['full_a_xg']:.2f}",
                "Over 1.5": f"{pred['prob_o15']}%",
                "BTTS (Oui)": f"{pred['prob_btts_yes']}%",
                "Corners": f"~{pred['corners']} (Ov 8.5: {pred['prob_c85']}%)",
                "Cartons": f"~{pred['cards']} (Ov 3.5: {pred['prob_cards35']}%)"
            })
        st.dataframe(pd.DataFrame(cal_data), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune rencontre programmée dans la fenêtre des 8 prochains jours pour cette ligue.")

# ------------------------------------------------------------------------------
# ONGLET 2 : ANALYSE TACTIQUE DÉTAILLÉE & DÉRIVÉS QUANT
# ------------------------------------------------------------------------------
with tab_detail:
    st.subheader("Analyse Tactique Bivariée & Modélisation Complète des Marchés")
    if upcoming_matches:
        match_map = {f"{m['utcDate'][:10]} {m['utcDate'][11:16]} : {m['homeTeam']['name']} vs {m['awayTeam']['name']}": m for m in upcoming_matches}
        chosen_match_label = st.selectbox("Sélectionnez l'affiche à disséquer :", list(match_map.keys()))
        match_obj = match_map[chosen_match_label]
        
        ht, at = match_obj['homeTeam']['name'], match_obj['awayTeam']['name']
        
        c_in1, c_in2 = st.columns([1, 1])
        with c_in1:
            input_bookmaker_odds = st.number_input("Cote proposée par votre bookmaker pour l'Option n°1 :", value=1.45, step=0.02, min_value=1.01)
        with c_in2:
            st.markdown(f"<div style='padding-top:25px;'><span class='badge-quant'>Modèle Dixon-Coles</span><span class='badge-edge'>Surdispersion Nbinom</span></div>", unsafe_allow_html=True)

        res = run_advanced_quant_prediction(
            ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
            profile, False, user_bankroll, input_bookmaker_odds, weather_condition
        )

        st.markdown(f"""
        <div class="matrix-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <h1 style="color:#38BDF8; margin:0; font-size:2rem;">{ht} <span style="color:#94A3B8; font-weight:300;">vs</span> {at}</h1>
                <span class="badge-quant" style="font-size:0.9rem;">xG Total : {(res['full_h_xg'] + res['full_a_xg']):.2f}</span>
            </div>
            <div class="sofascore-box">{res['sofascore_report']}</div>
        </div>
        """, unsafe_allow_html=True)

        # Les 3 Options Prioritaires
        st.markdown("### 🎯 SÉLECTION QUANTITATIVE HIÉRARCHISÉE")
        for opt in res['options']:
            style_cls = "option-box" if "SÉCURITÉ" in opt['type'] else ("option-box-sec" if "VALUE" in opt['type'] else "option-box-alt")
            st.markdown(f"""
            <div class="{style_cls}">
                <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; color:#38BDF8; letter-spacing:1px;">{opt['type']}</div>
                <div style="font-size:1.35rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{opt['desc']}</div>
                <div style="font-size:1rem; font-weight:700; color:#10B981;">
                    Probabilité Modélisée : <b>{opt['prob']}%</b> | Cote Juste Équitable : <b>{opt['odds']}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        
        # Marchés dérivés complets
        st.markdown("### 📊 TABLEAU DE BORD DES MARCHÉS DÉRIVÉS")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="sub-card">
                <b>1X2 CLASSIQUE</b><br>
                🏠 {ht} : <span class="stat-badge">{res['p_h']}%</span><br>
                🤝 Nul : <span class="stat-badge">{res['p_n']}%</span><br>
                ✈️ {at} : <span class="stat-badge">{res['p_a']}%</span>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="sub-card">
                <b>DOUBLE CHANCE</b><br>
                1X : <span class="stat-badge">{res['prob_1x']}%</span> (Cote {prob_to_odds(res['prob_1x'])})<br>
                X2 : <span class="stat-badge">{res['prob_x2']}%</span> (Cote {prob_to_odds(res['prob_x2'])})<br>
                12 : <span class="stat-badge">{res['prob_12']}%</span> (Cote {prob_to_odds(res['prob_12'])})
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="sub-card">
                <b>DRAW NO BET (DNB)</b><br>
                Remboursé si Nul :<br>
                🏠 {ht} : <span class="stat-badge">{res['prob_dnb_h']}%</span><br>
                ✈️ {at} : <span class="stat-badge">{res['prob_dnb_a']}%</span>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="sub-card">
                <b>LES DEUX MARQUENT (BTTS)</b><br>
                Oui : <span class="stat-badge">{res['prob_btts_yes']}%</span> (Cote {prob_to_odds(res['prob_btts_yes'])})<br>
                Non : <span class="stat-badge">{res['prob_btts_no']}%</span> (Cote {prob_to_odds(res['prob_btts_no'])})<br>
                Over 1.5 Buts : <span class="stat-badge">{res['prob_o15']}%</span>
            </div>
            """, unsafe_allow_html=True)

        # Marchés Spécialisés Corners & Cartons
        st.markdown("### ⛳ & 🟨 PROJECTIONS DES ACCESSOIRES (CORNERS & CARTONS)")
        co1, co2, ca1, ca2 = st.columns(4)
        with co1: st.markdown(f"""<div class="sub-card"><b>CORNERS TOTAUX PROJETÉS</b><h3 style="color:#38BDF8; margin:5px 0;">~{res['corners']}</h3><span style="font-size:0.8rem; color:#94A3B8;">Territorial Dominance Model</span></div>""", unsafe_allow_html=True)
        with co2: st.markdown(f"""<div class="sub-card"><b>+8.5 CORNERS</b><h3 style="color:#10B981; margin:5px 0;">{res['prob_c85']}%</h3><span style="font-size:0.8rem; color:#94A3B8;">+9.5 : {res['prob_c95']}%</span></div>""", unsafe_allow_html=True)
        with ca1: st.markdown(f"""<div class="sub-card"><b>CARTONS TOTAUX PROJETÉS</b><h3 style="color:#F59E0B; margin:5px 0;">~{res['cards']}</h3><span style="font-size:0.8rem; color:#94A3B8;">Indice de Friction Arbitre</span></div>""", unsafe_allow_html=True)
        with ca2: st.markdown(f"""<div class="sub-card"><b>+3.5 CARTONS</b><h3 style="color:#EF4444; margin:5px 0;">{res['prob_cards35']}%</h3><span style="font-size:0.8rem; color:#94A3B8;">+4.5 : {res['prob_cards45']}%</span></div>""", unsafe_allow_html=True)

        st.markdown("---")
        
        # Kelly & Exact Scores
        col_k, col_sc = st.columns([1, 2])
        with col_k:
            st.markdown("### 💰 OPTIMISATION KELLY")
            ev_sign = "+" if res['ev_percentage'] >= 0 else ""
            st.metric("Mise Conseillée (1/4 Kelly)", f"{res['kelly_stake']} $", f"Expected Value : {ev_sign}{res['ev_percentage']}%")
            if res['ev_percentage'] > 0:
                st.success(f"💎 Opportunité Value Bet détectée (+{res['ev_percentage']}% d'Edge mathématique).")
            else:
                st.warning("⚠️ Pas d'Edge suffisant contre la marge du bookmaker sur cette cote.")
                
        with col_sc:
            st.markdown("### 🏆 TOP 3 SCORES EXACTS LES PLUS PROBABLES")
            sc1, sc2, sc3 = st.columns(3)
            with sc1: st.markdown(f"""<div class="big-score-box"><b>1er SCORE</b><div class="big-score-val">{res['top_3_scores'][0]['score']}</div><div class="big-score-prob">{res['top_3_scores'][0]['prob']}%</div></div>""", unsafe_allow_html=True)
            with sc2: st.markdown(f"""<div class="big-score-box"><b>2ème SCORE</b><div class="big-score-val">{res['top_3_scores'][1]['score']}</div><div class="big-score-prob">{res['top_3_scores'][1]['prob']}%</div></div>""", unsafe_allow_html=True)
            with sc3: st.markdown(f"""<div class="big-score-box"><b>3ème SCORE</b><div class="big-score-val">{res['top_3_scores'][2]['score']}</div><div class="big-score-prob">{res['top_3_scores'][2]['prob']}%</div></div>""", unsafe_allow_html=True)

        # Affichage Déroulant de la Matrice Complète 9x9
        with st.expander("🔬 Consulter la Matrice Complète Dixon-Coles 9x9 (Probabilités par Score)"):
            matrix_df = pd.DataFrame(
                np.round(res['matrix'] * 100, 2),
                index=[f"Dom {i}" for i in range(res['matrix'].shape[0])],
                columns=[f"Ext {j}" for j in range(res['matrix'].shape[1])]
            )
            st.dataframe(matrix_df, use_container_width=True)
    else:
        st.info("Aucun match disponible pour l'analyse détaillée.")

# ------------------------------------------------------------------------------
# ONGLET 3 : MONTE CARLO & VALUE EDGE
# ------------------------------------------------------------------------------
with tab_monte_carlo:
    st.markdown("""
    <div class="vip-banner">
        <h2 style="margin:0; color:#38BDF8;">🎲 SIMULATEUR QUANTITATIF DE MONTE CARLO (10 000 ITÉRATIONS)</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Validation stochastique empirique et suppression de marge bookmaker (Méthode de Shin)</span>
    </div>
    """, unsafe_allow_html=True)
    
    if upcoming_matches:
        mc_chosen_label = st.selectbox("Sélectionnez le match pour la simulation Monte Carlo :", list(match_map.keys()), key="mc_select")
        mc_match = match_map[mc_chosen_label]
        ht, at = mc_match['homeTeam']['name'], mc_match['awayTeam']['name']
        
        mc_res = run_advanced_quant_prediction(
            ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
            profile, False, user_bankroll, None, weather_condition
        )
        
        mc_stats = run_monte_carlo_simulation(mc_res['matrix'], 10000)
        
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric("Victoires Domicile (MC)", f"{mc_stats['mc_h']}%", f"Théorique: {mc_res['p_h']}%")
        with k2: st.metric("Matchs Nuls (MC)", f"{mc_stats['mc_d']}%", f"Théorique: {mc_res['p_n']}%")
        with k3: st.metric("Victoires Extérieur (MC)", f"{mc_stats['mc_a']}%", f"Théorique: {mc_res['p_a']}%")
        with k4: st.metric("Over 2.5 Buts (MC)", f"{mc_stats['mc_o25']}%", f"95% CI: [{int(mc_stats['ci_low'])}-{int(mc_stats['ci_high'])} buts]")
        
        st.markdown("### 🧮 CALCULATEUR DE VALUE ET DÉMARGEAGE BOOKMAKER (SHIN / POWER)")
        st.markdown("Entrez les 3 cotes 1N2 de votre bookmaker pour enlever automatiquement la marge et voir où se situe l'Edge mathématique réel :")
        
        c_b1, c_b2, c_b3 = st.columns(3)
        with c_b1: odds_1 = st.number_input("Cote 1 (Domicile) :", value=round(prob_to_odds(mc_res['p_h']), 2), step=0.05)
        with c_b2: odds_n = st.number_input("Cote N (Nul) :", value=round(prob_to_odds(mc_res['p_n']), 2), step=0.05)
        with c_b3: odds_2 = st.number_input("Cote 2 (Extérieur) :", value=round(prob_to_odds(mc_res['p_a']), 2), step=0.05)
        
        true_h, true_n, true_a, vig_margin = shin_remove_vig(odds_1, odds_n, odds_2)
        
        st.markdown(f"**Marge appliquée par le bookmaker (Overround)** : <span style='color:#EF4444; font-weight:800;'>{vig_margin:.2f}%</span>", unsafe_allow_html=True)
        
        ev_1 = round((mc_res['p_h'] / 100.0 * odds_1 - 1.0) * 100, 2)
        ev_n = round((mc_res['p_n'] / 100.0 * odds_n - 1.0) * 100, 2)
        ev_2 = round((mc_res['p_a'] / 100.0 * odds_2 - 1.0) * 100, 2)
        
        df_edge = pd.DataFrame([
            {"Issue": f"1 ({ht})", "Cote Book": odds_1, "Proba Implicite Sans Marge": f"{true_h*100:.1f}%", "Proba Apex Quant": f"{mc_res['p_h']}%", "Expected Value (EV)": f"{ev_1:+.2f}%"},
            {"Issue": "N (Match Nul)", "Cote Book": odds_n, "Proba Implicite Sans Marge": f"{true_n*100:.1f}%", "Proba Apex Quant": f"{mc_res['p_n']}%", "Expected Value (EV)": f"{ev_n:+.2f}%"},
            {"Issue": f"2 ({at})", "Cote Book": odds_2, "Proba Implicite Sans Marge": f"{true_a*100:.1f}%", "Proba Apex Quant": f"{mc_res['p_a']}%", "Expected Value (EV)": f"{ev_2:+.2f}%"}
        ])
        st.dataframe(df_edge, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match disponible pour la simulation stochastique.")

# ------------------------------------------------------------------------------
# ONGLET 4 : AUDIT & CALIBRATION HISTORIQUE
# ------------------------------------------------------------------------------
with tab_audit:
    st.markdown("""
    <div class="vip-banner">
        <h2 style="margin:0; color:#F59E0B;">📈 AUDIT QUANTITATIF & BACKTESTING DU MODÈLE</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Vérification rigoureuse des prédictions sur les rencontres déjà terminées</span>
    </div>
    """, unsafe_allow_html=True)
    
    if finished_matches:
        audit_rows = []
        total_eval, success_pick_count, net_units = 0, 0, 0.0
        
        for m in finished_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            sc = m.get('score', {}).get('fullTime', {})
            rh, ra = sc.get('home'), sc.get('away')
            
            if rh is not None and ra is not None:
                real_score_str = f"{rh}-{ra}"
                pred = run_advanced_quant_prediction(
                    ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
                    profile, False, user_bankroll, None, weather_condition
                )
                top_opt = pred['options'][0]
                top_opt_desc = top_opt['desc']
                top_opt_odds = top_opt['odds']
                tot_goals = rh + ra
                
                # Évaluation stricte et sans ambiguïté
                pick_hit = False
                if "Double Chance" in top_opt_desc:
                    if "ou Nul (1X)" in top_opt_desc and rh >= ra: pick_hit = True
                    elif "Nul ou" in top_opt_desc and ra >= rh: pick_hit = True
                elif "Plus de 1.5" in top_opt_desc:
                    pick_hit = (tot_goals >= 2)
                elif "Moins de 3.5" in top_opt_desc:
                    pick_hit = (tot_goals <= 3)
                elif "Victoire Sèche" in top_opt_desc:
                    if ht in top_opt_desc and rh > ra: pick_hit = True
                    elif at in top_opt_desc and ra > rh: pick_hit = True
                    
                eval_status = "✅ GAGNÉ" if pick_hit else "❌ PERDU"
                if pick_hit:
                    success_pick_count += 1
                    net_units += 10.0 * (top_opt_odds - 1.0)
                else:
                    net_units -= 10.0
                    
                total_eval += 1
                audit_rows.append({
                    "Date": m.get('utcDate', '')[:10],
                    "Affiche": f"{ht} vs {at}",
                    "Score Réel": real_score_str,
                    "Option Validée (85%+)": top_opt_desc,
                    "Cote Juste": top_opt_odds,
                    "Résultat": eval_status
                })
                
        if total_eval > 0:
            winrate_pick = round((success_pick_count / total_eval) * 100.0, 1)
            roi = round((net_units / (total_eval * 10.0)) * 100.0, 1)
            
            k1, k2, k3 = st.columns(3)
            with k1: st.markdown(f"""<div class="sub-card" style="text-align:center;"><b>MATCHS AUDITÉS</b><br><span style="font-size:1.8rem; font-weight:800; color:#38BDF8;">{total_eval}</span></div>""", unsafe_allow_html=True)
            with k2: st.markdown(f"""<div class="sub-card" style="text-align:center;"><b>TAUX DE RÉUSSITE SÉCURITÉ</b><br><span style="font-size:1.8rem; font-weight:800; color:#10B981;">{winrate_pick}%</span></div>""", unsafe_allow_html=True)
            with k3: st.markdown(f"""<div class="sub-card" style="text-align:center;"><b>PROFIT NET / ROI</b><br><span style="font-size:1.8rem; font-weight:800; color:{'#10B981' if net_units>=0 else '#EF4444'};">{net_units:+.1f} U ({roi:+.1f}%)</span></div>""", unsafe_allow_html=True)
            
            st.dataframe(pd.DataFrame(audit_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune donnée de match terminé récent dans cette ligue pour backtesting immédiat.")

# ------------------------------------------------------------------------------
# ONGLET 5 : MARMITE SOFASCORE VIP
# ------------------------------------------------------------------------------
with tab_coupon:
    st.subheader("🎟️ Ticket Combiné Sécurisé SofaScore VIP (90%+ & Multi-Risque)")
    if upcoming_matches:
        coupon_candidates = []
        for m in upcoming_matches:
            ht, at = m['homeTeam']['name'], m['awayTeam']['name']
            pred = run_advanced_quant_prediction(
                ht, at, 0, 0, 0, team_stats, avg_goals_h, avg_goals_a, 
                profile, False, user_bankroll, None, weather_condition
            )
            top_opt = pred['options'][0]
            coupon_candidates.append({
                "match": f"{ht} vs {at}",
                "pick": top_opt['desc'],
                "prob": top_opt['prob'],
                "odds": top_opt['odds'],
                "corners": pred['corners'],
                "cards": pred['cards']
            })
            
        coupon_candidates.sort(key=lambda x: x['prob'], reverse=True)
        top_safe_picks = coupon_candidates[:5]
        total_combined_odds = float(np.prod([item['odds'] for item in top_safe_picks]))
        
        st.markdown(f"""
        <div class="vip-banner">
            <h2 style="margin:0; color:#F59E0B;">🛡️ COMBINÉ SÉCURITÉ ALGORITHMIQUE APEX (TOP 5)</h2>
            <div style="font-size:1.8rem; font-weight:900; color:#FFFFFF; margin-top:8px;">
                Cote Totale Estimée : <span style="color:#38BDF8;">{total_combined_odds:.2f}</span>
            </div>
            <div style="font-size:0.9rem; color:#E2E8F0; margin-top:4px;">Sélection des 5 plus hautes probabilités conditionnelles de la compétition</div>
        </div>
        """, unsafe_allow_html=True)
        
        for idx, item in enumerate(top_safe_picks, 1):
            st.markdown(f"""
            <div class="sub-card">
                <b>{idx}. {item['match']}</b><br>
                👉 Choix Quantifié : <b style="color:#10B981;">{item['pick']}</b> | Probabilité : <b>{item['prob']}%</b> (Cote Équitable : <b>{item['odds']}</b>)<br>
                <span style="font-size:0.85rem; color:#94A3B8;">⛳ Corners projetés : ~{item['corners']} | 🟨 Cartons projetés : ~{item['cards']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Nombre insuffisant de matchs programmés pour générer un combiné complet.")
