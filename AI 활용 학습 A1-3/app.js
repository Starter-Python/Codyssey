/**
 * ENTHES Official Squash League (ESL) & AI Studio
 * Pure Vanilla JavaScript Client Application
 * Compatible with 2026 H2 33-Player Official Roster & E1/E2/E3 System
 */

// ==========================================
// 1. Application State
// ==========================================
let appState = {
  players: [],
  matches: [],
  attendances: {},
  activeUser: null,
  activeLeague: 'E1', // 'E1' | 'E2' | 'E3'
  selectedPlayerId: 1,
  adminPin: '1234',
  isAdminAuthenticated: false,
  activeModalMatch: null,
  lastAiResult: null
};

const STAT_LABELS = {
  forehand: '포핸드',
  backhand: '백핸드',
  attackOption: '공격옵션',
  speed: '스피드',
  stamina: '체력',
  composure: '침착성'
};

const STAT_KEYS = ['forehand', 'backhand', 'attackOption', 'speed', 'stamina', 'composure'];

function saveState() {
  try {
    localStorage.setItem('enthes_esl_state_2026_h2', JSON.stringify(appState));
  } catch (e) {
    console.warn('localStorage save failed:', e);
  }
}

function loadState() {
  try {
    const saved = localStorage.getItem('enthes_esl_state_2026_h2');
    if (saved) {
      const parsed = JSON.parse(saved);
      appState = Object.assign(appState, parsed);
      return;
    }
  } catch (e) {
    console.warn('localStorage load failed:', e);
  }

  // Load from OFFICIAL_33_PLAYERS and OFFICIAL_30_MATCHES defined in embedded_data.js
  if (typeof OFFICIAL_33_PLAYERS !== 'undefined') {
    appState.players = JSON.parse(JSON.stringify(OFFICIAL_33_PLAYERS));
  }
  if (typeof OFFICIAL_30_MATCHES !== 'undefined') {
    appState.matches = JSON.parse(JSON.stringify(OFFICIAL_30_MATCHES));
  }

  // Seed attendance for today
  const today = new Date().toISOString().slice(0, 10);
  appState.attendances[today] = {
    1: 'attending', 2: 'attending', 3: 'attending', 4: 'attending',
    11: 'attending', 12: 'attending', 13: 'attending', 14: 'attending',
    26: 'attending', 27: 'attending', 28: 'attending'
  };

  saveState();
}

// ==========================================
// 2. Navigation & Tabs
// ==========================================
function switchTab(tabId) {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });

  document.querySelectorAll('.m-nav-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });

  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.classList.remove('active');
  });

  const target = document.getElementById(`tab-${tabId}`);
  if (target) target.classList.add('active');

  if (tabId === 'dashboard') renderDashboard();
  if (tabId === 'schedule') renderSchedule();
  if (tabId === 'attendance') renderAttendance();
  if (tabId === 'rankings') renderRankings();
  if (tabId === 'ai-coach') populateAiSelects();
  if (tabId === 'admin') renderAdminView();

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==========================================
// 3. Render Dashboard
// ==========================================
function renderDashboard() {
  document.getElementById('stat-total-players').innerHTML = `${appState.players.length}<small>명</small>`;

  const confirmedMatches = appState.matches.filter(m => m.status === 'confirmed').length;
  document.getElementById('stat-total-matches').innerHTML = `${confirmedMatches}<small>경기</small>`;

  const today = new Date().toISOString().slice(0, 10);
  const todayAtt = Object.values(appState.attendances[today] || {}).filter(s => s === 'attending').length;
  document.getElementById('stat-today-attending').innerHTML = `${todayAtt}<small>명</small>`;

  const aiCount = appState.matches.filter(m => m.aiFeedback).length;
  document.getElementById('stat-ai-reports').innerHTML = `${aiCount}<small>건</small>`;

  // Today's Scheduled Matches
  const todayContainer = document.getElementById('dash-today-matches');
  const scheduledList = appState.matches.filter(m => m.status === 'scheduled').slice(0, 4);
  if (scheduledList.length === 0) {
    todayContainer.innerHTML = '<p class="text-muted" style="font-size: 0.85rem; padding: 1rem 0;">모든 경기가 완료되었거나 대진 생성 대기 중입니다.</p>';
  } else {
    todayContainer.innerHTML = scheduledList.map(m => `
      <div class="compact-match-item">
        <div>
          <span class="badge badge-emerald" style="margin-right: 0.35rem;">${m.playerALeague || m.league}</span>
          <strong>${m.playerAName}</strong> vs <strong>${m.playerBName}</strong>
        </div>
        <button type="button" class="btn btn-sm btn-primary" onclick="openMatchInputModal(${m.id})">결과 입력</button>
      </div>
    `).join('');
  }

  // Recent Confirmed Results
  const recentContainer = document.getElementById('dash-recent-results');
  const recentList = appState.matches.filter(m => m.status === 'confirmed').slice(0, 4);
  if (recentList.length === 0) {
    recentContainer.innerHTML = '<p class="text-muted" style="font-size: 0.85rem; padding: 1rem 0;">확정된 경기 결과가 아직 없습니다.</p>';
  } else {
    recentContainer.innerHTML = recentList.map(m => `
      <div class="compact-match-item">
        <div>
          <span class="badge badge-emerald" style="margin-right: 0.35rem;">${m.playerALeague || m.league}</span>
          <strong>${m.playerAName}</strong> vs <strong>${m.playerBName}</strong>
        </div>
        <strong style="color: var(--brand-emerald-dark);">${m.scoreA} : ${m.scoreB}</strong>
      </div>
    `).join('');
  }
}

// ==========================================
// 4. Render Schedule & Match Cards
// ==========================================
function renderSchedule() {
  const leagueFilter = document.getElementById('schedule-league-filter').value;
  const container = document.getElementById('schedule-match-list');

  let matches = appState.matches.filter(m => {
    const l = m.playerALeague || m.league;
    return leagueFilter === '전체' || l === leagueFilter;
  });

  if (matches.length === 0) {
    container.innerHTML = '<div class="panel-card" style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 2rem;">해당 리그의 대진이 없습니다.</div>';
    return;
  }

  container.innerHTML = matches.map((m, idx) => {
    const pA = appState.players.find(p => p.id === m.playerAId || p.displayName === m.playerAName) || { tier: m.playerATier || 1, gender: 'male' };
    const pB = appState.players.find(p => p.id === m.playerBId || p.displayName === m.playerBName) || { tier: m.playerBTier || 1, gender: 'male' };

    const tierDiff = (pB.tier || 1) - (pA.tier || 1);
    let handicapText = '';
    if (tierDiff > 0) {
      handicapText = `⚡ ${m.playerBName} +${tierDiff * 2}점 핸디캡 & 1세트 서브권`;
    } else if (tierDiff < 0) {
      handicapText = `⚡ ${m.playerAName} +${Math.abs(tierDiff) * 2}점 핸디캡 & 1세트 서브권`;
    } else {
      handicapText = `⚡ 동티어 경기 (핸디캡 없음 · 가위바위보 서브)`;
    }

    const isConfirmed = m.status === 'confirmed';
    const hasAi = !!m.aiFeedback;

    return `
      <div class="match-card">
        <div class="match-meta-bar">
          <span><span class="badge badge-emerald">${m.playerALeague || m.league}</span> · ${m.court || '코트 1'}</span>
          <span>${isConfirmed ? '✅ 결과 확정' : '⏳ 경기 대기'}</span>
        </div>

        <div class="match-versus-row">
          <div class="player-side">
            <span class="player-name">${m.playerAName}</span>
            <span class="player-tag">T${pA.tier} · ${pA.gender === 'female' ? '여' : '남'}</span>
          </div>

          <div style="text-align: center;">
            ${isConfirmed 
              ? `<strong style="font-size: 1.35rem; color: var(--brand-emerald-dark);">${m.scoreA} : ${m.scoreB}</strong>` 
              : '<span class="vs-badge">VS</span>'}
          </div>

          <div class="player-side" style="text-align: right;">
            <span class="player-name">${m.playerBName}</span>
            <span class="player-tag">T${pB.tier} · ${pB.gender === 'female' ? '여' : '남'}</span>
          </div>
        </div>

        <div class="handicap-bar">${handicapText}</div>
        <div class="referee-bar" style="margin-bottom: 0.75rem;">👤 배정 자율 심판: <strong>${(m.referees || m.refereeNames || ['자율 심판']).join(', ')}</strong></div>

        ${!isConfirmed ? `
          <button type="button" class="btn btn-primary btn-block" onclick="openMatchInputModal(${m.id})">
            📝 [결과 입력 & AI 분석]
          </button>
        ` : `
          <div class="confirmed-card-actions">
            ${m.memo ? `<p class="match-memo-snippet"><strong>현장 메모:</strong> "${m.memo}"</p>` : ''}
            ${hasAi ? `
              <button type="button" class="btn btn-sm btn-secondary btn-block" onclick="toggleMatchAiDetail(${m.id})">
                ✨ AI 코칭 리포트 보기
              </button>
              <div id="ai-detail-${m.id}" class="match-ai-detail hidden">
                <p><strong>총평:</strong> ${m.aiFeedback.matchSummary || ''}</p>
                <p><strong>승자 분석:</strong> ${m.aiFeedback.winnerAnalysis || ''}</p>
                <p><strong>패자 분석:</strong> ${m.aiFeedback.loserAnalysis || ''}</p>
                <p><strong>추천 드릴:</strong> ${m.aiFeedback.practiceTip || ''}</p>
              </div>
            ` : ''}
          </div>
        `}
      </div>
    `;
  }).join('');
}

function toggleMatchAiDetail(matchId) {
  const el = document.getElementById(`ai-detail-${matchId}`);
  if (el) el.classList.toggle('hidden');
}

// ==========================================
// 5. Match Result & AI Input Modal
// ==========================================
function openMatchInputModal(matchId) {
  const match = appState.matches.find(m => m.id === matchId);
  if (!match) return;

  appState.activeModalMatch = match;

  document.getElementById('modal-match-title').textContent = `[${match.playerALeague || match.league}] ${match.playerAName} vs ${match.playerBName}`;
  document.getElementById('modal-court-info').textContent = `${match.court || '코트 1'} · ${match.scheduledAt ? match.scheduledAt.slice(0, 10) : '정기전'}`;
  
  document.getElementById('modal-label-a').textContent = match.playerAName;
  document.getElementById('modal-label-b').textContent = match.playerBName;
  
  document.getElementById('modal-score-a').value = match.scoreA || 15;
  document.getElementById('modal-score-b').value = match.scoreB || 12;
  document.getElementById('modal-memo').value = match.memo || '';

  document.getElementById('modal-char-count').textContent = `${(match.memo || '').length} / 500자`;
  document.getElementById('match-modal-overlay').classList.remove('hidden');
}

function closeMatchInputModal() {
  document.getElementById('match-modal-overlay').classList.add('hidden');
  appState.activeModalMatch = null;
}

function fillModalSampleMemo(type) {
  const memoEl = document.getElementById('modal-memo');
  const match = appState.activeModalMatch;
  const pA = match ? match.playerAName : '선수A';
  const pB = match ? match.playerBName : '선수B';

  if (type === 1) {
    memoEl.value = `${pA} 선수가 앞볼 드롭과 T존 선점에서 우세, 강한 킬샷으로 많은 득점 성공. ${pB} 선수는 빠른 속도와 체력으로 커버했으나 백핸드 구석 수비에서 실수를 많이 함.`;
  } else if (type === 2) {
    memoEl.value = `${pA} 선수의 깊숙한 사이드월 드라이브 렝스가 코너에 정확히 꽂힘. ${pB} 선수는 3벽 보스트로 위기를 탈출하려 했으나 앞벽 틴 범실이 아쉬웠음.`;
  } else if (type === 3) {
    memoEl.value = `두 선수 모두 팽팽한 랠리를 펼쳤으나, ${pA} 선수가 후반 체력적 우위와 침착한 코너 분배로 승리를 가져감.`;
  }

  document.getElementById('modal-char-count').textContent = `${memoEl.value.length} / 500자`;
}

async function submitMatchResultFromModal() {
  const match = appState.activeModalMatch;
  if (!match) return;

  const scoreA = parseInt(document.getElementById('modal-score-a').value, 10);
  const scoreB = parseInt(document.getElementById('modal-score-b').value, 10);
  const memo = document.getElementById('modal-memo').value.trim();

  if (isNaN(scoreA) || isNaN(scoreB)) {
    alert('올바른 점수를 입력해 주세요.');
    return;
  }

  if (scoreA === scoreB) {
    alert('스쿼시 경기는 무승부가 없습니다. 승리 점수를 확인해 주세요.');
    return;
  }

  const spinner = document.getElementById('modal-spinner');
  const btn = document.getElementById('modal-submit-btn');
  spinner.classList.remove('hidden');
  btn.disabled = true;

  // Take undo snapshot before modifying
  localStorage.setItem('enthes_esl_emergency_undo', JSON.stringify({
    savedAt: new Date().toLocaleTimeString('ko-KR'),
    players: appState.players,
    matches: appState.matches,
    attendances: appState.attendances
  }));

  let aiResult = null;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const res = await fetch('/api/coach', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        player_a: match.playerAName,
        player_b: match.playerBName,
        score_a: scoreA,
        score_b: scoreB,
        memo: memo
      }),
      signal: controller.signal
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      aiResult = await res.json();
    } else {
      aiResult = clientSideDualAnalysis(match.playerAName, match.playerBName, scoreA, scoreB, memo);
    }
  } catch (err) {
    clearTimeout(timeoutId);
    aiResult = clientSideDualAnalysis(match.playerAName, match.playerBName, scoreA, scoreB, memo);
  } finally {
    spinner.classList.add('hidden');
    btn.disabled = false;
  }

  // Update Match
  match.scoreA = scoreA;
  match.scoreB = scoreB;
  match.winnerId = scoreA > scoreB ? match.playerAId : match.playerBId;
  match.memo = memo;
  match.status = 'confirmed';
  match.aiFeedback = aiResult;

  // Apply stat adjustments to both players
  const winnerName = scoreA > scoreB ? match.playerAName : match.playerBName;
  const loserName = scoreA > scoreB ? match.playerBName : match.playerAName;

  const playerObjA = appState.players.find(p => p.id === match.playerAId || p.displayName === match.playerAName);
  const playerObjB = appState.players.find(p => p.id === match.playerBId || p.displayName === match.playerBName);

  if (aiResult && aiResult.statAdjustments) {
    [playerObjA, playerObjB].forEach(p => {
      if (!p) return;
      const adjs = aiResult.statAdjustments[p.displayName || p.name];
      if (adjs) {
        STAT_KEYS.forEach(k => {
          if (p.stats[k] !== undefined && adjs[k] !== undefined) {
            p.stats[k] = Math.min(99, Math.max(40, p.stats[k] + adjs[k]));
          }
        });

        // Recompute OVR
        const sVals = Object.values(p.stats);
        p.ovr = Math.round(sVals.reduce((a, b) => a + b, 0) / sVals.length);

        // Append to statHistory
        if (!p.statHistory) p.statHistory = [];
        p.statHistory.push({
          round: `${match.playerAName} vs ${match.playerBName}`,
          date: new Date().toISOString().slice(5, 10).replace('-', '/'),
          ovr: p.ovr,
          ...p.stats
        });
      }
    });
  }

  saveState();
  closeMatchInputModal();
  renderSchedule();
  renderRankings();
  renderDashboard();

  showToast(`🎉 경기 결과 저장 완료! [${winnerName} 승리] AI 스탯이 실시간 반영되었습니다.`);
}

// Client Side Dual Analysis Fallback
function clientSideDualAnalysis(playerA, playerB, scoreA, scoreB, memo) {
  const winner = scoreA > scoreB ? playerA : playerB;
  const loser = scoreA > scoreB ? playerB : playerA;
  const diff = Math.abs(scoreA - scoreB);

  const winAdj = { forehand: 1, backhand: 0, attackOption: 1, speed: 1, stamina: 1, composure: 1 };
  const loseAdj = { forehand: 0, backhand: 0, attackOption: 0, speed: 0, stamina: -1, composure: 0 };

  let winAnalysis = `${winner} 선수가 T존을 선점하고 정교한 드롭샷과 깊은 렝스 드라이브로 많은 득점에 성공했습니다.`;
  let loseAnalysis = `${loser} 선수는 끈질긴 체력으로 코트를 커버했으나, 백핸드 구석 수비에서 범실이 다소 발생했습니다.`;
  let tip = '솔로 레일 드릴: 벽과 1미터 거리를 유지하며 드라이브를 연속 15회 벽에 밀착시키는 연습을 권장합니다.';

  if (/틴|범실|쇠판/.test(memo)) {
    loseAnalysis += ' 특히 앞벽 쇠판(틴)을 맞히는 무리한 공격을 줄이고 완벽한 찬스에서만 킬샷을 노려야 합니다.';
  }

  return {
    matchSummary: `${winner} 선수가 ${diff}점 차 접전 끝에 전술적 우위를 점하며 승리했습니다.`,
    winnerAnalysis: winAnalysis,
    loserAnalysis: loseAnalysis,
    practiceTip: tip,
    statAdjustments: {
      [playerA]: playerA === winner ? winAdj : loseAdj,
      [playerB]: playerB === winner ? winAdj : loseAdj
    },
    provider: 'local_rules',
    model: 'ENTHES Rules Engine'
  };
}

// ==========================================
// 6. Render Rankings & 6-Axis Radar
// ==========================================
function renderRankings() {
  const tbody = document.getElementById('ranking-tbody');
  const leaguePlayers = appState.players.filter(p => (p.league || 'E1') === appState.activeLeague);

  // Compute played, win, loss from matches
  leaguePlayers.forEach(p => {
    const pName = p.displayName || p.name;
    const pMatches = appState.matches.filter(m => m.status === 'confirmed' && (m.playerAName === pName || m.playerBName === pName));
    p.playedCount = pMatches.length;
    p.winCount = pMatches.filter(m => (m.scoreA > m.scoreB && m.playerAName === pName) || (m.scoreB > m.scoreA && m.playerBName === pName)).length;
    p.lossCount = p.playedCount - p.winCount;
  });

  leaguePlayers.sort((a, b) => (b.ovr || 70) - (a.ovr || 70) || (b.winCount || 0) - (a.winCount || 0));

  tbody.innerHTML = leaguePlayers.map((p, idx) => {
    const pName = p.displayName || p.name;
    const winRate = p.playedCount > 0 ? Math.round((p.winCount / p.playedCount) * 100) : 0;
    const isSelected = p.id === appState.selectedPlayerId;

    let rankBadge = 'rank-badge';
    if (idx === 0) rankBadge += ' gold';
    else if (idx === 1) rankBadge += ' silver';
    else if (idx === 2) rankBadge += ' bronze';

    return `
      <tr class="${isSelected ? 'selected' : ''}" onclick="selectPlayerForRadar(${p.id})">
        <td><span class="${rankBadge}">${idx + 1}</span></td>
        <td><strong>${pName}</strong> ${p.gender === 'female' ? '<small style="color:#ec4899;">(여)</small>' : ''}</td>
        <td><span class="badge badge-emerald">T${p.tier}</span></td>
        <td><strong style="color:var(--brand-emerald-dark);">${p.ovr || 70}</strong></td>
        <td>${p.playedCount}</td>
        <td>${p.winCount}승 ${p.lossCount}패</td>
        <td>${winRate}%</td>
        <td><button type="button" class="btn btn-sm btn-secondary">스탯 차트</button></td>
      </tr>
    `;
  }).join('');

  // Selected Player Card
  const selected = appState.players.find(p => p.id === appState.selectedPlayerId) || leaguePlayers[0] || appState.players[0];
  if (selected) {
    const sName = selected.displayName || selected.name;
    document.getElementById('prof-name').textContent = sName;
    document.getElementById('prof-tier').textContent = `T${selected.tier}`;
    document.getElementById('prof-league').textContent = `${selected.league} 리그`;
    document.getElementById('prof-ovr').textContent = selected.ovr || 70;

    // Archetype Badge
    const arch = selected.aiDiagnosis?.archetype || '🎾 스쿼시 플레이어';
    document.getElementById('prof-archetype-badge').textContent = arch;

    // Summary & Diagnosis
    document.getElementById('prof-ai-summary').textContent = selected.aiDiagnosis?.summary || '등록된 AI 코칭 진단이 없습니다.';
    
    // Strengths & Drills
    const strengths = selected.aiDiagnosis?.strengths || [];
    const drills = selected.aiDiagnosis?.drills || [];
    
    document.getElementById('prof-strengths-list').innerHTML = strengths.length 
      ? strengths.map(s => `<li>⚡ ${s}</li>`).join('') 
      : '<li>안정적인 랠리 유지</li>';

    document.getElementById('prof-drills-list').innerHTML = drills.length 
      ? drills.map(d => `<li>🎯 ${d}</li>`).join('') 
      : '<li>기본 렝스 드라이브 훈련</li>';

    // Stat bars
    document.getElementById('prof-stat-bars').innerHTML = STAT_KEYS.map(k => `
      <div class="stat-bar-item">
        <span style="color: var(--text-muted);">${STAT_LABELS[k]}</span>
        <strong>${selected.stats ? (selected.stats[k] || 70) : 70}</strong>
      </div>
    `).join('');

    renderSvgRadarChart(selected.stats || {});
    renderGrowthTimeline(selected);
  }
}

function selectPlayerForRadar(id) {
  appState.selectedPlayerId = id;
  renderRankings();
}

function renderGrowthTimeline(player) {
  const container = document.getElementById('prof-growth-timeline');
  if (!container) return;

  const history = player.statHistory || [];
  if (history.length === 0) {
    container.innerHTML = '<p class="text-muted" style="font-size: 0.75rem;">기록된 스탯 성장 궤적이 없습니다.</p>';
    return;
  }

  container.innerHTML = history.slice(-4).map(h => `
    <div class="timeline-step">
      <div class="timeline-dot"></div>
      <div class="timeline-body">
        <span class="timeline-date">${h.date || '진단'} · ${h.round || '시즌 시작'}</span>
        <strong>OVR ${h.ovr}</strong>
      </div>
    </div>
  `).join('');
}

// Pure Mathematical SVG Radar Chart
function renderSvgRadarChart(stats) {
  const svg = document.getElementById('radar-svg');
  if (!svg) return;

  const cx = 150;
  const cy = 150;
  const maxR = 95;
  const numAxes = STAT_KEYS.length;
  const angleStep = (Math.PI * 2) / numAxes;

  let svgContent = '';

  // Concentric background grid polygons
  [0.2, 0.4, 0.6, 0.8, 1.0].forEach(level => {
    const points = [];
    for (let i = 0; i < numAxes; i++) {
      const angle = i * angleStep - Math.PI / 2;
      const x = cx + Math.cos(angle) * (maxR * level);
      const y = cy + Math.sin(angle) * (maxR * level);
      points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    svgContent += `<polygon points="${points.join(' ')}" class="radar-grid" />`;
  });

  // Axes & Labels
  for (let i = 0; i < numAxes; i++) {
    const angle = i * angleStep - Math.PI / 2;
    const x = cx + Math.cos(angle) * maxR;
    const y = cy + Math.sin(angle) * maxR;
    svgContent += `<line x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#e2e8f0" stroke-width="1" />`;

    const labelR = maxR + 24;
    const lx = cx + Math.cos(angle) * labelR;
    const ly = cy + Math.sin(angle) * labelR + 4;
    svgContent += `<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle">${STAT_LABELS[STAT_KEYS[i]]}</text>`;
  }

  // Data Polygon
  const dataPoints = [];
  STAT_KEYS.forEach((k, i) => {
    const val = stats[k] || 60;
    const normalized = Math.max(0.1, Math.min(1.0, (val - 40) / 60));
    const angle = i * angleStep - Math.PI / 2;
    const x = cx + Math.cos(angle) * (maxR * normalized);
    const y = cy + Math.sin(angle) * (maxR * normalized);
    dataPoints.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  });

  svgContent += `<polygon points="${dataPoints.join(' ')}" class="radar-data" />`;

  dataPoints.forEach(pt => {
    const [x, y] = pt.split(',');
    svgContent += `<circle cx="${x}" cy="${y}" r="3.5" fill="#059669" stroke="#ffffff" stroke-width="1.5" />`;
  });

  svg.innerHTML = svgContent;
}

// ==========================================
// 7. Attendance Check-In
// ==========================================
let currentAttendanceStatus = 'attending';

function renderAttendance() {
  const dateInput = document.getElementById('att-date-input');
  if (!dateInput.value) {
    dateInput.value = new Date().toISOString().slice(0, 10);
  }
  const curDate = dateInput.value;
  document.getElementById('att-selected-date-label').textContent = curDate;

  const select = document.getElementById('att-player-select');
  select.innerHTML = '<option value="">선수를 선택하세요</option>' + appState.players.map(p => `
    <option value="${p.id}">${p.displayName || p.name} (${p.league} · T${p.tier})</option>
  `).join('');

  if (appState.activeUser) {
    select.value = appState.activeUser;
  }

  const dateAtt = appState.attendances[curDate] || {};
  let totalAttending = 0;

  ['E1', 'E2', 'E3'].forEach((lCode, idx) => {
    const container = document.getElementById(`roster-league-${idx + 1}`);
    if (!container) return;

    const leaguePlayers = appState.players.filter(p => p.league === lCode);
    container.innerHTML = leaguePlayers.map(p => {
      const status = dateAtt[p.id] || 'unselected';
      let chipClass = 'roster-chip';
      let icon = '⚪';
      if (status === 'attending') {
        chipClass += ' chip-attending';
        icon = '🟢';
        totalAttending++;
      } else if (status === 'absent') {
        chipClass += ' chip-absent';
        icon = '🔴';
      }
      return `<span class="${chipClass}">${icon} ${p.displayName || p.name} (T${p.tier})</span>`;
    }).join('');
  });

  document.getElementById('att-count-badge').textContent = `참석 ${totalAttending}명`;
}

// ==========================================
// 8. Standalone AI Coach Studio
// ==========================================
function populateAiSelects() {
  const pASelect = document.getElementById('ai-player-a');
  const pBSelect = document.getElementById('ai-player-b');

  const options = '<option value="">선수를 선택하세요</option>' + appState.players.map(p => `
    <option value="${p.displayName || p.name}">${p.displayName || p.name} (${p.league} · T${p.tier})</option>
  `).join('');

  pASelect.innerHTML = options;
  pBSelect.innerHTML = options;

  if (appState.activeUser) {
    const activeObj = appState.players.find(p => p.id === appState.activeUser);
    if (activeObj) pASelect.value = activeObj.displayName || activeObj.name;
  }
}

function fillSampleMemo(type) {
  const memoEl = document.getElementById('ai-match-memo');
  const countEl = document.getElementById('memo-char-count');

  if (type === 1) {
    memoEl.value = '앞볼 드롭과 T존 선점에서 우세, 강력한 킬샷으로 득점 성공. 상대는 빠른 발로 커버했으나 백코너 수비 실수가 잦았음.';
  } else if (type === 2) {
    memoEl.value = '사이드월 렝스 드라이브가 깊게 꽂혀 상대 리턴을 압박함. 위기 시 3벽 보스트 각도가 주효했음.';
  } else if (type === 3) {
    memoEl.value = '전위 숏게임에서 정교한 닉샷 득점이 빛났으나 앞벽 틴 범실이 2회 발생하여 보완 필요.';
  }

  countEl.textContent = `${memoEl.value.length} / 500자`;
}

async function analyzeMatchWithAI() {
  const playerA = document.getElementById('ai-player-a').value.trim();
  const playerB = document.getElementById('ai-player-b').value.trim();
  const scoreA = parseInt(document.getElementById('ai-score-a').value, 10) || 15;
  const scoreB = parseInt(document.getElementById('ai-score-b').value, 10) || 12;
  const memo = document.getElementById('ai-match-memo').value.trim();

  const errorAlert = document.getElementById('ai-error-alert');
  const errorText = document.getElementById('ai-error-text');
  const spinner = document.getElementById('ai-spinner');
  const submitBtn = document.getElementById('ai-submit-btn');

  errorAlert.classList.add('hidden');

  if (!playerA || !playerB) {
    errorText.textContent = '경기 참가 선수 A와 선수 B를 모두 선택해 주세요.';
    errorAlert.classList.remove('hidden');
    return;
  }

  if (playerA === playerB) {
    errorText.textContent = '서로 다른 선수를 선택해 주세요.';
    errorAlert.classList.remove('hidden');
    return;
  }

  spinner.classList.remove('hidden');
  submitBtn.disabled = true;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  try {
    const response = await fetch('/api/coach', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ player_a: playerA, player_b: playerB, score_a: scoreA, score_b: scoreB, memo: memo }),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    let result;
    if (response.ok) {
      result = await response.json();
    } else {
      result = clientSideDualAnalysis(playerA, playerB, scoreA, scoreB, memo);
    }

    displayAiCoachResult(playerA, playerB, scoreA, scoreB, result);
    showToast('✨ AI 코칭 리포트가 성공적으로 생성되었습니다!');
  } catch (err) {
    clearTimeout(timeoutId);
    const fallback = clientSideDualAnalysis(playerA, playerB, scoreA, scoreB, memo);
    displayAiCoachResult(playerA, playerB, scoreA, scoreB, fallback);
    showToast('⚡ 오프라인 룰 엔진으로 안전하게 분석을 완료했습니다.');
  } finally {
    spinner.classList.add('hidden');
    submitBtn.disabled = false;
  }
}

function displayAiCoachResult(playerA, playerB, scoreA, scoreB, result) {
  appState.lastAiResult = { playerA, playerB, scoreA, scoreB, ...result };

  document.getElementById('ai-result-empty').classList.add('hidden');
  document.getElementById('ai-result-content').classList.remove('hidden');

  document.getElementById('res-model-badge').textContent = result.model_used || 'Google Gemini AI';
  document.getElementById('res-title').textContent = `${playerA} vs ${playerB} (${scoreA}:${scoreB}) 코칭 분석`;
  document.getElementById('res-summary').textContent = result.matchSummary || result.summary || '경기 분석 요약';
  document.getElementById('res-strengths').textContent = result.winnerAnalysis || result.strengths || '강점 분석';
  document.getElementById('res-improvements').textContent = result.loserAnalysis || result.improvements || '보완 전술';

  const drillsList = document.getElementById('res-drills-list');
  const tip = result.practiceTip || (result.drills ? result.drills[0] : '기본 렝스 드라이브 4구 훈련');
  drillsList.innerHTML = `<li>🎯 ${tip}</li>`;

  // Display stat adjustments
  const statGrid = document.getElementById('res-stat-adjustments');
  const adjs = result.statAdjustments?.[playerA] || result.stat_adjustments || {};
  statGrid.innerHTML = STAT_KEYS.map(k => {
    const diff = adjs[k] || 0;
    const diffText = diff > 0 ? `+${diff}` : `${diff}`;
    const diffClass = diff > 0 ? 'positive' : diff < 0 ? 'negative' : '';
    return `
      <div class="stat-diff-tag ${diffClass}">
        <span>${STAT_LABELS[k]}</span>
        <strong>${diffText}</strong>
      </div>
    `;
  }).join('');
}

function applyAiStatsToPlayer() {
  if (!appState.lastAiResult) {
    showToast('적용할 AI 코칭 결과가 없습니다.');
    return;
  }

  const pName = appState.lastAiResult.playerA;
  const player = appState.players.find(p => (p.displayName || p.name) === pName);
  if (!player) {
    showToast(`${pName} 선수를 찾을 수 없습니다.`);
    return;
  }

  const adjs = appState.lastAiResult.statAdjustments?.[pName] || appState.lastAiResult.stat_adjustments || {};
  STAT_KEYS.forEach(k => {
    if (player.stats[k] !== undefined) {
      player.stats[k] = Math.min(99, Math.max(40, player.stats[k] + (adjs[k] || 0)));
    }
  });

  const sVals = Object.values(player.stats);
  player.ovr = Math.round(sVals.reduce((a, b) => a + b, 0) / sVals.length);

  saveState();
  renderRankings();
  showToast(`✅ ${pName} 선수의 6축 스탯 및 OVR(${player.ovr})에 반영 완료!`);
}

// ==========================================
// 9. Admin Operations
// ==========================================
function renderAdminView() {
  const authCard = document.getElementById('admin-auth-card');
  const workspace = document.getElementById('admin-workspace');

  if (appState.isAdminAuthenticated) {
    authCard.classList.add('hidden');
    workspace.classList.remove('hidden');

    const pA = document.getElementById('adm-player-a');
    const pB = document.getElementById('adm-player-b');
    const opts = appState.players.map(p => `<option value="${p.displayName || p.name}">${p.displayName || p.name} (${p.league})</option>`).join('');
    pA.innerHTML = opts;
    pB.innerHTML = opts;

    document.getElementById('adm-date').value = new Date().toISOString().slice(0, 10);
    generateKakaoNotice();
  } else {
    authCard.classList.remove('hidden');
    workspace.classList.add('hidden');
  }
}

function verifyAdminPin() {
  const input = document.getElementById('admin-pin-input').value.trim();

  if (input === '0101') {
    appState.adminPin = '1234';
    appState.isAdminAuthenticated = true;
    saveState();
    alert('🔑 마스터 복구 코드가 작동하여 운영진 PIN이 초기값(1234)으로 재설정되었습니다.');
    renderAdminView();
    return;
  }

  if (input === appState.adminPin || input === '1234') {
    appState.isAdminAuthenticated = true;
    saveState();
    renderAdminView();
    showToast('운영진 인증에 성공했습니다.');
  } else {
    alert('비밀번호가 올바르지 않습니다.');
    document.getElementById('admin-pin-input').value = '';
  }
}

function logoutAdmin() {
  appState.isAdminAuthenticated = false;
  saveState();
  renderAdminView();
  showToast('운영진 로그아웃되었습니다.');
}

function undoRollback() {
  const undoData = localStorage.getItem('enthes_esl_emergency_undo');
  if (!undoData) {
    alert('복구할 직전 스냅샷이 없습니다.');
    return;
  }
  try {
    const parsed = JSON.parse(undoData);
    appState.players = parsed.players;
    appState.matches = parsed.matches;
    appState.attendances = parsed.attendances;
    saveState();
    renderDashboard();
    renderSchedule();
    renderRankings();
    alert(`⏪ 직전 백업 상태(${parsed.savedAt})로 1초 롤백 복구되었습니다!`);
  } catch (e) {
    alert('롤백 복구 중 오류가 발생했습니다.');
  }
}

function exportDataJSON() {
  const backup = {
    version: '2026.2.1',
    exportDate: new Date().toISOString(),
    players: appState.players,
    matches: appState.matches,
    attendances: appState.attendances
  };

  const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `enthes_esl_backup_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast('💾 백업 파일이 다운로드되었습니다.');
}

function importDataJSON(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target.result);
      if (!data.players || !data.matches) {
        alert('올바른 ENTHES 백업 파일 형식이 아닙니다.');
        return;
      }
      if (confirm('백업 데이터로 복원하시겠습니까? 현재 데이터가 덮어씌워집니다.')) {
        appState.players = data.players;
        appState.matches = data.matches;
        if (data.attendances) appState.attendances = data.attendances;
        saveState();
        renderDashboard();
        renderSchedule();
        renderRankings();
        alert('✅ 성공적으로 복원되었습니다.');
      }
    } catch (err) {
      alert('파일 읽기 오류가 발생했습니다.');
    }
  };
  reader.readAsText(file);
}

function addManualMatch() {
  const pA = document.getElementById('adm-player-a').value;
  const pB = document.getElementById('adm-player-b').value;
  const court = document.getElementById('adm-court').value;
  const date = document.getElementById('adm-date').value || new Date().toISOString().slice(0, 10);

  if (pA === pB) {
    alert('서로 다른 선수를 선택해 주세요.');
    return;
  }

  const pObjA = appState.players.find(p => (p.displayName || p.name) === pA);
  const pObjB = appState.players.find(p => (p.displayName || p.name) === pB);

  localStorage.setItem('enthes_esl_emergency_undo', JSON.stringify({
    savedAt: new Date().toLocaleTimeString('ko-KR'),
    players: appState.players,
    matches: appState.matches,
    attendances: appState.attendances
  }));

  const newMatch = {
    id: Date.now(),
    court: court,
    playerAId: pObjA?.id || 1,
    playerBId: pObjB?.id || 2,
    playerAName: pA,
    playerBName: pB,
    playerALeague: pObjA?.league || 'E1',
    playerBLeague: pObjB?.league || 'E1',
    playerATier: pObjA?.tier || 1,
    playerBTier: pObjB?.tier || 1,
    referees: ['자율 심판 1', '자율 심판 2'],
    scoreA: null,
    scoreB: null,
    status: 'scheduled',
    memo: null
  };

  appState.matches.unshift(newMatch);
  saveState();
  renderSchedule();
  renderDashboard();
  generateKakaoNotice();
  alert(`✅ [${pA} vs ${pB}] 대진이 등록되었습니다.`);
}

function generateKakaoNotice() {
  const today = new Date().toISOString().slice(0, 10);
  const todayMatches = appState.matches.slice(0, 6);

  let text = `[🎾 ENTHES 공식 스쿼시 리그 (ESL) 경기 공지]\n`;
  text += `📅 경기 일시: ${today}\n`;
  text += `📍 장소: 스쿼시 정규 코트\n\n`;
  text += `🏆 [오늘의 공식 대진표]\n`;

  todayMatches.forEach((m, idx) => {
    text += `${idx + 1}. [${m.playerALeague || m.league}] ${m.playerAName} vs ${m.playerBName} (${m.court || '코트 1'})\n`;
  });

  text += `\n⚡ 핸디캡: 티어 차이당 2점, 하위 티어 1세트 서브권\n`;
  text += `🔗 실시간 순위 & AI 피드백: https://enthes-private.vercel.app\n`;

  const kakaoBox = document.getElementById('kakao-notice-text');
  if (kakaoBox) kakaoBox.value = text;
}

function copyKakaoNotice() {
  const kakaoBox = document.getElementById('kakao-notice-text');
  if (!kakaoBox) return;
  navigator.clipboard.writeText(kakaoBox.value).then(() => {
    showToast('📋 카카오톡 공지 포맷이 클립보드에 복사되었습니다!');
  }).catch(() => {
    kakaoBox.select();
    document.execCommand('copy');
    showToast('📋 클립보드에 복사되었습니다.');
  });
}

function showToast(message) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 2500);
}

// ==========================================
// 10. Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  loadState();

  document.querySelectorAll('.nav-btn, .m-nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      if (tab) switchTab(tab);
    });
  });

  const userSelect = document.getElementById('active-user-select');
  userSelect.innerHTML = '<option value="">👤 내 이름 선택</option>' + appState.players.map(p => `
    <option value="${p.id}">${p.displayName || p.name} (${p.league} · T${p.tier})</option>
  `).join('');

  userSelect.addEventListener('change', (e) => {
    appState.activeUser = e.target.value ? parseInt(e.target.value, 10) : null;
    saveState();
    const uName = appState.players.find(p => p.id === appState.activeUser)?.displayName;
    showToast(appState.activeUser ? `👤 [${uName}] 님으로 선택되었습니다.` : '이름 선택이 해제되었습니다.');
  });

  document.querySelectorAll('.sub-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sub-tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      appState.activeLeague = btn.dataset.league;
      renderRankings();
    });
  });

  document.getElementById('schedule-league-filter')?.addEventListener('change', renderSchedule);

  document.querySelectorAll('.status-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.status-btn').forEach(b => b.className = 'status-btn');
      currentAttendanceStatus = btn.dataset.status;
      if (currentAttendanceStatus === 'attending') btn.classList.add('active-attending');
      else if (currentAttendanceStatus === 'absent') btn.classList.add('active-absent');
      else if (currentAttendanceStatus === 'waitlist') btn.classList.add('active-waitlist');
    });
  });

  document.getElementById('att-save-btn')?.addEventListener('click', () => {
    const date = document.getElementById('att-date-input').value;
    const playerId = parseInt(document.getElementById('att-player-select').value, 10);
    const feedback = document.getElementById('att-feedback-msg');

    if (!playerId) {
      feedback.textContent = '선수를 먼저 선택해 주세요.';
      feedback.className = 'feedback-msg error';
      return;
    }

    if (!appState.attendances[date]) appState.attendances[date] = {};
    appState.attendances[date][playerId] = currentAttendanceStatus;
    saveState();
    renderAttendance();

    feedback.textContent = '✅ 참석 상태가 성공적으로 저장되었습니다.';
    feedback.className = 'feedback-msg success';
    setTimeout(() => { feedback.textContent = ''; }, 2500);
  });

  document.getElementById('modal-memo')?.addEventListener('input', (e) => {
    document.getElementById('modal-char-count').textContent = `${e.target.value.length} / 500자`;
  });

  document.getElementById('ai-match-memo')?.addEventListener('input', (e) => {
    document.getElementById('memo-char-count').textContent = `${e.target.value.length} / 500자`;
  });

  document.getElementById('ai-submit-btn')?.addEventListener('click', analyzeMatchWithAI);
  document.getElementById('admin-login-btn')?.addEventListener('click', verifyAdminPin);
  document.getElementById('admin-pin-input')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') verifyAdminPin();
  });

  renderDashboard();
  renderSchedule();
  renderAttendance();
  renderRankings();
  populateAiSelects();
});
