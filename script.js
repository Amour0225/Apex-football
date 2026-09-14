/**
 * APEX QUANT ENGINE v30.0 - ENGINE & HISTORY MANAGEMENT
 */

const HISTORY_STORAGE_KEY = "apex_quant_history_v30";

// 1. Dictionnaire des Championnats et Paramètres Statistiques (Moyenne buts & avantage domicile)
const LEAGUES_CONFIG = {
  // Europe Majeure
  "LIGUE 1": { country: "FR", avgGoals: 2.52, homeAdv: 1.15 },
  "PREMIER LEAGUE": { country: "EN", avgGoals: 2.85, homeAdv: 1.20 },
  "LA LIGA": { country: "ES", avgGoals: 2.50, homeAdv: 1.18 },
  "SERIE A": { country: "IT", avgGoals: 2.61, homeAdv: 1.16 },
  "BUNDESLIGA": { country: "DE", avgGoals: 3.10, homeAdv: 1.22 },
  
  // Coupes Européennes (Milieu de semaine)
  "CHAMPIONS LEAGUE": { country: "EU", avgGoals: 2.98, homeAdv: 1.15 },
  "EUROPA LEAGUE": { country: "EU", avgGoals: 2.80, homeAdv: 1.18 },
  "CONFERENCE LEAGUE": { country: "EU", avgGoals: 2.75, homeAdv: 1.20 },

  // Ligues Secondaires & Semaine
  "EFL CHAMPIONSHIP": { country: "EN", avgGoals: 2.45, homeAdv: 1.14 },
  "SERIE B": { country: "IT", avgGoals: 2.30, homeAdv: 1.15 },

  // Amériques & Asie (Été / Jours Creux)
  "COPA LIBERTADORES": { country: "SA", avgGoals: 2.40, homeAdv: 1.30 },
  "BRASILEIRAO": { country: "BR", avgGoals: 2.38, homeAdv: 1.28 },
  "LIGA ARGENTINA": { country: "AR", avgGoals: 2.12, homeAdv: 1.25 },
  "ELITESERIEN": { country: "NO", avgGoals: 3.05, homeAdv: 1.20 },
  "ALLSVENSKAN": { country: "SE", avgGoals: 2.70, homeAdv: 1.18 },
  "MLS": { country: "US", avgGoals: 3.12, homeAdv: 1.24 },
  "J1 LEAGUE": { country: "JP", avgGoals: 2.55, homeAdv: 1.12 }
};

let activeCoupon = null;

// ==========================================
// LOCALSTORAGE & HISTORIQUE
// ==========================================

function getHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    console.error("Erreur lecture LocalStorage", e);
    return [];
  }
}

function saveHistory(history) {
  try {
    localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(history));
    renderHistoryUI();
  } catch (e) {
    console.error("Erreur sauvegarde LocalStorage", e);
  }
}

function saveCouponToHistory(coupon) {
  const history = getHistory();
  const index = history.findIndex(item => item.id === coupon.id);
  if (index >= 0) {
    history[index] = coupon;
  } else {
    history.unshift(coupon);
  }
  saveHistory(history);
}

function deleteCouponFromHistory(id, event) {
  if (event) event.stopPropagation();
  if (confirm("Supprimer ce coupon de l'historique ?")) {
    let history = getHistory().filter(item => item.id !== id);
    saveHistory(history);
    if (activeCoupon && activeCoupon.id === id) {
      activeCoupon = history.length > 0 ? history[0] : getDemoCoupon();
      renderActiveCouponUI(activeCoupon);
    }
  }
}

function handleClearAllHistory() {
  if (confirm("Effacer tout l'historique ?")) {
    localStorage.removeItem(HISTORY_STORAGE_KEY);
    activeCoupon = getDemoCoupon();
    saveCouponToHistory(activeCoupon);
    renderActiveCouponUI(activeCoupon);
    renderHistoryUI();
  }
}

// ==========================================
// CALCULS ALGORITHMIQUES & EVALUATION
// ==========================================

function getCouponStatus(selections) {
  if (selections.some(item => item.status === "PERDU")) return { text: "❌ PERDU", code: "lost" };
  if (selections.every(item => item.status === "GAGNÉ")) return { text: "✅ GAGNÉ", code: "won" };
  return { text: "⏳ EN COURS", code: "pending" };
}

function calculateTotalOdds(selections) {
  return selections.reduce((total, item) => total * item.odds, 1).toFixed(2);
}

// Détection du paramètre de ligue
function getLeagueParams(leagueName) {
  const cleanName = leagueName.toUpperCase().trim();
  for (let key in LEAGUES_CONFIG) {
    if (cleanName.includes(key)) return LEAGUES_CONFIG[key];
  }
  return { country: "GLOBAL", avgGoals: 2.50, homeAdv: 1.15 }; // Valeur par défaut
}

// ==========================================
// RENDU INTERFACE UTILISATEUR
// ==========================================

function renderActiveCouponUI(coupon) {
  activeCoupon = coupon;
  const container = document.getElementById("coupon-content");
  const statusBadge = document.getElementById("coupon-status");
  const dateDisplay = document.getElementById("coupon-date-display");

  const statusInfo = getCouponStatus(coupon.selections);
  statusBadge.textContent = statusInfo.text;
  statusBadge.className = `coupon-status status-${statusInfo.code}`;
  dateDisplay.textContent = `Créé le : ${coupon.date}`;

  let html = `<ul class="match-list">`;
  coupon.selections.forEach((item, index) => {
    const icon = item.status === "GAGNÉ" ? "✅" : item.status === "PERDU" ? "❌" : "⏳";
    const leagueData = getLeagueParams(item.league);
    
    html += `
      <li class="match-item">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="match-league">${index + 1}. [${item.league}]</span>
          <span class="badge-confidence">Moy. Buts: ${leagueData.avgGoals}</span>
        </div>
        <div class="match-teams">⚔️ ${item.match}</div>
        <div class="match-details">
          <span>🎯 Prono : <strong>${item.pick}</strong></span>
          <span>📊 Cote : <strong>${item.odds.toFixed(2)}</strong></span>
        </div>
        <div style="font-size:0.85rem; margin-top:4px; color:#475569;">
          Statut : <strong>${icon} ${item.status}</strong>
        </div>
      </li>`;
  });
  html += `</ul>`;
  container.innerHTML = html;
}

function renderHistoryUI() {
  const historyList = document.getElementById("history-list");
  const countDisplay = document.getElementById("history-count");
  const history = getHistory();

  countDisplay.textContent = history.length;

  if (history.length === 0) {
    historyList.innerHTML = `<p style="text-align:center; color:#94a3b8; padding:12px; margin:0;">Aucun coupon enregistré.</p>`;
    return;
  }

  let html = "";
  history.forEach(item => {
    const statusInfo = getCouponStatus(item.selections);
    const totalOdds = calculateTotalOdds(item.selections);
    const isActive = activeCoupon && activeCoupon.id === item.id ? "active-history-item" : "";

    html += `
      <div class="history-item ${isActive}" onclick="loadCouponFromHistory('${item.id}')">
        <div class="history-item-info">
          <span class="history-date">📅 ${item.date}</span>
          <span class="history-details">${item.selections.length} matchs | Cote : <strong>${totalOdds}</strong></span>
        </div>
        <div class="history-item-actions">
          <span class="coupon-status status-${statusInfo.code}">${statusInfo.text}</span>
          <button class="btn-delete-icon" onclick="deleteCouponFromHistory('${item.id}', event)">🗑️</button>
        </div>
      </div>`;
  });

  historyList.innerHTML = html;
}

function loadCouponFromHistory(id) {
  const history = getHistory();
  const selected = history.find(item => item.id === id);
  if (selected) {
    renderActiveCouponUI(selected);
    renderHistoryUI();
  }
}

// ==========================================
// PARSER & ACTIONS PRESS-PAPIER
// ==========================================

async function handlePasteCoupon() {
  const btn = document.getElementById("btn-paste-coupon");
  try {
    const pastedText = await navigator.clipboard.readText();
    const parsed = parseCouponText(pastedText);
    
    if (!parsed) {
      alert("Format du texte non reconnu.");
      return;
    }

    const newCoupon = {
      id: "coupon_" + Date.now(),
      date: parsed.date,
      selections: parsed.selections
    };

    saveCouponToHistory(newCoupon);
    renderActiveCouponUI(newCoupon);

    btn.innerHTML = "✅ Collé !";
    btn.classList.add("success");
    setTimeout(() => { btn.innerHTML = "📋 Coller"; btn.classList.remove("success"); }, 2000);
  } catch (err) {
    alert("Impossible d'accéder au presse-papier.");
  }
}

function parseCouponText(text) {
  try {
    const dateMatch = text.match(/📅 Date\s*:\s*([^\n]+)/i);
    const date = dateMatch ? dateMatch[1].trim() : new Date().toLocaleDateString("fr-FR");
    const blocks = text.split(/------------------------------|\n(?=\d+\.\s*\[)/);
    const selections = [];

    blocks.forEach(block => {
      const leagueMatch = block.match(/\[(.*?)\]/);
      const matchMatch = block.match(/⚔️\s*(.+)/);
      const pickMatch = block.match(/🎯 Prono\s*:\s*(.+)/);
      const oddsMatch = block.match(/📊 Cote\s*:\s*([\d\.,]+)/);
      const statusMatch = block.match(/📌 Statut\s*:\s*(?:✅|❌|⏳)?\s*(.+)/);

      if (leagueMatch && matchMatch && pickMatch) {
        const rawStatus = statusMatch ? statusMatch[1].trim().toUpperCase() : "EN_COURS";
        let status = "EN_COURS";
        if (rawStatus.includes("GAGNÉ") || rawStatus.includes("GAGNE")) status = "GAGNÉ";
        if (rawStatus.includes("PERDU")) status = "PERDU";

        selections.push({
          league: leagueMatch[1].trim(),
          match: matchMatch[1].trim(),
          pick: pickMatch[1].trim(),
          odds: oddsMatch ? parseFloat(oddsMatch[1].replace(',', '.')) : 1.00,
          status: status
        });
      }
    });

    return selections.length > 0 ? { date, selections } : null;
  } catch (e) {
    return null;
  }
}

function generateCouponPlainText(coupon) {
  const statusInfo = getCouponStatus(coupon.selections);
  let totalOdds = 1;
  let text = `==============================\n🎯 APEX QUANT ENGINE - COUPON\n📅 Date : ${coupon.date}\nRÉSULTAT : ${statusInfo.text}\n==============================\n\n`;

  coupon.selections.forEach((item, index) => {
    totalOdds *= item.odds;
    const icon = item.status === "GAGNÉ" ? "✅" : item.status === "PERDU" ? "❌" : "⏳";
    text += `${index + 1}. [${item.league.toUpperCase()}]\n   ⚔️ ${item.match}\n   🎯 Prono  : ${item.pick}\n   📊 Cote   : ${item.odds.toFixed(2)}\n   📌 Statut : ${icon} ${item.status}\n------------------------------\n`;
  });

  text += `\n🔥 COTE TOTALE : ${totalOdds.toFixed(2)}\n==============================`;
  return text;
}

async function handleCopyCoupon() {
  if (!activeCoupon) return;
  const btn = document.getElementById("btn-copy-coupon");
  try {
    await navigator.clipboard.writeText(generateCouponPlainText(activeCoupon));
    btn.innerHTML = "✅ Copié !";
    btn.classList.add("success");
    setTimeout(() => { btn.innerHTML = "📤 Copier"; btn.classList.remove("success"); }, 2000);
  } catch (err) { alert("Erreur lors de la copie."); }
}

function handleExportCoupon() {
  if (!activeCoupon) return;
  const blob = new Blob([generateCouponPlainText(activeCoupon)], { type: "text/plain;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `coupon_${activeCoupon.id}.txt`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function getDemoCoupon() {
  return {
    id: "coupon_demo",
    date: new Date().toLocaleDateString("fr-FR"),
    selections: [
      { league: "CHAMPIONS LEAGUE", match: "Real Madrid vs Man City", pick: "Les 2 équipes marquent", odds: 1.62, status: "GAGNÉ" },
      { league: "BRASILEIRAO", match: "Flamengo vs Palmeiras", pick: "Victoire Flamengo (1)", odds: 1.85, status: "GAGNÉ" },
      { league: "EFL CHAMPIONSHIP", match: "Leeds vs Leicester", pick: "+2.5 buts", odds: 1.75, status: "EN_COURS" }
    ]
  };
}

// ==========================================
// INITIALISATION
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
  const history = getHistory();
  if (history.length > 0) {
    activeCoupon = history[0];
  } else {
    activeCoupon = getDemoCoupon();
    saveCouponToHistory(activeCoupon);
  }
  renderActiveCouponUI(activeCoupon);
  renderHistoryUI();
});
// ==========================================
// MOTEUR DE PRÉDICTION MATHEMATIQUE (POISSON & DIXON-COLES)
// ==========================================

const ApexPredictor = {
  // Calcul de la factorielle
  factorial: function(n) {
    if (n === 0 || n === 1) return 1;
    let res = 1;
    for (let i = 2; i <= n; i++) res *= i;
    return res;
  },

  // Calcul de la probabilité de Poisson P(X = k)
  poissonProbability: function(k, lambda) {
    return (Math.pow(lambda, k) * Math.exp(-lambda)) / this.factorial(k);
  },

  // Générateur de matrice de scores exacts (jusqu'à 5-5)
  generateScoreMatrix: function(lambdaHome, lambdaAway) {
    let matrix = [];
    for (let h = 0; h <= 5; h++) {
      matrix[h] = [];
      for (let a = 0; a <= 5; a++) {
        matrix[h][a] = this.poissonProbability(h, lambdaHome) * this.poissonProbability(a, lambdaAway);
      }
    }
    return matrix;
  },

  // Analyse complète d'un match
  predictMatch: function(leagueKey, homeAttack, homeDefense, awayAttack, awayDefense) {
    const config = LEAGUES_CONFIG[leagueKey.toUpperCase()] || { avgGoals: 2.50, homeAdv: 1.15 };
    
    const baseGoalsPerTeam = config.avgGoals / 2;
    const lambdaHome = homeAttack * awayDefense * config.homeAdv * baseGoalsPerTeam;
    const lambdaAway = awayAttack * homeDefense * baseGoalsPerTeam;

    const matrix = this.generateScoreMatrix(lambdaHome, lambdaAway);

    let probHome = 0, probDraw = 0, probAway = 0;
    let probUnder25 = 0, probOver25 = 0;
    let probBTTS_Yes = 0, probBTTS_No = 0;

    for (let h = 0; h <= 5; h++) {
      for (let a = 0; a <= 5; a++) {
        const p = matrix[h][a];
        
        // 1X2
        if (h > a) probHome += p;
        else if (h === a) probDraw += p;
        else probAway += p;

        // Over / Under 2.5
        if (h + a < 2.5) probUnder25 += p;
        else probOver25 += p;

        // BTTS (Les 2 équipes marquent)
        if (h > 0 && a > 0) probBTTS_Yes += p;
        else probBTTS_No += p;
      }
    }
// Détermination de la meilleure sélection et de l'indice de confiance
    const selections = [
      { name: "Victoire Domicile (1)", prob: probHome, odds: (1 / probHome) },
      { name: "Match Nul (X)", prob: probDraw, odds: (1 / probDraw) },
      { name: "Victoire Extérieur (2)", prob: probAway, odds: (1 / probAway) },
      { name: "Plus de 2.5 Buts", prob: probOver25, odds: (1 / probOver25) },
      { name: "Moins de 2.5 Buts", prob: probUnder25, odds: (1 / probUnder25) },
      { name: "Les 2 équipes marquent (Oui)", prob: probBTTS_Yes, odds: (1 / probBTTS_Yes) }
    ];

    // Tri par probabilité décroissante
    selections.sort((a, b) => b.prob - a.prob);
    const bestPick = selections[0];
    const confidenceIndex = Math.min(Math.round(bestPick.prob * 100), 95);

    return {
      expectedGoals: { home: lambdaHome.toFixed(2), away: lambdaAway.toFixed(2) },
      probabilities: {
        home: (probHome * 100).toFixed(1) + "%",
        draw: (probDraw * 100).toFixed(1) + "%",
        away: (probAway * 100).toFixed(1) + "%",
        over25: (probOver25 * 100).toFixed(1) + "%",
        btts: (probBTTS_Yes * 100).toFixed(1) + "%"
      },
      recommendedPick: bestPick.name,
      fairOdds: bestPick.odds.toFixed(2),
      confidence: confidenceIndex + "%"
    };
  }
};
