import numpy as np
from scipy.stats import poisson, nbinom

def dixon_coles_tau(x, y, home_xg, away_xg, rho=-0.08):
    """Ajustement de Dixon-Coles pour corriger les faibles scores."""
    if x == 0 and y == 0:
        return max(0.01, 1.0 - (home_xg * away_xg * rho))
    elif x == 0 and y == 1:
        return max(0.01, 1.0 + (home_xg * rho))
    elif x == 1 and y == 0:
        return max(0.01, 1.0 + (away_xg * rho))
    elif x == 1 and y == 1:
        return max(0.01, 1.0 - rho)
    return 1.0

def run_hybrid_match_prediction(data):
    is_live = data.get("is_live", False)
    score_h = int(data.get("current_home_score", 0)) if is_live else 0
    score_a = int(data.get("current_away_score", 0)) if is_live else 0
    minute = int(data.get("minute", 0)) if is_live else 0

    full_home_xg = max(0.2, float(data.get("exp_goals_home", 1.4)))
    full_away_xg = max(0.2, float(data.get("exp_goals_away", 1.1)))

    # Statistiques d'intensité en direct
    sot_h = float(data.get("shots_on_target_home", 0))
    sot_a = float(data.get("shots_on_target_away", 0))
    shots_h = float(data.get("shots_total_home", 0))
    shots_a = float(data.get("shots_total_away", 0))
    fouls_h = float(data.get("fouls_home", 0))
    fouls_a = float(data.get("fouls_away", 0))

    max_goals = 8
    score_matrix = np.zeros((max_goals, max_goals))

    if is_live and minute > 5:
        time_elapsed_ratio = min(0.95, minute / 90.0)
        rem_time_ratio = max(0.05, (90.0 - min(88, minute)) / 90.0)

        # 1. Attente théorique à la minute t
        exp_sot_h_t = max(0.5, (full_home_xg * 3.2) * time_elapsed_ratio)
        exp_sot_a_t = max(0.5, (full_away_xg * 3.0) * time_elapsed_ratio)

        exp_shots_h_t = max(1.0, (full_home_xg * 8.0) * time_elapsed_ratio)
        exp_shots_a_t = max(1.0, (full_away_xg * 7.5) * time_elapsed_ratio)

        # 2. Ratio de performance/pression en direct
        ratio_sot_h = sot_h / exp_sot_h_t
        ratio_sot_a = sot_a / exp_sot_a_t

        ratio_shots_h = shots_h / exp_shots_h_t
        ratio_shots_a = shots_a / exp_shots_a_t

        # Combiné d'intensité offensive (Pondération 60% tirs cadrés, 40% tirs totaux)
        intensity_h = (0.6 * ratio_sot_h) + (0.4 * ratio_shots_h)
        intensity_a = (0.6 * ratio_sot_a) + (0.4 * ratio_shots_a)

        # Bornage de sécurité pour éviter les dérives irréalistes (entre 0.35x et 2.2x)
        mult_h = max(0.35, min(2.2, intensity_h))
        mult_a = max(0.35, min(2.2, intensity_a))

        # 3. Ajustement de réactivité selon les fautes (jeu haché)
        tot_fouls = fouls_h + fouls_a
        foul_penalty = 0.88 if tot_fouls > (14 * time_elapsed_ratio) else 1.0

        # Recalcul final des xG restants basés sur le temps ET l'intensité réelle
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
        rem_home_xg = full_home_xg
        rem_away_xg = full_away_xg
        for h in range(max_goals):
            for a in range(max_goals):
                p_h = poisson.pmf(h, full_home_xg)
                p_a = poisson.pmf(a, full_away_xg)
                tau = dixon_coles_tau(h, a, full_home_xg, full_away_xg)
                score_matrix[h, a] = p_h * p_a * tau

    total_p = np.sum(score_matrix)
    if total_p > 0:
        score_matrix /= total_p

    # Extraction des 3 scores exacts réels les plus probables
    exact_scores = []
    for h in range(max_goals):
        for a in range(max_goals):
            prob = score_matrix[h, a]
            if prob > 0.0001:
                exact_scores.append(((h, a), float(prob)))

    exact_scores.sort(key=lambda x: x[1], reverse=True)
    top_3_exact_scores = exact_scores[:3]

    p_home = float(np.sum(np.tril(score_matrix, -1)))
    p_draw = float(np.sum(np.diag(score_matrix)))
    p_away = float(np.sum(np.triu(score_matrix, 1)))

    curr_total_goals = score_h + score_a if is_live else 0
    goals_ou = {}
    for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
        if is_live and curr_total_goals > line:
            goals_ou[f"Over_{line}"] = 1.0
            goals_ou[f"Under_{line}"] = 0.0
        else:
            over_prob = sum(score_matrix[h, a] for h in range(max_goals) for a in range(max_goals) if (h + a) > line)
            goals_ou[f"Over_{line}"] = float(over_prob)
            goals_ou[f"Under_{line}"] = float(1.0 - over_prob)

    # Corners basés sur le temps + l'intensité
    c_home = float(data.get("exp_corners_home", 4.8))
    c_away = float(data.get("exp_corners_away", 4.0))
    tot_c_exp = (c_home + c_away) * ((90 - minute) / 90.0 if is_live else 1.0)
    tot_c_exp = max(1.0, tot_c_exp)
    r_c = 10.0
    p_c = r_c / (r_c + tot_c_exp)

    corners_ou = {}
    for line in [8.5, 9.5, 10.5, 11.5]:
        k = int(np.floor(line))
        under_p = float(nbinom.cdf(k, r_c, p_c))
        corners_ou[f"Over_{line}"] = float(1.0 - under_p)
        corners_ou[f"Under_{line}"] = under_p

    # Cartons : ajustés selon le nombre réel de fautes
    k_home = float(data.get("exp_cards_home", 2.0))
    k_away = float(data.get("exp_cards_away", 2.1))
    foul_card_boost = 1.3 if is_live and (fouls_h + fouls_a) > 15 else 1.0
    tot_k_exp = (k_home + k_away) * ((90 - minute) / 90.0 if is_live else 1.0) * foul_card_boost
    tot_k_exp = max(0.8, tot_k_exp)
    r_k = 8.0
    p_k = r_k / (r_k + tot_k_exp)

    cards_ou = {}
    for line in [3.5, 4.5, 5.5, 6.5]:
        k = int(np.floor(line))
        under_p = float(nbinom.cdf(k, r_k, p_k))
        cards_ou[f"Over_{line}"] = float(1.0 - under_p)
        cards_ou[f"Under_{line}"] = under_p

    return {
        "prob_1N2": {"1": p_home, "N": p_draw, "2": p_away},
        "score_matrix": score_matrix,
        "top_3_exact_scores": top_3_exact_scores,
        "goals_ou": goals_ou,
        "corners": {"exp_total": round(tot_c_exp, 1), "ou": corners_ou},
        "cards": {"exp_total": round(tot_k_exp, 1), "ou": cards_ou},
        "intensity_metrics": {
            "rem_home_xg": round(rem_home_xg, 2),
            "rem_away_xg": round(rem_away_xg, 2)
        }
    }
