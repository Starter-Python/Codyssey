# 🎬 무신사 스탠다드 AI 광고 영상 스토리보드 기획서

**프로젝트명:** 무신사 스탠다드 AI 광고 영상
**제작일:** 2025년
**총 영상 길이:** 12초 (씬 1: 6초 + 씬 2: 6초)

---

## 📌 브랜드 아이덴티티

| 항목 | 내용 |
|------|------|
| **브랜드** | 무신사 스탠다드 (MUSINSA STANDARD) |
| **타겟** | 20대 한국 남성, 꾸미지 않은 듯 세련된 데일리룩을 원하는 소비자 |
| **톤앤매너** | 미니멀, 시네마틱, 자연스러움 (화이트·베이지·그레이 톤) |
| **USP** | 합리적 가격의 고품질 베이직 — "누구나 입을 수 있는 기본템" |
| **핵심 메시지** | **"매일, 나답게 — 입는 순간 일상이 달라진다"** |
| **키워드** | #베이직 #데일리룩 #심플 #모던 |

---

## 🎞️ 씬 구성 (총 2컷)

### 🎬 씬 1 — 도심 속 자연스러운 등장 (0~6초)

| 필수 필드 | 내용 |
|------|------|
| **목표** | 타겟(20대 한국 남성)이 공감할 일상 착용 장면 제시, 브랜드 무드 전달 |
| **화면** | 안개 낀 도심 거리, 자연광 아래 한국인 남성 모델의 정면 슬로우 워킹샷 (흰 오버핏 티 + 베이지 와이드팬츠 + 흰 스니커즈) |
| **내레이션** | "매일 입는 옷이, 나를 말해준다" — TTS Maker (507 준혁 보이스) |
| **도구** | 이미지: Leonardo.ai GPT Image 2 → 영상: Hailuo 2.3 |
| **이미지 프롬프트** | `Korean young male model, white oversized t-shirt, beige wide pants, white sneakers, walking on urban street, cinematic, natural lighting, full body shot, minimal style, foggy city background` |
| **영상 프롬프트** | `person walking slowly forward, cinematic camera movement, smooth natural motion, minimal style, soft lighting` |
| **씬 길이** | 6초 |
| **출력 요약** | 1376×768(768p) mp4, 자연광 도심 워킹 컷, 씬 2로 컷 전환 |

---

### 🎬 씬 2 — 제품 클로즈업 & 브랜드 강조 (6~12초)

| 필수 필드 | 내용 |
|------|------|
| **목표** | 제품 디테일 집중 + 브랜드명 각인으로 광고 마무리 |
| **화면** | 순백색 배경, 흰 오버핏 티셔츠 플랫레이 슬로우 줌인 → 하단 `MUSINSA STANDARD` 텍스트 노출 |
| **내레이션** | "무신사 스탠다드" — TTS Maker (507 준혁 보이스) |
| **도구** | 이미지: Leonardo.ai GPT Image 2 → 영상: Hailuo 2.3 |
| **이미지 프롬프트** | `white oversized t-shirt flat lay, pure white background, minimal, brand name "MUSINSA STANDARD" text below, clean product shot, studio lighting, soft shadow` |
| **영상 프롬프트** | `slow zoom in on white clothing, soft light, clean white background, cinematic product shot, minimal` |
| **씬 길이** | 6초 |
| **출력 요약** | 1376×768(768p) mp4, 제품 줌인 컷 + 브랜드명 텍스트 포함 엔딩 |

---

## 🔊 오디오 설계 (AI 청각 요소)

| 요소 | 도구 | 내용 |
|------|------|------|
| **내레이션** | TTS Maker (507 - 준혁 보이스) | 씬별 한 줄 카피, 차분한 남성 톤 |
| **BGM** | Suno | 미니멀 로파이/앰비언트, 12초, 잔잔한 무드 |

---

## ✏️ 프롬프트 수정 전/후 기록 (씬 1)

| 구분 | 내용 |
|------|------|
| **수정 전** | `흰티셔츠 입은 남자가 거리에 걷는 영상 만들어줘.` (한국어 단순 입력, Text-to-Video 직접 생성) |
| **문제점** | ① 외국인 모델 생성 → 브랜드 타겟(20대 한국 남성)과 불일치 ② 배경·조명·스타일 정보 부재 ③ 영상 직접 생성 시 인물·구도 제어 불가 |
| **수정 후** | `Korean young male model, white oversized t-shirt, beige wide pants...` + **Text-to-Image → Image-to-Video 2단계 방식으로 전환** |
| **수정 이유** | `Korean` 명시로 타겟 일치 / 의상·배경·조명 구체화로 브랜드 무드 구현 / 이미지 단계에서 결과물을 먼저 검수한 뒤 영상화하여 **품질 제어력 확보** |
| **결과 변화** | 한국인 모델 + 의도한 코디·무드가 정확히 반영된 이미지 확보 → 영상 변환 성공률 상승, 크레딧 낭비 감소 |

---

## 🛠️ 제작 파이프라인

```
[기획] 스토리보드·핵심 메시지 확정
   ↓
[생성] 이미지 생성(Leonardo) → 검수 통과분만 영상 변환(Hailuo) / 오디오 병렬 생성(TTS Maker·Suno)
   ↓
[검수] 톤앤매너·인물 일관성·브랜드 무드 확인 → 미달 시 프롬프트 수정 후 재생성
   ↓
[편집/통합] CapCut — 씬 연결(총 12초), 자막·내레이션·BGM 믹싱
```

| 단계 | 도구 | 역할 |
|------|------|------|
| 이미지 생성 | Leonardo.ai GPT Image 2 (Dynamic / Low) | 씬별 키프레임 이미지 (1024×1024) |
| 영상 변환 | Hailuo 2.3 | Image-to-Video 6초 클립 (1376×768) |
| 내레이션 | TTS Maker (507 준혁) | AI 음성 카피 |
| 편집/통합 | QuickTime Player | 씬 연결, 자막, 오디오 믹싱 |

---

## 📐 에셋 규격 표준화 (톤앤매너 일관성)

| 항목 | 기준 |
|------|------|
| 이미지 | 1024×1024 / Dynamic / Low 설정 고정 |
| 영상 | 1376×768(768p), 최종 16:9, 씬당 6초 |
| 색감 | 화이트·베이지·그레이 톤 통일 |
| 공통 프롬프트 키워드 | `minimal`, `cinematic`, `soft lighting` — 전 씬 공통 삽입으로 무드 일관성 유지 |

---

## 📁 파일 네이밍 규칙

```
📂 AI 도구 학습 B1-2/
├── main.md
├── scene0.mp4     ← 씬 0 영상
├── scene1.mp4     ← 씬 1 영상 (0~6초)
├── scene1.png     ← 씬 1 이미지
├── scene2.mp4     ← 씬 2 영상 (6~12초)
├── scene2.pnh     ← 씬 2 이미지
├── storyboard.md       ← 스토리보드
└── storyboard.pdf      
```

---

## ⚖️ 저작권 확인 (직접 촬영/유료 스톡 미사용)

- **직접 촬영 소스:** 사용 안 함 — 전 장면 AI 생성
- **유료 스톡 소스:** 사용 안 함
- 이미지(Leonardo.ai) / 영상(Hailuo 2.3) / 음성(TTS Maker) **전부 AI 생성물**로만 구성

---

## ✅ 최종 산출물 체크리스트

- [x] 이미지 2장 생성 (Leonardo.ai GPT Image 2)
- [x] 영상 2개 변환 (Hailuo 2.3, 각 6초)
- [x] 내레이션 (TTS Maker) + BGM (Suno) — AI 청각 요소
- [x] 최종 영상 12초 완성
- [x] AI 시각 + 청각 요소 모두 포함
- [x] 프롬프트 수정 전/후 및 이유 기록
- [x] 씬별 필수 필드(목표/화면/내레이션/도구/프롬프트/길이/출력) 완비

---

*© 2025 무신사 스탠다드 AI 광고 프로젝트*
