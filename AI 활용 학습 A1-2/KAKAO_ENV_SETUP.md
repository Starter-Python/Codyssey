# Kakao REST API 키를 `.env`로 안전하게 설정하기

이 문서는 `travel_planner.py`에서 Kakao Local API를 실행하기 위해 필요한 **Kakao REST API 키를 소스 코드와 GitHub에 노출하지 않고 설정하는 방법**을 설명합니다. 실제 키는 이 문서, `README.md`, `travel_planner.py`, 결과 JSON·Markdown에 작성하지 않습니다.

> **왜 이렇게 하나요?** API 키는 은행 카드 비밀번호처럼 "이 프로그램이 카카오에 접속할 수 있게 해주는 비밀번호"입니다. 코드에 직접 쓰면 GitHub에 올릴 때 전 세계에 공개될 수 있습니다. 그래서 **`.env`라는 별도 파일에만 저장**하고, GitHub에는 그 파일이 올라가지 않도록 막아 두었습니다.

> **핵심 원칙:** 키는 로컬의 `.env` 파일에만 넣고, `.env`는 Git이 추적하지 않도록 유지합니다. 이 프로젝트는 이미 `.gitignore`에 `.env`를 등록해 두었습니다.

## 1. 사전 준비

Kakao Developers에서 애플리케이션을 만들고 **REST API 키**를 확인합니다. 이 프로젝트는 Kakao Local API의 키워드 장소 검색 엔드포인트를 사용하며, 요청 헤더에는 `Authorization: KakaoAK {REST_API_KEY}` 형식이 사용됩니다.[1]

### 이 프로젝트에 필요한 Kakao 키는 REST API 키입니다

| 키 종류 | 주된 용도 | 이 Python 프로그램에서의 사용 여부 |
|---|---|---|
| **REST API 키** | 서버·CLI 프로그램에서 Kakao의 REST 엔드포인트 호출 | **사용함**. `KAKAO_REST_API_KEY`에 설정 |
| JavaScript 키 | 웹페이지에서 Kakao Map JavaScript SDK를 로드 | 사용하지 않음. 이 과제는 웹 지도 화면이 아니라 Python CLI 프로그램 |
| Admin 키 | 앱 관리·사용자 관리 등 민감한 관리자용 API | 사용하지 않음. 일반 장소 검색에 사용하면 안 됨 |

Kakao 공식 문서도 장소 검색 REST API에는 REST API 키와 `Authorization: KakaoAK {REST_API_KEY}` 헤더를 사용하도록 명시합니다.[1] JavaScript 키는 웹 Map SDK의 도메인 등록 환경에서 쓰는 별도 키입니다.[2]

| 필요한 항목 | 설명 | 프로젝트에서의 변수명 |
|---|---|---|
| Kakao REST API 키 | Kakao Developers 애플리케이션의 REST API 키 | `KAKAO_REST_API_KEY` |
| Gemini API 키 | 여행 추천 JSON·최종 리포트 생성용 키 | `GEMINI_API_KEY` |
| Python 3.10 이상 | 프로그램 실행 환경 | 해당 없음 |

## 2. `.env.example`을 복사해 개인 `.env` 만들기

프로젝트 폴더에서 아래 명령을 실행합니다. `.env.example`은 키 이름과 설명만 포함하는 안전한 예시 파일이며, 실제 키는 없습니다.

### macOS / Linux

```bash
cd "AI 활용 학습 A1-2"
cp .env.example .env
chmod 600 .env
```

### Windows PowerShell

```powershell
Set-Location "AI 활용 학습 A1-2"
Copy-Item .env.example .env
```

`chmod 600 .env`는 macOS/Linux에서 현재 사용자만 `.env` 파일을 읽고 쓸 수 있게 제한합니다. 공유 컴퓨터에서 작업한다면 특히 권장합니다.

## 3. 실제 키를 `.env`에만 입력하기

텍스트 편집기로 `.env`를 열고 본인의 실제 키를 입력합니다. 아래의 `YOUR_...` 부분만 바꾸며, 따옴표는 꼭 필요하지 않습니다.

```dotenv
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
KAKAO_REST_API_KEY=YOUR_KAKAO_REST_API_KEY
GEMINI_MODEL=gemini-3.5-flash
```

`travel_planner.py`는 시작할 때 `load_dotenv(BASE_DIR / ".env")`를 실행하고, `os.getenv("GEMINI_API_KEY")`와 `os.getenv("KAKAO_REST_API_KEY")`로 키를 읽습니다. 따라서 키가 프로그램 코드에 하드코딩되지 않습니다.

## 4. GitHub에 키가 올라가지 않는지 확인하기

이 프로젝트의 `.gitignore`에는 다음 규칙이 포함되어 있습니다.

```gitignore
.env
.env.*
!.env.example
```

따라서 `.env`와 `.env.local` 같은 실제 비밀 설정 파일은 Git이 무시하고, 키 값이 없는 `.env.example`만 저장소에 남습니다. 커밋하기 전에는 반드시 아래 명령으로 확인합니다.

```bash
# 출력이 없으면 .env는 Git 변경 목록에 포함되지 않습니다.
git status --short

# .env가 어느 무시 규칙에 의해 제외되는지 확인합니다.
git check-ignore -v .env
```

`git status --short`에 `.env`가 보이면 커밋을 중단하고 `.gitignore` 설정을 먼저 확인합니다. `git add -f .env`처럼 무시 규칙을 강제로 우회하는 명령은 사용하지 마세요.

## 5. 실행과 정상 동작 확인

키를 설정한 뒤 다음과 같이 실행합니다.

```bash
python travel_planner.py --date "2026-10-03"
```

Kakao Local API가 정상 작동하면 콘솔에 다음과 비슷한 결과가 보입니다.

```text
[2/3] 맛집 검색 중(Kakao Local API)...
  - 맛집 5곳 검색 완료
```

검색된 장소는 `results/YYYY-MM-DD_travel_data.json`의 `restaurants` 배열에 저장되고, 최종 리포트의 **맛집 추천** 섹션에도 사용됩니다. 실제 결과를 GitHub에 올리기 전에는 개인 위치나 기타 민감한 정보가 없는지 먼저 검토하세요.

## 6. 오류별 점검 방법

| 콘솔 메시지 또는 오류 유형 | 가능 원인 | 조치 |
|---|---|---|
| `KAKAO_REST_API_KEY 미설정` | `.env`가 없거나 변수명이 다름 | 프로젝트 폴더의 `.env`에 정확히 `KAKAO_REST_API_KEY`를 입력 |
| HTTP 401 | 키 형식·값이 잘못되었거나 키가 폐기됨 | Kakao Developers의 REST API 키를 다시 확인하고 필요 시 재발급 |
| HTTP 403 | REST API 키 자체는 맞더라도 Kakao Map·Local 서비스가 비활성화되었을 수 있음 | Kakao Developers 콘솔에서 해당 앱을 열고 **제품 설정 > 카카오맵 > 이용 설정**을 `ON`으로 변경한 뒤 재시도. 콘솔이 서비스 비활성화를 알리면 이 설정이 우선 점검 대상 |
| HTTP 429 | 호출량 또는 쿼터 제한 | 잠시 뒤 재시도하고 호출 빈도를 줄임 |
| 검색 결과 0건 | 검색어에 맞는 장소가 없음 | 프로그램은 중단하지 않고 맛집을 `데이터 없음`으로 표기 |

프로그램은 장소 검색 오류가 발생해도 여행 추천과 최종 리포트 생성을 계속 수행합니다. 오류의 단계와 유형은 원본 JSON의 `errors` 배열에 저장되므로, 어떤 부분을 점검해야 하는지 추적할 수 있습니다.

## 7. Gemini API 키 설정

과제 요구사항은 LLM 제공자로 **OpenAI 계열 또는 Google Gemini 계열 중 하나를 선택**하도록 되어 있습니다. 현재 `travel_planner.py`는 Google Gemini API의 `generateContent` REST 엔드포인트를 사용하도록 구현되어 있으므로 `GEMINI_API_KEY`가 필요합니다. Gemini API 키는 Google AI Studio에서 발급하며, 무료 등급은 일부 모델과 제한된 요청량을 제공합니다.[3]

| 상황 | 필요한 LLM 키 |
|---|---|
| 현재 제출된 코드 그대로 실행 | `GEMINI_API_KEY` |
| 모델명을 변경해야 할 때 | 선택적으로 `GEMINI_MODEL` |
| Kakao 맛집 검색 실행 | 별도로 `KAKAO_REST_API_KEY` |

현재 기본 모델은 `gemini-3.5-flash`입니다. 계정의 무료 등급에서 이 모델을 사용할 수 없거나 요청 제한에 도달하면, Google AI Studio에서 사용 가능한 모델로 `GEMINI_MODEL`을 바꾸거나 제한이 해제될 때까지 기다립니다.

## 8. 키가 노출되었을 때의 조치

키를 GitHub 커밋, 공개 문서, 화면 공유, 대화 기록 등 예상하지 못한 위치에 입력했다면 해당 키를 더 이상 안전한 것으로 보지 않는 것이 좋습니다. Kakao Developers에서 기존 키를 관리·교체할 수 있는지 확인하고, 새 키를 발급한 후 로컬 `.env`만 갱신하세요. 이후 Git 저장소의 모든 커밋 기록도 점검해야 합니다.

자동 배포나 GitHub Actions를 도입한다면 `.env` 파일을 저장소에 복사하지 않고 GitHub Actions Secrets에 키를 등록해 실행 시 환경변수로만 주입합니다.[2]

## 참고 자료

[1] [Kakao Developers, 로컬 API: 키워드로 장소 검색](https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-keyword)

[2] [GitHub Docs, Using secrets in GitHub Actions](https://docs.github.com/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions)

[3] [Google AI, Gemini Developer API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
