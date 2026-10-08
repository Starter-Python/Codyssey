# 📋 [요구사항 점검표] AI 활용 학습 A1-3 과제 전수 충족 대조표

본 문서는 **AI 활용 학습 A1-3 과제(AI 웹 서비스 빌딩)**의 전체 요구사항 및 제약조건에 대해, 2026 하반기 공식 33인 체제(E1·E2·E3)로 발전된 최신 결과물을 바탕으로 전수 점검한 공식 대조표입니다.

---

## 1. 제출 패키지 5종 완비 점검

| No | 과제 요구 항목 | 세부 요구 기준 | 구현 파일 및 실제 위치 | 충족 상태 |
|:--:|---|---|---|:---:|
| **1** | **배포된 웹 서비스** | • 실제 접속 가능한 Vercel URL<br />• 3개 이상 섹션/메뉴 이동<br />• 모바일 반응형 완비<br />• AI API 연동(입력 $\rightarrow$ 출력) | • URL: [https://enthes-private.vercel.app](https://enthes-private.vercel.app)<br />• 6대 섹션: 홈, 대진, 참석, 순위·스탯, AI 분석, 운영진<br />• 모바일 하단 탭바 & 10종 실제 스크린샷 완비<br />• 경기 스코어 & 메모 $\rightarrow$ Gemini AI 코칭 출력 | **100% 충족** |
| **2** | **GitHub 저장소** | • 프로젝트 코드 업로드<br />• 프론트(HTML/CSS/JS)와 백엔드(`api/`) 분리 | • 저장소: [`Starter-Python/Manus`](https://github.com/Starter-Python/Manus)<br />• 경로: `AI 활용 학습 A1-3/` 폴더 내 분리 완료 | **100% 충족** |
| **3** | **README.md** | • 서비스 소개, 기술 스택<br />• 실행/배포 방법, 배포 URL<br />• 환경 변수(API 키) 설정 방법 | • [`README.md`](./README.md)<br />• 로컬 원본 위치 및 배포 환경 변수 가이드 완비 | **100% 충족** |
| **4** | **서비스 기획서** | • 서비스 목적, 타겟 사용자<br />• 페이지 구성, 핵심 기능<br />• AI 입력/출력/실패 처리 기준 | • [`SERVICE_PLAN.md`](./SERVICE_PLAN.md)<br />• 33인 E1·E2·E3 리그 규정, AI 입출력 스키마 명세 | **100% 충족** |
| **5** | **증빙 자료** | • 데스크톱 + 모바일 + AI 동작 증빙<br />• AI 코딩 도구 대화 로그 | • [`evidence/EVIDENCE_GUIDE.md`](./evidence/EVIDENCE_GUIDE.md)<br />• [`evidence/screenshots/`](./evidence/screenshots/) (실제 스크린샷 10종)<br />• [`evidence/AI_CODING_PROCESS.md`](./evidence/AI_CODING_PROCESS.md) | **100% 충족** |

---

## 2. 세부 기능 및 기술 제약 점검

| 항목 | 요구 명세 | 구현 세부 내용 | 결과 |
|---|---|---|:---:|
| **프론트엔드 제약** | • 순수 HTML/CSS/JavaScript (바닐라)<br />• React/Vue 등 프레임워크 사용 금지 | • 외부 라이브러리 0% 순수 바닐라 JS DOM 제어<br />• 삼각함수 기반 순수 SVG 6축 레이더 차트 자체 렌더링 | **PASS** |
| **백엔드 제약** | • Vercel Serverless Functions (Python)<br />• `api/` 폴더 내 구현 및 requirements.txt | • `api/coach.py` (`BaseHTTPRequestHandler` 표준)<br />• `requirements.txt` (`google-genai`, `requests`) | **PASS** |
| **AI 기능 UX** | • 입력 폼 제공 및 결과 화면 표시<br />• 실패 처리 3종 안내 (빈 입력, API 오류, 타임아웃) | • 대진 카드 내 [결과 입력 & AI 분석] 팝업 모달 제공<br />• 1) 필수값 검증 배너 2) API 장애 시 로컬 룰 엔진 즉시 폴백 3) 10초 타임아웃 방어 가드레일 | **PASS** |
| **보안 제약** | • API 키 환경 변수 관리<br />• 프론트 코드/README/스크린샷 노출 금지 | • 서버리스 백엔드 `os.environ.get("GEMINI_API_KEY")`로만 취득<br />• 프론트엔드 및 Git 커밋 노출 0건 완벽 은닉 | **PASS** |
| **반응형 검증** | • 모바일/태블릿/데스크톱 대응<br />• 최소 2가지 크기 확인 | • 모바일 전용 하단 탭바(Bottom Nav) 및 1열 카드<br />• 태블릿 2열, 데스크톱 와이드 4열 반응형 지원 | **PASS** |
| **독창성** | • 템플릿 그대로 복제 금지<br />• 독창적 아이디어 및 구성 | • 33인 E1·E2·E3 스쿼시 리그 규정 및 AI 코칭 고유 개발 | **PASS** |

---

## 3. 종합 평가 결과
- **과제 필수 요구사항 충족률**: **100% (All Clear)**
- **특기 사항**: 실 서비스 배포([enthes-private.vercel.app](https://enthes-private.vercel.app))와 완벽히 동기화되었으며, 10종의 실제 모바일 구동 스크린샷과 부원 이용 안내서가 함께 증빙 패키지에 포함되었습니다.
