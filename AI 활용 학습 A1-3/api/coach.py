"""ENTHES 공식 스쿼시 리그 (ESL) AI 코칭 분석 엔진.

Vercel Python Serverless Function (POST /api/coach).
보안 원칙: GEMINI_API_KEY는 환경 변수에서만 안전하게 읽으며, 응답이나 로그에 노출하지 않습니다.
안전 원칙: API 키 미설정 또는 네트워크 장애 시에도 내장 휴리스틱 룰 엔진으로 양 선수 개별 분석을 지속합니다.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from typing import Any

MAX_MEMO_LENGTH = 500

STAT_KEYS = ["forehand", "backhand", "attackOption", "speed", "stamina", "composure"]


def clean_text(value: Any, max_len: int = 500) -> str:
    """텍스트 입력값을 정제하고 제어 문자를 제거합니다."""
    if not isinstance(value, str):
        return ""
    sanitized = re.sub(r"[\x00-\x1f\x7f]", " ", value).strip()
    return sanitized[:max_len]


def rule_based_dual_analysis(player_a: str, player_b: str, score_a: int, score_b: int, memo: str) -> dict[str, Any]:
    """Gemini API 키가 없거나 외부 API 호출 실패 시 작동하는 고품질 내장 휴리스틱 룰 엔진 (양 선수 개별 분석 지원)."""
    winner = player_a if score_a > score_b else player_b
    loser = player_b if score_a > score_b else player_a
    win_score = max(score_a, score_b)
    lose_score = min(score_a, score_b)
    diff = win_score - lose_score

    # Winner default adjustments (+1 ~ +2), Loser default adjustments (-1 ~ 0)
    winner_adj = {k: 0 for k in STAT_KEYS}
    loser_adj = {k: 0 for k in STAT_KEYS}

    winner_adj["forehand"] = 1
    winner_adj["speed"] = 1
    winner_adj["composure"] = 1

    loser_adj["stamina"] = -1 if diff >= 4 else 0

    memo_lower = memo.lower() if memo else ""
    winner_notes = []
    loser_notes = []
    practice_tips = []

    # 1. 포핸드 / 렝스 드라이브 분석
    if any(k in memo_lower for k in ["포핸드", "드라이브", "렝스", "벽밀착"]):
        winner_adj["forehand"] = min(2, winner_adj["forehand"] + 1)
        winner_notes.append(f"{winner} 선수의 깊숙한 사이드월 드라이브 렝스가 코트 모서리에 정확히 꽂혀 랠리를 지배했습니다.")
        loser_notes.append(f"{loser} 선수는 수세 시 드라이브 길이가 짧아져 상대에게 전위 찬스를 허용했습니다.")
        practice_tips.append("솔로 레일 드릴: 벽과 1미터 거리를 유지하며 드라이브를 연속으로 15회 벽에 붙이는 훈련을 권장합니다.")

    # 2. 백핸드 / 코너 수비 분석
    if any(k in memo_lower for k in ["백핸드", "백", "코너수비", "탈출"]):
        if winner in memo:
            winner_adj["backhand"] = 1
            winner_notes.append(f"{winner} 선수의 백핸드 코너 수비 전환 및 로브가 결정적이었습니다.")
        else:
            loser_adj["backhand"] = max(-2, loser_adj["backhand"] - 1)
            loser_notes.append(f"{loser} 선수는 백핸드 구석 수비 시 타점이 뒤로 밀리는 경향이 관찰되었습니다.")
            practice_tips.append("백핸드 코너 보스트 탈출 및 크로스 리턴 20회 반복 드릴을 권장합니다.")

    # 3. 공격옵션 / 드롭 / 닉샷 / 발리 분석
    if any(k in memo_lower for k in ["공격", "드롭", "닉", "킬샷", "발리", "t존"]):
        winner_adj["attackOption"] = min(2, winner_adj["attackOption"] + 2)
        winner_notes.append(f"{winner} 선수가 T존을 선점하고 정교한 드롭샷과 빠른 킬샷으로 많은 득점을 올렸습니다.")
        if any(w in memo_lower for w in ["틴", "범실", "실수"]):
            loser_notes.append(f"{loser} 선수는 앞벽 아래 틴(Tin) 범실로 아쉽게 실점하는 빈도를 줄여야 합니다.")
            practice_tips.append("앞 코너 타깃 맞추기 드롭 정밀 타격 및 T존 복귀 40구 드릴을 추천합니다.")

    # 4. 스피드 & 체력 분석
    if any(k in memo_lower for k in ["체력", "스피드", "속도", "풋워크", "커버", "뛰"]):
        winner_adj["speed"] = min(2, winner_adj["speed"] + 1)
        winner_adj["stamina"] = min(2, winner_adj["stamina"] + 1)
        winner_notes.append(f"경기 후반까지 왕성한 활동량으로 코트 전 영역을 커버한 풋워크가 돋보였습니다.")
        loser_notes.append(f"후반 세트 접전 시 체력 소모로 인해 중심이 높아지는 점을 보완해야 합니다.")
        practice_tips.append("코트 6점 고스트 풋워크(Ghosting Footwork) 3세트(각 1분)로 인터벌 체력을 강화하세요.")

    # 기본값 보정
    if not winner_notes:
        winner_notes.append(f"{winner} 선수가 세트 후반까지 집중력을 유지하며 {diff}점 차 승리를 이끌어냈습니다.")
    if not loser_notes:
        loser_notes.append(f"{loser} 선수는 끈질기게 랠리를 추격했으나 승부처에서의 결정력에서 다소 아쉬움을 남겼습니다.")
    if not practice_tips:
        practice_tips.append("기본 렝스 드라이브 4구 후 전위 킬샷으로 마무리하는 2인 컴비네이션 드릴을 권장합니다.")

    match_summary = (
        f"{winner} 선수가 {loser} 선수를 상대로 {win_score}:{lose_score} ({diff}점 차) 접전 끝에 승리했습니다. "
        + ("경기 메모에 나타난 기술적 활약상이 스탯에 반영되었습니다." if memo else "점수 데이터를 기반으로 표준 경기력이 분석되었습니다.")
    )

    stat_adjustments = {
        player_a: winner_adj if player_a == winner else loser_adj,
        player_b: winner_adj if player_b == winner else loser_adj,
    }

    return {
        "matchSummary": match_summary,
        "winnerAnalysis": " ".join(winner_notes),
        "loserAnalysis": " ".join(loser_notes),
        "practiceTip": practice_tips[0],
        "statAdjustments": stat_adjustments,
        "provider": "local_rules",
        "model_used": "ENTHES Heuristic Rules Engine (Fallback)",
    }


def build_gemini_prompt(player_a: str, player_b: str, score_a: int, score_b: int, memo: str) -> str:
    """스쿼시 전문 AI 코칭을 위한 정밀 프롬프트를 구성합니다."""
    winner = player_a if score_a > score_b else player_b
    loser = player_b if score_a > score_b else player_a
    optional_memo = f'"{memo}"' if memo else '(경기 메모가 별도로 작성되지 않아 세트 스코어 기준으로 분석합니다.)'

    return f"""당신은 공식 스쿼시 리그(ESL)의 수석 코치 AI입니다.
선수들의 경기 점수와 현장 관찰 메모를 분석하여 승자와 패자 각각에 대한 전문적인 코칭 피드백과 6축 스탯 변동량을 산출하세요.

[경기 정보]
- 승자: {winner} ({max(score_a, score_b)}점)
- 패자: {loser} ({min(score_a, score_b)}점)
- 현장 관찰 메모: {optional_memo}

[6대 스탯 지표]
1. forehand (포핸드): 드라이브 파워 및 안정성
2. backhand (백핸드): 백핸드 스트로크 및 코너 리턴
3. attackOption (공격옵션): 드롭, 발리, 닉샷 등 전위 공격
4. speed (스피드): 코트 커버 및 전후좌우 이동 속도
5. stamina (체력): 랠리 지속력 및 후반 집중력
6. composure (침착성): 위기 탈출 보스트 및 에러 억제

[작성 가이드라인]
1. matchSummary: 경기의 전체적인 흐름과 승부처를 1~2문장으로 간결하게 요약합니다.
2. winnerAnalysis: 승자의 결정적 득점 요인, 기술적 우위, 코트 장악력을 1~2문장으로 칭찬합니다.
3. loserAnalysis: 패자의 보완점, 범실 원인 또는 전술적 약점을 부드럽고 건설적인 어조로 분석합니다.
4. practiceTip: 다음 경기 보완을 위해 코트에서 즉시 할 수 있는 구체적인 훈련 드릴(연습법) 1가지를 제시합니다.
5. statAdjustments: 두 선수 각각의 6대 스탯 변동치를 산출합니다.
   - 인플레이션 방지를 위해 각 스탯은 -2, -1, 0, +1, +2 중 하나여야 합니다.
   - 승자는 주로 +1~+2, 패자는 주로 0 또는 -1~-2가 적용됩니다.

[반환 형식]
반드시 유효한 JSON 형식으로만 응답하세요 (Markdown 태그 없이 순수 JSON):
{{
  "matchSummary": "경기 총평 요약",
  "winnerAnalysis": "승자 분석",
  "loserAnalysis": "패자 분석",
  "practiceTip": "추천 훈련 드릴",
  "statAdjustments": {{
    "{player_a}": {{
      "forehand": 1, "backhand": 0, "attackOption": 1, "speed": 1, "stamina": 1, "composure": 0
    }},
    "{player_b}": {{
      "forehand": 0, "backhand": 0, "attackOption": 0, "speed": -1, "stamina": -1, "composure": 0
    }}
  }}
}}"""


def call_gemini_rest_api(api_key: str, model_name: str, prompt: str) -> dict[str, Any]:
    """urllib를 사용해 Google Gemini REST API를 호출합니다."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=12) as response:
        res_data = json.loads(response.read().decode("utf-8"))

    candidates = res_data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini API에서 생성된 결과가 없습니다.")

    text_output = candidates[0]["content"]["parts"][0]["text"]
    cleaned_json = re.sub(r"^```(?:json)?\s*", "", text_output.strip(), flags=re.IGNORECASE)
    cleaned_json = re.sub(r"\s*```$", "", cleaned_json)

    parsed = json.loads(cleaned_json)
    parsed["provider"] = "gemini"
    parsed["model_used"] = f"Google Gemini ({model_name})"
    return parsed


class handler(BaseHTTPRequestHandler):
    """Vercel Python Serverless Function 요청 처리 핸들러."""

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._send_json(
            HTTPStatus.OK,
            {
                "status": "online",
                "service": "ENTHES ESL AI Coach Dual-Player API",
                "version": "2026.2.1",
                "method": "POST /api/coach with JSON body",
            },
        )

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0 or content_length > 8192:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "요청 본문의 크기가 올바르지 않습니다."})
            return

        try:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(raw_body)
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "JSON 요청 형식을 파싱할 수 없습니다."})
            return

        player_a = clean_text(data.get("player_a"), 40)
        player_b = clean_text(data.get("player_b"), 40)
        memo = clean_text(data.get("memo"), MAX_MEMO_LENGTH)

        try:
            score_a = int(data.get("score_a", 0))
            score_b = int(data.get("score_b", 0))
        except (ValueError, TypeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "점수는 올바른 숫자 형식이어야 합니다."})
            return

        # 1. 필수값 검증 (선수 선택 여부)
        if not player_a or not player_b:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "경기 참가 선수 A와 B를 모두 지정해 주세요."})
            return

        if player_a == player_b:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "서로 다른 선수를 선택해 주세요."})
            return

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()

        # 2. API Key 존재 시 Google Gemini 호출 시도
        if api_key:
            try:
                prompt = build_gemini_prompt(player_a, player_b, score_a, score_b, memo)
                result = call_gemini_rest_api(api_key, model_name, prompt)
                self._send_json(HTTPStatus.OK, result)
                return
            except Exception:
                pass

        # 3. API Key 미설정 또는 호출 오류 시 로컬 룰 엔진으로 즉각 폴백
        fallback = rule_based_dual_analysis(player_a, player_b, score_a, score_b, memo)
        self._send_json(HTTPStatus.OK, fallback)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return
