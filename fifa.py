import streamlit as st
import requests
import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson, nbinom, skellam
import pandas as pd
from datetime import datetime, timedelta
import math

# ==============================================================================
# 1. CONFIGURATION & STYLE ÉPURÉ
# ==============================================================================
st.set_page_config(
    page_title="Apex Quant — Moteur Mathématique Football",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700;800&family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .stApp { background-color: #060913; color: #F1F5F9; }
    .panel {
        background: #0D1322; border: 1px solid #1E293B;
        border-radius: 10px; padding: 14px; margin-bottom: 10px;
    }
    .panel-title {
        font-size: 0.78rem; font-weight: 800; text-transform: uppercase;
        letter-spacing: 0.8px; color: #94A3B8; margin-bottom: 8px;
    }
    .val { font-family: 'JetBrains Mono', monospace; font-weight: 800; color: #38BDF8; font-size: 1.05rem; }
    .val-green { font-family: 'JetBrains Mono', monospace; font-weight: 800; color: #10B981; font-size: 1.05rem; }
    .val-amber { font-family: 'JetBrains Mono', monospace; font-weight: 800; color: #F59E0B; font-size: 1.05rem; }
    .top-pick-bar {
        background: rgba(16, 185, 129, 0.10); border-left: 4px solid #10B981;
        padding: 10px 14px; border-radius: 0 8px 8px 0; margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. INFRASTRUCTURE API & PARAMÈTRES LIGUES
# ==============================================================================
API_KEY = st.secrets.get("FOOTBALL_API_KEY", "1e9518e7585349f9abe6d5a29ddb83b1")
BASE_URL = "https://api.football-data.org/v4/"

COMPETITIONS = {
    "Premier League (Angleterre)": "PL",
    "La Liga (Espagne)": "PD",
    "Serie A (Italie)": "SA",
    "Bundesliga (Allemagne)": "BL1",
    "Ligue 1 (France)": "FL1",
    "Ligue des Champions (UEFA)": "CL",
    "Europa League (UEFA)": "EL",
    "Championship (Angleterre)": "ELC"
}

LEAGUE_PRIORS = {
    "CL":  {"card_base": 4.1, "corner_base": 9.9,  "dispersion": 9.5},
    "PL":  {"card_base": 3.9, "corner_base": 10.4, "dispersion": 10.0},
    "PD":  {"card_base": 4.8, "corner_base": 9.4,  "dispersion": 9.2},
    "FL1": {"card_base": 3.8, "corner_base": 9.3,  "dispersion": 9.8},
    "SA":  {"card_base": 4.5, "corner_base": 9.8,  "dispersion": 9.4},
    "BL1": {"card_base": 3.9, "corner_base": 10.1, "dispersion": 11.2},
    "EL":  {"card_base": 4.2, "corner_base": 9.7,  "dispersion": 9.6},
    "ELC": {"card_base": 3.8, "corner_base": 10.2, "dispersion": 10.2}
}

@st.cache_data(ttl=60)
def fetch_live(endpoint):
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=6)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

@st.cache_data(ttl=1800)
def fetch_static(endpoint):
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", headers={"X-Auth-Token": API_KEY}, timeout=8)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None

# ==============================================================================
# 3. MODÈLE DE DIXON-COLES (1997) PAR MAXIMUM DE VRAISEMBLANCE (MLE)
# ==============================================================================

def dc_tau_vec(x, y, lh, la, rho):
    """Fonction de corrélation bivariée de Dixon-Coles vectorisée."""
    tau = np.ones_like(lh, dtype=float)
    m00 = (x == 0) & (y == 0)
    m01 = (x == 0) & (y == 1)
    m10 = (x == 1) & (y == 0)
    m11 = (x == 1) & (y == 1)
    tau[m00] = 1.0 - lh[m00] * la[m00] * rho
    tau[m01] = 1.0 + lh[m01] * rho
    tau[m10] = 1.0 + la[m10] * rho
    tau[m11] = 1.0 - rho
    return np.maximum(tau, 1e-4)

def dc_tau_scalar(x, y, lh, la, rho):
    if x == 0 and y == 0: return max(1e-4, 1.0 - lh * la * rho)
    if x == 0 and y == 1: return max(1e-4, 1.0 + lh * rho)
    if x == 1 and y == 0: return max(1e-4, 1.0 + la * rho)
    if x == 1 and y == 1: return max(1e-4, 1.0 - rho)
    return 1.0

@st.cache_data(ttl=1800)
def fit_dixon_coles_mle(league_code, xi=0.0045):
    """
    Ajuste par Maximum de Vraisemblance Régularisé (L-BFGS-B) les paramètres latents :
    - alpha_i : force offensive intrinsèque de l'équipe i
    - beta_i  : vulnérabilité défensive intrinsèque de l'équipe i
    - gamma   : avantage statistique du terrain à domicile
    - rho     : paramètre de dépendance des scores faibles (0-0, 1-0, 0-1, 1-1)
    Pondération exponentielle temporelle : w_k = exp(-xi * jours_écoulés).
    """
    raw = fetch_static(f"competitions/{league_code}/matches")
    matches = raw.get("matches", []) if raw else []
    
    finished = []
    teams_set = set()
    ref_date = datetime.utcnow()
    
    for m in matches:
        if m.get("status") == "FINISHED":
            sc = m.get("score", {}).get("fullTime", {})
            sh, sa = sc.get("home"), sc.get("away")
            if sh is not None and sa is not None:
                ht, at = m["homeTeam"]["name"], m["awayTeam"]["name"]
                teams_set.add(ht)
                teams_set.add(at)
                try:
                    dt = datetime.strptime(m["utcDate"][:19], "%Y-%m-%dT%H:%M:%S")
                    days_ago = max(0.0, (ref_date - dt).total_seconds() / 86400.0)
                except Exception:
                    days_ago = 30.0
                finished.append((ht, at, int(sh), int(sa), days_ago))

    teams = sorted(list(teams_set))
    n_teams = len(teams)
    if n_teams < 2 or len(finished) < 10:
        return {"teams": {}, "gamma": 0.26, "rho": -0.11, "base_rate": 0.30, "n_matches": len(finished)}

    idx_map = {t: i for i, t in enumerate(teams)}
    h_idx = np.array([idx_map[f[0]] for f in finished], dtype=int)
    a_idx = np.array([idx_map[f[1]] for f in finished], dtype=int)
    x_obs = np.array([f[2] for f in finished], dtype=int)
    y_obs = np.array([f[3] for f in finished], dtype=int)
    days = np.array([f[4] for f in finished], dtype=float)
    weights = np.exp(-xi * days)

    # Vecteur paramètres : [alpha_0..n-1, beta_0..n-1, gamma, rho]
    init_params = np.zeros(2 * n_teams + 2)
    init_params[2 * n_teams] = 0.25      # gamma initial
    init_params[2 * n_teams + 1] = -0.11 # rho initial

    bounds = [(-1.8, 1.8)] * (2 * n_teams) + [(0.0, 0.65), (-0.25, 0.05)]
    l2_reg = 0.08  # Régularisation de Ridge bayésienne contre le sur-apprentissage

    def neg_log_likelihood(params):
        alpha = params[:n_teams]
        beta = params[n_teams:2 * n_teams]
        gamma = params[2 * n_teams]
        rho = params[2 * n_teams + 1]

        # Contrainte souple d'identifiabilité : moyenne(alpha) = 0
        ident_penalty = 5.0 * (np.mean(alpha) ** 2)

        lh = np.exp(alpha[h_idx] + beta[a_idx] + gamma)
        la = np.exp(alpha[a_idx] + beta[h_idx])

        tau = dc_tau_vec(x_obs, y_obs, lh, la, rho)
        ll = weights * (
            np.log(tau)
            + x_obs * np.log(lh) - lh
            + y_obs * np.log(la) - la
        )
        reg = l2_reg * (np.sum(alpha ** 2) + np.sum(beta ** 2))
        return -np.sum(ll) + reg + ident_penalty

    res = minimize(neg_log_likelihood, init_params, method="L-BFGS-B", bounds=bounds, options={"maxiter": 250})
    opt = res.x
    alpha_opt = opt[:n_teams] - np.mean(opt[:n_teams])
    beta_opt = opt[n_teams:2 * n_teams] + np.mean(opt[:n_teams])
    gamma_opt = float(opt[2 * n_teams])
    rho_opt = float(opt[2 * n_teams + 1])

    team_params = {}
    for t, i in idx_map.items():
        # Calcul de la forme récente pondérée (5 derniers matchs)
        t_matches = [f for f in finished if f[0] == t or f[1] == t]
        t_matches.sort(key=lambda z: z[4])
        last5 = t_matches[:5]
        pts_rec = sum(3 if (m[0]==t and m[2]>m[3]) or (m[1]==t and m[3]>m[2]) else (1 if m[2]==m[3] else 0) for m in last5)
        team_params[t] = {
            "alpha": float(alpha_opt[i]),
            "beta": float(beta_opt[i]),
            "att_index": round(math.exp(float(alpha_opt[i])), 3),
            "def_index": round(math.exp(float(beta_opt[i])), 3),
            "pts_last5": pts_rec,
            "n_last5": len(last5)
        }

    return {
        "teams": team_params,
        "gamma": gamma_opt,
        "rho": rho_opt,
        "n_matches": len(finished)
    }

# ==============================================================================
# 4. MOTEUR DE CALCUL ANALYTIQUE COMPLET (MATRICE BIVARIÉE, SKELLAM, HT/FT)
# ==============================================================================

def prob_to_odds(p):
    if p <= 0.05: return 99.00
    return round(min(99.00, 100.0 / p), 2)

def compute_match_mathematics(
    h_name, a_name, model_fit, league_code,
    is_live=False, live_h=0, live_a=0, elapsed_min=0
):
    priors = LEAGUE_PRIORS.get(league_code, {"card_base": 4.0, "corner_base": 9.8, "dispersion": 10.0})
    teams = model_fit.get("teams", {})
    gamma = model_fit.get("gamma", 0.25)
    rho = model_fit.get("rho", -0.11)
    dispersion = priors["dispersion"]

    h_p = teams.get(h_name, {"alpha": 0.0, "beta": 0.0, "att_index": 1.0, "def_index": 1.0, "pts_last5": 7, "n_last5": 5})
    a_p = teams.get(a_name, {"alpha": 0.0, "beta": 0.0, "att_index": 1.0, "def_index": 1.0, "pts_last5": 7, "n_last5": 5})

    # Intensités attendues (Lambda Domicile & Lambda Extérieur)
    lambda_h = float(np.clip(math.exp(h_p["alpha"] + a_p["beta"] + gamma), 0.25, 3.80))
    lambda_a = float(np.clip(math.exp(a_p["alpha"] + h_p["beta"]), 0.20, 3.40))

    if is_live and elapsed_min > 0:
        rem_frac = max(0.02, (90.0 - min(89.0, float(elapsed_min))) / 90.0)
        # Exposant empirique de fin de match (0.87) : intensité légèrement accrue dans le dernier quart d'heure
        time_scale = rem_frac ** 0.87
        rem_h = lambda_h * time_scale
        rem_a = lambda_a * time_scale
    else:
        live_h, live_a = 0, 0
        rem_h, rem_a = lambda_h, lambda_a

    # 1. Matrice Bivariée Exacte (Binomiale Négative + Correction Dixon-Coles)
    max_g = 10
    matrix = np.zeros((max_g, max_g))
    r_disp = dispersion
    p_nb_h = r_disp / (r_disp + rem_h) if rem_h > 0 else 1.0
    p_nb_a = r_disp / (r_disp + rem_a) if rem_a > 0 else 1.0

    for dh in range(max_g - live_h):
        ph_k = nbinom.pmf(dh, r_disp, p_nb_h) if rem_h > 0 else (1.0 if dh == 0 else 0.0)
        for da in range(max_g - live_a):
            pa_k = nbinom.pmf(da, r_disp, p_nb_a) if rem_a > 0 else (1.0 if da == 0 else 0.0)
            tau = dc_tau_scalar(dh, da, rem_h, rem_a, rho)
            matrix[live_h + dh, live_a + da] = ph_k * pa_k * tau

    tot_p = np.sum(matrix)
    if tot_p > 0:
        matrix /= tot_p

    # 2. Probabilités 1N2, Double Chance & DNB
    p_1 = round(float(np.sum(np.tril(matrix, -1))) * 100.0, 1)
    p_x = round(float(np.sum(np.diag(matrix))) * 100.0, 1)
    p_2 = round(float(np.sum(np.triu(matrix, 1))) * 100.0, 1)

    p_1x = round(p_1 + p_x, 1)
    p_x2 = round(p_2 + p_x, 1)
    p_12 = round(p_1 + p_2, 1)

    denom_dnb = max(0.01, p_1 + p_2)
    p_dnb1 = round((p_1 / denom_dnb) * 100.0, 1)
    p_dnb2 = round((p_2 / denom_dnb) * 100.0, 1)

    # 3. Loi de Skellam Analytique pour Handicaps Asiatiques (Différence de buts D = X - Y)
    # P(X - Y >= 2) -> AH -1.5 Domicile | P(X - Y >= -1) -> AH +1.5 Domicile
    p_ah_h_m15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if (i - j) >= 2])) * 100.0, 1)
    p_ah_a_m15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if (j - i) >= 2])) * 100.0, 1)
    p_ah_h_p15 = round(100.0 - p_ah_a_m15, 1)
    p_ah_a_p15 = round(100.0 - p_ah_h_m15, 1)
    # Skellam théorique pur (écart attendu)
    skellam_mean_diff = round(rem_h - rem_a + (live_h - live_a), 2)

    # 4. Totaux Buts, BTTS, Buts par Équipe & Combos
    p_o15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) >= 2])) * 100.0, 1)
    p_u15 = round(100.0 - p_o15, 1)
    p_o25 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) >= 3])) * 100.0, 1)
    p_u25 = round(100.0 - p_o25, 1)
    p_o35 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if (i + j) >= 4])) * 100.0, 1)
    p_u35 = round(100.0 - p_o35, 1)

    p_btts_y = round(float(np.sum(matrix[1:, 1:])) * 100.0, 1)
    p_btts_n = round(100.0 - p_btts_y, 1)

    p_h_o05 = round(float(np.sum(matrix[1:, :])) * 100.0, 1)
    p_h_o15 = round(float(np.sum(matrix[2:, :])) * 100.0, 1)
    p_a_o05 = round(float(np.sum(matrix[:, 1:])) * 100.0, 1)
    p_a_o15 = round(float(np.sum(matrix[:, 2:])) * 100.0, 1)

    p_1x_o15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if i >= j and (i + j) >= 2])) * 100.0, 1)
    p_x2_o15 = round(float(np.sum([matrix[i, j] for i in range(max_g) for j in range(max_g) if j >= i and (i + j) >= 2])) * 100.0, 1)

    # 5. Convolution Analytique 1ère Mi-Temps & HT/FT (43.5% des buts en 1MT)
    theta_ht = 0.435
    lh1, la1 = lambda_h * theta_ht, lambda_a * theta_ht
    lh2, la2 = lambda_h * (1.0 - theta_ht), lambda_a * (1.0 - theta_ht)
    m1 = np.zeros((6, 6))
    m2 = np.zeros((6, 6))
    for x in range(6):
        for y in range(6):
            m1[x, y] = poisson.pmf(x, lh1) * poisson.pmf(y, la1) * dc_tau_scalar(x, y, lh1, la1, rho * 1.2)
            m2[x, y] = poisson.pmf(x, lh2) * poisson.pmf(y, la2)
    m1 /= max(1e-9, np.sum(m1))
    m2 /= max(1e-9, np.sum(m2))

    ht_1 = round(float(np.sum(np.tril(m1, -1))) * 100.0, 1)
    ht_x = round(float(np.sum(np.diag(m1))) * 100.0, 1)
    ht_2 = round(float(np.sum(np.triu(m1, 1))) * 100.0, 1)
    ht_o05 = round(float(1.0 - m1[0, 0]) * 100.0, 1)
    ht_o15 = round(float(1.0 - (m1[0, 0] + m1[1, 0] + m1[0, 1])) * 100.0, 1)

    ht_ft = {k: 0.0 for k in ['1/1', '1/X', '1/2', 'X/1', 'X/X', 'X/2', '2/1', '2/X', '2/2']}
    for x1 in range(6):
        for y1 in range(6):
            p1_val = m1[x1, y1]
            r1 = '1' if x1 > y1 else ('X' if x1 == y1 else '2')
            for x2 in range(6):
                for y2 in range(6):
                    tx, ty = x1 + x2, y1 + y2
                    r2 = '1' if tx > ty else ('X' if tx == ty else '2')
                    ht_ft[f'{r1}/{r2}'] += p1_val * m2[x2, y2]
    ht_ft_pct = {k: round(v * 100.0, 1) for k, v in ht_ft.items()}

    # 6. Accessoires : Corners & Cartons Jaunes (Loi de Poisson pondérée par domination)
    tot_xg = lambda_h + lambda_a
    dom_h = (lambda_h ** 1.15) / max(0.05, (lambda_h ** 1.15 + lambda_a ** 1.15))
    pace = (tot_xg / 2.65) ** 0.30
    exp_c_h = priors["corner_base"] * 0.54 * (dom_h ** 0.50) * pace
    exp_c_a = priors["corner_base"] * 0.46 * ((1.0 - dom_h) ** 0.50) * pace
    tot_corners = round(float(np.clip(exp_c_h + exp_c_a, 6.0, 14.0)), 1)
    p_c75 = round((1.0 - poisson.cdf(7, tot_corners)) * 100.0, 1)
    p_c85 = round((1.0 - poisson.cdf(8, tot_corners)) * 100.0, 1)
    p_c95 = round((1.0 - poisson.cdf(9, tot_corners)) * 100.0, 1)

    closeness = 1.22 if abs(lambda_h - lambda_a) < 0.35 else (1.08 if abs(lambda_h - lambda_a) < 0.75 else 0.94)
    tot_cards = round(float(np.clip(priors["card_base"] * closeness, 2.5, 7.2)), 1)
    p_y25 = round((1.0 - poisson.cdf(2, tot_cards)) * 100.0, 1)
    p_y35 = round((1.0 - poisson.cdf(3, tot_cards)) * 100.0, 1)
    p_y45 = round((1.0 - poisson.cdf(4, tot_cards)) * 100.0, 1)

    # 7. Top 5 Scores Exacts
    flat_idx = np.argsort(matrix.ravel())[::-1]
    top_scores = []
    for idx in flat_idx[:5]:
        gh, ga = np.unravel_index(idx, matrix.shape)
        pr = round(float(matrix[gh, ga]) * 100.0, 1)
        top_scores.append({"score": f"{gh}-{ga}", "prob": pr, "odds": prob_to_odds(pr)})

    # 8. Synthèse Hiérarchisée de Toutes les Propositions du Match
    all_props = [
        {"code": "1",      "family": "1N2",           "label": f"Victoire {h_name} (1)",                "prob": p_1},
        {"code": "X",      "family": "1N2",           "label": "Match Nul (X)",                         "prob": p_x},
        {"code": "2",      "family": "1N2",           "label": f"Victoire {a_name} (2)",                "prob": p_2},
        {"code": "1X",     "family": "Double Chance", "label": f"Double Chance : {h_name} ou Nul (1X)", "prob": p_1x},
        {"code": "X2",     "family": "Double Chance", "label": f"Double Chance : Nul ou {a_name} (X2)", "prob": p_x2},
        {"code": "DNB1",   "family": "DNB",           "label": f"{h_name} Remboursé si Nul (DNB 1)",    "prob": p_dnb1},
        {"code": "DNB2",   "family": "DNB",           "label": f"{a_name} Remboursé si Nul (DNB 2)",    "prob": p_dnb2},
        {"code": "AH_H_M15","family": "Handicap",     "label": f"Handicap {h_name} (-1.5)",             "prob": p_ah_h_m15},
        {"code": "AH_A_M15","family": "Handicap",     "label": f"Handicap {a_name} (-1.5)",             "prob": p_ah_a_m15},
        {"code": "O15",    "family": "Buts",          "label": "Plus de 1.5 Buts",                      "prob": p_o15},
        {"code": "O25",    "family": "Buts",          "label": "Plus de 2.5 Buts",                      "prob": p_o25},
        {"code": "U25",    "family": "Buts",          "label": "Moins de 2.5 Buts",                     "prob": p_u25},
        {"code": "U35",    "family": "Buts",          "label": "Moins de 3.5 Buts",                     "prob": p_u35},
        {"code": "BTTS_Y", "family": "BTTS",          "label": "Les Deux Équipes Marquent (Oui)",       "prob": p_btts_y},
        {"code": "BTTS_N", "family": "BTTS",          "label": "Les Deux Équipes Marquent (Non)",       "prob": p_btts_n},
        {"code": "1X_O15", "family": "Combo",         "label": f"{h_name} ou Nul & +1.5 Buts",          "prob": p_1x_o15},
        {"code": "X2_O15", "family": "Combo",         "label": f"Nul ou {a_name} & +1.5 Buts",          "prob": p_x2_o15},
        {"code": "HT_O05", "family": "Mi-Temps",      "label": "Plus de 0.5 But en 1ère Mi-Temps",      "prob": ht_o05},
        {"code": "C85",    "family": "Corners",       "label": "Plus de 8.5 Corners",                   "prob": p_c85},
        {"code": "Y35",    "family": "Cartons",       "label": "Plus de 3.5 Cartons Jaunes",            "prob": p_y35},
    ]
    for item in all_props:
        item["odds"] = prob_to_odds(item["prob"])

    # Prédiction de référence (pour l'audit strict sur résultats réels)
    audit_pool = [x for x in all_props if x["code"] in ["1", "2", "1X", "X2", "DNB1", "DNB2", "O15", "O25", "U25", "U35", "BTTS_Y", "1X_O15", "X2_O15"]]
    # On score l'équilibre entre haute probabilité et cote non triviale
    best_pick = max(audit_pool, key=lambda x: x["prob"] * (1.12 if 58.0 <= x["prob"] <= 78.0 else 0.96))

    return {
        "lambda_h": round(lambda_h, 2), "lambda_a": round(lambda_a, 2),
        "rem_h": round(rem_h, 2), "rem_a": round(rem_a, 2),
        "skellam_diff": skellam_mean_diff,
        "h_att": h_p["att_index"], "h_def": h_p["def_index"],
        "a_att": a_p["att_index"], "a_def": a_p["def_index"],
        "p_1": p_1, "p_x": p_x, "p_2": p_2,
        "p_1x": p_1x, "p_x2": p_x2, "p_12": p_12,
        "p_dnb1": p_dnb1, "p_dnb2": p_dnb2,
        "p_ah_h_m15": p_ah_h_m15, "p_ah_a_m15": p_ah_a_m15,
        "p_ah_h_p15": p_ah_h_p15, "p_ah_a_p15": p_ah_a_p15,
        "p_o15": p_o15, "p_u15": p_u15, "p_o25": p_o25, "p_u25": p_u25, "p_o35": p_o35, "p_u35": p_u35,
        "p_btts_y": p_btts_y, "p_btts_n": p_btts_n,
        "p_h_o05": p_h_o05, "p_h_o15": p_h_o15, "p_a_o05": p_a_o05, "p_a_o15": p_a_o15,
        "p_1x_o15": p_1x_o15, "p_x2_o15": p_x2_o15,
        "ht_1": ht_1, "ht_x": ht_x, "ht_2": ht_2, "ht_o05": ht_o05, "ht_o15": ht_o15,
        "ht_ft": ht_ft_pct,
        "tot_corners": tot_corners, "exp_c_h": round(exp_c_h, 1), "exp_c_a": round(exp_c_a, 1),
        "p_c75": p_c75, "p_c85": p_c85, "p_c95": p_c95,
        "tot_cards": tot_cards, "p_y25": p_y25, "p_y35": p_y35, "p_y45": p_y45,
        "top_scores": top_scores,
        "all_props": all_props,
        "best_pick": best_pick
    }

def check_pick_validated(code, rh, ra):
    tot = rh + ra
    if code == "1": return rh > ra
    if code == "2": return ra > rh
    if code == "1X": return rh >= ra
    if code == "X2": return ra >= rh
    if code == "DNB1": return rh >= ra
    if code == "DNB2": return ra >= rh
    if code == "O15": return tot >= 2
    if code == "O25": return tot >= 3
    if code == "U25": return tot <= 2
    if code == "U35": return tot <= 3
    if code == "BTTS_Y": return (rh >= 1) and (ra >= 1)
    if code == "1X_O15": return (rh >= ra) and (tot >= 2)
    if code == "X2_O15": return (ra >= rh) and (tot >= 2)
    return False

# ==============================================================================
# 5. INTERFACE UTILISATEUR : LISTE CLIQUABLE MATCH PAR MATCH + LIVE + AUDIT
# ==============================================================================
st.sidebar.title("📐 APEX QUANT MLE")
selected_comp = st.sidebar.selectbox("Compétition", list(COMPETITIONS.keys()))
league_code = COMPETITIONS[selected_comp]

xi_decay = st.sidebar.select_slider(
    "Mémoire temporelle du modèle (ξ)",
    options=[0.002, 0.0045, 0.008, 0.012],
    value=0.0045,
    help="Plus ξ est élevé, plus les matchs récents pèsent lourd par rapport au début de saison."
)

with st.spinner("Optimisation Maximum de Vraisemblance (Dixon-Coles MLE)..."):
    model_fit = fit_dixon_coles_mle(league_code, xi_decay)

st.sidebar.caption(f"Modèle calibré sur {model_fit['n_matches']} matchs | γ={model_fit['gamma']:.3f} | ρ={model_fit['rho']:.3f}")

raw_matches_obj = fetch_live(f"competitions/{league_code}/matches")
all_matches = raw_matches_obj.get("matches", []) if raw_matches_obj else []

now_utc = datetime.utcnow()
horizon_utc = now_utc + timedelta(days=10)

live_matches = [m for m in all_matches if m.get("status") in ["IN_PLAY", "PAUSED", "HALFTIME"]]
upcoming_matches = []
for m in all_matches:
    if m.get("status") in ["SCHEDULED", "TIMED"]:
        utc_str = m.get("utcDate", "")
        if utc_str:
            try:
                mdt = datetime.strptime(utc_str[:19], "%Y-%m-%dT%H:%M:%S")
                if now_utc - timedelta(hours=2) <= mdt <= horizon_utc:
                    upcoming_matches.append(m)
            except Exception:
                pass

finished_matches = sorted(
    [m for m in all_matches if m.get("status") == "FINISHED"],
    key=lambda x: x.get("utcDate", ""), reverse=True
)

tab_upcoming, tab_live, tab_audit = st.tabs([
    f"📅 MATCHS À VENIR ({len(upcoming_matches)}) — CLIQUER POUR ANALYSER",
    f"🔴 LIVE EN COURS ({len(live_matches)})",
    f"✅ AUDIT CHAMPIONNAT ({len(finished_matches)})"
])

# ------------------------------------------------------------------------------
# ONGLET 1 : LISTE DES MATCHS À VENIR (CLIQUER SUR CHAQUE MATCH POUR OUVRIR)
# ------------------------------------------------------------------------------
with tab_upcoming:
    st.subheader(f"{selected_comp} — Prochains Matchs (Clique sur un match pour ouvrir toutes ses prédictions)")
    if not upcoming_matches:
        st.info("Aucun match programmé dans les 10 prochains jours pour cette compétition.")
    else:
        for idx, m in enumerate(upcoming_matches):
            ht = m["homeTeam"]["name"]
            at = m["awayTeam"]["name"]
            dt_label = f"{m['utcDate'][:10]} à {m['utcDate'][11:16]} UTC"
            
            res = compute_match_mathematics(ht, at, model_fit, league_code, is_live=False)
            bp = res["best_pick"]

            header_text = (
                f"⚽ {dt_label}  |  {ht} vs {at}   "
                f"👉 {bp['label']} ({bp['prob']}% | Cote {bp['odds']})   "
                f"[1: {res['p_1']}% • X: {res['p_x']}% • 2: {res['p_2']}%]"
            )

            with st.expander(header_text, expanded=(idx == 0)):
                st.markdown(f"""
                <div class="top-pick-bar">
                    <b>🎯 PRÉDILECTION DU MODÈLE :</b> <span class="val-green">{bp['label']}</span> — 
                    Probabilité : <b>{bp['prob']}%</b> | Cote Équitable : <b>{bp['odds']}</b> | 
                    xG MLE : <b>{res['lambda_h']} - {res['lambda_a']}</b> (Écart Skellam : <b>{res['skellam_diff']:+.2f}</b>)
                </div>
                """, unsafe_allow_html=True)

                # LIGNE 1 : 1N2, DOUBLE CHANCE, DNB, HANDICAPS ASIATIQUES
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">1. Résultat Final (1N2)</div>
                        1 ({ht[:12]}) : <span class="val">{res['p_1']}%</span> (Cote {prob_to_odds(res['p_1'])})<br>
                        Nul (X) : <span class="val">{res['p_x']}%</span> (Cote {prob_to_odds(res['p_x'])})<br>
                        2 ({at[:12]}) : <span class="val">{res['p_2']}%</span> (Cote {prob_to_odds(res['p_2'])})
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">2. Double Chance & DNB</div>
                        1X : <span class="val-green">{res['p_1x']}%</span> | X2 : <span class="val-green">{res['p_x2']}%</span><br>
                        DNB 1 ({ht[:10]}) : <span class="val">{res['p_dnb1']}%</span><br>
                        DNB 2 ({at[:10]}) : <span class="val">{res['p_dnb2']}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                with c3:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">3. Handicaps Asiatiques (Skellam)</div>
                        {ht[:10]} (-1.5) : <span class="val">{res['p_ah_h_m15']}%</span><br>
                        {at[:10]} (-1.5) : <span class="val">{res['p_ah_a_m15']}%</span><br>
                        {ht[:10]} (+1.5) : <b>{res['p_ah_h_p15']}%</b> | {at[:10]} (+1.5) : <b>{res['p_ah_a_p15']}%</b>
                    </div>
                    """, unsafe_allow_html=True)
                with c4:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">4. Combos Résultat + Buts</div>
                        1X & +1.5 Buts : <span class="val-green">{res['p_1x_o15']}%</span><br>
                        X2 & +1.5 Buts : <span class="val-green">{res['p_x2_o15']}%</span><br>
                        12 (Pas de nul) : <span class="val">{res['p_12']}%</span>
                    </div>
                    """, unsafe_allow_html=True)

                # LIGNE 2 : TOTAUX BUTS, BTTS, BUTS PAR ÉQUIPE, 1ÈRE MI-TEMPS
                b1, b2, b3, b4 = st.columns(4)
                with b1:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">5. Total Buts Match</div>
                        +1.5 Buts : <span class="val-green">{res['p_o15']}%</span> | -1.5 : <b>{res['p_u15']}%</b><br>
                        +2.5 Buts : <span class="val">{res['p_o25']}%</span> | -2.5 : <span class="val">{res['p_u25']}%</span><br>
                        +3.5 Buts : <b>{res['p_o35']}%</b> | -3.5 : <span class="val-green">{res['p_u35']}%</span>
                    </div>
                    """, unsafe_allow_html=True)
                with b2:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">6. BTTS & Buts par Équipe</div>
                        BTTS Oui : <span class="val">{res['p_btts_y']}%</span> | Non : <span class="val">{res['p_btts_n']}%</span><br>
                        {ht[:10]} +0.5 : <b>{res['p_h_o05']}%</b> | +1.5 : <b>{res['p_h_o15']}%</b><br>
                        {at[:10]} +0.5 : <b>{res['p_a_o05']}%</b> | +1.5 : <b>{res['p_a_o15']}%</b>
                    </div>
                    """, unsafe_allow_html=True)
                with b3:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">7. 1ère Mi-Temps (45 min)</div>
                        1 MT : <span class="val">{res['ht_1']}%</span> | X MT : <span class="val">{res['ht_x']}%</span> | 2 MT : <span class="val">{res['ht_2']}%</span><br>
                        +0.5 But MT : <span class="val-green">{res['ht_o05']}%</span><br>
                        +1.5 Buts MT : <b>{res['ht_o15']}%</b>
                    </div>
                    """, unsafe_allow_html=True)
                with b4:
                    htft = res["ht_ft"]
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">8. Mi-Temps / Fin (HT/FT)</div>
                        1/1 : <span class="val">{htft['1/1']}%</span> | 2/2 : <span class="val">{htft['2/2']}%</span><br>
                        X/1 : <span class="val-amber">{htft['X/1']}%</span> | X/2 : <span class="val-amber">{htft['X/2']}%</span><br>
                        X/X : <b>{htft['X/X']}%</b> | 1/2 : <b>{htft['1/2']}%</b> | 2/1 : <b>{htft['2/1']}%</b>
                    </div>
                    """, unsafe_allow_html=True)

                # LIGNE 3 : CORNERS, CARTONS JAUNES & TOP 5 SCORES EXACTS
                a1, a2, a3 = st.columns([1, 1, 2])
                with a1:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">9. Corners (~{res['tot_corners']})</div>
                        Dom ~{res['exp_c_h']} | Ext ~{res['exp_c_a']}<br>
                        +7.5 : <span class="val-green">{res['p_c75']}%</span> | +8.5 : <span class="val">{res['p_c85']}%</span> | +9.5 : <b>{res['p_c95']}%</b>
                    </div>
                    """, unsafe_allow_html=True)
                with a2:
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">10. Cartons Jaunes (~{res['tot_cards']})</div>
                        +2.5 Cartons : <span class="val-green">{res['p_y25']}%</span><br>
                        +3.5 Cartons : <span class="val-amber">{res['p_y35']}%</span> | +4.5 : <b>{res['p_y45']}%</b>
                    </div>
                    """, unsafe_allow_html=True)
                with a3:
                    sc_str = "   |   ".join([f"<b>{s['score']}</b> ({s['prob']}% • @{s['odds']})" for s in res["top_scores"]])
                    st.markdown(f"""
                    <div class="panel">
                        <div class="panel-title">11. Top 5 Scores Exacts (Distribution Bivariée)</div>
                        <div style="margin-top:6px;">{sc_str}</div>
                        <div style="font-size:0.8rem; color:#94A3B8; margin-top:6px;">
                            Forces MLE : {ht} (Att {res['h_att']} / Déf {res['h_def']}) vs {at} (Att {res['a_att']} / Déf {res['a_def']})
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# ONGLET 2 : LIVE EN DIRECT (MATCHS EN COURS UNIQUEMENT)
# ------------------------------------------------------------------------------
with tab_live:
    st.subheader(f"🔴 Matchs en Direct — {selected_comp}")
    if st.button("🔄 Rafraîchir les scores en direct"):
        st.cache_data.clear()
        st.rerun()

    if not live_matches:
        st.info("Aucun match n'est actuellement en cours dans cette compétition.")
    else:
        for lm in live_matches:
            ht, at = lm["homeTeam"]["name"], lm["awayTeam"]["name"]
            sc = lm.get("score", {}).get("fullTime", {})
            sh = sc.get("home") if sc.get("home") is not None else 0
            sa = sc.get("away") if sc.get("away") is not None else 0
            minute = lm.get("minute")
            if not minute:
                try:
                    kick = datetime.strptime(lm["utcDate"][:19], "%Y-%m-%dT%H:%M:%S")
                    diff_m = int((datetime.utcnow() - kick).total_seconds() / 60)
                    minute = int(np.clip(diff_m if diff_m <= 45 else diff_m - 15, 1, 89))
                except Exception:
                    minute = 45

            l_res = compute_match_mathematics(ht, at, model_fit, league_code, is_live=True, live_h=sh, live_a=sa, elapsed_min=minute)
            with st.expander(f"🔴 {minute}' | {ht} {sh} - {sa} {at}  👉  {l_res['best_pick']['label']} ({l_res['best_pick']['prob']}%)", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.metric("1N2 Live", f"{l_res['p_1']}% | {l_res['p_x']}% | {l_res['p_2']}%")
                with c2: st.metric("Double Chance Live", f"1X: {l_res['p_1x']}%", f"X2: {l_res['p_x2']}%")
                with c3: st.metric("xG Restant", f"{l_res['rem_h']} - {l_res['rem_a']}")
                with c4: st.metric("Score Final le + Probable", l_res["top_scores"][0]["score"], f"{l_res['top_scores'][0]['prob']}%")

# ------------------------------------------------------------------------------
# ONGLET 3 : AUDIT PUR PAR CHAMPIONNAT (VALIDÉE / ÉCHEC)
# ------------------------------------------------------------------------------
with tab_audit:
    st.subheader(f"✅ Audit de Précision du Modèle — {selected_comp}")
    if not finished_matches:
        st.info("Aucun match terminé disponible pour l'audit.")
    else:
        nb_audit = st.slider("Nombre de derniers matchs terminés à vérifier :", 10, min(100, len(finished_matches)), min(30, len(finished_matches)), 5)
        rows = []
        ok_count = 0
        ko_count = 0

        for m in finished_matches[:nb_audit]:
            ht, at = m["homeTeam"]["name"], m["awayTeam"]["name"]
            sc = m.get("score", {}).get("fullTime", {})
            rh, ra = sc.get("home"), sc.get("away")
            if rh is not None and ra is not None:
                pred = compute_match_mathematics(ht, at, model_fit, league_code, is_live=False)
                bp = pred["best_pick"]
                valid = check_pick_validated(bp["code"], rh, ra)
                if valid:
                    ok_count += 1
                    verdict = "✅ VALIDÉE"
                else:
                    ko_count += 1
                    verdict = "❌ ÉCHEC"

                rows.append({
                    "Date": m["utcDate"][:10],
                    "Match": f"{ht} vs {at}",
                    "Prédiction du Bot": bp["label"],
                    "Probabilité": f"{bp['prob']}%",
                    "Score Réel": f"{rh} - {ra}",
                    "Résultat": verdict
                })

        tot_eval = ok_count + ko_count
        if tot_eval > 0:
            rate = round((ok_count / tot_eval) * 100.0, 1)
            k1, k2, k3 = st.columns(3)
            with k1: st.metric(f"Taux de Réussite ({league_code})", f"{rate}%")
            with k2: st.metric("Prédictions Validées", f"{ok_count} / {tot_eval}")
            with k3: st.metric("Prédictions en Échec", f"{ko_count}")
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
