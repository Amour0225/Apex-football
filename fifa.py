import streamlit as st
import numpy as np
from scipy.stats import poisson, nbinom
import pandas as pd
from datetime import datetime
import math
import copy
import re
import requests

# ==============================================================================
# 1. CONFIGURATION & DESIGN V52.0 APEX CUPS QUANT AUTONOMOUS PRO
# ==============================================================================
st.set_page_config(
    page_title="Apex Cups Quant v52.0 Autonomous Pro",
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
    .sync-box {
        background: #0D1527; border: 1.5px solid #38BDF8; border-radius: 14px; padding: 16px; margin-bottom: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. PROFILS DES COUPES & CALENDRIERS SYNCHRONISÉS
# ==============================================================================
CUP_COMPETITIONS = {
    "Angleterre : Coupe de la Ligue 🇬🇧 (Carabao Cup)": "EFL_CUP",
    "Allemagne : Coupe d'Allemagne 🇩🇪 (DFB-Pokal)": "DFB_POKAL",
    "Espagne : Coupe du Roi 🇪🇸 (Copa del Rey)": "COPA_DEL_REY"
}

CUP_PROFILES = {
    "EFL_CUP": {
        "name": "Coupe de la Ligue Anglaise (Carabao Cup)",
        "country": "Angleterre 🇬🇧",
        "api_league_id": 48,
        "avg_g_h": 1.62, "avg_g_a": 1.32, "rho": -0.105,
        "card_base": 3.7, "corner_base": 10.2, "dispersion": 10.2
    },
    "DFB_POKAL": {
        "name": "DFB-Pokal (Coupe d'Allemagne)",
        "country": "Allemagne 🇩🇪",
        "api_league_id": 529,
        "avg_g_h": 1.76, "avg_g_a": 1.48, "rho": -0.090,
        "card_base": 4.1, "corner_base": 10.0, "dispersion": 11.0
    },
    "COPA_DEL_REY": {
        "name": "Copa del Rey (Coupe du Roi)",
        "country": "Espagne 🇪🇸",
        "api_league_id": 143,
        "avg_g_h": 1.52, "avg_g_a": 1.18, "rho": -0.120,
        "card_base": 4.9, "corner_base": 9.5, "dispersion": 9.4
    }
}

# BASE INITIALE OFFICIELLE DES AFFICHES ET COTES RÉELLES DU TOUR
SCHEDULED_CUP_MATCHES = {
    "EFL_CUP": [
        {"home": "Bradford City", "away": "Peterborough United", "date": "27.10 19:45", "round": "8èmes de finale", "odds_1": 1.70, "odds_x": 4.04, "odds_2": 4.60},
        {"home": "Fleetwood Town", "away": "Arsenal", "date": "27.10 20:00", "round": "8èmes de finale", "odds_1": 30.00, "odds_x": 11.00, "odds_2": 1.075},
        {"home": "Manchester City", "away": "Brighton & Hove Albion", "date": "28.10 19:30", "round": "8èmes de finale", "odds_1": 1.632, "odds_x": 4.40, "odds_2": 4.68},
        {"home": "Bournemouth", "away": "Aston Villa", "date": "28.10 19:45", "round": "8èmes de finale", "odds_1": 2.295, "odds_x": 3.52, "odds_2": 3.008},
        {"home": "Sunderland", "away": "Brentford", "date": "28.10 19:45", "round": "8èmes de finale", "odds_1": 3.46, "odds_x": 3.48, "odds_2": 2.096},
        {"home": "Fulham", "away": "Crystal Palace", "date": "28.10 19:45", "round": "8èmes de finale", "odds_1": 1.904, "odds_x": 3.78, "odds_2": 3.78},
        {"home": "Liverpool", "away": "Chelsea", "date": "28.10 20:00", "round": "8èmes de finale", "odds_1": 2.344, "odds_x": 3.76, "odds_2": 2.775},
        {"home": "Everton", "away": "Newcastle United", "date": "29.10 19:45", "round": "8èmes de finale", "odds_1": 2.285, "odds_x": 3.38, "odds_2": 3.136}
    ],
    "DFB_POKAL": [
        {"home": "VfL Bochum", "away": "1. FSV Mayence 05", "date": "27.10 17:00", "round": "2ème Tour (16èmes)", "odds_1": 5.02, "odds_x": 4.15, "odds_2": 1.59},
        {"home": "Hambourg", "away": "Eintracht Frankfurt", "date": "27.10 17:00", "round": "2ème Tour (16èmes)", "odds_1": 3.155, "odds_x": 3.68, "odds_2": 2.08},
        {"home": "Rot-Weiss Essen", "away": "RB Leipzig", "date": "27.10 17:00", "round": "2ème Tour (16èmes)", "odds_1": 14.50, "odds_x": 8.10, "odds_2": 1.132},
        {"home": "Sonnenhof", "away": "Augsbourg", "date": "27.10 17:00", "round": "2ème Tour (16èmes)", "odds_1": 8.40, "odds_x": 6.10, "odds_2": 1.27},
        {"home": "Borussia Dortmund", "away": "Werder Bremen", "date": "27.10 19:45", "round": "2ème Tour (16èmes)", "odds_1": 1.395, "odds_x": 5.05, "odds_2": 7.10},
        {"home": "Borussia M'gladbach", "away": "Karlsruher", "date": "27.10 19:45", "round": "2ème Tour (16èmes)", "odds_1": 1.35, "odds_x": 5.30, "odds_2": 7.09},
        {"home": "Cologne", "away": "Union Berlin", "date": "27.10 19:45", "round": "2ème Tour (16èmes)", "odds_1": 1.80, "odds_x": 3.78, "odds_2": 4.03},
        {"home": "Elversberg", "away": "Darmstadt 98", "date": "27.10 19:45", "round": "2ème Tour (16èmes)", "odds_1": 1.39, "odds_x": 5.00, "odds_2": 6.65},
        {"home": "Dynamo Dresden", "away": "Schalke 04", "date": "28.10 17:00", "round": "2ème Tour (16èmes)", "odds_1": 3.345, "odds_x": 3.56, "odds_2": 2.04},
        {"home": "Paderborn 07", "away": "VfB Stuttgart", "date": "28.10 17:00", "round": "2ème Tour (16èmes)", "odds_1": 5.47, "odds_x": 4.45, "odds_2": 1.51},
        {"home": "SSV Jeddeloh", "away": "Hertha BSC", "date": "28.10 17:00", "round": "2ème Tour (16èmes)", "odds_1": 25.00, "odds_x": 13.50, "odds_2": 1.041},
        {"home": "Fribourg", "away": "VfL Wolfsburg", "date": "28.10 17:00", "round": "2ème Tour (16èmes)", "odds_1": 1.49, "odds_x": 4.55, "odds_2": 5.57},
        {"home": "Bayern Munich", "away": "1. Magdeburg", "date": "28.10 19:45", "round": "2ème Tour (16èmes)", "odds_1": 1.032, "odds_x": 15.00, "odds_2": 41.00},
        {"home": "Bayer 04 Leverkusen", "away": "Nurnberg", "date": "28.10 19:45", "round": "2ème Tour (16èmes)", "odds_1": 1.139, "odds_x": 8.10, "odds_2": 13.50},
        {"home": "Hanovre 96", "away": "Kaiserslautern", "date": "28.10 19:45", "round": "2ème Tour (16èmes)", "odds_1": 2.28, "odds_x": 3.60, "odds_2": 2.831},
        {"home": "Holstein Kiel", "away": "TSG 1899 Hoffenheim", "date": "28.10 19:45", "round": "2ème Tour (16èmes)", "odds_1": 5.66, "odds_x": 4.70, "odds_2": 1.47}
    ],
    "COPA_DEL_REY": [
        {"home": "Cuarte", "away": "Gérone", "date": "27.10 17:30", "round": "1er Tour Principal", "odds_1": 17.50, "odds_x": 6.60, "odds_2": 1.153},
        {"home": "CF Calamocha", "away": "CE Europa", "date": "27.10 18:00", "round": "1er Tour Principal", "odds_1": 4.31, "odds_x": 3.70, "odds_2": 1.76},
        {"home": "Sestao River Club", "away": "Espanyol", "date": "27.10 18:00", "round": "1er Tour Principal", "odds_1": 6.57, "odds_x": 4.20, "odds_2": 1.47},
        {"home": "UD Pinatar", "away": "Elche", "date": "27.10 18:00", "round": "1er Tour Principal", "odds_1": 25.00, "odds_x": 14.70, "odds_2": 1.034},
        {"home": "UD Castellonense", "away": "UD Almeria", "date": "27.10 18:45", "round": "1er Tour Principal", "odds_1": 7.41, "odds_x": 4.33, "odds_2": 1.42},
        {"home": "Atlético Tordesillas", "away": "Mirandes", "date": "27.10 19:00", "round": "1er Tour Principal", "odds_1": 4.85, "odds_x": 3.82, "odds_2": 1.66},
        {"home": "Gimnastica Segoviana", "away": "Cultural Leonesa", "date": "27.10 19:00", "round": "1er Tour Principal", "odds_1": 3.13, "odds_x": 3.48, "odds_2": 2.16},
        {"home": "UD Llanera", "away": "SD Ponferradina", "date": "27.10 19:00", "round": "1er Tour Principal", "odds_1": 4.94, "odds_x": 3.90, "odds_2": 1.635},
        {"home": "RSD Alcalá", "away": "UD Las Palmas", "date": "27.10 19:00", "round": "1er Tour Principal", "odds_1": 5.98, "odds_x": 4.15, "odds_2": 1.51},
        {"home": "Ciudad de Lucena", "away": "Rayo Majadahonda", "date": "27.10 19:00", "round": "1er Tour Principal", "odds_1": 3.285, "odds_x": 3.52, "odds_2": 2.08},
        {"home": "Don Benito", "away": "Extremadura", "date": "27.10 19:30", "round": "1er Tour Principal", "odds_1": 3.58, "odds_x": 3.56, "odds_2": 1.96},
        {"home": "CE Manresa", "away": "UE Sant Andreu", "date": "27.10 19:30", "round": "1er Tour Principal", "odds_1": 3.52, "odds_x": 3.50, "odds_2": 2.00},
        {"home": "Arosa", "away": "Pontevedra", "date": "27.10 20:00", "round": "1er Tour Principal", "odds_1": 4.27, "odds_x": 3.75, "odds_2": 1.76},
        {"home": "CD Atletico Paso", "away": "Cordoue", "date": "27.10 20:00", "round": "1er Tour Principal", "odds_1": 6.57, "odds_x": 4.30, "odds_2": 1.46},
        {"home": "CE Manacor", "away": "Villarreal", "date": "27.10 20:00", "round": "1er Tour Principal", "odds_1": 38.00, "odds_x": 13.70, "odds_2": 1.025},
        {"home": "Recreativo de Huelva", "away": "Rayo Vallecano", "date": "27.10 20:00", "round": "1er Tour Principal", "odds_1": 6.52, "odds_x": 4.15, "odds_2": 1.48},
        {"home": "Sporting Alcazar", "away": "Málaga", "date": "27.10 20:00", "round": "1er Tour Principal", "odds_1": 26.00, "odds_x": 21.00, "odds_2": 1.025},
        {"home": "CD Tudelano", "away": "Real Zaragoza", "date": "27.10 20:00", "round": "1er Tour Principal", "odds_1": 5.32, "odds_x": 3.84, "odds_2": 1.61}
    ]
}

# BASE CURÉE DES CLUBS MAJEURS ET DIVISIONNAIRES
CUP_TEAMS_DB = {
    # ANGLETERRE (Carabao Cup)
    "Bradford City": {"tier": 4, "elo": 1350, "att": 1.30, "def": 1.35},
    "Peterborough United": {"tier": 3, "elo": 1460, "att": 1.55, "def": 1.30},
    "Fleetwood Town": {"tier": 4, "elo": 1310, "att": 1.15, "def": 1.55},
    "Arsenal": {"tier": 1, "elo": 1980, "att": 2.25, "def": 0.82},
    "Manchester City": {"tier": 1, "elo": 2040, "att": 2.45, "def": 0.85},
    "Brighton & Hove Albion": {"tier": 1, "elo": 1780, "att": 1.85, "def": 1.35},
    "Bournemouth": {"tier": 1, "elo": 1730, "att": 1.65, "def": 1.45},
    "Aston Villa": {"tier": 1, "elo": 1880, "att": 2.00, "def": 1.10},
    "Sunderland": {"tier": 2, "elo": 1580, "att": 1.55, "def": 1.30},
    "Brentford": {"tier": 1, "elo": 1740, "att": 1.70, "def": 1.40},
    "Fulham": {"tier": 1, "elo": 1730, "att": 1.55, "def": 1.35},
    "Crystal Palace": {"tier": 1, "elo": 1720, "att": 1.45, "def": 1.35},
    "Liverpool": {"tier": 1, "elo": 1995, "att": 2.30, "def": 0.90},
    "Chelsea": {"tier": 1, "elo": 1870, "att": 2.05, "def": 1.15},
    "Everton": {"tier": 1, "elo": 1690, "att": 1.35, "def": 1.40},
    "Newcastle United": {"tier": 1, "elo": 1850, "att": 1.95, "def": 1.15},
    "Tottenham": {"tier": 1, "elo": 1860, "att": 2.10, "def": 1.30},
    "Manchester United": {"tier": 1, "elo": 1820, "att": 1.75, "def": 1.25},
    "Leicester City": {"tier": 1, "elo": 1670, "att": 1.40, "def": 1.65},

    # ALLEMAGNE (DFB-Pokal)
    "VfL Bochum": {"tier": 1, "elo": 1620, "att": 1.30, "def": 1.85},
    "1. FSV Mayence 05": {"tier": 1, "elo": 1710, "att": 1.55, "def": 1.35},
    "Hambourg": {"tier": 2, "elo": 1580, "att": 1.65, "def": 1.40},
    "Eintracht Frankfurt": {"tier": 1, "elo": 1790, "att": 1.90, "def": 1.35},
    "Rot-Weiss Essen": {"tier": 3, "elo": 1340, "att": 1.20, "def": 1.65},
    "RB Leipzig": {"tier": 1, "elo": 1910, "att": 2.25, "def": 0.95},
    "Sonnenhof": {"tier": 5, "elo": 1180, "att": 1.00, "def": 1.95},
    "Augsbourg": {"tier": 1, "elo": 1690, "att": 1.50, "def": 1.45},
    "Borussia Dortmund": {"tier": 1, "elo": 1890, "att": 2.20, "def": 1.15},
    "Werder Bremen": {"tier": 1, "elo": 1680, "att": 1.45, "def": 1.55},
    "Borussia M'gladbach": {"tier": 1, "elo": 1710, "att": 1.65, "def": 1.50},
    "Karlsruher": {"tier": 2, "elo": 1540, "att": 1.45, "def": 1.50},
    "Cologne": {"tier": 2, "elo": 1600, "att": 1.60, "def": 1.35},
    "Union Berlin": {"tier": 1, "elo": 1720, "att": 1.35, "def": 1.20},
    "Elversberg": {"tier": 2, "elo": 1520, "att": 1.45, "def": 1.50},
    "Darmstadt 98": {"tier": 2, "elo": 1530, "att": 1.50, "def": 1.60},
    "Dynamo Dresden": {"tier": 3, "elo": 1390, "att": 1.35, "def": 1.45},
    "Schalke 04": {"tier": 2, "elo": 1540, "att": 1.50, "def": 1.65},
    "Paderborn 07": {"tier": 2, "elo": 1550, "att": 1.55, "def": 1.45},
    "VfB Stuttgart": {"tier": 1, "elo": 1830, "att": 2.05, "def": 1.25},
    "SSV Jeddeloh": {"tier": 4, "elo": 1220, "att": 1.05, "def": 1.85},
    "Hertha BSC": {"tier": 2, "elo": 1590, "att": 1.60, "def": 1.45},
    "Fribourg": {"tier": 1, "elo": 1760, "att": 1.65, "def": 1.30},
    "VfL Wolfsburg": {"tier": 1, "elo": 1710, "att": 1.55, "def": 1.50},
    "Bayern Munich": {"tier": 1, "elo": 2020, "att": 2.75, "def": 0.88},
    "1. Magdeburg": {"tier": 2, "elo": 1530, "att": 1.40, "def": 1.55},
    "Bayer 04 Leverkusen": {"tier": 1, "elo": 1960, "att": 2.40, "def": 0.95},
    "Nurnberg": {"tier": 2, "elo": 1530, "att": 1.45, "def": 1.55},
    "Hanovre 96": {"tier": 2, "elo": 1580, "att": 1.55, "def": 1.35},
    "Kaiserslautern": {"tier": 2, "elo": 1550, "att": 1.50, "def": 1.50},
    "Holstein Kiel": {"tier": 1, "elo": 1640, "att": 1.35, "def": 1.80},
    "TSG 1899 Hoffenheim": {"tier": 1, "elo": 1730, "att": 1.80, "def": 1.60},

    # ESPAGNE (Copa del Rey)
    "Cuarte": {"tier": 5, "elo": 1160, "att": 0.95, "def": 1.95},
    "Gérone": {"tier": 1, "elo": 1790, "att": 1.90, "def": 1.30},
    "CF Calamocha": {"tier": 5, "elo": 1180, "att": 1.00, "def": 1.85},
    "CE Europa": {"tier": 4, "elo": 1310, "att": 1.30, "def": 1.45},
    "Sestao River Club": {"tier": 3, "elo": 1370, "att": 1.20, "def": 1.50},
    "Espanyol": {"tier": 1, "elo": 1670, "att": 1.35, "def": 1.45},
    "UD Pinatar": {"tier": 5, "elo": 1120, "att": 0.90, "def": 2.10},
    "Elche": {"tier": 2, "elo": 1590, "att": 1.50, "def": 1.25},
    "UD Castellonense": {"tier": 5, "elo": 1170, "att": 1.00, "def": 1.90},
    "UD Almeria": {"tier": 2, "elo": 1620, "att": 1.65, "def": 1.35},
    "Atlético Tordesillas": {"tier": 5, "elo": 1200, "att": 1.05, "def": 1.80},
    "Mirandes": {"tier": 2, "elo": 1550, "att": 1.35, "def": 1.35},
    "Gimnastica Segoviana": {"tier": 3, "elo": 1360, "att": 1.25, "def": 1.45},
    "Cultural Leonesa": {"tier": 3, "elo": 1410, "att": 1.35, "def": 1.30},
    "UD Llanera": {"tier": 4, "elo": 1270, "att": 1.15, "def": 1.65},
    "SD Ponferradina": {"tier": 3, "elo": 1420, "att": 1.35, "def": 1.30},
    "RSD Alcalá": {"tier": 5, "elo": 1210, "att": 1.05, "def": 1.80},
    "UD Las Palmas": {"tier": 1, "elo": 1680, "att": 1.30, "def": 1.45},
    "Ciudad de Lucena": {"tier": 5, "elo": 1220, "att": 1.10, "def": 1.75},
    "Rayo Majadahonda": {"tier": 4, "elo": 1320, "att": 1.25, "def": 1.45},
    "Don Benito": {"tier": 4, "elo": 1260, "att": 1.15, "def": 1.65},
    "Extremadura": {"tier": 4, "elo": 1300, "att": 1.25, "def": 1.50},
    "CE Manresa": {"tier": 5, "elo": 1210, "att": 1.10, "def": 1.75},
    "UE Sant Andreu": {"tier": 4, "elo": 1330, "att": 1.30, "def": 1.40},
    "Arosa": {"tier": 5, "elo": 1190, "att": 1.05, "def": 1.80},
    "Pontevedra": {"tier": 4, "elo": 1340, "att": 1.35, "def": 1.40},
    "CD Atletico Paso": {"tier": 4, "elo": 1260, "att": 1.10, "def": 1.65},
    "Cordoue": {"tier": 2, "elo": 1560, "att": 1.40, "def": 1.35},
    "CE Manacor": {"tier": 5, "elo": 1110, "att": 0.85, "def": 2.20},
    "Villarreal": {"tier": 1, "elo": 1830, "att": 2.05, "def": 1.30},
    "Recreativo de Huelva": {"tier": 3, "elo": 1380, "att": 1.25, "def": 1.45},
    "Rayo Vallecano": {"tier": 1, "elo": 1720, "att": 1.45, "def": 1.35},
    "Sporting Alcazar": {"tier": 5, "elo": 1100, "att": 0.85, "def": 2.20},
    "Málaga": {"tier": 2, "elo": 1560, "att": 1.40, "def": 1.35},
    "CD Tudelano": {"tier": 4, "elo": 1280, "att": 1.15, "def": 1.60},
    "Real Zaragoza": {"tier": 2, "elo": 1590, "att": 1.45, "def": 1.25}
}

# ==============================================================================
# 3. MOTEUR D'IMPORTATION AUTONOME & PROFILAGE DYNAMIQUE (ZÉRO DÉPENDANCE)
# ==============================================================================

def infer_team_profile(team_name, odds_team=None, odds_opp=None):
    """
    Déduit automatiquement la division, l'ELO et les forces xG de n'importe quel club inconnu
    à partir des probabilités implicites des cotes bookmaker.
    """
    if team_name in CUP_TEAMS_DB:
        return CUP_TEAMS_DB[team_name]
        
    if odds_team and odds_opp and odds_team > 0 and odds_opp > 0:
        p_team = 1.0 / odds_team
        p_opp = 1.0 / odds_opp
        tot = p_team + p_opp
        p_norm = p_team / tot if tot > 0 else 0.5
        p_norm = np.clip(p_norm, 0.02, 0.98)
        elo_diff = -400.0 * np.log10((1.0 / p_norm) - 1.0)
        base_elo = int(1550.0 + elo_diff)
        
        if base_elo >= 1800: tier = 1
        elif base_elo >= 1550: tier = 2
        elif base_elo >= 1350: tier = 3
        elif base_elo >= 1200: tier = 4
        else: tier = 5
        
        att = round(float(np.clip(1.40 + (base_elo - 1550) / 450.0, 0.80, 2.60)), 2)
        defense = round(float(np.clip(1.40 - (base_elo - 1550) / 500.0, 0.75, 2.30)), 2)
        return {"tier": tier, "elo": base_elo, "att": att, "def": defense}
        
    return {"tier": 2, "elo": 1550, "att": 1.40, "def": 1.40}

def parse_bookmaker_text(raw_text):
    """
    Parseur NLP/Regex robuste permettant d'extraire instantanément tous les matchs,
    dates et cotes (1, X, 2) copiés-collés directement depuis 1xBet, Flashscore, Betwinner, etc.
    """
    fixtures = []
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip()]
    if not lines:
        return fixtures
        
    # Format 1 : Ligne par ligne (Ex: "Manchester City vs Brighton 28.10 19:30 1.63 4.40 4.68")
    for line in lines:
        sep = re.search(r'\s+(?:vs|v|-|—|contre)\s+', line, re.IGNORECASE)
        if not sep:
            continue
            
        time_match = re.search(r'\b\d{1,2}:\d{2}\b', line)
        match_time = time_match.group(0) if time_match else ''
        
        date_match = re.search(r'\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b(?=\s+\d{1,2}:\d{2}|\s+[A-Za-z])', line)
        match_date = date_match.group(0) if date_match else ''
        full_dt = f'{match_date} {match_time}'.strip() or 'Direct / Prochain'
        
        clean_line = line
        if time_match: clean_line = clean_line.replace(match_time, ' ')
        if date_match: clean_line = clean_line.replace(match_date, ' ')
        
        floats = re.findall(r'\b\d{1,3}[.,]\d{1,3}\b', clean_line)
        odds_candidates = [float(f.replace(',', '.')) for f in floats]
        
        if len(odds_candidates) >= 3:
            o1, ox, o2 = odds_candidates[-3], odds_candidates[-2], odds_candidates[-1]
            odds_to_remove = floats[-3:]
        elif len(odds_candidates) == 2:
            o1, ox, o2 = odds_candidates[-2], 3.20, odds_candidates[-1]
            odds_to_remove = floats[-2:]
        elif len(odds_candidates) == 1:
            o1, ox, o2 = odds_candidates[-1], 3.20, 3.20
            odds_to_remove = floats[-1:]
        else:
            o1, ox, o2 = 2.10, 3.30, 3.10
            odds_to_remove = []
            
        text_without_odds = clean_line
        for ot in odds_to_remove:
            text_without_odds = text_without_odds.replace(ot, ' ')
            
        parts = re.split(r'\s+(?:vs|v|-|—|contre)\s+', text_without_odds.strip(), flags=re.IGNORECASE)
        if len(parts) >= 2:
            h = parts[0].strip(' -:|()[]')
            a = parts[1].strip(' -:|()[]')
            h = re.sub(r'^\d+\s*', '', h).strip()
            a = re.sub(r'\s*\d+$', '', a).strip()
            if len(h) >= 2 and len(a) >= 2:
                fixtures.append({
                    'home': h, 'away': a, 'date': full_dt,
                    'round': 'Coupe',
                    'odds_1': o1, 'odds_x': ox, 'odds_2': o2
                })
                
    # Format 2 : Blocs multilignes (Ex: Flashscore/1xBet mobile avec Equipe 1 sur ligne 1, Equipe 2 sur ligne 2, Cotes sur ligne 3)
    if not fixtures and len(lines) >= 3:
        i = 0
        while i < len(lines):
            l1 = lines[i]
            if i + 1 < len(lines):
                l2 = lines[i+1]
                if i + 2 < len(lines):
                    l3 = lines[i+2]
                    floats = re.findall(r'\b\d{1,3}[.,]\d{1,3}\b', l3)
                    if len(floats) >= 2:
                        odds = [float(f.replace(',', '.')) for f in floats]
                        o1 = odds[0]
                        ox = odds[1] if len(odds) > 1 else 3.20
                        o2 = odds[2] if len(odds) > 2 else 3.10
                        fixtures.append({
                            'home': l1.strip(' -:|()[]'),
                            'away': l2.strip(' -:|()[]'),
                            'date': 'Direct / Prochain',
                            'round': 'Coupe',
                            'odds_1': o1, 'odds_x': ox, 'odds_2': o2
                        })
                        i += 3
                        continue
            i += 1
            
    return fixtures

def fetch_api_sports_cup_fixtures(api_key, cup_code, season=2024):
    """
    Connexion directe à API-Sports (v3.football.api-sports.io) qui couvre 100% des Coupes Nationales.
    Offre gratuite : 100 requêtes/jour.
    """
    cup_cfg = CUP_PROFILES.get(cup_code, {})
    league_id = cup_cfg.get("api_league_id", 48)
    url = f"https://v3.football.api-sports.io/fixtures?league={league_id}&season={season}&next=20"
    headers = {"x-apisports-key": api_key.strip()}
    
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            items = data.get("response", [])
            parsed = []
            for item in items:
                f_info = item.get("fixture", {})
                t_info = item.get("teams", {})
                h_name = t_info.get("home", {}).get("name")
                a_name = t_info.get("away", {}).get("name")
                dt_raw = f_info.get("date", "")
                dt_str = dt_raw[8:10] + "." + dt_raw[5:7] + " " + dt_raw[11:16] if len(dt_raw) >= 16 else "Prochain"
                r_name = item.get("league", {}).get("round", "Tour de Coupe")
                
                # Cotes par défaut ou estimées
                parsed.append({
                    "home": h_name, "away": a_name,
                    "date": dt_str, "round": r_name,
                    "odds_1": 2.10, "odds_x": 3.30, "odds_2": 3.20
                })
            return parsed, None
        else:
            return None, f"Erreur API ({res.status_code}) : Vérifiez votre clé API-Sports."
    except Exception as e:
        return None, f"Erreur de connexion API : {str(e)}"

# ==============================================================================
# 4. MOTEUR STOCHASTIQUE DE KNOCKOUT : DIXON-COLES, TIER GAP & PROLONGATIONS
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

def run_cup_prediction(
    h_name, a_name, 
    cup_code="EFL_CUP",
    h_rotation="Équipe Type (100%)",
    a_rotation="Équipe Type (100%)",
    weather_mode="Normal (Idéal)",
    bankroll=1000.0,
    book_odds_custom=None,
    odds_h_ref=None,
    odds_a_ref=None
):
    cup_cfg = CUP_PROFILES.get(cup_code, CUP_PROFILES["EFL_CUP"])
    
    # Auto-profilage dynamique si le club n'est pas dans la base
    h_data = infer_team_profile(h_name, odds_h_ref, odds_a_ref)
    a_data = infer_team_profile(a_name, odds_a_ref, odds_h_ref)
    
    rot_mult = {
        "Équipe Type (100%)": {"att": 1.00, "def": 1.00},
        "Rotation Modérée (4-5 titulaires au repos)": {"att": 0.88, "def": 1.15},
        "Forte Rotation (7-8 remplaçants / Jeunesse)": {"att": 0.76, "def": 1.30}
    }
    h_rot_factors = rot_mult.get(h_rotation, rot_mult["Équipe Type (100%)"])
    a_rot_factors = rot_mult.get(a_rotation, rot_mult["Équipe Type (100%)"])
    
    tier_gap = a_data["tier"] - h_data["tier"]
    tier_advantage = tier_gap * 180.0
    poucet_bonus = 60.0 if h_data["tier"] > a_data["tier"] else 0.0
    eff_elo_diff = (h_data["elo"] - a_data["elo"]) + tier_advantage + poucet_bonus
    
    elo_mult_h = np.clip(1.0 + (eff_elo_diff / 750.0), 0.30, 2.30)
    elo_mult_a = np.clip(1.0 - (eff_elo_diff / 750.0), 0.30, 2.30)
    weather_mult = 0.88 if ("Pluie" in weather_mode or "Lourd" in weather_mode) else 1.0
    
    base_gh, base_ga = cup_cfg["avg_g_h"], cup_cfg["avg_g_a"]
    raw_h_xg = (h_data["att"] / 1.50) * (a_data["def"] / 1.30) * base_gh
    raw_a_xg = (a_data["att"] / 1.50) * (h_data["def"] / 1.30) * base_ga
    
    full_h_xg = float(np.clip(raw_h_xg * elo_mult_h * h_rot_factors["att"] * a_rot_factors["def"] * weather_mult, 0.18, 5.50))
    full_a_xg = float(np.clip(raw_a_xg * elo_mult_a * a_rot_factors["att"] * h_rot_factors["def"] * weather_mult, 0.15, 4.80))
    
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

    p_h_90 = float(np.sum(np.tril(matrix_90, -1))) * 100.0
    p_d_90 = float(np.sum(np.diag(matrix_90))) * 100.0
    p_a_90 = float(np.sum(np.triu(matrix_90, 1))) * 100.0
    
    prob_1x = round(p_h_90 + p_d_90, 1)
    prob_x2 = round(p_a_90 + p_d_90, 1)
    prob_12 = round(p_h_90 + p_a_90, 1)
    
    prob_o15 = round(float(np.sum([matrix_90[i, j] for i in range(max_g) for j in range(max_g) if i + j > 1])) * 100.0, 1)
    prob_o25 = round(float(np.sum([matrix_90[i, j] for i in range(max_g) for j in range(max_g) if i + j > 2])) * 100.0, 1)
    prob_u25 = round(100.0 - prob_o25, 1)
    prob_o35 = round(float(np.sum([matrix_90[i, j] for i in range(max_g) for j in range(max_g) if i + j > 3])) * 100.0, 1)
    prob_btts = round(float(np.sum(matrix_90[1:, 1:])) * 100.0, 1)

    # Prolongations & Tirs au But
    et_h_xg = full_h_xg * (30.0 / 90.0) * 0.82
    et_a_xg = full_a_xg * (30.0 / 90.0) * 0.82
    m_et = np.zeros((4, 4))
    for x in range(4):
        for y in range(4):
            m_et[x, y] = poisson.pmf(x, et_h_xg) * poisson.pmf(y, et_a_xg)
    tot_et = np.sum(m_et)
    if tot_et > 0: m_et /= tot_et
    p_h_et = float(np.sum(np.tril(m_et, -1)))
    p_draw_et = float(np.sum(np.diag(m_et)))
    
    pen_edge = 0.50 + np.clip(eff_elo_diff / 5000.0, -0.05, 0.05)
    p_h_pen = pen_edge

    prob_qual_h = (p_h_90 / 100.0) + (p_d_90 / 100.0) * (p_h_et + p_draw_et * p_h_pen)
    prob_qual_a = 1.0 - prob_qual_h
    prob_qual_h_pct = round(prob_qual_h * 100.0, 1)
    prob_qual_a_pct = round(prob_qual_a * 100.0, 1)
    
    odds_qual_h = prob_to_odds(prob_qual_h_pct)
    odds_qual_a = prob_to_odds(prob_qual_a_pct)

    # Corners & Cartons
    pace_factor = ((full_h_xg + full_a_xg) / 2.8) ** 0.35
    territorial_dom = (full_h_xg ** 1.2) / max(0.1, (full_h_xg ** 1.2 + full_a_xg ** 1.2))
    base_corner = cup_cfg["corner_base"]
    exp_c_h = base_corner * 0.54 * (territorial_dom ** 0.55) * pace_factor
    exp_c_a = base_corner * 0.46 * ((1.0 - territorial_dom) ** 0.55) * pace_factor
    tot_exp_corners = round(float(np.clip(exp_c_h + exp_c_a, 5.5, 14.5)), 1)
    
    base_card = cup_cfg["card_base"] * 1.15
    tot_exp_cards = round(float(np.clip(base_card * (1.10 if abs(eff_elo_diff) < 120 else 0.95), 2.5, 8.0)), 1)

    # Top 3 Scores
    flat_idx = np.argsort(matrix_90.ravel())[::-1]
    top_3_scores = []
    for idx in flat_idx[:3]:
        gh, ga = np.unravel_index(idx, matrix_90.shape)
        top_3_scores.append({"score": f"{gh}-{ga}", "prob": round(matrix_90[gh, ga] * 100.0, 1)})

    # Options recommandées
    fav_name = h_name if prob_qual_h_pct >= prob_qual_a_pct else a_name
    fav_qual_prob = max(prob_qual_h_pct, prob_qual_a_pct)
    fav_qual_odds = prob_to_odds(fav_qual_prob)
    
    options = []
    if fav_qual_prob >= 75.0:
        options.append({"type": "👑 SÉCURITÉ QUALIFICATION COUPE", "desc": f"Qualification pour le tour suivant : {fav_name}", "prob": fav_qual_prob, "odds": fav_qual_odds})
    elif prob_1x >= 82.0:
        options.append({"type": "👑 SÉCURITÉ TEMPS RÉGLEMENTAIRE", "desc": f"Double Chance (90 min) : {h_name} ou Nul (1X)", "prob": prob_1x, "odds": prob_to_odds(prob_1x)})
    elif prob_x2 >= 82.0:
        options.append({"type": "👑 SÉCURITÉ TEMPS RÉGLEMENTAIRE", "desc": f"Double Chance (90 min) : Nul ou {a_name} (X2)", "prob": prob_x2, "odds": prob_to_odds(prob_x2)})
    else:
        options.append({"type": "👑 SÉCURITÉ TEMPS RÉGLEMENTAIRE", "desc": "Plus de 1.5 Buts dans les 90 minutes", "prob": prob_o15, "odds": prob_to_odds(prob_o15)})

    if p_h_90 >= 54.0:
        options.append({"type": "🎯 VALUE BET 90 MINUTES", "desc": f"Victoire dans le temps réglementaire : {h_name}", "prob": round(p_h_90, 1), "odds": prob_to_odds(p_h_90)})
    elif p_a_90 >= 54.0:
        options.append({"type": "🎯 VALUE BET 90 MINUTES", "desc": f"Victoire dans le temps réglementaire : {a_name}", "prob": round(p_a_90, 1), "odds": prob_to_odds(p_a_90)})
    elif prob_btts >= 56.0:
        options.append({"type": "🎯 VALUE BET BUTS COUPE", "desc": "Les Deux Équipes Marquent (BTTS Oui)", "prob": prob_btts, "odds": prob_to_odds(prob_btts)})
    else:
        options.append({"type": "🎯 VALUE BET BUTS COUPE", "desc": "Plus de 2.5 Buts (Match Ouvert Knockout)", "prob": prob_o25, "odds": prob_to_odds(prob_o25)})

    if abs(eff_elo_diff) > 220.0:
        hcap_team = h_name if eff_elo_diff > 0 else a_name
        prob_hcap = round(max(p_h_90, p_a_90) * 0.82, 1)
        options.append({"type": "⚡ SCÉNARIO ÉCART DE NIVEAU", "desc": f"Victoire avec Handicap (-1.5) : {hcap_team}", "prob": prob_hcap, "odds": prob_to_odds(prob_hcap)})
    elif p_d_90 >= 28.0:
        options.append({"type": "⚡ SCÉNARIO PROLONGATIONS", "desc": "Match Nul après 90 min (Direction Prolongations)", "prob": round(p_d_90, 1), "odds": prob_to_odds(p_d_90)})
    else:
        options.append({"type": "⚡ SCÉNARIO CADENASSÉ COUPE", "desc": "Moins de 3.5 Buts (Match à élimination tendu)", "prob": prob_o35, "odds": prob_to_odds(prob_o35)})

    best_opt = options[0]
    fair_odds_best = prob_to_odds(best_opt["prob"])
    market_odds_best = book_odds_custom if book_odds_custom else round(fair_odds_best * 1.05, 2)
    kelly_stk, ev_val = calculate_quarter_kelly(best_opt["prob"], market_odds_best, bankroll)

    cup_context = (
        f"Gros écart de division (D{h_data['tier']} vs D{a_data['tier']}). Match piège pour le favori si rotation."
        if h_data['tier'] != a_data['tier'] else
        f"Duel serré entre pensionnaires de D{h_data['tier']}. Intensité maximale pour la qualification."
    )
    
    tactical_report = f"""
    🏆 <b>Intelligence Quantifiée Knockout Direct</b> :<br>
    • 🏠 <b>{h_name}</b> (D{h_data['tier']} | ELO {h_data['elo']} | {h_rotation}) : xG 90m = <b>{full_h_xg:.2f}</b><br>
    • ✈️ <b>{a_name}</b> (D{a_data['tier']} | ELO {a_data['elo']} | {a_rotation}) : xG 90m = <b>{full_a_xg:.2f}</b><br>
    • ⚔️ <b>Contexte Match de Coupe</b> : {cup_context}<br>
    • 👑 <b>Qualification Tour Suivant</b> : <b>{h_name} ({prob_qual_h_pct}%)</b> vs <b>{a_name} ({prob_qual_a_pct}%)</b><br>
    • ⏱️ <b>Risque de Prolongations</b> : <b>{p_d_90:.1f}%</b> | Risque Tirs au But : <b>{(p_d_90/100.0 * p_draw_et * 100.0):.1f}%</b><br>
    • ⛳ <b>Corners / Cartons</b> : ~<b>{tot_exp_corners} corners</b> | ~<b>{tot_exp_cards} cartons</b> (+ tension élimination)
    """

    return {
        "p_h_90": round(p_h_90, 1), "p_d_90": round(p_d_90, 1), "p_a_90": round(p_a_90, 1),
        "prob_1x": prob_1x, "prob_x2": prob_x2, "prob_12": prob_12,
        "prob_o15": prob_o15, "prob_o25": prob_o25, "prob_u25": prob_u25, "prob_o35": prob_o35,
        "prob_btts": prob_btts,
        "prob_qual_h": prob_qual_h_pct, "prob_qual_a": prob_qual_a_pct,
        "odds_qual_h": odds_qual_h, "odds_qual_a": odds_qual_a,
        "prob_overtime": round(p_d_90, 1), "prob_penalties": round(p_d_90/100.0 * p_draw_et * 100.0, 1),
        "corners": tot_exp_corners, "cards": tot_exp_cards,
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
# 5. INITIALISATION DE LA SESSION & GESTIONNAIRE AUTONOME
# ==============================================================================
if "cup_matches" not in st.session_state:
    cfg_file = "artifacts/file_generation/ttl=63d/output/cup_matches_config.json"
    import os, json
    loaded_cfg = None
    for p in [cfg_file, "cup_matches_config.json"]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as jf:
                    loaded_cfg = json.load(jf)
                break
            except Exception:
                pass
    st.session_state["cup_matches"] = loaded_cfg if loaded_cfg else copy.deepcopy(SCHEDULED_CUP_MATCHES)

st.sidebar.markdown("""
    <div style="text-align:center; padding:10px 0;">
        <h2 style="color:#F59E0B; margin:0; font-weight:900;">APEX CUPS QUANT</h2>
        <span style="font-size:0.8rem; letter-spacing:2px; color:#38BDF8; font-weight:800;">AUTONOMOUS LIVE PRO v52.0</span>
    </div>
""", unsafe_allow_html=True)

selected_cup_name = st.sidebar.selectbox("🏆 Compétition de Coupe Cible", list(CUP_COMPETITIONS.keys()))
active_cup_code = CUP_COMPETITIONS[selected_cup_name]
cup_cfg = CUP_PROFILES[active_cup_code]

st.sidebar.divider()
st.sidebar.markdown("### ⚙️ PARAMÈTRES DU TOUR")
weather_condition = st.sidebar.selectbox("Météo & Pelouse", ["Normal (Idéal)", "Pluie / Terrain Glissant", "Froid / Vent Fort"])
user_bankroll = st.sidebar.number_input("Capital Alloué aux Coupes ($ / €)", value=1000.0, step=50.0, min_value=10.0)

# ==============================================================================
# BANDEAU D'AUTONOMIE TOTALE : IMPORTATEUR EN 1 CLIC & API LIVE
# ==============================================================================
with st.expander("⚡ GESTIONNAIRE AUTONOME : IMPORTER VOS MATCHS EN 1 CLIC OU VIA API (Zéro modification de code)", expanded=False):
    st.markdown("""
    <div style="font-size:0.92rem; color:#94A3B8; margin-bottom:12px;">
        Ne dépendez plus jamais de personne pour les prochains tours ! Mettez à jour le bot vous-même en 2 secondes en collant le texte de votre bookmaker ou en connectant une API gratuite.
    </div>
    """, unsafe_allow_html=True)
    
    subtab_paste, subtab_api, subtab_manual = st.tabs([
        "📋 Copier-Coller Bookmaker (Recommandé en 1 Clic)", 
        "📡 API-Football Live (100% Automatique)", 
        "➕ Ajouter un Match Unique"
    ])
    
    # 1. COPIER COLLER DEPUIS 1XBET / FLASHSCORE / BETWINNER
    with subtab_paste:
        st.markdown("**Collez le texte brut copié depuis votre application de paris (1xBet, Betwinner, Flashscore, etc.) :**")
        pasted_text = st.text_area(
            "Zone de collage :",
            height=130,
            placeholder="Exemple de texte collé :\nBradford City vs Peterborough United 27.10 19:45 1.70 4.04 4.60\nManchester City vs Brighton 1.63 4.40 4.68\nRot-Weiss Essen - RB Leipzig 14.50 8.10 1.13"
        )
        col_b1, col_b2, col_b3 = st.columns([1, 1, 1])
        with col_b1:
            if st.button("⚡ Synchroniser & Remplacer le tour", use_container_width=True):
                if pasted_text.strip():
                    parsed_res = parse_bookmaker_text(pasted_text)
                    if parsed_res:
                        st.session_state["cup_matches"][active_cup_code] = parsed_res
                        st.success(f"✅ {len(parsed_res)} matchs importés et synchronisés avec succès pour {cup_cfg['name']} !")
                        st.rerun()
                    else:
                        st.error("Impossible de détecter les matchs. Vérifiez que le texte contient bien des noms d'équipes et des cotes.")
                else:
                    st.warning("Veuillez d'abord coller du texte.")
        with col_b2:
            if st.button("➕ Ajouter à la liste existante", use_container_width=True):
                if pasted_text.strip():
                    parsed_res = parse_bookmaker_text(pasted_text)
                    if parsed_res:
                        current_list = st.session_state["cup_matches"].get(active_cup_code, [])
                        current_list.extend(parsed_res)
                        st.session_state["cup_matches"][active_cup_code] = current_list
                        st.success(f"✅ {len(parsed_res)} matchs ajoutés ! Total : {len(current_list)} matchs.")
                        st.rerun()
        with col_b3:
            if st.button("🔄 Restaurer les matchs d'origine", use_container_width=True):
                st.session_state["cup_matches"][active_cup_code] = copy.deepcopy(SCHEDULED_CUP_MATCHES.get(active_cup_code, []))
                st.info("Matchs d'origine réinitialisés.")
                st.rerun()

    # 2. SYNCHRONISATION API DIRECTE (API-SPORTS)
    with subtab_api:
        st.markdown("""
        **Connexion directe au flux API-Sports (v3.football.api-sports.io) :**<br>
        *Contrairement à Football-Data.org (qui bloque les coupes sur l'offre gratuite), API-Sports couvre toutes les coupes nationales avec 100 requêtes gratuites/jour.*
        """, unsafe_allow_html=True)
        api_key_input = st.text_input("Votre Clé API-Sports (x-apisports-key) :", type="password", placeholder="Ex: 8a7c2b5...")
        season_pick = st.selectbox("Saison :", [2024, 2025, 2026], index=0)
        
        if st.button("📡 Télécharger les prochains matchs en direct", use_container_width=True):
            if api_key_input.strip():
                with st.spinner("Interrogation des serveurs API-Sports..."):
                    api_matches, err_msg = fetch_api_sports_cup_fixtures(api_key_input, active_cup_code, season_pick)
                    if api_matches:
                        st.session_state["cup_matches"][active_cup_code] = api_matches
                        st.success(f"✅ {len(api_matches)} matchs officiels récupérés en direct !")
                        st.rerun()
                    else:
                        st.error(err_msg)
            else:
                st.warning("Veuillez renseigner votre clé API-Sports gratuite.")

    # 3. AJOUT MANUEL D'UN MATCH UNIQUE
    with subtab_manual:
        col_m1, col_m2 = st.columns(2)
        with col_m1: man_h = st.text_input("Équipe Domicile :", placeholder="Ex: Liverpool")
        with col_m2: man_a = st.text_input("Équipe Extérieur :", placeholder="Ex: Chelsea")
        col_m3, col_m4, col_m5, col_m6 = st.columns(4)
        with col_m3: man_date = st.text_input("Date / Heure :", value="20:00")
        with col_m4: man_o1 = st.number_input("Cote 1 :", value=2.10, step=0.05)
        with col_m5: man_ox = st.number_input("Cote X :", value=3.40, step=0.05)
        with col_m6: man_o2 = st.number_input("Cote 2 :", value=3.20, step=0.05)
        if st.button("Ajouter ce match au programme", use_container_width=True):
            if man_h.strip() and man_a.strip():
                new_m = {
                    "home": man_h.strip(), "away": man_a.strip(),
                    "date": man_date.strip(), "round": "Tour de Coupe",
                    "odds_1": float(man_o1), "odds_x": float(man_ox), "odds_2": float(man_o2)
                }
                current_list = st.session_state["cup_matches"].get(active_cup_code, [])
                current_list.append(new_m)
                st.session_state["cup_matches"][active_cup_code] = current_list
                st.success(f"Match {man_h} vs {man_a} ajouté avec succès !")
                st.rerun()

# Récupération de la liste des vrais matchs programmés
real_cup_matches = st.session_state["cup_matches"].get(active_cup_code, [])

tab_match, tab_scanner, tab_all_matches, tab_ticket = st.tabs([
    "⚔️ ANALYSE MATCH DU JOUR",
    "🔍 SCANNER VALUE BETS OFFICIEL",
    f"📅 PROGRAMME OFFICIEL ({len(real_cup_matches)} MATCHS)",
    "🎟️ MARMITE QUALIFICATION VIP"
])

# ------------------------------------------------------------------------------
# ONGLET 1 : ANALYSE DU MATCH EXACT DU JOUR
# ------------------------------------------------------------------------------
with tab_match:
    st.subheader(f"Disséqueur Stochastique de Coupe — {cup_cfg['name']}")
    
    mode_pick = st.radio("Mode de sélection :", [
        "📌 Choisir parmi les vrais matchs programmés sur votre bookmaker", 
        "🛠️ Composer un match personnalisé libre"
    ], horizontal=True)

    if "vrais matchs" in mode_pick and real_cup_matches:
        match_labels = [f"{m['date']} : {m['home']} vs {m['away']} (Cotes: {m['odds_1']} / {m['odds_x']} / {m['odds_2']})" for m in real_cup_matches]
        sel_idx = st.selectbox("Sélectionnez l'affiche officielle du jour :", range(len(match_labels)), format_func=lambda i: match_labels[i])
        current_match = real_cup_matches[sel_idx]
        h_team_pick = current_match["home"]
        a_team_pick = current_match["away"]
        default_odds = current_match["odds_1"]
        ref_odds_h = current_match.get("odds_1")
        ref_odds_a = current_match.get("odds_2")
    else:
        all_avail_teams = sorted(list(set(list(CUP_TEAMS_DB.keys()) + [str(m["home"]) for m in real_cup_matches] + [str(m["away"]) for m in real_cup_matches])))
        col_c1, col_c2 = st.columns(2)
        with col_c1: h_team_pick = st.selectbox("Équipe Domicile :", all_avail_teams, index=0)
        with col_c2: a_team_pick = st.selectbox("Équipe Extérieur :", all_avail_teams, index=min(1, len(all_avail_teams)-1))
        default_odds = 1.45
        ref_odds_h = None
        ref_odds_a = None

    col_r1, col_r2, col_r3 = st.columns([1, 1, 1])
    with col_r1:
        h_rot_pick = st.selectbox(f"Composition {h_team_pick} :", [
            "Équipe Type (100%)", "Rotation Modérée (4-5 titulaires au repos)", "Forte Rotation (7-8 remplaçants / Jeunesse)"
        ], index=0)
    with col_r2:
        a_rot_pick = st.selectbox(f"Composition {a_team_pick} :", [
            "Équipe Type (100%)", "Rotation Modérée (4-5 titulaires au repos)", "Forte Rotation (7-8 remplaçants / Jeunesse)"
        ], index=0)
    with col_r3:
        book_odds_in = st.number_input("Cote Bookmaker de l'Option Prioritaire :", value=float(default_odds), step=0.02, min_value=1.01)

    res_cup = run_cup_prediction(
        h_team_pick, a_team_pick, active_cup_code, 
        h_rot_pick, a_rot_pick, weather_condition, user_bankroll, book_odds_in,
        odds_h_ref=ref_odds_h, odds_a_ref=ref_odds_a
    )

    st.markdown(f"""
    <div class="matrix-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h1 style="color:#F59E0B; margin:0; font-size:2rem;">{h_team_pick} <span style="color:#94A3B8; font-weight:300;">vs</span> {a_team_pick}</h1>
            <span class="badge-cup" style="font-size:0.9rem;">{cup_cfg['name']}</span>
        </div>
        <div class="cup-box">{res_cup['tactical_report']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 👑 MARCHÉ VEDETTE : QUI VA SE QUALIFIER ? (TO QUALIFY)")
    q1, q2 = st.columns(2)
    with q1:
        st.markdown(f"""
        <div class="qualif-box">
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; color:#F59E0B;">QUALIFICATION DOMICILE</span>
            <div style="font-size:1.6rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{h_team_pick} Passe au Tour Suivant</div>
            <div style="font-size:1.2rem; font-weight:800; color:#10B981;">Probabilité Totale : {res_cup['prob_qual_h']}% | Cote Équitable : {res_cup['odds_qual_h']}</div>
        </div>
        """, unsafe_allow_html=True)
    with q2:
        st.markdown(f"""
        <div class="qualif-box">
            <span style="font-size:0.85rem; font-weight:800; text-transform:uppercase; color:#F59E0B;">QUALIFICATION EXTÉRIEUR</span>
            <div style="font-size:1.6rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{a_team_pick} Passe au Tour Suivant</div>
            <div style="font-size:1.2rem; font-weight:800; color:#10B981;">Probabilité Totale : {res_cup['prob_qual_a']}% | Cote Équitable : {res_cup['odds_qual_a']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🎯 SÉLECTION QUANTITATIVE HIÉRARCHISÉE DU BOT")
    for opt in res_cup['options']:
        style_cls = "option-box" if "SÉCURITÉ" in opt['type'] else ("option-box-sec" if "VALUE" in opt['type'] else "qualif-box")
        st.markdown(f"""
        <div class="{style_cls}">
            <div style="font-size:0.8rem; font-weight:800; text-transform:uppercase; color:#F59E0B; letter-spacing:1px;">{opt['type']}</div>
            <div style="font-size:1.35rem; font-weight:900; color:#FFFFFF; margin:5px 0;">{opt['desc']}</div>
            <div style="font-size:1rem; font-weight:700; color:#10B981;">Probabilité Estimée : <b>{opt['prob']}%</b> | Cote Juste : <b>{opt['odds']}</b></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📊 TEMPS RÉGLEMENTAIRE (90 MINUTES) & MARCHÉS COMPLETS")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f"""<div class="sub-card"><b>1N2 TEMPS RÉGL.</b><br>1 : <span class="stat-badge">{res_cup['p_h_90']}%</span><br>Nul : <span class="stat-badge">{res_cup['p_d_90']}%</span><br>2 : <span class="stat-badge">{res_cup['p_a_90']}%</span></div>""", unsafe_allow_html=True)
    with m2: st.markdown(f"""<div class="sub-card"><b>DOUBLE CHANCE (90m)</b><br>1X : <span class="stat-badge">{res_cup['prob_1x']}%</span><br>X2 : <span class="stat-badge">{res_cup['prob_x2']}%</span><br>12 : <span class="stat-badge">{res_cup['prob_12']}%</span></div>""", unsafe_allow_html=True)
    with m3: st.markdown(f"""<div class="sub-card"><b>BUTS DANS LE MATCH</b><br>Over 1.5 : <span class="stat-badge">{res_cup['prob_o15']}%</span><br>Over 2.5 : <span class="stat-badge">{res_cup['prob_o25']}%</span><br>Under 2.5 : <span class="stat-badge">{res_cup['prob_u25']}%</span></div>""", unsafe_allow_html=True)
    with m4: st.markdown(f"""<div class="sub-card"><b>BTTS & PROLONGATIONS</b><br>BTTS (Oui) : <span class="stat-badge">{res_cup['prob_btts']}%</span><br>Prolongations : <span class="stat-badge">{res_cup['prob_overtime']}%</span><br>Tirs au But : <span class="stat-badge">{res_cup['prob_penalties']}%</span></div>""", unsafe_allow_html=True)

    col_k, col_sc = st.columns([1, 2])
    with col_k:
        st.markdown("### 💰 GESTION DE MISE KELLY")
        ev_sign = "+" if res_cup['ev_percentage'] >= 0 else ""
        st.metric("Mise Conseillée (1/4 Kelly)", f"{res_cup['kelly_stake']} $", f"Expected Value : {ev_sign}{res_cup['ev_percentage']}%")
    with col_sc:
        st.markdown("### 🏆 TOP 3 SCORES EXACTS (90 MIN)")
        sc1, sc2, sc3 = st.columns(3)
        with sc1: st.markdown(f"""<div class="big-score-box"><b>1er SCORE</b><div class="big-score-val">{res_cup['top_3_scores'][0]['score']}</div><div class="big-score-prob">{res_cup['top_3_scores'][0]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc2: st.markdown(f"""<div class="big-score-box"><b>2ème SCORE</b><div class="big-score-val">{res_cup['top_3_scores'][1]['score']}</div><div class="big-score-prob">{res_cup['top_3_scores'][1]['prob']}%</div></div>""", unsafe_allow_html=True)
        with sc3: st.markdown(f"""<div class="big-score-box"><b>3ème SCORE</b><div class="big-score-val">{res_cup['top_3_scores'][2]['score']}</div><div class="big-score-prob">{res_cup['top_3_scores'][2]['prob']}%</div></div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# ONGLET 2 : SCANNER DE VALUE BETS SUR LES VRAIES COTES DU BOOKMAKER
# ------------------------------------------------------------------------------
with tab_scanner:
    st.markdown(f"""
    <div class="vip-banner">
        <h2 style="margin:0; color:#F59E0B;">🔍 SCANNER DE VALUE BETS — {cup_cfg['name']}</h2>
        <span style="font-size:0.95rem; color:#E2E8F0;">Comparaison mathématique directe entre les vraies cotes du bookmaker et le modèle</span>
    </div>
    """, unsafe_allow_html=True)
    
    if real_cup_matches:
        min_ev_cup = st.slider("Seuil minimum d'Expected Value (EV%) :", -2.0, 15.0, 1.0, 0.5)
        scanner_cup_rows = []
        
        for m in real_cup_matches:
            ht, at = m["home"], m["away"]
            pred = run_cup_prediction(
                ht, at, active_cup_code, 
                "Équipe Type (100%)", "Équipe Type (100%)", weather_condition, user_bankroll,
                odds_h_ref=m.get("odds_1"), odds_a_ref=m.get("odds_2")
            )
            
            odds_1_book = m["odds_1"]
            odds_x_book = m["odds_x"]
            odds_2_book = m["odds_2"]
            
            stk_1, ev_1 = calculate_quarter_kelly(pred['p_h_90'], odds_1_book, user_bankroll)
            stk_x, ev_x = calculate_quarter_kelly(pred['p_d_90'], odds_x_book, user_bankroll)
            stk_2, ev_2 = calculate_quarter_kelly(pred['p_a_90'], odds_2_book, user_bankroll)
            
            sim_q_h = round(pred['odds_qual_h'] * 1.05, 2)
            sim_q_a = round(pred['odds_qual_a'] * 1.05, 2)
            stk_qh, ev_qh = calculate_quarter_kelly(pred['prob_qual_h'], sim_q_h, user_bankroll)
            stk_qa, ev_qa = calculate_quarter_kelly(pred['prob_qual_a'], sim_q_a, user_bankroll)

            bets_candidates = [
                {"label": f"Victoire 90m : {ht} (1)", "prob": pred['p_h_90'], "fair": prob_to_odds(pred['p_h_90']), "odds": odds_1_book, "ev": ev_1, "stk": stk_1},
                {"label": f"Match Nul 90m (X)", "prob": pred['p_d_90'], "fair": prob_to_odds(pred['p_d_90']), "odds": odds_x_book, "ev": ev_x, "stk": stk_x},
                {"label": f"Victoire 90m : {at} (2)", "prob": pred['p_a_90'], "fair": prob_to_odds(pred['p_a_90']), "odds": odds_2_book, "ev": ev_2, "stk": stk_2},
                {"label": f"Qualification : {ht}", "prob": pred['prob_qual_h'], "fair": pred['odds_qual_h'], "odds": sim_q_h, "ev": ev_qh, "stk": stk_qh},
                {"label": f"Qualification : {at}", "prob": pred['prob_qual_a'], "fair": pred['odds_qual_a'], "odds": sim_q_a, "ev": ev_qa, "stk": stk_qa}
            ]

            for item in bets_candidates:
                if item["ev"] >= min_ev_cup:
                    sig = "🟢 ULTRA VALUE" if item["ev"] >= 7.0 else ("🟡 FORTE VALUE" if item["ev"] >= 3.0 else "🔵 LÉGER EDGE")
                    scanner_cup_rows.append({
                        "Match": f"{ht} vs {at}",
                        "Date": m["date"],
                        "Marché & Option": item["label"],
                        "Proba Modèle": f"{item['prob']}%",
                        "Cote Équitable": item["fair"],
                        "Cote Bookmaker": item["odds"],
                        "Expected Value (EV)": item["ev"],
                        "Mise Quarter-Kelly": f"{item['stk']} $",
                        "Signal": sig
                    })

        if scanner_cup_rows:
            df_cup_scan = pd.DataFrame(scanner_cup_rows).sort_values(by="Expected Value (EV)", ascending=False)
            st.dataframe(df_cup_scan.style.format({"Expected Value (EV)": "{:+.2f}%"}), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune anomalie ne dépasse le seuil fixé.")
    else:
        st.warning("Aucun match disponible.")

# ------------------------------------------------------------------------------
# ONGLET 3 : PROGRAMME COMPLET DES VRAIS MATCHS DU TOUR
# ------------------------------------------------------------------------------
with tab_all_matches:
    st.subheader(f"Tableau Officiel des Rencontres — {cup_cfg['name']}")
    if real_cup_matches:
        sched_rows = []
        for m in real_cup_matches:
            pred = run_cup_prediction(
                m["home"], m["away"], active_cup_code, 
                "Équipe Type (100%)", "Équipe Type (100%)", weather_condition, user_bankroll,
                odds_h_ref=m.get("odds_1"), odds_a_ref=m.get("odds_2")
            )
            sched_rows.append({
                "Date": m["date"],
                "Affiche": f"{m['home']} vs {m['away']}",
                "Cotes 1X2 Bookmaker": f"{m['odds_1']} | {m['odds_x']} | {m['odds_2']}",
                "Proba Qualification": f"{m['home']} ({pred['prob_qual_h']}%) vs {m['away']} ({pred['prob_qual_a']}%)",
                "Option Maîtresse Bot": f"{pred['options'][0]['desc']} ({pred['options'][0]['prob']}%)",
                "Risque Prolongations": f"{pred['prob_overtime']}%",
                "Risque Tirs au But": f"{pred['prob_penalties']}%"
            })
        st.dataframe(pd.DataFrame(sched_rows), use_container_width=True, hide_index=True)
    else:
        st.info("Aucun match programmé. Utilisez le bandeau ci-dessus pour importer vos matchs en 1 clic.")

# ------------------------------------------------------------------------------
# ONGLET 4 : COMBINÉ SPÉCIAL QUALIFICATION VIP DU BOT
# ------------------------------------------------------------------------------
with tab_ticket:
    st.subheader(f"🎟️ Combiné Spécial Qualification VIP — {cup_cfg['name']}")
    if real_cup_matches:
        ticket_items = []
        for m in real_cup_matches:
            pred = run_cup_prediction(
                m["home"], m["away"], active_cup_code, 
                "Équipe Type (100%)", "Équipe Type (100%)", weather_condition, user_bankroll,
                odds_h_ref=m.get("odds_1"), odds_a_ref=m.get("odds_2")
            )
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
        top_qual_picks = ticket_items[:min(5, len(ticket_items))]
        total_cup_odds = float(np.prod([it["odds"] for it in top_qual_picks])) if top_qual_picks else 1.0
        
        st.markdown(f"""
        <div class="vip-banner">
            <h2 style="margin:0; color:#F59E0B;">🏆 COMBINÉ QUALIFICATION OFFICIEL DU BOT (TOP {len(top_qual_picks)})</h2>
            <div style="font-size:1.8rem; font-weight:900; color:#FFFFFF; margin-top:8px;">
                Cote Totale Cumulée : <span style="color:#38BDF8;">{total_cup_odds:.2f}</span>
            </div>
            <div style="font-size:0.9rem; color:#E2E8F0; margin-top:4px;">Sélection des qualifications les plus statistiquement sûres du tour</div>
        </div>
        """, unsafe_allow_html=True)
        
        for idx, item in enumerate(top_qual_picks, 1):
            st.markdown(f"""
            <div class="sub-card">
                <b>{idx}. {item['match']}</b><br>
                👉 Choix du Bot : <b style="color:#10B981;">{item['pick']}</b> | Probabilité : <b>{item['prob']}%</b> (Cote : <b>{item['odds']}</b>)
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Importez des matchs pour générer le ticket combiné VIP.")
