# 📸 [증빙 자료] 서비스 동작 및 실제 모바일 스크린샷 증빙 가이드

본 문서는 **ENTHES ESL 정규 리그 & AI 코칭 웹 서비스**의 데스크톱/모바일 반응형 지원 및 실제 구동 화면, AI 코칭 파이프라인 동작을 검증하는 공식 증빙 문서입니다.

---

## 1. 실제 모바일 UI 스크린샷 10종 증빙

본 프로젝트의 실제 모바일 웹앱 구동 화면을 캡처한 고해상도 스크린샷 10종이 [`evidence/screenshots/`](./screenshots/)에 보관되어 있습니다:

### 1) 경기 결과 입력 & AI 분석 흐름 (1~3단계)
| **Step 1: [대진] 탭 확인** | **Step 2: [결과 입력 & AI 분석] 터치** | **Step 3: 세트 스코어 & 메모 입력** |
| :---: | :---: | :---: |
| ![대진 탭](./screenshots/match_step1_tab.jpg) | ![카드 터치](./screenshots/match_step2_card.jpg) | ![점수 입력](./screenshots/match_step3_input.jpg) |
| `match_step1_tab.jpg` | `match_step2_card.jpg` | `match_step3_input.jpg` |

### 2) AI 코칭 분석 & 실시간 스탯 반영 흐름 (4~6단계)
| **Step 4: 실시간 순위 변동** | **Step 5: AI 승자/패자 피드백** | **Step 6: 6대 스탯 & 성장 궤적** |
| :---: | :---: | :---: |
| ![순위 반영](./screenshots/match_step5_rank.jpg) | ![AI 피드백](./screenshots/match_step6_feedback.jpg) | ![성장 궤적](./screenshots/match_step7_growth.png) |
| `match_step5_rank.jpg` | `match_step6_feedback.jpg` | `match_step7_growth.png` |

### 3) Safari PWA 홈 화면 앱 추가 지원
| **PWA Step 1: 공유 터치** | **PWA Step 2: 옵션 스크롤** | **PWA Step 3: 홈 화면 추가** |
| :---: | :---: | :---: |
| ![공유](./screenshots/step1_share.jpg) | ![옵션](./screenshots/step2_sheet.jpg) | ![홈화면 추가](./screenshots/step3_add_home.jpg) |
| `step1_share.jpg` | `step2_sheet.jpg` | `step3_add_home.jpg` |

---

## 2. AI 기능 3단계 동작 흐름 검증

```
[ 1단계: 사용자 입력 ]
- 경기: 임영현 (E1 T1) vs 조기호 (E1 T1)
- 스코어: 15 : 13
- 현장 메모: "조기호의 날카로운 백핸드 드롭을 임영현이 T존을 잡고 깊은 포핸드 드라이브 랭스로 역전함"
                  │
                  ▼ [ 비동기 POST /api/coach 호출 ]
[ 2단계: Gemini AI 코칭 리포트 생성 ]
- 총평: 임영현 선수가 2점 차 접전 끝에 전술적 우위를 점하며 승리했습니다.
- 승자 분석: 임영현 선수의 깊숙한 드라이브 랭스가 코트 모서리에 정확히 꽂혔습니다.
- 패자 분석: 조기호 선수는 수비 시 드라이브 길이가 짧아져 상대에게 공격 찬스를 허용했습니다.
- 추천 드릴: 솔로 레일 드릴: 벽과 1미터 거리를 유지하며 드라이브를 연속 15회 벽에 붙이는 훈련을 권장합니다.
- 스탯 변동:
  • 임영현: 포핸드 +1, 스피드 +2, 체력 +2, 침착성 +1
  • 조기호: 포핸드 -1, 스피드 -2, 체력 -2
                  │
                  ▼ [ 결과 확정 및 스탯 반영 ]
[ 3단계: 순위표 & 프로필 실시간 갱신 ]
- 순위표 OVR 실시간 변동
- 6축 SVG 레이더 차트 다각형 자동 재계산 및 시계열 성장 곡선 기록
```

---

## 3. 3대 실패 처리 시나리오 검증

1. **빈 입력 (필수값 누락)**:
   - 선수 미선택 또는 스코어 미입력 시 `alert-danger` 경고 배너가 출력되고 네트워크 호출이 안전하게 차단됩니다. (단, 메모는 선택 사항으로 점수만으로도 분석 가능)
2. **API 장애 / 키 미설정**:
   - `GEMINI_API_KEY`가 없거나 Google API 일시 장애(429/500) 시, 내장 휴리스틱 룰 엔진이 즉시 가동되어 중단 없이 분석 리포트를 반환합니다.
3. **10초 타임아웃 가드레일**:
   - `AbortController` 10초 타임아웃이 적용되어 네트워크 지연 시 사용자 인터페이스가 멈추지 않고 로컬 결과로 전환됩니다.
