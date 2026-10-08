# 🔐 Vercel 환경 변수 (GEMINI_API_KEY) 설정 및 보안 가이드

본 문서는 **ENTHES ESL 웹 애플리케이션의 Vercel 배포 시 Google Gemini API 키를 안전하게 등록하고 운영하는 방법**을 안내합니다.

---

## 1. 환경 변수 등록 개요

본 프로젝트의 백엔드(`api/coach.py`)는 Google Gemini API를 호출하여 AI 코칭 리포트를 생성합니다.  
보안 원칙에 따라 API 키는 절대 프론트엔드 코드나 Git 커밋에 포함되지 않으며, **Vercel의 암호화된 환경 변수(Environment Variables) 시스템**을 통해 주입됩니다.

---

## 2. 3분 만에 끝내는 환경 변수 등록 절차

### 1단계: Google AI Studio에서 API 키 발급
1. [Google AI Studio (aistudio.google.com)](https://aistudio.google.com/app/apikey) 접속 후 Google 계정으로 로그인합니다.
2. **`Create API Key`** 버튼을 클릭하여 새 API 키를 생성합니다.
3. 생성된 키(예: `AIzaSy...`)를 복사합니다.

### 2단계: Vercel 프로젝트 설정에 키 등록
1. [Vercel Dashboard](https://vercel.com/dashboard)에 로그인하고 본인의 `Manus` 프로젝트를 선택합니다.
2. 상단 메뉴에서 **`Settings`** ➔ 좌측 사이드바에서 **`Environment Variables`** 탭을 클릭합니다.
3. 아래의 키와 값을 입력합니다:
   - **Key**: `GEMINI_API_KEY`
   - **Value**: `AIzaSy...` (1단계에서 복사한 본인의 키)
   - **Environments**: `Production`, `Preview`, `Development` (전체 체크)
4. **`Save`** 버튼을 클릭합니다.

### 3단계 (선택): 사용할 Gemini 모델 지정
- **Key**: `GEMINI_MODEL`
- **Value**: `gemini-2.5-flash` (기본 추천 모델)
- **`Save`** 버튼을 클릭합니다.

### 4단계: 변경 사항 적용을 위한 재배포 (Redeploy)
환경 변수를 추가하거나 수정한 후에는 반드시 새 배포가 이루어져야 서버리스 함수에 환경 변수가 주입됩니다:
1. Vercel 상단 **`Deployments`** 탭으로 이동합니다.
2. 가장 최신 배포 항목 우측의 점 세 개(`...`) 메뉴를 누르고 **`Redeploy`**를 클릭합니다.

---

## 3. 보안 점검 수칙 (Security Checklist)

- [x] `.gitignore` 파일에 `.env` 및 `.env.local`이 등록되어 있는가?
- [x] 프론트엔드 JavaScript(`app.js`)에 하드코딩된 API 키가 없는가?
- [x] 서버리스 백엔드(`api/coach.py`)에서 `os.environ.get("GEMINI_API_KEY")`로 안전하게 읽고 있는가?
- [x] 백엔드 로그(`log_message`)에 API 키나 요청 본문이 남지 않도록 비활성화되어 있는가?
