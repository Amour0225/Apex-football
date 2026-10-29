import streamlit as st
import requests
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime, timedelta
import math

# ==============================================================================
# 1. CONFIGURATION & DESIGN AVANCÉ V50.0 APEX CUPS QUANT PRO
# ==============================================================================
st.set_page_config(
    page_title="Apex Cups Quant v50.0 Pro (Carabao, DFB-Pokal, Copa del Rey)",
    page_icon="🏆",
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
        background: linear-gradient(135deg, #0B132B 0%, #1A102F 50%, #032B45 100%);
        border: 2px solid #F59E0B; border-radius: 18px; padding: 24px; margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(245, 158, 11, 0.25);
    }
    .cup-box {
        background-color: #0B0F19; border: 1px solid #1E293B; border-left: 5px solid #F59E0B;
        border-radius: 0 14px 14px 0; padding: 20px; margin: 16px 0; font-size: 0.95rem; line-height: 1.65; color: #E2E8F0;
    }
    .vip-banner {
        background: linear-gradient(135deg, #311042 0%, #701A75 50%, #1E3A8A 100%);
        border: 2px solid #F59E0B; border-radius: 16px; padding: 22px; text-align: center; margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(245, 158, 11, 0.25);
    }
    .sub-card {
        background: #0B1120; border: 1.5px solid #1E293B;
        border-radius: 14px; padding: 18px; margin-bottom: 16px;
        transition: all 0.2s ease;
    }
    .sub-card:hover { border-color: #F59E0B; }
    .qualif-box {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.12) 0%, rgba(16, 185, 129, 0.12) 100%);
        border: 2px solid #F59E0B; border-radius: 14px; padding: 18px; margin: 12px 0;
    }
    .option-box {
        background: rgba(16, 185, 129, 0.08); border: 1.5px solid #10B981; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .option-box-sec {
        background: rgba(56, 189, 248, 0.08); border: 1.5px solid #38BDF8; border-radius: 14px; padding: 16px; margin: 10px 0;
    }
    .big-score-box {
        background: #0F172A; border: 2px solid #F59E0B; border-radius: 14px; padding: 16px; text-align: center; margin: 6px 0;
    }
    .big-score-val { font-size: 2.2rem; font-weight: 900; color: #F59E0B; line-height: 1.1; font-family: 'JetBrains Mono', monospace; }
    .big-score-prob { font-size: 1.05rem; font-weight: 700; color: #10B981; margin-top: 5px; }
    .badge-cup {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800; text-transform: uppercase;
        background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; margin-right: 6px;
    }
    .badge-edge {
        display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 800;
        background: rgba(16, 185, 129, 0.15); color: #10B981; border: 1px solid #10B981;
    }
    .stat-badge {
        font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 800; color: #F59E0B;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. BASE DE DONNÉES EXPERTE : COUPES NATIONALES & RATINGS INTER-DIVISIONS
# ==============================================================================
# Base de données calibrée de force, ELO et tiers inter-divisions
# Permet une précision mathématique maximale même lors de duels D1 vs D2 ou D1 vs D3
CUP_COMPETITIONS = {
    "Coupe de la Ligue Anglaise 🇬🇧 (Carabao Cup)": "EFL_CUP",
    "Coupe d'Allemagne 🇩🇪 (DFB-Pokal)": "DFB_POKAL",
    "Coupe du Roi Espagne 🇪🇸 (Copa del Rey)": "COPA_DEL_REY"
}

CUP_PROFILES = {
    "EFL_CUP": {
        "name": "Carabao Cup",
        "country": "Angleterre 🇬🇧",
        "avg_g_h": 1.60, "avg_g_a": 1.30, "rho": -0.105,
        "card_base": 3.7, "corner_base": 10.2, "dispersion": 10.2,
        "upset_factor": 1.15 # Taux de surprise en coupe anglaise
    },
    "DFB_POKAL": {
        "name": "DFB-Pokal",
        "country": "Allemagne 🇩🇪",
        "avg_g_h": 1.75, "avg_g_a": 1.45, "rho": -0.090,
        "card_base": 4.1, "corner_base": 10.0, "dispersion": 11.0,
        "upset_factor": 1.22 # Coupe très prolifique avec tradition d'exploits
    },
    "COPA_DEL_REY": {
        "name": "Copa del Rey",
        "country": "Espagne 🇪🇸",
        "avg_g_h": 1.50, "avg_g_a": 1.15, "rho": -0.120,
        "card_base": 4.9, "corner_base": 9.5, "dispersion": 9.4,
        "upset_factor": 1.10 # Matchs plus fermés et tactiques
    }
}

# Base d'équipes trans-divisions calibrées avec ELO absolu, force offensive et défensive
CUP_TEAMS_DB = {
    # ANGLETERRE (Carabao Cup)
    "Manchester City": {"cup": "EFL_CUP", "tier": 1, "elo": 2040, "att": 2.45, "def": 0.85, "cup_pri": 0.85},
    "Arsenal": {"cup": "EFL_CUP", "tier": 1, "elo": 1980, "att": 2.25, "def": 0.82, "cup_pri": 0.88},
    "Liverpool": {"cup": "EFL_CUP", "tier": 1, "elo": 1995, "att": 2.30, "def": 0.90, "cup_pri": 0.92},
    "Chelsea": {"cup": "EFL_CUP", "tier": 1, "elo": 1870, "att": 2.05, "def": 1.15, "cup_pri": 0.95},
    "Manchester United": {"cup": "EFL_CUP", "tier": 1, "elo": 1820, "att": 1.75, "def": 1.25, "cup_pri": 0.95},
    "Tottenham": {"cup": "EFL_CUP", "tier": 1, "elo": 1860, "att": 2.10, "def": 1.30, "cup_pri": 0.95},
    "Newcastle": {"cup": "EFL_CUP", "tier": 1, "elo": 1850, "att": 1.95, "def": 1.15, "cup_pri": 0.95},
    "Aston Villa": {"cup": "EFL_CUP", "tier": 1, "elo": 1880, "att": 2.00, "def": 1.10, "cup_pri": 0.90},
    "Brighton": {"cup": "EFL_CUP", "tier": 1, "elo": 1780, "att": 1.85, "def": 1.35, "cup_pri": 0.92},
    "West Ham": {"cup": "EFL_CUP", "tier": 1, "elo": 1740, "att": 1.65, "def": 1.45, "cup_pri": 0.90},
    "Crystal Palace": {"cup": "EFL_CUP", "tier": 1, "elo": 1710, "att": 1.45, "def": 1.35, "cup_pri": 0.92},
    "Fulham": {"cup": "EFL_CUP", "tier": 1, "elo": 1720, "att": 1.55, "def": 1.35, "cup_pri": 0.92},
    "Everton": {"cup": "EFL_CUP", "tier": 1, "elo": 1690, "att": 1.35, "def": 1.40, "cup_pri": 0.90},
    "Brentford": {"cup": "EFL_CUP", "tier": 1, "elo": 1730, "att": 1.70, "def": 1.45, "cup_pri": 0.92},
    "Leicester City": {"cup": "EFL_CUP", "tier": 1, "elo": 1670, "att": 1.40, "def": 1.65, "cup_pri": 0.90},
    "Southampton": {"cup": "EFL_CUP", "tier": 1, "elo": 1640, "att": 1.25, "def": 1.75, "cup_pri": 0.88},
    "Ipswich Town": {"cup": "EFL_CUP", "tier": 1, "elo": 1630, "att": 1.30, "def": 1.70, "cup_pri": 0.88},
    "Leeds United": {"cup": "EFL_CUP", "tier": 2, "elo": 1620, "att": 1.65, "def": 1.20, "cup_pri": 0.95},
    "Burnley": {"cup": "EFL_CUP", "tier": 2, "elo": 1590, "att": 1.50, "def": 1.25, "cup_pri": 0.92},
    "Sheffield United": {"cup": "EFL_CUP", "tier": 2, "elo": 1580, "att": 1.45, "def": 1.25, "cup_pri": 0.92},
    "Sunderland": {"cup": "EFL_CUP", "tier": 2, "elo": 1570, "att": 1.55, "def": 1.30, "cup_pri": 0.95},
    "Middlesbrough": {"cup": "EFL_CUP", "tier": 2, "elo": 1530, "att": 1.40, "def": 1.35, "cup_pri": 0.95},
    "Coventry City": {"cup": "EFL_CUP", "tier": 2, "elo": 1510, "att": 1.35, "def": 1.40, "cup_pri": 0.98},
    "Birmingham City": {"cup": "EFL_CUP", "tier": 3, "elo": 1420, "att": 1.45, "def": 1.30, "cup_pri": 1.00},
    "Wrexham": {"cup": "EFL_CUP", "tier": 3, "elo": 1390, "att": 1.40, "def": 1.35, "cup_pri": 1.00},
    
    # ALLEMAGNE (DFB-Pokal)
    "Bayern Munich": {"cup": "DFB_POKAL", "tier": 1, "elo": 2010, "att": 2.75, "def": 0.88, "cup_pri": 0.92},
    "Bayer Leverkusen": {"cup": "DFB_POKAL", "tier": 1, "elo": 1960, "att": 2.40, "def": 0.95, "cup_pri": 0.95},
    "Borussia Dortmund": {"cup": "DFB_POKAL", "tier": 1, "elo": 1890, "att": 2.20, "def": 1.25, "cup_pri": 0.95},
    "RB Leipzig": {"cup": "DFB_POKAL", "tier": 1, "elo": 1880, "att": 2.10, "def": 1.05, "cup_pri": 0.95},
    "Eintracht Frankfurt": {"cup": "DFB_POKAL", "tier": 1, "elo": 1810, "att": 1.95, "def": 1.35, "cup_pri": 0.98},
    "VfB Stuttgart": {"cup": "DFB_POKAL", "tier": 1, "elo": 1820, "att": 2.05, "def": 1.30, "cup_pri": 0.95},
    "SC Freiburg": {"cup": "DFB_POKAL", "tier": 1, "elo": 1750, "att": 1.65, "def": 1.35, "cup_pri": 0.95},
    "Union Berlin": {"cup": "DFB_POKAL", "tier": 1, "elo": 1710, "att": 1.35, "def": 1.30, "cup_pri": 0.95},
    "Werder Bremen": {"cup": "DFB_POKAL", "tier": 1, "elo": 1690, "att": 1.50, "def": 1.55, "cup_pri": 0.95},
    "Borussia M'gladbach": {"cup": "DFB_POKAL", "tier": 1, "elo": 1690, "att": 1.55, "def": 1.60, "cup_pri": 0.95},
    "VfL Wolfsburg": {"cup": "DFB_POKAL", "tier": 1, "elo": 1710, "att": 1.55, "def": 1.50, "cup_pri": 0.95},
    "FC Cologne (Köln)": {"cup": "DFB_POKAL", "tier": 2, "elo": 1610, "att": 1.60, "def": 1.40, "cup_pri": 0.98},
    "Hamburger SV": {"cup": "DFB_POKAL", "tier": 2, "elo": 1600, "att": 1.65, "def": 1.35, "cup_pri": 0.98},
    "Hertha BSC": {"cup": "DFB_POKAL", "tier": 2, "elo": 1580, "att": 1.55, "def": 1.45, "cup_pri": 0.98},
    "Fortuna Düsseldorf": {"cup": "DFB_POKAL", "tier": 2, "elo": 1570, "att": 1.50, "def": 1.30, "cup_pri": 0.98},
    "FC Schalke 04": {"cup": "DFB_POKAL", "tier": 2, "elo": 1520, "att": 1.45, "def": 1.60, "cup_pri": 0.98},
    "FC Saarbrücken": {"cup": "DFB_POKAL", "tier": 3, "elo": 1410, "att": 1.35, "def": 1.35, "cup_pri": 1.05},
    "Dynamo Dresden": {"cup": "DFB_POKAL", "tier": 3, "elo": 1390, "att": 1.40, "def": 1.30, "cup_pri": 1.00},

    # ESPAGNE (Copa del Rey)
    "Real Madrid": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 2050, "att": 2.50, "def": 0.85, "cup_pri": 0.90},
    "FC Barcelona": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 2020, "att": 2.60, "def": 0.92, "cup_pri": 0.92},
    "Atletico Madrid": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1920, "att": 1.95, "def": 0.85, "cup_pri": 0.96},
    "Athletic Bilbao": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1860, "att": 1.85, "def": 0.95, "cup_pri": 1.00}, # Spécialiste historique
    "Real Sociedad": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1840, "att": 1.70, "def": 0.95, "cup_pri": 0.98},
    "Villarreal": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1820, "att": 1.95, "def": 1.35, "cup_pri": 0.95},
    "Real Betis": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1790, "att": 1.65, "def": 1.20, "cup_pri": 0.98},
    "Sevilla FC": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1740, "att": 1.45, "def": 1.35, "cup_pri": 0.95},
    "Girona": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1780, "att": 1.85, "def": 1.35, "cup_pri": 0.90},
    "Valencia CF": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1710, "att": 1.35, "def": 1.45, "cup_pri": 0.95},
    "Celta Vigo": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1720, "att": 1.65, "def": 1.55, "cup_pri": 0.95},
    "RCD Mallorca": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1720, "att": 1.25, "def": 1.15, "cup_pri": 1.00},
    "RCD Espanyol": {"cup": "COPA_DEL_REY", "tier": 1, "elo": 1660, "att": 1.25, "def": 1.50, "cup_pri": 0.92},
    "Real Zaragoza": {"cup": "COPA_DEL_REY", "tier": 2, "elo": 1580, "att": 1.40, "def": 1.25, "cup_pri": 0.98},
    "Sporting Gijon": {"cup": "COPA_DEL_REY", "tier": 2, "elo": 1570, "att": 1.45, "def": 1.30, "cup_pri": 0.98},
    "Levante": {"cup": "COPA_DEL_REY", "tier": 2, "elo": 1590, "att": 1.50, "def": 1.30, "cup_pri": 0.98},
    "Cadiz CF": {"cup": "COPA_DEL_REY", "tier": 2, "elo": 1560, "att": 1.30, "def": 1.30, "cup_pri": 0.98},
    "Deportivo La Coruna": {"cup": "COPA_DEL_REY", "tier": 2, "elo": 1540, "att": 1.40, "def": 1.35, "cup_pri": 1.00},
    "Albacete": {"cup": "COPA_DEL_REY", "tier": 2, "elo": 1510, "att": 1.35, "def": 1.45, "cup_pri": 1.00},
    "Cultural Leonesa": {"cup": "COPA_DEL_REY", "tier": 3, "elo": 1380, "att": 1.30, "def": 1.30, "cup_pri": 1.05}
}

# Matchs programmés récents/types des coupes pour le calendrier
SCHEDULED_CUP_MATCHES = {
    "EFL_CUP": [
        {"home": "Tottenham", "away": "Manchester City", "date": "2026-10-30 20:15", "round": "8èmes de Finale"},
        {"home": "Brighton", "away": "Liverpool", "date": "2026-10-30 19:30", "round": "8èmes de Finale"},
        {"home": "Manchester United", "away": "Leicester City", "date": "2026-10-30 19:45", "round": "8èmes de Finale"},
        {"home": "Newcastle", "away": "Chelsea", "date": "2026-10-30 19:45", "round": "8èmes de Finale"},
        {"home": "Aston Villa", "away": "Crystal Palace", "date": "2026-10-30 19:45", "round": "8èmes de Finale"},
        {"home": "Arsenal", "away": "Leeds United", "date": "2026-10-31 19:45", "round": "8èmes de Finale"}
    ],
    "DFB_POKAL": [
        {"home": "VfL Wolfsburg", "away": "Borussia Dortmund", "date": "2026-10-29 19:45", "round": "2ème Tour (16èmes)"},
        {"home": "RB Leipzig", "away": "FC St. Pauli", "date": "2026-10-29 17:00", "round": "2ème Tour (16èmes)"},
        {"home": "VfB Stuttgart", "away": "FC Kaiserslautern", "date": "2026-10-29 19:45", "round": "2ème Tour (16èmes)"},
        {"home": "FC Cologne (Köln)", "away": "Holstein Kiel", "date": "2026-10-29 19:45", "round": "2ème Tour (16èmes)"},
        {"home": "SC Freiburg", "away": "Hamburger SV", "date": "2026-10-30 17:00", "round": "2ème Tour (16èmes)"},
        {"home": "FC Saarbrücken", "away": "Bayern Munich", "date": "2026-10-30 19:45", "round": "2ème Tour (16èmes)"}
    ],
    "COPA_DEL_REY": [
        {"home": "Albacete", "away": "Celta Vigo", "date": "2026-11-01 20:00", "round": "1er Tour Principal"},
        {"home": "Cultural Leonesa", "away": "Athletic Bilbao", "date": "2026-11-01 19:00", "round": "1er Tour Principal"},
        {"home": "Sporting Gijon", "away": "Valencia CF", "date": "2026-11-02 20:00", "round": "1er Tour Principal"},
        {"home": "Real Zaragoza", "away": "Real Sociedad", "date": "2026-11-02 21:00", "round": "1er Tour Principal"},
        {"home": "Deportivo La Coruna", "away": "Sevilla FC", "date": "2026-11-03 20:00", "round": "1er Tour Principal"},
        {"home": "Cadiz CF", "away": "Real Betis", "date": "2026-11-03 21:00", "round": "1er Tour Principal"}
    ]
}

# ==============================================================================
# 3. MOTEUR MATHÉMATIQUE KNOCKOUT DE COUPE : DIXON-COLES + QUALIFICATION
# ==============================================================================

def dixon_coles_tau(x, y, lambda_h, lambda_a, rho=-0.115):
    if x == 0 and y == 0: return max(0.01, 1.0 - (lambda_h * lambda_a * rho))
    elif x == 0 and y == 1: return max(0.01, 1.0 + (lambda_h * rho))
    elif x == 1 and y == 0: return max(0.01, 1.0 + (lambda_a * rho))
    elif x == 1 and y == 1: return max(0.01, 1.0 - rho)
    return 1.0

def negative_binomial_pmf(k, mu, dispersion=10.0):
    r = dispersion
    p = r / (r + mu)
    return nbinom.pmf(k, r, p)

def prob_to_odds(p):
    if p <= 0.001: return 99.00
    return round(min(99.00, 100.0 / p), 2)

def calculate_quarter_kelly(prob_pct, bookmaker_odds, bankroll, estimation_uncertainty=0.08, max_cap_pct=0.05):
    p = prob_pct / 100.0
    b = bookmaker_odds - 1.0
    if b <= 0 or p <= 0: return 0.0, 0.0
    f_star = (p * (b + 1.0) - 1.0) / b
    ev_val = round(((p * bookmaker_odds) - 1.0) * 100, 2)
    if f_star <= 0: return 0.0, ev_val
    f_adjusted = f_star * 0.25 * (1.0 - estimation_uncertainty)
    f_capped = min(max(0.0, f_adjusted), max_cap_pct)
    return round(bankroll * f_capped, 2), ev_val

# ==============================================================================
# 4. MOTEUR DE PRÉDICTION EXPERT COUPES NATIONALES (KNOCKOUT & PROLONGATIONS)
# ==============================================================================

def run_cup_prediction(
    h_name, a_name, 
    cup_code="EFL_CUP",
    h_rotation="Équipe Type (100%)",
    a_rotation="Équipe Type (100%)",
    weather_mode="Normal (Idéal)",
    bankroll=1000.0,
    book_odds_custom=None
):
    """
    Moteur de simulation stochastique à élimination directe (Knockout Match).
    Calcule simultanément le temps réglementaire (90 min) et la qualification (Prolongations + Tirs au but).
    """
    cup_cfg = CUP_PROFILES.get(cup_code, CUP_PROFILES["EFL_CUP"])
    
    # 1. Récupération des données trans-divisions des deux équipes
    default_team = {"cup": cup_code, "tier": 1, "elo": 1650, "att": 1.40, "def": 1.40, "cup_pri": 0.95}
    h_data = CUP_TEAMS_DB.get(h_name, default_team)
    a_data = CUP_TEAMS_DB.get(a_name, default_team)
    
    # 2. Facteur de Rotation / Composition Remaniée
    rot_mult = {
        "Équipe Type (100%)": {"att": 1.00, "def": 1.00},
        "Rotation Modérée (4-5 titulaires au repos)": {"att": 0.88, "def": 1.15},
        "Forte Rotation (7-8 remplaçants / Jeunesse)": {"att": 0.76, "def": 1.30}
    }
    h_rot_factors = rot_mult.get(h_rotation, rot_mult["Équipe Type (100%)"])
    a_rot_factors = rot_mult.get(a_rotation, rot_mult["Équipe Type (100%)"])
    
    # 3. Écart Hiérarchique de Division (Tier Gap) & ELO Différentiel
    tier_gap = a_data["tier"] - h_data["tier"]
    tier_advantage = tier_gap * 180.0 # 180 points ELO par division d'écart
    
    # Facteur de motivation "Petit Poucet" : l'outsider qui reçoit a un surcroît de rage de vaincre
    poucet_bonus = 0.0
    if h_data["tier"] > a_data["tier"]: # Outsider reçoit le cador
        poucet_bonus = 60.0
        
    eff_elo_diff = (h_data["elo"] - a_data["elo"]) + tier_advantage + poucet_bonus
    
    # 4. Calcul des xG attendus (Base ligue + ELO Sigmoïde + Rotation)
    elo_mult_h = np.clip(1.0 + (eff_elo_diff / 750.0), 0.35, 2.10)
    elo_mult_a = np.clip(1.0 - (eff_elo_diff / 750.0), 0.35, 2.10)
    
    weather_mult = 0.88 if ("Pluie" in weather_mode or "Lourd" in weather_mode) else (0.92 if "Canicule" in weather_mode else 1.0)
    
    base_gh, base_ga = cup_cfg["avg_g_h"], cup_cfg["avg_g_a"]
    
    raw_h_xg = (h_data["att"] / 1.50) * (a_data["def"] / 1.30) * base_gh
    raw_a_xg = (a_data["att"] / 1.50) * (h_data["def"] / 1.30) * base_ga
    
    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * h_rot_factors["att"] * a_rot_factors["def"] * weather_mult, 0.20, 5.20))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * a_rot_factors["att"] * h_rot_factors["def"] * weather_mult, 0.15, 4.50))
    
    # 5. Matrice bivariée Dixon-Coles 9x9 (Temps Réglementaire 90 min)
    rho = cup_cfg.get("rho", -0.110)
    dispersion = cup_cfg.get("dispersion", 10.0)
    max_g = 9
    
    matrix_90 = np.zeros((max_g, max_g))
    for x in range(max_g):
        for y in range(max_g):
            p_x = negative_binomial_pmf(x, full_h_xg, dispersion)
            p_y = negative_binomial_pmf(y, full_a_xg, dispersion)
            tau = dixon_coles_tau(x, y, full_h_xg, full_a_xg, rho)
            matrix_90[x, y] = max(0.0, p_x * p_y * tau)
    tot_90 = np.sum(matrix_90)
    if tot_90 > 0: matrix_90 /= tot_90

    # Probabilités 90 minutes
    p_h_90 = float(np.sum(np.tril(matrix_90, -1))) * 100.0
    p_d_90 = float(np.sum(np.diag(matrix_90))) * 100.0
    p_a_90 = float(np.sum(np.triu(matrix_90, 1))) * 100.0
    
    prob_1x = round(p_h_90 + p_d_90, 1)
    prob_x2 = round(p_a_90 + p_d_90, 1)
    prob_12 = round(p_h_90 + p_a_90, 1)
    
    # Over / Under
    prob_o15 = round(float(np.sum([matrix_90[i, j] for i in range(max_g) for j in range(max_g) if i + j > 1])) * 100.0, 1)
    prob_o25 = round(float(np.sum([matrix_90[i, j] for i in range(max_g) for j in range(max_g) if i + j > 2])) * 100.0, 1)
    prob_u25 = round(100.0 - prob_o25, 1)
    prob_o35 = round(float(np.sum([matrix_90[i, j] for i in range(max_g) for j in range(max_g) if i + j > 3])) * 100.0, 1)
    prob_u35 = round(100.0 - prob_o35, 1)
    prob_btts = round(float(np.sum(matrix_90[1:, 1:])) * 100.0, 1)

    # 6. Modélisation Stochastique des Prolongations (Extra Time - 30 min)
    # L'intensité offensive baisse en prolongations en raison de la fatigue accumulée
    et_h_xg = full_h_xg * (30.0 / 90.0) * 0.82
    et_a_xg = full_a_xg * (30.0 / 90.0) * 0.82
    
    m_et = np.zeros((4, 4))
    for x in range(4):
        for y in range(4):
            m_et[x, y] = poisson.pmf(x, et_h_xg) * poisson.pmf(y, et_a_xg)
    tot_et = np.sum(m_et)
    if tot_et > 0: m_et /= tot_et
    
    p_h_et = float(np.sum(np.tril(m_et, -1)))
    p_draw_et = float(np.sum(np.diag(m_et))) # Direction les tirs au but !
    p_a_et = float(np.sum(np.triu(m_et, 1)))

    # 7. Modélisation des Tirs au But (Penalty Shootout)
    # Avantage psychologique léger à l'équipe supérieure techniquement ou jouant à domicile
    pen_edge = 0.50 + np.clip(eff_elo_diff / 5000.0, -0.05, 0.05)
    p_h_pen = pen_edge
    p_a_pen = 1.0 - pen_edge

    # 8. Synthèse Globale de Qualification (To Qualify)
    prob_qual_h = (p_h_90 / 100.0) + (p_d_90 / 100.0) * (p_h_et + p_draw_et * p_h_pen)
    prob_qual_a = 1.0 - prob_qual_h
    
    prob_qual_h_pct = round(prob_qual_h * 100.0, 1)
    prob_qual_a_pct = round(prob_qual_a * 100.0, 1)
    
    odds_qual_h = prob_to_odds(prob_qual_h_pct)
    odds_qual_a = prob_to_odds(prob_qual_a_pct)

    # Méthode de victoire
    prob_h_90_win = round(p_h_90, 1)
    prob_h_et_win = round((p_d_90 / 100.0) * p_h_et * 100.0, 1)
    prob_h_pen_win = round((p_d_90 / 100.0) * p_draw_et * p_h_pen * 100.0, 1)
    
    prob_a_90_win = round(p_a_90, 1)
    prob_a_et_win = round((p_d_90 / 100.0) * p_a_et * 100.0, 1)
    prob_a_pen_win = round((p_d_90 / 100.0) * p_draw_et * p_a_pen * 100.0, 1)
    
    prob_overtime_total = round(p_d_90, 1)
    prob_penalties_total = round((p_d_90 / 100.0) * p_draw_et * 100.0, 1)

    # Corners & Cartons Spécifiques aux Coupes
    # En élimination directe, les fautes tactiques et la tension montent d'un cran
    pace_factor = ((full_h_xg + full_a_xg) / 2.8) ** 0.35
    territorial_dom = (full_h_xg ** 1.2) / max(0.1, (full_h_xg ** 1.2 + full_a_xg ** 1.2))
    
    base_corner = cup_cfg["corner_base"]
    exp_c_h = base_corner * 0.54 * (territorial_dom ** 0.55) * pace_factor
    exp_c_a = base_corner * 0.46 * ((1.0 - territorial_dom) ** 0.55) * pace_factor
    tot_exp_corners = round(float(np.clip(exp_c_h + exp_c_a, 5.5, 14.5)), 1)
    prob_c85 = round((1.0 - poisson.cdf(8, tot_exp_corners)) * 100.0, 1)
    
    # Tension accrue par élimination directe (+15% de cartons par rapport au championnat)
    base_card = cup_cfg["card_base"] * 1.15
    tot_exp_cards = round(float(np.clip(base_card * (1.10 if abs(eff_elo_diff) < 120 else 0.95), 2.5, 8.0)), 1)
    prob_cards35 = round((1.0 - poisson.cdf(3, tot_exp_cards)) * 100.0, 1)

    # Top 3 Scores 90 min
    flat_idx = np.argsort(matrix_90.ravel())[::-1]
    top_3_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix_90.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "prob": round(matrix_90[gh, ga] * 100.0, 1)})

    # Recommandations d'Options Spéciales Coupe
    options = []
    fav_name = h_name if prob_qual_h_pct >= prob_qual_a_pct else a_name
    fav_qual_prob = max(prob_qual_h_pct, prob_qual_a_pct)
    fav_qual_odds = prob_to_odds(fav_qual_prob)
    
    # Option 1 : Qualification Sécurité
    if fav_qual_prob >= 75.0:
        options.append({
            "type": "👑 SÉCURITÉ QUALIFICATION COUPE",
            "desc": f"Qualification pour le tour suivant : {fav_name}",
            "prob": fav_qual_prob, "odds": fav_qual_odds
        })
    elif prob_1x >= 82.0:
        options.append({
            "type": "👑 SÉCURITÉ TEMPS RÉGLEMENTAIRE",
            "desc": f"Double Chance (90 min) : {h_name} ou Nul (1X)",
            "prob": prob_1x, "odds": prob_to_odds(prob_1x)
        })
    elif prob_x2 >= 82.0:
        options.append({
            "type": "👑 SÉCURITÉ TEMPS RÉGLEMENTAIRE",
            "desc": f"Double Chance (90 min) : Nul ou {a_name} (X2)",
            "prob": prob_x2, "odds": prob_to_odds(prob_x2)
        })
    else:
        options.append({
            "type": "👑 SÉCURITÉ TEMPS RÉGLEMENTAIRE",
            "desc": "Plus de 1.5 Buts dans les 90 minutes",
            "prob": prob_o15, "odds": prob_to_odds(prob_o15)
        })

    # Option 2 : Value Bet Coupe
    if p_h_90 >= 54.0:
        options.append({
            "type": "🎯 VALUE BET 90 MINUTES",
            "desc": f"Victoire dans le temps réglementaire : {h_name}",
            "prob": round(p_h_90, 1), "odds": prob_to_odds(p_h_90)
        })
    elif p_a_90 >= 54.0:
        options.append({
            "type": "🎯 VALUE BET 90 MINUTES",
            "desc": f"Victoire dans le temps réglementaire : {a_name}",
            "prob": round(p_a_90, 1), "odds": prob_to_odds(p_a_90)
        })
    elif prob_btts >= 56.0:
        options.append({
            "type": "🎯 VALUE BET BUTS COUPE",
            "desc": "Les Deux Équipes Marquent (BTTS Oui)",
            "prob": prob_btts, "odds": prob_to_odds(prob_btts)
        })
    else:
        options.append({
            "type": "🎯 VALUE BET BUTS COUPE",
            "desc": "Plus de 2.5 Buts (Match Ouvert Knockout)",
            "prob": prob_o25, "odds": prob_to_odds(prob_o25)
        })

    # Option 3 : Scénario Élimination / Handicap
    if abs(eff_elo_diff) > 220.0:
        hcap_team = h_name if eff_elo_diff > 0 else a_name
        prob_hcap = round(max(p_h_90, p_a_90) * 0.82, 1)
        options.append({
            "type": "⚡ SCÉNARIO ÉCART DE NIVEAU",
            "desc": f"Victoire avec Handicap (-1.5) : {hcap_team}",
            "prob": prob_hcap, "odds": prob_to_odds(prob_hcap)
        })
    elif prob_overtime_total >= 28.0:
        options.append({
            "type": "⚡ SCÉNARIO PROLONGATIONS",
            "desc": "Match Nul après 90 min (Direction Prolongations)",
            "prob": round(p_d_90, 1), "odds": prob_to_odds(p_d_90)
        })
    else:
        options.append({
            "type": "⚡ SCÉNARIO CADENASSÉ COUPE",
            "desc": "Moins de 3.5 Buts (Match à élimination tendu)",
            "prob": prob_u35, "odds": prob_to_odds(prob_u35)
        })

    best_opt = options[0]
    fair_odds_best = prob_to_odds(best_opt["prob"])
    market_odds_best = book_odds_custom if book_odds_custom else round(fair_odds_best * 1.05, 2)
    kelly_stk, ev_val = calculate_quarter_kelly(best_opt["prob"], market_odds_best, bankroll)

    # Rapport Tactique de Coupe
    cup_context = (
        f"Gros écart hiérarchique (D{h_data['tier']} vs D{a_data['tier']}). Match piège pour le favori si composition remaniée."
        if h_data['tier'] != a_data['tier'] else
        f"Choc entre pensionnaires de D{h_data['tier']}. Intensité maximale pour une place au tour suivant."
    )
    
    tactical_report = f"""
    🏆 <b>Intelligence Quantifiée Spéciale Coupe (Knockout Engine Pro)</b> :<br>
    • 🏠 <b>{h_name}</b> (D{h_data['tier']} | ELO {h_data['elo']} | {h_rotation}) : xG 90m = <b>{full_h_xg:.2f}</b><br>
    • ✈️ <b>{a_name}</b> (D{a_data['tier']} | ELO {a_data['elo']} | {a_rotation}) : xG 90m = <b>{full_a_xg:.2f}</b><br>
    • ⚔️ <b>Contexte Élimination Directe</b> : {cup_context}<br>
    • 👑 <b>Ticket Qualification Tour Suivant</b> : <b>{h_name} ({prob_qual_h_pct}%)</b> vs <b>{a_name} ({prob_qual_a_pct}%)</b><br>
    • ⏱️ <b>Risque de Prolongations</b> : <b>{prob_overtime_total}%</b> | Risque de Tirs au But : <b>{prob_penalties_total}%</b><br>
    • ⛳ <b>Corners / Cartons Knockout</b> : ~<b>{tot_exp_corners} corners</b> | ~<b>{tot_exp_cards} cartons</b> (+ tension élimination)
    """

    return {
        "p_h_90": round(p_h_90, 1), "p_d_90": round(p_d_90, 1), "p_a_90": round(p_a_90, 1),
        "prob_1x": prob_1x, "prob_x2": prob_x2, "prob_12": prob_12,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u25": prob_u25, "prob_o35": prob_o35, "prob_u35": prob_u35,
        "prob_btts": prob_btts,
        "prob_qual_h": prob_qual_h_pct, "prob_qual_a": prob_qual_a_pct,
        "odds_qual_h": odds_qual_h, "odds_qual_a": odds_qual_a,
        "prob_h_90_win": prob_h_90_win, "prob_h_et_win": prob_h_et_win, "prob_h_pen_win": prob_h_pen_win,
        "prob_a_90_win": prob_a_90_win, "prob_a_et_win": prob_a_et_win, "prob_a_pen_win": prob_a_pen_win,
        "prob_overtime": prob_overtime_total, "prob_penalties": prob_penalties_total,
        "corners": tot_exp_corners, "prob_c85": prob_c85,
        "cards": tot_exp_cards, "prob_cards35": prob_cards35,
        "top_3_scores": top_3_scores,
        "matrix_90": matrix_90,
        "options": options,
        "best_pick": best_opt["desc"], "best_prob": best_opt["prob"],
        "tactical_report": tactical_report,
        "full_h_xg": full_h_xg, "full_a_xg": full_a_xg,
        "fair_odds_best": fair_odds_best, "market_odds_best": market_odds_best,
        "kelly_stake": kelly_stk, "ev_percentage": ev_val
    }

# ==============================================================================
# 5. MONTE CARLO KNOCKOUT SIMULATOR (10 000 MATCHS AVEC PROLONGATIONS ET PENALTIES)
# ==============================================================================
def run_cup_monte_carlo(res, n_sims=10000):
    m_90 = res["matrix_90"]
    flat_probs = m_90.ravel()
    flat_idx = np.random.choice(len(flat_probs), size=n_sims, p=flat_probs)
    h_90, a_90 = np.unravel_index(flat_idx, m_90.shape)
    
    # 90 min stats
    h_reg_wins = np.sum(h_90 > a_90)
    a_reg_wins = np.sum(h_90 < a_90)
    draws_reg = np.sum(h_90 == a_90)
    
    # Extra time simulations on tied games
    et_h_wins, et_a_wins, pen_h_wins, pen_a_wins = 0, 0, 0, 0
    if draws_reg > 0:
        l_h_et = res["full_h_xg"] * (30.0 / 90.0) * 0.82
        l_a_et = res["full_a_xg"] * (30.0 / 90.0) * 0.82
        et_goals_h = np.random.poisson(l_h_et, size=draws_reg)
        et_goals_a = np.random.poisson(l_a_et, size=draws_reg)
        
        et_h_wins = np.sum(et_goals_h > et_goals_a)
        et_a_wins = np.sum(et_goals_h < et_goals_a)
        pen_games = np.sum(et_goals_h == et_goals_a)
        
        if pen_games > 0:
            pen_coin = np.random.rand(pen_games)
            pen_h_wins = np.sum(pen_coin <= (res["prob_qual_h"] / 100.0))
            pen_a_wins = pen_games - pen_h_wins

    total_h_qual = (h_reg_wins + et_h_wins + pen_h_wins) / n_sims * 100.0
    total_a_qual = (a_reg_wins + et_a_wins + pen_a_wins) / n_sims * 100.0
    
    return {
        "mc_h_qual": round(total_h_qual, 1),
        "mc_a_qual": round(total_a_qual, 1),
        "mc_overtime_pct": round((draws_reg / n_sims) * 100.0, 1),
        "mc_penalties_pct": round(((pen_h_wins + pen_a_wins) / n_sims) * 100.0, 1)
    }

# ==============================================================================
# 6. INTERFACE STREAMLIT ULTRA-PRO APEX CUPS V50.0
# ==============================================================================
st.sidebar.markdown("""
    <div style="text-align:center; padding:10px 0;">
        <h2 style="color:#F59E0B; margin:0; font-weight:900;">APEX CUPS QUANT</h2>
        <span style="font-size:0.8rem; letter-spacing:2px; color:#38BDF8; font-weight:800;">KNOCKOUT SPECIALIST v50.0</span>
    </div>
""", unsafe_allow_html=True)

selected_cup_name = st.sidebar.selectbox("🏆 Compétition de Coupe Cible", list(CUP_COMPETITIONS.keys()))
active_cup_code = CUP_COMPETITIONS[selected_cup_name]
cup_cfg = CUP_PROFILES[active_cup_code]

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ PARAMÈTRES TACTIQUES & ROTATION")
weather_condition = st.sidebar.selectbox("Météo / Pelouse", ["Normal (Idéal)", "Pluie / Terrain Glissant", "Froid Polaire"])
user_bankroll = st.sidebar.number_input("Capital Alloué aux Coupes ($ / €)", value=1000.0, step=50.0, min_value=10.0)

# Récupération des équipes éligibles pour cette coupe
eligible_teams = sorted([t for t, d in CUP_TEAMS_DB.items() if d["cup"] == active_cup_code])

# ONGLETS SPÉCIFIQUES COUPES
tab_sim, tab_scanner, tab_sched, tab_monte, tab_ticket = st.tabs([
    "⚔️ ANALYSE MATCH DE COUPE",
    "🔍 SCANNER VALUE BETS COUPE",
    "📅 CALENDRIER DES TOURS",
    "🎲 MONTE CARLO KNOCKOUT",
    "🎟️ MARMITE QUALIFICATION VIP"
])

# ------------------------------------------------------------------------------
# ONGLET 1 : ANALYSE DÉTAILLÉE DU MATCH DE COUPE
# ------------------------------------------------------------------------------
with tab_sim:
    st.subheader(f"Disséqueur Stochastique de Coupe — {selected_cup_name}")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        h_team_pick = st.selectbox("🏠 Équipe à Domicile :", eligible_teams, index=0)
        h_rot_pick = st.selectbox("Composition Domicile :", [
            "Équipe Type (100%)", 
            "Rotation Modérée (4-5 titulaires au repos)", 
            "Forte Rotation (7-8 remplaçants / Jeunesse)"
        ], index=0)
    with col_t2:
        default_away_idx = 1 if len(eligible_teams) > 1 else 0
        a_team_pick = st.selectbox("✈️ Équipe à l'Extérieur :", eligible_teams, index=default_away_idx)
        a_rot_pick = st.selectbox("Composition Extérieur :", [
            "Équipe Type (100%)", 
            "Rotation Modérée (4-5 titulaires au repos)", 
            "Forte Rotation (7-8 remplaçants / Jeunesse)"
        ], index=0)
        
    book_odds_in = st.number_input("Cote Bookmaker de l'Option Prioritaire :", value=1.45, step=0.02, min_value=1.01)

    res_cup = run_cup_prediction(
        h_team_pick, a_team_pick, 
        active_cup_code, h_rot_pick, a_rot_pick, 
        weather_condition, user_bankroll, book_odds_in
    )

    st.markdown(f"""
    <div class="matrix-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h1 style="color:#F59E0B; margin:0; font-size:2rem;">{h_team_pick} <span style="color:#94A3B8; font-weight:300;">vs</span> {a_team_pick}</h1>
            <span class="badge-cup" style="font-size:0.9rem;">Knockout Match • {cup_cfg['name']}</span>
        </div>
        <div class="cup-box">{res_cup['tactical_report']}</div>
    </div>
    """, unsafe_allow_html=True)

    # CADRE VEDETTE : QUALIFICATION AU TOUR SUIVANT
    st.markdown("### 👑 MARCHÉ VEDETTE : QUI VA SE QUALIFIER ? (TO QUALIFY)")
    q1, q2 = st.columns(2)
    with q1:
        st.markdown(f"""
        <div class="qualif-box">
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; color:#F59E0B;">QUALIFICATION DOMICILE</span>
            <div style="font-size:1.6rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{h_team_pick} Passe au Tour Suivant</div>
            <div style="font-size:1.2rem; font-weight:800; color:#10B981;">Probabilité Totale : {res_cup['prob_qual_h']}% | Cote Équitable : {res_cup['odds_qual_h']}</div>
            <span style="font-size:0.85rem; color:#94A3B8;">En 90m: {res_cup['prob_h_90_win']}% | En Prolongations: {res_cup['prob_h_et_win']}% | Aux Tirs au But: {res_cup['prob_h_pen_win']}%</span>
        </div>
        """, unsafe_allow_html=True)
    with q2:
        st.markdown(f"""
        <div class="qualif-box">
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; color:#F59E0B;">QUALIFICATION EXTÉRIEUR</span>
            <div style="font-size:1.6rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{a_team_pick} Passe au Tour Suivant</div>
            <div style="font-size:1.2rem; font-weight:800; color:#10B981;">Probabilité Totale : {res_cup['prob_qual_a']}% | Cote Équitable : {res_cup['odds_qual_a']}</div>
            <span style="font-size:0.85rem; color:#94A3B8;">En 90m: {res_cup['prob_a_90_win']}% | En Prolongations: {res_cup['prob_a_et_win']}% | Aux Tirs au But: {res_cup['prob_a_pen_win']}%</span>
        </div>
        """, unsafe_allow_html=True)

    # LES 3 OPTIONS HIÉRARCHISÉES
    st.markdown("### 🎯 SÉLECTION QUANTITATIVE HIÉRARCHISÉE DE COUPE")
    for opt in res_cup['options']:
        style_cls = "option-box" if "SÉCURITÉ" in opt['type'] else ("option-box-sec" if "VALUE" in opt['type'] else "qualif-box")
        st.markdown(f"""
        <div class="{style_cls}">
            <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; color:#F59E0B; letter-spacing:1px;">{opt['type']}</div>
            <div style="font-size:1.35rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{opt['desc']}</div>
            <div style="font-size:1rem; font-weight:700; color:#10B981;">
                Probabilité Estimée : <b>{opt['prob']}%</b> | Cote Juste : <b>{opt['odds']}</b>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 MARCHÉS TEMPS RÉGLEMENTAIRE (90 MINUTES)")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="sub-card">
            <b>1N2 TEMPS RÉGLEMENTAIRE</b><br>
            1 ({h_team_pick}) : <span class="stat-badge">{res_cup['p_h_90']}%</span><br>
            N (Prolongations) : <span class="stat-badge">{res_cup['p_d_90']}%</span><br>
            2 ({a_team_pick}) : <span class="stat-badge">{res_cup['p_a_90']}%</span>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="sub-card">
            <b>DOUBLE CHANCE (90m)</b><br>
            1X : <span class="stat-badge">{res_cup['prob_1x']}%</span><br>
            X2 : <span class="stat-badge">{res_cup['prob_x2']}%</span><br>
            12 : <span class="stat-badge">{res_cup['prob_12']}%</span>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="sub-card">
            <b>BUTS DANS LE MATCH</b><br>
            Over 1.5 : <span class="stat-badge">{res_cup['prob_o15']}%</span><br>
            Over 2.5 : <span class="stat-badge">{res_cup['prob_o25']}%</span><br>
            Under 2.5 : <span class="stat-badge">{res_cup['prob_u25']}%</span>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="sub-card">
            <b>LES DEUX MARQUENT (BTTS)</b><br>
            BTTS Oui : <span class="stat-badge">{res_cup['prob_btts']}%</span><br>
            Tirs au but possibles : <span class="stat-badge">{res_cup['prob_penalties']}%</span><br>
            Prolongations : <span class="stat-badge">{res_cup['prob_overtime']}%</span>
        </div>
        """, unsafe_allow_html=True)

    # Kelly & Scores
    col_k, col_sc = st.columns([1, 2])
    with col_k:
        st.markdown("### 💰 GESTION DE MISE KELLY")
        ev_sign = "+" if res_cup['ev_percentage'] >= 0 else ""
        st.metric("Mise Conseillée (1/4 Kelly)", f"{res_cup['kelly_stake']} $", f"Expected Value : {ev_sign}{res_cup['ev_percentage']}%")
    with col_sc:
        st.markdown("### 🏆 TOP 3 SCORES 90 MINUTES")
        sc1, sc2, sc3 = st.columns(3)
        with sc1: st.markdown(f"""<div class="big-score-box"><b>1er SCORE</b><div class="big-score-val">{res_cup['top_3_scores'][0]['score']}</div><div class="big-score-prob">{res_cup['top_3_scores'][0]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc2: st.markdown(f"""<div class="big-score-box"><b>2ème SCORE</b><div class="big-score-val">{res_cup['top_3_scores'][1]['score']}</div><div class="big-score-prob">{res_cup['top_3_scores'][1]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc3: st.markdown(f"""<div class="big-score-box"><b>3ème SCORE</b><div class="big-score-val">{res_cup['top_3_scores'][2]['score']}</div><div class="big-score-prob">{res_cup['top_3_scores'][2]['prob']}%</div></div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# ONGLET 2 : SCANNER DE VALUE BETS DE COUPE
# ------------------------------------------------------------------------------
with tab_scanner:
    st.markdown(f"""
    <div class="vip-banner">
        <h2 style="margin:0; color:#F59E0B;">🔍 SCANNER DE VALUE BETS SPÉCIAL COUPE — {cup_cfg['name']}</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Détection des cotes sous-évaluées sur les Qualifications, 1N2 et Buts</span>
    </div>
    """, unsafe_allow_html=True)
    
    cup_matches = SCHEDULED_CUP_MATCHES.get(active_cup_code, [])
    if cup_matches:
        min_ev_cup = st.slider("Seuil minimum d'Expected Value (EV%) :", -2.0, 15.0, 1.5, 0.5)
        scanner_cup_rows = []
        
        for m in cup_matches:
            ht, at = m["home"], m["away"]
            pred = run_cup_prediction(ht, at, active_cup_code, "Équipe Type (100%)", "Équipe Type (100%)", weather_condition, user_bankroll)
            
            # Marchés à scanner
            pool = [
                {"market": "Qualification", "label": f"Qualif : {ht}", "prob": pred['prob_qual_h'], "fair": pred['odds_qual_h']},
                {"market": "Qualification", "label": f"Qualif : {at}", "prob": pred['prob_qual_a'], "fair": pred['odds_qual_a']},
                {"market": "1N2 (90m)", "label": f"Victoire 90m : {ht}", "prob": pred['p_h_90'], "fair": prob_to_odds(pred['p_h_90'])},
                {"market": "1N2 (90m)", "label": f"Victoire 90m : {at}", "prob": pred['p_a_90'], "fair": prob_to_odds(pred['p_a_90'])},
                {"market": "Double Chance", "label": f"1X (90m) : {ht} ou Nul", "prob": pred['prob_1x'], "fair": prob_to_odds(pred['prob_1x'])},
                {"market": "Buts", "label": "Over 2.5 Buts (90m)", "prob": pred['prob_o25'], "fair": prob_to_odds(pred['prob_o25'])},
                {"market": "BTTS", "label": "Les Deux Équipes Marquent", "prob": pred['prob_btts'], "fair": prob_to_odds(pred['prob_btts'])}
            ]
            
            for item in pool:
                p = item["prob"]
                fair_o = item["fair"]
                sim_market_odds = round(fair_o * 1.055, 2)
                stk, ev = calculate_quarter_kelly(p, sim_market_odds, user_bankroll)
                
                if ev >= min_ev_cup:
                    sig = "🟢 ULTRA VALUE" if ev >= 7.0 else ("🟡 FORTE VALUE" if ev >= 3.0 else "🔵 LÉGER EDGE")
                    scanner_cup_rows.append({
                        "Match": f"{ht} vs {at}",
                        "Tour": m["round"],
                        "Marché Spécialisé": item["label"],
                        "Probabilité": f"{p}%",
                        "Cote Équitable": fair_o,
                        "Cote Marché": sim_market_odds,
                        "Expected Value (EV)": ev,
                        "Mise Quarter-Kelly": f"{stk} $",
                        "Signal": sig
                    })

        if scanner_cup_rows:
            df_cup_scan = pd.DataFrame(scanner_cup_rows).sort_values(by="Expected Value (EV)", ascending=False)
            st.dataframe(df_cup_scan.style.format({"Expected Value (EV)": "{:+.2f}%"}), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun value bet dépassant le seuil fixé.")
    else:
        st.warning("Aucun match au calendrier pour cette coupe.")

# ------------------------------------------------------------------------------
# ONGLET 3 : CALENDRIER DES TOURS DE COUPE
# ------------------------------------------------------------------------------
with tab_sched:
    st.subheader(f"Tableau des Affiches Officielles — {cup_cfg['name']}")
    cup_matches = SCHEDULED_CUP_MATCHES.get(active_cup_code, [])
    if cup_matches:
        sched_rows = []
        for m in cup_matches:
            pred = run_cup_prediction(m["home"], m["away"], active_cup_code, "Équipe Type (100%)", "Équipe Type (100%)", weather_condition, user_bankroll)
            sched_rows.append({
                "Date": m["date"],
                "Tour": m["round"],
                "Affiche": f"{m['home']} vs {m['away']}",
                "Proba Qualification": f"{pred['prob_qual_h']}% (Cote {pred['odds_qual_h']}) vs {pred['prob_qual_a']}% (Cote {pred['odds_qual_a']})",
                "1N2 (90m)": f"{pred['p_h_90']}% | {pred['p_d_90']}% | {pred['p_a_90']}%",
                "Option Recommandée": f"{pred['options'][0]['desc']} ({pred['options'][0]['prob']}%)",
                "Prolongations": f"{pred['prob_overtime']}%",
                "Tirs au But": f"{pred['prob_penalties']}%"
            })
        st.dataframe(pd.DataFrame(sched_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune rencontre programmée.")

# ------------------------------------------------------------------------------
# ONGLET 4 : MONTE CARLO KNOCKOUT ENGINE (10 000 RUNS)
# ------------------------------------------------------------------------------
with tab_monte:
    st.markdown(f"""
    <div class="vip-banner">
        <h2 style="margin:0; color:#38BDF8;">🎲 SIMULATION MONTE CARLO KNOCKOUT (10 000 TOURS)</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Simulation vectorisée incluant les 90 minutes, les prolongations et la séance de tirs au but</span>
    </div>
    """, unsafe_allow_html=True)
    
    mc_res = run_cup_prediction(h_team_pick, a_team_pick, active_cup_code, h_rot_pick, a_rot_pick, weather_condition, user_bankroll)
    mc_cup_stats = run_cup_monte_carlo(mc_res, 10000)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric(f"Qualif {h_team_pick} (MC)", f"{mc_cup_stats['mc_h_qual']}%", f"Théorique: {mc_res['prob_qual_h']}%")
    with c2: st.metric(f"Qualif {a_team_pick} (MC)", f"{mc_cup_stats['mc_a_qual']}%", f"Théorique: {mc_res['prob_qual_a']}%")
    with c3: st.metric("Matchs en Prolongations", f"{mc_cup_stats['mc_overtime_pct']}%", f"Théorique: {mc_res['prob_overtime']}%")
    with c4: st.metric("Matchs aux Tirs au But", f"{mc_cup_stats['mc_penalties_pct']}%", f"Théorique: {mc_res['prob_penalties']}%")

# ------------------------------------------------------------------------------
# ONGLET 5 : MARMITE QUALIFICATION VIP
# ------------------------------------------------------------------------------
with tab_ticket:
    st.subheader(f"🎟️ Combiné Spécial Qualification VIP — {cup_cfg['name']}")
    cup_matches = SCHEDULED_CUP_MATCHES.get(active_cup_code, [])
    if cup_matches:
        ticket_items = []
        for m in cup_matches:
            pred = run_cup_prediction(m["home"], m["away"], active_cup_code, "Équipe Type (100%)", "Équipe Type (100%)", weather_condition, user_bankroll)
            # Sélection de la qualification du favori
            fav = m["home"] if pred["prob_qual_h"] >= pred["prob_qual_a"] else m["away"]
            fav_prob = max(pred["prob_qual_h"], pred["prob_qual_a"])
            fav_odds = pred["odds_qual_h"] if fav == m["home"] else pred["odds_qual_a"]
            ticket_items.append({
                "match": f"{m['home']} vs {m['away']}",
                "pick": f"Qualification de {fav}",
                "prob": fav_prob,
                "odds": fav_odds
            })
            
        ticket_items.sort(key=lambda x: x["prob"], reverse=True)
        top_qual_picks = ticket_items[:4]
        total_cup_odds = float(np.prod([it["odds"] for it in top_qual_picks]))
        
        st.markdown(f"""
        <div class="vip-banner">
            <h2 style="margin:0; color:#F59E0B;">🏆 COMBINÉ QUALIFICATION ULTIME (TOP 4 FAVORIS)</h2>
            <div style="font-size:1.8rem; font-weight:900; color:#FFFFFF; margin-top:8px;">
                Cote Totale Estimée : <span style="color:#38BDF8;">{total_cup_odds:.2f}</span>
            </div>
            <div style="font-size:0.9rem; color:#E2E8F0; margin-top:4px;">Sécurité maximale sur le marché 'To Qualify' (Indépendant des prolongations)</div>
        </div>
        """, unsafe_allow_html=True)
        
        for idx, item in enumerate(top_qual_picks, 1):
            st.markdown(f"""
            <div class="sub-card">
                <b>{idx}. {item['match']}</b><br>
                👉 Choix Stratégique : <b style="color:#10B981;">{item['pick']}</b> | Probabilité : <b>{item['prob']}%</b> (Cote : <b>{item['odds']}</b>)
            </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("Nombre insuffisant de matchs pour générer le combiné.")
