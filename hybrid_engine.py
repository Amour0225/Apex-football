import numpy as np
from scipy.stats import poisson, nbinom

def dixon_coles_tau(x, y, home_xg, away_xg, rho=-0.08):
    """
    Ajustement de Dixon-Coles pour corriger la sous-estimation
    des petits scores (0-0, 1-0, 0-1, 1-1).
    """
    if x == 0 and y == 0:
        return 1.0 - (home_xg * away_xg * rho)
    elif x == 0 and y == 1:
        return 1.0 + (home_xg * rho)
    elif x == 1 and y == 0:
        return 1.0 + (away_xg * rho)
    elif x == 1 and y == 1:
        return 1.0 - rho
    else:
        return 1.0

def run_hybrid_match_prediction(data):
    """
    Moteur de prédiction hybride :
    - Dixon-Coles pour les buts et probabilités 1N2
    - Loi Binomiale Négative pour les corners et cartons
    """
    home_xg = float(data.get("exp_goals_home", 1.5))
    away_xg = float(data.get("exp_goals_away", 1.2))
    
    c_home = float(data.get("exp_corners_home", 5.0))
    c_away = float(data.get("exp_corners_away", 4.0))
    
    k_home = float(data.get("exp_cards_home", 2.0))
    k_away = float(data.get("exp_cards_away", 2.0))

    # --- 1. MODÈLE DIXON-COLES (BUTS & 1N2) ---
    max_goals = 8
    score_matrix = np.zeros((max_goals, max_goals))
    
    for h in range(max_goals):
        for a in range(max_goals):
            p_h = poisson.pmf(h, home_xg)
            p_a = poisson.pmf(a, away_xg)
            tau = dixon_coles_tau(h, a, home_xg, away_xg)
            score_matrix[h, a] = p_h * p_a * tau

    # Normalisation de la matrice de probabilité
    total_p = np.sum(score_matrix)
    if total_p > 0:
        score_matrix = score_matrix / total_p

    # Probabilités 1N2
    p_home = float(np.sum(np.tril(score_matrix, -1)))
    p_draw = float(np.sum(np.diag(score_matrix)))
    p_away = float(np.sum(np.triu(score_matrix, 1)))

    # Marchés Over/Under Buts
    goals_ou = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        over_prob = 0.0
        for h in range(max_goals):
            for a in range(max_goals):
                if (h + a) > line:
                    over_prob += score_matrix[h, a]
        goals_ou[f"Over_{line}"] = float(over_prob)
        goals_ou[f"Under_{line}"] = float(1.0 - over_prob)

    # --- 2. MODÈLE BINOMIALE NÉGATIVE (CORNERS) ---
    tot_corners_exp = c_home + c_away
    r_corners = 15.0  # Paramètre de dispersion
    p_c = r_corners / (r_corners + tot_corners_exp)
    
    corners_ou = {}
    for line in [8.5, 9.5, 10.5, 11.5]:
        k = int(np.floor(line))
        under_prob = float(nbinom.cdf(k, r_corners, p_c))
        over_prob = float(1.0 - under_prob)
        corners_ou[f"Over_{line}"] = over_prob
        corners_ou[f"Under_{line}"] = under_prob

    # --- 3. MODÈLE BINOMIALE NÉGATIVE (CARTONS) ---
    tot_cards_exp = k_home + k_away
    r_cards = 10.0  # Paramètre de dispersion
    p_k = r_cards / (r_cards + tot_cards_exp)

    cards_ou = {}
    for line in [3.5, 4.5, 5.5, 6.5]:
        k = int(np.floor(line))
        under_prob = float(nbinom.cdf(k, r_cards, p_k))
        over_prob = float(1.0 - under_prob)
        cards_ou[f"Over_{line}"] = over_prob
        cards_ou[f"Under_{line}"] = under_prob

    return {
        "goals_and_1N2": {
            "prob_1N2": {"1": p_home, "N": p_draw, "2": p_away},
            "score_matrix": score_matrix,
            "over_under": goals_ou
        },
        "corners": {
            "exp_total": round(tot_corners_exp, 1),
            "over_under": corners_ou
        },
        "cards": {
            "exp_total": round(tot_cards_exp, 1),
            "over_under": cards_ou
        }
    }
