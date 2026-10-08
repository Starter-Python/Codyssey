# 🎾 ENTHES — Official Squash League (ESL) & AI Studio

> **과제명**: AI 활용 학습 A1-3 — AI 웹 서비스 빌딩  
> **배포 URL**: [https://enthes-private.vercel.app](https://enthes-private.vercel.app)  
> **로컬 원본 프로젝트 위치**: `/Users/macbook/Documents/antigravity/ENTHES-private`  
> **과제 제출 패키지 위치**: `/Users/macbook/Documents/antigravity/Manus/AI 활용 학습 A1-3`  
> **GitHub 저장소**: [`Starter-Python/Manus`](https://github.com/Starter-Python/Manus) (`AI 활용 학습 A1-3` 폴더)  
> **기술 스택**: 순수 바닐라 HTML5 / CSS3 / JavaScript (ES6+) + Vercel Serverless Functions (Python 3.9+) + Google Gemini AI

---

## 📌 1. 서비스 소개 (Overview)

**ENTHES (Enjoy The Squash)**는 스쿼시 정규 리그(ESL: 2026 하반기 공식 33인 체제)를 공정하고 스마트하게 운영하며, 경기 결과와 현장 관찰 메모를 바탕으로 맞춤형 피드백을 생성하는 **AI 경기 분석 & 코칭 웹 플랫폼**입니다.

### 🌟 핵심 가치
1. **2026 하반기 33인 공식 리그 체제 (E1·E2·E3)**:
   - **E1 리그 (1부 10명)**: 총 18경기, 최소 7경기 필수 출전
   - **E2 리그 (2부 15명)**: 총 28경기, 최소 7경기 필수 출전
   - **E3 리그 (3부 8명)**: 총 14경기, 최소 7경기 필수 출전
2. **원클릭 대진 카드 내 [결과 입력 & AI 분석]**:
   - 대진 카드에서 바로 스코어와 특이사항 메모(선택)를 입력하면 Gemini AI가 양 선수의 플레이를 동시 식별하여 개별 스탯 증감 및 맞춤 드릴을 산출합니다.
3. **선수별 6대 역량 스탯 & 아키타입 AI 진단**:
   - `포핸드`, `백핸드`, `공격옵션`, `스피드`, `체력`, `침착성` 6대 역량을 순수 SVG 레이더 차트로 시각화.
   - 선수의 플레이스타일에 따른 AI 아키타입(예: 👑 구석 찌르기 장인, ⚡ 시원한 파워 스트로커 등) 및 OVR 성장 궤적 추적.
4. **1초 비상 롤백 및 데이터 불변성**:
   - 실수로 인한 점수 오입력 시 직전 상태로 100% 자동 원상복구되는 1초 롤백(Undo)과 JSON 백업 지원.

---

## 📱 2. 실제 모바일 UI 스크린샷 (Real iPhone Screenshots)

과제 요구사항에 따른 모바일 반응형 및 AI 기능 동작 실제 스크린샷입니다:

| **1단계: [대진] 탭 확인** | **2단계: [결과 입력 & AI 분석]** | **3단계: 점수 & 메모 입력** |
| :---: | :---: | :---: |
| ![1단계](./evidence/screenshots/match_step1_tab.jpg) | ![2단계](./evidence/screenshots/match_step2_card.jpg) | ![3단계](./evidence/screenshots/match_step3_input.jpg) |
| 당일 경기 일정 및 코트 배정 | 경기 카드의 결과 입력 버튼 터치 | 세트 점수 및 1~2줄 메모 작성 |

| **4단계: 실시간 순위 반영** | **5단계: AI 코칭 피드백** | **6단계: 6대 스탯 & 성장 궤적** |
| :---: | :---: | :---: |
| ![4단계](./evidence/screenshots/match_step5_rank.jpg) | ![5단계](./evidence/screenshots/match_step6_feedback.jpg) | ![6단계](./evidence/screenshots/match_step7_growth.png) |
| 승패 집계 및 OVR 실시간 변동 | AI 총평, 승자/패자 분석, 드릴 | 6축 레이더 차트 및 회차별 추이 |

> 📌 상세 이용 안내: [`evidence/ENTHES_ESL_부원가이드.md`](./evidence/ENTHES_ESL_부원가이드.md)

---

## 🛠️ 3. 기술 스택 & 시스템 아키텍처

```
[ Frontend (Vanilla) ]             [ Backend (Serverless) ]            [ External AI ]
┌───────────────────────────┐      ┌─────────────────────────────┐     ┌───────────────────────┐
│ index.html (Semantic HTML)│ ───► │ api/coach.py                │ ──► │ Google Gemini API     │
│ styles.css (Modern CSS3)  │      │ (BaseHTTPRequestHandler)    │     │ (gemini-2.5-flash)    │
│ app.js (Pure Vanilla JS)  │ ◄─── │ (Urllib / REST Protocol)    │ ◄── │                       │
└───────────────────────────┘      └─────────────────────────────┘     └───────────────────────┘
  • E1/E2/E3 6개 탭 네비게이션          • 환경 변수(GEMINI_API_KEY) 격리        • 양 선수 동시 개별 분석
  • 카드 내 결과 입력 모달 팝업          • 3단계 에러 & 내장 룰 엔진 Fallback      • 인플레이션 방지 (±1~2점)
  • 순수 SVG 레이더 차트 엔진           • 무결성 검증 및 제어문자 정제
```

- **프론트엔드**: 순수 바닐라 HTML5, CSS3, JavaScript (ES6+), React/Vue 등 외부 프레임워크 배제
- **백엔드**: Vercel Serverless Functions (`api/coach.py`, Python 3.9+)
- **AI 연동**: Google Gemini Interactions API (`gemini-2.5-flash`)
- **보안**: `GEMINI_API_KEY` 환경 변수 서버리스 격리 (프론트엔드 및 깃허브 코드 노출 0%)

---

## 📂 4. 디렉터리 구성

```text
AI 활용 학습 A1-3/
├── api/
│   └── coach.py               # Vercel Python Serverless Function (POST /api/coach)
├── assets/
│   ├── data/                  # 33인 공식 데이터셋 (players, leagues, matches)
│   └── guide/                 # PWA 및 부원 안내서 스크린샷 10종
├── evidence/                  # 과제 증빙 패키지
│   ├── screenshots/           # 실제 모바일 구동 증빙 스크린샷 10종
│   ├── ENTHES_ESL_부원가이드.md# 공식 부원 이용 안내서 (PDF/Markdown)
│   ├── AI_CODING_PROCESS.md   # AI 코딩 도구 대화 내역 및 프롬프트 로그
│   └── EVIDENCE_GUIDE.md      # 데스크톱/모바일 반응형 및 AI 동작 증빙
├── .env.example               # 환경 변수 템플릿
├── .gitignore                 # 보안 및 임시 파일 제외 규칙
├── GEMINI_VERCEL_ENV_GUIDE.md # Vercel 환경 변수 등록 가이드
├── index.html                 # 순수 HTML5 메인 웹앱
├── package.json               # 프로젝트 설정 메타데이터
├── README.md                  # 본 문서
├── REQUIREMENTS_CHECK.md      # 과제 요구사항 100% 충족 대조표
├── requirements.txt           # Vercel Python 의존성 정의
├── SERVICE_PLAN.md            # 공식 서비스 기획서
├── styles.css                 # 순수 CSS3 반응형 스타일시트
├── app.js                     # 순수 바닐라 JS 상태 및 AI 연동 스크립트
└── vercel.json                # Vercel 배포 및 라우팅 설정
```

---

## 🚀 5. 로컬 실행 및 테스트 방법

### 1) 프론트엔드 웹 서버 실행
```bash
cd "Manus/AI 활용 학습 A1-3"
python3 -m http.server 3000
```
브라우저에서 `http://localhost:3000` 접속

### 2) 백엔드 파이썬 AI 분석기 단독 검증
```bash
python3 -c "
import sys; sys.path.insert(0, './api')
import coach
res = coach.rule_based_dual_analysis('임영현', '조기호', 15, 13, '임영현 T존 선점 및 드라이브 우세')
print('Summary:', res['matchSummary'])
print('Adjustments:', res['statAdjustments'])
"
```

---

## ☁️ 6. Vercel 배포 및 환경 변수 등록

Vercel 대시보드 ➔ **Settings** ➔ **Environment Variables**에서 다음 키를 설정합니다:

| 키 (Key) | 기본값 | 설명 |
|---|---|---|
| `GEMINI_API_KEY` | `AIzaSy...` | [Google AI Studio](https://aistudio.google.com/app/apikey)에서 발급한 API 키 |
| `GEMINI_MODEL` | `gemini-2.5-flash` | 사용할 Gemini 모델명 |

---

## 📄 7. 과제 제출 패키지 5종 완비 내역

1. **배포된 웹 서비스**: [https://enthes-private.vercel.app](https://enthes-private.vercel.app)
2. **GitHub 저장소**: [`Starter-Python/Manus`](https://github.com/Starter-Python/Manus) (`AI 활용 학습 A1-3`)
3. **README.md**: 본 문서 ([README.md](./README.md))
4. **서비스 기획서**: [`SERVICE_PLAN.md`](./SERVICE_PLAN.md)
5. **증빙 자료**: [`evidence/EVIDENCE_GUIDE.md`](./evidence/EVIDENCE_GUIDE.md), [`evidence/AI_CODING_PROCESS.md`](./evidence/AI_CODING_PROCESS.md), [`evidence/ENTHES_ESL_부원가이드.md`](./evidence/ENTHES_ESL_부원가이드.md)
