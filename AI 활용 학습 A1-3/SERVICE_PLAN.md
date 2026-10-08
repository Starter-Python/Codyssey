# 📋 [서비스 기획서] ENTHES 공식 스쿼시 리그 (ESL) & AI 코칭 스튜디오

---

## 1. 서비스 개요 (Service Overview)

| 항목 | 내용 |
|---|---|
| **서비스명** | **ENTHES (Enjoy The Squash) — ESL 정규 리그 & AI 코치** |
| **서비스 정의** | 2026 하반기 스쿼시 정규 리그(ESL 33인 체제) 운영 및 Google Gemini 기반 실시간 경기 분석·스탯 변환 AI 웹 플랫폼 |
| **타겟 사용자** | 1) 스쿼시 동아리 회원(33명 공식 선수단): 본인 대진 확인, 경기 결과 & 메모 등록, 6축 스탯 및 AI 진단 열람<br />2) 동아리 운영진: 공정 대진 자동 편성, 결과 확정/수정, 1초 롤백 복구, 단톡방 카톡 공지 생성 |
| **핵심 가치** | 1) 복잡한 3개 리그(E1, E2, E3) 출전수 및 티어 핸디캡 자동 계산<br />2) 경기 메모 한 줄로 승자/패자 플레이를 동시 식별하여 개별 6축 스탯 및 실천 드릴을 산출하는 스마트 AI 코칭 |

---

## 2. 타겟 사용자 및 해결 과제 (Problem & Solution)

### 1) 동아리 회원 (Player)
- **Problem**: "경기가 끝나도 내 플레이의 구체적인 강점이나 보완점을 알기 어렵고, 스쿼시 역량을 객관적으로 파악할 지표가 부족함."
- **Solution**:
  - 경기 종료 후 대진 카드에서 **[결과 입력 & AI 분석]** 버튼을 터치하여 스코어와 1~2줄 메모만 입력하면, AI가 승리 요인과 패배 원인을 분석하고 맞춤 드릴을 제시합니다.
  - `포핸드`, `백핸드`, `공격옵션`, `스피드`, `체력`, `침착성` 6대 역량 레이더 차트와 OVR 성장 궤적을 통해 본인의 성장을 시각적으로 확인합니다.

### 2) 동아리 운영진 (Administrator)
- **Problem**: "33명의 선수가 속한 E1(10명), E2(15명), E3(8명) 리그에서 최소 7경기 출전 규정, 티어 핸디캡(+2점), 하위 티어 우선 서브권을 수작업으로 관리하기 어려움."
- **Solution**:
  - 리그 규정이 내장된 스마트 스케줄러로 자동 대진 및 핸디캡을 1초 만에 산출합니다.
  - 실수로 점수를 잘못 기입하거나 삭제하더라도 **1초 Undo 롤백** 버튼으로 직전 상태를 완벽 복원합니다.

---

## 3. 페이지 및 섹션 구성 (Information Architecture)

```
ENTHES ESL WebApp
├── 🏠 1. 홈 대시보드 (Dashboard)
│   ├── 시즌 현황 카운터 (33명 선수단, 확정 경기, 참석 현황, AI 리포트 건수)
│   ├── 진행 예정 주요 대진 카드 (결과 입력 원클릭 이동)
│   └── 최근 확정 결과 요약
├── 📅 2. 대진표 (Schedule)
│   ├── 리그별 필터링 (전체, E1 1부, E2 2부, E3 3부)
│   ├── 날짜별 대진 카드 (코트, 시간, 티어별 핸디캡, 서브권, 자율 심판)
│   ├── 팝업 모달: [결과 입력 & AI 분석] (세트 점수 + 관찰 메모 입력)
│   └── 확정 경기: AI 피드백 펼쳐보기 (총평, 승자/패자 분석, 추천 드릴)
├── ⚡ 3. 참석 체크 (Attendance)
│   ├── 경기 날짜 및 선수 선택
│   ├── 참석 / 불참 / 대기 원터치 상태 등록
│   └── E1·E2·E3 리그별 실시간 출석 현황 칩(Chip) 뷰어
├── 📊 4. 순위 & 6축 스탯 (Rankings & Radar)
│   ├── E1(10명), E2(15명), E3(8명) 리그별 실시간 순위표
│   ├── 순수 SVG 6축 레이더 차트 (포핸드, 백핸드, 공격옵션, 스피드, 체력, 침착성)
│   ├── 수석 코치 AI 정밀 진단 (아키타입 뱃지, 강점 요인, 추천 드릴)
│   └── OVR 성장 궤적 타임라인
├── ✨ 5. AI 코칭 스튜디오 (AI Coach Simulator)
│   ├── 임의의 두 선수 선택 및 스코어·메모 입력 폼
│   ├── Gemini AI 비동기 분석 호출 (/api/coach)
│   └── 양 선수 6대 스탯 변동량 시뮬레이션 및 프로필 반영
└── ⚙️ 6. 운영진 데스크 (Admin Operations)
    ├── 운영진 4자리 PIN 인증 (1234, 마스터 리셋 0101)
    ├── 신규 경기 대진 수동 추가
    ├── 1초 Undo 롤백 복구 & 전체 데이터 JSON 백업/복원
    └── 단톡방 공지 포맷 1초 클립보드 복사
```

---

## 4. AI 기능 상세 설계 (AI Feature Specification)

### 1) 기능 개요: 양 선수 동시 개별 코칭 및 6축 스탯 산출 엔진
- **엔드포인트**: `POST /api/coach` (Vercel Python Serverless Function)
- **AI 모델**: Google Gemini API (`gemini-2.5-flash`)
- **특징**: 하나의 현장 관찰 메모를 통해 승자와 패자 각각의 강점과 약점을 식별하고, 인플레이션을 방지하는 정량적 스탯 변동량(승자 +1~2, 패자 -1~0)을 산출.

### 2) 입력 (Input) 명세
| 필드명 | 타입 | 필수 여부 | 유효성 검사 기준 |
|---|---|:---:|---|
| `player_a` | string | **필수** | 선수 A 이름 (선수 B와 중복 불가) |
| `player_b` | string | **필수** | 선수 B 이름 (선수 A와 중복 불가) |
| `score_a` | integer | **필수** | 선수 A 세트 득점 (0 ~ 30 정수, 동점 불가) |
| `score_b` | integer | **필수** | 선수 B 세트 득점 (0 ~ 30 정수, 동점 불가) |
| `memo` | string | 선택 | 현장 경기 특이사항 메모 (최대 500자, 미입력 시 스코어 기반 분석) |

### 3) 출력 (Output) 명세
```json
{
  "matchSummary": "임영현 선수가 김형석 선수를 상대로 15:10 (5점 차) 접전 끝에 승리했습니다.",
  "winnerAnalysis": "임영현 선수가 T존을 선점하고 정교한 드롭샷과 강력한 킬샷으로 많은 득점에 성공했습니다.",
  "loserAnalysis": "김형석 선수는 끈질긴 체력으로 코트를 커버했으나, 백코너 수비에서 실수가 잦았습니다.",
  "practiceTip": "솔로 레일 드릴: 벽과 1미터 거리를 유지하며 드라이브를 연속 15회 벽에 밀착시키는 연습을 권장합니다.",
  "statAdjustments": {
    "임영현": { "forehand": 1, "backhand": 0, "attackOption": 2, "speed": 1, "stamina": 1, "composure": 1 },
    "김형석": { "forehand": 0, "backhand": -1, "attackOption": 0, "speed": 0, "stamina": -1, "composure": 0 }
  },
  "provider": "gemini",
  "model_used": "Google Gemini (gemini-2.5-flash)"
}
```

### 4) 3단계 UX 실패 처리 기준

1. **빈 입력 (Validation Error)**:
   - 선수 미선택 또는 스코어 미입력 시 경고 안내 및 요청 차단. (단, 메모는 선택 사항으로 점수만으로도 분석 가능)
2. **API 장애 및 키 누락 (4xx/5xx)**:
   - `GEMINI_API_KEY` 미등록 또는 Google 서버 오류 시 내장 휴리스틱 룰 엔진(`rule_based_dual_analysis`)으로 100% 자동 폴백하여 무중단 분석 제공.
3. **지연 및 타임아웃 (10s Timeout)**:
   - `AbortController` 10초 타임아웃 가드레일이 작동하여 로딩 스피너를 해제하고 로컬 분석 결과로 즉각 전환.

---

## 5. 데이터 모델 설계 (Data Schema)

### 33인 공식 선수 객체 (`Player`)
```typescript
interface Player {
  id: number;
  displayName: string;
  league: "E1" | "E2" | "E3";
  tier: 1 | 2 | 3;
  gender: "male" | "female";
  stats: {
    forehand: number;     // 포핸드 (드라이브 파워 & 벽 밀착)
    backhand: number;     // 백핸드 (백코너 수비 & 리턴)
    attackOption: number; // 공격옵션 (드롭, 닉샷, 킬샷, 발리)
    speed: number;        // 스피드 (풋워크 & 코트 커버)
    stamina: number;      // 체력 (랠리 지속력 & 후반 집중력)
    composure: number;    // 침착성 (보스트 탈출 & 에러 억제)
  };
  statHistory: Array<{
    round: string;
    date: string;
    ovr: number;
    [statKey: string]: any;
  }>;
  aiDiagnosis: {
    archetype: string; // 예: "👑 구석 찌르기 장인"
    summary: string;
    strengths: string[];
    weaknesses: string[];
    drills: string[];
  };
}
```

### 경기 대진 객체 (`Match`)
```typescript
interface Match {
  id: number; // 예: 20260825001
  court: string;
  playerAId: number;
  playerBId: number;
  playerAName: string;
  playerBName: string;
  playerALeague: "E1" | "E2" | "E3";
  playerBLeague: "E1" | "E2" | "E3";
  playerATier: number;
  playerBTier: number;
  refereeNames: string[];
  scoreA: number | null;
  scoreB: number | null;
  winnerId: number | null;
  memo: string | null;
  aiFeedback: {
    matchSummary: string;
    winnerAnalysis: string;
    loserAnalysis: string;
    practiceTip: string;
    statAdjustments: Record<string, Record<string, number>>;
    provider: string;
    model: string;
  } | null;
  status: "scheduled" | "confirmed";
}
```
