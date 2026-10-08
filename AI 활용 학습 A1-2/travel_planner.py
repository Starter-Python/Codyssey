#!/usr/bin/env python3
"""Gemini API와 Kakao Local API로 국내 여행 추천 리포트를 생성하는 CLI 프로그램."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args: Any, **kwargs: Any) -> bool:  # type: ignore[misc]
        return False

BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
COPA_URL = "https://copa.codyssey.kr/v1/chat/completions"
TIMEOUT_SECONDS = 20
RECOMMENDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "recommended_city": {"type": "string"},
        "weather": {"type": "string"},
        "events": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["recommended_city", "weather", "events", "reason"],
}


class PlannerError(RuntimeError):
    """사용자에게 안내할 수 있는 오류."""


class GeminiRequestError(RuntimeError):
    """HTTP 상태를 포함하는 Gemini API 요청 오류."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gemini API와 Kakao Local API로 국내 여행 추천 리포트를 생성합니다.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-date", "--date", dest="travel_date", required=False, default=None, metavar="YYYY-MM-DD", help="여행 날짜 (생략하면 실행 중에 입력받습니다)")
    parser.add_argument("--cached", action="store_true", help="저장된 원본 데이터(JSON)가 있으면 API 재호출 없이 캐시를 재사용합니다.")
    parser.add_argument("--refresh", action="store_true", help="기존 캐시를 무시하고 API를 새로 호출합니다.")
    args = parser.parse_args()
    if args.travel_date is None:
        while True:
            try:
                args.travel_date = input("여행 날짜를 입력하세요 (YYYY-MM-DD): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                parser.error("날짜가 입력되지 않았습니다.")
            try:
                datetime.strptime(args.travel_date, "%Y-%m-%d")
                break
            except ValueError:
                print("  - YYYY-MM-DD 형식의 실제 날짜로 다시 입력하세요.")
    else:
        try:
            datetime.strptime(args.travel_date, "%Y-%m-%d")
        except ValueError:
            parser.error("-date/--date는 YYYY-MM-DD 형식의 실제 날짜여야 합니다.")
    return args


def normalize_city_name(city: str) -> str:
    """광역시/도 등 광역 지자체 명칭이나 수식어를 지도 검색에 적합한 대표 도시/지역명으로 정규화."""
    cleaned = city.strip()
    replacements = {
        "제주특별자치도": "제주",
        "강원특별자치도": "강원",
        "전북특별자치도": "전북",
        "강원도": "강릉",  # 광역 도 단위일 경우 관광 중심 도시로 보정
        "경기도": "가평",
        "충청북도": "단양",
        "충청남도": "태안",
        "전라북도": "전주",
        "전라남도": "여수",
        "경상북도": "경주",
        "경상남도": "통영",
        "서울특별시": "서울",
        "부산광역시": "부산",
        "대구광역시": "대구",
        "인천광역시": "인천",
        "광주광역시": "광주",
        "대전광역시": "대전",
        "울산광역시": "울산",
        "세종특별자치시": "세종",
    }
    return replacements.get(cleaned, cleaned)


def extract_json_object(raw_text: str) -> str:
    """마크다운 코드블록이나 불필요한 앞뒤 텍스트가 섞여 있어도 유효한 JSON 객체 블록만 추출."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def redact_secrets(message: str) -> str:
    safe = str(message)
    for name in ("GEMINI_API_KEY", "KAKAO_REST_API_KEY", "OPENROUTER_API_KEY"):
        if key := os.getenv(name):
            safe = safe.replace(key, "[REDACTED]")
    return re.sub(r"(?:AIza|sk-)[A-Za-z0-9_-]+", "[REDACTED]", safe)


def add_error(errors: list[dict[str, str]], step: str, kind: str, message: str) -> None:
    errors.append({"step": step, "type": kind, "message": redact_secrets(message)[:300]})


def validate_recommendation(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("추천 결과의 최상위 형식이 객체가 아닙니다.")
    if "recommended_city" not in data and len(data) == 1:
        only = next(iter(data.values()))
        if isinstance(only, dict):
            data = only
    if isinstance(data.get("events"), str):
        data["events"] = [s.strip() for s in data["events"].split(",") if s.strip()]
    required = {"recommended_city": str, "weather": str, "events": list, "reason": str}
    for name, value_type in required.items():
        if not isinstance(data.get(name), value_type):
            raise ValueError(f"필수 키 또는 타입이 올바르지 않습니다: {name}")
    if not all(data[name].strip() for name in ("recommended_city", "weather", "reason")):
        raise ValueError("문자열 필수 값이 비어 있습니다.")
    if not all(isinstance(item, str) for item in data["events"]):
        raise ValueError("events의 모든 항목은 문자열이어야 합니다.")
    return data


def build_gemini_settings() -> tuple[str, str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise PlannerError(
            "GEMINI_API_KEY가 설정되지 않았습니다. .env에 GEMINI_API_KEY를 설정하거나 "
            "export GEMINI_API_KEY='YOUR_KEY'를 실행한 뒤 다시 시도하세요."
        )
    # 무료 등급 사용 가능 모델은 계정·시점별로 다를 수 있어 환경변수로 바꿀 수 있다.
    return api_key, os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def build_llm_settings() -> tuple[str, str, str]:
    """LLM 제공자를 결정한다."""
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    groq_key = os.getenv("GROQ_API_KEY")
    if provider == "groq":
        if not groq_key:
            raise PlannerError("GROQ_API_KEY가 설정되지 않았습니다. .env에 GROQ_API_KEY를 설정하세요.")
        return "groq", groq_key, os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    if provider == "openrouter":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise PlannerError("OPENROUTER_API_KEY가 설정되지 않았습니다. .env에 OPENROUTER_API_KEY를 설정하세요.")
        return "openrouter", openrouter_key, os.getenv("OPENROUTER_MODEL", "openrouter/free")
    if provider == "copa":
        copa_key = os.getenv("COPA_API_KEY")
        if not copa_key:
            raise PlannerError("COPA_API_KEY가 설정되지 않았습니다. .env에 COPA_API_KEY를 설정하세요.")
        return "copa", copa_key, os.getenv("COPA_MODEL", "gemini-3-flash")
    if provider == "gemini":
        api_key, model = build_gemini_settings()
        return "gemini", api_key, model

    # LLM_PROVIDER 미설정: Groq → OpenRouter → Copa → Gemini 순으로 키가 있으면 사용
    if groq_key:
        return "groq", groq_key, os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return "openrouter", openrouter_key, os.getenv("OPENROUTER_MODEL", "openrouter/free")
    copa_key = os.getenv("COPA_API_KEY")
    if copa_key:
        return "copa", copa_key, os.getenv("COPA_MODEL", "gemini-3-flash")
    api_key, model = build_gemini_settings()
    return "gemini", api_key, model


def request_openrouter(
    api_key: str, model: str, prompt: str, *, max_output_tokens: int, response_schema: dict[str, Any] | None = None
) -> str:
    if requests is None:
        raise PlannerError("외부 API 호출을 위해 requests 패키지가 필요합니다. pip install -r requirements.txt를 실행하세요.")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "당신은 한국 국내 여행 추천 전문가입니다. 사용자의 지시를 충실히 따르고, 요구된 형식(JSON 또는 Markdown)으로만 답변하세요."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": max_output_tokens,
    }
    for attempt in range(3):
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code in (429, 503) and attempt < 2:
                print(f"  - OpenRouter 일시적 오류(HTTP {response.status_code}): 3초 후 재시도합니다.")
                time.sleep(3)
                continue
            if response.status_code >= 400:
                raise GeminiRequestError(f"HTTP {response.status_code}", response.status_code)
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except GeminiRequestError:
            raise
        except requests.Timeout as exc:
            raise GeminiRequestError(f"timeout after {TIMEOUT_SECONDS} seconds") from exc
        except requests.RequestException as exc:
            raise GeminiRequestError(f"network error: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GeminiRequestError(f"response parse error: {exc}") from exc
    raise GeminiRequestError("OpenRouter 요청 재시도 한도를 초과했습니다.")


def request_copa(
    api_key: str, model: str, prompt: str, *, max_output_tokens: int, response_schema: dict[str, Any] | None = None
) -> str:
    """copa.codyssey.kr(OpenAI 호환 엔드포인트)에 요청을 보냅니다."""
    if requests is None:
        raise PlannerError("외부 API 호출을 위해 requests 패키지가 필요합니다. pip install -r requirements.txt를 실행하세요.")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "당신은 한국 국내 여행 추천 전문가입니다. 사용자의 지시를 충실히 따르고, 요구된 형식(JSON 또는 Markdown)으로만 답변하세요."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": max_output_tokens,
    }
    for attempt in range(3):
        try:
            response = requests.post(
                COPA_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code in (429, 503) and attempt < 2:
                print(f"  - Copa 일시적 오류(HTTP {response.status_code}): 3초 후 재시도합니다.")
                time.sleep(3)
                continue
            if response.status_code >= 400:
                raise GeminiRequestError(f"HTTP {response.status_code}", response.status_code)
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except GeminiRequestError:
            raise
        except requests.Timeout as exc:
            raise GeminiRequestError(f"timeout after {TIMEOUT_SECONDS} seconds") from exc
        except requests.RequestException as exc:
            raise GeminiRequestError(f"network error: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GeminiRequestError(f"response parse error: {exc}") from exc
    raise GeminiRequestError("Copa 요청 재시도 한도를 초과했습니다.")


def extract_gemini_text(payload: dict[str, Any]) -> str:
    try:
        parts = payload["candidates"][0]["content"]["parts"]
        text = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Gemini 응답에 생성 텍스트가 없습니다.") from exc
    if not text.strip():
        raise ValueError("Gemini가 빈 텍스트를 반환했습니다.")
    return text


def request_gemini(
    api_key: str, model: str, prompt: str, *, max_output_tokens: int, response_schema: dict[str, Any] | None = None
) -> str:
    if requests is None:
        raise PlannerError("외부 API 호출을 위해 requests 패키지가 필요합니다. pip install -r requirements.txt를 실행하세요.")
    generation: dict[str, Any] = {"temperature": 0.5, "maxOutputTokens": max_output_tokens}
    # thinking 토큰이 maxOutputTokens를 잡아먹어 본문이 잘리는 문제 방지
    generation["thinkingConfig"] = {"thinkingBudget": 0}
    if response_schema:
        generation.update({"responseMimeType": "application/json", "responseSchema": response_schema})
    payload = {
        "systemInstruction": {"parts": [{"text": "당신은 한국 국내 여행 추천 전문가입니다. 사용자의 지시를 충실히 따르고, 요구된 형식(JSON 또는 Markdown)으로만 답변하세요."}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": generation,
    }
    for attempt in range(3):
        try:
            response = requests.post(
                GEMINI_URL.format(model=model),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code == 503 and attempt < 2:
                print("  - Gemini 일시적 과부하(HTTP 503): 3초 후 재시도합니다.")
                time.sleep(3)
                continue
            if response.status_code >= 400:
                raise GeminiRequestError(f"HTTP {response.status_code}", response.status_code)
            return extract_gemini_text(response.json())
        except GeminiRequestError:
            raise
        except requests.Timeout as exc:
            raise GeminiRequestError(f"timeout after {TIMEOUT_SECONDS} seconds") from exc
        except requests.RequestException as exc:
            raise GeminiRequestError(f"network error: {exc}") from exc
        except (ValueError, json.JSONDecodeError) as exc:
            raise GeminiRequestError(f"response parse error: {exc}") from exc
    raise GeminiRequestError("Gemini 요청 재시도 한도를 초과했습니다.")


def request_groq(
    api_key: str, model: str, prompt: str, *, max_output_tokens: int, response_schema: dict[str, Any] | None = None
) -> str:
    if requests is None:
        raise PlannerError("requests 패키지가 필요합니다. pip install -r requirements.txt")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": "당신은 한국 국내 여행 추천 전문가입니다. 사용자의 지시를 충실히 따르고, 요구된 형식(JSON 또는 Markdown)으로만 답변하세요."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.5,
        "max_tokens": max_output_tokens,
    }
    for attempt in range(3):
        try:
            response = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=TIMEOUT_SECONDS,
            )
            if response.status_code in (429, 503) and attempt < 2:
                print(f"  - Groq 일시적 오류(HTTP {response.status_code}): 3초 후 재시도합니다.")
                time.sleep(3)
                continue
            if response.status_code >= 400:
                raise GeminiRequestError(f"HTTP {response.status_code}", response.status_code)
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except GeminiRequestError:
            raise
        except requests.Timeout as exc:
            raise GeminiRequestError(f"timeout after {TIMEOUT_SECONDS} seconds") from exc
        except requests.RequestException as exc:
            raise GeminiRequestError(f"network error: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GeminiRequestError(f"response parse error: {exc}") from exc
    raise GeminiRequestError("Groq 요청 재시도 한도를 초과했습니다.")


def create_recommendation(api_key: str, model: str, travel_date: str, errors: list[dict[str, str]], provider: str = "gemini") -> dict[str, Any]:
    month = int(travel_date.split("-")[1])
    season = "봄" if month in (3, 4, 5) else "여름" if month in (6, 7, 8) else "가을" if month in (9, 10, 11) else "겨울"
    initial = f"""여행 날짜는 {travel_date}입니다. 이 날짜는 {season}에 해당합니다.
같은 계절이라도 매번 다른 지역을 선정할 수 있도록, {season} 시기에 실제로 방문객이 많은 지역 중 하나를 다양하게 추천하세요.
도/광역 단위(예: 강원도, 경기도)가 아닌 시/군/구 단위의 구체적인 도시명(예: 제주, 강릉, 경주, 여수)을 추천하세요.
추천 근거(reason)에는 반드시 해당 계절({season})의 날씨 특징과 그 계절에 어울리는 이유를 포함하세요.
실시간 예보·확정 행사가 아닌 일반적 계절 경향과 행사 후보를 제시하세요.
JSON 객체만 반환하세요: recommended_city(문자열), weather(문자열), events(문자열 배열 1~3개), reason(2~4문장 문자열)."""
    repair = "설명이나 마크다운 코드블록 없이 recommended_city, weather, events, reason 네 키만 가진 유효한 JSON 객체만 반환하세요."
    for attempt in range(3):
        try:
            raw_text = (request_gemini if provider == "gemini" else request_openrouter if provider == "openrouter" else request_copa if provider == "copa" else request_groq)(
                api_key, model, initial if attempt == 0 else repair, max_output_tokens=700, response_schema=RECOMMENDATION_SCHEMA
            )
            json_text = extract_json_object(raw_text)
            return validate_recommendation(json.loads(json_text))
        except (json.JSONDecodeError, ValueError) as exc:
            if attempt < 2:
                print("  - JSON 검증 실패: 형식을 보정하여 재시도합니다.")
                continue
            add_error(errors, "recommendation", "JSON_PARSE_ERROR", str(exc))
            raise PlannerError("LLM 추천 JSON을 생성하지 못했습니다. 잠시 후 다시 시도하세요.") from exc
        except GeminiRequestError as exc:
            status = exc.status_code
            kind = "AUTH_ERROR" if status in (401, 403) else "QUOTA_ERROR" if status == 429 else "NETWORK_OR_API_ERROR"
            add_error(errors, "recommendation", kind, str(exc))
            if status == 429:
                raise PlannerError("LLM 무료 모델의 요청 제한 또는 쿼터를 확인하세요(HTTP 429). 잠시 후 다시 시도하거나 다른 모델을 사용하세요.") from exc
            if status in (401, 403):
                raise PlannerError(f"LLM API 키 또는 설정을 확인하세요(HTTP {status}).") from exc
            raise PlannerError(f"LLM API 연결 또는 응답 처리에 실패했습니다(HTTP {status}).") from exc
    raise PlannerError("Gemini 추천 생성 재시도 한도를 초과했습니다.")


def normalize_place(place: dict[str, Any]) -> dict[str, Any]:
    def as_number(value: Any) -> float | None:
        try:
            return float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None
    return {
        "name": str(place.get("place_name", "")),
        "address": str(place.get("road_address_name") or place.get("address_name") or ""),
        "category": str(place.get("category_name", "")),
        "url": str(place.get("place_url", "")),
        "x": as_number(place.get("x")), "y": as_number(place.get("y")),
    }


def search_restaurants(city: str, errors: list[dict[str, str]]) -> list[dict[str, Any]]:
    kakao_key = os.getenv("KAKAO_REST_API_KEY")
    search_city = normalize_city_name(city)
    if not kakao_key:
        add_error(errors, "place_search", "MISSING_API_KEY", "KAKAO_REST_API_KEY가 없어 장소 검색을 건너뛰었습니다.")
        print("  - KAKAO_REST_API_KEY 미설정: 맛집을 '데이터 없음'으로 처리하고 계속합니다.")
        return []
    try:
        response = requests.get(
            KAKAO_KEYWORD_URL,
            headers={"Authorization": f"KakaoAK {kakao_key}"},
            params={"query": f"{search_city} 맛집", "size": 5},
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code in (401, 403):
            add_error(errors, "place_search", "AUTH_ERROR", f"HTTP {response.status_code}")
            print(f"  - 장소 검색 인증 실패(HTTP {response.status_code}): 데이터 없음으로 계속합니다.")
            return []
        if response.status_code == 429:
            add_error(errors, "place_search", "QUOTA_ERROR", "HTTP 429")
            print("  - 장소 검색 쿼터 제한(HTTP 429): 데이터 없음으로 계속합니다.")
            return []
        response.raise_for_status()
        documents = response.json().get("documents", [])
        if not isinstance(documents, list):
            raise ValueError("Kakao 응답의 documents 형식이 목록이 아닙니다.")
        places = [normalize_place(place) for place in documents[:5] if isinstance(place, dict)]
        if not places:
            add_error(errors, "place_search", "EMPTY_RESULT", f"0 results for query={city} 맛집")
            print("  - 검색 결과 0건: 데이터 없음으로 계속합니다.")
        return places
    except requests.Timeout:
        add_error(errors, "place_search", "NETWORK_TIMEOUT", f"timeout after {TIMEOUT_SECONDS} seconds")
    except requests.RequestException as exc:
        add_error(errors, "place_search", "NETWORK_OR_HTTP_ERROR", str(exc))
    except (ValueError, json.JSONDecodeError) as exc:
        add_error(errors, "place_search", "RESPONSE_PARSE_ERROR", str(exc))
    print("  - 장소 검색 요청 또는 응답 처리 실패: 데이터 없음으로 계속합니다.")
    return []


def fallback_report(date: str, recommendation: dict[str, Any], places: list[dict[str, Any]], errors: list[dict[str, str]]) -> str:
    """LLM 리포트 생성 실패 시 확보한 데이터로 만드는 대체 리포트입니다.
    원래 LLM 리포트 형식(맛집 링크·카테고리, 상세 일정)에 가깝게 맞춥니다."""
    if places:
        restaurants = "\n\n".join(
            f"{i}. **{p['name']}**\n"
            f"   - 주소: {p['address']}\n"
            f"   - 카테고리: {p['category']}\n"
            f"   - 링크: {p['url']}"
            for i, p in enumerate(places, 1)
        )
    else:
        restaurants = "- 데이터 없음"
    events = "\n".join(f"- {event}" for event in recommendation["events"]) or "- 데이터 없음"
    errors_text = "\n".join(f"- [{e['step']}/{e['type']}] {e['message']}" for e in errors) or "- 없음"
    return f"""# {date} 국내 여행 추천 리포트

> 최종 LLM 리포트 생성에 실패해 확보한 데이터로 만든 대체 리포트입니다.

## 추천 지역

- {recommendation['recommended_city']}

## 추천 이유

- {recommendation['reason']}

## 날씨 요약

- {recommendation['weather']}

## 행사/축제

{events}

> ※ 위 행사는 확정이 아닌 후보 정보입니다.

## 맛집 추천

{restaurants}

## 1일 일정 제안

- **오전**
  - {recommendation['recommended_city']} 대표 관광지 및 산책 코스 방문
- **점심**
  - 맛집 목록에서 지역 특색 식당에서 식사
- **오후**
  - 지역 문화 공간 또는 카페 방문
- **저녁**
  - 맛집 목록을 확인해 식사하고 야간 산책으로 마무리

## 오류 요약(errors)

{errors_text}
"""


def create_report(api_key: str, model: str, date: str, recommendation: dict[str, Any], places: list[dict[str, Any]], errors: list[dict[str, str]], provider: str = "gemini") -> str:
    source = json.dumps({"recommendation": recommendation, "restaurants": places, "errors": errors}, ensure_ascii=False, indent=2)
    prompt = f"""다음은 {date} 국내 여행 추천 입력 데이터입니다. 이 데이터만 근거로 한국어 Markdown 리포트를 작성하세요.

{source}

반드시 추천 지역, 추천 이유, 날씨 요약, 행사/축제, 맛집 추천, 1일 일정 제안, 오류 요약(errors) 제목을 포함하세요. 맛집 목록이 비어 있으면 맛집 추천에 정확히 '데이터 없음'이라고 쓰고, 행사는 확정이 아닌 후보임을 밝히세요. 맛집은 번호, 이름, 주소, 카테고리, 링크(URL)를 포함해 주세요."""
    # 현재 제공자가 실패하면 다른 제공자로 재시도 (폴백)
    tried = {provider}
    while True:
        try:
            report = (request_gemini if provider == "gemini" else request_openrouter if provider == "openrouter" else request_copa if provider == "copa" else request_groq)(api_key, model, prompt, max_output_tokens=1400)
            return f"# {date} 국내 여행 추천 리포트\n\n{report.lstrip('# ').strip()}\n"
        except (GeminiRequestError, ValueError) as exc:
            if not _is_quota_or_overload_error(exc):
                break  # 한도/과부하가 아니면 즉시 대체 리포트로
            fallback = _fallback_provider(provider)
            if fallback is None or fallback[0] in tried:
                break
            provider, api_key, model = fallback
            tried.add(provider)
            print(f"  - 리포트 생성 실패: {provider}(으)로 재시도합니다.")
    add_error(errors, "report_generation", "GEMINI_REPORT_ERROR", str(exc))
    print("  - 최종 LLM 리포트 생성 실패: 대체 Markdown 리포트를 저장합니다.")
    return fallback_report(date, recommendation, places, errors)


def load_cached_data(date: str) -> dict[str, Any] | None:
    """기존 저장된 원본 데이터(JSON)가 있으면 읽어와 반환 (항목 4: 결과 캐싱 전략)."""
    data_path = RESULTS_DIR / f"{date}_travel_data.json"
    if not data_path.exists():
        return None
    try:
        content = json.loads(data_path.read_text(encoding="utf-8"))
        if isinstance(content, dict) and "recommendation" in content and "restaurants" in content:
            return content
    except Exception:
        return None
    return None


def write_results(date: str, recommendation: dict[str, Any], places: list[dict[str, Any]], errors: list[dict[str, str]], report: str) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(exist_ok=True)
    data_path, report_path = RESULTS_DIR / f"{date}_travel_data.json", RESULTS_DIR / f"{date}_travel_plan.md"
    data_path.write_text(json.dumps({"travel_date": date, "recommendation": recommendation, "restaurants": places, "errors": errors}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(report, encoding="utf-8")
    return data_path, report_path


def run_pipeline(provider: str, api_key: str, model: str, travel_date: str, errors: list[dict[str, str]]) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    """선택된 제공자로 [1/3] → [2/3] → [3/3] 전체 파이프라인을 실행합니다."""
    print(f"[1/3] 1차 추천 생성 중({provider})...")
    recommendation = create_recommendation(api_key, model, travel_date, errors, provider)
    print(f"  - recommended_city: {recommendation['recommended_city']}")
    print("[2/3] 맛집 검색 중(Kakao Local API)...")
    places = search_restaurants(recommendation["recommended_city"], errors)
    print(f"  - 맛집 {len(places)}곳 검색 완료")
    print(f"[3/3] 최종 리포트 생성 중({provider})...")
    report = create_report(api_key, model, travel_date, recommendation, places, errors, provider)
    return recommendation, places, report


def _is_quota_or_overload_error(exc: Exception) -> bool:
    """429(요청 제한) 또는 503(과부하) 성격의 오류인지 확인합니다. 전환 대상 여부 판단에 씁니다."""
    text = str(exc)
    return any(keyword in text for keyword in ("429", "503", "제한", "쿼터", "과부하"))


def _fallback_provider(provider: str) -> tuple[str, str, str] | None:
    """현재 제공자가 안 되면 대신 쓸 수 있는 다른 제공자를 찾습니다. 키가 없으면 None.
    폴백 순서: Gemini → OpenRouter(무료 라우터) → Copa(OpenAI 호환)"""
    if provider == "gemini":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            return "openrouter", openrouter_key, os.getenv("OPENROUTER_MODEL", "openrouter/free")
        copa_key = os.getenv("COPA_API_KEY")
        if copa_key:
            return "copa", copa_key, os.getenv("COPA_MODEL", "gpt-5-mini")
    if provider == "openrouter":
        copa_key = os.getenv("COPA_API_KEY")
        if copa_key:
            return "copa", copa_key, os.getenv("COPA_MODEL", "gpt-5-mini")
        api_key, model = build_gemini_settings()
        return "gemini", api_key, model
    if provider == "copa":
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            return "openrouter", openrouter_key, os.getenv("OPENROUTER_MODEL", "openrouter/free")
        api_key, model = build_gemini_settings()
        return "gemini", api_key, model
    return None


def main() -> int:
    args = parse_args()
    load_dotenv(BASE_DIR / ".env")
    errors: list[dict[str, str]] = []

    # 항목 4: 결과 캐싱 검사
    cached_data = None
    if args.cached or (not args.refresh and (RESULTS_DIR / f"{args.travel_date}_travel_data.json").exists()):
        cached_data = load_cached_data(args.travel_date)

    if cached_data:
        print(f"[캐시 재사용] {args.travel_date} 저장된 원본 JSON을 활용하여 외부 API 호출을 생략합니다.")
        print("  - (새로고침을 원할 경우 --refresh 옵션을 사용하세요)")
        recommendation = cached_data["recommendation"]
        places = cached_data["restaurants"]
        errors = cached_data.get("errors", [])
        report_path = RESULTS_DIR / f"{args.travel_date}_travel_plan.md"
        data_path = RESULTS_DIR / f"{args.travel_date}_travel_data.json"

        if not report_path.exists():
            report = fallback_report(args.travel_date, recommendation, places, errors)
            report_path.write_text(report, encoding="utf-8")

        print("  - 캐시 기반 리포트 로드 완료")
        print(f"완료! {report_path.relative_to(BASE_DIR)} 및 {data_path.relative_to(BASE_DIR)}를 확인하세요.")
        return 0

    try:
        provider, api_key, model = build_llm_settings()
        # 3중 폴백: 현재 제공자가 429/503으로 실패하면 다른 제공자로 순서대로 전환
        tried = {provider}
        while True:
            try:
                recommendation, places, report = run_pipeline(provider, api_key, model, args.travel_date, errors)
                break
            except (PlannerError, GeminiRequestError) as exc:
                if not _is_quota_or_overload_error(exc):
                    raise
                fallback = _fallback_provider(provider)
                if fallback is None or fallback[0] in tried:
                    raise
                provider, api_key, model = fallback
                tried.add(provider)
                print(f"  - 현재 제공자 장애/한도로 인해 {provider}(으)로 자동 전환합니다.")
        data_path, report_path = write_results(args.travel_date, recommendation, places, errors, report)
        print("  - 리포트 생성 완료")
        print(f"완료! {report_path.relative_to(BASE_DIR)} 및 {data_path.relative_to(BASE_DIR)}를 확인하세요.")
        return 0
    except PlannerError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
