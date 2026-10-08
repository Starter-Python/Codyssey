#!/usr/bin/env python3
"""Gemini API와 Kakao Local API로 국내 여행 추천 리포트를 생성하는 CLI 프로그램."""
from __future__ import annotations  # 미래 파이썬 문법을 미리 허용합니다. 타입 힌트 문법을 안전하게 쓰기 위한 것입니다.

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
    import requests
except ImportError:  # 패키지가 설치되어 있지 않으면 아래처럼 처리합니다.
    requests = None  # type: ignore[assignment]

try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
    from dotenv import load_dotenv
except ImportError:  # 패키지가 설치되어 있지 않으면 아래처럼 처리합니다.
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:  # type: ignore[misc]
        return False  # .env 로딩 실패를 알리는 값(타입 힌트용).

BASE_DIR = Path(__file__).resolve().parent  # 이 파일이 있는 폴더의 전체 경로입니다.
RESULTS_DIR = BASE_DIR / "results"  # 결과 파일을 저장할 results 폴더 경로입니다.
KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
COPA_URL = "https://copa.codyssey.kr/v1/chat/completions"  # Copa(OpenAI 호환) API 주소입니다.
TIMEOUT_SECONDS = 20  # 외부 API 응답 대기 시간 상한(초).
RECOMMENDATION_SCHEMA: dict[str, Any] = {
    "type": "object",  # 전체 답변이 '객체(키-값 묶음)' 형태여야 함을 명시합니다.
    "properties": {  # 객체 안에 들어갈 키들과 각각의 타입을 정의합니다.
        "recommended_city": {"type": "string"},  # 추천 도시 이름은 문자열이어야 합니다.
        "weather": {"type": "string"},  # 날씨 요약은 문자열이어야 합니다.
        "events": {"type": "array", "items": {"type": "string"}},  # 행사 목록은 문자열들의 배열이어야 합니다.
        "reason": {"type": "string"},  # 추천 이유는 문자열이어야 합니다.
    },  # 데이터 구조의 일부입니다.
    "required": ["recommended_city", "weather", "events", "reason"],  # 이 4개 키가 반드시 다 있어야 합니다.
}  # 블록 끝.


class PlannerError(RuntimeError):
    """사용자에게 안내할 수 있는 오류."""


class GeminiRequestError(RuntimeError):
    """HTTP 상태를 포함하는 Gemini API 요청 오류."""

    def __init__(self, message: str, status_code: int | None = None) -> None:  # 오류가 만들어질 때 실행되는 초기화 함수입니다.
        super().__init__(message)  # 부모 클래스(RuntimeError)의 초기화를 그대로 실행합니다.
        self.status_code = status_code  # HTTP 코드(예: 429)를 오류 객체 안에 저장해 둡니다.


def parse_args() -> argparse.Namespace:  # 1단계 준비: 명령어 옵션을 읽고 날짜를 검증합니다.
    parser = argparse.ArgumentParser(  # 옵션 파서를 만들고 설명과 도움말 형식을 지정합니다.
        description="Gemini API와 Kakao Local API로 국내 여행 추천 리포트를 생성합니다.",  # --help 실행 시 보여 줄 프로그램 설명입니다.
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,  # 옵션 기본값을 도움말에 자동으로 표시하는 형식입니다.
    )  # 안내 메시지 끝.
    parser.add_argument("-date", "--date", dest="travel_date", required=False, default=None, metavar="YYYY-MM-DD", help="여행 날짜 (생략하면 실행 중에 입력받습니다)")  # 여행 날짜 옵션. 생략하면 나중에 직접 물어봅니다.
    parser.add_argument("--cached", action="store_true", help="저장된 원본 데이터(JSON)가 있으면 API 재호출 없이 캐시를 재사용합니다.")  # --cached: 저장된 결과를 그대로 재사용합니다.
    parser.add_argument("--refresh", action="store_true", help="기존 캐시를 무시하고 API를 새로 호출합니다.")  # --refresh: 캐시를 무시하고 새로 API를 부릅니다.
    args = parser.parse_args()  # 실제 입력된 옵션 값들을 args에 담습니다.
    if args.travel_date is None:  # 날짜를 안 주고 실행했으면 직접 입력받습니다.
        while True:  # 올바른 날짜가 입력될 때까지 반복합니다.
            try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
                args.travel_date = input("여행 날짜를 입력하세요 (YYYY-MM-DD): ").strip()  # 사용자에게 날짜를 물어보고 앞뒤 공백을 제거합니다.
            except (EOFError, KeyboardInterrupt):  # 입력이 끊기거나 Ctrl+C로 취소하면 처리합니다.
                print()  # 줄바꿈을 출력합니다.
                parser.error("날짜가 입력되지 않았습니다.")  # 안내 메시지와 함께 프로그램을 종료합니다.
            try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
                datetime.strptime(args.travel_date, "%Y-%m-%d")  # 날짜 형식이 맞는지 검사합니다. 형식이 틀리면 ValueError가 납니다.
                break  # 올바른 날짜가 확인됐으므로 반복을 끝냅니다.
            except ValueError:  # 날짜 형식이 틀렸을 때 처리합니다.
                print("  - YYYY-MM-DD 형식의 실제 날짜로 다시 입력하세요.")  # 어떤 형식으로 다시 입력해야 하는지 알려 줍니다.
    else:  # -date 옵션으로 직접 준 경우입니다.
        try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
            datetime.strptime(args.travel_date, "%Y-%m-%d")  # 날짜 형식이 맞는지 검사합니다. 형식이 틀리면 ValueError가 납니다.
        except ValueError:  # 날짜 형식이 틀렸을 때 처리합니다.
            parser.error("-date/--date는 YYYY-MM-DD 형식의 실제 날짜여야 합니다.")  # 잘못된 날짜 형식이면 사용법 안내 후 종료합니다.
    return args  # 검증된 옵션 값들을 돌려줍니다.


def normalize_city_name(city: str) -> str:  # 넓은 지역명을 검색에 적합한 도시명으로 바꿉니다.
    """광역시/도 등 광역 지자체 명칭이나 수식어를 지도 검색에 적합한 대표 도시/지역명으로 정규화."""
    cleaned = city.strip()  # 앞뒤 공백을 제거합니다.
    replacements = {  # 바꿀 이름과 바뀔 결과를 짝지은 사전입니다.
        "제주특별자치도": "제주",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "강원특별자치도": "강원",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "전북특별자치도": "전북",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "강원도": "강릉",  # 광역 도 단위일 경우 관광 중심 도시로 보정  # 강원도는 관광 중심 도시인 강릉으로 보정합니다.
        "경기도": "가평",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "충청북도": "단양",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "충청남도": "태안",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "전라북도": "전주",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "전라남도": "여수",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "경상북도": "경주",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "경상남도": "통영",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "서울특별시": "서울",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "부산광역시": "부산",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "대구광역시": "대구",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "인천광역시": "인천",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "광주광역시": "광주",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "대전광역시": "대전",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "울산광역시": "울산",  # 넓은 이름을 대표 도시명으로 바꿉니다.
        "세종특별자치시": "세종",  # 넓은 이름을 대표 도시명으로 바꿉니다.
    }  # 블록 끝.
    return replacements.get(cleaned, cleaned)  # 사전에 있으면 바뀐 이름을, 없으면 원래 이름을 돌려줍니다.


def extract_json_object(raw_text: str) -> str:  # AI 답변 텍스트에서 JSON 부분만 골라냅니다.
    """마크다운 코드블록이나 불필요한 앞뒤 텍스트가 섞여 있어도 유효한 JSON 객체 블록만 추출."""
    text = raw_text.strip()  # 앞뒤 공백을 제거합니다.
    if text.startswith("```"):  # 답변이 ```로 시작하면 코드블록이라는 뜻입니다.
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)  # 코드블록 시작 표시를 지웁니다.
        text = re.sub(r"\s*```$", "", text)  # 코드블록 끝 표시를 지웁니다.
    match = re.search(r"(\{.*\})", text, re.DOTALL)  # 텍스트 안에서 { ... } 부분을 찾습니다.
    if match:  # 찾았다면 아래를 실행합니다.
        return match.group(1).strip()  # 찾은 JSON 부분만 돌려줍니다.
    return text  # 못 찾았으면 원래 텍스트를 그대로 돌려줍니다.


def redact_secrets(message: str) -> str:  # 비밀(API 키)이 노출되지 않게 가리는 함수입니다.
    safe = str(message)  # 원본 메시지를 문자열로 준비합니다.
    for name in ("GEMINI_API_KEY", "KAKAO_REST_API_KEY", "OPENROUTER_API_KEY"):  # 세 가지 키 이름을 하나씩 확인합니다.
        if key := os.getenv(name):  # 해당 이름의 키가 설정되어 있으면 가져옵니다.
            safe = safe.replace(key, "[REDACTED]")  # 메시지 속 실제 키 값을 [REDACTED]로 바꿉니다.
    return re.sub(r"(?:AIza|sk-)[A-Za-z0-9_-]+", "[REDACTED]", safe)  # 키처럼 생긴 문자열 패턴도 한 번 더 가립니다.


def add_error(errors: list[dict[str, str]], step: str, kind: str, message: str) -> None:  # 오류 기록을 목록에 추가하는 작은 도우미입니다.
    errors.append({"step": step, "type": kind, "message": redact_secrets(message)[:300]})  # {단계, 종류, 내용} 형태로 추가하되, 비밀을 가리고 300자로 자릅니다.


def validate_recommendation(data: Any) -> dict[str, Any]:  # AI 답변 JSON이 우리 형식과 맞는지 검사합니다.
    if not isinstance(data, dict):  # 답변이 객체(사전) 형태가 아니면 거부합니다.
        raise ValueError("추천 결과의 최상위 형식이 객체가 아닙니다.")  # 형식이 틀렸다는 오류를 냅니다.
    if "recommended_city" not in data and len(data) == 1:  # 키가 recommended_city 하나가 아니고 내용이 1개뿐이면,
        only = next(iter(data.values()))  # 그 하나의 값을 꺼냅니다.
        if isinstance(only, dict):  # 그 값이 객체면 한 번 더 펼쳐서 검사합니다.
            data = only  # 펼친 값을 검사 대상으로 삼습니다.
    if isinstance(data.get("events"), str):  # events가 문자열이면(배열이 아니라면) 보정합니다.
        data["events"] = [s.strip() for s in data["events"].split(",") if s.strip()]  # 쉼표로 나뉜 문자열을 배열로 바꿉니다.
    required = {"recommended_city": str, "weather": str, "events": list, "reason": str}  # 必 키와 기대 타입을 정해 둡니다.
    for name, value_type in required.items():  # 각 키를 하나씩 확인합니다.
        if not isinstance(data.get(name), value_type):  # 타입이 맞지 않으면 거부합니다.
            raise ValueError(f"필수 키 또는 타입이 올바르지 않습니다: {name}")  # 어떤 키가 틀렸는지 알려 줍니다.
    if not all(data[name].strip() for name in ("recommended_city", "weather", "reason")):  # 문자열 필드가 모두 비어 있지 않은지 확인합니다.
        raise ValueError("문자열 필수 값이 비어 있습니다.")  # 빈 값이면 거부합니다.
    if not all(isinstance(item, str) for item in data["events"]):  # events의 각 항목이 문자열인지 확인합니다.
        raise ValueError("events의 모든 항목은 문자열이어야 합니다.")  # 문자열이 아닌 항목이 있으면 거부합니다.
    return data  # 검증을 통과한 추천 데이터를 돌려줍니다.


def build_gemini_settings() -> tuple[str, str]:  # Gemini 키와 모델명을 읽어 옵니다.
    api_key = os.getenv("GEMINI_API_KEY")  # 환경변수(.env)에서 키를 가져옵니다. 코드에 키를 직접 쓰지 않습니다.
    if not api_key:  # 키가 없으면,
        raise PlannerError(  # 친절한 안내 메시지와 함께 중단합니다.
            "GEMINI_API_KEY가 설정되지 않았습니다. .env에 GEMINI_API_KEY를 설정하거나 "  # 키 설정 방법 안내 1.
            "export GEMINI_API_KEY='YOUR_KEY'를 실행한 뒤 다시 시도하세요."  # 키 설정 방법 안내 2.
        )  # 안내 메시지 끝.
    # 무료 등급 사용 가능 모델은 계정·시점별로 다를 수 있어 환경변수로 바꿀 수 있다.
    return api_key, os.getenv("GEMINI_MODEL", "gemini-3.8-flash")  # 키와 모델명(없으면 기본값)을 돌려줍니다.


def build_llm_settings() -> tuple[str, str, str]:  # 어떤 AI 제공자를 쓸지 결정합니다.
    """LLM 제공자를 결정한다."""
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()  # 사용자가 지정한 제공자 이름을 읽습니다.
    groq_key = os.getenv("GROQ_API_KEY")  # Groq 키가 있는지 확인합니다.
    if provider == "groq":  # Groq를 쓰기로 했다면,
        if not groq_key:  # 키가 없으면,
            raise PlannerError("GROQ_API_KEY가 설정되지 않았습니다. .env에 GROQ_API_KEY를 설정하세요.")  # 설정 방법을 안내하고 중단합니다.
        return "groq", groq_key, os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # Groq를 씁니다.
    if provider == "openrouter":  # OpenRouter를 쓰기로 했다면,
        openrouter_key = os.getenv("OPENROUTER_API_KEY")  # OpenRouter 키도 확인합니다.
        if not openrouter_key:  # 키가 없으면,
            raise PlannerError("OPENROUTER_API_KEY가 설정되지 않았습니다. .env에 OPENROUTER_API_KEY를 설정하세요.")  # 설정 방법을 안내하고 중단합니다.
        return "openrouter", openrouter_key, os.getenv("OPENROUTER_MODEL", "openrouter/free")  # OpenRouter를 씁니다.
    if provider == "copa":  # Copa를 쓰기로 했다면,
        copa_key = os.getenv("COPA_API_KEY")  # Copa 키를 읽습니다.
        if not copa_key:
            raise PlannerError("COPA_API_KEY가 설정되지 않았습니다. .env에 COPA_API_KEY를 설정하세요.")  # 키가 없으면 안내합니다.  # 친절한 오류 메시지로 중단합니다.
        return "copa", copa_key, os.getenv("COPA_MODEL", "gpt-5-mini")  # (제공자, 키, 모델)을 돌려줍니다.
    if provider == "gemini":  # Gemini를 쓰기로 했다면,
        api_key, model = build_gemini_settings()  # Gemini 설정을 읽어 옵니다.
        return "gemini", api_key, model  # 마지막으로 Gemini를 씁니다.

    # LLM_PROVIDER 미설정: Groq → OpenRouter → Copa → Gemini 순으로 키가 있으면 사용
    if groq_key:  # 제공자 지정이 없으면, Groq 키가 있으면 Groq를,
        return "groq", groq_key, os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")  # Groq를 씁니다.
    openrouter_key = os.getenv("OPENROUTER_API_KEY")  # OpenRouter 키도 확인합니다.
    if openrouter_key:  # OpenRouter 키가 있으면 OpenRouter를,
        return "openrouter", openrouter_key, os.getenv("OPENROUTER_MODEL", "openrouter/free")  # OpenRouter를 씁니다.
    copa_key = os.getenv("COPA_API_KEY")  # Copa 키도 확인합니다.
    if copa_key:
        return "copa", copa_key, os.getenv("COPA_MODEL", "gpt-5-mini")  # (제공자, 키, 모델)을 돌려줍니다.
    api_key, model = build_gemini_settings()  # Gemini 설정을 읽어 옵니다.
    return "gemini", api_key, model  # 마지막으로 Gemini를 씁니다.


def request_openrouter(  # OpenRouter에 요청을 보내는 함수입니다.
    api_key: str, model: str, prompt: str, *, max_output_tokens: int, response_schema: dict[str, Any] | None = None  # 이 함수들이 받는 재료들입니다.
) -> str:  # 호출 블록 끝.
    if requests is None:  # requests 패키지가 없으면,
        raise PlannerError("외부 API 호출을 위해 requests 패키지가 필요합니다. pip install -r requirements.txt를 실행하세요.")  # 설치 안내와 함께 중단합니다.
    payload: dict[str, Any] = {  # 보낼 데이터(질문 본문)를 만듭니다.
        "model": model,  # 사용할 AI 모델을 지정합니다.
        "messages": [  # 대화 형식의 질문 목록입니다.
            {"role": "system", "content": "당신은 한국 국내 여행 추천 전문가입니다. 사용자의 지시를 충실히 따르고, 요구된 형식(JSON 또는 Markdown)으로만 답변하세요."},  # 시스템 지시: AI의 역할과 답변 형식을 정합니다.
            {"role": "user", "content": prompt},  # 사용자 질문을 담습니다.
        ],  # 목록 끝.
        "temperature": 0.5,  # 답변의 무작위성 조절값(0.5는 적당히 다양하게).
        "max_tokens": max_output_tokens,  # 답변 길이 상한입니다.
    }  # 블록 끝.
    for attempt in range(3):  # 최대 3번 시도합니다.
        try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
            response = requests.post(  # POST 요청을 보냅니다.
                OPENROUTER_URL,  # 요청을 보낼 주소입니다.
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},  # 인증 헤더(열쇠)를 담습니다.
                json=payload,  # 보낼 데이터 본문을 넣습니다.
                timeout=TIMEOUT_SECONDS,  # 최대 대기 시간을 둡니다.
            )  # 안내 메시지 끝.
            if response.status_code in (429, 503) and attempt < 2:  # 서버 응답 코드를 확인합니다.
                print(f"  - OpenRouter 일시적 오류(HTTP {response.status_code}): 3초 후 재시도합니다.")  # 사용자에게 화면에 보여 줍니다.
                time.sleep(3)  # 3초 기다렸다가 다시 시도합니다.
                continue  # 다음 시도로 넘어갑니다.
            if response.status_code >= 400:  # 서버 응답 코드를 확인합니다.
                raise GeminiRequestError(f"HTTP {response.status_code}", response.status_code)  # API 오류를 위로 올려 보냅니다.
            data = response.json()  # 응답 본문을 JSON으로 파싱합니다.
            return str(data["choices"][0]["message"]["content"])  # AI 답변 텍스트를 돌려줍니다.
        except GeminiRequestError:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise  # 그대로 다시 올립니다.
        except requests.Timeout as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"timeout after {TIMEOUT_SECONDS} seconds") from exc  # API 오류를 위로 올려 보냅니다.
        except requests.RequestException as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"network error: {exc}") from exc  # API 오류를 위로 올려 보냅니다.
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"response parse error: {exc}") from exc  # API 오류를 위로 올려 보냅니다.
    raise GeminiRequestError("OpenRouter 요청 재시도 한도를 초과했습니다.")  # API 오류를 위로 올려 보냅니다.


# Copa(OpenAI 호환 엔드포인트)에 요청을 보내는 함수입니다.
def request_copa(
    api_key: str, model: str, prompt: str, *, max_output_tokens: int, response_schema: dict[str, Any] | None = None  # 이 함수들이 받는 재료들입니다.
) -> str:  # 호출 블록 끝.
    """copa.codyssey.kr(OpenAI 호환 엔드포인트)에 요청을 보냅니다."""  # OpenRouter와 같은 형식으로 요청합니다.
    if requests is None:  # requests 패키지가 없으면,
        raise PlannerError("외부 API 호출을 위해 requests 패키지가 필요합니다. pip install -r requirements.txt를 실행하세요.")  # 설치 안내와 함께 중단합니다.
    payload: dict[str, Any] = {  # 보낼 데이터(질문 본문)를 만듭니다.
        "model": model,  # 사용할 AI 모델을 지정합니다.
        "messages": [  # 대화 형식의 질문 목록입니다.
            {"role": "system", "content": "당신은 한국 국내 여행 추천 전문가입니다. 사용자의 지시를 충실히 따르고, 요구된 형식(JSON 또는 Markdown)으로만 답변하세요."},  # 시스템 지시: AI의 역할과 답변 형식을 정합니다.
            {"role": "user", "content": prompt},  # 사용자 질문을 담습니다.
        ],  # 목록 끝.
        "temperature": 0.5,  # 답변의 무작위성 조절값(0.5는 적당히 다양하게).
        "max_tokens": max_output_tokens,  # 답변 길이 상한입니다.
    }  # 블록 끝.
    for attempt in range(3):  # 최대 3번 시도합니다.
        try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
            response = requests.post(  # POST 요청을 보냅니다.
                COPA_URL,  # 요청을 보낼 주소입니다.
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},  # 인증 헤더(열쇠)를 담습니다.
                json=payload,  # 보낼 데이터 본문을 넣습니다.
                timeout=TIMEOUT_SECONDS,  # 최대 대기 시간을 둡니다.
            )  # 안내 메시지 끝.
            if response.status_code in (429, 503) and attempt < 2:  # 서버 응답 코드를 확인합니다.
                print(f"  - Copa 일시적 오류(HTTP {response.status_code}): 3초 후 재시도합니다.")  # 일시적 오류면 재시도합니다.  # 사용자에게 화면에 보여 줍니다.
                time.sleep(3)  # 3초 기다렸다가 다시 시도합니다.
                continue  # 다음 시도로 넘어갑니다.
            if response.status_code >= 400:  # 서버 응답 코드를 확인합니다.
                raise GeminiRequestError(f"HTTP {response.status_code}", response.status_code)  # API 오류를 위로 올려 보냅니다.
            data = response.json()  # 응답 본문을 JSON으로 파싱합니다.
            return str(data["choices"][0]["message"]["content"])  # AI 답변 텍스트를 돌려줍니다.
        except GeminiRequestError:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise  # 그대로 다시 올립니다.
        except requests.Timeout as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"timeout after {TIMEOUT_SECONDS} seconds") from exc  # API 오류를 위로 올려 보냅니다.
        except requests.RequestException as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"network error: {exc}") from exc  # API 오류를 위로 올려 보냅니다.
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"response parse error: {exc}") from exc  # API 오류를 위로 올려 보냅니다.
    raise GeminiRequestError("Copa 요청 재시도 한도를 초과했습니다.")  # 재시도 한도를 넘으면 오류를 냅니다.  # API 오류를 위로 올려 보냅니다.


def extract_gemini_text(payload: dict[str, Any]) -> str:  # 함수 정의입니다.
    try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
        parts = payload["candidates"][0]["content"]["parts"]
        text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    except (KeyError, IndexError, TypeError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
        raise ValueError("Gemini 응답에 생성 텍스트가 없습니다.") from exc
    if not text.strip():
        raise ValueError("Gemini가 빈 텍스트를 반환했습니다.")
    return text  # 못 찾았으면 원래 텍스트를 그대로 돌려줍니다.


def request_gemini(  # Gemini에 요청을 보내는 함수입니다.
    api_key: str, model: str, prompt: str, *, max_output_tokens: int, response_schema: dict[str, Any] | None = None  # 이 함수들이 받는 재료들입니다.
) -> str:  # 호출 블록 끝.
    if requests is None:  # requests 패키지가 없으면,
        raise PlannerError("외부 API 호출을 위해 requests 패키지가 필요합니다. pip install -r requirements.txt를 실행하세요.")  # 설치 안내와 함께 중단합니다.
    generation: dict[str, Any] = {"temperature": 0.5, "maxOutputTokens": max_output_tokens}  # 답변 생성 옵션을 만듭니다.
    # thinking 토큰이 maxOutputTokens를 잡아먹어 본문이 잘리는 문제 방지
    generation["thinkingConfig"] = {"thinkingBudget": 0}  # 답변 생성 옵션을 만듭니다.
    if response_schema:  # 스키마가 주어지면 JSON 형식 강제를 켭니다.
        generation.update({"responseMimeType": "application/json", "responseSchema": response_schema})  # 답변 생성 옵션을 만듭니다.
    payload = {  # 보낼 데이터(질문 본문)를 만듭니다.
        "systemInstruction": {"parts": [{"text": "당신은 한국 국내 여행 추천 전문가입니다. 사용자의 지시를 충실히 따르고, 요구된 형식(JSON 또는 Markdown)으로만 답변하세요."}]},  # AI에게 줄 역할 지시문입니다.
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],  # 사용자 질문 본문입니다.
        "generationConfig": generation,  # 생성 옵션을 넣습니다.
    }  # 블록 끝.
    for attempt in range(3):  # 최대 3번 시도합니다.
        try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
            response = requests.post(  # POST 요청을 보냅니다.
                GEMINI_URL.format(model=model),  # 모델명을 주소에 끼워 넣습니다.
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},  # 인증 헤더(열쇠)를 담습니다.
                json=payload,  # 보낼 데이터 본문을 넣습니다.
                timeout=TIMEOUT_SECONDS,  # 최대 대기 시간을 둡니다.
            )  # 안내 메시지 끝.
            if response.status_code == 503 and attempt < 2:  # 서버 응답 코드를 확인합니다.
                print("  - Gemini 일시적 과부하(HTTP 503): 3초 후 재시도합니다.")  # 사용자에게 화면에 보여 줍니다.
                time.sleep(3)  # 3초 기다렸다가 다시 시도합니다.
                continue  # 다음 시도로 넘어갑니다.
            if response.status_code >= 400:  # 서버 응답 코드를 확인합니다.
                raise GeminiRequestError(f"HTTP {response.status_code}", response.status_code)  # API 오류를 위로 올려 보냅니다.
            return extract_gemini_text(response.json())  # 응답에서 텍스트만 꺼내 돌려줍니다.
        except GeminiRequestError:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise  # 그대로 다시 올립니다.
        except requests.Timeout as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"timeout after {TIMEOUT_SECONDS} seconds") from exc  # API 오류를 위로 올려 보냅니다.
        except requests.RequestException as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"network error: {exc}") from exc  # API 오류를 위로 올려 보냅니다.
        except (ValueError, json.JSONDecodeError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"response parse error: {exc}") from exc  # API 오류를 위로 올려 보냅니다.
    raise GeminiRequestError("Gemini 요청 재시도 한도를 초과했습니다.")  # API 오류를 위로 올려 보냅니다.


def request_groq(  # Groq에 요청을 보내는 함수입니다.
    api_key: str, model: str, prompt: str, *, max_output_tokens: int, response_schema: dict[str, Any] | None = None  # 이 함수들이 받는 재료들입니다.
) -> str:  # 호출 블록 끝.
    if requests is None:  # requests 패키지가 없으면,
        raise PlannerError("requests 패키지가 필요합니다. pip install -r requirements.txt")  # 설치 안내와 함께 중단합니다.
    payload: dict[str, Any] = {  # 보낼 데이터(질문 본문)를 만듭니다.
        "model": model,  # 사용할 AI 모델을 지정합니다.
        "messages": [  # 대화 형식의 질문 목록입니다.
            {"role": "system", "content": "당신은 한국 국내 여행 추천 전문가입니다. 사용자의 지시를 충실히 따르고, 요구된 형식(JSON 또는 Markdown)으로만 답변하세요."},  # 시스템 지시: AI의 역할과 답변 형식을 정합니다.
            {"role": "user", "content": prompt},  # 사용자 질문을 담습니다.
        ],  # 목록 끝.
        "temperature": 0.5,  # 답변의 무작위성 조절값(0.5는 적당히 다양하게).
        "max_tokens": max_output_tokens,  # 답변 길이 상한입니다.
    }  # 블록 끝.
    for attempt in range(3):  # 최대 3번 시도합니다.
        try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
            response = requests.post(  # POST 요청을 보냅니다.
                GROQ_URL,  # 요청을 보낼 주소입니다.
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},  # 인증 헤더(열쇠)를 담습니다.
                json=payload,  # 보낼 데이터 본문을 넣습니다.
                timeout=TIMEOUT_SECONDS,  # 최대 대기 시간을 둡니다.
            )  # 안내 메시지 끝.
            if response.status_code in (429, 503) and attempt < 2:  # 서버 응답 코드를 확인합니다.
                print(f"  - Groq 일시적 오류(HTTP {response.status_code}): 3초 후 재시도합니다.")  # 사용자에게 화면에 보여 줍니다.
                time.sleep(3)  # 3초 기다렸다가 다시 시도합니다.
                continue  # 다음 시도로 넘어갑니다.
            if response.status_code >= 400:  # 서버 응답 코드를 확인합니다.
                raise GeminiRequestError(f"HTTP {response.status_code}", response.status_code)  # API 오류를 위로 올려 보냅니다.
            data = response.json()  # 응답 본문을 JSON으로 파싱합니다.
            return str(data["choices"][0]["message"]["content"])  # AI 답변 텍스트를 돌려줍니다.
        except GeminiRequestError:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise  # 그대로 다시 올립니다.
        except requests.Timeout as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"timeout after {TIMEOUT_SECONDS} seconds") from exc  # API 오류를 위로 올려 보냅니다.
        except requests.RequestException as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"network error: {exc}") from exc  # API 오류를 위로 올려 보냅니다.
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            raise GeminiRequestError(f"response parse error: {exc}") from exc  # API 오류를 위로 올려 보냅니다.
    raise GeminiRequestError("Groq 요청 재시도 한도를 초과했습니다.")  # API 오류를 위로 올려 보냅니다.


def create_recommendation(api_key: str, model: str, travel_date: str, errors: list[dict[str, str]], provider: str = "gemini") -> dict[str, Any]:  # 함수 정의입니다.
    month = int(travel_date.split("-")[1])  # 날짜에서 월만 숫자로 꺼냅니다.
    season = "봄" if month in (3, 4, 5) else "여름" if month in (6, 7, 8) else "가을" if month in (9, 10, 11) else "겨울"  # 월에 따라 계절을 정합니다.
    initial = f"""여행 날짜는 {travel_date}입니다. 이 날짜는 {season}에 해당합니다.  # AI에게 줄 1차 추천 지시문을 만듭니다.
같은 계절이라도 매번 다른 지역을 선정할 수 있도록, {season} 시기에 실제로 방문객이 많은 지역 중 하나를 다양하게 추천하세요.
도/광역 단위(예: 강원도, 경기도)가 아닌 시/군/구 단위의 구체적인 도시명(예: 제주, 강릉, 경주, 여수)을 추천하세요.
추천 근거(reason)에는 반드시 해당 계절({season})의 날씨 특징과 그 계절에 어울리는 이유를 포함하세요.
실시간 예보·확정 행사가 아닌 일반적 계절 경향과 행사 후보를 제시하세요.
JSON 객체만 반환하세요: recommended_city(문자열), weather(문자열), events(문자열 배열 1~3개), reason(2~4문장 문자열)."""
    repair = "설명이나 마크다운 코드블록 없이 recommended_city, weather, events, reason 네 키만 가진 유효한 JSON 객체만 반환하세요."  # JSON이 깨졌을 때 다시 시키는 짧은 지시문입니다.
    for attempt in range(3):  # 최대 3번 시도합니다.
        try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
            raw_text = (request_gemini if provider == "gemini" else request_openrouter if provider == "openrouter" else request_copa if provider == "copa" else request_groq)(  # 제공자에 맞는 함수로 AI 답변을 받습니다.
                api_key, model, initial if attempt == 0 else repair, max_output_tokens=700, response_schema=RECOMMENDATION_SCHEMA  # 인자를 전달합니다.
            )  # 안내 메시지 끝.
            json_text = extract_json_object(raw_text)  # 답변에서 JSON 부분만 골라냅니다.
            return validate_recommendation(json.loads(json_text))  # JSON을 해석하고 형식을 검사한 뒤 돌려줍니다.
        except (json.JSONDecodeError, ValueError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            if attempt < 2:  # 아직 남은 시도가 있으면,
                print("  - JSON 검증 실패: 형식을 보정하여 재시도합니다.")  # 사용자에게 화면에 보여 줍니다.
                continue  # 다음 시도로 넘어갑니다.
            add_error(errors, "recommendation", "JSON_PARSE_ERROR", str(exc))  # 오류 목록에 실패를 기록합니다.
            raise PlannerError("LLM 추천 JSON을 생성하지 못했습니다. 잠시 후 다시 시도하세요.") from exc  # 친절한 오류 메시지로 중단합니다.
        except GeminiRequestError as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
            status = exc.status_code  # 오류에 담긴 HTTP 코드를 꺼냅니다.
            kind = "AUTH_ERROR" if status in (401, 403) else "QUOTA_ERROR" if status == 429 else "NETWORK_OR_API_ERROR"  # HTTP 코드에 따라 오류 종류를 정합니다.
            add_error(errors, "recommendation", kind, str(exc))  # 오류 목록에 실패를 기록합니다.
            if status == 429:  # 요청 제한(429)이면,
                raise PlannerError("LLM 무료 모델의 요청 제한 또는 쿼터를 확인하세요(HTTP 429). 잠시 후 다시 시도하거나 다른 모델을 사용하세요.") from exc  # 친절한 오류 메시지로 중단합니다.
            if status in (401, 403):  # 인증 오류(401/403)면,
                raise PlannerError(f"LLM API 키 또는 설정을 확인하세요(HTTP {status}).") from exc  # 친절한 오류 메시지로 중단합니다.
            raise PlannerError(f"LLM API 연결 또는 응답 처리에 실패했습니다(HTTP {status}).") from exc  # 친절한 오류 메시지로 중단합니다.
    raise PlannerError("Gemini 추천 생성 재시도 한도를 초과했습니다.")  # 친절한 오류 메시지로 중단합니다.


def normalize_place(place: dict[str, Any]) -> dict[str, Any]:  # 함수 정의입니다.
    def as_number(value: Any) -> float | None:  # 함수 정의입니다.
        try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
            return float(value) if value not in (None, "") else None  # 숫자로 바꾸어 돌려줍니다.
        except (TypeError, ValueError):  # 해당 오류가 나면 아래처럼 처리합니다.
            return None  # 없다는 뜻으로 None을 돌려줍니다.
    return {  # 표준 모양의 사전을 만듭니다.
        "name": str(place.get("place_name", "")),  # 장소 이름을 표준 키에 담습니다.
        "address": str(place.get("road_address_name") or place.get("address_name") or ""),  # 주소를 표준 키에 담습니다.
        "category": str(place.get("category_name", "")),  # 카테고리를 표준 키에 담습니다.
        "url": str(place.get("place_url", "")),  # 장소 링크를 표준 키에 담습니다.
        "x": as_number(place.get("x")), "y": as_number(place.get("y")),  # 경도·위도를 숫자로 담습니다.
    }  # 블록 끝.


def search_restaurants(city: str, errors: list[dict[str, str]]) -> list[dict[str, Any]]:  # 함수 정의입니다.
    kakao_key = os.getenv("KAKAO_REST_API_KEY")  # Kakao 키를 읽습니다.
    search_city = normalize_city_name(city)  # 도시 이름을 검색에 적합하게 바꿉니다.
    if not kakao_key:  # 키가 없으면,
        add_error(errors, "place_search", "MISSING_API_KEY", "KAKAO_REST_API_KEY가 없어 장소 검색을 건너뛰었습니다.")  # 오류 목록에 이유를 남깁니다.
        print("  - KAKAO_REST_API_KEY 미설정: 맛집을 '데이터 없음'으로 처리하고 계속합니다.")  # 사용자에게 화면에 보여 줍니다.
        return []  # 빈 목록을 돌려줍니다.
    try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
        response = requests.get(  # GET 요청을 보냅니다.
            KAKAO_KEYWORD_URL,
            headers={"Authorization": f"KakaoAK {kakao_key}"},  # 인증 헤더(열쇠)를 담습니다.
            params={"query": f"{search_city} 맛집", "size": 5},  # 검색어와 개수를 파라미터로 보냅니다.
            timeout=TIMEOUT_SECONDS,  # 최대 대기 시간을 둡니다.
        )  # 안내 메시지 끝.
        if response.status_code in (401, 403):  # 서버 응답 코드를 확인합니다.
            add_error(errors, "place_search", "AUTH_ERROR", f"HTTP {response.status_code}")  # 오류 목록에 이유를 남깁니다.
            print(f"  - 장소 검색 인증 실패(HTTP {response.status_code}): 데이터 없음으로 계속합니다.")  # 사용자에게 화면에 보여 줍니다.
            return []  # 빈 목록을 돌려줍니다.
        if response.status_code == 429:  # 서버 응답 코드를 확인합니다.
            add_error(errors, "place_search", "QUOTA_ERROR", "HTTP 429")  # 오류 목록에 이유를 남깁니다.
            print("  - 장소 검색 쿼터 제한(HTTP 429): 데이터 없음으로 계속합니다.")  # 사용자에게 화면에 보여 줍니다.
            return []  # 빈 목록을 돌려줍니다.
        response.raise_for_status()  # 오류 코드면 예외를 내 줍니다.
        documents = response.json().get("documents", [])  # 장소 목록을 꺼냅니다.
        if not isinstance(documents, list):  # 목록 형태가 아니면 거부합니다.
            raise ValueError("Kakao 응답의 documents 형식이 목록이 아닙니다.")  # 오류를 냅니다.
        places = [normalize_place(place) for place in documents[:5] if isinstance(place, dict)]  # 각 장소를 표준 모양으로 바꿉니다(최대 5곳).
        if not places:  # 검색 결과가 없으면,
            add_error(errors, "place_search", "EMPTY_RESULT", f"0 results for query={city} 맛집")  # 오류 목록에 이유를 남깁니다.
            print("  - 검색 결과 0건: 데이터 없음으로 계속합니다.")  # 사용자에게 화면에 보여 줍니다.
        return places  # 맛집 목록을 돌려줍니다.
    except requests.Timeout:  # 해당 오류가 나면 아래처럼 처리합니다.
        add_error(errors, "place_search", "NETWORK_TIMEOUT", f"timeout after {TIMEOUT_SECONDS} seconds")  # 오류 목록에 이유를 남깁니다.
    except requests.RequestException as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
        add_error(errors, "place_search", "NETWORK_OR_HTTP_ERROR", str(exc))  # 오류 목록에 이유를 남깁니다.
    except (ValueError, json.JSONDecodeError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
        add_error(errors, "place_search", "RESPONSE_PARSE_ERROR", str(exc))  # 오류 목록에 이유를 남깁니다.
    print("  - 장소 검색 요청 또는 응답 처리 실패: 데이터 없음으로 계속합니다.")  # 사용자에게 화면에 보여 줍니다.
    return []  # 빈 목록을 돌려줍니다.


def fallback_report(date: str, recommendation: dict[str, Any], places: list[dict[str, Any]], errors: list[dict[str, str]]) -> str:  # 함수 정의입니다.
    restaurants = "\n".join(f"- **{p['name']}** — {p['address']}" for p in places) or "- 데이터 없음"  # 맛집 목록을 불릿 문자열로 만듭니다.
    events = "\n".join(f"- {event}" for event in recommendation["events"]) or "- 데이터 없음"  # 행사 목록을 불릿 문자열로 만듭니다.
    errors_text = "\n".join(f"- [{e['step']}/{e['type']}] {e['message']}" for e in errors) or "- 없음"  # 오류 목록을 불릿 문자열로 만듭니다.
    return f"""# {date} 국내 여행 추천 리포트

> 최종 Gemini 리포트 생성에 실패해 확보한 데이터로 만든 대체 리포트입니다.

## 추천 지역

**{recommendation['recommended_city']}**

## 추천 이유

{recommendation['reason']}

## 날씨 요약

{recommendation['weather']}

## 행사/축제

{events}

## 맛집 추천

{restaurants}

## 1일 일정 제안

오전에는 대표 관광지와 산책 코스를 둘러보고, 오후에는 지역 문화 공간 또는 카페를 방문합니다. 저녁에는 맛집 목록을 확인해 식사하고 야간 산책으로 마무리합니다.

## 오류 요약(errors)

{errors_text}
"""


def create_report(api_key: str, model: str, date: str, recommendation: dict[str, Any], places: list[dict[str, Any]], errors: list[dict[str, str]], provider: str = "gemini") -> str:  # 함수 정의입니다.
    source = json.dumps({"recommendation": recommendation, "restaurants": places, "errors": errors}, ensure_ascii=False, indent=2)  # 추천·맛집·오류 데이터를 JSON 문자열로 묶습니다.
    prompt = f"""다음은 {date} 국내 여행 추천 입력 데이터입니다. 이 데이터만 근거로 한국어 Markdown 리포트를 작성하세요.  # AI에게 줄 리포트 작성 지시문을 만듭니다.

{source}

반드시 추천 지역, 추천 이유, 날씨 요약, 행사/축제, 맛집 추천, 1일 일정 제안, 오류 요약(errors) 제목을 포함하세요. 맛집 목록이 비어 있으면 맛집 추천에 정확히 '데이터 없음'이라고 쓰고, 행사는 확정이 아닌 후보임을 밝히세요."""
    try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
        report = (request_gemini if provider == "gemini" else request_openrouter if provider == "openrouter" else request_copa if provider == "copa" else request_groq)(api_key, model, prompt, max_output_tokens=1400)  # 제공자에 맞는 함수로 리포트를 받습니다.
        return f"# {date} 국내 여행 추천 리포트\n\n{report.lstrip('# ').strip()}\n"
    except (GeminiRequestError, ValueError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
        add_error(errors, "report_generation", "GEMINI_REPORT_ERROR", str(exc))  # 오류 목록에 실패 이유를 남깁니다.
        print("  - 최종 Gemini 리포트 생성 실패: 대체 Markdown 리포트를 저장합니다.")  # 사용자에게 화면에 보여 줍니다.
        return fallback_report(date, recommendation, places, errors)


def load_cached_data(date: str) -> dict[str, Any] | None:  # 함수 정의입니다.
    """기존 저장된 원본 데이터(JSON)가 있으면 읽어와 반환 (항목 4: 결과 캐싱 전략)."""
    data_path = RESULTS_DIR / f"{date}_travel_data.json"  # JSON 결과 파일 경로를 만듭니다.
    if not data_path.exists():  # 저장된 JSON이 없으면,
        return None  # 없다는 뜻으로 None을 돌려줍니다.
    try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
        content = json.loads(data_path.read_text(encoding="utf-8"))  # 파일 내용을 읽어 JSON으로 해석합니다.
        if isinstance(content, dict) and "recommendation" in content and "restaurants" in content:  # 형식이 맞는지 확인합니다.
            return content  # 유효한 캐시 데이터를 돌려줍니다.
    except Exception:  # 해당 오류가 나면 아래처럼 처리합니다.
        return None  # 없다는 뜻으로 None을 돌려줍니다.
    return None  # 없다는 뜻으로 None을 돌려줍니다.


def write_results(date: str, recommendation: dict[str, Any], places: list[dict[str, Any]], errors: list[dict[str, str]], report: str) -> tuple[Path, Path]:  # 함수 정의입니다.
    RESULTS_DIR.mkdir(exist_ok=True)  # results 폴더가 없으면 만듭니다.
    data_path, report_path = RESULTS_DIR / f"{date}_travel_data.json", RESULTS_DIR / f"{date}_travel_plan.md"  # 두 결과 파일 경로를 만듭니다.
    data_path.write_text(json.dumps({"travel_date": date, "recommendation": recommendation, "restaurants": places, "errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")  # 원본 데이터를 JSON 파일로 저장합니다.
    report_path.write_text(report, encoding="utf-8")  # 리포트를 Markdown 파일로 저장합니다.
    return data_path, report_path  # 저장된 파일 경로들을 돌려줍니다.


def run_pipeline(provider: str, api_key: str, model: str, travel_date: str, errors: list[dict[str, str]]) -> tuple[dict[str, Any], list[dict[str, Any]], str]:  # 함수 정의입니다.
    """선택된 제공자로 [1/3] → [2/3] → [3/3] 전체 파이프라인을 실행합니다."""
    print(f"[1/3] 1차 추천 생성 중({provider})...")  # 사용자에게 화면에 보여 줍니다.
    recommendation = create_recommendation(api_key, model, travel_date, errors, provider)  # 4) 1단계: AI가 추천 JSON을 만듭니다.
    print(f"  - recommended_city: {recommendation['recommended_city']}")  # 사용자에게 화면에 보여 줍니다.
    print("[2/3] 맛집 검색 중(Kakao Local API)...")  # 사용자에게 화면에 보여 줍니다.
    places = search_restaurants(recommendation["recommended_city"], errors)  # 5) 2단계: 카카오 지도에서 맛집을 검색합니다.
    print(f"  - 맛집 {len(places)}곳 검색 완료")  # 사용자에게 화면에 보여 줍니다.
    print(f"[3/3] 최종 리포트 생성 중({provider})...")  # 사용자에게 화면에 보여 줍니다.
    report = create_report(api_key, model, travel_date, recommendation, places, errors, provider)  # 6) 3단계: AI가 최종 리포트를 만듭니다.
    return recommendation, places, report


def _is_quota_or_overload_error(exc: Exception) -> bool:  # 함수 정의입니다.
    """429(요청 제한) 또는 503(과부하) 성격의 오류인지 확인합니다. 전환 대상 여부 판단에 씁니다."""
    text = str(exc)
    return any(keyword in text for keyword in ("429", "503", "제한", "쿼터", "과부하"))


# 현재 제공자가 안 되면 대신 쓸 수 있는 다른 제공자를 찾습니다. 키가 없으면 None.
# 폴백 순서: Gemini → OpenRouter(무료 라우터) → Copa(OpenAI 호환)
def _fallback_provider(provider: str) -> tuple[str, str, str] | None:
    """현재 제공자가 안 되면 대신 쓸 수 있는 다른 제공자를 찾습니다. 키가 없으면 None.
    폴백 순서: Gemini → OpenRouter(무료 라우터) → Copa(OpenAI 호환)"""
    if provider == "gemini":  # Gemini를 쓰기로 했다면,
        openrouter_key = os.getenv("OPENROUTER_API_KEY")  # OpenRouter 키도 확인합니다.
        if openrouter_key:  # OpenRouter 키가 있으면 OpenRouter를,
            return "openrouter", openrouter_key, os.getenv("OPENROUTER_MODEL", "openrouter/free")  # OpenRouter를 씁니다.
        copa_key = os.getenv("COPA_API_KEY")  # Copa 키를 읽습니다.
        if copa_key:
            return "copa", copa_key, os.getenv("COPA_MODEL", "gpt-5-mini")
    if provider == "openrouter":  # OpenRouter를 쓰기로 했다면,
        copa_key = os.getenv("COPA_API_KEY")  # Copa 키를 읽습니다.
        if copa_key:
            return "copa", copa_key, os.getenv("COPA_MODEL", "gpt-5-mini")
        api_key, model = build_gemini_settings()  # Gemini 설정을 읽어 옵니다.
        return "gemini", api_key, model  # 마지막으로 Gemini를 씁니다.
    if provider == "copa":  # Copa를 쓰기로 했다면,
        openrouter_key = os.getenv("OPENROUTER_API_KEY")  # OpenRouter 키도 확인합니다.
        if openrouter_key:  # OpenRouter 키가 있으면 OpenRouter를,
            return "openrouter", openrouter_key, os.getenv("OPENROUTER_MODEL", "openrouter/free")  # OpenRouter를 씁니다.
        api_key, model = build_gemini_settings()  # Gemini 설정을 읽어 옵니다.
        return "gemini", api_key, model  # 마지막으로 Gemini를 씁니다.
    return None  # 없다는 뜻으로 None을 돌려줍니다.


def main() -> int:  # 함수 정의입니다.
    args = parse_args()  # 1) 명령어 옵션 읽기.
    load_dotenv(BASE_DIR / ".env")  # 2) .env에서 키 읽기.
    errors: list[dict[str, str]] = []  # 오류를 모을 빈 목록을 준비합니다.

    # 항목 4: 결과 캐싱 검사
    cached_data = None  # 캐시 데이터를 담을 변수를 준비합니다.
    if args.cached or (not args.refresh and (RESULTS_DIR / f"{args.travel_date}_travel_data.json").exists()):  # 캐시를 써야 하는 상황인지 판단합니다.
        cached_data = load_cached_data(args.travel_date)  # 캐시 파일을 읽어 옵니다.

    if cached_data:  # 캐시가 있으면,
        print(f"[캐시 재사용] {args.travel_date} 저장된 원본 JSON을 활용하여 외부 API 호출을 생략합니다.")  # 사용자에게 화면에 보여 줍니다.
        print("  - (새로고침을 원할 경우 --refresh 옵션을 사용하세요)")  # 사용자에게 화면에 보여 줍니다.
        recommendation = cached_data["recommendation"]  # 캐시에서 추천 데이터를 꺼냅니다.
        places = cached_data["restaurants"]  # 캐시에서 맛집 목록을 꺼냅니다.
        errors = cached_data.get("errors", [])  # 캐시에서 오류 목록을 꺼냅니다.
        report_path = RESULTS_DIR / f"{args.travel_date}_travel_plan.md"  # Markdown 리포트 파일 경로를 만듭니다.
        data_path = RESULTS_DIR / f"{args.travel_date}_travel_data.json"  # JSON 결과 파일 경로를 만듭니다.

        if not report_path.exists():  # 리포트 파일이 없으면 새로 만듭니다.
            report = fallback_report(args.travel_date, recommendation, places, errors)  # 대체 리포트를 만듭니다.
            report_path.write_text(report, encoding="utf-8")  # 리포트를 Markdown 파일로 저장합니다.

        print("  - 캐시 기반 리포트 로드 완료")  # 사용자에게 화면에 보여 줍니다.
        print(f"완료! {report_path.relative_to(BASE_DIR)} 및 {data_path.relative_to(BASE_DIR)}를 확인하세요.")  # 사용자에게 화면에 보여 줍니다.
        return 0  # 정상 종료를 알립니다(0은 성공 코드).

    try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
        provider, api_key, model = build_llm_settings()  # 3) AI 제공자와 키, 모델을 결정합니다.
        # 3중 폴백: 현재 제공자가 429/503으로 실패하면 다른 제공자로 순서대로 전환
        tried = {provider}  # 이미 시도한 제공자를 기록해 둡니다.
        while True:  # 올바른 날짜가 입력될 때까지 반복합니다.
            try:  # 오류가 날 수 있는 코드를 감싸서, 문제가 생기면 except에서 처리합니다.
                recommendation, places, report = run_pipeline(provider, api_key, model, args.travel_date, errors)  # 현재 제공자로 실행
                break  # 성공하면 반복을 끝냅니다.  # 올바른 날짜가 확인됐으므로 반복을 끝냅니다.
            except (PlannerError, GeminiRequestError) as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
                if not _is_quota_or_overload_error(exc):  # 한도/과부하가 아닌 오류면,
                    raise  # 전환하지 않고 그냥 오류를 냅니다.  # 그대로 다시 올립니다.
                fallback = _fallback_provider(provider)  # 대안 제공자를 찾습니다.
                if fallback is None or fallback[0] in tried:  # 대안이 없거나 이미 시도했으면,
                    raise  # 오류를 냅니다.  # 그대로 다시 올립니다.
                provider, api_key, model = fallback  # 대안 제공자로 교체합니다.
                tried.add(provider)  # 시도했다고 기록합니다.
                print(f"  - 현재 제공자 장애/한도로 인해 {provider}(으)로 자동 전환합니다.")  # 사용자에게 화면에 보여 줍니다.
        data_path, report_path = write_results(args.travel_date, recommendation, places, errors, report)  # 두 결과 파일 경로를 만듭니다.
        print("  - 리포트 생성 완료")  # 사용자에게 화면에 보여 줍니다.
        print(f"완료! {report_path.relative_to(BASE_DIR)} 및 {data_path.relative_to(BASE_DIR)}를 확인하세요.")  # 사용자에게 화면에 보여 줍니다.
        return 0  # 정상 종료를 알립니다(0은 성공 코드).
    except PlannerError as exc:  # 해당 오류가 나면 아래처럼 처리합니다.
        print(f"오류: {exc}", file=sys.stderr)  # 사용자에게 화면에 보여 줍니다.
        return 1  # 실패 종료를 알립니다(1은 오류 코드).


if __name__ == "__main__":  # 이 파일을 직접 실행할 때만 아래를 실행합니다.
    raise SystemExit(main())  # main() 결과 코드로 프로그램을 종료합니다.
